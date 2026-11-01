import React from 'react';
import { useBiddingCockpit } from '@/components/BiddingCockpit/hooks/useBiddingCockpit';
import { Search, ExternalLink, Car, AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react';
import { ComparableEncarV2Section } from './ComparableEncarV2Section';
import { ComparableKcarV2Section } from './ComparableKcarV2Section';
import { SelectedCarDetailV2Section } from './SelectedCarDetailV2Section';
import { SelectedKcarDetailV2Section } from './SelectedKcarDetailV2Section';
import { SidebarOptionSection } from './SidebarOptionSection';
import { HeydealerBidsV2Section } from './HeydealerBidsV2Section';
import { SelectedHeydealerBidDetailV2Section } from './SelectedHeydealerBidDetailV2Section';

export const BiddingCockpitV2Tab: React.FC = () => {
  const cockpit = useBiddingCockpit({
    onSaveToLedger: () => {},
  });

  // 0. 비교 목록 활성 탭 (엔카 기본 / 케이카 / 헤이딜러 낙찰) 및 선택 상태 (V2 전용)
  const [activeCompTab, setActiveCompTab] = React.useState<'encar' | 'kcar' | 'heydealer'>('encar');
  const [lastRetailTab, setLastRetailTab] = React.useState<'encar' | 'kcar'>('encar');
  const [selectedKcarCarCd, setSelectedKcarCarCd] = React.useState<string | null>(null);

  // 케이카 목록 변경 시 유효 엄격(isStrict) 차량 중에서만 첫 번째 차량 자동 선택 (없으면 첫 번째 차량, 없으면 null)
  React.useEffect(() => {
    if (activeCompTab === 'kcar' && cockpit.kcarStats?.cars && cockpit.kcarStats.cars.length > 0) {
      const kcarCars = cockpit.kcarStats.cars;
      if (!selectedKcarCarCd || !kcarCars.some(c => c.carCd === selectedKcarCarCd)) {
        const strictMatch = kcarCars.find(c => c.isStrict);
        setSelectedKcarCarCd(strictMatch ? strictMatch.carCd : (kcarCars[0]?.carCd || null));
      }
    }
  }, [activeCompTab, cockpit.kcarStats?.cars, selectedKcarCarCd]);

  const selectedKcar = React.useMemo(() => {
    if (!selectedKcarCarCd || !cockpit.kcarStats?.cars) return null;
    return cockpit.kcarStats.cars.find(c => c.carCd === selectedKcarCarCd) || null;
  }, [cockpit.kcarStats?.cars, selectedKcarCarCd]);

  // 1. 목표차 한 줄 정보 (훅 값 그대로 사용)
  const targetCarName = cockpit.carName || '-';
  const targetDetailModel = cockpit.detailModel || '-';
  const targetYear = cockpit.yearModel ? `${cockpit.yearModel}년형` : '-';
  const targetMileage = cockpit.mileageKm && cockpit.mileageKm > 0
    ? `${cockpit.mileageKm.toLocaleString()}km`
    : '-';

  // 2. 최종 소매가 1카드 (훅 값 그대로 사용, 0이거나 없으면 '-')
  const finalPriceText = (cockpit.finalRetailPrice && cockpit.finalRetailPrice > 0)
    ? `${cockpit.finalRetailPrice.toLocaleString()}만원`
    : '-';

  // 3. 참고 한 줄 (훅 값 그대로 사용, 0이거나 없으면 '-')
  const rawStdVal = cockpit.encarStats?.rawStd100Price || 0;
  const cohortNoAccVal = cockpit.encarStats?.cohortNoAccAvg || 0;
  const chaolmaRetailVal = cockpit.targetCarHistory?.chaolmaRetailPrice || 0;

  const rawStdText = rawStdVal > 0 ? `${rawStdVal.toLocaleString()}만원` : '-';
  const cohortNoAccText = cohortNoAccVal > 0 ? `${cohortNoAccVal.toLocaleString()}만원` : '-';
  const chaolmaRetailText = chaolmaRetailVal > 0 ? `${chaolmaRetailVal.toLocaleString()}만원` : '-';

  // 4. 조회 전 초기 상태 여부 판정 (차량명 없고, 조회 중도 아니며, 매물 목록도 없는 상태)
  const isInitialState =
    !cockpit.carName &&
    cockpit.encarList.length === 0 &&
    !cockpit.isSearchingCar &&
    !cockpit.isAiEstimating;

  return (
    <div className="w-full max-w-[1920px] mx-auto px-4 py-4 space-y-4">
      {/* 새 버전 안내 헤더 */}
      <div className="flex items-center justify-between border-b border-[#1f222e] pb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[#cc9166]/20 border border-[#cc9166]/40 flex items-center justify-center">
            <Car className="w-4 h-4 text-[#cc9166]" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white flex items-center gap-2">
              비딩 콕핏 <span className="text-xs px-2 py-0.5 rounded bg-[#cc9166]/20 text-[#cc9166] border border-[#cc9166]/40">V2 (사이드바·메인 구조)</span>
            </h1>
            <p className="text-xs text-[#8b8e9d]">사이드바: 조회·목표차·소매가 | 메인: 비교 목록(좌) · 선택 상세(우) 반반 나란히</p>
          </div>
        </div>
      </div>

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

            {/* 상태 메시지 알림 (검색 중/경고/안내) */}
            {cockpit.searchStatus && (
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

          {/* 2) 목표차 한 줄 정보 (차명 · 등급 · 연식 · 주행거리) */}
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
            <div className="flex items-center justify-between font-mono text-xs text-[#8b8e9d] pt-1 border-t border-[#1e2029]">
              <span>연식 <strong className="text-zinc-200 font-semibold">{targetYear}</strong></span>
              <span>주행거리 <strong className="text-zinc-200 font-semibold">{targetMileage}</strong></span>
            </div>
          </div>

          {/* 2-1) 추가 옵션 및 매칭 섹션 */}
          <SidebarOptionSection
            targetOptions={cockpit.targetOptions}
            optionsTag={cockpit.optionsTag}
            selectedEncar={cockpit.selectedEncar}
            targetCatalog={cockpit.targetNewCarCatalog}
            historyOptionTotalMan={cockpit.targetCarHistory?.totalOptionPrice}
            unclassifiedBalance={cockpit.unclassifiedBalance}
          />


        </aside>

        {/* [메인 영역 (오른쪽, 나머지 너비)] */}
        <main className="flex-1 min-w-0 w-full space-y-4">
          {/* 상단 2열: 최종 소매가 & 참고 지표 카드 (목업 구조) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 1) 최종 소매가 1카드 */}
            <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-4 shadow-sm flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-[#8b8e9d] uppercase tracking-wider block">
                  최종 소매가
                </span>
                <p className="text-[11px] text-[#5e616e] mt-0.5">기존 콕핏 엔진 산출 검증 소매가</p>
              </div>
              <div className="text-right">
                <span className="text-2xl sm:text-3xl font-black text-sky-400 font-mono tracking-tight">
                  {finalPriceText}
                </span>
              </div>
            </div>

            {/* 2) 참고 한 줄 (엔카 역산 기준가 · 무사고 평균 · 차얼마 기준소매가) */}
            <div className="bg-[#0b0c10] border border-[#1b1e28] rounded-xl p-3.5 space-y-2 text-xs flex flex-col justify-center">
              <span className="font-semibold text-[#8b8e9d] block text-[11px] uppercase">참고 지표</span>
              <div className="grid grid-cols-3 gap-2 font-mono text-zinc-300 text-xs">
                <div>
                  <span className="text-zinc-500 text-[10px] block">엔카 역산 기준가</span>
                  <strong className="text-zinc-100 font-bold text-xs truncate block">{rawStdText}</strong>
                </div>
                <div>
                  <span className="text-zinc-500 text-[10px] block">무사고 평균</span>
                  <strong className="text-zinc-100 font-bold text-xs truncate block">{cohortNoAccText}</strong>
                </div>
                <div>
                  <span className="text-zinc-500 text-[10px] block">차얼마 기준소매가</span>
                  <strong className="text-zinc-100 font-bold text-xs truncate block">{chaolmaRetailText}</strong>
                </div>
              </div>
            </div>
          </div>

          {/* 비교 목록(왼쪽 절반)과 선택 상세(오른쪽 절반) 나란히 배치 */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 items-start">
            {/* 좌측 절반: 비교 목록 (엔카 / 케이카 탭 전환) */}
            <div className="min-w-0 w-full space-y-3">
              {/* 상단 탭 토글 (엔카 / 케이카 / 헤이딜러 낙찰) */}
              <div className="flex items-center justify-between gap-2">
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

              {/* 탭 본문 (엔카 / 케이카 / 헤이딜러 비교 목록): 마운트 유지 및 hidden 토글로 탭 전환 시 캐시 보존 및 무재호출 보장 */}
              <div className="max-h-[640px] overflow-y-auto rounded-xl">
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
                    errorMessage={cockpit.encarErrorMessage}
                  />
                </div>
                <div className={activeCompTab === 'kcar' ? 'block' : 'hidden'}>
                  <ComparableKcarV2Section
                    kcarList={cockpit.kcarStats?.cars || []}
                    selectedCarCd={selectedKcarCarCd}
                    onSelectCar={(carCd) => setSelectedKcarCarCd(carCd)}
                    yearModel={cockpit.yearModel}
                    isLoading={cockpit.isKcarLoading}
                    totalCount={cockpit.kcarStats?.count || cockpit.kcarStats?.cars?.length || 0}
                    strictCount={cockpit.kcarStats?.strictCount ?? (cockpit.kcarStats?.count || cockpit.kcarStats?.cars?.length || 0)}
                    isInitialState={isInitialState}
                    errorMessage={cockpit.kcarStats?.message}
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

            {/* 우측 절반: 선택 차량 상세 & 2D 상태도 (낙찰 탭 + 낙찰 선택 시 낙찰 상세, 그 외에는 마지막 소매 차량 상세 유지) */}
            <div className="min-w-0 w-full">
              <div className={activeCompTab === 'heydealer' && Boolean(cockpit.selectedHeydealerBid) ? 'block' : 'hidden'}>
                <SelectedHeydealerBidDetailV2Section
                  selectedHeydealerBid={cockpit.selectedHeydealerBid}
                />
              </div>
              <div className={!(activeCompTab === 'heydealer' && Boolean(cockpit.selectedHeydealerBid)) && lastRetailTab === 'encar' ? 'block' : 'hidden'}>
                <SelectedCarDetailV2Section
                  selectedEncar={cockpit.selectedEncar}
                  isInspectionLoading={cockpit.isInspectionLoading}
                />
              </div>
              <div className={!(activeCompTab === 'heydealer' && Boolean(cockpit.selectedHeydealerBid)) && lastRetailTab === 'kcar' ? 'block' : 'hidden'}>
                <SelectedKcarDetailV2Section
                  selectedKcar={selectedKcar}
                />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};
