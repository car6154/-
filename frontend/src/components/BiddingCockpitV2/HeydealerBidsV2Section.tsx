import React from 'react';
import { HeydealerBidItem, HeydealerSummaryData } from '@/components/BiddingCockpit/Sections/HeydealerBidsSection';

export interface HeydealerBidsV2SectionProps {
  heydealerSummary: HeydealerSummaryData;
  availableHeydealerGrades: string[];
  bestMatchHeydealerGrade: string | null;
  heydealerGradeCounts: Record<string, number>;
  selectedHeydealerGradeFilter: string;
  setSelectedHeydealerGradeFilter: (val: string) => void;
  heydealerBids: HeydealerBidItem[];
  filteredHeydealerBids: HeydealerBidItem[];
  selectedHeydealerBidId: string | null;
  setSelectedHeydealerBidId: (id: string) => void;
  mileageKm: number;
}

export const HeydealerBidsV2Section: React.FC<HeydealerBidsV2SectionProps> = ({
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
  mileageKm,
}) => {
  // 1. 헤이딜러 데이터가 없는 경우 (빈 상태 안내 박스)
  if (!heydealerSummary || !heydealerSummary.hasData) {
    return (
      <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-6 text-center space-y-2">
        <div className="text-sm font-bold text-zinc-300">
          📋 헤이딜러 동급 낙찰 데이터 (도매 실거래)
        </div>
        <p className="text-xs text-zinc-500 max-w-md mx-auto leading-relaxed">
          등록된 헤이딜러 낙찰 데이터가 없거나 조회가 실행되지 않았습니다.
          상단 조회 영역에서 차량을 검색하거나 헤이딜러 URL을 통해 분석 시 최근 1달간의 동급 낙찰 이력이 표시됩니다.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 1. 상단 요약 카드 (총 매물 수 · 최저 · 최고 · 평균) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-3">
          <span className="text-[10px] text-zinc-400 block font-medium">총 매물 수</span>
          <div className="flex items-baseline gap-1 mt-1">
            <span className="text-lg font-black text-white font-mono">{heydealerSummary.totalCount}대</span>
            <span className="text-[10px] text-zinc-500 truncate">
              {heydealerSummary.exportCount > 0 ? `(내수 ${heydealerSummary.domCount} / 수출 ${heydealerSummary.exportCount})` : '(전체 내수)'}
            </span>
          </div>
        </div>

        <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-3">
          <span className="text-[10px] text-zinc-400 block font-medium">최저가 (내수)</span>
          <div className="text-lg font-black text-sky-400 font-mono mt-1 flex items-center gap-0.5">
            {heydealerSummary.minPrice.toLocaleString()}만 <span>⬇</span>
          </div>
        </div>

        <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-3">
          <span className="text-[10px] text-zinc-400 block font-medium">최고가 (내수)</span>
          <div className="text-lg font-black text-sky-400 font-mono mt-1 flex items-center gap-0.5">
            {heydealerSummary.maxPrice.toLocaleString()}만 <span>⬆</span>
          </div>
        </div>

        <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-3">
          <span className="text-[10px] text-zinc-400 block font-medium">내수 평균가</span>
          <div className="text-lg font-black text-white font-mono mt-1">
            {heydealerSummary.avgPrice.toLocaleString()}만
          </div>
        </div>
      </div>

      {/* 2. AI 매입가 산출 내역 박스 (훅 값 1:1 표시, 새 계산 없음) */}
      <div className="p-3.5 bg-[#0f1015] border border-[#1e2029] rounded-xl space-y-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <span className="text-xs font-bold text-zinc-200 flex items-center gap-1.5">
            <span>🤖</span> AI 판단 매입가 (헤이딜러 내수 낙찰 기준)
          </span>
          <div className="px-2.5 py-1 rounded bg-blue-500/20 border border-blue-500/40 text-blue-300 text-xs font-bold font-mono">
            AI 매입가: {heydealerSummary.aiWholesalePrice.toLocaleString()}만원
          </div>
        </div>

        <div className="space-y-1 text-xs text-zinc-400 pt-0.5 leading-relaxed font-mono">
          <p>
            • <strong className="text-zinc-200">AI 산출 내역:</strong> <span className="text-sky-400 font-bold">{heydealerSummary.aiWholesalePrice.toLocaleString()}만원</span> (내수 평균 {heydealerSummary.avgPrice.toLocaleString()}만 대비 주행거리({mileageKm.toLocaleString()}km: {heydealerSummary.milAdj >= 0 ? `+${heydealerSummary.milAdj}` : heydealerSummary.milAdj}만), 옵션가치({heydealerSummary.optAdj >= 0 ? `+${heydealerSummary.optAdj}` : heydealerSummary.optAdj}만) 실시간 반영)
          </p>
          <p>
            • <strong className="text-zinc-200">동급 경매 평균:</strong> {heydealerSummary.avgPrice.toLocaleString()}만원 (무사고 {heydealerSummary.noAccAvg.toLocaleString()}만원 / 유사고 {heydealerSummary.accAvg.toLocaleString()}만원)
          </p>
        </div>
      </div>

      {/* 3. 등급 필터 & 낙찰 목록 테이블 */}
      <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl overflow-hidden shadow-sm">
        {/* 테이블 헤더 바 (등급 필터 select) */}
        <div className="p-3 border-b border-[#1e2029] flex flex-wrap items-center justify-between gap-2 bg-[#121317]">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-white">
              헤이딜러 낙찰 이력 ({filteredHeydealerBids.length}대)
            </span>
          </div>

          {availableHeydealerGrades.length > 1 && (
            <div className="flex items-center gap-1.5 bg-[#1a1c26] border border-[#2d3142] rounded-lg px-2.5 py-1">
              <span className="text-[11px] text-zinc-400 font-medium">등급 필터:</span>
              <select
                value={selectedHeydealerGradeFilter}
                onChange={(e) => setSelectedHeydealerGradeFilter(e.target.value)}
                className="bg-transparent text-xs text-sky-400 font-bold focus:outline-none cursor-pointer"
              >
                {bestMatchHeydealerGrade && (
                  <option value={bestMatchHeydealerGrade} className="bg-[#14151b] text-sky-300">
                    🎯 조회 등급: {bestMatchHeydealerGrade} ({heydealerGradeCounts[bestMatchHeydealerGrade] || 0}대)
                  </option>
                )}
                <option value="ALL" className="bg-[#14151b] text-zinc-200">
                  🌐 전체 등급 보기 (총 {heydealerBids.length}대)
                </option>
                {availableHeydealerGrades.filter(g => g !== bestMatchHeydealerGrade).map(g => (
                  <option key={g} value={g} className="bg-[#14151b] text-zinc-300">
                    🏷️ {g} ({heydealerGradeCounts[g] || 0}대)
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* 테이블 본문 (별도 자체 세로 스크롤 없음, 부모 스크롤 영역 안에서 자연스럽게 동작) */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-[#c7c9d1] border-collapse">
            <thead className="bg-[#14151b] text-[11px] text-zinc-400 border-b border-[#1e2029] uppercase sticky top-0 z-10">
              <tr>
                <th className="p-2.5 text-center w-10">선택</th>
                <th className="p-2.5 min-w-[140px]">차량명</th>
                <th className="p-2.5 w-16">연식</th>
                <th className="p-2.5 text-right w-24">주행거리</th>
                <th className="p-2.5 text-right w-28">낙찰가</th>
                <th className="p-2.5 w-24">낙찰일</th>
                <th className="p-2.5 w-24">사고구분</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2029]">
              {filteredHeydealerBids.map((b) => {
                const isSelected = selectedHeydealerBidId === b.id;
                return (
                  <tr
                    key={b.id}
                    onClick={() => setSelectedHeydealerBidId(b.id)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-blue-600/15 text-white font-medium'
                        : 'hover:bg-[#14151c]'
                    }`}
                  >
                    <td className="p-2.5 text-center">
                      <input
                        type="radio"
                        name="selected_v2_hd_bid"
                        checked={isSelected}
                        onChange={() => setSelectedHeydealerBidId(b.id)}
                        className="accent-blue-500 cursor-pointer"
                      />
                    </td>
                    <td className="p-2.5 text-white font-medium text-[11.5px] truncate max-w-[200px]" title={b.model}>
                      {b.model}
                    </td>
                    <td className="p-2.5 text-[11.5px] text-zinc-400 font-mono">
                      {b.year}
                    </td>
                    <td className="p-2.5 text-right text-[11.5px] font-mono text-zinc-200 font-semibold">
                      {b.mileage.toLocaleString()}km
                    </td>
                    <td className="p-2.5 text-right font-mono font-black text-[12px]">
                      {b.isExport ? (
                        <span className="text-rose-400">🚢 수출 {b.bidPrice}만</span>
                      ) : (
                        <span className="text-sky-400">{b.bidPrice.toLocaleString()}만원</span>
                      )}
                    </td>
                    <td className="p-2.5 text-[11px] text-emerald-400 font-mono">
                      {b.bidDate}
                    </td>
                    <td className="p-2.5 text-[11px]">
                      {b.accidentType === '완전무사고' ? (
                        <span className="text-emerald-400 font-medium">🟢 {b.accident}</span>
                      ) : b.accidentType === '유사고' ? (
                        <span className="text-rose-400 font-medium">🔴 {b.accident}</span>
                      ) : (
                        <span className="text-amber-400 font-medium">🟡 {b.accident}</span>
                      )}
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
