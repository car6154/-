/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useMemo } from 'react';
import { INITIAL_CAR_LEDGER } from '@/data/initialData';
import { INITIAL_SETTLEMENT_ITEMS } from '@/data/settlementSeedData';
import { CarLedgerItem, InventorySettlementItem, CockpitPresetData } from '@/types';
import { Header, AppTab } from '@/components/Header';
import { LedgerTab } from '@/components/LedgerTab';
import { BiddingCockpitTab } from '@/components/BiddingCockpitTab';
import { SettlementTab } from '@/components/SettlementTab';
import { SoldOutSettlementTab } from '@/components/SoldOutSettlementTab';
import { CompanyPerformanceTab } from '@/components/CompanyPerformanceTab';
import { CompanyInventoryTab } from '@/components/CompanyInventoryTab';
import { CarDetailModal } from '@/components/CarDetailModal';
import { AddCarModal } from '@/components/AddCarModal';
import { DriveModal } from '@/components/DriveModal';
import { CookieSyncModal } from '@/components/CookieSyncModal';
import { MobileNav } from '@/components/MobileNav';
import { RefreshCw, Cloud, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { sendCarToGoogleSheet } from '@/services/googleSheetService';
import { startContinuousCookieSync, subscribeCookieSync, uploadCookieToServer } from '@/services/cookieBridge';

export default function App() {
  // 1. Persistence for cars ledger (Real Python backend my_car_ledger.csv & fallback)
  const [cars, setCars] = useState<CarLedgerItem[]>(() => {
    try {
      const saved = localStorage.getItem('jpro_ledger_v3');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (e) {
      console.error('Failed to load saved ledger:', e);
    }
    return INITIAL_CAR_LEDGER;
  });

  // 로컬 FastAPI 백엔드(http://127.0.0.1:8000/api/ledger)에서 진짜 my_car_ledger.csv 데이터 로드
  useEffect(() => {
    let isMounted = true;
    fetch('http://127.0.0.1:8000/api/ledger')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (isMounted && Array.isArray(data) && data.length > 0) {
          console.log(`[J-PRO] 로컬 my_car_ledger.csv 장부 ${data.length}건 동기화 완료`);
          setCars(data);
        }
      })
      .catch((err) => {
        console.warn('[J-PRO] 백엔드 장부 API 미응답 (localStorage/기본값 유지):', err.message);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem('jpro_ledger_v3', JSON.stringify(cars));
    } catch (e) {
      console.error('Failed to save ledger:', e);
    }
  }, [cars]);

  // 2. Persistence for Jay's real settlement items (37다1840 카니발 보유 1대 & 297로2620 레이 완판 1대)
  const [settlementItems, setSettlementItems] = useState<InventorySettlementItem[]>(() => {
    try {
      localStorage.removeItem('jpro_settlement_v1');
      localStorage.removeItem('jpro_settlement_v2');
      localStorage.removeItem('jpro_settlement_v3');
      localStorage.removeItem('jpro_settlement_v4');
      const saved = localStorage.getItem('jpro_settlement_v5');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (e) {
      console.error('Failed to load saved settlement:', e);
    }
    return INITIAL_SETTLEMENT_ITEMS;
  });

  useEffect(() => {
    try {
      localStorage.setItem('jpro_settlement_v5', JSON.stringify(settlementItems));
    } catch (e) {
      console.error('Failed to save settlement:', e);
    }
  }, [settlementItems]);

  // 로컬 FastAPI 백엔드(http://127.0.0.1:8000/api/settlement)에서 진짜 my_inventory_settlement.csv 데이터 로드
  useEffect(() => {
    let isMounted = true;
    fetch('http://127.0.0.1:8000/api/settlement')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (isMounted && Array.isArray(data) && data.length > 0) {
          console.log(`[J-PRO] 로컬 my_inventory_settlement.csv 정산 ${data.length}건 동기화 완료`);
          setSettlementItems(data);
        }
      })
      .catch((err) => {
        console.warn('[J-PRO] 백엔드 정산 API 미응답 (localStorage/기본값 유지):', err.message);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Privacy Unlock State (장부/정산/재고 숨김 모드)
  const [isPrivateUnlocked, setIsPrivateUnlocked] = useState<boolean>(() => {
    return localStorage.getItem('jpro_privacy_unlocked') === 'true';
  });

  // Tab & Search state
  const [activeTab, setActiveTab] = useState<AppTab>('cockpit');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals state
  const [selectedCar, setSelectedCar] = useState<CarLedgerItem | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isDriveModalOpen, setIsDriveModalOpen] = useState(false);
  const [isCookieModalOpen, setIsCookieModalOpen] = useState(false);

  // Cookie status state
  const [cookieStatus, setCookieStatus] = useState<'active' | 'expired' | 'missing'>('missing');

  useEffect(() => {
    // 1. 실시간 로컬 IDE(8502 포트) & 크롬 확장프로그램 자동 동기화 엔진 기동
    const stopSync = startContinuousCookieSync();

    // 2. 동기화 상태 실시간 수신
    const unsubscribe = subscribeCookieSync((status) => {
      if (status.hasHeydealer || status.hasAutoplus) {
        setCookieStatus('active');
      } else {
        setCookieStatus('missing');
      }
    });

    return () => {
      stopSync();
      unsubscribe();
    };
  }, []);

  // Floating Toast Notification state
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3800);
  };

  // Cockpit Preset state (장부/재고 역추적 시세 분석용)
  const [cockpitPreset, setCockpitPreset] = useState<CockpitPresetData | null>(null);

  // 🔗 URL 파라미터 딥링크 파싱 (예: ?tab=cockpit&car=37다1840)
  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get('tab') as AppTab | null;
      const carParam = params.get('car');
      const hashIdParam = params.get('hashId');
      const titleParam = params.get('title');

      if (tabParam && ['cockpit', 'ledger', 'settlement', 'soldout', 'performance', 'inventory'].includes(tabParam)) {
        setActiveTab(tabParam);
      }

      if (hashIdParam || titleParam) {
        setActiveTab('cockpit');
        setCockpitPreset({
          carName: titleParam ? decodeURIComponent(titleParam) : '',
          memo: `[헤이딜러 1초 연동 매물: ${hashIdParam || ''}]`
        });
        showToast(`⚡ 헤이딜러 매물 [${titleParam ? decodeURIComponent(titleParam) : hashIdParam}] 콕핏 연동 완료!`);
      } else if (carParam) {
        setCockpitPreset({
          carNumber: carParam,
          memo: `[URL 직통 딥링크 조회: ${carParam}]`
        });
        showToast(`🔗 URL 직통 파라미터 [${carParam}] 시세 분석 콕핏으로 연동되었습니다.`);
      }
    } catch (e) {
      console.error(e);
    }
  }, []);

  // 🔗 현재 탭 및 차량 상태를 브라우저 URL에 실시간 반영 (새로고침/공유 시 유지)
  useEffect(() => {
    try {
      const url = new URL(window.location.href);
      url.searchParams.set('tab', activeTab);
      if (cockpitPreset?.carNumber) {
        url.searchParams.set('car', cockpitPreset.carNumber);
      } else {
        url.searchParams.delete('car');
      }
      window.history.replaceState({}, '', url.toString());
    } catch (e) {
      console.error(e);
    }
  }, [activeTab, cockpitPreset]);

  // KPI calculations
  const totalCarsCount = cars.length;
  const totalBuyAmount = useMemo(() => cars.reduce((acc, c) => acc + (c.buyPrice || 0), 0), [cars]);
  const avgMargin = useMemo(() => {
    if (!cars.length) return 0;
    const totalMargin = cars.reduce(
      (acc, c) => acc + (c.sellPrice - c.buyPrice - c.repairCost - c.heydealerFee),
      0
    );
    return Math.round(totalMargin / cars.length);
  }, [cars]);

  // Handlers
  const handleUpdateStatus = async (id: string, newStatus: string) => {
    setCars(prev => prev.map(c => (c.id === id ? { ...c, status: newStatus } : c)));
    const target = cars.find(c => c.id === id);
    const key = target?.carNumber || id;
    try {
      await fetch(`http://127.0.0.1:8000/api/ledger/${encodeURIComponent(key)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
    } catch (e) {
      console.warn('[J-PRO] 백엔드 상태 갱신 경고:', e);
    }
  };

  const handleUpdateCar = async (updatedCar: CarLedgerItem) => {
    setCars(prev => prev.map(c => (c.id === updatedCar.id ? updatedCar : c)));
    const key = updatedCar.carNumber || updatedCar.id;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/ledger/${encodeURIComponent(key)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          carNumber: updatedCar.carNumber,
          manufacturer: updatedCar.manufacturer,
          carName: updatedCar.carName,
          detailModel: updatedCar.detailModel,
          year: updatedCar.year,
          mileage: updatedCar.mileage,
          options: updatedCar.options,
          buyPrice: updatedCar.buyPrice,
          sellPrice: updatedCar.sellPrice,
          outerRepairs: updatedCar.outerRepairs,
          repairCost: updatedCar.repairCost,
          heydealerFee: updatedCar.heydealerFee,
          memo: updatedCar.memo,
          status: updatedCar.status,
        }),
      });
      if (res.ok) {
        showToast(`💾 [${updatedCar.carNumber}] 장부 수정사항이 CSV에 영구 저장되었습니다.`);
      }
    } catch (e) {
      console.warn('[J-PRO] 백엔드 장부 수정 경고:', e);
    }
  };

  const handleDeleteCar = async (id: string) => {
    const target = cars.find(c => c.id === id);
    const key = target?.carNumber || id;
    setCars(prev => prev.filter(c => c.id !== id));
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/ledger/${encodeURIComponent(key)}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        showToast(`🗑️ [${target?.carNumber || key}] 장부 CSV에서 영구 삭제되었습니다.`);
      }
    } catch (e) {
      console.warn('[J-PRO] 백엔드 장부 삭제 경고:', e);
    }
  };

  const handleAddCar = async (newCarData: Omit<CarLedgerItem, 'id' | 'regDate'>) => {
    const today = new Date();
    const yy = String(today.getFullYear()).slice(2);
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    const regDate = `${yy}-${mm}-${dd}`;

    const newCar: CarLedgerItem = {
      id: `${newCarData.carNumber}_${regDate}`,
      regDate,
      ...newCarData,
    };

    // 1. UI 및 브라우저 상태 즉시 갱신 (동일 차량번호가 있으면 갱신, 없으면 상단 추가)
    setCars(prev => {
      const filtered = prev.filter(c => c.carNumber !== newCarData.carNumber);
      return [newCar, ...filtered];
    });

    // 2. 파이썬 로컬 백엔드를 통해 실제 my_car_ledger.csv 파일에 영구 기록
    try {
      const ledgerRes = await fetch('http://127.0.0.1:8000/api/ledger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          regDate,
          carNumber: newCarData.carNumber,
          manufacturer: newCarData.manufacturer,
          carName: newCarData.carName,
          detailModel: newCarData.detailModel,
          year: newCarData.year,
          mileage: newCarData.mileage,
          options: newCarData.options,
          buyPrice: newCarData.buyPrice,
          sellPrice: newCarData.sellPrice,
          outerRepairs: newCarData.outerRepairs,
          repairCost: newCarData.repairCost,
          heydealerFee: newCarData.heydealerFee,
          memo: newCarData.memo,
          status: newCarData.status || '장부저장'
        })
      });

      if (ledgerRes.ok) {
        const resJson = await ledgerRes.json();
        showToast(`✅ [${newCarData.carNumber}] my_car_ledger.csv 영구 저장 완료! (총 ${resJson.totalCount}대)`);
      } else {
        showToast(`✅ [${newCarData.carNumber}] 브라우저 장부 저장 완료`);
      }
    } catch (err: any) {
      console.warn('로컬 CSV 저장 API 호출 경고:', err);
      showToast(`✅ [${newCarData.carNumber}] 브라우저 장부 저장 완료`);
    }

    // 3. 🚀 Google Sheets Realtime Webhook Auto-Sync
    try {
      await sendCarToGoogleSheet({
        차량번호: newCarData.carNumber,
        제조사: newCarData.manufacturer,
        차량명: newCarData.carName,
        세부모델: newCarData.detailModel,
        연식: newCarData.year,
        주행거리: newCarData.mileage,
        옵션: newCarData.options,
        매입가: newCarData.buyPrice,
        판매가: newCarData.sellPrice,
        외판수리: newCarData.outerRepairs,
        외판수리비: newCarData.repairCost,
        헤딜수수료: newCarData.heydealerFee,
        특이사항: newCarData.memo,
        상태: newCarData.status || '장부저장',
        등록일: regDate
      });
    } catch (err) {
      console.error('Google Sheet auto-sync error:', err);
    }
  };

  // Mark a car as sold in settlement
  const handleMarkSold = async (id: string, finalSellPrice?: number) => {
    const target = settlementItems.find(item => item.id === id);
    if (!target) return;

    const sell = finalSellPrice || target.sellPrice || 0;
    const buy = target.buyPrice || 0;
    const vatMargin = sell > buy ? Math.round(((sell - buy) / 1.1) * 10) / 10 : 0;
    const heyFeeTax = Math.round(target.heydealerFee * 1.1 * 10) / 10;
    const comm = Math.round(sell * 0.003 * 10) / 10;
    const contrib = Math.round((vatMargin - heyFeeTax - (target.repairCost || 0) - 15 - comm) * 10) / 10;
    const myTake = Math.round(contrib * (target.feeRate || 0.1) * 10) / 10;

    const updatedItem = {
      ...target,
      status: '판매완료',
      sellPrice: sell,
      contributionMargin: contrib,
      netProfit: myTake,
      finalProfit: myTake,
    };

    setSettlementItems(prev => prev.map(item => (item.id === id ? updatedItem : item)));

    // 백엔드 my_inventory_settlement.csv에 판매완료 및 정산 결과 영구 반영
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/settlement/${encodeURIComponent(target.carNumber)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: '판매완료',
          sellPrice: sell,
          contributionMargin: contrib,
          netProfit: myTake,
          finalProfit: myTake,
        }),
      });
      if (res.ok) {
        showToast(`🎉 [${target.carNumber}] 판매완료 정산이 my_inventory_settlement.csv에 영구 저장되었습니다.`);
      }
    } catch (e) {
      console.warn('[J-PRO] 백엔드 정산 상태 갱신 경고:', e);
    }
  };

  // Confirm purchase from ledger into inventory settlement (tab_ledger.py workflow)
  const handleConfirmPurchase = async (car: CarLedgerItem, actualBuyPrice: number) => {
    const alreadyExists = settlementItems.some(s => s.carNumber === car.carNumber);
    if (alreadyExists) {
      showToast(`⚠️ [${car.carNumber}] 이미 재고 및 정산 관리에 등록된 차량입니다.`);
      setActiveTab('settlement');
      return;
    }

    const today = new Date();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    const buyDate = `${mm}. ${dd}`;

    const newSettlementItem: InventorySettlementItem = {
      id: `settle_${car.carNumber}`,
      order: settlementItems.length + 1,
      buyDate,
      status: '보유/상품화중',
      carNumber: car.carNumber,
      carName: `${car.manufacturer} ${car.carName} ${car.detailModel}`.trim(),
      sellPrice: car.sellPrice,
      stockDays: 0,
      buyPrice: actualBuyPrice || car.buyPrice,
      outerRepairs: car.outerRepairs,
      repairCost: car.repairCost,
      heydealerFee: car.heydealerFee,
      baseExpenses: 15,
      contributionMargin: 0,
      netProfit: 0,
      feeRate: 0.10,
      salesCommission: Math.round(car.sellPrice * 0.007),
      finalProfit: 0,
      isMine: true,
    };

    setSettlementItems(prev => [newSettlementItem, ...prev]);
    setCars(prev => prev.map(c => c.id === car.id ? { ...c, status: '보유중', buyPrice: actualBuyPrice || c.buyPrice } : c));

    // 1. my_inventory_settlement.csv 에 영구 등록
    try {
      const settleRes = await fetch('http://127.0.0.1:8000/api/settlement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          buyDate,
          status: '보유/상품화중',
          carNumber: car.carNumber,
          carName: `${car.manufacturer} ${car.carName} ${car.detailModel}`.trim(),
          sellPrice: car.sellPrice,
          stockDays: 0,
          buyPrice: actualBuyPrice || car.buyPrice,
          outerRepairs: car.outerRepairs,
          repairCost: car.repairCost,
          heydealerFee: car.heydealerFee,
          baseExpenses: 15,
          contributionMargin: 0,
          netProfit: 0,
          feeRate: 0.10,
          salesCommission: Math.round(car.sellPrice * 0.007),
          finalProfit: 0,
          isMine: true,
        }),
      });

      // 2. my_car_ledger.csv 에도 보유중 상태 및 실제 매입가 갱신
      await fetch(`http://127.0.0.1:8000/api/ledger/${encodeURIComponent(car.carNumber)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: '보유중',
          buyPrice: actualBuyPrice || car.buyPrice,
        }),
      });

      if (settleRes.ok) {
        showToast(`🎉 [${car.carNumber}] 매입 확정! my_inventory_settlement.csv에 등록 완료되었습니다.`);
      }
    } catch (e) {
      console.warn('[J-PRO] 백엔드 정산 등록 경고:', e);
    }

    setActiveTab('settlement');
  };

  // Jump to cockpit for instant market comparison with full ledger details
  const handleAnalyzeInCockpit = (car: CarLedgerItem) => {
    let parsedYear = 20;
    const yearMatch = (car.year || '').match(/\d+/);
    if (yearMatch) {
      let y = parseInt(yearMatch[0], 10);
      if (y > 2000) y -= 2000;
      parsedYear = y;
    }

    let parsedMileage = 40000;
    const milClean = (car.mileage || '').replace(/[^\d]/g, '');
    if (milClean) {
      parsedMileage = parseInt(milClean, 10);
    }

    setCockpitPreset({
      carNumber: car.carNumber,
      manufacturer: car.manufacturer,
      carName: car.carName,
      detailModel: car.detailModel,
      year: parsedYear,
      mileage: parsedMileage,
      sellPrice: car.sellPrice,
      buyPrice: car.buyPrice,
      outerRepairs: car.outerRepairs || 0,
      options: car.options || '+기본형',
      memo: car.memo || `[장부 역추적 / 매입가: ${car.buyPrice}만 / 예상소매: ${car.sellPrice}만]`,
      targetMargin: 120,
    });
    showToast(`🔍 [${car.carNumber} ${car.carName}] 사이드바 필터 및 실시간 역추적 시세 연동 완료!`);
    setActiveTab('cockpit');
  };

  // Jump to cockpit for instant market comparison with full settlement inventory details
  const handleAnalyzeSettlementInCockpit = (item: InventorySettlementItem) => {
    let brand = '현대';
    if (item.carName.includes('기아') || item.carName.includes('카니발') || item.carName.includes('레이') || item.carName.includes('모닝') || item.carName.includes('K5')) {
      brand = '기아';
    } else if (item.carName.includes('르노') || item.carName.includes('SM') || item.carName.includes('QM')) {
      brand = '르노코리아';
    } else if (item.carName.includes('KG') || item.carName.includes('쌍용')) {
      brand = 'KG모빌리티';
    } else if (item.carName.includes('제네시스') || item.carName.includes('G80')) {
      brand = '제네시스';
    }

    setCockpitPreset({
      carNumber: item.carNumber,
      manufacturer: brand,
      carName: item.carName,
      detailModel: item.carName,
      year: 20,
      mileage: 45000,
      sellPrice: item.sellPrice,
      buyPrice: item.buyPrice,
      outerRepairs: item.outerRepairs || 0,
      options: '+기본형',
      memo: `[재고 역추적 / 매입일: ${item.buyDate} / ${item.stockDays}일차 재고]`,
      targetMargin: 120,
    });
    showToast(`🎯 [${item.carNumber} ${item.carName}] 사이드바 필터 및 실시간 역추적 시세 연동 완료!`);
    setActiveTab('cockpit');
  };

  // Jump to cockpit for instant market comparison from company performance DB
  const handleAnalyzePerformanceInCockpit = (record: any) => {
    let brand = '현대';
    if (record.carName.includes('기아') || record.carName.includes('카니발') || record.carName.includes('레이') || record.carName.includes('모닝') || record.carName.includes('K5')) {
      brand = '기아';
    } else if (record.carName.includes('르노') || record.carName.includes('SM') || record.carName.includes('QM')) {
      brand = '르노코리아';
    } else if (record.carName.includes('KG') || record.carName.includes('쌍용')) {
      brand = 'KG모빌리티';
    } else if (record.carName.includes('제네시스') || record.carName.includes('G80')) {
      brand = '제네시스';
    }

    setCockpitPreset({
      carNumber: record.plate,
      manufacturer: brand,
      carName: record.carName,
      detailModel: record.subModel,
      year: 20,
      mileage: record.mileage || 40000,
      sellPrice: record.sellPrice || 1400,
      buyPrice: record.buyPrice || 1200,
      outerRepairs: 0,
      options: '+순정옵션',
      memo: `[실적DB 역추적 / 판매일: ${record.regDate} / ${record.stockDays}일 완판]`,
      targetMargin: 120,
    });
    showToast(`📈 [${record.plate} ${record.carName}] 사이드바 필터 및 실시간 역추적 시세 연동 완료!`);
    setActiveTab('cockpit');
  };

  const handleResetToInitial = () => {
    if (confirm('저장된 원장과 정산 데이터를 초기 상태로 리셋하시겠습니까?')) {
      setCars(INITIAL_CAR_LEDGER);
      setSettlementItems(INITIAL_SETTLEMENT_ITEMS);
      localStorage.removeItem('jpro_ledger_v3');
      localStorage.removeItem('jpro_settlement_v3');
    }
  };

  const handleUpdateCookie = async (newCookie: string): Promise<boolean> => {
    try {
      localStorage.setItem('jpro_session_cookie', newCookie);

      // 서버 백엔드 금고에도 동시에 영구 보관
      await fetch('/api/session/cookie', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cookie: newCookie,
          secretToken: 'jpro_sec_9981_live_auth'
        })
      });

      setCookieStatus('active');
      showToast('🟢 헤이딜러 세션 쿠키가 클라우드 금고에 동기화되었습니다!');
      return true;
    } catch {
      return false;
    }
  };

  // 클립보드에 복사된 쿠키 원클릭 자동 연동 핸들러
  const handlePasteClipboardCookie = async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.readText) {
        const text = await navigator.clipboard.readText();
        if (text && text.trim().length > 10) {
          const ok = await handleUpdateCookie(text.trim());
          if (ok) {
            showToast('🟢 클립보드에서 복사된 헤이딜러 세션 쿠키가 즉시 적용되었습니다!');
            return;
          }
        }
      }
    } catch (e) {
      console.warn('Clipboard read permission skipped, opening modal:', e);
    }
    // 클립보드 접근이 차단된 경우 모달 오픈
    setIsCookieModalOpen(true);
  };

  // 전역 Ctrl+V (붙여넣기) 단축키로 쿠키 자동 감지 및 적용
  useEffect(() => {
    const handleGlobalPaste = async (e: ClipboardEvent) => {
      const activeEl = document.activeElement as HTMLElement;
      if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA')) {
        return;
      }
      const text = e.clipboardData?.getData('text') || '';
      if (
        text &&
        (text.includes('sessionid=') ||
          text.includes('JSESSIONID=') ||
          text.includes('csrftoken=') ||
          text.includes('remember-me='))
      ) {
        e.preventDefault();
        const ok = await handleUpdateCookie(text.trim());
        if (ok) {
          showToast('🟢 [Ctrl+V] 클립보드에 복사된 헤이딜러 세션 쿠키가 즉시 연동되었습니다!');
        }
      }
    };
    window.addEventListener('paste', handleGlobalPaste);
    return () => window.removeEventListener('paste', handleGlobalPaste);
  }, []);

  return (
    <div className="min-h-screen bg-[#08080a] text-[#e2e3e9] flex flex-col font-sans-ui pb-20 md:pb-10 selection:bg-[#cc9166]/30 selection:text-white">
      
      {/* Top Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        totalCarsCount={totalCarsCount}
        totalBuyAmount={totalBuyAmount}
        avgMargin={avgMargin}
        onOpenAddModal={() => setIsAddModalOpen(true)}
        onOpenDriveModal={() => setIsDriveModalOpen(true)}
        onOpenCookieModal={() => setIsCookieModalOpen(true)}
        onPasteClipboardCookie={handlePasteClipboardCookie}
        cookieStatus={cookieStatus}
        isPrivateUnlocked={isPrivateUnlocked}
        setIsPrivateUnlocked={setIsPrivateUnlocked}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-[1550px] w-full mx-auto px-3 sm:px-5 lg:px-6 py-5">
        
        {/* Tab 1: 📊 시세 분석 및 스캔 (Bidding Cockpit) */}
        {activeTab === 'cockpit' && (
          <BiddingCockpitTab
            onSaveToLedger={handleAddCar}
            preset={cockpitPreset}
            presetCarName={cockpitPreset?.carName}
            presetSellPrice={cockpitPreset?.sellPrice}
          />
        )}

        {/* Tab 2: 📋 매입 장부 관리 (125대 라이프사이클) */}
        {activeTab === 'ledger' && (
          <LedgerTab
            cars={cars}
            searchQuery={searchQuery}
            onSelectCar={(car) => setSelectedCar(car)}
            onUpdateStatus={handleUpdateStatus}
            onConfirmPurchase={handleConfirmPurchase}
            onAnalyzeInCockpit={handleAnalyzeInCockpit}
          />
        )}

        {/* Tab 3: 💰 재고 및 정산 관리 (현재 보유 차량 손익 정산) */}
        {activeTab === 'settlement' && (
          <SettlementTab
            settlementList={settlementItems}
            onMarkSold={handleMarkSold}
            onAnalyzeInCockpit={handleAnalyzeSettlementInCockpit}
          />
        )}

        {/* Tab 4: 🎉 판매완료 정산 내역 (완판 차량 최종 확정 손익) */}
        {activeTab === 'soldout' && (
          <SoldOutSettlementTab
            completedList={settlementItems}
          />
        )}

        {/* Tab 5: 📈 자사 판매 실적 (회사 7,493건 완판 실적 참고 DB) */}
        {activeTab === 'performance' && (
          <CompanyPerformanceTab
            onAnalyzeInCockpit={handleAnalyzePerformanceInCockpit}
          />
        )}

        {/* Tab 6: 📦 자사 보유 재고 (회사 1,266건 보유재고 참고 DB) */}
        {activeTab === 'inventory' && (
          <CompanyInventoryTab />
        )}
      </main>

      {/* Footer Info */}
      <footer className="border-t border-[#1c1d22] py-6 px-4 text-center text-xs text-[#5e616e]">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-serif-display font-bold text-white tracking-wider">J-PRO</span>
            <span>•</span>
            <span className="text-emerald-400 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              보안 클린 아키텍처
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsDriveModalOpen(true)}
              className="hover:text-blue-400 transition flex items-center gap-1"
            >
              <Cloud className="w-3.5 h-3.5" />
              <span>Google Drive</span>
            </button>
            <span>•</span>
            <button
              onClick={handleResetToInitial}
              className="hover:text-white transition flex items-center gap-1"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>원장 초기화</span>
            </button>
          </div>
        </div>
      </footer>

      {/* Modals */}
      <CarDetailModal
        car={selectedCar}
        onClose={() => setSelectedCar(null)}
        onUpdate={handleUpdateCar}
        onDelete={handleDeleteCar}
      />

      <AddCarModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAdd={handleAddCar}
      />

      <DriveModal
        isOpen={isDriveModalOpen}
        onClose={() => setIsDriveModalOpen(false)}
        cars={cars}
        settlementItems={settlementItems}
        onRestoreLedger={(restoredCars, restoredSettlement) => {
          setCars(restoredCars);
          if (restoredSettlement && restoredSettlement.length > 0) {
            setSettlementItems(restoredSettlement);
          }
        }}
      />

      <CookieSyncModal
        isOpen={isCookieModalOpen}
        onClose={() => setIsCookieModalOpen(false)}
        cookieStatus={cookieStatus}
        onUpdateCookie={handleUpdateCookie}
      />

      {/* Mobile Bottom Navigation Bar */}
      <MobileNav
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      {/* Floating Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-20 md:bottom-8 right-6 z-50 animate-bounce duration-300">
          <div className="bg-emerald-950/95 border border-emerald-500/80 text-emerald-200 px-4 py-3 rounded-xl shadow-2xl flex items-center gap-2.5 backdrop-blur-md">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <span className="text-sm font-semibold">{toastMessage}</span>
          </div>
        </div>
      )}

    </div>
  );
}
