import React, { useState, useMemo } from 'react';
import { InventorySettlementItem } from '@/types';
import { 
  DollarSign, 
  Clock, 
  ExternalLink, 
  CheckCircle2, 
  AlertTriangle, 
  UserCheck,
  Check
} from 'lucide-react';

interface SettlementTabProps {
  settlementList: InventorySettlementItem[];
  onMarkSold?: (id: string, sellPrice?: number) => void;
  onAnalyzeInCockpit?: (item: InventorySettlementItem) => void;
}

export const SettlementTab: React.FC<SettlementTabProps> = ({
  settlementList,
  onMarkSold,
  onAnalyzeInCockpit,
}) => {
  const [salesTier, setSalesTier] = useState<string>('tier2');

  const getSalesFeeRate = (tier: string) => {
    switch (tier) {
      case 'tier1': return { rate: 0.002, fixed: 0, label: '15대 이하 (0.2%)' };
      case 'tier2': return { rate: 0.003, fixed: 0, label: '16~21대 (0.3%)' };
      case 'tier3': return { rate: 0.004, fixed: 0, label: '22~26대 (0.4%)' };
      case 'tier4': return { rate: 0.007, fixed: 0, label: '27~32대 (0.7%)' };
      case 'tier5': return { rate: 0.009, fixed: 0, label: '33대 이상 (0.9%)' };
      case 'export': return { rate: 0, fixed: 10, label: '수출 (대당 10만)' };
      case 'emp': return { rate: 0, fixed: 5, label: '임직원 구매 (대당 5만)' };
      default: return { rate: 0.003, fixed: 0, label: '16~21대 (0.3%)' };
    }
  };

  const currentTierInfo = getSalesFeeRate(salesTier);

  // Filter only holding stock (status !== '판매완료')
  const holdingItems = useMemo(() => {
    return settlementList.filter(item => item.status !== '판매완료');
  }, [settlementList]);

  // Auto fee rate based on total bought volume (tab_settlement.py)
  const totalBoughtCount = settlementList.length;
  const autoFeeRate = useMemo(() => {
    if (totalBoughtCount <= 12) return 0.10;
    if (totalBoughtCount <= 18) return 0.30;
    if (totalBoughtCount <= 31) return 0.40;
    return 0.50;
  }, [totalBoughtCount]);

  // Recalculate settlement amounts
  const calculatedItems = useMemo(() => {
    return holdingItems.map((item) => {
      const sell = item.sellPrice || 0;
      const buy = item.buyPrice || 0;
      const heyFee = item.heydealerFee || 25;
      const heyFeeWithTax = Math.round(heyFee * 1.1 * 10) / 10;
      const directExpense = 15; // 기본제경비 15만원
      
      let salesComm = 0;
      if (currentTierInfo.fixed > 0) {
        salesComm = currentTierInfo.fixed;
      } else {
        salesComm = Math.round(sell * currentTierInfo.rate * 10) / 10;
      }

      // 공헌이익: (판매가 - 매입가) / 1.1 - 수수료 - 상품화 - 제경비(15) - 판매수수료
      const vatMargin = sell > buy ? Math.round(((sell - buy) / 1.1) * 10) / 10 : 0;
      const totalExpenses = heyFeeWithTax + (item.repairCost || 0) + directExpense + salesComm;
      const contributionMargin = Math.round((vatMargin - totalExpenses) * 10) / 10;
      const effectiveRate = item.feeRate && item.feeRate > 0 ? item.feeRate : autoFeeRate;
      const myProfit = Math.round((contributionMargin * effectiveRate) * 10) / 10;

      return {
        ...item,
        heyFeeWithTax,
        salesComm,
        contributionMargin,
        myProfit,
        directExpense,
        feeRate: effectiveRate
      };
    });
  }, [holdingItems, currentTierInfo, autoFeeRate]);

  // KPIs
  const totalStockCount = calculatedItems.length;
  const normalStock = calculatedItems.filter(s => s.stockDays <= 30);
  const warningStock = calculatedItems.filter(s => s.stockDays > 30 && s.stockDays <= 60);
  const dangerStock = calculatedItems.filter(s => s.stockDays > 60);
  const totalStockCost = calculatedItems.reduce((acc, curr) => acc + (curr.buyPrice + (curr.repairCost || 0) + curr.heydealerFee + 15), 0);
  const totalEstimatedProfit = Math.round(calculatedItems.reduce((acc, curr) => acc + curr.myProfit, 0));

  return (
    <div className="space-y-6">
      
      {/* Header & Fee Selector */}
      <div className="bg-[#0e0f13] border border-[#1c1d22] rounded-xl p-4 sm:p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-white font-serif-display">
              재고 및 정산 관리 (현재 보유 차량)
            </h2>
            <p className="text-xs text-[#9194a1] mt-0.5">
              매입 확정 후 현재 보유 중인 재고 차량의 원가와 예상 손익 관리. 판매 완료 시 [판매완료] 버튼 클릭
            </p>
          </div>

          <div className="flex items-center gap-2 bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2">
            <UserCheck className="w-4 h-4 text-[#cc9166]" />
            <div className="text-xs">
              <span className="text-[#9194a1] block text-[10px]">수수료 구간:</span>
              <select
                value={salesTier}
                onChange={(e) => setSalesTier(e.target.value)}
                className="bg-transparent text-white font-semibold text-xs focus:outline-none cursor-pointer"
              >
                <option value="tier1" className="bg-[#121317]">15대 이하 (0.2%)</option>
                <option value="tier2" className="bg-[#121317]">16 ~ 21대 (0.3%) [기본]</option>
                <option value="tier3" className="bg-[#121317]">22 ~ 26대 (0.4%)</option>
                <option value="tier4" className="bg-[#121317]">27 ~ 32대 (0.7%)</option>
                <option value="tier5" className="bg-[#121317]">33대 이상 (0.9%)</option>
                <option value="export" className="bg-[#121317]">수출 (대당 10만)</option>
                <option value="emp" className="bg-[#121317]">임직원 구매 (대당 5만)</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* 🎯 보유 재고 실시간 동급 시세 분석 바 (tab_settlement.py 1:1 완벽 복원) */}
      <div className="bg-[#121317] border border-blue-500/40 rounded-xl p-3.5 shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-blue-400">🎯 보유 재고 실시간 동급 시세 분석</span>
            <span className="text-[10px] bg-blue-950 text-blue-300 border border-blue-800/60 px-1.5 py-0.5 rounded font-medium">메인 콕핏 원클릭 연동</span>
          </div>
          <span className="text-[11px] text-[#9194a1]">
            보유 차량을 선택하면 메인 시세 분석 콕핏으로 즉시 동급 매물을 스캔하여 이관합니다.
          </span>
        </div>
        <div className="flex flex-col sm:flex-row gap-2">
          <select
            onChange={(e) => {
              const selected = calculatedItems.find(i => i.carNumber === e.target.value);
              if (selected && onAnalyzeInCockpit) {
                onAnalyzeInCockpit(selected);
              }
            }}
            className="flex-1 bg-[#0a0b0e] border border-[#22242c] rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
          >
            <option value="">보유 재고 차량 선택 후 바로 분석 화면으로 이동...</option>
            {calculatedItems.map(item => (
              <option key={item.id} value={item.carNumber}>
                [{item.carNumber}] {item.carName} (매입 {item.buyPrice}만 / 판매 {item.sellPrice}만 / {item.stockDays}일차)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4">
        
        {/* Total Stock */}
        <div className="bg-[#0e0f13] border border-[#1c1d22] rounded-xl p-4">
          <div className="text-xs text-[#9194a1] flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-blue-400" />
            현재 보유 재고
          </div>
          <div className="text-xl sm:text-2xl font-bold text-white mt-1">
            {totalStockCount}<span className="text-xs font-normal text-[#9194a1] ml-1">대</span>
          </div>
          <div className="text-[11px] text-[#9194a1] mt-1">
            보유원가 합: {totalStockCost.toLocaleString()}만원
          </div>
        </div>

        {/* 30-Day Golden Time */}
        <div className="bg-[#0e0f13] border border-emerald-500/30 rounded-xl p-4 bg-emerald-500/5">
          <div className="text-xs text-emerald-400 flex items-center gap-1.5 font-medium">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            30일 이내 (골든타임)
          </div>
          <div className="text-xl sm:text-2xl font-bold text-emerald-300 mt-1">
            {normalStock.length}<span className="text-xs font-normal text-[#9194a1] ml-1">대</span>
          </div>
          <div className="text-[11px] text-emerald-400/80 mt-1">목표 마진 설계구간 유지</div>
        </div>

        {/* 31~60 Days Warning */}
        <div className="bg-[#0e0f13] border border-amber-500/30 rounded-xl p-4 bg-amber-500/5">
          <div className="text-xs text-amber-400 flex items-center gap-1.5 font-medium">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            31~60일 (주의 재고)
          </div>
          <div className="text-xl sm:text-2xl font-bold text-amber-300 mt-1">
            {warningStock.length}<span className="text-xs font-normal text-[#9194a1] ml-1">대</span>
          </div>
          <div className="text-[11px] text-amber-400/80 mt-1">
            {dangerStock.length > 0 ? `60일 초과 ${dangerStock.length}대 포함` : '원가회수 가격조정'}
          </div>
        </div>

        {/* Total Volume Incentive */}
        <div className="bg-[#0e0f13] border border-blue-500/30 rounded-xl p-4 bg-blue-500/5">
          <div className="text-xs text-blue-400 flex items-center gap-1.5 font-semibold">
            <UserCheck className="w-3.5 h-3.5 text-blue-400" />
            총 매입 인센티브
          </div>
          <div className="text-xl sm:text-2xl font-bold text-blue-300 mt-1">
            {totalBoughtCount}대 <span className="text-xs font-bold text-blue-400">({Math.round(autoFeeRate * 100)}%)</span>
          </div>
          <div className="text-[11px] text-[#9194a1] mt-1">
            {totalBoughtCount <= 12 ? '12대 이하 (10%)' : totalBoughtCount <= 18 ? '13~18대 (30%)' : totalBoughtCount <= 31 ? '19~31대 (40%)' : '32대 이상 (50%)'}
          </div>
        </div>

        {/* Expected Net Profit */}
        <div className="bg-[#0e0f13] border border-[#cc9166]/40 rounded-xl p-4 bg-[#cc9166]/5">
          <div className="text-xs text-[#cc9166] flex items-center gap-1.5 font-semibold">
            <DollarSign className="w-3.5 h-3.5 text-[#cc9166]" />
            판매 완료 시 내 실수익 예상
          </div>
          <div className="text-xl sm:text-2xl font-bold text-[#cc9166] mt-1">
            +{totalEstimatedProfit.toLocaleString()}<span className="text-xs font-normal text-[#9194a1] ml-1">만원</span>
          </div>
          <div className="text-[11px] text-[#9194a1] mt-1">
            공헌이익 × {Math.round(autoFeeRate * 100)}% 정산
          </div>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-[#0e0f13] border border-[#1c1d22] rounded-xl overflow-hidden">
        <div className="p-4 border-b border-[#1c1d22] flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white font-serif-display">
              실전 재고 정산 원장 ({calculatedItems.length}대)
            </h3>
            <p className="text-xs text-[#9194a1] mt-0.5">
              판매가 완료된 차량은 우측 [판매완료] 버튼을 누르면 '판매완료 정산' 탭으로 즉시 이동합니다.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-[#e2e3e9]">
            <thead className="bg-[#121317] text-[#9194a1] border-b border-[#1c1d22] font-medium">
              <tr>
                <th className="py-3 px-3">매입일</th>
                <th className="py-3 px-3">차량번호</th>
                <th className="py-3 px-3">차종명</th>
                <th className="py-3 px-3 text-center">재고일</th>
                <th className="py-3 px-3 text-right">매입가</th>
                <th className="py-3 px-3 text-right">판매가</th>
                <th className="py-3 px-3 text-right">상품화</th>
                <th className="py-3 px-3 text-right">수수료</th>
                <th className="py-3 px-3 text-right">공헌이익</th>
                <th className="py-3 px-3 text-right">실수익</th>
                <th className="py-3 px-3 text-center">작업</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1c1d22]">
              {calculatedItems.map((item) => {
                const isOver30 = item.stockDays > 30 && item.stockDays <= 60;
                const isOver60 = item.stockDays > 60;

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
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        isOver60 
                          ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          : isOver30
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      }`}>
                        {item.stockDays}일
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right font-medium text-white">
                      {item.buyPrice.toLocaleString()}만
                    </td>
                    <td className="py-3 px-3 text-right font-semibold text-white">
                      {item.sellPrice.toLocaleString()}만
                    </td>
                    <td className="py-3 px-3 text-right text-[#9194a1]">
                      {item.repairCost > 0 ? `${item.repairCost}만` : '-'}
                    </td>
                    <td className="py-3 px-3 text-right text-[#9194a1]">
                      {item.heydealerFee > 0 ? `${item.heydealerFee}만` : '-'}
                    </td>
                    <td className="py-3 px-3 text-right font-bold text-blue-400">
                      +{item.contributionMargin.toLocaleString()}만
                    </td>
                    <td className="py-3 px-3 text-right font-bold text-[#cc9166]">
                      +{item.myProfit.toLocaleString()}만
                    </td>
                    <td className="py-3 px-3 text-center whitespace-nowrap">
                      <div className="flex items-center justify-center gap-1.5">
                        {onAnalyzeInCockpit && (
                          <button
                            type="button"
                            onClick={() => onAnalyzeInCockpit(item)}
                            className="px-2 py-1 rounded bg-[#1e2029] hover:bg-[#2a2d3b] text-slate-300 border border-slate-700 text-[10px] font-semibold transition cursor-pointer"
                            title="동급 시세 분석 콕핏으로 이동"
                          >
                            <span>시세</span>
                          </button>
                        )}
                        <button
                          onClick={() => onMarkSold?.(item.id, item.sellPrice)}
                          className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold transition flex items-center gap-1 shadow"
                        >
                          <Check className="w-3 h-3" />
                          <span>판매완료</span>
                        </button>
                      </div>
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
