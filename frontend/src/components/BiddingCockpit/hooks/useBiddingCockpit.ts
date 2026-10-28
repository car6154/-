import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { CarLedgerItem } from '@/types';
import { queryChaolmaCar, type ChaolmaCarHistory, type ChaolmaOriginDoc, type OptionItem } from '@/services/chaolmaService';
import { searchCockpitUnified, compareEncarItemsByBackendRule } from '@/services/cockpitService';
import { computeRuleBasedAssessment } from '@/utils/ruleBasedAssessment';
import {
  HD_PART_MAP,
  HD_REPAIR_MAP,
  formatHdRelativeDate,
  parseHeydealerOptions,
  fetchNewCarCatalog,
  normalizeChaolmaOptions,
  NewCarCatalogData,
} from '@/services/biddingOptionCatalog';
import { copyToClipboard } from '@/utils/clipboard';
import { EncarItem, EncarSoldItem, EncarSoldStats, HeydealerBidItem, BiddingCockpitTabProps, KcarMarketStats } from '../types';

export function useBiddingCockpit({
  initialCarName,
  initialSellPrice,
  presetCarName,
  presetSellPrice,
  preset,
  comparables = [],
  onSaveToLedger,
}: BiddingCockpitTabProps) {
  // ----------------------------------------------------
  // [좌측 고정 사이드바 상태값] - 100% 클린 빈 상태 초기화 (임의 더미 기본값 금지)
  // ----------------------------------------------------
  const [heydealerUrl, setHeydealerUrl] = useState('');
  const [carNumber, setCarNumber] = useState('');
  const [manufacturer, setManufacturer] = useState('');
  const [carName, setCarName] = useState('');
  const [detailModel, setDetailModel] = useState('');
  const [yearModel, setYearModel] = useState<number>(0);
  const [mileageKm, setMileageKm] = useState<number>(0);
  const [optionsTag, setOptionsTag] = useState('');
  const [targetOptions, setTargetOptions] = useState<OptionItem[]>([]);
  const [unclassifiedBalance, setUnclassifiedBalance] = useState<number>(0);
  const [expectedSellPrice, setExpectedSellPrice] = useState<number>(0);
  const [outerRepairCount, setOuterRepairCount] = useState<number>(0);
  const [auctionType, setAuctionType] = useState('셀프(기본)');
  const [targetMargin, setTargetMargin] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('jpro_target_margin');
      if (saved !== null) {
        const parsed = Number(saved);
        if (!isNaN(parsed) && parsed >= 0) return parsed;
      }
    } catch (e) {}
    return 150;
  });

  useEffect(() => {
    try {
      localStorage.setItem('jpro_target_margin', String(targetMargin));
    } catch (e) {}
  }, [targetMargin]);
  const [memo, setMemo] = useState('');
  const [savedSuccess, setSavedSuccess] = useState(false);

  // 8501 빅데이터 정밀 밸류에이션 상태
  const [encarValuation, setEncarValuation] = useState<{
    hasData: boolean;
    individualPrice: number;
    minPrice: number;
    maxPrice: number;
    score: number;
    bubbleGap: number;
    bubblePct: number;
    safeCeiling: number;
    baseMileage?: number;
  } | null>(null);

  // 백엔드에서 반환하는 엔카 API 통계 정보 (optAdj, accAdj 등 포함)
  const [backendEncarStats, setBackendEncarStats] = useState<any>(null);

  // 헤이딜러 실시간 동급 낙찰 데이터 및 선택 상태
  const [rawHeydealerComps, setRawHeydealerComps] = useState<any[]>([]);
  const [selectedHeydealerBidId, setSelectedHeydealerBidId] = useState<string | null>(null);
  const [selectedHeydealerGradeFilter, setSelectedHeydealerGradeFilter] = useState<string>('ALL');

  // 🌟 타겟 차량 원부 및 보험사고 이력 (carhistory) 상태
  const [targetCarHistory, setTargetCarHistory] = useState<{
    ownerChangedCount: number;
    isSingleOwner: boolean;
    myCarAccidentCount: number;
    myCarAccidentCost: number; // 만원 단위
    otherCarAccidentCount: number;
    otherCarAccidentCost: number; // 만원 단위
    totalLossCount: number;
    floodedCount: number;
    stolenCount: number;
    hasRentHistory: boolean;
    standardNewCarPrice: number; // 만원 단위
    baseCarPrice?: number; // 만원 단위
    totalOptionPrice?: number; // 만원 단위
    vin?: string;
    manufacturedDate?: string;
    inspectionValidUntil?: string;
    rawHistory?: ChaolmaCarHistory;
    originDoc?: ChaolmaOriginDoc;
  } | null>(null);

  // 🌟 보험사고 & 카히스토리 대형 상세 리포트 모달 표시 상태
  const [showCarHistoryModal, setShowCarHistoryModal] = useState<boolean>(false);

  // 🛡️ 5단계 전체 규칙 기반 차량 상태 종합 판정 (컴포넌트 레벨 공통 엔진)
  const currentAssessment = useMemo(() => {
    return computeRuleBasedAssessment({
      carNumber: carNumber || '',
      yearModel: yearModel || 20,
      currentMileage: mileageKm || 50000,
      ownerChangedCount: targetCarHistory?.ownerChangedCount ?? 0,
      isSingleOwner: targetCarHistory?.isSingleOwner ?? (targetCarHistory ? targetCarHistory.ownerChangedCount === 0 : false),
      hasRentHistory: targetCarHistory?.hasRentHistory ?? false,
      myCarAccidentCount: targetCarHistory?.myCarAccidentCount ?? 0,
      myCarAccidentCostMan: targetCarHistory?.myCarAccidentCost ?? 0,
      otherCarAccidentCount: targetCarHistory?.otherCarAccidentCount ?? 0,
      totalLossCount: targetCarHistory?.totalLossCount ?? 0,
      floodedCount: targetCarHistory?.floodedCount ?? 0,
      stolenCount: targetCarHistory?.stolenCount ?? 0,
      seizureCount: targetCarHistory?.originDoc?.seizure_count,
      mortgageCount: targetCarHistory?.originDoc?.mortgage_count,
      tuningCount: targetCarHistory?.originDoc?.tuning_count,
      inspectionValidEnd: targetCarHistory?.originDoc?.inspection_valid_end || targetCarHistory?.inspectionValidUntil,
      inspectionMileage: targetCarHistory?.originDoc?.inspection_mileage,
      lastHistoryMileage: (targetCarHistory?.rawHistory as any)?.mileages?.[0]?.mileage,
      outerRepairCount: outerRepairCount,
      frameDamage: false
    });
  }, [carNumber, yearModel, mileageKm, targetCarHistory, outerRepairCount]);

  // 실행 및 연동 상태값
  const [isSearchingCar, setIsSearchingCar] = useState(false);
  const [isAiEstimating, setIsAiEstimating] = useState(false);
  const [aiEstimateStep, setAiEstimateStep] = useState<string | null>(null);
  const [searchStatus, setSearchStatus] = useState<{ type: 'success' | 'error' | 'warning' | 'info'; message: string } | null>(null);

  // CarDetailModal 연동 상태 및 데이터 매핑
  const [cockpitModalCar, setCockpitModalCar] = useState<CarLedgerItem | null>(null);

  // ----------------------------------------------------
  // [엔카 실시간 동급 시세 상태 및 함수 (호이스팅 방지 상단 배치)]
  // ----------------------------------------------------
  const [liveEncarList, setLiveEncarList] = useState<EncarItem[]>([]);
  const [liveEncarSoldStats, setLiveEncarSoldStats] = useState<EncarSoldStats | null>(null);
  const [encarTotalModelCount, setEncarTotalModelCount] = useState<number>(0);
  const [encarFilteredCount, setEncarFilteredCount] = useState<number>(0);
  const [encarFilterStats, setEncarFilterStats] = useState<{
    targetBadge?: string;
    totalModelCount?: number;
    excludedByBadge?: number;
    validCount?: number;
    filterMethod?: string;
    reason?: string;
  } | null>(null);
  const [isEncarLoading, setIsEncarLoading] = useState<boolean>(false);
  const [encarErrorMessage, setEncarErrorMessage] = useState<string>('');
  const [encarSourceUrl, setEncarSourceUrl] = useState<string>('');
  const [showTrimColumn, setShowTrimColumn] = useState<boolean>(false);
  const activeRequestIdRef = useRef<number>(0);
  const skipAutoFetchRef = useRef<boolean>(false);
  const rawGradeNameRef = useRef<string>('');
  const rawGradeDetailNameRef = useRef<string>('');
  const prevAiRetailPriceRef = useRef<number>(0);
  const lastEncarFailReasonRef = useRef<string>('');

  // 선택된 엔카 매물 및 실시간 성능점검표 연동 상태 (상단 호이스팅)
  const [selectedEncarId, setSelectedEncarId] = useState<string>('');
  const [selectedInspectionMap, setSelectedInspectionMap] = useState<Record<string, any>>({});
  const selectedInspectionMapRef = useRef<Record<string, any>>({});
  const [isInspectionLoading, setIsInspectionLoading] = useState<boolean>(false);

  // 자사 오토플러스 실적 및 시장 수요도 상태 (상단 호이스팅)
  const [liveMarketStats, setLiveMarketStats] = useState<any>(null);

  // 🌟 공식 신차가격표 카탈로그 실시간 보관 상태 (옵션 툴팁 즉시 렌더링용)
  const [targetNewCarCatalog, setTargetNewCarCatalog] = useState<NewCarCatalogData | null>(null);

  // 🏢 K-Car 직영 실시간 시세 및 매물 상태
  const [kcarStats, setKcarStats] = useState<KcarMarketStats | null>(null);
  const [isKcarLoading, setIsKcarLoading] = useState<boolean>(false);

  // 🧹 차량 변경/재조회 시 이전 차량 데이터 완전 초기화 (상태 잔류 및 가격 오염 방지)
  const resetCockpitState = useCallback((options?: { keepInputs?: boolean }) => {
    // 1. 헤이딜러 실시간 낙찰 데이터 및 선택 상태 완전 초기화
    setRawHeydealerComps([]);
    setSelectedHeydealerBidId(null);
    setSelectedHeydealerGradeFilter('ALL');

    // 2. 가격 계산 및 밸류에이션 상태 초기화
    prevAiRetailPriceRef.current = 0;
    setExpectedSellPrice(0);
    setEncarValuation(null);
    setBackendEncarStats(null);
    setOuterRepairCount(0);
    setMemo('');

    // 3. 엔카 실시간 매물 및 통계 초기화
    setLiveEncarList([]);
    setSelectedEncarId('');
    setSelectedInspectionMap({});
    selectedInspectionMapRef.current = {};
    setLiveEncarSoldStats(null);
    setEncarTotalModelCount(0);
    setEncarFilteredCount(0);
    setEncarFilterStats(null);
    setEncarErrorMessage('');
    setEncarSourceUrl('');

    // 3-1. K-Car 실시간 시세 및 통계 초기화
    setKcarStats(null);

    // 4. 차량 원부 / 카히스토리 / 모달 상태 초기화
    setTargetCarHistory(null);
    setLiveMarketStats(null);
    setCockpitModalCar(null);
    setOptionsTag('');
    setTargetOptions([]);
    setUnclassifiedBalance(0);
    setSearchStatus(null);
    setTargetNewCarCatalog(null);

    // 5. 기본 입력 필드 (keepInputs가 false이거나 없을 때만 초기화)
    if (!options?.keepInputs) {
      setManufacturer('');
      setCarName('');
      setDetailModel('');
      setYearModel(0);
      setMileageKm(0);
      rawGradeNameRef.current = '';
      rawGradeDetailNameRef.current = '';
    }
  }, []);

  const fetchEncarSoldOut = useCallback(async (carIds: string[], expectedModel: string, targetYear: string, targetDetailModel?: string) => {
    if (!carIds.length || !expectedModel) return;
    try {
      const res = await fetch('/api/encar/soldout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          carIds,
          expectedModel,
          targetYear,
          detailModel: targetDetailModel !== undefined ? targetDetailModel : detailModel
        })
      });
      if (res.ok) {
        const result = await res.json();
        if (result.success && result.data) {
          setLiveEncarSoldStats(result.data);
        }
      }
    } catch (e) {
      console.warn('Encar soldout fetch failed:', e);
    }
  }, [detailModel]);

  // ----------------------------------------------------
  // [엔카 & 케이카 데이터 상태 반영 일원화 헬퍼 (Phase 2)]
  // ----------------------------------------------------
  const applyEncarData = useCallback((data: any, optionsUrl?: string) => {
    if (data && data.success && Array.isArray(data.items) && data.items.length > 0) {
      lastEncarFailReasonRef.current = '';
      setEncarErrorMessage('');
      setLiveEncarList(data.items);
      setEncarTotalModelCount(data.totalModelCount || data.items.length);
      setEncarFilteredCount(data.filteredCount || data.items.length);
      setEncarFilterStats(data.filterStats || null);
      if (data.directSearchUrl) {
        setEncarSourceUrl(data.directSearchUrl);
      } else if (optionsUrl) {
        setEncarSourceUrl(optionsUrl);
      }
      if (data.stats) {
        setBackendEncarStats(data.stats);
      }
      if (data.valuation && data.valuation.hasData) {
        setEncarValuation(data.valuation);
      } else if (data.stats?.avg && data.stats.avg > 0) {
        const avgP = data.stats.avg;
        const benchP = data.stats.benchmarkPrice || 0;
        if (benchP > 0) {
          const minP = data.stats.minBand || Math.round(benchP * 0.94);
          const maxP = data.stats.maxBand || Math.round(benchP * 1.08);
          const bGap = avgP - benchP;
          const bPct = Math.round((bGap / benchP) * 1000) / 10;
          setEncarValuation({
            hasData: true,
            individualPrice: benchP,
            minPrice: minP,
            maxPrice: maxP,
            score: 96.1,
            bubbleGap: bGap,
            bubblePct: bPct,
            safeCeiling: Math.max(0, benchP - 180)
          });
        } else {
          setEncarValuation(null);
        }
      }

      const cids = data.items.map((it: any) => String(it._carid || it.id || it.carid || '').replace(/\D/g, '')).filter(Boolean);
      if (cids.length > 0) {
        fetchEncarSoldOut(cids, carName, String(yearModel), detailModel);
      }

      return data.items;
    } else {
      const rawReason = data?.failReason ? String(data.failReason).replace(/^[❌\s]+/, '').trim() : '';
      lastEncarFailReasonRef.current = rawReason;
      setLiveEncarList([]);
      setEncarTotalModelCount(data?.totalModelCount || 0);
      setEncarFilteredCount(0);
      setEncarFilterStats(null);
      setEncarValuation(null);
      setEncarErrorMessage(data?.message || '엔카 실시간 매물을 불러오지 못했습니다.');
      if (data?.directSearchUrl) {
        setEncarSourceUrl(data.directSearchUrl);
      }
      return [];
    }
  }, [carName, yearModel, detailModel, fetchEncarSoldOut]);

  const applyKcarData = useCallback((data: any) => {
    if (data && data.success) {
      setKcarStats(data);
    } else {
      setKcarStats(null);
    }
  }, []);

  const fetchEncarComparable = useCallback(async (options: {
    url?: string;
    carName?: string;
    detailModel?: string;
    gradeName?: string;
    gradeDetailName?: string;
    manufacturer?: string;
    year?: number;
    mileage?: number;
    carNumber?: string;
    skipDetail?: boolean;
  }) => {
    const targetCarName = options.carName || carName;
    if (!targetCarName && !options.url) {
      setLiveEncarList([]);
      setEncarTotalModelCount(0);
      setEncarFilteredCount(0);
      return [];
    }

    const reqId = ++activeRequestIdRef.current;
    setIsEncarLoading(true);
    setEncarErrorMessage('');
    try {
      const targetCarNumber = options.carNumber !== undefined ? options.carNumber : (carNumber || '');
      const targetDetail = options.detailModel !== undefined ? options.detailModel : detailModel;
      const targetGradeName = options.gradeName !== undefined ? options.gradeName : rawGradeNameRef.current;
      const targetGradeDetail = options.gradeDetailName !== undefined ? options.gradeDetailName : rawGradeDetailNameRef.current;
      const targetMaker = options.manufacturer || manufacturer;
      const targetYr = options.year !== undefined ? options.year : yearModel;
      const targetMil = options.mileage !== undefined ? options.mileage : mileageKm;
      const targetOpt = optionsTag || '';
      const skipDetail = options.skipDetail !== undefined ? options.skipDetail : false;

      const unifiedRes = await searchCockpitUnified({
        encarUrl: options.url || '',
        carName: targetCarName,
        detailModel: targetDetail,
        gradeName: targetGradeName,
        gradeDetailName: targetGradeDetail,
        manufacturer: targetMaker,
        year: targetYr,
        mileage: targetMil,
        targetOptions: targetOpt,
        carNumber: targetCarNumber,
        skipDetail: skipDetail,
        sources: ['encar'],
      });

      const data = unifiedRes.encar;
      if (reqId !== activeRequestIdRef.current) {
        if (!data || !data.success || !Array.isArray(data.items) || data.items.length === 0) {
          return [];
        }
      }

      return applyEncarData(data, options.url);
    } catch (e: any) {
      console.warn('Encar fetch failed:', e);
      lastEncarFailReasonRef.current = e?.message ? String(e.message).replace(/^[❌\s]+/, '').trim() : '';
      setLiveEncarList([]);
      setEncarTotalModelCount(0);
      setEncarFilteredCount(0);
      setEncarFilterStats(null);
      setEncarValuation(null);
      setEncarErrorMessage('엔카 실시간 매물을 불러오지 못했습니다.');
    } finally {
      if (reqId === activeRequestIdRef.current) {
        setIsEncarLoading(false);
      }
    }
    return [];
  }, [carName, detailModel, manufacturer, yearModel, mileageKm, carNumber, optionsTag, applyEncarData]);

  // 🏢 K-Car 직영 실시간 시세 및 통계 비동기 수집
  const fetchKcarMarket = useCallback(async (options?: {
    carName?: string;
    detailModel?: string;
    gradeName?: string;
    gradeDetailName?: string;
    manufacturer?: string;
    year?: number;
    mileage?: number;
    accident?: string;
    targetOptions?: string;
  }) => {
    const targetCarName = options?.carName || carName;
    if (!targetCarName) {
      setKcarStats(null);
      return;
    }
    setIsKcarLoading(true);
    try {
      const targetDetail = options?.detailModel !== undefined ? options.detailModel : detailModel;
      const targetGradeName = options?.gradeName !== undefined ? options.gradeName : rawGradeNameRef.current;
      const targetGradeDetail = options?.gradeDetailName !== undefined ? options.gradeDetailName : rawGradeDetailNameRef.current;
      const targetMaker = options?.manufacturer || manufacturer;
      const targetYr = options?.year !== undefined ? options.year : yearModel;
      const targetMil = options?.mileage !== undefined ? options.mileage : mileageKm;
      const targetOpt = options?.targetOptions !== undefined ? options.targetOptions : (optionsTag || '');

      const unifiedRes = await searchCockpitUnified({
        carName: targetCarName,
        detailModel: targetDetail,
        gradeName: targetGradeName,
        gradeDetailName: targetGradeDetail,
        manufacturer: targetMaker,
        year: targetYr,
        mileage: targetMil,
        targetOptions: targetOpt,
        sources: ['kcar'],
      });

      applyKcarData(unifiedRes.kcar);
    } catch (e) {
      console.warn('[useBiddingCockpit] fetchKcarMarket failed:', e);
    } finally {
      setIsKcarLoading(false);
    }
  }, [carName, detailModel, manufacturer, yearModel, mileageKm, optionsTag, applyKcarData]);

  // 사이드바 차량 조건 변경 시 실데이터 자동 수집 (차량이 있을 때만)
  useEffect(() => {
    if (isSearchingCar) return;
    if (skipAutoFetchRef.current) {
      skipAutoFetchRef.current = false;
      return;
    }
    if (!carName && !initialCarName) return;
    const timer = setTimeout(() => {
      fetchEncarComparable({
        carName: carName || initialCarName,
        detailModel: detailModel,
        gradeName: rawGradeNameRef.current,
        gradeDetailName: rawGradeDetailNameRef.current,
        manufacturer: manufacturer,
        year: yearModel,
        mileage: mileageKm,
        carNumber: carNumber
      });
      fetchKcarMarket({
        carName: carName || initialCarName,
        detailModel: detailModel,
        gradeName: rawGradeNameRef.current,
        gradeDetailName: rawGradeDetailNameRef.current,
        manufacturer: manufacturer,
        year: yearModel,
        mileage: mileageKm,
        accident: currentAssessment?.accidentDamage?.status,
        targetOptions: optionsTag,
      });
    }, 300);
    return () => clearTimeout(timer);
  }, [carName, detailModel, manufacturer, yearModel, mileageKm, carNumber, currentAssessment?.accidentDamage?.status, optionsTag, fetchEncarComparable, fetchKcarMarket]);

  // 텍스트/복사 데이터 빠른 자동 분석 모달 상태
  const [isQuickPasteOpen, setIsQuickPasteOpen] = useState(false);
  const [quickPasteText, setQuickPasteText] = useState('');

  const handleQuickParseText = () => {
    if (!quickPasteText.trim()) return;
    const raw = quickPasteText;

    // 🧹 텍스트 빠른 분석 시 이전 차량 상태 즉시 완전 리셋
    resetCockpitState({ keepInputs: false });
    
    // 1. 차량번호 추출 (예: 12가1234, 123가1234)
    const carNoMatch = raw.match(/(\d{2,3}[가-힣]\s*\d{4})/);
    if (carNoMatch) setCarNumber(carNoMatch[1].replace(/\s+/g, ''));

    // 2. 연식 추출 (예: 2021년, 21년식, 19년)
    const yearMatch = raw.match(/(\d{2,4})\s*(년식|년|\.|\/)/);
    if (yearMatch) {
      let y = parseInt(yearMatch[1], 10);
      if (y > 2000) y -= 2000;
      if (y >= 10 && y <= 26) setYearModel(y);
    }

    // 3. 주행거리 추출 (예: 45,000km, 4.5만km, 45000)
    const kmMatch = raw.match(/([\d,]+)\s*(?:km|킬로|k)/i) || raw.match(/(\d+(?:\.\d+)?)\s*만\s*(?:km)?/i);
    if (kmMatch) {
      if (kmMatch[0].includes('만')) {
        const num = parseFloat(kmMatch[1]) * 10000;
        setMileageKm(Math.round(num));
      } else {
        const num = parseInt(kmMatch[1].replace(/,/g, ''), 10);
        if (!isNaN(num) && num > 500) setMileageKm(num);
      }
    }

    // 4. 가격 추출 (예: 1,380만원, 1380만, 815만원)
    const priceMatch = raw.match(/([\d,]+)\s*(?:만원|만)/);
    if (priceMatch) {
      const p = parseInt(priceMatch[1].replace(/,/g, ''), 10);
      if (!isNaN(p) && p >= 100 && p <= 15000) setExpectedSellPrice(p);
    }

    // 5. 차종 판별
    if (raw.includes('아반떼')) { setManufacturer('현대'); setCarName('더 뉴 아반떼 AD'); }
    else if (raw.includes('그랜저')) { setManufacturer('현대'); setCarName('더 뉴 그랜저 IG'); }
    else if (raw.includes('쏘나타')) { setManufacturer('현대'); setCarName('쏘나타 (DN8)'); }
    else if (raw.includes('카니발')) { setManufacturer('기아'); setCarName('올 뉴 카니발'); }
    else if (raw.includes('레이')) { setManufacturer('기아'); setCarName('더 뉴 레이'); }
    else if (raw.includes('모닝')) { setManufacturer('기아'); setCarName('올뉴모닝(JA)'); }
    else if (raw.includes('K5')) { setManufacturer('기아'); setCarName('K5 3세대'); }
    else if (raw.includes('캐스퍼')) { setManufacturer('현대'); setCarName('캐스퍼'); }
    else if (raw.includes('QM6')) { setManufacturer('르노코리아'); setCarName('QM6'); }
    else if (raw.includes('G80')) { setManufacturer('제네시스'); setCarName('제네시스 G80'); }
    else if (raw.includes('스포티지')) { setManufacturer('기아'); setCarName('스포티지 더 볼드'); }
    else if (raw.includes('투싼')) { setManufacturer('현대'); setCarName('투싼 (NX4)'); }
    else if (raw.includes('토레스')) { setManufacturer('KG모빌리티'); setCarName('토레스'); }

    // 6. 판금/교환/외판 수리 판수 정밀 감지 (예: '외판: 4판', '외판 4판', '판금 2건', '교환 1건')
    const outerMatch = raw.match(/외판\s*[:：]?\s*(\d+)\s*판?/i);
    const repairMatch = raw.match(/(?:판금|교환)\s*(\d+)\s*(?:건|판)/i);
    if (outerMatch) {
      setOuterRepairCount(parseInt(outerMatch[1], 10));
    } else if (repairMatch) {
      setOuterRepairCount(parseInt(repairMatch[1], 10));
    } else if (raw.includes('무사고') || raw.includes('완전무사고')) {
      setOuterRepairCount(0);
    }

    setIsQuickPasteOpen(false);
    setSearchStatus({
      type: 'success',
      message: '✨ 텍스트 분석 완료! 제원, 연식, 주행거리, 시세가 콕핏에 자동 세팅되었습니다.'
    });
  };

  // 1. 장부 / 재고 / 외부에서 preset 객체가 들어왔을 때 모든 사이드바 필터 100% 동기화
  useEffect(() => {
    if (!preset) return;

    (async () => {
      // d. 기존의 낡은 ref 리셋 (a 단계 전에 유지)
      rawGradeNameRef.current = '';
      rawGradeDetailNameRef.current = '';

      console.info(`[InvDiag] preset 수신: carNumber=${preset.carNumber || ''}, mileage=${preset.mileage || ''}, carName=${preset.carName || ''}, detailModel=${preset.detailModel || ''}`);

      // a. preset의 기본 정보부터 적용: setCarNumber, setManufacturer, setCarName, setDetailModel, setYearModel, setMileageKm (조회 실패 시에도 화면에 표시되도록)
      if (preset.carNumber) {
        setCarNumber(preset.carNumber);
      }
      if (preset.manufacturer) {
        setManufacturer(preset.manufacturer);
      }
      if (preset.carName) {
        setCarName(preset.carName);
        if (!preset.manufacturer) {
          if (preset.carName.includes('아반떼') || preset.carName.includes('쏘나타') || preset.carName.includes('그랜저') || preset.carName.includes('캐스퍼')) {
            setManufacturer('현대');
          } else if (preset.carName.includes('기아') || preset.carName.includes('모닝') || preset.carName.includes('레이') || preset.carName.includes('카니발') || preset.carName.includes('K5')) {
            setManufacturer('기아');
          } else if (preset.carName.includes('르노') || preset.carName.includes('SM') || preset.carName.includes('QM')) {
            setManufacturer('르노코리아');
          } else if (preset.carName.includes('KG') || preset.carName.includes('쌍용')) {
            setManufacturer('KG모빌리티');
          } else if (preset.carName.includes('제네시스') || preset.carName.includes('G80')) {
            setManufacturer('제네시스');
          }
        }
      }
      if (preset.detailModel) {
        setDetailModel(preset.detailModel);
      }
      if (preset.year !== undefined) {
        let y = typeof preset.year === 'number' ? preset.year : parseInt(String(preset.year).replace(/[^\d]/g, ''), 10);
        if (y > 2000) y -= 2000;
        if (!isNaN(y) && y > 0) setYearModel(y);
      }
      let parsedMileage = 0;
      if (preset.mileage !== undefined && preset.mileage !== null && preset.mileage !== '') {
        let m = typeof preset.mileage === 'number' ? preset.mileage : parseInt(String(preset.mileage).replace(/[^\d]/g, ''), 10);
        if (!isNaN(m) && m > 0) {
          parsedMileage = m;
          setMileageKm(m);
        } else {
          setMileageKm(0);
        }
      } else {
        // 프리셋에 주행거리가 없으면 이전 차 숫자가 남지 않게 0으로 초기화
        setMileageKm(0);
      }
      if (preset.options) {
        setOptionsTag(preset.options);
      }

      // b. await handleLookupCarNumber(preset.carNumber, parsedMileage, true) — 정상 조회와 완전히 동일한 경로. 성공 시 실시간 차얼마·엔카 산출 시세 그대로 유지.
      let lookupSucceeded = false;
      if (preset.carNumber) {
        lookupSucceeded = Boolean(await handleLookupCarNumber(preset.carNumber, parsedMileage, true));
      }

      // c. 차얼마 실시간 조회 실패 시, preset의 제원으로 엔카/K-Car 크롤링 폴백 직접 가동
      let fallbackCrawlingSucceeded = false;
      if (!lookupSucceeded) {
        if (preset.sellPrice && preset.sellPrice > 0) {
          setExpectedSellPrice(preset.sellPrice);
        }
        if (preset.buyPrice && preset.buyPrice > 0) {
          setUserBid(preset.buyPrice);
        }

        const fbCarName = preset.carName || carName;
        const fbDetailModel = preset.detailModel || detailModel;
        const fbMileage = parsedMileage || mileageKm;
        const fbYear = typeof preset.year === 'number'
          ? preset.year
          : (preset.year ? parseInt(String(preset.year).replace(/[^\d]/g, ''), 10) : undefined);
        const fbManufacturer = preset.manufacturer || manufacturer;

        if (fbCarName) {
          console.info(`[InvDiag] 폴백 크롤링 호출: carName=${fbCarName}, detailModel=${fbDetailModel}, mileage=${fbMileage}`);
          try {
            const encarItems = await fetchEncarComparable({
              carName: fbCarName,
              detailModel: fbDetailModel,
              year: fbYear,
              mileage: fbMileage,
              carNumber: preset.carNumber || carNumber,
              manufacturer: fbManufacturer,
            });

            fetchKcarMarket({
              carName: fbCarName,
              detailModel: fbDetailModel,
              year: fbYear,
              mileage: fbMileage,
              manufacturer: fbManufacturer,
            });

            if (encarItems && encarItems.length > 0) {
              fallbackCrawlingSucceeded = true;
            }
          } catch (crawlingErr) {
            console.error('[InvDiag] 폴백 크롤링 오류:', crawlingErr);
          }
        } else {
          console.info(`[InvDiag] 폴백 크롤링 건너뜀 (carName 부재): carNumber=${preset.carNumber || ''}`);
        }
      }

      // d. 외판 수리 판수: 장부/역추적 프리셋의 외판 수리 개수를 최우선 자동 입력
      if (typeof preset.outerRepairs === 'number') {
        setOuterRepairCount(preset.outerRepairs);
      }

      // e. 특이사항: 조회된 차량의 특이사항 메모 자동 입력 (기존 수동 입력값이 있으면 유지)
      if (preset.memo) {
        setMemo((prevMemo) => {
          const trimmedPrev = (prevMemo || '').trim();
          // 기존에 사용자가 직접 타이핑한 유의미한 수동 입력값이 있으면 덮어쓰지 않고 유지
          if (trimmedPrev && !trimmedPrev.startsWith('[장부 역추적') && !trimmedPrev.startsWith('[재고 역추적') && !trimmedPrev.startsWith('[실적DB') && !trimmedPrev.startsWith('[헤이딜러')) {
            return prevMemo;
          }
          return preset.memo || prevMemo;
        });
      }

      if (preset.targetMargin) {
        setTargetMargin(preset.targetMargin);
      }
      if (preset.auctionType) {
        setAuctionType(preset.auctionType);
      }

      // f. 실제 결과에 따른 정직한 상태 메시지 구분 표시
      if (lookupSucceeded) {
        setSearchStatus({
          type: 'success',
          message: `✅ [${preset.carNumber || preset.carName}] 차얼마 제원 및 엔카 실시간 시세 연동 완료!`
        });
      } else if (fallbackCrawlingSucceeded) {
        setSearchStatus({
          type: 'warning',
          message: `⚠️ [${preset.carNumber || preset.carName}] 차얼마 미등록 — 엔카 동급 매물 크롤링 연동 완료`
        });
      } else {
        setSearchStatus({
          type: 'error',
          message: `❌ [${preset.carNumber || preset.carName}] 차얼마 조회 및 엔카 크롤링 연동 실패 (조건 재확인 필요)`
        });
      }
      setTimeout(() => setSearchStatus(null), 4000);
    })();
  }, [preset]);

  // 구형 호환: presetCarName / presetSellPrice만 들어올 때 (임의 더미 제원 강제 주입 금지)
  useEffect(() => {
    if (presetCarName && !preset) {
      setCarName(presetCarName);
    }
    if (presetSellPrice && presetSellPrice > 0 && !preset) {
      setExpectedSellPrice(presetSellPrice);
    }
  }, [presetCarName, presetSellPrice, preset]);

  // 2. 차량번호 [조회] 실제 실행 핸들러 (차얼마 & 엔카 실시간 제원 및 옵션 완벽 연동)
  const handleLookupCarNumber = async (targetNo?: string, overrideMileage?: number, silent?: boolean) => {
    const no = (targetNo || carNumber).replace(/\s+/g, '').trim();
    if (!no) {
      if (!silent) {
        setSearchStatus({
          type: 'warning',
          message: '⚠️ 차량번호를 입력해주세요.'
        });
        alert('차량번호를 입력해주세요.');
      }
      return;
    }
    const effectiveMileage = (overrideMileage !== undefined && overrideMileage > 0) ? overrideMileage : mileageKm;
    if (!effectiveMileage || effectiveMileage <= 0) {
      if (!silent) {
        setSearchStatus({
          type: 'warning',
          message: '⚠️ 주행거리를 입력해주세요. (차얼마 조회 시 차량번호와 주행거리 필수)'
        });
        alert('주행거리를 입력해주세요. (차얼마 조회 시 차량번호와 주행거리 입력이 필수입니다)');
      }
      return;
    }

    // 🧹 새 차량번호 조회 시 이전 차량의 헤이딜러 낙찰/엔카 매물/밸류에이션 즉시 리셋 (입력 필드는 유지)
    resetCockpitState({ keepInputs: true });

    setIsSearchingCar(true);
    setSearchStatus({
      type: 'info',
      message: '🔍 차얼마 & 엔카 실시간 제원/옵션 스캔 중...'
    });

    try {
      // 콕핏 통합 검색 (Phase 2: 백엔드 단일 진실 공급원 - 차얼마, 엔카, 케이카 일괄 수집)
      const unifiedRes = await searchCockpitUnified({
        carNumber: no,
        mileage: effectiveMileage,
        sources: ['chaolma', 'encar', 'kcar']
      });
      console.info(`[InvDiag] 콕핏 통합 조회 응답: carNumber=${no}, success=${Boolean(unifiedRes?.success)}`);

      const res = unifiedRes.chaolma;
      if (res && res.success) {
        skipAutoFetchRef.current = true;
        setCarNumber(no);
        if (res.maker) setManufacturer(res.maker);
        const resolvedCarName = res.model_detail_name || res.model_name || '';
        if (resolvedCarName) setCarName(resolvedCarName);
        const rawG = String(res.grade_name || '').trim();
        const rawGd = String(res.grade_detail_name || '').trim();
        rawGradeNameRef.current = rawG;
        rawGradeDetailNameRef.current = rawGd;

        // 💡 유종/배기량(rawG: 예 '가솔린 1.0 터보')과 세부트림(rawGd: 예 '인스퍼레이션')을 온전히 결합 (app.py:1605-1616 동일)
        let resolvedGrade = '';
        if (rawG && rawGd) {
          if (rawGd.includes(rawG)) {
            resolvedGrade = rawGd;
          } else {
            const gParts = rawG.split(/\s+/).filter(p => p && !rawGd.includes(p));
            resolvedGrade = gParts.length > 0 ? `${gParts.join(' ')} ${rawGd}`.trim() : `${rawG} ${rawGd}`.trim();
          }
        } else if (rawGd) {
          resolvedGrade = rawGd;
        } else {
          resolvedGrade = rawG;
        }
        if (resolvedGrade) setDetailModel(resolvedGrade);

        let yr = yearModel;
        if (res.year) {
          const ym = res.year.match(/\d+/);
          if (ym) {
            let y = parseInt(ym[0], 10);
            if (y > 2000) y -= 2000;
            yr = y;
          }
        }
        setYearModel(yr);

        let calculatedOptionsTag = '';
        if (res.options && res.options.length > 0) {
          setTargetOptions(res.options);
          setUnclassifiedBalance(res.unclassified_balance_man || 0);
          const optStr = res.options.map(o => `${o.name}(${o.price_man || Math.round(o.price / 10000)}만)`).join(' · ');
          const totalOptMan = res.total_option_price ? (res.total_option_price > 10000 ? Math.round(res.total_option_price / 10000) : res.total_option_price) : res.options.reduce((acc, cur) => acc + (cur.price_man || Math.round(cur.price / 10000)), 0);
          calculatedOptionsTag = `${optStr} [옵션총액: ${totalOptMan}만]`;
          setOptionsTag(calculatedOptionsTag);
        } else {
          setTargetOptions([]);
          setUnclassifiedBalance(0);
          calculatedOptionsTag = '추가 옵션 없음 (기본 출고 사양)';
          setOptionsTag(calculatedOptionsTag);
        }

        if (res.new_car_price > 0 || res.vin || res.car_history) {
          const rawNewP = res.new_car_price || 0;
          const stdP = rawNewP > 10000 ? Math.round(rawNewP / 10000) : rawNewP;
          const rawBaseP = res.base_car_price || 0;
          const baseP = rawBaseP > 10000 ? Math.round(rawBaseP / 10000) : rawBaseP;
          const rawOptP = res.total_option_price || 0;
          const optP = rawOptP > 10000 ? Math.round(rawOptP / 10000) : rawOptP;

          const ch = res.car_history;
          const doc = res.origin_doc;
          const ocCount = ch ? ch.owner_changed_count : 0;
          const isSingle = ch ? ch.is_single_owner : true;
          const myCnt = ch ? ch.my_car_accident_count : 0;
          const myCost = ch ? ch.my_car_accident_cost_man : 0;
          const otherCnt = ch ? ch.other_car_accident_count : 0;
          const otherCost = ch ? ch.other_car_accident_cost_man : 0;
          const totLoss = ch ? ch.total_loss_count : 0;
          const flood = ch ? ch.flooded_count : 0;
          const stole = ch ? ch.stolen_count : 0;
          const rent = ch ? ch.has_rent_history : false;

          setTargetCarHistory({
            ownerChangedCount: ocCount,
            isSingleOwner: isSingle,
            myCarAccidentCount: myCnt,
            myCarAccidentCost: myCost,
            otherCarAccidentCount: otherCnt,
            otherCarAccidentCost: otherCost,
            totalLossCount: totLoss,
            floodedCount: flood,
            stolenCount: stole,
            hasRentHistory: rent,
            standardNewCarPrice: stdP,
            baseCarPrice: baseP,
            totalOptionPrice: optP,
            vin: res.vin || (doc ? doc.raw_doc?.VIN : '') || '',
            manufacturedDate: res.release_date || (ch ? ch.first_reg_date : '') || (doc ? doc.first_regist_date : '') || '',
            inspectionValidUntil: (doc ? doc.inspection_valid_end : '') || (ch ? ch.uninsured_period : '') || '',
            rawHistory: ch,
            originDoc: doc
          });
        }

        // 프리셋 주행거리가 없을 때만 차얼마/검사/카히스토리 주행거리 결과로 채움 (프리셋이 있으면 절대 덮어쓰지 않음)
        if (!overrideMileage || overrideMileage <= 0) {
          const docMil = res.origin_doc?.inspection_mileage;
          const histMil = (res.car_history as any)?.mileages?.[0]?.mileage;
          const foundMil = docMil || histMil;
          if (foundMil && typeof foundMil === 'number' && foundMil > 0) {
            setMileageKm(foundMil);
          } else if (foundMil) {
            const parsed = parseInt(String(foundMil).replace(/[^\d]/g, ''), 10);
            if (!isNaN(parsed) && parsed > 0) {
              setMileageKm(parsed);
            }
          }
        }

        // 자사 소매/도매 실적 통계도 즉시 연동 (동일 차종 재조회 시 resetCockpitState로 초기화된 상태 복구 보장)
        fetchMarketStats(resolvedCarName || carName, resolvedGrade || detailModel, yr);

        // 엔카 실시간 매물 및 밸류에이션 반영
        if (unifiedRes.encar) {
          applyEncarData(unifiedRes.encar);
        }

        // 케이카 직영 마켓 통계 반영
        if (unifiedRes.kcar) {
          applyKcarData(unifiedRes.kcar);
        }

        skipAutoFetchRef.current = true;

        // 백엔드 통합 상태 메시지 직결 (단일 진실 공급원)
        if (unifiedRes.statusMessage) {
          setSearchStatus(unifiedRes.statusMessage);
        }
        return true;
      } else {
        if (unifiedRes.statusMessage) {
          setSearchStatus(unifiedRes.statusMessage);
        } else {
          setSearchStatus({
            type: 'warning',
            message: `⚠️ [${no}] ${res?.message || '차얼마 데이터 조회 실패 또는 미등록 차량'}`
          });
        }
        return false;
      }
    } catch (err: any) {
      console.error('차량 조회 오류:', err);
      setSearchStatus({
        type: 'error',
        message: `❌ [${no}] 차량 조회 중 오류가 발생했습니다: ${err?.message || err}`
      });
      return false;
    } finally {
      setIsSearchingCar(false);
    }
  };

  // 3. 헤이딜러 URL [AI 견적 산출] 실제 실행 핸들러 (실제 백엔드 프록시 호출)
  const handleHeydealerAiEstimate = async () => {
    if (!heydealerUrl.trim()) {
      setSearchStatus({
        type: 'error',
        message: '❌ 헤이딜러 차량 URL(예: https://dealer.heydealer.com/cars/lRrZ86Wl/) 또는 ID를 입력해주세요.'
      });
      return;
    }

    // 🧹 새 헤이딜러 URL 조회 시 이전 차량의 모든 상태 즉시 완전 리셋
    resetCockpitState({ keepInputs: false });

    setIsAiEstimating(true);
    setAiEstimateStep('헤이딜러 딜러 전용 API 연결 중...');

    try {
      let hashId = heydealerUrl.trim();
      const match = hashId.match(/cars\/([a-zA-Z0-9_-]+)/);
      if (match) {
        hashId = match[1];
      }

      setAiEstimateStep(`매물 ID [${hashId}] 제원 및 진단 리포트 수신 중...`);

      const savedCookie = localStorage.getItem('jpro_session_cookie') || '';
      const headers: Record<string, string> = {};
      if (savedCookie.trim()) {
        headers['x-heydealer-cookie'] = savedCookie.trim();
        if (savedCookie.startsWith('Bearer ') || savedCookie.startsWith('Token ')) {
          headers['Authorization'] = savedCookie.trim();
        }
      }

      const res = await fetch(`/api/heydealer/car/${hashId}`, {
        headers
      });

      const resJson = await res.json();

      // 헤이딜러 세션 인증이 만료되었거나 비로그인 차단된 경우
      if (!res.ok || resJson.errorType === 'LOGIN_REQUIRED' || resJson.raw?.toast_message === '로그인 후 사용해주세요.' || resJson.toast_message === '로그인 후 사용해주세요.') {
        setSearchStatus({
          type: 'warning',
          message: '⚠️ [헤이딜러 딜러 세션 만료] dealer.heydealer.com 로그인 세션(sessionid)이 만료되었습니다. 헤이딜러 딜러 페이지에 다시 로그인 후 상단 [세션 연동]에서 쿠키를 전송해주세요. (아래 [차량번호 검색] 또는 [샘플 데이터]는 즉시 작동합니다)'
        });
        setAiEstimateStep(null);
        setIsAiEstimating(false);
        return;
      }

      const carData = resJson.data || resJson;
      const detail = carData.detail || carData;
      const auction = carData.auction || {};

      // 정상 데이터가 수신된 경우 (모든 null/undefined 값 안전 처리)
      const cNo = String(detail.car_number || detail.car_no || detail.plate_no || carData.car_number || carData.car_no || detail.vehicle_information?.car_number || '').trim();
      const cModelPart = String(detail.model_part_name || detail.model || '').trim();
      const cGradePart = String(detail.grade_part_name || '').trim();
      const cName = cModelPart || (String(detail.full_name || detail.display_car_name || '').replace(cGradePart, '').trim() || '-');
      const cGrade = cGradePart || '-';
      const cBrand = String(detail.brand_name || '-').trim();
      const rawYear = detail.year ?? carData.year ?? 0;
      const rawMil = Number(detail.mileage) || Number(carData.mileage) || Number(detail.vehicle_information?.mileage) || 0;
      const cAccident = String(detail.accident_repairs_summary_display || detail.accident_repairs_summary || detail.accident_description || '').trim();
      const cDesiredPrice = Number(auction.desired_price) || 0;

      if (cNo || cName) {
        skipAutoFetchRef.current = true;
        if (cNo) setCarNumber(cNo);
        setCarName(cName);
        if (cBrand) setManufacturer(cBrand);
        setDetailModel(cGrade);

        // 💡 [연식/형식 엄격 구분 - Streamlit app.py 1110~1114행 100% 동일]
        // initial_registration_date: 최초등록일 기준 연식 (예: 2020-07-23 -> 20 / '20년식')
        // year: 모델 형식연도 (예: 2021년형 -> '21년형')
        const initRegDate = detail.initial_registration_date || detail.vehicle_information?.initial_registration_date || carData.initial_registration_date || '';
        let resolvedYear = 0;
        if (initRegDate) {
          const m = String(initRegDate).match(/(\d{4})/);
          if (m) {
            let y = parseInt(m[1], 10);
            if (y > 2000) y -= 2000;
            resolvedYear = y;
          }
        }
        if (!resolvedYear && rawYear) {
          let y = typeof rawYear === 'number' ? rawYear : parseInt(String(rawYear).match(/\d+/)?.[0] || '0', 10);
          if (y > 2000) y -= 2000;
          resolvedYear = y;
        }
        if (resolvedYear > 0) {
          setYearModel(resolvedYear);
        }

        if (rawMil !== undefined && rawMil !== null) {
          const m = typeof rawMil === 'number' ? rawMil : parseInt(String(rawMil).replace(/[^\d]/g, ''), 10);
          if (!isNaN(m)) setMileageKm(m);
        }

        // 실시간 엔카 동급 시세 기반 현실적 소매 판매가 세팅 (Streamlit 원본과 100% 동일: 디폴트 0, 임의의 더미값 강제 주입 금지)
        if (cDesiredPrice > 0) {
          setExpectedSellPrice(Math.round(cDesiredPrice * 1.15));
          setTargetMargin(120);
        } else {
          // Streamlit app.py: l_sell_price 기본값 0, 목표마진 기본값 120
          setExpectedSellPrice(0);
          setTargetMargin(120);
        }

        // 외판/사고 요약 자동 감지 (헤이딜러 실측 외판 수리 판수 연동)
        // 1순위: condition_data.basic 에서 type: 'outer_panel_scratch' / label: '외판' 파싱 (예: "2판", "4판")
        let detectedOuterCount: number | null = null;
        const conditionData = detail.condition_data || carData.condition_data || resJson.data?.condition_data;
        if (conditionData?.basic && Array.isArray(conditionData.basic)) {
          const outerItem = conditionData.basic.find((item: any) =>
            item.type === 'outer_panel_scratch' || String(item.label || '').includes('외판')
          );
          if (outerItem) {
            const rawText = String(outerItem.text || outerItem.text_html || '');
            const m = rawText.match(/(\d+)\s*판?/);
            if (m) {
              detectedOuterCount = parseInt(m[1], 10);
            } else if (rawText.includes('없음') || rawText.includes('양호')) {
              detectedOuterCount = 0;
            }
          }
        }

        // 2순위: condition_description 또는 car_description 텍스트에서 '외판 : N판' 파싱
        if (detectedOuterCount === null) {
          const condDesc = String(
            detail.condition_description ||
            carData.condition_description ||
            detail.car_description ||
            carData.car_description ||
            ''
          );
          const outerTextMatch = condDesc.match(/외판\s*[:：]?\s*(\d+)\s*판?/i);
          if (outerTextMatch) {
            detectedOuterCount = parseInt(outerTextMatch[1], 10);
          }
        }

        // 3순위: accident_repairs 목록 (범퍼 제외 실 외판 부위 집계)
        if (detectedOuterCount !== null) {
          setOuterRepairCount(detectedOuterCount);
        } else {
          const repairsList = (detail.accident_repairs && Array.isArray(detail.accident_repairs))
            ? detail.accident_repairs
            : (Array.isArray(carData.accident_repairs) ? carData.accident_repairs : (Array.isArray(resJson.data?.accident_repairs) ? resJson.data.accident_repairs : []));

          if (repairsList.length > 0) {
            const nonBumper = repairsList.filter((r: any) => {
              const p = String(r.part || r.name || '').toLowerCase();
              return !p.includes('bumper') && !p.includes('범퍼');
            });
            setOuterRepairCount(nonBumper.length);
          } else if (cAccident.includes('무사고') && !cAccident.includes('교환')) {
            setOuterRepairCount(0);
          } else if (cAccident.includes('단순교환')) {
            setOuterRepairCount(1);
          } else if (cAccident.includes('유사고') || cAccident.includes('사고')) {
            setOuterRepairCount(3);
          }
        }

        // 경매방식 자동 감지
        if (auction.auction_type) {
          if (auction.auction_type === 'self') setAuctionType('셀프(기본)');
          else if (auction.auction_type.includes('zero')) setAuctionType('제로(탁송/진단)');
        }

        // 🌟 실차주 신차 출고 유료 옵션 (8501과 동일: car_spec.description 우선 파싱 -> advanced_options fallback)
        const specDesc = detail.car_spec?.description || carData.car_spec?.description || resJson.data?.car_spec?.description || '';
        const parsedSpecOpts = parseHeydealerOptions(specDesc);

        const loadedAdvOptions = (detail.advanced_options || [])
          .filter((opt: any) => opt.choice === 'loaded')
          .map((opt: any) => opt.name || opt.content?.option_name)
          .filter(Boolean);

        const finalOpts = parsedSpecOpts.length > 0 ? parsedSpecOpts : loadedAdvOptions;
        const optionsResult = finalOpts.length > 0 ? finalOpts.join(' · ') : '';
        setOptionsTag(optionsResult);

        // 🌟 타겟 차량 보험사고 이력 (carhistory) & 출고정보 정밀 파싱
        const ch = detail.carhistory || carData.carhistory || resJson.data?.carhistory || {};
        const chSum = detail.carhistory_summary || carData.carhistory_summary || resJson.data?.carhistory_summary || {};
        const vi = detail.vehicle_information || carData.vehicle_information || resJson.data?.vehicle_information || {};
        const stdPrice = detail.standard_new_car_price || carData.standard_new_car_price || resJson.data?.standard_new_car_price || 0;

        const ocCount = typeof ch.owner_changed_count === 'number' ? ch.owner_changed_count : (typeof chSum.owner_changed_count === 'number' ? chSum.owner_changed_count : 0);
        const myAccCnt = typeof ch.my_car_accident_count === 'number' ? ch.my_car_accident_count : (typeof chSum.my_car_accident_count === 'number' ? chSum.my_car_accident_count : 0);
        const myAccCost = ch.my_car_accident_cost ? Math.round(Number(ch.my_car_accident_cost) / 10000) : 0;
        const otherAccCnt = typeof ch.other_car_accident_count === 'number' ? ch.other_car_accident_count : (typeof chSum.other_car_accident_count === 'number' ? chSum.other_car_accident_count : 0);
        const otherAccCost = ch.other_car_accident_cost ? Math.round(Number(ch.other_car_accident_cost) / 10000) : 0;
        const totalLoss = ch.total_loss_count || chSum.total_loss_count || 0;
        const flooded = ch.flooded_count || ch.flooded_total_loss_count || chSum.flooded_total_loss_count || 0;
        const stolen = ch.stolen_count || chSum.stolen_count || 0;
        const rentHist = Boolean(ch.has_rent_use_record || (ch.rent_use_record_count && ch.rent_use_record_count > 0));

        setTargetCarHistory({
          ownerChangedCount: ocCount,
          isSingleOwner: ocCount === 0,
          myCarAccidentCount: myAccCnt,
          myCarAccidentCost: myAccCost,
          otherCarAccidentCount: otherAccCnt,
          otherCarAccidentCost: otherAccCost,
          totalLossCount: totalLoss,
          floodedCount: flooded,
          stolenCount: stolen,
          hasRentHistory: rentHist,
          standardNewCarPrice: typeof stdPrice === 'number' ? (stdPrice > 10000 ? Math.round(stdPrice / 10000) : stdPrice) : 0,
          vin: vi.vin || '',
          manufacturedDate: vi.manufactured_date ? String(vi.manufactured_date).slice(0, 10) : '',
          inspectionValidUntil: vi.inspection_valid_until ? String(vi.inspection_valid_until).slice(0, 10) : ''
        });

        // 🌟 [4단계 API 직결] 차올마(오토플러스 ERP) 신차가 & 순정옵션 원본 직결 호출
        if (cNo) {
          try {
            const chRes = await queryChaolmaCar(cNo, rawMil || 50000);
            if (chRes && chRes.success) {
              if (chRes.grade_name) rawGradeNameRef.current = String(chRes.grade_name);
              if (chRes.grade_detail_name) rawGradeDetailNameRef.current = String(chRes.grade_detail_name);
              const rawNewP = chRes.new_car_price || 0;
              const stdP = rawNewP > 10000 ? Math.round(rawNewP / 10000) : rawNewP;
              const rawBaseP = chRes.base_car_price || 0;
              const baseP = rawBaseP > 10000 ? Math.round(rawBaseP / 10000) : rawBaseP;
              const rawOptP = chRes.total_option_price || 0;
              const optP = rawOptP > 10000 ? Math.round(rawOptP / 10000) : rawOptP;

              setTargetCarHistory(prev => {
                const ch = chRes.car_history;
                const doc = chRes.origin_doc;
                if (!prev) {
                  if (ch || doc) {
                    return {
                      ownerChangedCount: ch ? ch.owner_changed_count : 0,
                      isSingleOwner: ch ? ch.is_single_owner : true,
                      myCarAccidentCount: ch ? ch.my_car_accident_count : 0,
                      myCarAccidentCost: ch ? ch.my_car_accident_cost_man : 0,
                      otherCarAccidentCount: ch ? ch.other_car_accident_count : 0,
                      otherCarAccidentCost: ch ? ch.other_car_accident_cost_man : 0,
                      totalLossCount: ch ? ch.total_loss_count : 0,
                      floodedCount: ch ? ch.flooded_count : 0,
                      stolenCount: ch ? ch.stolen_count : 0,
                      hasRentHistory: ch ? ch.has_rent_history : false,
                      standardNewCarPrice: stdP,
                      baseCarPrice: baseP,
                      totalOptionPrice: optP,
                      vin: chRes.vin || (doc ? doc.raw_doc?.VIN : '') || '',
                      manufacturedDate: chRes.release_date || (ch ? ch.first_reg_date : '') || (doc ? doc.first_regist_date : '') || '',
                      inspectionValidUntil: (doc ? doc.inspection_valid_end : '') || (ch ? ch.uninsured_period : '') || '',
                      rawHistory: ch,
                      originDoc: doc
                    };
                  }
                  return prev;
                }
                return {
                  ...prev,
                  standardNewCarPrice: stdP > 0 ? stdP : prev.standardNewCarPrice,
                  baseCarPrice: baseP > 0 ? baseP : prev.baseCarPrice,
                  totalOptionPrice: optP > 0 ? optP : prev.totalOptionPrice,
                  vin: chRes.vin || (doc ? doc.raw_doc?.VIN : '') || prev.vin || '',
                  manufacturedDate: chRes.release_date || (ch ? ch.first_reg_date : '') || (doc ? doc.first_regist_date : '') || prev.manufacturedDate || '',
                  ownerChangedCount: (prev.ownerChangedCount === 0 && ch && ch.owner_changed_count > 0) ? ch.owner_changed_count : prev.ownerChangedCount,
                  isSingleOwner: (ch && !ch.is_single_owner) ? false : prev.isSingleOwner,
                  myCarAccidentCount: (prev.myCarAccidentCount === 0 && ch && ch.my_car_accident_count > 0) ? ch.my_car_accident_count : prev.myCarAccidentCount,
                  myCarAccidentCost: (prev.myCarAccidentCost === 0 && ch && ch.my_car_accident_cost_man > 0) ? ch.my_car_accident_cost_man : prev.myCarAccidentCost,
                  otherCarAccidentCount: (prev.otherCarAccidentCount === 0 && ch && ch.other_car_accident_count > 0) ? ch.other_car_accident_count : prev.otherCarAccidentCount,
                  otherCarAccidentCost: (prev.otherCarAccidentCost === 0 && ch && ch.other_car_accident_cost_man > 0) ? ch.other_car_accident_cost_man : prev.otherCarAccidentCost,
                  totalLossCount: (ch && ch.total_loss_count > 0) ? ch.total_loss_count : prev.totalLossCount,
                  floodedCount: (ch && ch.flooded_count > 0) ? ch.flooded_count : prev.floodedCount,
                  stolenCount: (ch && ch.stolen_count > 0) ? ch.stolen_count : prev.stolenCount,
                  hasRentHistory: (ch && ch.has_rent_history) ? true : prev.hasRentHistory,
                  inspectionValidUntil: (doc ? doc.inspection_valid_end : '') || prev.inspectionValidUntil || (ch ? ch.uninsured_period : '') || '',
                  rawHistory: ch || prev.rawHistory,
                  originDoc: doc || prev.originDoc
                };
              });

              // 차올마 순정옵션이 있으면 옵션태그를 카탈로그 기준 표준 옵션명(출고가 포함)으로 정확히 교체 (중복 방지)
              if (chRes.options && chRes.options.length > 0) {
                const cat = await fetchNewCarCatalog(chRes.model_detail_name || chRes.model_name || carData.car_name, (chRes as any).model_year || chRes.year);
                if (cat) setTargetNewCarCatalog(cat);
                const normalized = normalizeChaolmaOptions(chRes.options, cat);
                const optStr = normalized.map(o => `${o.standardName}(${o.standardPriceMan}만)`).join(' · ');
                const totalOptMan = normalized.reduce((acc, cur) => acc + cur.standardPriceMan, 0);
                setOptionsTag(`${optStr} [순정옵션총액: ${totalOptMan}만]`);
              }
            }
          } catch (chErr) {
            console.warn('차올마 백그라운드 직결 조회 중 오류 (정상 진행):', chErr);
          }
        }

        // 🌟 헤이딜러 동급 20대 낙찰가 데이터 저장
        const rawMp = carData.market_prices || resJson.data?.market_prices || resJson.market_prices;
        if (rawMp) {
          const compList = Array.isArray(rawMp) ? rawMp : (rawMp.results || []);
          if (Array.isArray(compList) && compList.length > 0) {
            setRawHeydealerComps(compList);
          }
        }

        // 🌟 엔카 실시간 동급 매물 시세 자동 수집 트리거 (Heydealer etc.external_url.encar 기반)
        const directEncarUrl = detail.etc?.external_url?.encar || 
                               resJson.data?.etc?.external_url?.encar || 
                               resJson.raw?.etc?.external_url?.encar || 
                               resJson.data?.detail?.etc?.external_url?.encar || '';
        
        let calculatedYear = resolvedYear || 20;
        if (!calculatedYear && rawYear !== undefined && rawYear !== null) {
          let y = typeof rawYear === 'number' ? rawYear : parseInt(String(rawYear).match(/\d+/)?.[0] || '20', 10);
          if (y > 2000) y -= 2000;
          calculatedYear = y;
        }

        let calculatedMil = 0;
        if (rawMil !== undefined && rawMil !== null) {
          const m = typeof rawMil === 'number' ? rawMil : parseInt(String(rawMil).replace(/[^\d]/g, ''), 10);
          if (!isNaN(m)) calculatedMil = m;
        }

        setAiEstimateStep(`엔카 실시간 동급 매물 수집 중... [${cBrand} ${cName}]`);
        let fetchedItems: any[] = [];

        if (directEncarUrl) {
          setEncarSourceUrl(directEncarUrl);
          fetchedItems = await fetchEncarComparable({
            url: directEncarUrl,
            carName: cName,
            detailModel: cGrade,
            gradeName: rawGradeNameRef.current,
            gradeDetailName: rawGradeDetailNameRef.current,
            manufacturer: cBrand,
            year: calculatedYear,
            mileage: calculatedMil
          });
        } else if (cName) {
          fetchedItems = await fetchEncarComparable({
            carName: cName,
            detailModel: cGrade,
            gradeName: rawGradeNameRef.current,
            gradeDetailName: rawGradeDetailNameRef.current,
            manufacturer: cBrand,
            year: calculatedYear,
            mileage: calculatedMil
          });
        }

        fetchKcarMarket({
          carName: cName,
          detailModel: cGrade,
          gradeName: rawGradeNameRef.current,
          gradeDetailName: rawGradeDetailNameRef.current,
          manufacturer: cBrand,
          year: calculatedYear,
          mileage: calculatedMil,
        });

        if (fetchedItems.length === 0) {
          const reasonSuffix = lastEncarFailReasonRef.current ? ` (원인: ${lastEncarFailReasonRef.current})` : '';
          setSearchStatus({
            type: 'warning',
            message: `⚠️ 엔카 매물을 가져오지 못했습니다. (${cNo} ${cName})${reasonSuffix}`
          });
        } else {
          setSearchStatus({
            type: 'success',
            message: `🎉 [헤이딜러 & 엔카 실시간 연동 완료] ${cNo} ${cName} (${(rawMil || 0).toLocaleString()}km${cAccident ? ` / ${cAccident}` : ''}) (동급 ${fetchedItems.length}대 연동)`
          });
        }
      } else {
        setSearchStatus({
          type: 'warning',
          message: '⚠️ 헤이딜러 응답을 받았으나 차량 세부 제원을 추출하지 못했습니다. 차량번호로 재검색을 권장합니다.'
        });
      }
    } catch (err: any) {
      console.error('헤이딜러 조회 실패:', err);
      setSearchStatus({
        type: 'error',
        message: `❌ 헤이딜러 연동 오류: ${err?.message || '네트워크 통신 오류가 발생했습니다.'}`
      });
    } finally {
      setIsAiEstimating(false);
      setAiEstimateStep(null);
    }
  };

  // ----------------------------------------------------
  // [2단계. 동급매물 (엔카) 데이터] - 실시간 엔카 API 연동 데이터 (8501 콕핏과 100% 동일 정렬)
  // ----------------------------------------------------
  const encarList: EncarItem[] = useMemo(() => {
    if (!liveEncarList || liveEncarList.length === 0) {
      return [];
    }

    // 🌟 중복 매물 정밀 제거 (Deduplication: ID 중복 및 동일 실물 매물 중복 배제)
    const seenIds = new Set<string>();
    const seenSpecs = new Set<string>();
    const dedupedList: EncarItem[] = [];

    for (const item of liveEncarList) {
      if (!item) continue;
      // 1. 매물 ID (_carid / id) 기준 중복 제거
      const rawId = String(item.id || (item as any)._carid || '').trim();
      const cleanId = rawId.replace(/\D/g, '');
      if (cleanId) {
        if (seenIds.has(cleanId)) continue;
        seenIds.add(cleanId);
      } else if (rawId) {
        if (seenIds.has(rawId)) continue;
        seenIds.add(rawId);
      }

      // 2. 실물 매물 (스트림릿 기준: 차량명 + 연식 + 주행거리 + 가격) 중복 제거 (딜러 중복등록 차단)
      const carName = String(item.carName || item.modelName || '').trim();
      const yrMatch = String(item.year || '').match(/\d{2}/)?.[0] || '';
      const milVal = Number(item.mileage || 0);
      const priceVal = Number(item.price || 0);
      if (milVal > 0 && priceVal > 0) {
        const specKey = `${carName}_${yrMatch}_${milVal}_${priceVal}`;
        if (seenSpecs.has(specKey)) continue;
        seenSpecs.add(specKey);
      }

      dedupedList.push(item);
    }

    // 백엔드 확정 기준 정렬 (Phase 3: 단일 진실 공급원):
    // 1. 점검 유무(등록 우선) -> 2. 점검일 최신순 -> 3. 가격 낮은순 -> 4. 연식 최신순
    return dedupedList.sort(compareEncarItemsByBackendRule);
  }, [liveEncarList, carName, detailModel, expectedSellPrice, yearModel, mileageKm, optionsTag]);

  // (selectedEncarId, selectedInspectionMap, isInspectionLoading, isEncarSoldOpen 상태는 호이스팅 방지를 위해 상단 배치됨)

  // 🚨 [5순위 UX 혼동 방지]: 조회 차량과 비교 매물이 섞이지 않도록, 엔카 매물 로드 시 1위 매물 자동선택을 완전히 제거합니다.
  // (사용자가 비교 매물 테이블의 행을 직접 클릭했을 때만 해당 매물의 상세 스펙 및 2D 점검표가 열립니다.)
  useEffect(() => {
    setSelectedEncarId('');
  }, [carName, detailModel, yearModel, carNumber]);

  // 🚀 [사전 프리패치(Prefetch)]: 엔카 매물 목록이 준비되면 백그라운드에서 상위 매물들의 성능점검표/신차가격을 순차 로드
  // 사용자가 테이블 행을 클릭하는 순간 지연 없이(0.0초) 즉각 렌더링되도록 사전 캐싱합니다.
  useEffect(() => {
    if (!encarList || encarList.length === 0) return;

    let isCancelled = false;
    const prefetchList = encarList.slice(0, 30); // 상위 30대 우선 프리패치

    const runPrefetch = async () => {
      for (const car of prefetchList) {
        if (isCancelled) break;
        const carId = car.id;
        if (!carId) continue;

        // 이미 캐시(ref)에 있으면 스킵
        if (selectedInspectionMapRef.current[carId]) continue;

        try {
          const res = await fetch(`/api/encar/inspection/${carId}`);
          if (isCancelled) break;
          const data = await res.json();
          if (data.success && data.data && !isCancelled) {
            selectedInspectionMapRef.current[carId] = data.data;
            setSelectedInspectionMap(prev => ({
              ...prev,
              [carId]: data.data
            }));
          }
        } catch (e) {
          // 백그라운드 프리패치는 무음 처리
        }

        // 브라우저 렌더링 프레임 및 네트워크 여유를 위해 100ms 지연
        await new Promise(r => setTimeout(r, 100));
      }
    };

    runPrefetch();

    return () => {
      isCancelled = true;
    };
  }, [encarList]);

  // 행 클릭 시 성능점검표 및 상세 옵션 즉시 호출
  const handleSelectEncarCar = async (carId: string) => {
    if (!carId) return;
    setSelectedEncarId(carId);

    // 이미 프리패치되어 캐시에 있으면 네트워크 대기 없이 즉시 표시 (0ms 지연)
    if (selectedInspectionMapRef.current[carId] || selectedInspectionMap[carId]) {
      return;
    }

    setIsInspectionLoading(true);
    try {
      const res = await fetch(`/api/encar/inspection/${carId}`);
      const data = await res.json();
      if (data.success && data.data) {
        selectedInspectionMapRef.current[carId] = data.data;
        setSelectedInspectionMap(prev => ({
          ...prev,
          [carId]: data.data
        }));
      }
    } catch (e) {
      console.warn('엔카 성능점검표 조회 실패:', e);
    } finally {
      setIsInspectionLoading(false);
    }
  };

  const selectedEncar: EncarItem | null = useMemo(() => {
    const found = selectedEncarId ? (encarList.find(c => c.id === selectedEncarId) || null) : null;
    if (!found) {
      return null;
    }

    const insp = selectedInspectionMap[found.id];
    if (insp) {
      const parsedReplaces: string[] = Array.isArray(insp.replaces) && insp.replaces.length > 0 ? [...insp.replaces] : [];
      const parsedRepairs: string[] = Array.isArray(insp.repairs) && insp.repairs.length > 0 ? [...insp.repairs] : [];
      const replaceNames: string[] = Array.isArray(insp.replaceNames) && insp.replaceNames.length > 0 ? [...insp.replaceNames] : [];
      const repairNames: string[] = Array.isArray(insp.repairNames) && insp.repairNames.length > 0 ? [...insp.repairNames] : [];
      
      const rawPartsList = [
        ...(Array.isArray(insp.outers) ? insp.outers : []),
        ...(Array.isArray(insp.inners) ? insp.inners : []),
        ...(Array.isArray(insp.outerPanels) ? insp.outerPanels : []),
        ...(Array.isArray(insp.panels) ? insp.panels : [])
      ];

      if (rawPartsList.length > 0) {
        rawPartsList.forEach((p: any) => {
          const name = String(p.type?.title || p.panelName || p.name || p.partName || '').trim();
          const statuses = p.statusTypes || [];
          const stateCodes = Array.isArray(statuses) ? statuses.map((s: any) => String(s.code || '').toUpperCase()) : [];
          const state = String(p.status || p.type || p.repairType || '').toUpperCase();
          const isReplace = stateCodes.includes('X') || state.includes('교환') || state.includes('X') || state === '1';
          const isRepair = stateCodes.some((c: string) => ['W', 'C', 'A', 'U', 'T'].includes(c)) || state.includes('판금') || state.includes('용접') || state.includes('W') || state === '2';

          let mappedPart = '';
          if (name.includes('후드') || name.includes('본넷')) mappedPart = 'HOOD';
          else if (name.includes('앞휀더(좌)') || name.includes('프론트 휀더(좌)') || name.includes('프론트휀더(좌)')) mappedPart = 'F_FENDER_L';
          else if (name.includes('앞휀더(우)') || name.includes('프론트 휀더(우)') || name.includes('프론트휀더(우)')) mappedPart = 'F_FENDER_R';
          else if (name.includes('앞도어(좌)') || name.includes('프론트 도어(좌)') || name.includes('프론트도어(좌)')) mappedPart = 'FRONT_DOOR_L';
          else if (name.includes('앞도어(우)') || name.includes('프론트 도어(우)') || name.includes('프론트도어(우)')) mappedPart = 'FRONT_DOOR_R';
          else if (name.includes('뒤도어(좌)') || name.includes('리어 도어(좌)') || name.includes('리어도어(좌)')) mappedPart = 'REAR_DOOR_L';
          else if (name.includes('뒤도어(우)') || name.includes('리어 도어(우)') || name.includes('리어도어(우)')) mappedPart = 'REAR_DOOR_R';
          else if (name.includes('쿼터') && name.includes('좌')) mappedPart = 'QUARTER_L';
          else if (name.includes('쿼터') && name.includes('우')) mappedPart = 'QUARTER_R';
          else if (name.includes('사이드실') && name.includes('좌')) mappedPart = 'SIDE_SILL_L';
          else if (name.includes('사이드실') && name.includes('우')) mappedPart = 'SIDE_SILL_R';
          else if (name.includes('루프')) mappedPart = 'ROOF';
          else if (name.includes('트렁크')) mappedPart = 'TRUNK';
          else if (name.includes('라디에이터')) mappedPart = 'RADIATOR_SUPPORT';
          else if (name.includes('인사이드') && name.includes('좌')) mappedPart = 'INSIDE_PANEL_L';
          else if (name.includes('인사이드') && name.includes('우')) mappedPart = 'INSIDE_PANEL_R';
          else if (name.includes('크로스')) mappedPart = 'CROSS_MEMBER';
          else if (name.includes('프론트 패널') || name.includes('프론트패널')) mappedPart = 'FRONT_PANEL';
          else if (name.includes('사이드 멤버') && name.includes('좌')) mappedPart = 'FRONT_SIDE_MEMBER_L';
          else if (name.includes('사이드 멤버') && name.includes('우')) mappedPart = 'FRONT_SIDE_MEMBER_R';
          else if (name.includes('휠하우스') && name.includes('좌')) mappedPart = 'FRONT_WHEEL_HOUSE_L';
          else if (name.includes('휠하우스') && name.includes('우')) mappedPart = 'FRONT_WHEEL_HOUSE_R';
          else if (name.includes('리어 패널') || name.includes('리어패널')) mappedPart = 'REAR_PANEL';
          else if (name.includes('트렁크 플로어') || name.includes('트렁크플로어')) mappedPart = 'TRUNK_FLOOR';
          else if (name.includes('A필러') && name.includes('좌')) mappedPart = 'A_PILLAR_L';
          else if (name.includes('A필러') && name.includes('우')) mappedPart = 'A_PILLAR_R';
          else if (name.includes('B필러') && name.includes('좌')) mappedPart = 'B_PILLAR_L';
          else if (name.includes('B필러') && name.includes('우')) mappedPart = 'B_PILLAR_R';
          else if (name.includes('C필러') && name.includes('좌')) mappedPart = 'C_PILLAR_L';
          else if (name.includes('C필러') && name.includes('우')) mappedPart = 'C_PILLAR_R';

          if (isReplace) {
            if (mappedPart) parsedReplaces.push(mappedPart);
            if (name) replaceNames.push(name);
          } else if (isRepair) {
            if (mappedPart) parsedRepairs.push(mappedPart);
            if (name) repairNames.push(name);
          }
        });
      }

      const inspColor = insp.color || found.color;
      // 🌟 상세 성능점검 데이터가 로드되면 상세 점검 결과(insp.accidentType, insp.inspectionDate)를 최우선 적용
      const inspDate = insp.inspectionDate && insp.inspectionDate !== '-' 
        ? insp.inspectionDate 
        : (found.checkDate && found.checkDate !== '-' ? found.checkDate : (insp.checkDate || found.checkDate));
      
      const inspAccident = insp.accidentType && insp.accidentType !== '-' && insp.accidentType !== '미확인'
        ? insp.accidentType
        : (found.accidentType && found.accidentType !== '-' ? found.accidentType : '미확인');

      const inspOpts = insp.optionsText || (insp.options ? insp.options.join(' · ') : (insp.optionNames ? insp.optionNames.join(' · ') : found.optionsText));

      return {
        ...found,
        color: inspColor || found.color,
        checkDate: inspDate || found.checkDate,
        inspectionDate: inspDate || (found as any).inspectionDate || '-',
        registrationDate: insp.registrationDate || (found as any).registrationDate || '-',
        accidentType: inspAccident || found.accidentType,
        optionsText: inspOpts || found.optionsText,
        replaces: parsedReplaces.length > 0 ? Array.from(new Set(parsedReplaces)) : (found.replaces || []),
        repairs: parsedRepairs.length > 0 ? Array.from(new Set(parsedRepairs)) : (found.repairs || []),
        replaceNames: replaceNames.length > 0 ? Array.from(new Set(replaceNames)) : (Array.isArray(insp.replaceNames) ? insp.replaceNames : []),
        repairNames: repairNames.length > 0 ? Array.from(new Set(repairNames)) : (Array.isArray(insp.repairNames) ? insp.repairNames : []),
        damageData: insp.damageData || (found as any).damageData || {},
        originPrice: insp.originPrice ?? (found as any).originPrice ?? 0,
        optionPrice: insp.optionPrice ?? (found as any).optionPrice ?? 0,
        newCarPrice: insp.newCarPrice ?? (found as any).newCarPrice ?? 0,
      };
    }

    return found;
  }, [selectedEncarId, encarList, selectedInspectionMap, carName, yearModel, mileageKm, expectedSellPrice]);

  // ----------------------------------------------------
  // [4단계. 헤이딜러 낙찰 데이터 20대 - 실데이터 파싱 및 정밀 통계]
  // ----------------------------------------------------
  const heydealerBids: HeydealerBidItem[] = useMemo(() => {
    if (rawHeydealerComps && rawHeydealerComps.length > 0) {
      return rawHeydealerComps.map((item: any, idx: number) => {
        const d = item.detail || item;
        const auc = item.auction || {};
        const bid = auc.highest_bid || {};
        const price = Number(bid.price) || Number(item.price) || 0;
        const mil = Number(d.mileage) || 0;
        const yr = Number(d.year) || 0;
        const yrStr = yr > 0 ? `${yr}년` : '-';

        const repairs = Array.isArray(d.accident_repairs) ? d.accident_repairs : [];
        const parsedRepairs = repairs.map((rep: any) => {
          const p = rep.part || rep.part_name || '';
          const t = rep.repair || rep.type_name || '';
          const pKr = HD_PART_MAP[p] || p || '기타부위';
          const tKr = HD_REPAIR_MAP[t] || t || '교환';
          return { part: pKr, repair: tKr, desc: `${pKr} (${tKr})` };
        });

        const tags = Array.isArray(auc.tags) ? auc.tags : [];
        const tagTexts = tags
          .map((t: any) => (typeof t === 'string' ? t : t?.short_text || ''))
          .filter((t: string) => t && !['재경매', '연장'].includes(t));

        let baseAcc = tagTexts.length > 0 ? tagTexts.join(' ') : (d.accident_repairs_summary_display || d.accident_repairs_summary || '완무');
        const compCh = d.carhistory || item.carhistory || {};
        const compOc = typeof compCh.owner_changed_count === 'number' ? compCh.owner_changed_count : null;
        if (compOc === 0 && !baseAcc.includes('1인소유')) {
          baseAcc += ' 1인소유';
        }

        let accType: '완전무사고' | '단순수리' | '유사고' = '단순수리';
        if (baseAcc.includes('완무') || baseAcc.includes('완전무사고') || baseAcc.includes('무사고')) {
          accType = '완전무사고';
        } else if (baseAcc.includes('유사고') || baseAcc.includes('사고')) {
          accType = '유사고';
        }

        const specDesc = String(d.car_spec?.description || item.car_spec?.description || d.spec_description || item.spec_description || '');
        const parsedSpecOpts = parseHeydealerOptions(specDesc);

        const advOpts = Array.isArray(d.advanced_options)
          ? d.advanced_options.filter((o: any) => o.choice === 'loaded').map((o: any) => o.name || o.content?.option_name).filter(Boolean)
          : [];

        const finalHdOpts = parsedSpecOpts.length > 0 ? parsedSpecOpts : advOpts;
        const isExport = Boolean(bid.is_export || bid.is_export_dealer || auc.is_export || baseAcc.includes('수출') || price < 300);
        const bidDateStr = formatHdRelativeDate(item);
        const carHashId = String(item.id || item.car_id || item.hash_id || '').trim();
        const hdDirectLink = carHashId ? `https://dealer.heydealer.com/cars/${carHashId}` : '';

        return {
          id: String(item.id || item.car_id || `hd_bid_${idx}`),
          model: String(d.grade_part_name || d.model_part_name || `${carName} ${detailModel}`).trim(),
          year: yrStr,
          yearNum: yr,
          mileage: mil,
          bidPrice: price,
          bidDate: bidDateStr,
          accident: baseAcc,
          accidentType: accType,
          options: finalHdOpts.length > 0 ? finalHdOpts.join(' · ') : '-',
          isExport,
          repairs: parsedRepairs,
          keyOptions: finalHdOpts,
          link: hdDirectLink
        };
      });
    }

    // 🌟 실데이터 미수신 시 가짜/가상 데이터 생성 금지 (검증된 실데이터만 표시)
    return [];
  }, [rawHeydealerComps, carName, detailModel, expectedSellPrice, yearModel, mileageKm]);

  // 헤이딜러 세부등급 목록 및 타겟 차종 최적 매칭 등급 (Streamlit tab_main.py L1710-L1728 100% 동일 구현)
  const { availableHeydealerGrades, bestMatchHeydealerGrade, heydealerGradeCounts } = useMemo(() => {
    const counts: Record<string, number> = {};
    heydealerBids.forEach(b => {
      const g = b.model || '기타';
      counts[g] = (counts[g] || 0) + 1;
    });

    const grades = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
    let bestMatch: string | null = null;

    if (detailModel) {
      const cleanTarget = detailModel.replace(/\s+/g, '').toLowerCase();
      bestMatch = grades.find(g => {
        const cleanG = g.replace(/\s+/g, '').toLowerCase();
        return cleanG.includes(cleanTarget) || cleanTarget.includes(cleanG);
      }) || null;
    }

    if (!bestMatch && grades.length > 0) {
      bestMatch = grades[0];
    }

    return {
      availableHeydealerGrades: grades,
      bestMatchHeydealerGrade: bestMatch,
      heydealerGradeCounts: counts
    };
  }, [heydealerBids, detailModel]);

  // 등급 필터 초기값 자동 세팅 (최적 매칭 등급 우선)
  useEffect(() => {
    if (bestMatchHeydealerGrade && selectedHeydealerGradeFilter === 'ALL') {
      setSelectedHeydealerGradeFilter(bestMatchHeydealerGrade);
    }
  }, [bestMatchHeydealerGrade]);

  // 선택된 등급에 따라 정밀 필터링된 헤이딜러 낙찰 목록
  const filteredHeydealerBids = useMemo(() => {
    if (selectedHeydealerGradeFilter === 'ALL' || !selectedHeydealerGradeFilter) {
      return heydealerBids;
    }
    return heydealerBids.filter(b => b.model === selectedHeydealerGradeFilter || b.model.includes(selectedHeydealerGradeFilter));
  }, [heydealerBids, selectedHeydealerGradeFilter]);

  // 선택된 헤이딜러 낙찰 차량
  const selectedHeydealerBid = useMemo(() => {
    if (selectedHeydealerBidId) {
      const found = filteredHeydealerBids.find(b => b.id === selectedHeydealerBidId);
      if (found) return found;
    }
    return filteredHeydealerBids[0] || null;
  }, [selectedHeydealerBidId, filteredHeydealerBids]);

  // 헤이딜러 4개 메트릭 및 AI 판단 매입가 요약 통계 (순수 내수 기준 100% 실측 일치)
  const heydealerSummary = useMemo(() => {
    const totalCount = filteredHeydealerBids.length;
    if (totalCount === 0) {
      return {
        hasData: false,
        totalCount: 0,
        domCount: 0,
        exportCount: 0,
        minPrice: 0,
        maxPrice: 0,
        avgPrice: 0,
        noAccAvg: 0,
        accAvg: 0,
        avgMil: 0,
        milAdj: 0,
        optAdj: 0,
        aiWholesalePrice: 0
      };
    }

    const domesticBids = filteredHeydealerBids.filter(b => !b.isExport);
    const targetBids = domesticBids.length > 0 ? domesticBids : filteredHeydealerBids;
    const domCount = domesticBids.length;
    const exportCount = totalCount - domCount;

    const prices = targetBids.map(b => b.bidPrice).filter(p => p > 0);
    const minPrice = prices.length > 0 ? Math.min(...prices) : 0;
    const maxPrice = prices.length > 0 ? Math.max(...prices) : 0;
    const avgPrice = prices.length > 0 ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) : 0;

    // 무사고 vs 유사고 평균
    const noAccBids = targetBids.filter(b => b.accidentType === '완전무사고');
    const accBids = targetBids.filter(b => b.accidentType !== '완전무사고');
    const noAccAvg = noAccBids.length > 0 ? Math.round(noAccBids.reduce((a, b) => a + b.bidPrice, 0) / noAccBids.length) : avgPrice;
    const accAvg = accBids.length > 0 ? Math.round(accBids.reduce((a, b) => a + b.bidPrice, 0) / accBids.length) : avgPrice;

    // AI 판단 매입가 (주행거리 + 옵션 보정)
    const avgMil = targetBids.length > 0 ? Math.round(targetBids.reduce((a, b) => a + b.mileage, 0) / targetBids.length) : mileageKm;
    const milDiff = mileageKm - avgMil;
    const milSlope = -0.005; // 1만km당 약 50만원 감가
    const milAdj = Math.round(milDiff * milSlope);

    // 옵션 보정: 엔카 API 산출된 정밀 옵션가치 보정 사용
    let optAdj = backendEncarStats?.optAdj || 0;

    const aiWholesalePrice = Math.max(10, avgPrice + milAdj + optAdj);

    return {
      hasData: true,
      totalCount,
      domCount,
      exportCount,
      minPrice,
      maxPrice,
      avgPrice,
      noAccAvg,
      accAvg,
      avgMil,
      milAdj,
      optAdj,
      aiWholesalePrice
    };
  }, [filteredHeydealerBids, mileageKm, optionsTag, backendEncarStats]);

  // S6: scatterPlotData useMemo 및 SVG 렌더링은 ScatterPlotSection 컴포넌트 내부로 캡슐화 이전됨

  // ----------------------------------------------------
  // [1단계. 오토플러스 실적 DB & 탭 상태]
  // ----------------------------------------------------
  const [soldTabMode, setSoldTabMode] = useState<'encar' | 'autoplus' | 'wholesale' | 'none'>('none');

  // ----------------------------------------------------
  // [1단계. 자사 오토플러스 실적 및 시장 수요도 - Streamlit 8501 100% 동일 API 연동]
  // (liveMarketStats 상태는 호이스팅 방지를 위해 상단 배치됨)

  const fetchMarketStats = useCallback(async (cName?: string, dModel?: string, yModel?: number) => {
    const targetCName = cName || carName;
    if (!targetCName) return;
    const targetDModel = dModel !== undefined ? dModel : detailModel;
    const targetYModel = yModel !== undefined ? yModel : yearModel;

    try {
      const fullYr = typeof targetYModel === 'number' 
        ? (targetYModel > 0 ? (targetYModel > 2000 ? targetYModel : 2000 + targetYModel) : '')
        : (targetYModel || '');
      const res = await fetch(`/api/market_statistics?car_name=${encodeURIComponent(targetCName)}&sub_model=${encodeURIComponent(targetDModel || '')}&year=${encodeURIComponent(String(fullYr))}`);
      if (res.ok) {
        const json = await res.json();
        if (json.success && json.data) {
          setLiveMarketStats(json.data);
        }
      }
    } catch (e) {
      console.warn('Market stats fetch failed:', e);
    }
  }, [carName, detailModel, yearModel]);

  useEffect(() => {
    if (!carName) return;
    fetchMarketStats(carName, detailModel, yearModel);
  }, [carName, detailModel, yearModel, fetchMarketStats]);

  const matchedAutoplusList = useMemo(() => {
    if (liveMarketStats && Array.isArray(liveMarketStats.sample_list)) {
      return liveMarketStats.sample_list;
    }
    return [];
  }, [liveMarketStats]);

  const matchedAuctionList = useMemo(() => {
    if (liveMarketStats && Array.isArray(liveMarketStats.auction_sample_list)) {
      return liveMarketStats.auction_sample_list;
    }
    return [];
  }, [liveMarketStats]);

  // 자사 오토플러스 실적 통계 (8501 SalesDataAnalyzer 결과 100% 일치)
  const autoplusStats = useMemo(() => {
    if (liveMarketStats && liveMarketStats.has_data && liveMarketStats.total_count > 0) {
      return {
        matchedCount: liveMarketStats.total_count,
        avgStockDays: liveMarketStats.avg_days || 0,
        avgPastSellPrice: liveMarketStats.avg_sell_price || 0,
        avgPastMileage: liveMarketStats.avg_mileage || 0,
        avgMargin: liveMarketStats.avg_profit || 0,
        marginPct: String(liveMarketStats.profit_rate || '0.0'),
        matchedName: liveMarketStats.matched_name || carName,
        matchedTier: liveMarketStats.matched_tier || ''
      };
    }

    return {
      matchedCount: 0,
      avgStockDays: 0,
      avgPastSellPrice: 0,
      avgPastMileage: 0,
      avgMargin: 0,
      marginPct: '0.0',
      matchedName: '',
      matchedTier: ''
    };
  }, [liveMarketStats, carName]);

  // ----------------------------------------------------
  // [1단계. 엔카 최근 판매완료(광고종료 팔린매물) 실거래 DB - 8501 SoldOutTracker 실측 100% 일치]
  // ----------------------------------------------------
  const encarSoldList: EncarSoldItem[] = useMemo(() => {
    if (liveEncarSoldStats?.enriched_cars && liveEncarSoldStats.enriched_cars.length > 0) {
      return liveEncarSoldStats.enriched_cars.map((c: any, idx: number) => {
        const cleanId = String(c.id || c.carid || c.carId || '').replace(/\D/g, '');
        const directUrl = c.encarUrl || (cleanId ? `https://fem.encar.com/cars/detail/${cleanId}` : '');
        const milNum = Number(c.mileage || c.km_num || 0);
        const pNum = Number(c.price || c.finalPrice || c.soldPrice || 0);
        const fullCarName = c.name || c.carName || `${carName} ${detailModel}`.trim();
        return {
          id: cleanId ? `enc-sold-${cleanId}` : `es-${idx}`,
          carId: cleanId,
          carName: fullCarName,
          subModel: c.subModel || c.badge || '',
          year: String(c.year || yearModel),
          mileage: milNum,
          finalPrice: pNum,
          daysTaken: Number(c.holding_days || c.daysTaken || 0),
          soldDate: String(c.sold_date || c.soldDate || liveEncarSoldStats.latest_sold_date || '-'),
          accident: String(c.accident || c.accidentType || '미확인'),
          encarUrl: directUrl,
          saleType: c.saleType || c.category || c.badge || '-'
        };
      });
    }

    return [];
  }, [liveEncarSoldStats, carName, detailModel, yearModel]);

  // 🎯 AI 종합 비딩 전략 판정 (Streamlit tab_main.py L241-L305 100% 동일 구현)
  const biddingVerdict = useMemo(() => {
    if (!carName) return null;
    const bdCnt = autoplusStats.matchedCount || 0;
    const bdDays = autoplusStats.avgStockDays || 0;
    const encar30d = liveEncarSoldStats?.count_30d || 0;
    const hasAutoplus = bdCnt > 0;

    let badge = "🟢 정상 유통 회전 (표준 입찰)";
    let badgeColor = "#4ade80";
    let mainText = `엔카 시장(월 ${encar30d}대 출고)에서 꾸준히 소화되는 정상 유통 차종입니다.`;
    let recommendation = "표준 입찰 추천 (기본 기대마진 150~180만 원 확보)";

    if (encar30d >= 15) {
      badge = "⚡ 시장 초고속 완판 (적극 매입)";
      badgeColor = "#38bdf8";
      mainText = `엔카 시장에서 최근 30일간 <b>${encar30d}대</b>가 완판(일평균 ${(encar30d / 30).toFixed(1)}대 출고)되는 초인기 차종으로 회전이 매우 빠릅니다.`;
      recommendation = "적극 입찰 권장 (기본 기대마진 140~170만 원 확보, 빠른 회전으로 현금화 유리)";
    } else if (encar30d >= 8) {
      badge = "🟢 정상 유통 회전 (표준 입찰)";
      badgeColor = "#4ade80";
      mainText = `엔카 시장에서 최근 30일간 <b>${encar30d}대</b>가 완판되는 정상 유통 차종입니다.`;
      recommendation = "표준 입찰 권장 (기본 기대마진 150~180만 원 확보)";
    } else if (encar30d > 0) {
      badge = "🟡 소화 속도 완만 (신중 입찰)";
      badgeColor = "#facc15";
      mainText = `엔카 시장 최근 30일 완판이 <b>${encar30d}대</b>로 유통 속도가 완만합니다.`;
      recommendation = "신중 입찰 권장 (안전마진 180~220만 원 이상 확보 후 입찰)";
    } else if (hasAutoplus && bdCnt >= 3) {
      if (bdDays <= 20 && bdCnt >= 3) {
        badge = "⚡ 빠른 회전 (공격 입찰)";
        badgeColor = "#38bdf8";
        mainText = `자사 소매 평균 ${Math.round(bdDays)}일 만에 완판되는 빠른 회전 효자 차종입니다.`;
        recommendation = "공격적 입찰 추천 (기대마진 100~130만 원)";
      } else if (bdDays <= 40) {
        badge = "🟢 정상 재고 (표준 입찰)";
        badgeColor = "#4ade80";
        mainText = `자사 소매 평균 ${Math.round(bdDays)}일 소요되는 정상 유통 차종입니다.`;
        recommendation = "표준 입찰 추천 (기본 기대마진 150~180만 원)";
      } else if (bdDays <= 60) {
        badge = "🟡 장기 재고 주의 (신중 입찰)";
        badgeColor = "#facc15";
        mainText = `자사 소매 평균 ${Math.round(bdDays)}일 소요로 40일을 초과하는 장기 재고 진입 차종입니다.`;
        recommendation = "신중 입찰 권장 (안전마진 200~250만 원)";
      } else {
        badge = "🔴 악성 재고 주의 (방어적 입찰)";
        badgeColor = "#ef4444";
        mainText = `소매 평균 재고일 ${Math.round(bdDays)}일로 60일을 초과한 악성 재고 주의 차종입니다.`;
        recommendation = "방어적 입찰 필수 (가격 하락 방어 위해 마진 280~350만 원 이상 확보)";
      }
    }

    return { badge, badgeColor, mainText, recommendation };
  }, [carName, autoplusStats, liveEncarSoldStats]);

  // 엔카 동급 매물 통계 (최저가, 최고가, 평균가, 중앙값, 매물수 - Streamlit 8501 int(mean) 방식 100% 동일)
  const encarStats = useMemo(() => {
    if (!encarList.length) {
      return {
        count: 0, min: 0, max: 0, avg: 0, median: 0,
        strictAdjAvg: 0, strictAdjMin: 0, strictAdjMedian: 0, strictAdjMax: 0,
        strictAdjCount: 0, strictAdjExcludedCount: 0
      };
    }
    const prices = [...encarList.map(c => c.price)].sort((a, b) => a - b);
    const min = prices[0];
    const max = prices[prices.length - 1];
    // Streamlit app.py L1153: avg_price = int(valid_prices.mean()) 과 100% 동일한 정수 처리
    const avg = Math.floor(prices.reduce((sum, p) => sum + p, 0) / prices.length);
    const midIdx = Math.floor(prices.length / 2);
    const median = prices.length % 2 === 0 ? Math.round((prices[midIdx - 1] + prices[midIdx]) / 2) : prices[midIdx];
    return {
      count: encarList.length,
      min,
      max,
      avg,
      median,
      strictAdjAvg: backendEncarStats?.strictAdjAvg ?? 0,
      strictAdjMin: backendEncarStats?.strictAdjMin ?? 0,
      strictAdjMedian: backendEncarStats?.strictAdjMedian ?? 0,
      strictAdjMax: backendEncarStats?.strictAdjMax ?? 0,
      strictAdjCount: backendEncarStats?.strictAdjCount ?? 0,
      strictAdjExcludedCount: backendEncarStats?.strictAdjExcludedCount ?? 0
    };
  }, [encarList, backendEncarStats]);

  // 연식별 호가 평균 및 대수 (Streamlit tab_main.py L500-L525 100% 동일 구현 - 9대 전수 집계)
  const encarYearStats = useMemo(() => {
    if (!encarList.length) return [];
    const targetYr = yearModel > 0 ? (yearModel > 100 ? yearModel % 100 : yearModel) : 22;
    const yearGroups: Record<number, { count: number; sum: number }> = {};
    
    encarList.forEach(car => {
      let y = targetYr;
      const yrStr = String(car.year || '').trim();
      const match = yrStr.match(/(\d{2,4})/);
      if (match) {
        const parsed = parseInt(match[1], 10);
        if (parsed > 2000) y = parsed - 2000;
        else if (parsed > 100) y = parsed % 100;
        else if (parsed > 0) y = parsed;
      }
      if (!yearGroups[y]) yearGroups[y] = { count: 0, sum: 0 };
      yearGroups[y].count++;
      yearGroups[y].sum += car.price;
    });

    const years = Object.keys(yearGroups).map(Number).sort((a, b) => b - a);

    return years.map(y => {
      const { count, sum } = yearGroups[y];
      const avg = Math.floor(sum / count);
      const isTarget = y === targetYr;
      return { year: y, avg, count, isTarget };
    });
  }, [encarList, yearModel]);

  // 🎯 [실시간 AI 빅데이터 정밀 소매가] (Streamlit 8501 100% 동일)
  const aiRetailPrice = useMemo(() => {
    const marketAvg = encarStats.avg > 0 
      ? encarStats.avg 
      : (encarList.length > 0 ? Math.round(encarList.reduce((a, b) => a + (b.price || 0), 0) / encarList.length) : 0);
    const rawIndPrice = encarValuation?.individualPrice || 0;
    // 💡 벤치마크가 없으면 전체 평균(marketAvg)으로 대체하지 않고 0(해당 없음)으로 유지
    const validIndPrice = (rawIndPrice > 0 && marketAvg > 0 && rawIndPrice < marketAvg * 1.6 && rawIndPrice > marketAvg * 0.4)
      ? rawIndPrice
      : (rawIndPrice > 0 ? rawIndPrice : 0);
    return validIndPrice;
  }, [encarStats, encarList, encarValuation]);

  // 🔄 AI 정밀 소매가가 새로 산출(변경)될 때만 좌측 예상 소매가(expectedSellPrice) 초기값 세팅
  // (사용자가 사이드바에서 값을 지워 0으로 만들거나 직접 수정할 때는 강제 덮어쓰기 금지)
  useEffect(() => {
    if (aiRetailPrice !== prevAiRetailPriceRef.current) {
      prevAiRetailPriceRef.current = aiRetailPrice;
      if (aiRetailPrice > 0) {
        setExpectedSellPrice(aiRetailPrice);
      }
    }
  }, [aiRetailPrice]);

  // 실시간 유효 소매가 (사용자 직접 입력값 우선, 없으면 AI 정밀 소매가)
  const effectiveSellPrice = useMemo(() => {
    return expectedSellPrice > 0 ? expectedSellPrice : aiRetailPrice;
  }, [expectedSellPrice, aiRetailPrice]);

  // 💡 [8501 Streamlit 100% 동기화] 실시간 안전 입찰 상한가 & 제비용 & 헤이딜러 수수료 공식
  const isLightCar = useMemo(() => {
    return ['모닝', '레이', '스파크', '마티즈', '캐스퍼', '티코'].some(k => (carName || '').includes(k));
  }, [carName]);

  const sellingFee = useMemo(() => Math.round(expectedSellPrice * 0.007 * 10) / 10, [expectedSellPrice]); // 판매수수료 0.7% (사이드바 입력 판매가 기준)
  const repairCostTotal = outerRepairCount * 13; // 외판 판당 13만
  const directExpense = 15; // 기본제경비 15만

  // 헤이딜러 실측 수수료 구간표 계산 함수
  const calcPurchaseFee = useCallback((targetVal: number, route: string, isLight: boolean) => {
    if (route === '셀프(기본)') {
      if (targetVal <= 100) return 7.5;
      if (targetVal <= 500) return 18.5;
      if (targetVal <= 1000) return isLight ? 19.0 : 24.5;
      if (targetVal <= 3000) return 25.0;
      return 36.0;
    } else if (route === '제로') {
      if (targetVal <= 100) return 14.0;
      if (targetVal <= 500) return 30.0;
      if (targetVal <= 1000) return isLight ? 30.5 : 36.5;
      if (targetVal <= 1500) return 36.5;
      if (targetVal <= 3000) return 39.5;
      if (targetVal <= 4000) return 47.5;
      return 50.5;
    }
    return 0; // 개인 직접입력 등
  }, []);

  // 💡 사이드바 시뮬레이션 권장 매입가 (사이드바 예상 소매가 기준)
  const safeBidCeiling = useMemo(() => {
    const basePrice = expectedSellPrice;
    if (basePrice <= 0) return 0;

    const sFee = Math.round(basePrice * 0.007 * 10) / 10;
    const repCost = outerRepairCount * 13;
    const dExpense = 15;
    const fixedDeductions = sFee + dExpense + repCost + targetMargin;

    // 매입수수료는 매입가 구간에 따라 달라지므로(순환 참조) 초기 추정값에서 3회 반복 계산으로 수렴
    let estBid = Math.max(0, basePrice - 180);
    for (let i = 0; i < 3; i++) {
      const pFee = calcPurchaseFee(estBid, auctionType, isLightCar);
      estBid = Math.max(0, Math.floor(basePrice - fixedDeductions - pFee));
    }
    return estBid;
  }, [expectedSellPrice, outerRepairCount, targetMargin, auctionType, isLightCar, calcPurchaseFee]);

  // 💡 우측 메인 상단 고정 권장 매입가 (AI 정밀 소매가 aiRetailPrice 기준, 사이드바 판매가 변경과 독립)
  const aiSafeBidCeiling = useMemo(() => {
    const basePrice = aiRetailPrice;
    if (basePrice <= 0) return 0;

    const sFee = Math.round(basePrice * 0.007 * 10) / 10;
    const repCost = outerRepairCount * 13;
    const dExpense = 15;
    const fixedDeductions = sFee + dExpense + repCost + targetMargin;

    let estBid = Math.max(0, basePrice - 180);
    for (let i = 0; i < 3; i++) {
      const pFee = calcPurchaseFee(estBid, auctionType, isLightCar);
      estBid = Math.max(0, Math.floor(basePrice - fixedDeductions - pFee));
    }
    return estBid;
  }, [aiRetailPrice, outerRepairCount, targetMargin, auctionType, isLightCar, calcPurchaseFee]);

  // 사용자가 직접 수정한 입찰가 (기본값: safeBidCeiling)
  const [userBid, setUserBid] = useState<number>(safeBidCeiling);
  const lastCalculatedRef = useRef<number>(safeBidCeiling);

  // 권장 입찰가가 재계산되면 사용자 입력값도 동기화
  useEffect(() => {
    if (lastCalculatedRef.current !== safeBidCeiling) {
      lastCalculatedRef.current = safeBidCeiling;
      setUserBid(safeBidCeiling);
    }
  }, [safeBidCeiling]);

  // 수정된 입찰가 기준 실제 수수료 및 실수익 마진 재계산
  const actualPurchaseFee = useMemo(() => {
    return calcPurchaseFee(userBid, auctionType, isLightCar);
  }, [calcPurchaseFee, userBid, auctionType, isLightCar]);

  const actualMargin = useMemo(() => {
    return expectedSellPrice - sellingFee - directExpense - repairCostTotal - actualPurchaseFee - userBid;
  }, [expectedSellPrice, sellingFee, directExpense, repairCostTotal, actualPurchaseFee, userBid]);

  // 저장 핸들러 (실제 계산된 안전 입찰 상한가 및 수정 입찰가로 원장에 실시간 반영 + 클립보드 자동 복사!)
  const handleSaveToLedger = async () => {
    const finalBid = userBid > 0 ? userBid : safeBidCeiling;
    onSaveToLedger({
      carNumber,
      manufacturer,
      carName,
      detailModel,
      year: yearModel.toString(),
      mileage: `${mileageKm.toLocaleString()} km`,
      options: optionsTag,
      buyPrice: finalBid, // 실제 입찰가
      sellPrice: expectedSellPrice,
      outerRepairs: outerRepairCount,
      repairCost: repairCostTotal,
      heydealerFee: actualPurchaseFee,
      memo: `[헤이딜러 ${auctionType} / 마진: ${Math.round(actualMargin)}만 / 예상소매: ${expectedSellPrice}만 / 권장상한: ${safeBidCeiling}만] ${memo}`,
      status: '장부저장'
    });

    // 제이 워크플로우: 저장 후 헤이딜러에 바로 붙여넣기할 수 있도록 최종 입찰가 자동 복사
    if (finalBid > 0) {
      await copyToClipboard(String(finalBid));
      setSearchStatus({
        type: 'success',
        message: `💾 장부 저장 완료 & 최종 입찰가(${finalBid.toLocaleString()}만원) 자동 복사되었습니다!`
      });
      setTimeout(() => setSearchStatus(null), 3000);
    }

    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };


  return {
    // 사이드바 상태 및 핸들러
    heydealerUrl,
    setHeydealerUrl,
    isAiEstimating,
    setIsAiEstimating,
    handleHeydealerAiEstimate,
    resetCockpitState,
    isQuickPasteOpen,
    setIsQuickPasteOpen,
    quickPasteText,
    setQuickPasteText,
    handleQuickParseText,
    carNumber,
    setCarNumber,
    isSearchingCar,
    handleLookupCarNumber,
    aiEstimateStep,
    searchStatus,
    setSearchStatus,
    manufacturer,
    setManufacturer,
    carName,
    setCarName,
    detailModel,
    setDetailModel,
    yearModel,
    setYearModel,
    mileageKm,
    setMileageKm,
    optionsTag,
    setOptionsTag,
    selectedEncar,
    setSelectedEncarId,
    expectedSellPrice,
    setExpectedSellPrice,
    effectiveSellPrice,
    aiRetailPrice,
    aiSafeBidCeiling,
    outerRepairCount,
    setOuterRepairCount,
    auctionType,
    setAuctionType,
    targetMargin,
    setTargetMargin,
    userBid,
    setUserBid,
    safeBidCeiling,
    actualMargin,
    actualPurchaseFee,
    repairCostTotal,
    memo,
    setMemo,
    savedSuccess,
    setSavedSuccess,
    handleSaveToLedger,

    // 밸류에이션 요약 섹션 관련
    biddingVerdict,
    isEncarLoading,
    encarSourceUrl,
    autoplusStats,
    currentAssessment,
    targetCarHistory,
    liveMarketStats,
    liveEncarSoldStats,
    encarStats,
    encarValuation,
    encarYearStats,
    encarSoldList,
    matchedAutoplusList,
    matchedAuctionList,
    encarList,
    soldTabMode,
    setSoldTabMode,
    showTrimColumn,
    setShowTrimColumn,
    fetchEncarComparable,
    showCarHistoryModal,
    setShowCarHistoryModal,

    // K-Car 직영 시세 통계
    kcarStats,
    isKcarLoading,
    fetchKcarMarket,

    // 시장 비교 매물 (엔카)
    encarTotalModelCount,
    encarFilteredCount,
    encarFilterStats,
    selectedEncarId,
    isInspectionLoading,
    encarErrorMessage,
    handleSelectEncarCar,

    // 헤이딜러 섹션
    heydealerSummary,
    availableHeydealerGrades,
    bestMatchHeydealerGrade,
    heydealerGradeCounts,
    selectedHeydealerGradeFilter,
    setSelectedHeydealerGradeFilter,
    heydealerBids,
    filteredHeydealerBids,
    selectedHeydealerBidId,
    setSelectedHeydealerBidId,
    selectedHeydealerBid,

    // 모달 상태
    cockpitModalCar,
    setCockpitModalCar,

    // 신차 공식 카탈로그 상태
    targetNewCarCatalog,

    // 일원화된 목표차 옵션 배열 및 미분류 잔액
    targetOptions,
    unclassifiedBalance,
  };
}
