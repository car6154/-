import React from 'react';
import {
  Sparkles,
  ExternalLink,
  Zap,
} from 'lucide-react';
import { EncarItem } from './ComparableEncarSection';

export interface ValuationSummarySectionProps {
  carName: string;
  carNumber?: string;
  detailModel: string;
  manufacturer?: string;
  yearModel: number;
  mileageKm: number;
  expectedSellPrice: number;
  effectiveSellPrice: number;
  aiRetailPrice?: number;
  aiSafeBidCeiling?: number;
  targetMargin: number;
  repairCostTotal: number;
  safeBidCeiling: number;
  optionsTag?: string;
  outerRepairCount?: number;
  biddingVerdict?: any;
  isEncarLoading: boolean;
  encarSourceUrl?: string;
  autoplusStats: { matchedCount: number; [key: string]: any };
  currentAssessment: any;
  targetCarHistory: any;
  liveMarketStats: any;
  liveEncarSoldStats: any;
  encarStats: { count: number; min: number; max: number; avg: number; median: number };
  encarValuation: any;
  encarYearStats: Array<{ year: number; avg: number; count: number; isTarget: boolean }>;
  encarSoldList: any[];
  matchedAutoplusList: any[];
  matchedAuctionList: any[];
  encarList: EncarItem[];
  soldTabMode: 'none' | 'encar' | 'autoplus' | 'wholesale';
  setSoldTabMode: (mode: 'none' | 'encar' | 'autoplus' | 'wholesale') => void;
  showTrimColumn: boolean;
  onRescanEncar: () => void;
  onOpenHistoryModal: () => void;
}

