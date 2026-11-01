import React from 'react';
import { useBiddingCockpit } from '@/components/BiddingCockpit/hooks/useBiddingCockpit';
import { Search, ExternalLink, Car, AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react';
import { ComparableEncarV2Section } from './ComparableEncarV2Section';
import { SelectedCarDetailV2Section } from './SelectedCarDetailV2Section';

export const BiddingCockpitV2Tab: React.FC = () => {
  const cockpit = useBiddingCockpit({
    onSaveToLedger: () => {},
  });

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
    <div className="w-full max-w-5xl mx-auto space-y-6 py-4">
      {/* 새 버전 1단계 안내 헤더 */}
      <div className="flex items-center justify-between border-b border-[#1f222e] pb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[#cc9166]/20 border border-[#cc9166]/40 flex items-center justify-center">
            <Car className="w-4 h-4 text-[#cc9166]" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white flex items-center gap-2">
              비딩 콕핏 <span className="text-xs px-2 py-0.5 rounded bg-[#cc9166]/20 text-[#cc9166] border border-[#cc9166]/40">V2 (1단계)</span>
            </h1>
            <p className="text-xs text-[#8b8e9d]">최소 구성 틀: 조회 입력 · 목표차 요약 · 최종 소매가 · 참고 지표</p>
          </div>
        </div>
      </div>

      {/* 1) 조회 입력 영역 (매물 URL · 차량번호 · 주행거리 · 조회 버튼) */}
      <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-5 shadow-sm space-y-4">
        <div className="text-xs font-semibold text-[#8b8e9d] uppercase tracking-wider">
          조회 입력
        </div>

        {/* 헤이딜러 매물 URL 조회 */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
          <div className="flex-1">
            <input
              type="text"
              value={cockpit.heydealerUrl}
              onChange={(e) => cockpit.setHeydealerUrl(e.target.value)}
              placeholder="헤이딜러 매물 URL 또는 경매 ID (예: https://dealer.heydealer.com/cars/xxxx)"
              className="w-full px-3.5 py-2.5 rounded-lg bg-[#161822] border border-[#262938] text-xs sm:text-sm text-white placeholder-[#5e616e] focus:outline-none focus:border-[#cc9166] transition font-mono"
            />
          </div>
          <button
            type="button"
            onClick={cockpit.handleHeydealerAiEstimate}
            disabled={cockpit.isAiEstimating}
            className="px-4 py-2.5 rounded-lg bg-gradient-to-r from-amber-600/50 to-[#cc9166]/60 hover:from-amber-600/70 hover:to-[#cc9166]/80 text-xs sm:text-sm font-bold text-white border border-[#cc9166]/60 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5 shrink-0"
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
        <div className="relative flex py-1 items-center">
          <div className="flex-grow border-t border-[#1e2029]" />
          <span className="flex-shrink mx-3 text-[11px] text-[#5e616e]">또는 차량번호 직접 조회</span>
          <div className="flex-grow border-t border-[#1e2029]" />
        </div>

        {/* 차량번호 & 주행거리 조회 */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-2">
          <div className="sm:col-span-6">
            <input
              type="text"
              value={cockpit.carNumber}
              onChange={(e) => cockpit.setCarNumber(e.target.value)}
              placeholder="차량번호 (예: 12가3456)"
              className="w-full px-3.5 py-2.5 rounded-lg bg-[#161822] border border-[#262938] text-xs sm:text-sm text-white placeholder-[#5e616e] focus:outline-none focus:border-blue-500 transition font-mono"
              onKeyDown={(e) => {
                if (e.key === 'Enter') cockpit.handleLookupCarNumber();
              }}
            />
          </div>
          <div className="sm:col-span-4">
            <input
              type="number"
              value={cockpit.mileageKm || ''}
              onChange={(e) => cockpit.setMileageKm(Number(e.target.value))}
              placeholder="주행거리 (km)"
              className="w-full px-3.5 py-2.5 rounded-lg bg-[#161822] border border-[#262938] text-xs sm:text-sm text-white placeholder-[#5e616e] focus:outline-none focus:border-blue-500 transition font-mono"
              onKeyDown={(e) => {
                if (e.key === 'Enter') cockpit.handleLookupCarNumber();
              }}
            />
          </div>
          <div className="sm:col-span-2">
            <button
              type="button"
              onClick={() => cockpit.handleLookupCarNumber()}
              disabled={cockpit.isSearchingCar}
              className="w-full h-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs sm:text-sm font-bold text-white transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5 shadow-sm"
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
      <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl px-5 py-3.5 flex flex-wrap items-center justify-between gap-3 text-xs sm:text-sm">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold text-[#8b8e9d] uppercase">목표 차량:</span>
          <span className="font-bold text-white">{targetCarName}</span>
          <span className="text-[#5e616e]">/</span>
          <span className="text-zinc-300">{targetDetailModel}</span>
        </div>
        <div className="flex items-center gap-3 font-mono text-xs text-[#8b8e9d]">
          <span>연식 <strong className="text-zinc-200 font-semibold">{targetYear}</strong></span>
          <span className="text-[#3b3e4f]">|</span>
          <span>주행거리 <strong className="text-zinc-200 font-semibold">{targetMileage}</strong></span>
        </div>
      </div>

      {/* 3) 최종 소매가 1카드 */}
      <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-6 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <span className="text-xs font-semibold text-[#8b8e9d] uppercase tracking-wider block mb-1">
            최종 소매가
          </span>
          <p className="text-xs text-[#5e616e]">기존 콕핏 엔진이 산출한 검증 소매가</p>
        </div>
        <div className="text-right">
          <span className="text-3xl sm:text-4xl font-black text-sky-400 font-mono tracking-tight">
            {finalPriceText}
          </span>
        </div>
      </div>

      {/* 4) 참고 한 줄 (엔카 역산 기준가 · 무사고 평균 · 차얼마 기준소매가) */}
      <div className="bg-[#0b0c10] border border-[#1b1e28] rounded-xl px-5 py-3 flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="font-semibold text-[#8b8e9d]">참고 지표:</span>
        <div className="flex items-center gap-3 flex-wrap font-mono text-zinc-300">
          <span>
            엔카 역산 기준가 <strong className="text-zinc-100 font-bold">{rawStdText}</strong>
          </span>
          <span className="text-[#3b3e4f]">|</span>
          <span>
            무사고 평균 <strong className="text-zinc-100 font-bold">{cohortNoAccText}</strong>
          </span>
          <span className="text-[#3b3e4f]">|</span>
          <span>
            차얼마 기준소매가 <strong className="text-zinc-100 font-bold">{chaolmaRetailText}</strong>
          </span>
        </div>
      </div>

      {/* 5) 엔카 비교 목록 (V2 전용 분리 컴포넌트) */}
      <ComparableEncarV2Section
        encarList={cockpit.encarList || []}
        selectedEncarId={cockpit.selectedEncarId}
        onSelectCar={cockpit.handleSelectEncarCar}
        isLoading={cockpit.isEncarLoading}
        totalModelCount={cockpit.encarTotalModelCount || 0}
        filteredCount={cockpit.encarFilteredCount || 0}
        isInitialState={isInitialState}
        errorMessage={cockpit.encarErrorMessage}
      />

      {/* 6) 선택 차량 상세 & 2D 상태도 (V2 전용 분리 컴포넌트) */}
      <SelectedCarDetailV2Section
        selectedEncar={cockpit.selectedEncar}
        isInspectionLoading={cockpit.isInspectionLoading}
      />
    </div>
  );
};
