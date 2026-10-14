import React, { useState, useMemo } from 'react';
import { X, ShieldAlert, ShieldCheck, Car, Calendar, AlertTriangle, FileText, CheckCircle2, Gauge, ExternalLink, Scale, Check, Shield, ChevronDown, ChevronUp } from 'lucide-react';
import type { ChaolmaCarHistory, ChaolmaOriginDoc } from '@/services/chaolmaService';
import { computeRuleBasedAssessment } from '@/utils/ruleBasedAssessment';
import { CarDamageDiagram2D } from './BiddingCockpit/Sections/CarDamageDiagram2D';
import { AutoplusDamageDiagram } from './AutoplusDamageDiagram';

export interface CarHistoryDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  carNumber: string;
  carName?: string;
  currentMileage?: number;
  data: {
    ownerChangedCount: number;
    isSingleOwner: boolean;
    myCarAccidentCount: number;
    myCarAccidentCost: number; // 만원
    otherCarAccidentCount: number;
    otherCarAccidentCost: number; // 만원
    totalLossCount: number;
    floodedCount: number;
    stolenCount: number;
    hasRentHistory: boolean;
    standardNewCarPrice: number; // 만원
    baseCarPrice?: number; // 만원
    totalOptionPrice?: number; // 만원
    vin?: string;
    manufacturedDate?: string;
    inspectionValidUntil?: string;
    rawHistory?: ChaolmaCarHistory;
    originDoc?: ChaolmaOriginDoc;
  } | null;
}

// 카히스토리 수리부위 상세 문자열(r502-16) 파서 -> CarDamageDiagram2D 연동 포맷 변환
function parseRepairDetailsToDiagram(repairDetailsStr?: string) {
  if (!repairDetailsStr || typeof repairDetailsStr !== 'string' || !repairDetailsStr.trim()) {
    return { selectedEncar: null, items: [] };
  }
  const parts = repairDetailsStr.split(',').map(s => s.trim()).filter(Boolean);
  const replaces: string[] = [];
  const repairs: string[] = [];
  const damageData: Record<string, string> = {};
  const items: { name: string; action: '교환' | '판금' | '도장' | '탈착' | '기타'; raw: string }[] = [];

  for (const p of parts) {
    if (!p) continue;
    let action: '교환' | '판금' | '도장' | '탈착' | '기타' = '기타';
    if (p.includes('교환')) action = '교환';
    else if (p.includes('판금') || p.includes('용접')) action = '판금';
    else if (p.includes('도장')) action = '도장';
    else if (p.includes('탈착')) action = '탈착';

    const cleanName = p.replace(/\((교환|판금|용접|도장|탈착)\)/g, '').trim() || p;

    if (action === '교환') {
      replaces.push(cleanName);
      damageData[cleanName] = '교환';
    } else if (action === '판금') {
      repairs.push(cleanName);
      damageData[cleanName] = '판금';
    }

    items.push({ name: cleanName, action, raw: p });
  }

  return {
    selectedEncar: {
      replaces: replaces || [],
      repairs: repairs || [],
      damageData: damageData || {},
      replaceNames: replaces || [],
      repairNames: repairs || [],
    },
    items: items || []
  };
}

