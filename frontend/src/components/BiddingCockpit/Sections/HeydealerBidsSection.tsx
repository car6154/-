import React from 'react';
import { Eye } from 'lucide-react';

export interface HeydealerBidItem {
  id: string;
  model: string;
  year: number | string;
  mileage: number;
  bidPrice: number;
  bidDate: string;
  accident: string;
  accidentType: '완전무사고' | '단순수리' | '유사고';
  options: string;
  isExport: boolean;
  repairs: { part: string; repair: string; desc: string }[];
  keyOptions: string[];
  link?: string;
}

export interface HeydealerSummaryData {
  hasData: boolean;
  totalCount: number;
  domCount: number;
  exportCount: number;
  minPrice: number;
  maxPrice: number;
  avgPrice: number;
  aiWholesalePrice: number;
  milAdj: number;
  optAdj: number;
  noAccAvg: number;
  accAvg: number;
}

export interface HeydealerBidsSectionProps {
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
  selectedHeydealerBid: HeydealerBidItem | null;
  mileageKm: number;
}

export const HeydealerBidsSection: React.FC<HeydealerBidsSectionProps> = ({
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
  mileageKm,
}) => {
  return (
    <div className="bg-[#0e0f13] border border-[#1c1d22] rounded-xl p-4 sm:p-5 shadow-lg space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#1c1d22]">
        <div className="flex items-center gap-2">
          <span className="text-base font-bold text-white font-serif-display flex items-center gap-1.5">
            🤖 헤이딜러 동급 낙찰 데이터 요약 (도매 실거래)
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {availableHeydealerGrades.length > 1 && (
            <div className="flex items-center gap-1.5 bg-[#14151b] border border-[#262833] rounded-lg px-2 py-1">
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
          {heydealerSummary.hasData && (
            <span className="text-xs text-blue-400 font-semibold">
              최근 1달 간 {heydealerSummary.totalCount}건 낙찰 기록 전수 분석 (상세 스펙 연동)
            </span>
          )}
        </div>
      </div>

      {heydealerSummary.hasData ? (
        <>
          {/* 4 Wholesale Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-[#121317] border border-[#1c1d22] rounded-xl p-3">
              <span className="text-[10px] text-[#8b8e9d] block">총 매물 수</span>
              <div className="flex items-baseline gap-1 mt-1">
                <span className="text-xl font-black text-white font-serif-display">{heydealerSummary.totalCount} 대</span>
                <span className="text-[10px] text-[#717482]">
                  {heydealerSummary.exportCount > 0 ? `(내수 ${heydealerSummary.domCount} / 수출 ${heydealerSummary.exportCount})` : '(전체 내수)'}
                </span>
              </div>
            </div>

            <div className="bg-[#121317] border border-[#1c1d22] rounded-xl p-3">
              <span className="text-[10px] text-[#8b8e9d] block">최저가(내수)</span>
              <div className="text-xl font-black text-blue-400 font-serif-display mt-1 flex items-center gap-1">
                {heydealerSummary.minPrice.toLocaleString()} 만원 <span>⬇</span>
              </div>
            </div>

            <div className="bg-[#121317] border border-[#1c1d22] rounded-xl p-3">
              <span className="text-[10px] text-[#8b8e9d] block">최고가(내수)</span>
              <div className="text-xl font-black text-blue-400 font-serif-display mt-1 flex items-center gap-1">
                {heydealerSummary.maxPrice.toLocaleString()} 만원 <span>⬆</span>
              </div>
            </div>

            <div className="bg-[#121317] border border-[#1c1d22] rounded-xl p-3">
              <span className="text-[10px] text-[#8b8e9d] block">내수 평균가</span>
              <div className="text-xl font-black text-white font-serif-display mt-1">
                {heydealerSummary.avgPrice.toLocaleString()} 만원
              </div>
            </div>
          </div>

          {/* AI Wholesale Bid Summary Box */}
          <div className="p-3.5 bg-[#121317] border border-[#1c1d22] rounded-xl space-y-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <span className="text-xs font-bold text-white">
                📊 (2) 예상 매입가 기준 (헤이딜러 내수 낙찰 데이터)
              </span>
              <div className="px-2.5 py-1 rounded-lg bg-blue-600 text-white text-xs font-bold shadow-md">
                AI 판단 매입가: {heydealerSummary.aiWholesalePrice.toLocaleString()} 만원
              </div>
            </div>

            <div className="space-y-1 text-xs text-[#8b8e9d] pt-1">
              <p>
                • <strong className="text-white">AI 매입(낙찰)가 산출 내역:</strong> <span className="text-blue-400 font-bold">{heydealerSummary.aiWholesalePrice.toLocaleString()}만원</span> (내수 평균 {heydealerSummary.avgPrice}만 대비 주행거리({mileageKm.toLocaleString()}km: {heydealerSummary.milAdj >= 0 ? `+${heydealerSummary.milAdj}` : heydealerSummary.milAdj}만), 옵션가치({heydealerSummary.optAdj >= 0 ? `+${heydealerSummary.optAdj}` : heydealerSummary.optAdj}만) 실시간 반영)
              </p>
              <p>
                • <strong className="text-white">동급 경매 평균(내수):</strong> {heydealerSummary.avgPrice.toLocaleString()}만원 (무사고 {heydealerSummary.noAccAvg.toLocaleString()}만원 / 유사고 {heydealerSummary.accAvg.toLocaleString()}만원)
              </p>
            </div>
          </div>

          {/* 20 Auction Bids 2-Column Layout */}
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 items-start">
            
            {/* Table (Left 7 cols) */}
            <div className="xl:col-span-7 space-y-2">
              <div className="flex items-center justify-between text-xs font-bold text-white px-1">
                <span>📰 헤이딜러 낙찰 이력리스트</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 font-semibold">
                  {selectedHeydealerGradeFilter === 'ALL' ? `🌐 전체 (${filteredHeydealerBids.length}대)` : `🎯 ${selectedHeydealerGradeFilter} (${filteredHeydealerBids.length}대)`}
                </span>
              </div>

              <div className="overflow-x-auto border border-[#1c1d22] rounded-xl max-h-80 overflow-y-auto scrollbar-thin scrollbar-thumb-zinc-700">
                <table className="w-full text-left text-xs text-[#c7c9d1]">
                  <thead className="bg-[#121317] text-[11px] text-[#8b8e9d] sticky top-0 uppercase border-b border-[#1c1d22] z-10">
                    <tr>
                      <th className="p-2 text-center w-8 bg-[#121317]">선택</th>
                      <th className="p-2 bg-[#121317]">차량명</th>
                      <th className="p-2 bg-[#121317]">연식</th>
                      <th className="p-2 text-right bg-[#121317]">주행거리</th>
                      <th className="p-2 text-right bg-[#121317]">낙찰가</th>
                      <th className="p-2 bg-[#121317]">낙찰시기</th>
                      <th className="p-2 bg-[#121317]">사고유무</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1c1d22]">
                    {filteredHeydealerBids.map((b) => {
                      const isSelected = selectedHeydealerBid?.id === b.id;
                      return (
                        <tr
                          key={b.id}
                          onClick={() => setSelectedHeydealerBidId(b.id)}
                          className={`cursor-pointer transition ${
                            isSelected ? 'bg-rose-500/15 text-white font-medium' : 'hover:bg-[#14151c]'
                          }`}
                        >
                          <td className="p-2 text-center">
                            <input
                              type="radio"
                              name="selected_hd_bid"
                              checked={isSelected}
                              onChange={() => setSelectedHeydealerBidId(b.id)}
                              className="accent-rose-500 cursor-pointer"
                            />
                          </td>
                          <td className="p-2 text-white font-medium text-[11px] max-w-[140px] truncate">{b.model}</td>
                          <td className="p-2 text-[11px] text-[#8b8e9d]">{b.year}</td>
                          <td className="p-2 text-right text-[11px] font-semibold text-white">
                            {b.mileage.toLocaleString()} km
                          </td>
                          <td className="p-2 text-right font-extrabold font-serif-display text-[11px]">
                            {b.isExport ? (
                              <span className="text-rose-400">🚢 수출 {b.bidPrice} 만원</span>
                            ) : (
                              <span className="text-blue-400">{b.bidPrice.toLocaleString()} 만원</span>
                            )}
                          </td>
                          <td className="p-2 text-[11px] font-medium text-emerald-400">{b.bidDate}</td>
                          <td className="p-2 text-[11px]">
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

            {/* Right: Detailed Wholesale Specs (Right 5 cols) */}
            <div className="xl:col-span-5 bg-[#121317] border border-[#1c1d22] rounded-xl p-4 space-y-3.5">
              <div className="flex items-center justify-between pb-2 border-b border-[#1c1d22]">
                <div className="flex items-center gap-1.5 text-xs font-bold text-white">
                  <Eye className="w-3.5 h-3.5 text-blue-400" />
                  <span>상세설명 및 옵션 (헤이딜러)</span>
                </div>
              </div>

              {selectedHeydealerBid ? (
                <>
                  <div className="space-y-1">
                    <div className="text-base font-bold text-white">{selectedHeydealerBid.model}</div>
                    <div className="text-xs text-[#8b8e9d]">{selectedHeydealerBid.year} · {selectedHeydealerBid.mileage.toLocaleString()}km</div>
                  </div>

                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {selectedHeydealerBid.isExport ? (
                      <span className="px-2.5 py-1 rounded bg-blue-500/20 text-blue-300 font-bold text-xs">
                        🚢 수출딜러 낙찰
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 font-bold text-xs">
                        🚙 내수딜러 낙찰
                      </span>
                    )}
                    <span className="px-2.5 py-1 rounded bg-rose-500/20 text-rose-300 font-extrabold text-xs">
                      {selectedHeydealerBid.isExport ? `🚢 수출 ${selectedHeydealerBid.bidPrice}만원` : `${selectedHeydealerBid.bidPrice.toLocaleString()}만원`}
                    </span>
                    <span className="px-2.5 py-1 rounded bg-[#1c1d22] text-[#8b8e9d] font-semibold text-xs">
                      ⏱️ {selectedHeydealerBid.bidDate}
                    </span>
                  </div>

                  <div className="pt-2 border-t border-[#1c1d22] space-y-2">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-[#8b8e9d]">사고유무:</span>
                      <span className={`px-2 py-0.5 rounded font-bold text-[11px] ${
                        selectedHeydealerBid.accidentType === '완전무사고'
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : selectedHeydealerBid.accidentType === '유사고'
                          ? 'bg-rose-500/20 text-rose-300'
                          : 'bg-amber-500/20 text-amber-300'
                      }`}>
                        {selectedHeydealerBid.accident}
                      </span>
                    </div>

                    <div className="text-xs text-white font-bold pt-1">🛠️ 교환 및 수리 부위</div>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedHeydealerBid.repairs && selectedHeydealerBid.repairs.length > 0 ? (
                        selectedHeydealerBid.repairs.map((r, pIdx) => (
                          <span
                            key={pIdx}
                            className="px-2 py-0.5 rounded bg-amber-600/30 text-amber-200 border border-amber-500/40 text-[10px] font-semibold"
                          >
                            {r.desc}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-[#717482]">수리 이력 없음 (완전무사고)</span>
                      )}
                    </div>

                    <div className="pt-2">
                      <div className="text-xs text-white font-bold">주요옵션</div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {selectedHeydealerBid.keyOptions && selectedHeydealerBid.keyOptions.length > 0 ? (
                          selectedHeydealerBid.keyOptions.map((opt, oIdx) => (
                            <span
                              key={oIdx}
                              className="px-2 py-0.5 rounded bg-blue-500/15 text-blue-300 border border-blue-500/20 text-[10px] font-medium"
                            >
                              {opt}
                            </span>
                          ))
                        ) : (
                          <div className="text-xs text-[#717482]">{selectedHeydealerBid.options || '등록된 옵션 없음'}</div>
                        )}
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-xs text-[#717482] py-8 text-center">선택된 헤이딜러 매물이 없습니다.</div>
              )}

            </div>

          </div>
        </>
      ) : (
        <div className="p-4 bg-[#121317] border border-[#1c1d22] rounded-xl space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-[#cc9166]">
            <span>📋 (2) 예상 매입가 기준 (헤이딜러 낙찰 데이터)</span>
          </div>
          <p className="text-xs text-[#8b8e9d] leading-relaxed">
            • 상단 헤이딜러 URL 입력창에 경매 차량 주소(예: <code className="text-blue-400 font-mono">https://dealer.heydealer.com/cars/...</code>)를 입력하고 <strong>[AI 견적 산출]</strong>을 실행하시면, 실제 헤이딜러 20대 동급 낙찰 이력과 주행거리·옵션이 보정된 <strong>AI 판단 매입(낙찰)가</strong>가 여기에 실시간으로 계산되어 표시됩니다.
          </p>
        </div>
      )}

    </div>
  );
};
