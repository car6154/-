import React from 'react';
import { useBiddingCockpit } from '@/components/BiddingCockpit/hooks/useBiddingCockpit';
import { Search, ExternalLink, AlertCircle, CheckCircle2, RefreshCw, X } from 'lucide-react';
import { ComparableEncarV2Section, EncarSummaryHeader } from './ComparableEncarV2Section';
import { ComparableKcarV2Section, KcarSummaryHeader } from './ComparableKcarV2Section';
import { SelectedCarDetailV2Section } from './SelectedCarDetailV2Section';
import { SelectedKcarDetailV2Section } from './SelectedKcarDetailV2Section';
import { SidebarOptionSection } from './SidebarOptionSection';
import { HeydealerBidsV2Section } from './HeydealerBidsV2Section';
import { SelectedHeydealerBidDetailV2Section } from './SelectedHeydealerBidDetailV2Section';
import { SoldListingsV2Section } from './SoldListingsV2Section';
import { VehicleAssessmentV2Bar } from './VehicleAssessmentV2Bar';
import { CarHistoryDetailModal } from '@/components/CarHistoryDetailModal';

export interface BiddingCockpitV2TabProps {
  onSaveToLedger?: (car: any) => Promise<void> | void;
}

export const BiddingCockpitV2Tab: React.FC<BiddingCockpitV2TabProps> = ({
  onSaveToLedger,
}) => {
  const cockpit = useBiddingCockpit({
    onSaveToLedger: onSaveToLedger || (() => {}),
  });

  // 0. 비교 목록 활성 탭 (엔카 기본 / 케이카 / 헤이딜러 낙찰) 및 선택 상태 (V2 전용)
  const [activeCompTab, setActiveCompTab] = React.useState<'encar' | 'kcar' | 'heydealer'>('encar');
  const [lastRetailTab, setLastRetailTab] = React.useState<'encar' | 'kcar'>('encar');
  const [selectedKcarCarCd, setSelectedKcarCarCd] = React.useState<string | null>(null);

  // 💡 [11-03-17]: success 알림 스낵바 5초 자동 닫힘 타이머 (새 메시지 시 리셋 및 언마운트 cleanup)
  React.useEffect(() => {
    if (cockpit.searchStatus && cockpit.searchStatus.type === 'success') {
      const timer = setTimeout(() => {
        cockpit.setSearchStatus(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [cockpit.searchStatus, cockpit.setSearchStatus]);

  // 케이카 비교 목록 소스: wideCars(넓은 목록) 우선, 없으면 cars(엄격) 폴백 (V1 선례와 동일)
  const kcarDisplayList = React.useMemo(() => {
    if (cockpit.kcarStats?.wideCars && cockpit.kcarStats.wideCars.length > 0) {
      return cockpit.kcarStats.wideCars;
    }
    return cockpit.kcarStats?.cars || [];
  }, [cockpit.kcarStats?.wideCars, cockpit.kcarStats?.cars]);

  // 케이카 탭 전환 또는 목록 갱신 시 목록 안에서 엄격(isStrict) 차를 먼저, 없으면 첫 번째 차, 없으면 null
  React.useEffect(() => {
    if (activeCompTab === 'kcar' && kcarDisplayList.length > 0) {
      if (!selectedKcarCarCd || !kcarDisplayList.some(c => c.carCd === selectedKcarCarCd)) {
        const strictMatch = kcarDisplayList.find(c => c.isStrict);
        setSelectedKcarCarCd(strictMatch ? strictMatch.carCd : (kcarDisplayList[0]?.carCd || null));
      }
    }
  }, [activeCompTab, kcarDisplayList, selectedKcarCarCd]);

  const selectedKcar = React.useMemo(() => {
    if (!selectedKcarCarCd || !kcarDisplayList.length) return null;
    return kcarDisplayList.find(c => c.carCd === selectedKcarCarCd) || null;
  }, [kcarDisplayList, selectedKcarCarCd]);

  // 1. 목표차 한 줄 정보 (훅 값 그대로 사용)
  const targetCarName = cockpit.carName || '-';
  const targetDetailModel = cockpit.detailModel || '-';
  const targetYear = cockpit.yearModel ? `${cockpit.yearModel}년형` : '-';
  const targetMileage = cockpit.mileageKm && cockpit.mileageKm > 0
    ? `${cockpit.mileageKm.toLocaleString()}km`
    : '-';
  const targetColor = cockpit.targetCarHistory?.color || '-';

  // 2. 상단 4칸 지표 (소매가 · 엔카평균(카드값 strictAdjAvg) · 엔카시세 · 기준소매) 및 델타 계산
  const finalPriceVal = (cockpit.finalRetailPrice && cockpit.finalRetailPrice > 0) ? cockpit.finalRetailPrice : 0;
  const finalPriceText = finalPriceVal > 0 ? `${finalPriceVal.toLocaleString()}만원` : '-';

  // 엔카평균: 카드값(strictAdjAvg) 기준
  const strictAdjVal = cockpit.encarStats?.strictAdjAvg || 0;
  const rawStdVal = cockpit.encarStats?.rawStd100Price || 0;
  const chaolmaRetailVal = cockpit.targetCarHistory?.chaolmaRetailPrice || 0;

  const strictAdjText = strictAdjVal > 0 ? `${strictAdjVal.toLocaleString()}만원` : '-';
  const rawStdText = rawStdVal > 0 ? `${rawStdVal.toLocaleString()}만원` : '-';
  const chaolmaRetailText = chaolmaRetailVal > 0 ? `${chaolmaRetailVal.toLocaleString()}만원` : '-';

  const formatDelta = (val: number, base: number) => {
    if (!val || val <= 0 || !base || base <= 0) return null;
    const diff = val - base;
    if (diff > 0) return `+${diff}`;
    if (diff < 0) return `${diff}`;
    return '0';
  };

  const strictAdjDelta = formatDelta(strictAdjVal, finalPriceVal);
  const rawStdDelta = formatDelta(rawStdVal, finalPriceVal);
  const chaolmaDelta = formatDelta(chaolmaRetailVal, finalPriceVal);

  // 케이카 연식 통계 헬퍼 (kcarStats.yearStats 우선 사용, 없으면 kcarStats.cars에서 엔카와 동일 방식으로 집계)
  const kcarYearStats = React.useMemo(() => {
    if (cockpit.kcarStats?.yearStats && cockpit.kcarStats.yearStats.length > 0) {
      return cockpit.kcarStats.yearStats;
    }
    const cars = cockpit.kcarStats?.cars;
    if (!cars || cars.length === 0) return [];

    const targetYr = cockpit.yearModel > 0 ? (cockpit.yearModel > 100 ? cockpit.yearModel % 100 : cockpit.yearModel) : 22;
    const yearGroups: Record<number, { count: number; sum: number }> = {};

    cars.forEach(car => {
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
      yearGroups[y].sum += (Number(car.price) || 0);
    });

    const years = Object.keys(yearGroups).map(Number).sort((a, b) => b - a);
    return years.map(y => {
      const { count, sum } = yearGroups[y];
      const avg = Math.floor(sum / count);
      const isTarget = y === targetYr;
      return { year: y, avg, count, isTarget };
    });
  }, [cockpit.kcarStats, cockpit.yearModel]);

  // 4. 조회 전 초기 상태 여부 판정 (차량명 없고, 조회 중도 아니며, 매물 목록도 없는 상태)
  const isInitialState =
    !cockpit.carName &&
    cockpit.encarList.length === 0 &&
    !cockpit.isSearchingCar &&
    !cockpit.isAiEstimating;

  return (
    <div className="w-full max-w-[1920px] mx-auto px-4 py-4 space-y-4">
      {/* 사이드바(좌측) + 메인(우측) 2단 레이아웃 */}
      <div className="flex flex-col lg:flex-row gap-5 items-start">
        {/* [사이드바 (왼쪽, 고정 280px 너비, sticky)] */}
        <aside className="w-full lg:w-[280px] shrink-0 space-y-4 lg:sticky lg:top-4">
          {/* 1) 조회 입력 영역 (매물 URL · 차량번호 · 주행거리 · 조회 버튼) */}
          <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-4 shadow-sm space-y-3.5">
            <div className="text-xs font-semibold text-[#8b8e9d] uppercase tracking-wider">
              조회 입력
            </div>

            {/* 헤이딜러 매물 URL 조회 (세로 고정 배치) */}
            <div className="space-y-2">
              <input
                type="text"
                value={cockpit.heydealerUrl}
                onChange={(e) => cockpit.setHeydealerUrl(e.target.value)}
                placeholder="헤이딜러 매물 URL 또는 경매 ID"
                className="w-full px-3 py-2 rounded-lg bg-[#161822] border border-[#262938] text-xs text-white placeholder-[#5e616e] focus:outline-none focus:border-[#cc9166] transition font-mono"
              />
              <button
                type="button"
                onClick={cockpit.handleHeydealerAiEstimate}
                disabled={cockpit.isAiEstimating}
                className="w-full py-2 rounded-lg bg-gradient-to-r from-amber-600/50 to-[#cc9166]/60 hover:from-amber-600/70 hover:to-[#cc9166]/80 text-xs font-bold text-white border border-[#cc9166]/60 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5 shadow-sm"
              >
                {cockpit.isAiEstimating ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>조회 중...</span>
                  </>
                ) : (
                  <>
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>매물 URL 조회</span>
                  </>
                )}
              </button>
            </div>

            {/* 구분선 */}
            <div className="relative flex py-0.5 items-center">
              <div className="flex-grow border-t border-[#1e2029]" />
              <span className="flex-shrink mx-2 text-[10.5px] text-[#5e616e]">또는 차량번호 직접 조회</span>
              <div className="flex-grow border-t border-[#1e2029]" />
            </div>

            {/* 차량번호 & 주행거리 조회 (세로 고정 배치) */}
            <div className="space-y-2">
              <input
                type="text"
                value={cockpit.carNumber}
                onChange={(e) => cockpit.setCarNumber(e.target.value)}
                placeholder="차량번호 (예: 12가3456)"
                className="w-full px-3 py-2 rounded-lg bg-[#161822] border border-[#262938] text-xs text-white placeholder-[#5e616e] focus:outline-none focus:border-blue-500 transition font-mono"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') cockpit.handleLookupCarNumber();
                }}
              />
              <input
                type="number"
                value={cockpit.mileageKm || ''}
                onChange={(e) => cockpit.setMileageKm(Number(e.target.value))}
                placeholder="주행거리 (km)"
                className="w-full px-3 py-2 rounded-lg bg-[#161822] border border-[#262938] text-xs text-white placeholder-[#5e616e] focus:outline-none focus:border-blue-500 transition font-mono"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') cockpit.handleLookupCarNumber();
                }}
              />
              <button
                type="button"
                onClick={() => cockpit.handleLookupCarNumber()}
                disabled={cockpit.isSearchingCar}
                className="w-full py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-bold text-white transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5 shadow-sm"
              >
                {cockpit.isSearchingCar ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>조회 중</span>
                  </>
                ) : (
                  <>
                    <Search className="w-3.5 h-3.5" />
                    <span>통합 조회</span>
                  </>
                )}
              </button>
            </div>

            {/* 상태 메시지 알림 (검색 중/경고/안내 - error/warning/info 등 non-success만 고정 박스로 표시) */}
            {cockpit.searchStatus && cockpit.searchStatus.type !== 'success' && (
              <div
                className={`text-xs px-3 py-2 rounded-lg flex items-center gap-1.5 ${
                  cockpit.searchStatus.type === 'error'
                    ? 'bg-rose-950/40 border border-rose-900/60 text-rose-300'
                    : cockpit.searchStatus.type === 'warning'
                    ? 'bg-amber-950/40 border border-amber-900/60 text-amber-300'
                    : 'bg-blue-950/40 border border-blue-900/60 text-blue-300'
                }`}
              >
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>{cockpit.searchStatus.message}</span>
              </div>
            )}
          </div>

          {/* 2) 목표차 한 줄 정보 (차명 · 등급 · 연식 · 주행거리 · 색상) */}
          <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl px-4 py-3 space-y-1.5 text-xs">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-semibold text-[#8b8e9d] uppercase">목표 차량</span>
              <span className="font-bold text-white truncate max-w-[200px]">{targetCarName}</span>
            </div>
            {targetDetailModel !== '-' && (
              <div className="text-[11px] text-zinc-300 truncate">
                {targetDetailModel}
              </div>
            )}
            {/* 등급 밑에 색상 표시 (지어내지 않고 조회 결과의 색상 필드, 없으면 '-') */}
            <div className="flex items-center justify-between text-[11px] text-zinc-300">
              <span className="text-[#8b8e9d]">색상</span>
              <span className="font-medium text-white">{targetColor}</span>
            </div>
            <div className="flex items-center justify-between font-mono text-xs text-[#8b8e9d] pt-1 border-t border-[#1e2029]">
              <span>연식 <strong className="text-zinc-200 font-semibold">{targetYear}</strong></span>
              <span>주행거리 <strong className="text-zinc-200 font-semibold">{targetMileage}</strong></span>
            </div>
          </div>

          {/* 2-1) 추가 옵션 및 매칭 섹션 */}
          <SidebarOptionSection
            targetOptions={cockpit.targetOptions}
            optionsTag={cockpit.optionsTag}
            targetCarName={cockpit.carName}
            targetYear={cockpit.yearModel}
            selectedEncar={cockpit.selectedEncar}
            selectedKcar={selectedKcar}
            activeCompTab={activeCompTab === 'kcar' ? 'kcar' : 'encar'}
            targetCatalog={cockpit.targetNewCarCatalog}
            historyOptionTotalMan={cockpit.targetCarHistory?.totalOptionPrice}
            unclassifiedBalance={cockpit.unclassifiedBalance}
          />

          {/* 2-2) 장부 저장 폼 (예상 소매가 · 외판 수리 갯수 · 매입 경로 · 목표 마진 · 특이사항 메모 · 저장 버튼) */}
          <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-4 shadow-sm space-y-3 text-xs">
            <div className="text-xs font-semibold text-[#8b8e9d] uppercase tracking-wider flex items-center justify-between">
              <span>장부 저장</span>
              {cockpit.savedSuccess && (
                <span className="text-emerald-400 font-bold flex items-center gap-1 text-[11px]">
                  <CheckCircle2 className="w-3.5 h-3.5" /> 저장 완료!
                </span>
              )}
            </div>

            {/* 예상 소매가 (만원) */}
            <div className="space-y-1">
              <div className="flex justify-between items-center text-zinc-400">
                <span className="text-[11px]">예상 소매가 (만원)</span>
                {cockpit.expectedSellPrice > 0 && (
                  <span className="text-[10px] text-zinc-500 font-mono">
                    {cockpit.expectedSellPrice.toLocaleString()}만원
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => cockpit.setExpectedSellPrice(Math.max(0, cockpit.expectedSellPrice - 10))}
                  className="w-7 h-7 rounded bg-[#161822] hover:bg-[#202330] text-white font-bold transition flex items-center justify-center border border-[#262938]"
                >-</button>
                <input
                  type="number"
                  value={cockpit.expectedSellPrice === 0 ? '' : cockpit.expectedSellPrice}
                  onChange={(e) => cockpit.setExpectedSellPrice(Math.max(0, Number(e.target.value) || 0))}
                  placeholder="예상 소매가 입력"
                  className="flex-1 px-2.5 py-1.5 rounded-lg bg-[#161822] border border-[#262938] text-xs text-white placeholder-[#5e616e] focus:outline-none focus:border-sky-400 font-mono text-center"
                />
                <button
                  type="button"
                  onClick={() => cockpit.setExpectedSellPrice(cockpit.expectedSellPrice + 10)}
                  className="w-7 h-7 rounded bg-[#161822] hover:bg-[#202330] text-white font-bold transition flex items-center justify-center border border-[#262938]"
                >+</button>
              </div>
            </div>

            {/* 외판 수리 갯수 */}
            <div className="space-y-1">
              <span className="text-[11px] text-zinc-400 block">외판 수리 갯수</span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => cockpit.setOuterRepairCount(Math.max(0, cockpit.outerRepairCount - 1))}
                  className="w-7 h-7 rounded bg-[#161822] hover:bg-[#202330] text-white font-bold transition flex items-center justify-center border border-[#262938]"
                >-</button>
                <input
                  type="number"
                  min={0}
                  value={cockpit.outerRepairCount}
                  onChange={(e) => cockpit.setOuterRepairCount(Math.max(0, Number(e.target.value) || 0))}
                  className="flex-1 px-2.5 py-1.5 rounded-lg bg-[#161822] border border-[#262938] text-xs text-white font-mono text-center focus:outline-none focus:border-sky-400"
                />
                <button
                  type="button"
                  onClick={() => cockpit.setOuterRepairCount(cockpit.outerRepairCount + 1)}
                  className="w-7 h-7 rounded bg-[#161822] hover:bg-[#202330] text-white font-bold transition flex items-center justify-center border border-[#262938]"
                >+</button>
              </div>
            </div>

            {/* 매입 경로 (입력란, 기본값 '셀프'. 직접 입력 가능) */}
            <div className="space-y-1">
              <span className="text-[11px] text-zinc-400 block">매입 경로</span>
              <input
                type="text"
                value={cockpit.auctionType || '셀프'}
                onChange={(e) => cockpit.setAuctionType(e.target.value)}
                placeholder="셀프"
                className="w-full px-3 py-1.5 rounded-lg bg-[#161822] border border-[#262938] text-xs text-white placeholder-[#5e616e] focus:outline-none focus:border-sky-400 font-mono"
              />
            </div>

            {/* 목표 마진 (만원) */}
            <div className="space-y-1">
              <span className="text-[11px] text-zinc-400 block">목표 마진 (만원)</span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => cockpit.setTargetMargin(Math.max(0, cockpit.targetMargin - 10))}
                  className="w-7 h-7 rounded bg-[#161822] hover:bg-[#202330] text-white font-bold transition flex items-center justify-center border border-[#262938]"
                >-</button>
                <input
                  type="number"
                  value={cockpit.targetMargin === 0 ? '' : cockpit.targetMargin}
                  onChange={(e) => cockpit.setTargetMargin(Number(e.target.value) || 0)}
                  placeholder="0"
                  className="flex-1 px-2.5 py-1.5 rounded-lg bg-[#161822] border border-[#262938] text-xs text-emerald-400 font-mono font-bold text-center focus:outline-none focus:border-emerald-400"
                />
                <button
                  type="button"
                  onClick={() => cockpit.setTargetMargin(cockpit.targetMargin + 10)}
                  className="w-7 h-7 rounded bg-[#161822] hover:bg-[#202330] text-white font-bold transition flex items-center justify-center border border-[#262938]"
                >+</button>
              </div>
            </div>

            {/* 매입 희망가 (만원) - 미입력 시 권장상한 자동 적용 */}
            <div className="space-y-1">
              <div className="flex justify-between items-center text-zinc-400">
                <span className="text-[11px] font-medium">매입 희망가 (만원)</span>
                <span className="text-[10px] text-zinc-500 font-mono">
                  {cockpit.safeBidCeiling > 0 ? `권장상한 ${cockpit.safeBidCeiling.toLocaleString()}만` : '미입력 시 권장상한 자동적용'}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => cockpit.setUserBid(Math.max(0, (cockpit.userBid || cockpit.safeBidCeiling) - 10))}
                  className="w-7 h-7 rounded bg-[#161822] hover:bg-[#202330] text-white font-bold transition flex items-center justify-center border border-[#262938]"
                >-</button>
                <input
                  type="number"
                  value={cockpit.userBid === 0 ? '' : cockpit.userBid}
                  onChange={(e) => cockpit.setUserBid(Math.max(0, Number(e.target.value) || 0))}
                  placeholder={cockpit.safeBidCeiling > 0 ? `${cockpit.safeBidCeiling}` : '매입가 입력'}
                  className="flex-1 px-2.5 py-1.5 rounded-lg bg-[#161822] border border-[#262938] text-xs text-emerald-400 placeholder-[#5e616e] focus:outline-none focus:border-emerald-400 font-mono font-bold text-center"
                />
                <button
                  type="button"
                  onClick={() => cockpit.setUserBid((cockpit.userBid || cockpit.safeBidCeiling) + 10)}
                  className="w-7 h-7 rounded bg-[#161822] hover:bg-[#202330] text-white font-bold transition flex items-center justify-center border border-[#262938]"
                >+</button>
              </div>
            </div>

            {/* 매입 비용 내역 (권장/최종 매입가, 예상마진, 수수료·수리·잡비) */}
            <div className="bg-emerald-500/10 border border-emerald-500/30 p-2.5 rounded-lg space-y-1.5">
              {/* 매입가 줄: 클릭 시 최종 입찰가 자동 복사 + 장부 저장 */}
              <div
                onClick={cockpit.carName ? cockpit.handleSaveToLedger : undefined}
                className={`flex justify-between items-baseline p-1.5 -m-0.5 rounded-md transition ${
                  cockpit.carName
                    ? 'cursor-pointer hover:bg-emerald-500/20 active:scale-[0.99] group'
                    : 'cursor-not-allowed opacity-75'
                }`}
                title={cockpit.carName ? '클릭 시 최종 입찰가 자동 복사 & 장부 저장' : '차량을 먼저 선택해주세요'}
              >
                <div>
                  <div className="text-xs font-bold text-zinc-300">
                    {cockpit.userBid > 0 && cockpit.userBid !== cockpit.safeBidCeiling ? (
                      <span>최종 매입가 <small className="text-zinc-400 font-normal">(권장 {cockpit.safeBidCeiling.toLocaleString()}만)</small></span>
                    ) : (
                      <span className="text-zinc-300">권장 매입가</span>
                    )}
                  </div>
                  <div className="text-[10px] text-emerald-400 font-medium flex items-center gap-1 mt-0.5">
                    <span>💾 클릭하면 복사·저장</span>
                  </div>
                </div>
                <div className="text-lg font-black text-emerald-400 tracking-tight font-mono group-hover:text-emerald-300 transition-colors">
                  {(cockpit.userBid > 0 ? cockpit.userBid : cockpit.safeBidCeiling).toLocaleString()}{' '}
                  <span className="text-xs font-bold text-zinc-300">만원</span>
                </div>
              </div>

              <div className="flex justify-between items-center pt-1.5 border-t border-dashed border-emerald-500/20 text-xs">
                <span className="text-zinc-300 font-medium">예상마진</span>
                <span className="text-blue-400 font-black font-mono">
                  {cockpit.actualMargin >= 0 ? `+${Math.round(cockpit.actualMargin).toLocaleString()}` : Math.round(cockpit.actualMargin).toLocaleString()}만원
                </span>
              </div>

              <div className="text-[10.5px] text-zinc-400 pt-0.5 font-mono">
                수수료: {cockpit.actualPurchaseFee}만 · 수리: {cockpit.repairCostTotal}만 · 잡비: 15만
              </div>
            </div>

            {/* 특이사항 메모 */}
            <div className="space-y-1">
              <span className="text-[11px] text-zinc-400 block">특이사항 메모</span>
              <input
                type="text"
                value={cockpit.memo}
                onChange={(e) => cockpit.setMemo(e.target.value)}
                placeholder="보조키, 틴팅, 블박 등"
                className="w-full px-3 py-1.5 rounded-lg bg-[#161822] border border-[#262938] text-xs text-white placeholder-[#5e616e] focus:outline-none focus:border-sky-400"
              />
            </div>

            {/* '내 장부 및 구글시트에 저장' 버튼 */}
            <button
              type="button"
              onClick={cockpit.handleSaveToLedger}
              disabled={!cockpit.carName}
              className={`w-full py-2.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-md ${
                cockpit.savedSuccess
                  ? 'bg-emerald-600 text-white'
                  : !cockpit.carName
                  ? 'bg-[#161822] text-zinc-600 border border-[#262938] cursor-not-allowed'
                  : 'bg-[#1f222e] hover:bg-[#2c3040] text-white border border-[#35394a] cursor-pointer'
              }`}
            >
              {cockpit.savedSuccess ? '✅ 저장 완료!' : '📋 내 장부 및 구글시트에 저장'}
            </button>
          </div>


        </aside>

        {/* [메인 영역 (오른쪽, 나머지 너비)] */}
        <main className="flex-1 min-w-0 w-full space-y-4">
          {/* 차량 상태 판정(보험이력 포함) 칩 행 (메인 최상단) */}
          <VehicleAssessmentV2Bar
            currentAssessment={cockpit.currentAssessment}
            targetCarHistory={cockpit.targetCarHistory}
            onOpenHistoryModal={() => cockpit.setShowCarHistoryModal(true)}
          />

          {/* 상단 4칸 한 줄: 소매가 · 엔카평균 · 엔카시세 · 기준소매 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {/* 1) 소매가 */}
            <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-2 shadow-sm flex flex-col justify-between">
              <span className="text-[11px] font-semibold text-[#8b8e9d] uppercase">소매가</span>
              <div className="mt-1 flex items-baseline">
                <span className="text-xl sm:text-2xl font-black text-sky-400 font-mono tracking-tight">
                  {finalPriceText}
                </span>
              </div>
            </div>

            {/* 2) 엔카평균 */}
            <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-2 shadow-sm flex flex-col justify-between">
              <span className="text-[11px] font-semibold text-[#8b8e9d] uppercase">엔카평균</span>
              <div className="mt-1 flex items-baseline justify-between gap-1 flex-wrap">
                <span className="text-base sm:text-lg font-bold text-zinc-100 font-mono tracking-tight">
                  {strictAdjText}
                </span>
                {strictAdjDelta && (
                  <span className={`text-xs font-mono font-bold ${
                    strictAdjDelta.startsWith('+') ? 'text-rose-400' : strictAdjDelta.startsWith('-') ? 'text-blue-400' : 'text-zinc-400'
                  }`}>
                    {strictAdjDelta}
                  </span>
                )}
              </div>
            </div>

            {/* 3) 엔카시세 */}
            <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-2 shadow-sm flex flex-col justify-between">
              <span className="text-[11px] font-semibold text-[#8b8e9d] uppercase">엔카시세</span>
              <div className="mt-1 flex items-baseline justify-between gap-1 flex-wrap">
                <span className="text-base sm:text-lg font-bold text-zinc-100 font-mono tracking-tight">
                  {rawStdText}
                </span>
                {rawStdDelta && (
                  <span className={`text-xs font-mono font-bold ${
                    rawStdDelta.startsWith('+') ? 'text-rose-400' : rawStdDelta.startsWith('-') ? 'text-blue-400' : 'text-zinc-400'
                  }`}>
                    {rawStdDelta}
                  </span>
                )}
              </div>
            </div>

            {/* 4) 기준소매 */}
            <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-2 shadow-sm flex flex-col justify-between">
              <span className="text-[11px] font-semibold text-[#8b8e9d] uppercase">기준소매</span>
              <div className="mt-1 flex items-baseline justify-between gap-1 flex-wrap">
                <span className="text-base sm:text-lg font-bold text-zinc-100 font-mono tracking-tight">
                  {chaolmaRetailText}
                </span>
                {chaolmaDelta && (
                  <span className={`text-xs font-mono font-bold ${
                    chaolmaDelta.startsWith('+') ? 'text-rose-400' : chaolmaDelta.startsWith('-') ? 'text-blue-400' : 'text-zinc-400'
                  }`}>
                    {chaolmaDelta}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* 팔린매물 3탭 영역 (엔카 팔린매물 · 자사 소매 실적 · 자사 도매 실적) */}
          <SoldListingsV2Section
            encarSoldList={cockpit.encarSoldList || []}
            matchedAutoplusList={cockpit.matchedAutoplusList || []}
            matchedAuctionList={cockpit.matchedAuctionList || []}
            carName={cockpit.carName}
            detailModel={cockpit.detailModel}
            yearModel={cockpit.yearModel}
            liveMarketStats={cockpit.liveMarketStats}
            biddingVerdict={cockpit.biddingVerdict}
          />

          {/* 비교 목록(왼쪽 7)과 선택 상세(오른쪽 5) lg 나란히 배치 (7:5 비율) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* 좌측 7/12: 비교 목록 (요약 4칸 + 연식별 평균 + 탭 토글 + 비교 목록) */}
            <div className="min-w-0 w-full lg:col-span-7 space-y-3">
              {/* 탭 본문 (엔카 / 케이카 / 헤이딜러 비교 목록): 마운트 유지 및 hidden 토글로 탭 전환 시 캐시 보존 및 무재호출 보장 */}
              <div className="max-h-[640px] overflow-y-auto rounded-xl space-y-3">
                {/* 0. 목록 헤더 스티키 래퍼: [활성 탭 요약 4칸 + 연식별 평균] + [탭바 토글] 한 덩어리 고정 (11-03-23) */}
                <div className="sticky top-0 z-20 bg-[#08080a] pb-1 space-y-2.5">
                  {/* 0-1. 활성 탭 요약 4칸 + 연식별 호가 평균 (엔카 / 케이카) */}
                  {activeCompTab === 'encar' && (
                    <EncarSummaryHeader
                      encarList={cockpit.encarList || []}
                      cohortNoAccAvg={cockpit.encarStats?.cohortNoAccAvg || 0}
                      encarYearStats={cockpit.encarYearStats || []}
                      encarSourceUrl={cockpit.encarSourceUrl}
                    />
                  )}
                  {activeCompTab === 'kcar' && (
                    <KcarSummaryHeader
                      kcarList={kcarDisplayList}
                      kcarYearStats={kcarYearStats || []}
                      kcarSearchUrl={cockpit.kcarStats?.searchUrl}
                    />
                  )}

                  {/* 0-2. 상단 탭 토글 (엔카 / 케이카 / 헤이딜러 낙찰) */}
                  <div className="flex items-center justify-between gap-2 pt-0.5">
                    <div className="inline-flex p-1 bg-[#0f1015] border border-[#1e2029] rounded-xl shadow-sm">
                      <button
                        type="button"
                        onClick={() => { setActiveCompTab('encar'); setLastRetailTab('encar'); }}
                        className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${
                          activeCompTab === 'encar'
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-zinc-400 hover:text-white hover:bg-[#1a1c26]'
                        }`}
                      >
                        <span>엔카</span>
                        <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono font-black ${
                          activeCompTab === 'encar' ? 'bg-black/30 text-white' : 'bg-[#1a1c26] text-zinc-400'
                        }`}>
                          {cockpit.encarFilteredCount || cockpit.encarList?.length || 0}
                        </span>
                      </button>

                      <button
                        type="button"
                        onClick={() => { setActiveCompTab('kcar'); setLastRetailTab('kcar'); }}
                        className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${
                          activeCompTab === 'kcar'
                            ? 'bg-amber-600 text-white shadow-sm'
                            : 'text-zinc-400 hover:text-white hover:bg-[#1a1c26]'
                        }`}
                      >
                        <span>케이카</span>
                        <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono font-black ${
                          activeCompTab === 'kcar' ? 'bg-black/30 text-white' : 'bg-[#1a1c26] text-zinc-400'
                        }`}>
                          {cockpit.kcarStats?.strictCount ?? cockpit.kcarStats?.count ?? cockpit.kcarStats?.cars?.length ?? 0}
                        </span>
                      </button>

                      <button
                        type="button"
                        onClick={() => setActiveCompTab('heydealer')}
                        className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${
                          activeCompTab === 'heydealer'
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-zinc-400 hover:text-white hover:bg-[#1a1c26]'
                        }`}
                      >
                        <span>헤이딜러 낙찰</span>
                        <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono font-black ${
                          activeCompTab === 'heydealer' ? 'bg-black/30 text-white' : 'bg-[#1a1c26] text-zinc-400'
                        }`}>
                          {cockpit.filteredHeydealerBids?.length || 0}
                        </span>
                      </button>
                    </div>
                  </div>
                </div>
                <div className={activeCompTab === 'encar' ? 'block' : 'hidden'}>
                  <ComparableEncarV2Section
                    encarList={cockpit.encarList || []}
                    selectedEncarId={cockpit.selectedEncarId}
                    onSelectCar={cockpit.handleSelectEncarCar}
                    isLoading={cockpit.isEncarLoading}
                    totalModelCount={cockpit.encarTotalModelCount || 0}
                    filteredCount={cockpit.encarFilteredCount || 0}
                    isInitialState={isInitialState}
                    targetMileageKm={cockpit.mileageKm || 0}
                    cohortNoAccAvg={cockpit.encarStats?.cohortNoAccAvg || 0}
                    errorMessage={cockpit.encarErrorMessage}
                    encarYearStats={cockpit.encarYearStats || []}
                    encarSourceUrl={cockpit.encarSourceUrl}
                    targetOptions={cockpit.targetOptions}
                    optionsTag={cockpit.optionsTag}
                    targetCatalog={cockpit.targetNewCarCatalog}
                    targetCarName={cockpit.carName}
                    targetYear={cockpit.yearModel}
                  />
                </div>
                <div className={activeCompTab === 'kcar' ? 'block' : 'hidden'}>
                  <ComparableKcarV2Section
                    kcarList={kcarDisplayList}
                    selectedCarCd={selectedKcarCarCd}
                    onSelectCar={(carCd) => setSelectedKcarCarCd(carCd)}
                    yearModel={cockpit.yearModel}
                    isLoading={cockpit.isKcarLoading}
                    totalCount={cockpit.kcarStats?.wideCount ?? cockpit.kcarStats?.count ?? cockpit.kcarStats?.cars?.length ?? 0}
                    strictCount={cockpit.kcarStats?.strictCount ?? (cockpit.kcarStats?.count || cockpit.kcarStats?.cars?.length || 0)}
                    isInitialState={isInitialState}
                    errorMessage={cockpit.kcarStats?.message}
                    kcarYearStats={kcarYearStats || []}
                    kcarSearchUrl={cockpit.kcarStats?.searchUrl}
                    targetOptions={cockpit.targetOptions}
                    optionsTag={cockpit.optionsTag}
                    targetCatalog={cockpit.targetNewCarCatalog}
                    targetCarName={cockpit.carName}
                    targetYear={cockpit.yearModel}
                  />
                </div>
                <div className={activeCompTab === 'heydealer' ? 'block' : 'hidden'}>
                  <HeydealerBidsV2Section
                    heydealerSummary={cockpit.heydealerSummary}
                    availableHeydealerGrades={cockpit.availableHeydealerGrades}
                    bestMatchHeydealerGrade={cockpit.bestMatchHeydealerGrade}
                    heydealerGradeCounts={cockpit.heydealerGradeCounts}
                    selectedHeydealerGradeFilter={cockpit.selectedHeydealerGradeFilter}
                    setSelectedHeydealerGradeFilter={cockpit.setSelectedHeydealerGradeFilter}
                    heydealerBids={cockpit.heydealerBids}
                    filteredHeydealerBids={cockpit.filteredHeydealerBids}
                    selectedHeydealerBidId={cockpit.selectedHeydealerBidId}
                    setSelectedHeydealerBidId={cockpit.setSelectedHeydealerBidId}
                    mileageKm={cockpit.mileageKm || 0}
                  />
                </div>
              </div>
            </div>

            {/* 우측 5/12: 선택 차량 상세 & 2D 상태도 (낙찰 탭 + 낙찰 선택 시 낙찰 상세, 그 외에는 마지막 소매 차량 상세 유지) */}
            <div className="min-w-0 w-full lg:col-span-5">
              <div className={activeCompTab === 'heydealer' && Boolean(cockpit.selectedHeydealerBid) ? 'block' : 'hidden'}>
                <SelectedHeydealerBidDetailV2Section
                  selectedHeydealerBid={cockpit.selectedHeydealerBid}
                />
              </div>
              <div className={!(activeCompTab === 'heydealer' && Boolean(cockpit.selectedHeydealerBid)) && lastRetailTab === 'encar' ? 'block' : 'hidden'}>
                <SelectedCarDetailV2Section
                  selectedEncar={cockpit.selectedEncar}
                  isInspectionLoading={cockpit.isInspectionLoading}
                  targetCarName={cockpit.carName}
                  targetYear={cockpit.yearModel}
                  targetOptions={cockpit.targetOptions}
                  optionsTag={cockpit.optionsTag}
                />
              </div>
              <div className={!(activeCompTab === 'heydealer' && Boolean(cockpit.selectedHeydealerBid)) && lastRetailTab === 'kcar' ? 'block' : 'hidden'}>
                <SelectedKcarDetailV2Section
                  selectedKcar={selectedKcar}
                  targetCatalog={cockpit.targetNewCarCatalog}
                  targetCarName={cockpit.carName}
                  targetYear={cockpit.yearModel}
                  targetOptions={cockpit.targetOptions}
                  optionsTag={cockpit.optionsTag}
                />
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* 🌟 원부 & 카히스토리 대형 상세 리포트 모달 */}
      <CarHistoryDetailModal
        isOpen={cockpit.showCarHistoryModal}
        onClose={() => cockpit.setShowCarHistoryModal(false)}
        carNumber={cockpit.carNumber}
        carName={cockpit.carName}
        currentMileage={cockpit.mileageKm}
        data={cockpit.targetCarHistory}
      />

      {/* 💡 [11-03-17]: 연동완료 success 스낵바 (화면 하단 고정 오버레이 토스트, 레이아웃 공간 차지 없음) */}
      {cockpit.searchStatus && cockpit.searchStatus.type === 'success' && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 bg-emerald-950/90 border border-emerald-500/60 text-emerald-200 text-xs sm:text-sm font-medium rounded-xl shadow-2xl backdrop-blur-md animate-in fade-in slide-in-from-bottom-3 duration-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{cockpit.searchStatus.message}</span>
          <button
            type="button"
            onClick={() => cockpit.setSearchStatus(null)}
            className="ml-2 p-1 text-emerald-400/70 hover:text-emerald-200 hover:bg-emerald-900/50 rounded-lg transition"
            title="닫기"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
};