export const ValuationSummarySection: React.FC<ValuationSummarySectionProps> = ({
  carName,
  carNumber,
  detailModel,
  manufacturer,
  yearModel,
  mileageKm,
  expectedSellPrice,
  effectiveSellPrice,
  aiRetailPrice = 0,
  aiSafeBidCeiling = 0,
  targetMargin,
  repairCostTotal,
  safeBidCeiling,
  optionsTag,
  outerRepairCount = 0,
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
  onRescanEncar,
  onOpenHistoryModal,
}) => {
  // 🏢 [KCAR] 실시간 공식 검색 필터 URL 동적 생성 (모델명 + 연식 ±1년 + 주행거리 ±3만km)
  const kcarUrl = React.useMemo(() => {
    const cond: Record<string, any> = {};
    const searchText = (carName || '').trim();
    if (searchText) {
      cond.wr_txt_idx = searchText;
    }

    if (yearModel && Number(yearModel) > 0) {
      const yVal = Number(yearModel);
      const kcarYear = yVal < 100 ? 2000 + yVal : yVal;
      cond.wr_gt_mfg_dt = `${kcarYear - 1}01`;
      cond.wr_lt_mfg_dt = `${kcarYear + 1}12`;
    }

    if (mileageKm && Number(mileageKm) > 0) {
      const milVal = Number(mileageKm);
      const roundedMil = Math.round(milVal / 10000) * 10000;
      cond.wr_gt_milg = Math.max(0, roundedMil - 30000);
      cond.wr_lt_milg = roundedMil + 30000;
    }

    if (Object.keys(cond).length > 0) {
      return `https://www.kcar.com/bc/search?searchCond=${encodeURIComponent(JSON.stringify(cond))}`;
    }
    return 'https://www.kcar.com/bc/search';
  }, [carName, yearModel, mileageKm]);

  return (
        <div className="bg-[#0e0f13] border border-[#262833] rounded-xl p-4 sm:p-5 shadow-lg space-y-3.5">
          
          {/* Top Bar: Title, Specs */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-[#232634]">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-base font-black text-white font-serif-display flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <span>🎯 AI 권장 시세 &amp; 비딩 결론</span>
              </span>
              <span className="text-xs sm:text-sm px-2.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/35 font-bold font-mono">
                {carName} {detailModel} ({yearModel}년식 / {mileageKm.toLocaleString()}km)
              </span>
              {autoplusStats.matchedCount > 0 && (
                <span className="text-xs px-2.5 py-0.5 rounded bg-emerald-500/25 text-emerald-300 border border-emerald-500/40 font-bold">
                  🏢 자사 실적 {autoplusStats.matchedCount}대 매칭
                </span>
              )}
            </div>
          </div>

          {/* 🎯 핵심 3대 지표 카드: [매입가] | [판매가] | [이익금] (우측 메인 상단은 순수 AI 정밀 소매가 기준으로 고정) */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {/* 1. 매입가 */}
            <div className="bg-gradient-to-br from-[#0c1a14] via-[#102119] to-[#0e1c15] border border-emerald-500/40 rounded-xl px-3 py-2 sm:px-3.5 sm:py-2.5 shadow-sm flex items-center justify-between min-h-[56px]">
              <div className="space-y-0.5">
                <div className="text-[11px] font-bold text-emerald-400 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span>매입가</span>
                  <span className="text-[10px] text-zinc-400 font-normal hidden sm:inline">(안전마진 반영 권장가)</span>
                </div>
                <div className="text-lg sm:text-xl font-black text-emerald-400 font-mono tracking-tight leading-none">
                  {(aiSafeBidCeiling || safeBidCeiling) > 0 ? `${(aiSafeBidCeiling || safeBidCeiling).toLocaleString()}만원` : '-'}
                </div>
              </div>
              <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-base shrink-0">
                🛡️
              </div>
            </div>

            {/* 2. 판매가 */}
            <div className="bg-gradient-to-br from-[#0e1726] via-[#121f33] to-[#0f192b] border border-sky-500/40 rounded-xl px-3 py-2 sm:px-3.5 sm:py-2.5 shadow-sm flex items-center justify-between min-h-[56px]">
              <div className="space-y-0.5">
                <div className="text-[11px] font-bold text-sky-400 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
                  <span>판매가</span>
                  <span className="text-[10px] text-zinc-400 font-normal hidden sm:inline">(엔카 동급 및 자사실거래)</span>
                </div>
                <div className="text-lg sm:text-xl font-black text-sky-300 font-mono tracking-tight leading-none">
                  {aiRetailPrice > 0 ? `${aiRetailPrice.toLocaleString()}만원` : '-'}
                </div>
              </div>
              <div className="w-8 h-8 rounded-lg bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-base shrink-0">
                🏷️
              </div>
            </div>

            {/* 3. 이익금 */}
            <div className="bg-gradient-to-br from-[#1c140c] via-[#241a10] to-[#1e150d] border border-amber-500/40 rounded-xl px-3 py-2 sm:px-3.5 sm:py-2.5 shadow-sm flex items-center justify-between min-h-[56px]">
              <div className="space-y-0.5">
                <div className="text-[11px] font-bold text-amber-400 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                  <span>이익금</span>
                  <span className="text-[10px] text-zinc-400 font-normal hidden sm:inline">(수수료·수리비 차감 후)</span>
                </div>
                <div className="text-lg sm:text-xl font-black text-amber-400 font-mono tracking-tight leading-none">
                  {targetMargin > 0 ? `+${targetMargin.toLocaleString()}만원` : '-'}
                </div>
              </div>
              <div className="w-8 h-8 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-base shrink-0">
                💰
              </div>
            </div>
          </div>

          {/* 🛡️ 차량 상태 판정 및 원부·카히스토리 통합 브리핑 바 (클릭 시 전용 대형 리포트 모달 오픈) */}
          <div 
            onClick={onOpenHistoryModal}
            className="bg-[#121622] hover:bg-[#161c2d] border border-sky-500/35 hover:border-sky-400/60 rounded-xl p-3 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-md transition cursor-pointer group"
            title="클릭 시 국토부 등록원부 및 카히스토리 상세 모달 열기"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span 
                className="px-2.5 py-0.5 rounded-full text-xs font-black border flex items-center gap-1"
                style={{ 
                  backgroundColor: `${currentAssessment.gradeBadgeColor}20`, 
                  color: currentAssessment.gradeBadgeColor, 
                  borderColor: `${currentAssessment.gradeBadgeColor}50` 
                }}
              >
                <span>🛡️</span>
                <span>{currentAssessment.gradeName}</span>
              </span>
              
              {/* 핵심 검증 태그 칩들: '5단계' 및 '주행' 제외, 실무 우선순위 반영 */}
              <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                {/* 1. 사고 및 내차피해 */}
                <span className={`px-2 py-0.5 rounded border ${currentAssessment.accidentDamage.isPass ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border-rose-500/40 font-bold'}`}>
                  사고: {currentAssessment.accidentDamage.status === 'PERFECT' ? '무사고' : currentAssessment.accidentDamage.status === 'MINOR' ? '단순수리' : '골격/결격'}
                  {outerRepairCount > 0 ? (
                    <span className="ml-1 text-[10px] opacity-90 font-mono">
                      (외판 {outerRepairCount}판)
                    </span>
                  ) : null}
                  {targetCarHistory && targetCarHistory.myCarAccidentCount > 0 ? (
                    <span className="ml-1 text-[10px] opacity-90 font-mono">
                      (내차 {targetCarHistory.myCarAccidentCount}건/{targetCarHistory.myCarAccidentCost}만)
                    </span>
                  ) : null}
                </span>

                {/* 2. 침수 / 전손 */}
                <span className={`px-2 py-0.5 rounded border ${(!targetCarHistory || (targetCarHistory.floodedCount === 0 && targetCarHistory.totalLossCount === 0)) ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border-rose-500/40 font-bold animate-pulse'}`}>
                  침수·전손: {targetCarHistory && (targetCarHistory.floodedCount > 0 || targetCarHistory.totalLossCount > 0) 
                    ? `🚨${targetCarHistory.floodedCount + targetCarHistory.totalLossCount}건` 
                    : '0건'}
                </span>

                {/* 3. 용도 및 소유자 변경 */}
                <span className={`px-2 py-0.5 rounded border ${currentAssessment.ownershipUsage.isPass ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' : 'bg-amber-500/20 text-amber-300 border-amber-500/40'}`}>
                  용도: {currentAssessment.ownershipUsage.status === 'SINGLE' ? '1인신조' : currentAssessment.ownershipUsage.status === 'RENT' ? '렌트이력' : '자가용'}
                  {targetCarHistory && targetCarHistory.ownerChangedCount > 0 && !targetCarHistory.isSingleOwner ? (
                    <span className="ml-1 text-[10px] opacity-90 font-mono">({targetCarHistory.ownerChangedCount}회 변경)</span>
                  ) : null}
                </span>

                {/* 4. 원부 (압류/저당) */}
                <span className={`px-2 py-0.5 rounded border ${currentAssessment.legalRights.isPass ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border-rose-500/40 font-bold'}`}>
                  원부: {currentAssessment.legalRights.isPass 
                    ? '클린' 
                    : (targetCarHistory?.originDoc && (targetCarHistory.originDoc.seizure_count > 0 || targetCarHistory.originDoc.mortgage_count > 0)
                        ? `압류${targetCarHistory.originDoc.seizure_count} 저당${targetCarHistory.originDoc.mortgage_count}`
                        : '하자')}
                </span>

                {/* 5. 정기검사 */}
                <span className={`px-2 py-0.5 rounded border ${currentAssessment.inspectionValidity.isPass ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border-rose-500/40 font-bold'}`}>
                  검사: {currentAssessment.inspectionValidity.status === 'EXPIRED' ? '🚨만료' : currentAssessment.inspectionValidity.status === 'EXPIRING_SOON' ? '⚠️임박' : '유효'}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3 self-end md:self-auto shrink-0">
              {currentAssessment.totalAdjustmentMan !== 0 && (
                <span className="text-xs font-mono font-bold">
                  규칙 가감: <span className={currentAssessment.totalAdjustmentMan > 0 ? 'text-emerald-400' : 'text-rose-400'}>
                    {currentAssessment.totalAdjustmentMan > 0 ? `+${currentAssessment.totalAdjustmentMan}만` : `${currentAssessment.totalAdjustmentMan}만`}
                  </span>
                </span>
              )}
              <span className="text-xs text-sky-300 font-bold bg-sky-500/20 group-hover:bg-sky-500/30 px-2.5 py-1 rounded-lg border border-sky-400/40 flex items-center gap-1 transition">
                원부·카히스토리 정밀리포트 ↗
              </span>
            </div>
          </div>

          {/* 📊 [TOP] J-PRO 빅데이터 실적 분석 (회전율·마진·수요) & ⚡ AI 종합 비딩 전략 판정 (Streamlit 8501 원본 100% 동일 구조) */}
          {liveMarketStats && liveMarketStats.has_data && (
            <div className="space-y-2.5 pb-2 border-b border-[#232634]">
              {/* 상단 안내 문구 */}
              <div className="text-xs text-slate-300 flex flex-wrap items-center gap-1.5 leading-relaxed">
                <span>💡 순수 내수 소매 완판 데이터 <strong className="text-white">{liveMarketStats.pure_sales_count ? Number(liveMarketStats.pure_sales_count).toLocaleString() : '6,170'}건</strong> 중 <strong className="text-sky-300">[{liveMarketStats.matched_name || `${carName} ${detailModel}`}]</strong> 실적(<strong className="text-emerald-400">{liveMarketStats.total_count || 0}대</strong>) 분석 결과입니다.</span>
                {liveMarketStats.matched_tier && (
                  <span className="bg-[#cc9166]/20 border border-[#cc9166] text-[#cc9166] px-2 py-0.5 rounded-full text-[11px] font-bold">
                    {liveMarketStats.matched_tier}
                  </span>
                )}
                {liveMarketStats.year_diff_note && (
                  <span className="bg-rose-500/20 border border-rose-500 text-rose-300 px-2 py-0.5 rounded-full text-[11px] font-bold">
                    ⚠️ {liveMarketStats.year_diff_note}
                  </span>
                )}
                <span className="text-slate-400 text-[11px]">
                  (경매·도매 출고 {Number(liveMarketStats.auction_filtered_count || 1339).toLocaleString()}건 왜곡 방지 자동 제외 완료)
                </span>
              </div>

              {/* 4대 핵심 KPI 카드 (슬림 템플릿 & 공간 절약) */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="bg-[#121319] border border-[#262835] rounded-xl px-2.5 py-1.5 flex items-center gap-2.5 shadow-sm min-h-[52px]">
                  <div className="w-7 h-7 rounded-md bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center text-sm shrink-0">⏱️</div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[10px] text-zinc-400 font-medium">평균 판매소요</div>
                    <div className="flex items-baseline gap-1.5 flex-wrap">
                      <span className="text-sm sm:text-base font-bold font-mono text-emerald-400">
                        {liveMarketStats.avg_days || 0}일
                      </span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300 font-medium truncate max-w-[85px]" title={liveMarketStats.turnover_grade || '정상 유통'}>
                        {liveMarketStats.turnover_grade ? String(liveMarketStats.turnover_grade).split('(')[0].trim() : '정상 회전'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="bg-[#121319] border border-[#262835] rounded-xl px-2.5 py-1.5 flex items-center gap-2.5 shadow-sm min-h-[52px]">
                  <div className="w-7 h-7 rounded-md bg-slate-800/60 border border-slate-700/50 flex items-center justify-center text-sm shrink-0">🏷️</div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[10px] text-zinc-400 font-medium">과거 평균 판매가</div>
                    <div className="text-sm sm:text-base font-bold text-slate-100 font-mono">
                      {Number(liveMarketStats.avg_sell_price || 0).toLocaleString()}만원
                    </div>
                  </div>
                </div>

                <div className="bg-[#121319] border border-[#262835] rounded-xl px-2.5 py-1.5 flex items-center gap-2.5 shadow-sm min-h-[52px]">
                  <div className="w-7 h-7 rounded-md bg-slate-800/60 border border-slate-700/50 flex items-center justify-center text-sm shrink-0">🛣️</div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[10px] text-zinc-400 font-medium">완판 평균 주행거리</div>
                    <div className="text-sm sm:text-base font-bold text-slate-200 font-mono">
                      {Number(liveMarketStats.avg_mileage || 0).toLocaleString()}km
                    </div>
                  </div>
                </div>

                <div className="bg-[#121319] border border-[#262835] rounded-xl px-2.5 py-1.5 flex items-center gap-2.5 shadow-sm min-h-[52px]">
                  <div className="w-7 h-7 rounded-md bg-amber-500/10 border border-amber-500/25 flex items-center justify-center text-sm shrink-0">💰</div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[10px] text-zinc-400 font-medium">과거 평균 실현마진</div>
                    <div className="text-sm sm:text-base font-bold text-amber-300 font-mono">
                      +{Number(liveMarketStats.avg_profit || 0).toLocaleString()}만원 <span className="text-[10px] text-zinc-400 font-normal">({liveMarketStats.profit_rate || 0}%)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ⚡ AI 종합 비딩 전략 판정 브리핑 박스 (참고용 슬림 배너) */}
          {biddingVerdict && (
            <div className="bg-[#141722] border border-amber-500/30 rounded-xl p-2.5 space-y-1.5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-amber-300 flex items-center gap-1">
                    <Zap className="w-3.5 h-3.5 text-amber-400" />
                    <span>AI 비딩 전략 브리핑</span>
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-bold" style={{ backgroundColor: `${biddingVerdict.badgeColor}25`, color: biddingVerdict.badgeColor, border: `1px solid ${biddingVerdict.badgeColor}` }}>
                    {biddingVerdict.badge}
                  </span>
                </div>

                {/* 엔카 완판 핵심 팩트 칩 3종 */}
                {liveEncarSoldStats && liveEncarSoldStats.has_data && (
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                    <span className="px-2 py-0.5 rounded bg-[#1a1d2b] border border-[#2b3044] text-zinc-300">
                      최근 30일: <strong>{liveEncarSoldStats.count_30d}대 완판</strong>
                    </span>
                    {Number(liveEncarSoldStats.sold_avg_price || 0) > 0 && (
                      <span className="px-2 py-0.5 rounded bg-[#1a1d2b] border border-[#2b3044] text-zinc-300">
                        완판 평균: <strong className="text-amber-300 font-mono">{Number(liveEncarSoldStats.sold_avg_price).toLocaleString()}만</strong>
                      </span>
                    )}
                    <span className="px-2 py-0.5 rounded bg-[#1a1d2b] border border-[#2b3044] text-zinc-300">
                      평균 소요: <strong className="text-emerald-400 font-mono">{liveEncarSoldStats.sold_avg_days || 28}일</strong>
                    </span>
                  </div>
                )}
              </div>

              <div className="text-xs text-slate-300 space-y-0.5 leading-relaxed pt-0.5">
                <p dangerouslySetInnerHTML={{ __html: biddingVerdict.mainText }} />
                <p className="text-amber-300 font-bold flex items-center gap-1 pt-0.5">
                  <span>👉</span>
                  <span>{biddingVerdict.recommendation}</span>
                </p>
              </div>
            </div>
          )}

              {/* Sub Navigation Bar for Data Transparency (3개 서브탭) */}
              <div className="flex items-center gap-2 overflow-x-auto scrollbar-none text-xs pt-1 border-t border-[#232634]">
                <button
                  type="button"
                  onClick={() => setSoldTabMode(soldTabMode === 'encar' ? 'none' : 'encar')}
                  className={`px-3 py-1.5 rounded-lg font-bold transition cursor-pointer flex items-center gap-1.5 ${
                    soldTabMode === 'encar'
                      ? 'bg-blue-500/25 text-blue-200 border border-blue-500/40'
                      : 'text-zinc-300 hover:text-white hover:bg-[#181a24] border border-transparent'
                  }`}
                >
                  <span>🚗 엔카 팔린매물 ({encarSoldList.length}건) {soldTabMode === 'encar' ? '▲' : '▼'}</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSoldTabMode(soldTabMode === 'autoplus' ? 'none' : 'autoplus')}
                  className={`px-3 py-1.5 rounded-lg font-bold transition cursor-pointer flex items-center gap-1.5 ${
                    soldTabMode === 'autoplus'
                      ? 'bg-emerald-500/25 text-emerald-200 border border-emerald-500/40'
                      : 'text-zinc-300 hover:text-white hover:bg-[#181a24] border border-transparent'
                  }`}
                >
                  <span>🏢 자사 소매 실적 ({matchedAutoplusList.length}대) {soldTabMode === 'autoplus' ? '▲' : '▼'}</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSoldTabMode(soldTabMode === 'wholesale' ? 'none' : 'wholesale')}
                  className={`px-3 py-1.5 rounded-lg font-bold transition cursor-pointer flex items-center gap-1.5 ${
                    soldTabMode === 'wholesale'
                      ? 'bg-amber-500/25 text-amber-200 border border-amber-500/40'
                      : 'text-zinc-300 hover:text-white hover:bg-[#181a24] border border-transparent'
                  }`}
                >
                  <span>📦 자사 도매 실적 ({matchedAuctionList.length}대) {soldTabMode === 'wholesale' ? '▲' : '▼'}</span>
                </button>
              </div>

          {/* Collapsible Detail Tab 1: 엔카 팔린매물 */}
          {soldTabMode === 'encar' && (
            <div className="space-y-2 pt-1 border-t border-[#232634]">
              <div className="flex justify-between items-center text-xs sm:text-sm text-zinc-300">
                <span>엔카 최근 판매완료(광고종료) 기록 (<strong className="text-blue-400 font-bold">{encarSoldList.length}건</strong>)</span>
                <span className="text-xs text-amber-300 font-medium">※ 실측 스냅샷 기반</span>
              </div>
              {encarSoldList.length > 0 ? (
                <div className="overflow-x-auto max-h-72 overflow-y-auto border border-[#262833] rounded-xl">
                  <table className="w-full text-left text-xs sm:text-sm text-zinc-200">
                    <thead className="bg-[#14151b] text-xs text-zinc-400 sticky top-0 uppercase border-b border-[#262833]">
                      <tr>
                        <th className="p-2.5">차량정보</th>
                        <th className="p-2.5 text-center">연식(년/월)</th>
                        <th className="p-2.5 text-right">주행거리</th>
                        <th className="p-2.5 text-center">판매구분</th>
                        <th className="p-2.5 text-right">소매 판매가</th>
                        <th className="p-2.5 text-right">판매일</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#232634] bg-[#0a0b0e]">
                      {encarSoldList.map((s) => (
                        <tr key={s.id} className="hover:bg-[#14151c] transition">
                          <td className="p-2.5 text-white font-bold text-xs sm:text-sm">
                            {s.encarUrl ? (
                              <a
                                href={s.encarUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="hover:text-blue-400 hover:underline inline-flex items-center gap-1.5"
                                title="엔카 원본 상세페이지 보기"
                              >
                                <span>{s.carName || s.subModel || '차량정보 없음'}</span>
                                <ExternalLink className="w-3 h-3 text-zinc-500 hover:text-blue-400 shrink-0 inline" />
                              </a>
                            ) : (
                              <span>{s.carName || s.subModel || '차량정보 없음'}</span>
                            )}
                          </td>
                          <td className="p-2.5 text-center text-xs text-blue-400 font-mono">
                            {s.year ? (s.year.includes('식') || s.year.includes('년') ? s.year : `${s.year}년`) : '-'}
                          </td>
                          <td className="p-2.5 text-right text-xs text-white font-mono">
                            {s.mileage > 0 ? `${s.mileage.toLocaleString()}km` : '-'}
                          </td>
                          <td className="p-2.5 text-center text-xs text-zinc-400 font-mono">
                            {s.saleType || '-'}
                          </td>
                          <td className="p-2.5 text-right font-bold text-emerald-400 font-mono">
                            {s.finalPrice > 0 ? `${s.finalPrice.toLocaleString()}만` : '-'}
                          </td>
                          <td className="p-2.5 text-right text-xs text-zinc-400 font-mono">
                            {s.soldDate || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-4 text-center bg-[#0a0b0e] rounded-xl border border-[#262833] text-xs sm:text-sm text-zinc-400 font-medium">
                  💡 최근 90일 내 매칭된 엔카 판매완료(광고종료) 스냅샷 이력이 없습니다.
                </div>
              )}
            </div>
          )}

          {/* Collapsible Detail Tab 2: 자사 소매 실적 */}
          {soldTabMode === 'autoplus' && (
            <div className="space-y-2 pt-1 border-t border-[#232634]">
              <div className="flex justify-between items-center text-xs sm:text-sm text-zinc-300">
                <span>자사 소매 실적 DB 매물 (<strong className="text-emerald-400 font-bold">{matchedAutoplusList.length}대</strong>)</span>
                <span className="text-xs text-zinc-400">엔카 광고 집행 순수 소매 완판 데이터</span>
              </div>

              {/* 자사 DB 필터 조건 투명 공개 박스 */}
              <div className="bg-[#12131b] border border-[#232634] rounded-xl p-3 text-xs space-y-2">
                <div className="flex items-center justify-between text-zinc-300 border-b border-[#202230] pb-2">
                  <div className="flex items-center gap-1.5 font-bold text-emerald-400">
                    <span>🔍</span>
                    <span>자사 원장(2,964건) 매칭 필터 기준</span>
                  </div>
                  <span className="text-[11px] text-zinc-400">
                    매칭 결과: <strong className={matchedAutoplusList.length > 0 ? "text-emerald-400" : "text-amber-400"}>{matchedAutoplusList.length}대</strong>
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-zinc-300">
                  <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                    <div className="text-[10px] text-zinc-500">조회 차종</div>
                    <div className="font-bold text-white truncate" title={carName}>{carName || '-'}</div>
                  </div>
                  <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                    <div className="text-[10px] text-zinc-500">세부 모델/트림</div>
                    <div className="font-bold text-emerald-400 truncate" title={detailModel}>{detailModel || '기본형 (전체)'}</div>
                  </div>
                  <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                    <div className="text-[10px] text-zinc-500">연식 대역 (±1년)</div>
                    <div className="font-bold text-blue-400 font-mono">
                      {yearModel ? `${Number(yearModel) - 1}년 ~ ${Number(yearModel) + 1}년` : '연식 전체'}
                    </div>
                  </div>
                  <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                    <div className="text-[10px] text-zinc-500">매칭 판정</div>
                    <div className="font-bold text-amber-300 truncate font-mono">
                      {liveMarketStats?.matched_tier || (matchedAutoplusList.length > 0 ? '정밀 매칭' : '매칭 실적 없음')}
                    </div>
                  </div>
                </div>
                {liveMarketStats?.year_diff_note && (
                  <div className="text-[11px] text-amber-300 bg-amber-500/10 p-2 rounded border border-amber-500/20">
                    ℹ️ {liveMarketStats.year_diff_note}
                  </div>
                )}
              </div>

              {matchedAutoplusList.length > 0 ? (
                <div className="overflow-x-auto max-h-64 overflow-y-auto border border-[#262833] rounded-xl">
                  <table className="w-full text-left text-xs sm:text-sm text-zinc-200">
                    <thead className="bg-[#14151b] text-xs text-zinc-400 sticky top-0 uppercase border-b border-[#262833]">
                      <tr>
                        <th className="p-2.5">판매일자</th>
                        <th className="p-2.5">차량번호</th>
                        <th className="p-2.5">세부모델</th>
                        <th className="p-2.5">연식</th>
                        <th className="p-2.5 text-right">주행거리</th>
                        <th className="p-2.5 text-right">매입가</th>
                        <th className="p-2.5 text-right">소매 판매가</th>
                        <th className="p-2.5 text-center">경과일수</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#232634] bg-[#0a0b0e]">
                      {matchedAutoplusList.map((item: any, idx: number) => {
                        const rawBuy = Number(item.buyPrice);
                        const buyMan = rawBuy ? (rawBuy >= 100000 ? Math.round(rawBuy / 10000) : Math.round(rawBuy)) : null;
                        
                        const rawSell = Number(item.sellPrice);
                        const sellMan = rawSell ? (rawSell >= 100000 ? Math.round(rawSell / 10000) : Math.round(rawSell)) : null;

                        return (
                          <tr key={item.id || idx} className="hover:bg-[#14151c]">
                            <td className="p-2.5 text-xs text-zinc-400 font-mono">{item.soldDate || item.regDate || '-'}</td>
                            <td className="p-2.5 font-mono text-white font-bold">{item.carNumber || item.plate || '-'}</td>
                            <td className="p-2.5 text-white font-semibold text-xs sm:text-sm">{item.subModel || item.carName || '-'}</td>
                            <td className="p-2.5 text-xs text-blue-400 font-mono">{item.year ? `${item.year}년` : '-'}</td>
                            <td className="p-2.5 text-right text-xs text-white font-mono">{item.mileage > 0 ? `${Number(item.mileage).toLocaleString()}km` : '-'}</td>
                            <td className="p-2.5 text-right text-zinc-300 font-mono">
                              {buyMan !== null ? `${buyMan.toLocaleString()}만` : '-'}
                            </td>
                            <td className="p-2.5 text-right text-emerald-400 font-bold font-mono">
                              {sellMan !== null ? `${sellMan.toLocaleString()}만` : '-'}
                            </td>
                            <td className="p-2.5 text-center font-mono text-xs">{item.stockDays ? `${item.stockDays}일` : '0일'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-4 text-center bg-[#0a0b0e] rounded-xl border border-[#262833] text-xs sm:text-sm space-y-1.5">
                  <div className="text-amber-400 font-bold flex items-center justify-center gap-1.5">
                    <span>⚠️</span>
                    <span>자사 소매 실적 0건 (필터 조건 매칭 매물 없음)</span>
                  </div>
                  <div className="text-zinc-400 text-xs leading-relaxed max-w-lg mx-auto">
                    자사 전체 정산 원장(2,964건) 중 차종 <strong className="text-zinc-200">[{carName}]</strong>, 
                    세부모델 <strong className="text-zinc-200">[{detailModel || '기본형'}]</strong>, 
                    연식 대역 <strong className="text-zinc-200">[{yearModel ? `${Number(yearModel) - 1}~${Number(yearModel) + 1}년` : '전체'}]</strong> 
                    조건과 100% 일치하는 소매 완판 매물이 없습니다.
                  </div>
                  <div className="text-[11px] text-zinc-500 pt-1">
                    💡 팁: 해당 세부모델의 과거 자사 소매 실적이 없으므로, 상단 <strong className="text-blue-400">엔카 팔린매물 ({encarSoldList.length}건)</strong>의 시장 실거래 시세를 표준으로 참고하세요.
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Collapsible Detail Tab 3: 자사 도매 실적 */}
          {soldTabMode === 'wholesale' && (
            <div className="space-y-2 pt-1 border-t border-[#232634]">
              <div className="flex justify-between items-center text-xs sm:text-sm text-zinc-300">
                <span>자사 도매 실적 DB 매물 (<strong className="text-amber-400 font-bold">{matchedAuctionList.length}대</strong>)</span>
                <span className="text-xs text-zinc-400">도매/경매 낙찰 출고 데이터 (도매 바닥 시세)</span>
              </div>

              {/* 자사 도매 필터 조건 투명 공개 박스 */}
              <div className="bg-[#12131b] border border-[#232634] rounded-xl p-3 text-xs space-y-2">
                <div className="flex items-center justify-between text-zinc-300 border-b border-[#202230] pb-2">
                  <div className="flex items-center gap-1.5 font-bold text-amber-400">
                    <span>🔍</span>
                    <span>자사 경매/도매 원장 매칭 필터 기준</span>
                  </div>
                  <span className="text-[11px] text-zinc-400">
                    매칭 결과: <strong className={matchedAuctionList.length > 0 ? "text-emerald-400" : "text-amber-400"}>{matchedAuctionList.length}대</strong>
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-zinc-300">
                  <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                    <div className="text-[10px] text-zinc-500">조회 차종</div>
                    <div className="font-bold text-white truncate" title={carName}>{carName || '-'}</div>
                  </div>
                  <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                    <div className="text-[10px] text-zinc-500">세부 모델/트림</div>
                    <div className="font-bold text-amber-400 truncate" title={detailModel}>{detailModel || '기본형 (전체)'}</div>
                  </div>
                  <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                    <div className="text-[10px] text-zinc-500">연식 대역 (±1년)</div>
                    <div className="font-bold text-blue-400 font-mono">
                      {yearModel ? `${Number(yearModel) - 1}년 ~ ${Number(yearModel) + 1}년` : '연식 전체'}
                    </div>
                  </div>
                  <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                    <div className="text-[10px] text-zinc-500">매칭 판정</div>
                    <div className="font-bold text-amber-300 truncate font-mono">
                      {liveMarketStats?.matched_tier || (matchedAuctionList.length > 0 ? '정밀 매칭' : '매칭 실적 없음')}
                    </div>
                  </div>
                </div>
              </div>

              {matchedAuctionList.length > 0 ? (
                <div className="overflow-x-auto max-h-64 overflow-y-auto border border-[#262833] rounded-xl">
                  <table className="w-full text-left text-xs sm:text-sm text-zinc-200">
                    <thead className="bg-[#14151b] text-xs text-zinc-400 sticky top-0 uppercase border-b border-[#262833]">
                      <tr>
                        <th className="p-2.5">판매일자</th>
                        <th className="p-2.5">차량번호</th>
                        <th className="p-2.5">세부모델</th>
                        <th className="p-2.5">연식</th>
                        <th className="p-2.5 text-right">주행거리</th>
                        <th className="p-2.5 text-right">매입가</th>
                        <th className="p-2.5 text-right">도매 낙찰가</th>
                        <th className="p-2.5 text-center">경과일수</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#232634] bg-[#0a0b0e]">
                      {matchedAuctionList.map((item: any, idx: number) => {
                        const rawBuy = Number(item.buyPrice);
                        const buyMan = rawBuy ? (rawBuy >= 100000 ? Math.round(rawBuy / 10000) : Math.round(rawBuy)) : null;
                        
                        const rawSell = Number(item.sellPrice);
                        const sellMan = rawSell ? (rawSell >= 100000 ? Math.round(rawSell / 10000) : Math.round(rawSell)) : null;

                        return (
                          <tr key={item.id || idx} className="hover:bg-[#14151c]">
                            <td className="p-2.5 text-xs text-zinc-400 font-mono">{item.soldDate || item.regDate || '-'}</td>
                            <td className="p-2.5 font-mono text-white font-bold">{item.carNumber || item.plate || '-'}</td>
                            <td className="p-2.5 text-white font-semibold text-xs sm:text-sm">{item.subModel || item.carName || '-'}</td>
                            <td className="p-2.5 text-xs text-blue-400 font-mono">{item.year ? `${item.year}년` : '-'}</td>
                            <td className="p-2.5 text-right text-xs text-white font-mono">{item.mileage > 0 ? `${Number(item.mileage).toLocaleString()}km` : '-'}</td>
                            <td className="p-2.5 text-right text-zinc-300 font-mono">
                              {buyMan !== null ? `${buyMan.toLocaleString()}만` : '-'}
                            </td>
                            <td className="p-2.5 text-right text-amber-400 font-bold font-mono">
                              {sellMan !== null ? `${sellMan.toLocaleString()}만` : '-'}
                            </td>
                            <td className="p-2.5 text-center font-mono text-xs">{item.stockDays ? `${item.stockDays}일` : '0일'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-4 text-center bg-[#0a0b0e] rounded-xl border border-[#262833] text-xs sm:text-sm space-y-1.5">
                  <div className="text-amber-400 font-bold flex items-center justify-center gap-1.5">
                    <span>⚠️</span>
                    <span>자사 도매 실적 0건 (필터 조건 매칭 매물 없음)</span>
                  </div>
                  <div className="text-zinc-400 text-xs leading-relaxed max-w-lg mx-auto">
                    자사 경매/도매 원장 중 차종 <strong className="text-zinc-200">[{carName}]</strong>, 
                    세부모델 <strong className="text-zinc-200">[{detailModel || '기본형'}]</strong>, 
                    연식 대역 <strong className="text-zinc-200">[{yearModel ? `${Number(yearModel) - 1}~${Number(yearModel) + 1}년` : '전체'}]</strong> 
                    조건의 출고 이력이 없습니다.
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 🚘 [1] 엔카 실시간 소매 시세 요약 4대 지표 바 (리스트 바로 위 배치로 가독성 극대화) */}
          <div className="space-y-3 pt-1">
            <div className="flex items-center justify-between">
              <div className="text-sm sm:text-base font-black text-white flex items-center gap-2">
                <span>🚘</span>
                <span>엔카 실시간 소매 시세 요약</span>
              </div>
              <div className="flex items-center gap-2">
                {encarSourceUrl && (
                  <a
                    href={encarSourceUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs px-2.5 py-1 rounded bg-[#1e293b] hover:bg-blue-600/30 text-sky-400 hover:text-white border border-sky-500/30 font-bold transition flex items-center gap-1"
                    title="엔카 공식 실시간 검색 페이지 새창 열기"
                  >
                    <span>🚗 엔카시세 ↗</span>
                  </a>
                )}
                <a
                  href={kcarUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs px-2.5 py-1 rounded bg-[#1e293b] hover:bg-rose-600/30 text-rose-300 hover:text-white border border-rose-500/30 font-bold transition flex items-center gap-1"
                  title="KCAR 직영점 동일 조건(연식±1년/주행거리±3만km) 매물 검색 새창 열기"
                >
                  <span>🏢 KCAR ↗</span>
                </a>
              </div>
            </div>

            {/* 4 Metrics Bar - 슬림 템플릿 적용 */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="bg-[#121319] border border-[#262835] rounded-xl px-2.5 py-1.5 flex items-center gap-2.5 shadow-sm min-h-[52px]">
                <div className="w-7 h-7 rounded-md bg-blue-500/10 border border-blue-500/25 flex items-center justify-center text-sm shrink-0">🚙</div>
                <div className="min-w-0 flex-1">
                  <div className="text-[10px] text-zinc-400 font-medium">총 매물 수</div>
                  <div className="text-sm sm:text-base font-bold text-white font-mono">{encarStats.count || encarList.length}대</div>
                </div>
              </div>
              <div className="bg-[#121319] border border-[#262835] rounded-xl px-2.5 py-1.5 flex items-center gap-2.5 shadow-sm min-h-[52px]">
                <div className="w-7 h-7 rounded-md bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center text-sm shrink-0">⬇️</div>
                <div className="min-w-0 flex-1">
                  <div className="text-[10px] text-zinc-400 font-medium">최저가</div>
                  <div className="text-sm sm:text-base font-bold text-emerald-400 font-mono">
                    {encarStats.min > 0 ? `${encarStats.min.toLocaleString()}만원` : '-'}
                  </div>
                </div>
              </div>
              <div className="bg-[#121319] border border-[#262835] rounded-xl px-2.5 py-1.5 flex items-center gap-2.5 shadow-sm min-h-[52px]">
                <div className="w-7 h-7 rounded-md bg-rose-500/10 border border-rose-500/25 flex items-center justify-center text-sm shrink-0">⬆️</div>
                <div className="min-w-0 flex-1">
                  <div className="text-[10px] text-zinc-400 font-medium">최고가</div>
                  <div className="text-sm sm:text-base font-bold text-rose-400 font-mono">
                    {encarStats.max > 0 ? `${encarStats.max.toLocaleString()}만원` : '-'}
                  </div>
                </div>
              </div>
              <div className="bg-[#121319] border border-[#262835] rounded-xl px-2.5 py-1.5 flex items-center gap-2.5 shadow-sm min-h-[52px]">
                <div className="w-7 h-7 rounded-md bg-amber-500/10 border border-amber-500/25 flex items-center justify-center text-sm shrink-0">📊</div>
                <div className="min-w-0 flex-1">
                  <div className="text-[10px] text-zinc-400 font-medium">평균가</div>
                  <div className="text-sm sm:text-base font-bold text-amber-300 font-mono">
                    {encarStats.avg > 0 ? `${encarStats.avg.toLocaleString()}만원` : '-'}
                  </div>
                </div>
              </div>
            </div>

            {/* 📋 [2] 실시간 소매 시세 & 빅데이터 밸류에이션 2분할 카드 (핵심 수치 가독성 극대화) */}
            {(() => {
              const marketAvg = encarStats.avg > 0 
                ? encarStats.avg 
                : (encarList.length > 0 ? Math.round(encarList.reduce((a, b) => a + (b.price || 0), 0) / encarList.length) : 0);
              const retailPrice = aiRetailPrice;

              // 매물 또는 유효 소매가가 전혀 없는 경우 목업 렌더링 방지
              if (retailPrice <= 0 || marketAvg <= 0 || (encarStats.count === 0 && encarList.length === 0)) {
                return null;
              }

              const minValPrice = (encarValuation?.minPrice && encarValuation.minPrice < retailPrice * 1.1 && encarValuation.minPrice > retailPrice * 0.8)
                ? encarValuation.minPrice
                : Math.round(retailPrice * 0.94);
              const maxValPrice = (encarValuation?.maxPrice && encarValuation.maxPrice > retailPrice * 0.9 && encarValuation.maxPrice < retailPrice * 1.2)
                ? encarValuation.maxPrice
                : Math.round(retailPrice * 1.06);
              const valScore = (encarValuation?.score && encarValuation.score >= 50 && encarValuation.score <= 150) ? encarValuation.score : 100.0;
              const gapVal = marketAvg - retailPrice;
              const gapPct = retailPrice > 0 ? ((gapVal / retailPrice) * 100).toFixed(1) : '0.0';
              const optCount = optionsTag && optionsTag.trim() && !optionsTag.includes('옵션 없음')
                ? optionsTag.replace(/\[[^\]]*\]/g, '').split(/[·,+,\/]/).filter((s: string) => s.trim().length > 0 && !s.includes('옵션 없음') && !s.includes('기본')).length
                : 0;

              return (
                <div className="bg-[#121319] border border-[#2a2d3d] rounded-xl p-3.5 space-y-2.5 shadow-md">
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[#232634]">
                    <div className="flex items-center gap-2 font-bold text-amber-300 text-sm sm:text-base">
                      <span>📋</span>
                      <span>실시간 소매 시세 &amp; 빅데이터 밸류에이션</span>
                    </div>
                    {retailPrice > 0 && (
                      <div className="px-2.5 py-0.5 rounded-lg bg-[#1a2234] border border-sky-500/50 text-sky-300 font-bold text-xs sm:text-sm flex items-center gap-1.5 shadow-sm">
                        <span>🎯 정밀 소매가:</span>
                        <strong className="text-white text-sm sm:text-base font-mono">{retailPrice.toLocaleString()}</strong>
                        <span className="text-xs text-zinc-300">만원</span>
                        <span className="text-[11px] text-zinc-400 font-normal font-mono">
                          ({minValPrice.toLocaleString()}~{maxValPrice.toLocaleString()}만)
                        </span>
                      </div>
                    )}
                  </div>

                  {/* 2-Column Split Details */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                    {/* Left Card: AI 빅데이터 적정 시세 */}
                    <div className="bg-[#151824] p-3 rounded-xl border border-sky-500/30 space-y-2 shadow-sm">
                      <div className="flex justify-between items-center">
                        <span className="text-xs sm:text-sm font-bold text-sky-400 flex items-center gap-1.5">
                          <span>📊</span>
                          <span>AI 빅데이터 적정 시세</span>
                        </span>
                        <span className="text-[11px] px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/40 font-bold font-mono">
                          가치지수 {valScore}점
                        </span>
                      </div>
                      <div className="space-y-1.5">
                        {/* 굵고 선명한 적정 밴드 메인 수치 */}
                        <div className="flex items-baseline gap-2 flex-wrap">
                          <span className="text-xs text-zinc-400 font-semibold shrink-0">적정 밴드:</span>
                          <span className="text-base sm:text-lg font-black font-mono text-sky-300 tracking-tight">
                            {minValPrice.toLocaleString()} ~ {maxValPrice.toLocaleString()}만원
                          </span>
                          <span className="text-xs text-zinc-400 font-mono">(기준 {retailPrice.toLocaleString()}만)</span>
                        </div>
                        <div className="flex flex-wrap items-center gap-1.5 text-xs pt-0.5">
                          <span className="text-zinc-400 shrink-0 text-[11px]">반영 스펙:</span>
                          <span className="px-2 py-0.5 rounded bg-[#1f2436] text-zinc-200 font-mono text-[11px]">
                            주행 {mileageKm.toLocaleString()}km
                          </span>
                          <span className="px-2 py-0.5 rounded bg-[#1f2436] text-zinc-200 text-[11px]">
                            {outerRepairCount > 0
                              ? `외판 ${outerRepairCount}판 감가`
                              : (targetCarHistory && targetCarHistory.myCarAccidentCount > 0
                                  ? `보험 ${targetCarHistory.myCarAccidentCount}건(${targetCarHistory.myCarAccidentCost}만)`
                                  : '완전무사고')}
                          </span>
                          {optCount > 0 && (
                            <span className="px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30 font-bold text-[11px]">
                              추가옵션 {optCount}개
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Right Card: 시장 판매 호가 현황 */}
                    <div className="bg-[#151824] p-3 rounded-xl border border-amber-500/30 space-y-2 shadow-sm">
                      <div className="flex justify-between items-center">
                        <span className="text-xs sm:text-sm font-bold text-amber-400 flex items-center gap-1.5">
                          <span>🏷️</span>
                          <span>시장 판매 호가 현황 ({encarStats.count || encarList.length}대)</span>
                        </span>
                        <span className="text-[11px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold font-mono">
                          호가 괴리: {gapVal >= 0 ? `+${gapVal.toLocaleString()}` : `${gapVal.toLocaleString()}`}만 ({gapVal >= 0 ? `+${gapPct}` : `${gapPct}`}%)
                        </span>
                      </div>
                      <div className="space-y-1.5">
                        {/* 굵고 선명한 시장 호가 메인 수치 */}
                        <div className="flex items-baseline gap-2 flex-wrap">
                          <span className="text-xs text-zinc-400 font-semibold shrink-0">시장 평균:</span>
                          <span className="text-base sm:text-lg font-black font-mono text-amber-300 tracking-tight">
                            {marketAvg > 0 ? `${marketAvg.toLocaleString()}만원` : '-'}
                          </span>
                          <span className="text-xs text-zinc-400 font-mono">
                            (최저 {encarStats.min > 0 ? encarStats.min.toLocaleString() : '-'}만 ~ 최고 {encarStats.max > 0 ? encarStats.max.toLocaleString() : '-'}만)
                          </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-1 text-xs pt-0.5">
                          <span className="text-zinc-400 shrink-0 text-[11px]">연식 분포:</span>
                          {encarYearStats.length > 0 ? (
                            encarYearStats.map((st) => (
                              <span 
                                key={st.year}
                                className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                                  st.isTarget 
                                    ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 font-bold' 
                                    : 'bg-[#1f2436] text-zinc-300'
                                }`}
                              >
                                {st.year}년 {st.avg.toLocaleString()}만 <span className="opacity-80">({st.count}대)</span>
                              </span>
                            ))
                          ) : (
                            <span className="text-zinc-400 text-[11px]">집계 중</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
  );
};