export const CarHistoryDetailModal: React.FC<CarHistoryDetailModalProps> = ({
  isOpen,
  onClose,
  carNumber,
  carName,
  currentMileage,
  data
}) => {
  // 자동차 전개도 탭 상태 (기본값: 접힘)
  const [isDiagramTabOpen, setIsDiagramTabOpen] = useState<boolean>(false);

  const raw = data?.rawHistory;
  const doc = data?.originDoc;
  const accidents = useMemo(() => raw?.accident_histories || [], [raw]);
  const mileages = useMemo(() => raw?.mileage_records || [], [raw]);

  // 탈착/도장 코드 또는 수리부위 상세(repair_details) 존재 여부 판정
  const hasDiagramData = useMemo(() => {
    if (!raw) return false;
    if ((raw.total_dismantle_count || 0) > 0 || (raw.total_paint_count || 0) > 0) return true;
    return accidents.some(a => 
      Boolean((a.dismantle_codes && a.dismantle_codes.trim()) || 
              (a.paint_codes && a.paint_codes.trim()) || 
              (a.repair_details && a.repair_details.trim()))
    );
  }, [raw, accidents]);

  const assessment = useMemo(() => {
    if (!data) return null;
    return computeRuleBasedAssessment({
      carNumber,
      currentMileage: currentMileage || (mileages[0]?.mileage) || doc?.inspection_mileage || 50000,
      ownerChangedCount: data.ownerChangedCount,
      isSingleOwner: data.isSingleOwner,
      hasRentHistory: data.hasRentHistory,
      myCarAccidentCount: data.myCarAccidentCount,
      myCarAccidentCostMan: data.myCarAccidentCost,
      otherCarAccidentCount: data.otherCarAccidentCount,
      totalLossCount: data.totalLossCount,
      floodedCount: data.floodedCount,
      stolenCount: data.stolenCount,
      seizureCount: doc?.seizure_count,
      mortgageCount: doc?.mortgage_count,
      tuningCount: doc?.tuning_count,
      inspectionValidEnd: doc?.inspection_valid_end || data.inspectionValidUntil,
      inspectionMileage: doc?.inspection_mileage,
      lastHistoryMileage: mileages[0]?.mileage,
      outerRepairCount: 0
    });
  }, [data, carNumber, currentMileage, mileages, doc]);

  // 🌟 모든 Hook 호출이 완료된 후 Early Return 실행 (React Rules of Hooks 준수)
  if (!isOpen || !data || !assessment) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="bg-[#0e1017] border border-[#2a2d3d] w-full max-w-4xl max-h-[92vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden text-zinc-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 모달 상단 헤더 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#222533] bg-[#141622]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">
                  보험사고 &amp; 카히스토리 정밀 리포트
                </h2>
                <span className="text-xs px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-300 font-mono font-bold border border-sky-500/30">
                  {carNumber || '차량번호 미확인'}
                </span>
                {data.isSingleOwner && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30">
                    🟢 1인 신조
                  </span>
                )}
              </div>
              <div className="text-xs text-zinc-400 mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1">
                {carName && <span className="text-zinc-300 font-medium">{carName}</span>}
                {data.vin && <span>차대번호: <code className="text-sky-300 font-mono">{data.vin}</code></span>}
                {data.manufacturedDate && <span>최초등록: <span className="text-zinc-300 font-mono">{data.manufacturedDate}</span></span>}
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition cursor-pointer"
            title="닫기"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 모달 본문 스크롤 영역 */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6 scrollbar-thin scrollbar-thumb-zinc-700">
          
          {/* 🌟 5단계 전체 규칙 기반 종합 상태 판정 배너 */}
          <div className="bg-gradient-to-r from-[#141a29] to-[#12141f] border border-sky-500/30 rounded-xl p-4 shadow-lg space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-2.5">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-white flex items-center gap-1.5">
                  <ShieldCheck className="w-5 h-5 text-sky-400" />
                  5단계 전체 규칙 기반 종합 상태 판정
                </span>
                <span 
                  className="px-2.5 py-0.5 rounded-full text-xs font-black border"
                  style={{ backgroundColor: `${assessment.gradeBadgeColor}20`, color: assessment.gradeBadgeColor, borderColor: `${assessment.gradeBadgeColor}50` }}
                >
                  종합 {assessment.gradeName}
                </span>
              </div>
              <div className="text-xs text-zinc-300 font-medium">
                {assessment.isEligibleForBidding ? (
                  <span className="text-emerald-400 font-bold">🟢 입찰 적격 차량</span>
                ) : (
                  <span className="text-rose-400 font-bold">🚨 입찰 주의/결격 대상</span>
                )}
                {assessment.totalAdjustmentMan !== 0 && (
                  <span className="ml-2 font-mono font-bold text-amber-300">
                    규칙 감가/가산 합계: {assessment.totalAdjustmentMan > 0 ? `+${assessment.totalAdjustmentMan}만` : `${assessment.totalAdjustmentMan}만`}
                  </span>
                )}
              </div>
            </div>

            {/* 5대 검증 체크 바이트 */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
              <div className={`p-2 rounded-lg border ${assessment.legalRights.isPass ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-rose-500/10 border-rose-500/30'}`}>
                <div className="text-[10px] text-zinc-400">1. 권리 상태</div>
                <div className="font-bold text-[11px] truncate mt-0.5" title={assessment.legalRights.label}>{assessment.legalRights.label}</div>
              </div>
              <div className={`p-2 rounded-lg border ${assessment.accidentDamage.isPass ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-rose-500/10 border-rose-500/30'}`}>
                <div className="text-[10px] text-zinc-400">2. 사고/손상</div>
                <div className="font-bold text-[11px] truncate mt-0.5" title={assessment.accidentDamage.label}>{assessment.accidentDamage.label}</div>
              </div>
              <div className={`p-2 rounded-lg border ${assessment.ownershipUsage.isPass ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-amber-500/10 border-amber-500/30'}`}>
                <div className="text-[10px] text-zinc-400">3. 소유/용도</div>
                <div className="font-bold text-[11px] truncate mt-0.5" title={assessment.ownershipUsage.label}>{assessment.ownershipUsage.label}</div>
              </div>
              <div className={`p-2 rounded-lg border ${assessment.mileageIntegrity.isPass ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-rose-500/10 border-rose-500/30'}`}>
                <div className="text-[10px] text-zinc-400">4. 주행거리 무결성</div>
                <div className="font-bold text-[11px] truncate mt-0.5" title={assessment.mileageIntegrity.label}>{assessment.mileageIntegrity.label}</div>
              </div>
              <div className={`p-2 rounded-lg border ${assessment.inspectionValidity.isPass ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-rose-500/10 border-rose-500/30'}`}>
                <div className="text-[10px] text-zinc-400">5. 정기검사</div>
                <div className="font-bold text-[11px] truncate mt-0.5" title={assessment.inspectionValidity.label}>{assessment.inspectionValidity.label}</div>
              </div>
            </div>
          </div>

          {/* 1. 핵심 지표 4분할 그리드 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            
            {/* 카드 1: 출고가 & 옵션 */}
            <div className="bg-[#13151f] border border-[#262838] rounded-xl p-3.5 space-y-1.5 shadow-sm">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span className="font-semibold flex items-center gap-1 text-sky-400">
                  <Car className="w-3.5 h-3.5" /> 신차 출고가
                </span>
                <span className="text-[11px] text-zinc-500 font-mono">순정기준</span>
              </div>
              <div className="text-lg font-bold text-white font-mono">
                {data.standardNewCarPrice > 0 ? `${data.standardNewCarPrice.toLocaleString()}만 원` : '-'}
              </div>
              <div className="text-[11px] text-zinc-400 space-y-0.5 font-mono pt-1 border-t border-white/5">
                <div className="flex justify-between">
                  <span>기본차량가:</span>
                  <span className="text-zinc-200">{data.baseCarPrice ? `${data.baseCarPrice.toLocaleString()}만` : '-'}</span>
                </div>
                <div className="flex justify-between">
                  <span>순정옵션가:</span>
                  <span className="text-amber-300 font-semibold">{data.totalOptionPrice ? `+${data.totalOptionPrice.toLocaleString()}만` : '0만'}</span>
                </div>
              </div>
            </div>

            {/* 카드 2: 소유자 및 용도 */}
            <div className="bg-[#13151f] border border-[#262838] rounded-xl p-3.5 space-y-1.5 shadow-sm">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span className="font-semibold flex items-center gap-1 text-emerald-400">
                  <CheckCircle2 className="w-3.5 h-3.5" /> 소유 &amp; 용도
                </span>
                <span className="text-[11px] text-zinc-500">명의변경</span>
              </div>
              <div className="text-lg font-bold font-mono">
                {data.isSingleOwner ? (
                  <span className="text-emerald-400">1인 신조 (0회)</span>
                ) : (
                  <span className="text-amber-400">변경 {data.ownerChangedCount}회</span>
                )}
              </div>
              <div className="text-[11px] text-zinc-400 space-y-0.5 pt-1 border-t border-white/5">
                <div className="flex justify-between">
                  <span>용도(렌트):</span>
                  <span className={data.hasRentHistory ? "text-rose-400 font-semibold" : "text-emerald-400 font-medium"}>
                    {data.hasRentHistory ? '⚠️ 렌트이력 있음' : '없음 (자가용)'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>번호판 변경:</span>
                  <span className="text-zinc-200 font-mono">{raw?.plate_change_count ?? 0}회</span>
                </div>
              </div>
            </div>

            {/* 카드 3: 사고 피해 */}
            <div className="bg-[#13151f] border border-[#262838] rounded-xl p-3.5 space-y-1.5 shadow-sm">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span className="font-semibold flex items-center gap-1 text-rose-400">
                  <ShieldAlert className="w-3.5 h-3.5" /> 사고 피해 내역
                </span>
                <span className="text-[11px] text-zinc-500">보험처리</span>
              </div>
              <div className="text-lg font-bold font-mono">
                {data.myCarAccidentCount > 0 ? (
                  <span className="text-rose-400">내차 {data.myCarAccidentCount}건 ({data.myCarAccidentCost}만)</span>
                ) : (
                  <span className="text-emerald-400">내차 0건 (무사고)</span>
                )}
              </div>
              <div className="text-[11px] text-zinc-400 space-y-0.5 font-mono pt-1 border-t border-white/5">
                <div className="flex justify-between">
                  <span>타차가해:</span>
                  <span className="text-zinc-200">{data.otherCarAccidentCount}건 ({data.otherCarAccidentCost}만)</span>
                </div>
                <div className="flex justify-between">
                  <span>원보험금총액:</span>
                  <span className="text-zinc-300">{raw?.my_car_accident_cost ? `${raw.my_car_accident_cost.toLocaleString()}원` : '0원'}</span>
                </div>
              </div>
            </div>

            {/* 카드 4: 특수사고 & 결격 */}
            <div className="bg-[#13151f] border border-[#262838] rounded-xl p-3.5 space-y-1.5 shadow-sm">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span className="font-semibold flex items-center gap-1 text-amber-400">
                  <AlertTriangle className="w-3.5 h-3.5" /> 특수사고 &amp; 결격
                </span>
                <span className="text-[11px] text-zinc-500">중대결격</span>
              </div>
              <div className="text-lg font-bold font-mono">
                {data.floodedCount > 0 || data.totalLossCount > 0 || data.stolenCount > 0 ? (
                  <span className="text-rose-400">⚠️ 특수사고 발견</span>
                ) : (
                  <span className="text-emerald-400">🟢 이상 없음</span>
                )}
              </div>
              <div className="text-[11px] text-zinc-400 space-y-0.5 pt-1 border-t border-white/5">
                <div className="flex justify-between">
                  <span>침수 / 전손 / 도난:</span>
                  <span className="text-zinc-200 font-mono">{data.floodedCount} / {data.totalLossCount} / {data.stolenCount}</span>
                </div>
                <div className="flex justify-between">
                  <span>미가입기간:</span>
                  <span className={raw?.uninsured_period ? "text-amber-300 font-semibold" : "text-zinc-400"}>
                    {raw?.uninsured_period || '전 기간 가입'}
                  </span>
                </div>
              </div>
            </div>

          </div>

          {/* 🏛️ 1.5. 국토교통부 공식 자동차등록원부 (압류·저당·구조변경·검사유효기간) */}
          <div className="bg-[#13151f] border border-[#262838] rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-white/5 pb-2.5">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-white flex items-center gap-1.5">
                  <Scale className="w-4 h-4 text-emerald-400" />
                  국토교통부 자동차등록원부 (갑부/을부 법적 권리 및 검사 원본)
                </span>
                <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 font-medium border border-emerald-500/25">
                  VMIS 전산 직결
                </span>
              </div>
              {doc?.last_regist_date && (
                <span className="text-xs text-zinc-400">
                  최종 명의이전일: <b className="text-zinc-200 font-mono">{doc.last_regist_date}</b>
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 text-xs">
              {/* 압류 */}
              <div className="bg-[#191c28] p-2.5 rounded-lg border border-[#2a2d3d] space-y-1">
                <div className="text-[11px] text-zinc-400">압류 건수</div>
                <div className="text-sm font-bold font-mono">
                  {doc ? (
                    doc.seizure_count > 0 ? (
                      <span className="text-rose-400">🚨 {doc.seizure_count}건</span>
                    ) : (
                      <span className="text-emerald-400">🟢 0건 (없음)</span>
                    )
                  ) : '-'}
                </div>
              </div>

              {/* 저당 */}
              <div className="bg-[#191c28] p-2.5 rounded-lg border border-[#2a2d3d] space-y-1">
                <div className="text-[11px] text-zinc-400">저당 건수</div>
                <div className="text-sm font-bold font-mono">
                  {doc ? (
                    doc.mortgage_count > 0 ? (
                      <span className="text-rose-400">🚨 {doc.mortgage_count}건</span>
                    ) : (
                      <span className="text-emerald-400">🟢 0건 (해지)</span>
                    )
                  ) : '-'}
                </div>
              </div>

              {/* 구조변경 */}
              <div className="bg-[#191c28] p-2.5 rounded-lg border border-[#2a2d3d] space-y-1">
                <div className="text-[11px] text-zinc-400">구조변경(튜닝)</div>
                <div className="text-sm font-bold font-mono">
                  {doc ? (
                    doc.tuning_count > 0 ? (
                      <span className="text-amber-400">🟡 {doc.tuning_count}건 이력</span>
                    ) : (
                      <span className="text-zinc-300">0건 (순정)</span>
                    )
                  ) : '-'}
                </div>
              </div>

              {/* 정기검사 만료일 */}
              <div className="bg-[#191c28] p-2.5 rounded-lg border border-[#2a2d3d] space-y-1 col-span-2 sm:col-span-1">
                <div className="text-[11px] text-zinc-400">정기검사 만료일</div>
                <div className="text-sm font-bold text-sky-300 font-mono">
                  {doc?.inspection_valid_end || data.inspectionValidUntil || '-'}
                </div>
              </div>

              {/* 검사소 실측 주행 */}
              <div className="bg-[#191c28] p-2.5 rounded-lg border border-[#2a2d3d] space-y-1">
                <div className="text-[11px] text-zinc-400">검사소 기록 주행</div>
                <div className="text-sm font-bold text-white font-mono">
                  {doc?.inspection_mileage ? `${doc.inspection_mileage.toLocaleString()} km` : '-'}
                </div>
              </div>

              {/* 형식 및 제원 */}
              <div className="bg-[#191c28] p-2.5 rounded-lg border border-[#2a2d3d] space-y-1">
                <div className="text-[11px] text-zinc-400">승차정원 / 엔진</div>
                <div className="text-sm font-bold text-zinc-200 font-mono">
                  {doc?.seating_capacity ? `${doc.seating_capacity}인승` : '-'} {doc?.engine_type ? `(${doc.engine_type})` : ''}
                </div>
              </div>
            </div>
          </div>

          {/* 2. 내차피해 상세 이력 테이블 (일자별 수리비 분해) */}
          <div className="bg-[#13151f] border border-[#262838] rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-white flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                  사고이력 상세 수리비 분해 내역 (총 {accidents.length}건)
                </span>
                {accidents.length > 0 && (
                  <span className="text-[11px] text-zinc-400 font-mono">
                    (내차보험 총액: {raw?.my_car_accident_cost?.toLocaleString()}원)
                  </span>
                )}
              </div>
              {raw?.market_price_range && (
                <span className="text-xs text-sky-400 font-medium">
                  카히스토리 시세 범위: <b className="text-white font-mono">{raw.market_price_range}만 원</b>
                </span>
              )}
            </div>

            {accidents.length > 0 ? (
              <div className="overflow-x-auto border border-[#262838] rounded-lg">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[#191c28] text-zinc-300 border-b border-[#262838] font-semibold">
                    <tr>
                      <th className="p-2.5">구분</th>
                      <th className="p-2.5">사고일자</th>
                      <th className="p-2.5 text-right">총 수리비</th>
                      <th className="p-2.5 text-right">부품비</th>
                      <th className="p-2.5 text-right">공임비</th>
                      <th className="p-2.5 text-right">도장료</th>
                      <th className="p-2.5 text-right text-rose-300">보험금지급액</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#262838]/60 font-mono">
                    {accidents.map((acc, idx) => {
                      const isOther = acc.acc_type === 'other';
                      return (
                        <tr 
                          key={idx} 
                          className={`hover:bg-[#1a1d2b] transition ${isOther ? 'bg-amber-950/15' : ''}`}
                        >
                          <td className="p-2.5">
                            {isOther ? (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                타차가해
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                                내차피해
                              </span>
                            )}
                          </td>
                          <td className="p-2.5 text-zinc-300 font-bold">
                            {acc.date && typeof acc.date === 'string' && acc.date.length >= 8 
                              ? `${acc.date.slice(0, 4)}-${acc.date.slice(4, 6)}-${acc.date.slice(6)}` 
                              : (acc.date || '-')}
                          </td>
                          <td className="p-2.5 text-right font-bold text-white">
                            {typeof acc.repair_cost === 'number' ? `${acc.repair_cost.toLocaleString()}원` : '-'}
                          </td>
                          <td className="p-2.5 text-right text-zinc-300">
                            {typeof acc.parts_cost === 'number' ? `${acc.parts_cost.toLocaleString()}원` : '-'}
                          </td>
                          <td className="p-2.5 text-right text-zinc-300">
                            {typeof acc.labor_cost === 'number' ? `${acc.labor_cost.toLocaleString()}원` : '-'}
                          </td>
                          <td className="p-2.5 text-right text-zinc-300">
                            {typeof acc.paint_cost === 'number' ? `${acc.paint_cost.toLocaleString()}원` : '-'}
                          </td>
                          <td className={`p-2.5 text-right font-bold ${isOther ? 'text-amber-400 bg-amber-500/5' : 'text-rose-400 bg-rose-500/5'}`}>
                            {typeof acc.insurance_paid === 'number' ? `${acc.insurance_paid.toLocaleString()}원` : '-'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-4 text-center bg-[#0d0e14] rounded-lg border border-[#262838] text-xs text-emerald-400 font-medium flex items-center justify-center gap-2">
                <ShieldCheck className="w-4 h-4" />
                등록된 사고 피해 이력이 없습니다 (보험처리 기준 완전 무사고).
              </div>
            )}
          </div>

          {/* 2.5 자동차 전개도 및 일자별 수리부위 상세 탭 */}
          <div className="bg-[#13151f] border border-[#262838] rounded-xl overflow-hidden">
            {/* 탭 헤더 버튼 (클릭 시 토글) */}
            <button
              type="button"
              onClick={() => hasDiagramData && setIsDiagramTabOpen(!isDiagramTabOpen)}
              className={`w-full flex items-center justify-between p-3.5 bg-[#161824] transition ${
                hasDiagramData ? 'hover:bg-[#1c1f2e] cursor-pointer' : 'cursor-not-allowed opacity-75'
              }`}
            >
              <div className="flex items-center gap-2">
                <Car className={`w-4 h-4 ${hasDiagramData ? 'text-indigo-400' : 'text-zinc-500'}`} />
                <span className="text-sm font-bold text-white">자동차 전개도 &amp; 일자별 수리부위 상세</span>
                {hasDiagramData ? (
                  <div className="flex items-center gap-1.5">
                    {(raw?.total_dismantle_count || 0) > 0 && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-sky-500/20 text-sky-300 border border-sky-500/30 font-mono">
                        탈착 {raw?.total_dismantle_count}건
                      </span>
                    )}
                    {(raw?.total_paint_count || 0) > 0 && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30 font-mono">
                        도장 {raw?.total_paint_count}건
                      </span>
                    )}
                    {(!raw?.total_dismantle_count && !raw?.total_paint_count) && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono">
                        데이터 보유
                      </span>
                    )}
                  </div>
                ) : (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
                    정보 없음
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {hasDiagramData ? (
                  <span className="text-xs text-zinc-400 flex items-center gap-1">
                    {isDiagramTabOpen ? '접기' : '펼쳐보기'}
                    {isDiagramTabOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </span>
                ) : (
                  <span className="text-xs text-zinc-500">수리부위 전산 미기록</span>
                )}
              </div>
            </button>

            {/* 펼쳐졌을 때의 전개도 및 상세 내용 (오토플러스 원본 1:1) */}
            {hasDiagramData && isDiagramTabOpen && (
              <div className="p-4 border-t border-[#262838] bg-[#0c0d14]">
                <AutoplusDamageDiagram history={raw} />
              </div>
            )}
          </div>

          {/* 3. 실측 주행거리 이력 테이블 (보험사 / 검사소 기록) */}
          <div className="bg-[#13151f] border border-[#262838] rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-white flex items-center gap-1.5">
                <Gauge className="w-4 h-4 text-sky-400" />
                공식 실측 주행거리 이력 (총 {mileages.length}회 기록)
              </span>
              <span className="text-xs text-zinc-400">
                보험사 정기 갱신 및 검사소 등록 실측치
              </span>
            </div>

            {mileages.length > 0 ? (
              <div className="overflow-x-auto border border-[#262838] rounded-lg">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[#191c28] text-zinc-300 border-b border-[#262838] font-semibold">
                    <tr>
                      <th className="p-2.5">확인일자</th>
                      <th className="p-2.5">정보 출처</th>
                      <th className="p-2.5 text-right">기록 주행거리</th>
                      <th className="p-2.5 text-right">상태</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#262838]/60 font-mono">
                    {mileages.map((m, idx) => (
                      <tr key={idx} className="hover:bg-[#1a1d2b] transition">
                        <td className="p-2.5 text-zinc-300 font-bold">
                          {m.date ? `${m.date.slice(0, 4)}-${m.date.slice(4, 6)}-${m.date.slice(6)}` : '-'}
                        </td>
                        <td className="p-2.5 text-zinc-300 font-sans">
                          {m.source || '자동차보험회사'}
                        </td>
                        <td className="p-2.5 text-right font-bold text-sky-300">
                          {m.mileage ? `${m.mileage.toLocaleString()} km` : '-'}
                        </td>
                        <td className="p-2.5 text-right text-emerald-400 font-sans font-medium">
                          {idx === 0 ? '🟢 최신' : '정상 누적'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-4 text-center bg-[#0d0e14] rounded-lg border border-[#262838] text-xs text-zinc-400">
                등록된 공식 주행거리 기록이 없습니다.
              </div>
            )}
          </div>

        </div>

        {/* 모달 하단 푸터 */}
        <div className="flex items-center justify-between px-5 py-3.5 border-t border-[#222533] bg-[#141622]">
          <div className="text-xs text-zinc-400 flex items-center gap-1.5">
            <span>※ 본 데이터는 보험개발원(CarHistory) 및 차얼마 전산 원본 기반입니다.</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-[#282c3c] hover:bg-[#353a4e] text-white text-xs font-bold transition cursor-pointer"
          >
            닫기
          </button>
        </div>

      </div>
    </div>
  );
};
