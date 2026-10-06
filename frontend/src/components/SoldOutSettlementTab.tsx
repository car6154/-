import React, { useState } from 'react';
import { InventorySettlementItem } from '@/types';
import { 
  Trophy, 
  TrendingUp, 
  DollarSign, 
  Coins, 
  RotateCcw, 
  ExternalLink 
} from 'lucide-react';

interface SoldOutSettlementTabProps {
  completedList: InventorySettlementItem[];
  onRestoreToStock?: (carNumber: string) => void;
}

export const SoldOutSettlementTab: React.FC<SoldOutSettlementTabProps> = ({ 
  completedList,
  onRestoreToStock,
}) => {
  const [restoreTargetCar, setRestoreTargetCar] = useState<string>('');

  // Filter only completed items (상태 === '판매완료') (tab_ledger.py L595-L596)
  const soldItems = completedList.filter(item => item.status === '판매완료');

  const totalSoldCount = soldItems.length;
  const totalSalesRevenue = soldItems.reduce((acc, curr) => acc + (curr.sellPrice || 0), 0);
  const totalNetProfit = soldItems.reduce((acc, curr) => acc + (curr.contributionMargin || 0), 0);
  const totalMyTake = soldItems.reduce((acc, curr) => acc + (curr.netProfit || curr.finalProfit || 0), 0);

  return (
    <div className="space-y-4">
      {/* 1. Header & Title (tab_ledger.py L592-L593) */}
      <div className="border-b border-[#1f2433] pb-3">
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <span>🎉 판매완료 정산 내역</span>
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          📋 판매가 완료된 차량들의 최종 확정 매출, 공헌이익, 그리고 내 실수익을 확인·관리합니다.
        </p>
      </div>

      {/* 2. Top Metric KPI Dashboard (tab_ledger.py L604-L635) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* 총 판매완료 대수 */}
        <div className="bg-[#12151e] border border-[#232733] rounded-xl p-3.5 flex items-center gap-3.5 shadow-sm">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-lg">
            🏆
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">총 판매완료 대수</div>
            <div className="text-lg font-bold text-emerald-400 mt-0.5">
              {totalSoldCount.toLocaleString()} 대
            </div>
          </div>
        </div>

        {/* 누적 총 매출 (판매가) */}
        <div className="bg-[#12151e] border border-[#232733] rounded-xl p-3.5 flex items-center gap-3.5 shadow-sm">
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-lg">
            📈
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">누적 총 매출(판매가)</div>
            <div className="text-lg font-bold text-white mt-0.5">
              {totalSalesRevenue.toLocaleString()} 만원
            </div>
          </div>
        </div>

        {/* 누적 총 공헌이익 */}
        <div className="bg-[#12151e] border border-[#232733] rounded-xl p-3.5 flex items-center gap-3.5 shadow-sm">
          <div className="w-10 h-10 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-lg">
            📊
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">누적 총 공헌이익</div>
            <div className={`text-lg font-bold mt-0.5 ${totalNetProfit >= 0 ? 'text-sky-400' : 'text-rose-400'}`}>
              {totalNetProfit >= 0 ? `+${totalNetProfit.toLocaleString()}` : totalNetProfit.toLocaleString()} 만원
            </div>
          </div>
        </div>

        {/* 내 정산 실수익 총합 */}
        <div className="bg-[#12151e] border border-amber-600/70 rounded-xl p-3.5 flex items-center gap-3.5 shadow-sm">
          <div className="w-10 h-10 rounded-lg bg-amber-950/60 border border-amber-700/60 flex items-center justify-center text-lg">
            💰
          </div>
          <div>
            <div className="text-xs text-amber-400 font-bold">내 정산 실수익 총합</div>
            <div className={`text-lg font-black mt-0.5 ${totalMyTake >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {totalMyTake >= 0 ? `+${totalMyTake.toLocaleString()}` : totalMyTake.toLocaleString()} 만원
            </div>
          </div>
        </div>
      </div>

      {/* 3. Main Completed Settlement Table (tab_ledger.py L637-L690) */}
      {soldItems.length > 0 ? (
        <div className="bg-[#0f1117] border border-[#232733] rounded-xl overflow-hidden">
          <div className="p-3 border-b border-[#232733] flex items-center justify-between">
            <span className="text-xs font-bold text-slate-200">
              📜 판매완료 최종 확정 정산표 (단위: 만원)
            </span>
            <span className="text-xs text-slate-500">
              총 {soldItems.length}대 완판 완료
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-[#e2e3e9]">
              <thead className="bg-[#181b24] text-slate-400 border-b border-[#282c3c] font-bold">
                <tr>
                  <th className="py-2.5 px-2 text-center w-10">순차</th>
                  <th className="py-2.5 px-2.5 whitespace-nowrap">매입일</th>
                  <th className="py-2.5 px-2.5 whitespace-nowrap">차량번호</th>
                  <th className="py-2.5 px-3">차종</th>
                  <th className="py-2.5 px-2 text-center whitespace-nowrap">재고일</th>
                  <th className="py-2.5 px-2.5 text-right whitespace-nowrap">매입가</th>
                  <th className="py-2.5 px-2.5 text-right whitespace-nowrap text-sky-400">판매가</th>
                  <th className="py-2.5 px-2 text-center whitespace-nowrap">외판</th>
                  <th className="py-2.5 px-2 text-right whitespace-nowrap">상품화</th>
                  <th className="py-2.5 px-2 text-right whitespace-nowrap">수수료</th>
                  <th className="py-2.5 px-2 text-right whitespace-nowrap">제경비</th>
                  <th className="py-2.5 px-2 text-right whitespace-nowrap">판매수수료</th>
                  <th className="py-2.5 px-2.5 text-right whitespace-nowrap text-sky-400">공헌이익</th>
                  <th className="py-2.5 px-2.5 text-right whitespace-nowrap text-amber-400 font-bold">실수익</th>
                  <th className="py-2.5 px-2 text-center whitespace-nowrap">수수료율</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1a1d27]">
                {soldItems.map((item) => {
                  const profit = item.netProfit || item.finalProfit || 0;
                  return (
                    <tr key={item.id} className="hover:bg-[#151824] transition">
                      <td className="py-2.5 px-2 text-center text-slate-500 font-mono">
                        {item.order}
                      </td>
                      <td className="py-2.5 px-2.5 text-slate-400 whitespace-nowrap font-mono">
                        {item.buyDate}
                      </td>
                      <td className="py-2.5 px-2.5 font-bold text-white whitespace-nowrap">
                        {item.carNumber}
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-slate-200 max-w-xs truncate">
                        {item.carName}
                      </td>
                      <td className="py-2.5 px-2 text-center whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                          {item.stockDays}일
                        </span>
                      </td>
                      <td className="py-2.5 px-2.5 text-right text-slate-400 whitespace-nowrap">
                        {item.buyPrice.toLocaleString()}만
                      </td>
                      <td className="py-2.5 px-2.5 text-right font-bold text-white whitespace-nowrap">
                        {item.sellPrice.toLocaleString()}만
                      </td>
                      <td className="py-2.5 px-2 text-center text-amber-400 whitespace-nowrap">
                        {item.outerRepairs > 0 ? `${item.outerRepairs}판` : '0판'}
                      </td>
                      <td className="py-2.5 px-2 text-right text-slate-300 whitespace-nowrap">
                        {item.repairCost > 0 ? `${item.repairCost}만` : '-'}
                      </td>
                      <td className="py-2.5 px-2 text-right text-slate-300 whitespace-nowrap">
                        {item.heydealerFee > 0 ? `${item.heydealerFee}만` : '-'}
                      </td>
                      <td className="py-2.5 px-2 text-right text-slate-400 whitespace-nowrap">
                        {item.baseExpenses || 15}만
                      </td>
                      <td className="py-2.5 px-2 text-right text-slate-400 whitespace-nowrap">
                        {item.salesCommission > 0 ? `${item.salesCommission}만` : '-'}
                      </td>
                      <td className="py-2.5 px-2.5 text-right font-bold text-sky-400 whitespace-nowrap">
                        +{item.contributionMargin.toLocaleString()}만
                      </td>
                      <td className="py-2.5 px-2.5 text-right font-black text-amber-400 whitespace-nowrap">
                        +{profit.toLocaleString()}만
                      </td>
                      <td className="py-2.5 px-2 text-center text-slate-300 whitespace-nowrap font-mono">
                        {Math.round((item.feeRate || 0.1) * 100)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-[#12151e] border border-[#232733] rounded-xl p-8 text-center text-slate-400 text-xs">
          아직 판매완료된 차량이 없습니다. [💰 실전 재고 및 정산 관리] 탭에서 판매된 차량의 [판매완료]를 클릭하시면 여기에 정산 내역이 기록됩니다.
        </div>
      )}

      {/* 4. Restore to Stock Feature (tab_ledger.py L692-L704) */}
      {soldItems.length > 0 && (
        <div className="bg-[#12151e] border border-[#232733] p-4 rounded-xl">
          <div className="flex items-center gap-2 text-xs font-bold text-sky-400 mb-1">
            <RotateCcw className="w-3.5 h-3.5" />
            <span>판매완료 차량 ➔ 보유재고로 복구</span>
          </div>
          <p className="text-[11px] text-slate-400 mb-3">
            실수로 [판매완료] 처리했거나 판매가 취소된 차량을 다시 보유재고 탭으로 복구합니다.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex-1 min-w-[200px]">
              <select
                value={restoreTargetCar}
                onChange={(e) => setRestoreTargetCar(e.target.value)}
                className="w-full bg-[#0a0b0e] border border-[#282c3c] rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500"
              >
                <option value="">다시 보유재고로 복구할 차량 선택...</option>
                {soldItems.map((c) => (
                  <option key={c.id} value={c.carNumber}>
                    {c.carNumber} | {c.carName}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              disabled={!restoreTargetCar}
              onClick={() => {
                if (restoreTargetCar && onRestoreToStock) {
                  onRestoreToStock(restoreTargetCar);
                  setRestoreTargetCar('');
                }
              }}
              className="px-3.5 py-1.5 bg-sky-950 hover:bg-sky-900 border border-sky-700/60 text-sky-300 rounded-lg text-xs font-bold transition disabled:opacity-40 flex items-center gap-1.5"
            >
              <RotateCcw className="w-3 h-3" />
              <span>보유재고로 복구</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
