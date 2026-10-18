import React, { useState, useMemo, useEffect } from 'react';
import { InventorySettlementItem } from '@/types';
import {
  Check,
  Edit2,
  X,
  Save,
  RefreshCw
} from 'lucide-react';

interface SettlementTabProps {
  settlementList: InventorySettlementItem[];
  onMarkSold?: (id: string, sellPrice?: number) => void;
  onAnalyzeInCockpit?: (item: InventorySettlementItem) => void;
  onUpdateItem?: (updatedItem: InventorySettlementItem) => void;
  onRefresh?: () => Promise<void> | void;
}

interface InlineEditForm {
  buyDate: string;
  buyPrice: number;
  sellPrice: number;
  outerRepairs: number;
  repairCost: number;
  heydealerFee: number;
  baseExpenses: number;
  salesCommission: number;
  feeRate: number;
}

export const SettlementTab: React.FC<SettlementTabProps> = ({
  settlementList,
  onMarkSold,
  onAnalyzeInCockpit,
  onUpdateItem,
  onRefresh,
}) => {
  // 자사 차량 carid 매핑 맵
  const [companyCarIdMap, setCompanyCarIdMap] = useState<Record<string, string>>({});

  useEffect(() => {
    fetch('/api/autoplus/company_carids')
      .then(r => r.json())
      .then(data => {
        if (data && typeof data === 'object') {
          setCompanyCarIdMap(data);
        }
      })
      .catch(() => {});
  }, []);

  const getEncarDetailLink = (carNo: string, encarUrl?: string): string | null => {
    if (encarUrl) {
      const m = encarUrl.match(/carid=(\d+)/) || encarUrl.match(/\/cars\/detail\/(\d+)/);
      if (m) return `https://fem.encar.com/cars/detail/${m[1]}`;
      if (encarUrl.startsWith('http')) return encarUrl;
    }
    const cleanNo = (carNo || '').replace(/\s+/g, '');
    const matchedId = companyCarIdMap[cleanNo];
    if (matchedId) {
      return `https://fem.encar.com/cars/detail/${matchedId}`;
    }
    return null;
  };

  // tab_settlement.py states
  const [filterMode, setFilterMode] = useState<'all' | '30plus' | '60plus' | 'margin_risk'>('all');
  const [selectedStockCarNum, setSelectedStockCarNum] = useState<string>('');

  // 매입연동 상태
  const [syncLoading, setSyncLoading] = useState(false);

  // 인라인 편집 상태
  const [editingCarNumber, setEditingCarNumber] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<InlineEditForm>({
    buyDate: '',
    buyPrice: 0,
    sellPrice: 0,
    outerRepairs: 0,
    repairCost: 0,
    heydealerFee: 0,
    baseExpenses: 15,
    salesCommission: 0,
    feeRate: 0.1,
  });

  // 1. 구간별 기본 수수료율 함수 (2026년 4분기 공문 기준: 이익/손실 차등)
  const getAutoFeeRate = (volume: number, isLoss = false): number => {
    if (volume <= 12) return isLoss ? 0.30 : 0.10;
    if (volume <= 16) return isLoss ? 0.30 : 0.20;
    if (volume <= 19) return 0.30;
    if (volume <= 31) return 0.40;
    return 0.50;
  };

  // 현재 월 (기본값: 오늘 날짜 기준 월, 예: 10월)
  const currentMonth = useMemo(() => new Date().getMonth() + 1, []);

  // 당월(해당 월) 매입 대수 계산 (전체 누적이 아닌 당월 매입 기준)
  const monthlyBoughtCount = useMemo(() => {
    return settlementList.filter(item => {
      const bDate = (item.buyDate || '').trim();
      // '10. 15', '10.08', '2026-10-13', '10/01' 등에서 월(Month) 추출
      const m = bDate.match(/(?:20\d{2}[-/.])?0?(\d{1,2})[-/.]/);
      if (m) {
        return parseInt(m[1], 10) === currentMonth;
      }
      return false;
    }).length;
  }, [settlementList, currentMonth]);

  // 당월 매입대수 기준으로 수수료율 자동 산정
  const autoFeeRate = getAutoFeeRate(monthlyBoughtCount);

  // 2. 보유 재고 vs 완료 재고 분리 (tab_settlement.py L103-L108)
  const stockItems = useMemo(() => {
    return settlementList.filter(item => item.status !== '판매완료');
  }, [settlementList]);

  const soldItems = useMemo(() => {
    return settlementList.filter(item => item.status === '판매완료');
  }, [settlementList]);

  // 3. settlement_service.py recalc_settlement_df 공식 100% 1:1 완벽 계산
  const calculatedStockItems = useMemo(() => {
    return stockItems.map((item, idx) => {
      const order = item.order > 0 ? item.order : (idx + 1);
      const pSell = item.sellPrice || 0;
      const pBuy = item.buyPrice || 0;
      const extCnt = item.outerRepairs || 0;

      // 기본제경비 = 15만원 고정 (settlement_service.py L24-L25)
      const baseExpenses = item.baseExpenses > 0 ? item.baseExpenses : 15;

      // 외판수 > 0이고 상품화가 0이면 외판수 * 13만원 (L27-L29)
      const repairCost = (item.repairCost > 0) ? item.repairCost : (extCnt > 0 ? extCnt * 13 : 0);

      // 판매수수료: 판매가의 0.7% (L31-L36)
      const calcFee = pSell > 0 ? Math.round(pSell * 0.007) : 0;
      const salesCommission = (item.salesCommission && item.salesCommission > 0) ? item.salesCommission : calcFee;

      // 수수료율: 사용자 직접 지정 수수료율_수동 우선, 없으면 feeRate, 없으면 구간별 autoFeeRate (L38-L45)
      const effectiveFeeRate = (item.feeRateManual && item.feeRateManual > 0)
        ? item.feeRateManual
        : ((item.feeRate && item.feeRate > 0) ? item.feeRate : autoFeeRate);

      // 공헌손익 및 실수익 계산 (L47-L56)
      let contributionMargin = 0;
      let netProfit = 0;
      let finalFeeRate = effectiveFeeRate;

      if (pSell > 0) {
        const vatMargin = (pSell - pBuy) / 1.1;
        const totalExpenses = (item.heydealerFee || 0) + repairCost + baseExpenses + salesCommission;
        contributionMargin = Math.round(vatMargin - totalExpenses);

        // 손실 발생 시 손실 요율 자동 적용 (사용자 수동 입력값이 없는 경우)
        if (contributionMargin < 0 && (!item.feeRateManual || item.feeRateManual <= 0)) {
          finalFeeRate = getAutoFeeRate(monthlyBoughtCount, true);
        }
        netProfit = Math.round(contributionMargin * finalFeeRate);
      }

      return {
        ...item,
        order,
        baseExpenses,
        repairCost,
        salesCommission,
        feeRate: finalFeeRate,
        contributionMargin,
        netProfit,
      };
    });
  }, [stockItems, autoFeeRate, monthlyBoughtCount]);

  // 4. 상단 핵심 현황 대시보드 지표 (tab_settlement.py L107-L127)
  const stockCount = calculatedStockItems.length;
  const soldCount = soldItems.length;

  const totalStockCost = useMemo(() => {
    return calculatedStockItems.reduce((acc, curr) => {
      return acc + (curr.buyPrice + curr.repairCost + (curr.heydealerFee || 0) + curr.baseExpenses);
    }, 0);
  }, [calculatedStockItems]);

  const avgStockDays = useMemo(() => {
    if (calculatedStockItems.length === 0) return 0;
    const sumDays = calculatedStockItems.reduce((acc, curr) => acc + (curr.stockDays || 0), 0);
    return Math.round(sumDays / calculatedStockItems.length);
  }, [calculatedStockItems]);

  const over30Count = useMemo(() => {
    return calculatedStockItems.filter(s => s.stockDays >= 30 && s.stockDays < 60).length;
  }, [calculatedStockItems]);

  const over60Count = useMemo(() => {
    return calculatedStockItems.filter(s => s.stockDays >= 60).length;
  }, [calculatedStockItems]);

  const marginRiskCount = useMemo(() => {
    return calculatedStockItems.filter(s => s.sellPrice > 0 && s.contributionMargin < 100).length;
  }, [calculatedStockItems]);

  // 5. 필터 적용 (tab_settlement.py L590-L601)
  const filteredViewItems = useMemo(() => {
    switch (filterMode) {
      case '30plus':
        return calculatedStockItems.filter(s => s.stockDays >= 30 && s.stockDays < 60);
      case '60plus':
        return calculatedStockItems.filter(s => s.stockDays >= 60);
      case 'margin_risk':
        return calculatedStockItems.filter(s => s.sellPrice > 0 && s.contributionMargin < 100);
      default:
        return calculatedStockItems;
    }
  }, [calculatedStockItems, filterMode]);

  // Selected car for live cockpit analysis
  const currentSelectedStock = useMemo(() => {
    return calculatedStockItems.find(i => i.carNumber === selectedStockCarNum) || calculatedStockItems[0];
  }, [calculatedStockItems, selectedStockCarNum]);

  // 인라인 편집 핸들러
  const handleStartEdit = (item: typeof calculatedStockItems[0]) => {
    setEditingCarNumber(item.carNumber);
    setEditForm({
      buyDate: item.buyDate || '',
      buyPrice: item.buyPrice || 0,
      sellPrice: item.sellPrice || 0,
      outerRepairs: item.outerRepairs || 0,
      repairCost: item.repairCost || 0,
      heydealerFee: item.heydealerFee || 0,
      baseExpenses: item.baseExpenses || 15,
      salesCommission: item.salesCommission || 0,
      feeRate: item.feeRate || autoFeeRate,
    });
  };

  const handleCancelEdit = () => {
    setEditingCarNumber(null);
  };

  const handleFormChange = (field: keyof InlineEditForm, value: any) => {
    setEditForm(prev => {
      const updated = { ...prev, [field]: value };
      if (field === 'outerRepairs') {
        const panels = Number(value) || 0;
        if (prev.repairCost === 0 || prev.repairCost === prev.outerRepairs * 13) {
          updated.repairCost = panels * 13;
        }
      }
      if (field === 'sellPrice') {
        const sPrice = Number(value) || 0;
        const prevExpectedFee = prev.sellPrice > 0 ? Math.round(prev.sellPrice * 0.007) : 0;
        if (prev.salesCommission === 0 || prev.salesCommission === prevExpectedFee) {
          updated.salesCommission = sPrice > 0 ? Math.round(sPrice * 0.007) : 0;
        }
      }
      return updated;
    });
  };

  const handleSaveEdit = (originalItem: typeof calculatedStockItems[0]) => {
    if (!onUpdateItem) return;

    const pSell = Number(editForm.sellPrice) || 0;
    const pBuy = Number(editForm.buyPrice) || 0;
    const extCnt = Number(editForm.outerRepairs) || 0;
    const repCost = Number(editForm.repairCost) || 0;
    const heyFee = Number(editForm.heydealerFee) || 0;
    const baseExp = Number(editForm.baseExpenses) || 15;
    const salesComm = Number(editForm.salesCommission) || (pSell > 0 ? Math.round(pSell * 0.007) : 0);
    const fRate = Number(editForm.feeRate) || autoFeeRate;

    const totalExp = heyFee + repCost + baseExp + salesComm;
    const vatMargin = pSell > 0 ? (pSell - pBuy) / 1.1 : 0;
    const contrib = pSell > 0 ? Math.round(vatMargin - totalExp) : 0;
    const net = pSell > 0 ? Math.round(contrib * fRate) : 0;

    const updated: InventorySettlementItem = {
      ...originalItem,
      buyDate: editForm.buyDate.trim(),
      buyPrice: pBuy,
      sellPrice: pSell,
      outerRepairs: extCnt,
      repairCost: repCost,
      heydealerFee: heyFee,
      baseExpenses: baseExp,
      salesCommission: salesComm,
      feeRate: fRate,
      feeRateManual: fRate,
      contributionMargin: contrib,
      netProfit: net,
      finalProfit: net,
    };

    onUpdateItem(updated);
    setEditingCarNumber(null);
  };

  // 편집 중인 행의 실시간 계산 미리보기
  const liveEditCalc = useMemo(() => {
    const pSell = Number(editForm.sellPrice) || 0;
    const pBuy = Number(editForm.buyPrice) || 0;
    const repCost = Number(editForm.repairCost) || 0;
    const heyFee = Number(editForm.heydealerFee) || 0;
    const baseExp = Number(editForm.baseExpenses) || 15;
    const salesComm = Number(editForm.salesCommission) || 0;
    const fRate = Number(editForm.feeRate) || 0.1;

    if (pSell <= 0) return { contrib: 0, net: 0 };
    const vatMargin = (pSell - pBuy) / 1.1;
    const totalExp = heyFee + repCost + baseExp + salesComm;
    const contrib = Math.round(vatMargin - totalExp);
    const net = Math.round(contrib * fRate);
    return { contrib, net };
  }, [editForm]);

  // high A+ 모바일 API 직접 호출 및 화면 새로고침 핸들러
  const handleCheckSyncStatus = async () => {
    setSyncLoading(true);
    try {
      // 1. 모바일 API 백엔드 직접 호출 (/api/settlement/sync_highplus_buy)
      const res = await fetch('/api/settlement/sync_highplus_buy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });

      let syncData: any = {};
      if (res.ok) {
        syncData = await res.json();
      } else {
        const errText = await res.text().catch(() => '');
        throw new Error(`서버 응답 오류 (HTTP ${res.status}): ${errText}`);
      }

      // 2. 화면 데이터 즉시 새로고침 (/api/settlement 재조회)
      if (onRefresh) {
        await onRefresh();
      }

      const st = (syncData && syncData.data) || {};
      const timeStr = st.last_sync_time || new Date().toLocaleTimeString('ko-KR');
      const total = st.total_synced_cars || 0;
      const added = st.new_inventory_added || 0;
      const updated = st.inventory_updated || 0;

      if (syncData.success !== false) {
        alert(
          `[high A+ 매입 모바일 API 연동 결과]\n\n` +
          `• 연동 시간: ${timeStr}\n` +
          `• 감지된 매입차량: ${total}대\n` +
          `• 신규 재고 등록: ${added}대\n` +
          `• 기존 재고 갱신: ${updated}대\n\n` +
          `✅ 모바일 API를 통해 실시간 매입 데이터(매입가, 수수료 등)가 장부 및 재고로 정상 연동되었습니다.`
        );
      } else {
        alert(
          `[high A+ 매입 연동 알림]\n\n` +
          `• 상태: ${syncData.message || '세션 만료 또는 데이터 없음'}\n` +
          `• 이전 성공 시점: ${st.last_sync_time || '없음'}\n\n` +
          `💡 high_cookie.txt 쿠키를 확인하거나, high.autoplus.co.kr 로그인 상태를 점검해 주세요.`
        );
      }
    } catch (e: any) {
      alert(`매입연동 오류: ${e.message}`);
    } finally {
      setSyncLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* 1. Header & Title */}
      <div className="border-b border-[#1f2433] pb-3">
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <span>💰 실전 재고 및 정산 관리 (현재 보유 차량)</span>
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          📋 매입 확정 후 현재 보유 중인 재고 차량의 원가와 손익을 관리합니다. 판매가 완료되면 표 맨 끝의 **[판매완료]**를 클릭하여 이동하세요.
        </p>
      </div>

      {/* 2. Top Metric KPI Dashboard (tab_settlement.py L131-L179) */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {/* 보유 재고 */}
        <div className="bg-[#12151e] border border-[#232733] rounded-xl p-3 flex items-center gap-3 shadow-sm">
          <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-base">
            🚗
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">보유 재고</div>
            <div className="text-base font-bold text-sky-400">
              {stockCount}대 <span className="text-[11px] font-normal text-slate-500">(완료: {soldCount})</span>
            </div>
          </div>
        </div>

        {/* 평균 재고일 */}
        <div className="bg-[#12151e] border border-[#232733] rounded-xl p-3 flex items-center gap-3 shadow-sm">
          <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-base">
            ⏱️
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">평균 재고일</div>
            <div className={`text-base font-bold ${avgStockDays < 15 ? 'text-emerald-400' : 'text-amber-400'}`}>
              {avgStockDays}일
            </div>
          </div>
        </div>

        {/* 장기 재고 (30일+/60일+) */}
        <div className={`bg-[#12151e] rounded-xl p-3 flex items-center gap-3 shadow-sm border ${over60Count > 0 ? 'border-rose-500' : over30Count > 0 ? 'border-amber-500' : 'border-[#232733]'
          }`}>
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center text-base ${over60Count > 0 ? 'bg-rose-500/20 text-rose-400' : over30Count > 0 ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-800'
            }`}>
            ⚠️
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">장기 재고 (30+/60+)</div>
            <div className="text-base font-bold">
              <span className={over60Count > 0 ? 'text-rose-400 font-extrabold' : 'text-slate-400'}>{over60Count}대</span>
              <span className="text-xs text-amber-400 ml-1">(30일+: {over30Count}대)</span>
            </div>
          </div>
        </div>

        {/* 마진 주의 (100만↓) */}
        <div className={`bg-[#12151e] rounded-xl p-3 flex items-center gap-3 shadow-sm border ${marginRiskCount > 0 ? 'border-rose-500' : 'border-[#232733]'
          }`}>
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center text-base ${marginRiskCount > 0 ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/10 text-emerald-400'
            }`}>
            📉
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">마진 주의 (100만↓)</div>
            <div className={`text-base font-bold ${marginRiskCount > 0 ? 'text-rose-400 font-extrabold' : 'text-emerald-400'}`}>
              {marginRiskCount}대
            </div>
          </div>
        </div>

        {/* 재고 총 원가 */}
        <div className="bg-[#12151e] border border-[#232733] rounded-xl p-3 flex items-center gap-3 shadow-sm">
          <div className="w-9 h-9 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-base">
            💵
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">재고 총 원가</div>
            <div className="text-base font-bold text-slate-100">
              {totalStockCost.toLocaleString()}만원
            </div>
          </div>
        </div>

        {/* 당월 매입 대수 (인센티브) */}
        <div className="bg-[#12151e] border border-sky-600 rounded-xl p-3 flex items-center gap-3 shadow-sm">
          <div className="w-9 h-9 rounded-lg bg-sky-950 border border-sky-700 flex items-center justify-center text-base">
            📦
          </div>
          <div>
            <div className="text-[11px] text-sky-400 font-medium">당월 매입 대수 ({currentMonth}월)</div>
            <div className="text-base font-bold text-sky-400">
              {monthlyBoughtCount}대 <span className="text-xs text-slate-400">({Math.round(autoFeeRate * 100)}%)</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2-1. 2026년 4분기 매입사원 수수료 및 인센티브 운영 기준 안내 */}
      <div className="bg-[#151728] border border-indigo-500/30 rounded-xl p-3 shadow-md flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold border border-indigo-500/40 text-[11px]">
              📢 2026년 4분기 매입사원 수수료 기준
            </span>
            <span className="text-slate-400 text-[11px]">시행기간: 2026.10.01 ~ 2026.12.31</span>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-slate-300 text-[11px]">
            <span>• ~12대: <b className="text-emerald-400">이익 10%</b> / <b className="text-rose-400">손실 30%</b></span>
            <span>• 13~16대: <b className="text-emerald-400">이익 20%</b> / <b className="text-rose-400">손실 30%</b></span>
            <span>• 17~19대: <b>30%</b></span>
            <span>• 20~31대: <b>40%</b></span>
            <span>• 32대 이상: <b>50%</b></span>
          </div>
        </div>
        <div className="flex items-center gap-2 text-[11px]">
          <div className="px-2.5 py-1 rounded-lg bg-emerald-950/60 border border-emerald-700/50 text-emerald-300">
            🛡️ <b>손실 누적 차감 기준:</b> 수수료 <b>200만 원 이하 전액 지급</b>(손실 미차감), 200만 원 초과분 50% 차감 후 지급
          </div>
        </div>
      </div>

      {/* 3. Live Encar Market Comparison Bar (tab_settlement.py L181-L260) */}
      <div className="bg-[#12151e] border border-sky-600/60 rounded-xl p-3.5 shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-sky-400">🎯 보유 재고 실시간 동급 시세 분석 (메인 화면 원클릭 연동)</span>
          </div>
          <span className="text-[11px] text-slate-400">
            💡 보유 차량을 선택하면 메인 콕핏으로 즉시 동급 매물을 스캔하여 이관합니다.
          </span>
        </div>

        <div className="flex flex-col sm:flex-row gap-2 items-center">
          <select
            value={selectedStockCarNum || currentSelectedStock?.carNumber || ''}
            onChange={(e) => setSelectedStockCarNum(e.target.value)}
            className="flex-1 bg-[#0a0b0e] border border-[#2b2f42] rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-sky-500 font-semibold"
          >
            {calculatedStockItems.map((item) => (
              <option key={item.id} value={item.carNumber}>
                {item.carNumber} | {item.carName} (매입 {item.buyPrice}만 / 판매 {item.sellPrice}만 / {item.stockDays}일차)
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => {
              if (currentSelectedStock && onAnalyzeInCockpit) {
                onAnalyzeInCockpit(currentSelectedStock);
              }
            }}
            className="px-4 py-2 bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-white rounded-lg text-xs font-bold transition shadow-md flex items-center gap-1.5 shrink-0"
          >
            <span>🚀 메인 화면에서 동급 시세 분석</span>
          </button>
        </div>
      </div>

      {/* 4. Filter Toolbar (tab_settlement.py L505-L523) */}
      <div className="bg-[#0f1117] border border-[#232733] p-3 rounded-xl flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col sm:flex-row sm:items-center gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-200">📝 현재 보유 재고 정산표</span>
            <span className="text-xs text-slate-500">({calculatedStockItems.length}대)</span>
          </div>
          <span className="text-[11px] text-sky-400 bg-sky-950/40 border border-sky-800/40 px-2 py-0.5 rounded">
            💡 행을 <b>더블클릭</b>하거나 <b>[수정]</b> 버튼을 누르면 매입일·매입가·판매가·수수료 등을 즉시 수정할 수 있습니다.
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* high A+ 매입연동 버튼 */}
          <button
            type="button"
            onClick={handleCheckSyncStatus}
            disabled={syncLoading}
            className="px-2.5 py-1.5 rounded-lg bg-emerald-950/40 hover:bg-emerald-900/60 border border-emerald-600/50 text-emerald-300 font-bold text-xs flex items-center gap-1.5 transition shadow-sm"
            title="high A+ 매입 전산 자동 연동 현황 확인"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncLoading ? 'animate-spin' : ''}`} />
            <span>매입연동</span>
          </button>

          {/* Filter Radio Buttons */}
          <div className="flex flex-wrap items-center gap-1.5 bg-[#181b24] p-1 rounded-lg border border-[#282c3c] text-xs">
          <button
            type="button"
            onClick={() => setFilterMode('all')}
            className={`px-2.5 py-1 rounded transition font-medium ${filterMode === 'all'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
              }`}
          >
            전체 ({stockCount})
          </button>
          <button
            type="button"
            onClick={() => setFilterMode('30plus')}
            className={`px-2.5 py-1 rounded transition font-medium ${filterMode === '30plus'
                ? 'bg-amber-600 text-white shadow-sm'
                : 'text-amber-400 hover:text-amber-300'
              }`}
          >
            ⚠️ 30일+ ({over30Count})
          </button>
          <button
            type="button"
            onClick={() => setFilterMode('60plus')}
            className={`px-2.5 py-1 rounded transition font-medium ${filterMode === '60plus'
                ? 'bg-rose-600 text-white shadow-sm'
                : 'text-rose-400 hover:text-rose-300'
              }`}
          >
            🚨 60일+ ({over60Count})
          </button>
          <button
            type="button"
            onClick={() => setFilterMode('margin_risk')}
            className={`px-2.5 py-1 rounded transition font-medium ${filterMode === 'margin_risk'
                ? 'bg-rose-700 text-white shadow-sm'
                : 'text-rose-400 hover:text-rose-300'
              }`}
          >
            📉 마진주의 ({marginRiskCount})
          </button>
        </div>
      </div>
    </div>

      {/* 5. Main Inventory Settlement Table (tab_settlement.py L524-L633) */}
      <div className="bg-[#0f1117] border border-[#232733] rounded-xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-[#e2e3e9]">
            <thead className="bg-[#181b24] text-slate-400 border-b border-[#282c3c] font-bold">
              <tr>
                <th className="py-2.5 px-2 text-center w-10">순차</th>
                <th className="py-2.5 px-2.5 whitespace-nowrap">매입일</th>
                <th className="py-2.5 px-2.5 whitespace-nowrap">차량번호</th>
                <th className="py-2.5 px-3">차종</th>
                <th className="py-2.5 px-2 text-center whitespace-nowrap">재고일</th>
                <th className="py-2.5 px-2.5 text-right whitespace-nowrap">매입가</th>
                <th className="py-2.5 px-2.5 text-right whitespace-nowrap">판매가</th>
                <th className="py-2.5 px-2 text-center whitespace-nowrap">외판</th>
                <th className="py-2.5 px-2 text-right whitespace-nowrap">상품화</th>
                <th className="py-2.5 px-2 text-right whitespace-nowrap">헤딜수수료</th>
                <th className="py-2.5 px-2 text-right whitespace-nowrap">제경비</th>
                <th className="py-2.5 px-2 text-right whitespace-nowrap">판매수수료</th>
                <th className="py-2.5 px-2.5 text-right whitespace-nowrap text-sky-400">공헌이익</th>
                <th className="py-2.5 px-2.5 text-right whitespace-nowrap text-amber-400">실수익</th>
                <th className="py-2.5 px-2 text-center whitespace-nowrap">수수료율</th>
                <th className="py-2.5 px-3 text-center whitespace-nowrap">작업 / 판매완료</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1a1d27]">
              {filteredViewItems.map((item) => {
                const isOver30 = item.stockDays >= 30 && item.stockDays < 60;
                const isOver60 = item.stockDays >= 60;
                const isRisk = item.sellPrice > 0 && item.contributionMargin < 100;
                const isEditing = item.carNumber === editingCarNumber;

                // [인라인 편집 모드 렌더링]
                if (isEditing) {
                  return (
                    <tr
                      key={item.id}
                      className="bg-sky-950/30 border-y-2 border-sky-500/60 shadow-inner"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveEdit(item);
                        if (e.key === 'Escape') handleCancelEdit();
                      }}
                    >
                      <td className="py-2.5 px-2 text-center text-sky-400 font-mono font-bold">
                        {item.order}
                      </td>
                      <td className="py-2 px-1 whitespace-nowrap">
                        <input
                          type="text"
                          value={editForm.buyDate}
                          onChange={(e) => handleFormChange('buyDate', e.target.value)}
                          placeholder="MM. DD"
                          className="w-16 bg-[#0a0c14] border border-sky-500 rounded px-1.5 py-1 text-center text-slate-100 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-sky-400"
                          title="매입일자 (예: 10. 01)"
                        />
                      </td>
                      <td className="py-2.5 px-2.5 font-bold text-sky-300 whitespace-nowrap">
                        {item.carNumber}
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-slate-200 max-w-xs truncate" title={item.carName}>
                        {(() => {
                          const link = getEncarDetailLink(item.carNumber, item.encarUrl);
                          if (link) {
                            return (
                              <a
                                href={link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sky-400 hover:text-sky-300 hover:underline font-bold"
                                title={`엔카 매물 상세페이지 새창 열기 (${item.carName})`}
                              >
                                {item.carName}
                              </a>
                            );
                          }
                          return item.carName;
                        })()}
                      </td>
                      <td className="py-2.5 px-2 text-center whitespace-nowrap">
                        <span className="text-[11px] font-bold text-slate-400 font-mono">
                          {item.stockDays}일
                        </span>
                      </td>
                      <td className="py-2 px-1 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-0.5">
                          <input
                            type="number"
                            step="any"
                            value={editForm.buyPrice || ''}
                            onChange={(e) => handleFormChange('buyPrice', parseFloat(e.target.value) || 0)}
                            className="w-20 bg-[#0a0c14] border border-sky-500 rounded px-1.5 py-1 text-right text-white font-mono font-bold text-xs focus:outline-none focus:ring-1 focus:ring-sky-400"
                            placeholder="매입가"
                          />
                          <span className="text-slate-400 text-[11px]">만</span>
                        </div>
                      </td>
                      <td className="py-2 px-1 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-0.5">
                          <input
                            type="number"
                            step="any"
                            value={editForm.sellPrice || ''}
                            onChange={(e) => handleFormChange('sellPrice', parseFloat(e.target.value) || 0)}
                            className="w-20 bg-[#0a0c14] border border-sky-500 rounded px-1.5 py-1 text-right text-sky-400 font-bold font-mono text-xs focus:outline-none focus:ring-1 focus:ring-sky-400"
                            placeholder="판매가"
                          />
                          <span className="text-sky-400 text-[11px]">만</span>
                        </div>
                      </td>
                      <td className="py-2 px-1 text-center whitespace-nowrap">
                        <div className="flex items-center justify-center gap-0.5">
                          <input
                            type="number"
                            min="0"
                            value={editForm.outerRepairs}
                            onChange={(e) => handleFormChange('outerRepairs', parseInt(e.target.value) || 0)}
                            className="w-12 bg-[#0a0c14] border border-amber-500/80 rounded px-1 py-1 text-center text-amber-400 font-bold font-mono text-xs focus:outline-none focus:ring-1 focus:ring-amber-400"
                            title="외판 판수"
                          />
                          <span className="text-amber-400 text-[11px]">판</span>
                        </div>
                      </td>
                      <td className="py-2 px-1 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-0.5">
                          <input
                            type="number"
                            step="any"
                            value={editForm.repairCost || ''}
                            onChange={(e) => handleFormChange('repairCost', parseFloat(e.target.value) || 0)}
                            className="w-16 bg-[#0a0c14] border border-slate-600 rounded px-1.5 py-1 text-right text-slate-200 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-sky-400"
                            placeholder="상품화"
                          />
                          <span className="text-slate-400 text-[11px]">만</span>
                        </div>
                      </td>
                      <td className="py-2 px-1 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-0.5">
                          <input
                            type="number"
                            step="any"
                            value={editForm.heydealerFee || ''}
                            onChange={(e) => handleFormChange('heydealerFee', parseFloat(e.target.value) || 0)}
                            className="w-20 bg-[#0a0c14] border border-emerald-500 rounded px-1.5 py-1 text-right text-emerald-400 font-bold font-mono text-xs focus:outline-none focus:ring-1 focus:ring-emerald-400"
                            title="헤이딜러 수수료 + 영업사원 소개수수료 합산 금액 (예: 54.5 또는 55)"
                            placeholder="수수료"
                          />
                          <span className="text-emerald-400 text-[11px]">만</span>
                        </div>
                      </td>
                      <td className="py-2 px-1 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-0.5">
                          <input
                            type="number"
                            step="any"
                            value={editForm.baseExpenses || ''}
                            onChange={(e) => handleFormChange('baseExpenses', parseFloat(e.target.value) || 0)}
                            className="w-14 bg-[#0a0c14] border border-slate-600 rounded px-1.5 py-1 text-right text-slate-300 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-sky-400"
                            placeholder="15"
                          />
                          <span className="text-slate-400 text-[11px]">만</span>
                        </div>
                      </td>
                      <td className="py-2 px-1 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-0.5">
                          <input
                            type="number"
                            step="any"
                            value={editForm.salesCommission || ''}
                            onChange={(e) => handleFormChange('salesCommission', parseFloat(e.target.value) || 0)}
                            className="w-14 bg-[#0a0c14] border border-slate-600 rounded px-1.5 py-1 text-right text-slate-300 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-sky-400"
                            placeholder="0.7%"
                          />
                          <span className="text-slate-400 text-[11px]">만</span>
                        </div>
                      </td>
                      <td className="py-2.5 px-2.5 text-right font-bold whitespace-nowrap">
                        <span className={`text-xs ${liveEditCalc.contrib >= 100 ? 'text-sky-400' : liveEditCalc.contrib > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {editForm.sellPrice > 0 ? `${liveEditCalc.contrib > 0 ? '+' : ''}${liveEditCalc.contrib.toLocaleString()}만` : '0만'}
                        </span>
                      </td>
                      <td className="py-2.5 px-2.5 text-right font-bold text-amber-400 whitespace-nowrap">
                        <span className="text-xs">
                          {editForm.sellPrice > 0 ? `${liveEditCalc.net > 0 ? '+' : ''}${liveEditCalc.net.toLocaleString()}만` : '0만'}
                        </span>
                      </td>
                      <td className="py-2 px-1 text-center whitespace-nowrap">
                        <select
                          value={editForm.feeRate}
                          onChange={(e) => handleFormChange('feeRate', parseFloat(e.target.value) || 0.1)}
                          className="bg-[#0a0c14] border border-slate-600 rounded px-1 py-1 text-xs text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-sky-400"
                        >
                          <option value={0.1}>10%</option>
                          <option value={0.2}>20%</option>
                          <option value={0.3}>30%</option>
                          <option value={0.4}>40%</option>
                          <option value={0.5}>50%</option>
                        </select>
                      </td>
                      <td className="py-2.5 px-3 text-center whitespace-nowrap">
                        <div className="flex items-center justify-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => handleSaveEdit(item)}
                            className="px-2.5 py-1 rounded bg-sky-600 hover:bg-sky-500 text-white text-[11px] font-bold transition flex items-center gap-1 shadow-sm shadow-sky-600/30"
                            title="저장 (Enter)"
                          >
                            <Save className="w-3.5 h-3.5" />
                            <span>저장</span>
                          </button>
                          <button
                            type="button"
                            onClick={handleCancelEdit}
                            className="px-2 py-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-300 text-[11px] font-medium transition flex items-center gap-1"
                            title="취소 (Esc)"
                          >
                            <X className="w-3.5 h-3.5" />
                            <span>취소</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                }

                // [일반 읽기 모드 렌더링 - 더블클릭 또는 수정 버튼으로 편집 진입]
                return (
                  <tr
                    key={item.id}
                    onDoubleClick={() => handleStartEdit(item)}
                    className={`hover:bg-[#151824] transition cursor-pointer select-none ${isOver60 ? 'bg-rose-950/10' : isRisk ? 'bg-amber-950/10' : ''
                      }`}
                    title="더블클릭하면 인라인 수정을 시작합니다."
                  >
                    <td className="py-2.5 px-2 text-center text-slate-500 font-mono">
                      {item.order}
                    </td>
                    <td className="py-2.5 px-2.5 text-slate-400 whitespace-nowrap font-mono">
                      {item.buyDate}
                    </td>
                    <td className="py-2.5 px-2.5 font-bold text-white whitespace-nowrap">
                      {item.carNumber}
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-200 max-w-xs truncate">
                      {(() => {
                        const link = getEncarDetailLink(item.carNumber, item.encarUrl);
                        if (link) {
                          return (
                            <a
                              href={link}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="text-sky-400 hover:text-sky-300 hover:underline font-bold"
                              title={`엔카 매물 상세페이지 새창 열기 (${item.carName})`}
                            >
                              {item.carName}
                            </a>
                          );
                        }
                        return item.carName;
                      })()}
                    </td>
                    <td className="py-2.5 px-2 text-center whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${isOver60
                          ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          : isOver30
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        }`}>
                        {item.stockDays}일
                      </span>
                    </td>
                    <td className="py-2.5 px-2.5 text-right font-medium text-white whitespace-nowrap">
                      {item.buyPrice.toLocaleString()}만
                    </td>
                    <td className="py-2.5 px-2.5 text-right font-bold text-sky-400 whitespace-nowrap">
                      {item.sellPrice > 0 ? `${item.sellPrice.toLocaleString()}만` : '-'}
                    </td>
                    <td className="py-2.5 px-2 text-center text-amber-400 whitespace-nowrap">
                      {item.outerRepairs > 0 ? `${item.outerRepairs}판` : '0판'}
                    </td>
                    <td className="py-2.5 px-2 text-right text-slate-300 whitespace-nowrap">
                      {item.repairCost > 0 ? `${item.repairCost.toLocaleString()}만` : '-'}
                    </td>
                    <td className="py-2.5 px-2 text-right text-slate-300 whitespace-nowrap font-medium text-emerald-400">
                      {item.heydealerFee > 0 ? `${item.heydealerFee.toLocaleString()}만` : '-'}
                    </td>
                    <td className="py-2.5 px-2 text-right text-slate-400 whitespace-nowrap">
                      {item.baseExpenses}만
                    </td>
                    <td className="py-2.5 px-2 text-right text-slate-400 whitespace-nowrap">
                      {item.salesCommission > 0 ? `${item.salesCommission}만` : '-'}
                    </td>
                    <td className="py-2.5 px-2.5 text-right font-bold whitespace-nowrap">
                      <span className={item.contributionMargin >= 100 ? 'text-sky-400' : item.contributionMargin > 0 ? 'text-emerald-400' : 'text-rose-400'}>
                        {item.sellPrice > 0 ? `${item.contributionMargin > 0 ? '+' : ''}${item.contributionMargin.toLocaleString()}만` : '0만'}
                      </span>
                    </td>
                    <td className="py-2.5 px-2.5 text-right font-bold text-amber-400 whitespace-nowrap">
                      {item.sellPrice > 0 ? `${item.netProfit > 0 ? '+' : ''}${item.netProfit.toLocaleString()}만` : '0만'}
                    </td>
                    <td className="py-2.5 px-2 text-center text-slate-300 whitespace-nowrap font-mono">
                      {Math.round((item.feeRate || autoFeeRate) * 100)}%
                    </td>
                    <td className="py-2.5 px-3 text-center whitespace-nowrap">
                      <div className="flex items-center justify-center gap-1.5">
                        {onAnalyzeInCockpit && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onAnalyzeInCockpit(item);
                            }}
                            className="px-2 py-1 rounded bg-[#1e2230] hover:bg-[#282d3e] text-slate-300 border border-slate-700 text-[11px] font-semibold transition"
                            title="동급 시세 분석 콕핏으로 이동"
                          >
                            시세
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStartEdit(item);
                          }}
                          className="px-2 py-1 rounded bg-[#161c2e] hover:bg-sky-600/30 text-sky-400 border border-sky-600/40 text-[11px] font-semibold transition flex items-center gap-1"
                          title="매입일자, 매입가, 판매가, 수수료 등 실시간 수정"
                        >
                          <Edit2 className="w-3 h-3" />
                          <span>수정</span>
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (window.confirm(`[${item.carNumber}] 차량의 판매가 완료되었습니까? '판매완료 정산' 탭으로 이동합니다.`)) {
                              onMarkSold?.(item.id, item.sellPrice);
                            }
                          }}
                          className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold transition flex items-center gap-1 shadow-sm shadow-emerald-600/30"
                        >
                          <Check className="w-3 h-3" />
                          <span>판매완료</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

