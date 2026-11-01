import React from 'react';

export interface VehicleAssessmentV2BarProps {
  currentAssessment?: any;
  targetCarHistory?: any;
  outerRepairCount?: number;
  onOpenHistoryModal?: () => void;
}

export const VehicleAssessmentV2Bar: React.FC<VehicleAssessmentV2BarProps> = ({
  currentAssessment,
  targetCarHistory,
  outerRepairCount = 0,
  onOpenHistoryModal,
}) => {
  if (!currentAssessment) return null;

  return (
    <div
      onClick={onOpenHistoryModal}
      className="bg-[#121622] hover:bg-[#161c2d] border border-sky-500/35 hover:border-sky-400/60 rounded-xl p-3 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-md transition cursor-pointer group"
      title="클릭 시 국토부 등록원부 및 카히스토리 상세 모달 열기"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          className="px-2.5 py-0.5 rounded-full text-xs font-black border flex items-center gap-1 shrink-0"
          style={{
            backgroundColor: `${currentAssessment.gradeBadgeColor}20`,
            color: currentAssessment.gradeBadgeColor,
            borderColor: `${currentAssessment.gradeBadgeColor}50`,
          }}
        >
          <span>🛡️</span>
          <span>{currentAssessment.gradeName}</span>
        </span>

        {/* 핵심 검증 태그 칩들: '5단계' 및 '주행' 제외, 실무 우선순위 반영 */}
        <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
          {/* 1. 사고 및 내차피해 */}
          <span
            className={`px-2 py-0.5 rounded border ${
              currentAssessment.accidentDamage?.isPass
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                : 'bg-rose-500/20 text-rose-300 border-rose-500/40 font-bold'
            }`}
          >
            사고: {currentAssessment.accidentDamage?.status === 'PERFECT' ? '무사고' : currentAssessment.accidentDamage?.status === 'MINOR' ? '단순수리' : '골격/결격'}
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
          <span
            className={`px-2 py-0.5 rounded border ${
              !targetCarHistory || (targetCarHistory.floodedCount === 0 && targetCarHistory.totalLossCount === 0)
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                : 'bg-rose-500/20 text-rose-300 border-rose-500/40 font-bold animate-pulse'
            }`}
          >
            침수·전손: {targetCarHistory && (targetCarHistory.floodedCount > 0 || targetCarHistory.totalLossCount > 0)
              ? `🚨${targetCarHistory.floodedCount + targetCarHistory.totalLossCount}건`
              : '0건'}
          </span>

          {/* 3. 용도 및 소유자 변경 */}
          <span
            className={`px-2 py-0.5 rounded border ${
              currentAssessment.ownershipUsage?.isPass
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
            }`}
          >
            용도: {currentAssessment.ownershipUsage?.status === 'SINGLE' ? '1인신조' : currentAssessment.ownershipUsage?.status === 'RENT' ? '렌트이력' : '자가용'}
            {targetCarHistory && targetCarHistory.ownerChangedCount > 0 && !targetCarHistory.isSingleOwner ? (
              <span className="ml-1 text-[10px] opacity-90 font-mono">({targetCarHistory.ownerChangedCount}회 변경)</span>
            ) : null}
          </span>

          {/* 4. 원부 (압류/저당) */}
          <span
            className={`px-2 py-0.5 rounded border ${
              currentAssessment.legalRights?.isPass
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                : 'bg-rose-500/20 text-rose-300 border-rose-500/40 font-bold'
            }`}
          >
            원부: {currentAssessment.legalRights?.isPass
              ? '클린'
              : (targetCarHistory?.originDoc && (targetCarHistory.originDoc.seizure_count > 0 || targetCarHistory.originDoc.mortgage_count > 0)
                  ? `압류${targetCarHistory.originDoc.seizure_count} 저당${targetCarHistory.originDoc.mortgage_count}`
                  : '하자')}
          </span>

          {/* 5. 정기검사 */}
          <span
            className={`px-2 py-0.5 rounded border ${
              currentAssessment.inspectionValidity?.isPass
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                : 'bg-rose-500/20 text-rose-300 border-rose-500/40 font-bold'
            }`}
          >
            검사: {currentAssessment.inspectionValidity?.status === 'EXPIRED' ? '🚨만료' : currentAssessment.inspectionValidity?.status === 'EXPIRING_SOON' ? '⚠️임박' : '유효'}
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
  );
};
