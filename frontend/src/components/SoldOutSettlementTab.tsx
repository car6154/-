import React from 'react';
import { InventorySettlementItem } from '@/types';
import { DollarSign, CheckCircle2, TrendingUp, ExternalLink } from 'lucide-react';

interface SoldOutSettlementTabProps {
  completedList: InventorySettlementItem[];
}

export const SoldOutSettlementTab: React.FC<SoldOutSettlementTabProps> = ({ completedList }) => {
  // Filter only completed items (상태 === '판매완료')
  const soldItems = completedList.filter(item => item.status === '판매완료');

  const totalSoldCount = soldItems.length;
  const totalSalesRevenue = soldItems.reduce((acc, curr) => acc + (curr.sellPrice || 0), 0);
  const totalNetProfit = soldItems.reduce((acc, curr) => acc + (curr.contributionMargin || 0), 0);
  const totalMyTake = soldItems.reduce((acc, curr) => acc + (curr.netProfit || curr.finalProfit || 0), 0);

  return (
    <div className="space-y-6">
      
      {/* Top Metric Cards matching Jay's original render_completed_tab */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        
        {/* Total Sold Count */}
        <div className="bg-[#0e0f13] border border-[#1c1d22] rounded-xl p-4">
          <div className="text-xs text-[#9194a1] flex items-center gap-1.5 font-medium">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            총 판매완료 대수
          </div>
          <div className="text-xl sm:text-2xl font-bold text-emerald-400 mt-1">
            {totalSoldCount.toLocaleString()}<span className="text-xs font-normal text-[#9194a1] ml-1">대 완판</span>
          </div>
          <div className="text-[11px] text-[#9194a1] mt-1">
            실판매 및 정산 완료 확정
          </div>
        </div>

        {/* Total Sales Revenue */}
        <div className="bg-[#0e0f13] border border-[#1c1d22] rounded-xl p-4">
          <div className="text-xs text-[#9194a1] flex items-center gap-1.5 font-medium">
            <DollarSign className="w-3.5 h-3.5 text-blue-400" />
            누적 총 매출 (판매가)
          </div>
          <div className="text-xl sm:text-2xl font-bold text-white mt-1">
            {totalSalesRevenue.toLocaleString()}<span className="text-xs font-normal text-[#9194a1] ml-1">만원</span>
          </div>
          <div className="text-[11px] text-[#9194a1] mt-1">
            완판 대금 총 합계
          </div>
        </div>

        {/* Total Contribution Margin */}
        <div className="bg-[#0e0f13] border border-[#1c1d22] rounded-xl p-4">
          <div className="text-xs text-[#9194a1] flex items-center gap-1.5 font-medium">
            <TrendingUp className="w-3.5 h-3.5 text-sky-400" />
            누적 총 공헌이익
          </div>
          <div className={`text-xl sm:text-2xl font-bold mt-1 ${totalNetProfit >= 0 ? 'text-sky-400' : 'text-rose-400'}`}>
            {totalNetProfit >= 0 ? `+${totalNetProfit.toLocaleString()}` : totalNetProfit.toLocaleString()}
            <span className="text-xs font-normal text-[#9194a1] ml-1">만원</span>
          </div>
          <div className="text-[11px] text-[#9194a1] mt-1">
            제경비·수수료 차감 후 공헌이익
          </div>
        </div>

        {/* Total My Take (내 실수익) */}
        <div className="bg-[#0e0f13] border border-[#cc9166]/50 rounded-xl p-4 bg-[#cc9166]/5 shadow-lg shadow-[#cc9166]/10">
          <div className="text-xs text-[#cc9166] flex items-center gap-1.5 font-bold">
            <DollarSign className="w-3.5 h-3.5 text-[#cc9166]" />
            내 정산 실수익 총합 (내 수익)
          </div>
          <div className={`text-xl sm:text-2xl font-black mt-1 ${totalMyTake >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {totalMyTake >= 0 ? `+${totalMyTake.toLocaleString()}` : totalMyTake.toLocaleString()}
            <span className="text-xs font-normal text-[#9194a1] ml-1">만원</span>
          </div>
          <div className="text-[11px] text-[#cc9166]/80 mt-1">
            공헌이익 × 요율 최종 실수령액
          </div>
        </div>

      </div>

      {/* Main Table: 판매완료 최종 확정 정산표 */}
      <div className="bg-[#0e0f13] border border-[#1c1d22] rounded-xl overflow-hidden">
        <div className="p-4 border-b border-[#1c1d22] flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white font-serif-display">
              판매완료 최종 확정 정산표 ({soldItems.length}대)
            </h3>
            <p className="text-xs text-[#9194a1] mt-0.5">
              판매가 완료된 차량들의 최종 확정 매출, 공헌이익 및 내 실수익 정산 명세서 (단위: 만원)
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-[#e2e3e9]">
            <thead className="bg-[#121317] text-[#9194a1] border-b border-[#1c1d22] font-medium">
              <tr>
                <th className="py-3 px-3">매입일</th>
                <th className="py-3 px-3">차량번호</th>
                <th className="py-3 px-3">차종</th>
                <th className="py-3 px-3 text-center">재고일</th>
                <th className="py-3 px-3 text-right">매입가</th>
                <th className="py-3 px-3 text-right">판매가</th>
                <th className="py-3 px-3 text-right">상품화</th>
                <th className="py-3 px-3 text-right">수수료</th>
                <th className="py-3 px-3 text-right">제경비</th>
                <th className="py-3 px-3 text-right">공헌이익</th>
                <th className="py-3 px-3 text-right">내 실수익</th>
                <th className="py-3 px-3 text-center">엔카</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1c1d22]">
              {soldItems.map((item) => {
                const profit = item.netProfit || item.finalProfit || 0;
                return (
                  <tr key={item.id} className="hover:bg-[#121317]/80 transition">
                    <td className="py-3 px-3 text-[#9194a1] whitespace-nowrap">
                      {item.buyDate}
                    </td>
                    <td className="py-3 px-3 font-semibold text-white whitespace-nowrap">
                      {item.carNumber}
                    </td>
                    <td className="py-3 px-3 font-medium text-white max-w-xs truncate">
                      {item.carName}
                    </td>
                    <td className="py-3 px-3 text-center whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                        {item.stockDays}일
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right font-medium text-[#9194a1]">
                      {item.buyPrice.toLocaleString()}만
                    </td>
                    <td className="py-3 px-3 text-right font-bold text-white">
                      {item.sellPrice.toLocaleString()}만
                    </td>
                    <td className="py-3 px-3 text-right text-[#9194a1]">
                      {item.repairCost > 0 ? `${item.repairCost}만` : '-'}
                    </td>
                    <td className="py-3 px-3 text-right text-[#9194a1]">
                      {item.heydealerFee > 0 ? `${item.heydealerFee}만` : '-'}
                    </td>
                    <td className="py-3 px-3 text-right text-[#9194a1]">
                      15만
                    </td>
                    <td className="py-3 px-3 text-right font-bold text-sky-400">
                      +{item.contributionMargin.toLocaleString()}만
                    </td>
                    <td className="py-3 px-3 text-right font-black text-emerald-400">
                      +{profit.toLocaleString()}만
                    </td>
                    <td className="py-3 px-3 text-center">
                      {item.encarUrl ? (
                        <a
                          href={item.encarUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] text-blue-400 hover:text-blue-300 hover:underline"
                        >
                          <span>보기</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      ) : (
                        <span className="text-[10px] text-slate-600">-</span>
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
