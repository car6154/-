import React, { useState, useMemo } from 'react';
import { InventorySettlementItem } from '@/types';
import {
  Car,
  Clock,
  AlertTriangle,
  TrendingDown,
  Coins,
  PackageCheck,
  Search,
  ExternalLink,
  CheckCircle2,
  Check
} from 'lucide-react';

interface SettlementTabProps {
  settlementList: InventorySettlementItem[];
  onMarkSold?: (id: string, sellPrice?: number) => void;
  onAnalyzeInCockpit?: (item: InventorySettlementItem) => void;
  onUpdateItem?: (updatedItem: InventorySettlementItem) => void;
}

export const SettlementTab: React.FC<SettlementTabProps> = ({
  settlementList,
  onMarkSold,
  onAnalyzeInCockpit,
  onUpdateItem,
}) => {
  // tab_settlement.py states
  const [filterMode, setFilterMode] = useState<'all' | '30plus' | '60plus' | 'margin_risk'>('all');
  const [selectedStockCarNum, setSelectedStockCarNum] = useState<string>('');

  // 1. 구간별 기본 수수료율 함수 (2026년 4분기 공문 기준: 이익/손실 차등)
  const getAutoFeeRate = (volume: number, isLoss = false): number => {
    if (volume <= 12) return isLoss ? 0.30 : 0.10;
    if (volume <= 16) return isLoss ? 0.30 : 0.20;
    if (volume <= 19) return 0.30;
    if (volume <= 31) return 0.40;
    return 0.50;
  };

  const totalBoughtCount = settlementList.length;
  const autoFeeRate = getAutoFeeRate(totalBoughtCount);

  // 2. 보유 재고 vs 완료 재고 분리 (tab_settlement.py L103-L108)
  const stockItems = useMemo(() => {
    return settlementList.filter(item => item.status !== '판매완료');
  }, [settlementList]);

  const soldItems = useMemo(() => {
    return settlementList.filter(item => item.status === '판매완료');
  }, [settlementList]);

  // 3. settlement_service.py recalc_settlement_df 공식 100% 1:1 완벽 계산
  const calculatedStockItems = useMemo(() => {
    return stockItems.map((item, idx) => {
      const order = item.order > 0 ? item.order : (idx + 1);
      const pSell = item.sellPrice || 0;
      const pBuy = item.buyPrice || 0;
      const extCnt = item.outerRepairs || 0;

      // 기본제경비 = 15만원 고정 (settlement_service.py L24-L25)
      const baseExpenses = item.baseExpenses > 0 ? item.baseExpenses : 15;

      // 외판수 > 0이고 상품화가 0이면 외판수 * 13만원 (L27-L29)
      const repairCost = (item.repairCost > 0) ? item.repairCost : (extCnt > 0 ? extCnt * 13 : 0);

      // 판매수수료: 판매가의 0.7% (L31-L36)
      const calcFee = pSell > 0 ? Math.round(pSell * 0.007) : 0;
      const salesCommission = (item.salesCommission && item.salesCommission > 0) ? item.salesCommission : calcFee;

      // 수수료율: 사용자 직접 지정 수수료율_수동 우선, 없으면 feeRate, 없으면 구간별 autoFeeRate (L38-L45)
      const effectiveFeeRate = (item.feeRateManual && item.feeRateManual > 0)
        ? item.feeRateManual
        : ((item.feeRate && item.feeRate > 0) ? item.feeRate : autoFeeRate);

      // 공헌손익 및 실수익 계산 (L47-L56)
      let contributionMargin = 0;
      let netProfit = 0;
      let finalFeeRate = effectiveFeeRate;

      if (pSell > 0) {
        const vatMargin = (pSell - pBuy) / 1.1;
        const totalExpenses = (item.heydealerFee || 0) + repairCost + baseExpenses + salesCommission;
        contributionMargin = Math.round(vatMargin - totalExpenses);

        // 손실 발생 시 손실 요율 자동 적용 (사용자 수동 입력값이 없는 경우)
        if (contributionMargin < 0 && (!item.feeRateManual || item.feeRateManual <= 0)) {
          finalFeeRate = getAutoFeeRate(totalBoughtCount, true);
        }
        netProfit = Math.round(contributionMargin * finalFeeRate);
      }

      return {
        ...item,
        order,
        baseExpenses,
        repairCost,
        salesCommission,
        feeRate: finalFeeRate,
        contributionMargin,
        netProfit,
      };
    });
  }, [stockItems, autoFeeRate]);

  // 4. 상단 핵심 현황 대시보드 지표 (tab_settlement.py L107-L127)
  const stockCount = calculatedStockItems.length;
  const soldCount = soldItems.length;

  const totalStockCost = useMemo(() => {
    return calculatedStockItems.reduce((acc, curr) => {
      return acc + (curr.buyPrice + curr.repairCost + (curr.heydealerFee || 0) + curr.baseExpenses);
    }, 0);
  }, [calculatedStockItems]);

  const avgStockDays = useMemo(() => {
    if (calculatedStockItems.length === 0) return 0;
    const sumDays = calculatedStockItems.reduce((acc, curr) => acc + (curr.stockDays || 0), 0);
    return Math.round(sumDays / calculatedStockItems.length);
  }, [calculatedStockItems]);

  const over30Count = useMemo(() => {
    return calculatedStockItems.filter(s => s.stockDays >= 30 && s.stockDays < 60).length;
  }, [calculatedStockItems]);

  const over60Count = useMemo(() => {
    return calculatedStockItems.filter(s => s.stockDays >= 60).length;
  }, [calculatedStockItems]);

  const marginRiskCount = useMemo(() => {
    return calculatedStockItems.filter(s => s.sellPrice > 0 && s.contributionMargin < 100).length;
  }, [calculatedStockItems]);

  // 5. 필터 적용 (tab_settlement.py L590-L601)
  const filteredViewItems = useMemo(() => {
    switch (filterMode) {
      case '30plus':
        return calculatedStockItems.filter(s => s.stockDays >= 30 && s.stockDays < 60);
      case '60plus':
        return calculatedStockItems.filter(s => s.stockDays >= 60);
      case 'margin_risk':
        return calculatedStockItems.filter(s => s.sellPrice > 0 && s.contributionMargin < 100);
      default:
        return calculatedStockItems;
    }
  }, [calculatedStockItems, filterMode]);

  // Selected car for live cockpit analysis
  const currentSelectedStock = useMemo(() => {
    return calculatedStockItems.find(i => i.carNumber === selectedStockCarNum) || calculatedStockItems[0];
  }, [calculatedStockItems, selectedStockCarNum]);

  return (
    <div className="space-y-4">
      {/* 1. Header & Title */}
      <div className="border-b border-[#1f2433] pb-3">
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <span>💰 실전 재고 및 정산 관리 (현재 보유 차량)</span>
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          📋 매입 확정 후 현재 보유 중인 재고 차량의 원가와 손익을 관리합니다. 판매가 완료되면 표 맨 끝의 **[판매완료]**를 클릭하여 이동하세요.
        </p>
      </div>

      {/* 2. Top Metric KPI Dashboard (tab_settlement.py L131-L179) */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {/* 보유 재고 */}
        <div className="bg-[#12151e] border border-[#232733] rounded-xl p-3 flex items-center gap-3 shadow-sm">
          <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-base">
            🚗
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">보유 재고</div>
            <div className="text-base font-bold text-sky-400">
              {stockCount}대 <span className="text-[11px] font-normal text-slate-500">(완료: {soldCount})</span>
            </div>
          </div>
        </div>

        {/* 평균 재고일 */}
        <div className="bg-[#12151e] border border-[#232733] rounded-xl p-3 flex items-center gap-3 shadow-sm">
          <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-base">
            ⏱️
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">평균 재고일</div>
            <div className={`text-base font-bold ${avgStockDays < 15 ? 'text-emerald-400' : 'text-amber-400'}`}>
              {avgStockDays}일
            </div>
          </div>
        </div>

        {/* 장기 재고 (30일+/60일+) */}
        <div className={`bg-[#12151e] rounded-xl p-3 flex items-center gap-3 shadow-sm border ${over60Count > 0 ? 'border-rose-500' : over30Count > 0 ? 'border-amber-500' : 'border-[#232733]'
          }`}>
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center text-base ${over60Count > 0 ? 'bg-rose-500/20 text-rose-400' : over30Count > 0 ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-800'
            }`}>
            ⚠️
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">장기 재고 (30+/60+)</div>
            <div className="text-base font-bold">
              <span className={over60Count > 0 ? 'text-rose-400 font-extrabold' : 'text-slate-400'}>{over60Count}대</span>
              <span className="text-xs text-amber-400 ml-1">(30일+: {over30Count}대)</span>
            </div>
          </div>
        </div>

        {/* 마진 주의 (100만↓) */}
        <div className={`bg-[#12151e] rounded-xl p-3 flex items-center gap-3 shadow-sm border ${marginRiskCount > 0 ? 'border-rose-500' : 'border-[#232733]'
          }`}>
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center text-base ${marginRiskCount > 0 ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/10 text-emerald-400'
            }`}>
            📉
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">마진 주의 (100만↓)</div>
            <div className={`text-base font-bold ${marginRiskCount > 0 ? 'text-rose-400 font-extrabold' : 'text-emerald-400'}`}>
              {marginRiskCount}대
            </div>
          </div>
        </div>

        {/* 재고 총 원가 */}
        <div className="bg-[#12151e] border border-[#232733] rounded-xl p-3 flex items-center gap-3 shadow-sm">
          <div className="w-9 h-9 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-base">
            💵
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">재고 총 원가</div>
            <div className="text-base font-bold text-slate-100">
              {totalStockCost.toLocaleString()}만원
            </div>
          </div>
        </div>

        {/* 총 매입 대수 (인센티브) */}
        <div className="bg-[#12151e] border border-sky-600 rounded-xl p-3 flex items-center gap-3 shadow-sm">
          <div className="w-9 h-9 rounded-lg bg-sky-950 border border-sky-700 flex items-center justify-center text-base">
            📦
          </div>
          <div>
            <div className="text-[11px] text-sky-400 font-medium">총 매입 대수</div>
            <div className="text-base font-bold text-sky-400">
              {totalBoughtCount}대 <span className="text-xs text-slate-400">({Math.round(autoFeeRate * 100)}%)</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2-1. 2026년 4분기 매입사원 수수료 및 인센티브 운영 기준 안내 */}
      <div className="bg-[#151728] border border-indigo-500/30 rounded-xl p-3 shadow-md flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold border border-indigo-500/40 text-[11px]">
              📢 2026년 4분기 매입사원 수수료 기준
            </span>
            <span className="text-slate-400 text-[11px]">시행기간: 2026.10.01 ~ 2026.12.31</span>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-slate-300 text-[11px]">
            <span>• ~12대: <b className="text-emerald-400">이익 10%</b> / <b className="text-rose-400">손실 30%</b></span>
            <span>• 13~16대: <b className="text-emerald-400">이익 20%</b> / <b className="text-rose-400">손실 30%</b></span>
            <span>• 17~19대: <b>30%</b></span>
            <span>• 20~31대: <b>40%</b></span>
            <span>• 32대 이상: <b>50%</b></span>
          </div>
        </div>
        <div className="flex items-center gap-2 text-[11px]">
          <div className="px-2.5 py-1 rounded-lg bg-emerald-950/60 border border-emerald-700/50 text-emerald-300">
            🛡️ <b>손실 누적 차감 기준:</b> 수수료 <b>200만 원 이하 전액 지급</b>(손실 미차감), 200만 원 초과분 50% 차감 후 지급
          </div>
        </div>
      </div>

      {/* 3. Live Encar Market Comparison Bar (tab_settlement.py L181-L260) */}
      <div className="bg-[#12151e] border border-sky-600/60 rounded-xl p-3.5 shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-sky-400">🎯 보유 재고 실시간 동급 시세 분석 (메인 화면 원클릭 연동)</span>
          </div>
          <span className="text-[11px] text-slate-400">
            💡 보유 차량을 선택하면 메인 콕핏으로 즉시 동급 매물을 스캔하여 이관합니다.
          </span>
        </div>

        <div className="flex flex-col sm:flex-row gap-2 items-center">
          <select
            value={selectedStockCarNum || currentSelectedStock?.carNumber || ''}
            onChange={(e) => setSelectedStockCarNum(e.target.value)}
            className="flex-1 bg-[#0a0b0e] border border-[#2b2f42] rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-sky-500 font-semibold"
          >
            {calculatedStockItems.map((item) => (
              <option key={item.id} value={item.carNumber}>
                {item.carNumber} | {item.carName} (매입 {item.buyPrice}만 / 판매 {item.sellPrice}만 / {item.stockDays}일차)
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => {
              if (currentSelectedStock && onAnalyzeInCockpit) {
                onAnalyzeInCockpit(currentSelectedStock);
              }
            }}
            className="px-4 py-2 bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-white rounded-lg text-xs font-bold transition shadow-md flex items-center gap-1.5 shrink-0"
          >
            <span>🚀 메인 화면에서 동급 시세 분석</span>
          </button>
        </div>
      </div>

      {/* 4. Filter Toolbar (tab_settlement.py L505-L523) */}
      <div className="bg-[#0f1117] border border-[#232733] p-3 rounded-xl flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-200">📝 현재 보유 재고 정산표</span>
          <span className="text-xs text-slate-500">({calculatedStockItems.length}대)</span>
        </div>

        {/* Filter Radio Buttons */}
        <div className="flex flex-wrap items-center gap-1.5 bg-[#181b24] p-1 rounded-lg border border-[#282c3c] text-xs">
          <button
            type="button"
            onClick={() => setFilterMode('all')}
            className={`px-2.5 py-1 rounded transition font-medium ${filterMode === 'all'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
              }`}
          >
            전체 ({stockCount})
          </button>
          <button
            type="button"
            onClick={() => setFilterMode('30plus')}
            className={`px-2.5 py-1 rounded transition font-medium ${filterMode === '30plus'
                ? 'bg-amber-600 text-white shadow-sm'
                : 'text-amber-400 hover:text-amber-300'
              }`}
          >
            ⚠️ 30일+ ({over30Count})
          </button>
          <button
            type="button"
            onClick={() => setFilterMode('60plus')}
            className={`px-2.5 py-1 rounded transition font-medium ${filterMode === '60plus'
                ? 'bg-rose-600 text-white shadow-sm'
                : 'text-rose-400 hover:text-rose-300'
              }`}
          >
            🚨 60일+ ({over60Count})
          </button>
          <button
            type="button"
            onClick={() => setFilterMode('margin_risk')}
            className={`px-2.5 py-1 rounded transition font-medium ${filterMode === 'margin_risk'
                ? 'bg-rose-700 text-white shadow-sm'
                : 'text-rose-400 hover:text-rose-300'
              }`}
          >
            📉 마진주의 ({marginRiskCount})
          </button>
        </div>
      </div>

      {/* 5. Main Inventory Settlement Table (tab_settlement.py L524-L633) */}
      <div className="bg-[#0f1117] border border-[#232733] rounded-xl overflow-hidden">
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
                <th className="py-2.5 px-2.5 text-right whitespace-nowrap">판매가</th>
                <th className="py-2.5 px-2 text-center whitespace-nowrap">외판</th>
                <th className="py-2.5 px-2 text-right whitespace-nowrap">상품화</th>
                <th className="py-2.5 px-2 text-right whitespace-nowrap">헤딜수수료</th>
                <th className="py-2.5 px-2 text-right whitespace-nowrap">제경비</th>
                <th className="py-2.5 px-2 text-right whitespace-nowrap">판매수수료</th>
                <th className="py-2.5 px-2.5 text-right whitespace-nowrap text-sky-400">공헌이익</th>
                <th className="py-2.5 px-2.5 text-right whitespace-nowrap text-amber-400">실수익</th>
                <th className="py-2.5 px-2 text-center whitespace-nowrap">수수료율</th>
                <th className="py-2.5 px-3 text-center whitespace-nowrap">작업 / 판매완료</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1a1d27]">
              {filteredViewItems.map((item) => {
                const isOver30 = item.stockDays >= 30 && item.stockDays < 60;
                const isOver60 = item.stockDays >= 60;
                const isRisk = item.sellPrice > 0 && item.contributionMargin < 100;

                return (
                  <tr
                    key={item.id}
                    className={`hover:bg-[#151824] transition ${isOver60 ? 'bg-rose-950/10' : isRisk ? 'bg-amber-950/10' : ''
                      }`}
                  >
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
                      <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${isOver60
                          ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          : isOver30
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        }`}>
                        {item.stockDays}일
                      </span>
                    </td>
                    <td className="py-2.5 px-2.5 text-right font-medium text-white whitespace-nowrap">
                      {item.buyPrice.toLocaleString()}만
                    </td>
                    <td className="py-2.5 px-2.5 text-right font-bold text-sky-400 whitespace-nowrap">
                      {item.sellPrice > 0 ? `${item.sellPrice.toLocaleString()}만` : '-'}
                    </td>
                    <td className="py-2.5 px-2 text-center text-amber-400 whitespace-nowrap">
                      {item.outerRepairs > 0 ? `${item.outerRepairs}판` : '0판'}
                    </td>
                    <td className="py-2.5 px-2 text-right text-slate-300 whitespace-nowrap">
                      {item.repairCost > 0 ? `${item.repairCost.toLocaleString()}만` : '-'}
                    </td>
                    <td className="py-2.5 px-2 text-right text-slate-300 whitespace-nowrap">
                      {item.heydealerFee > 0 ? `${item.heydealerFee.toLocaleString()}만` : '-'}
                    </td>
                    <td className="py-2.5 px-2 text-right text-slate-400 whitespace-nowrap">
                      {item.baseExpenses}만
                    </td>
                    <td className="py-2.5 px-2 text-right text-slate-400 whitespace-nowrap">
                      {item.salesCommission > 0 ? `${item.salesCommission}만` : '-'}
                    </td>
                    <td className="py-2.5 px-2.5 text-right font-bold whitespace-nowrap">
                      <span className={item.contributionMargin >= 100 ? 'text-sky-400' : item.contributionMargin > 0 ? 'text-emerald-400' : 'text-rose-400'}>
                        {item.sellPrice > 0 ? `${item.contributionMargin > 0 ? '+' : ''}${item.contributionMargin.toLocaleString()}만` : '0만'}
                      </span>
                    </td>
                    <td className="py-2.5 px-2.5 text-right font-bold text-amber-400 whitespace-nowrap">
                      {item.sellPrice > 0 ? `${item.netProfit > 0 ? '+' : ''}${item.netProfit.toLocaleString()}만` : '0만'}
                    </td>
                    <td className="py-2.5 px-2 text-center text-slate-300 whitespace-nowrap font-mono">
                      {Math.round((item.feeRate || autoFeeRate) * 100)}%
                    </td>
                    <td className="py-2.5 px-3 text-center whitespace-nowrap">
                      <div className="flex items-center justify-center gap-1.5">
                        {onAnalyzeInCockpit && (
                          <button
                            type="button"
                            onClick={() => onAnalyzeInCockpit(item)}
                            className="px-2 py-1 rounded bg-[#1e2230] hover:bg-[#282d3e] text-slate-300 border border-slate-700 text-[11px] font-semibold transition"
                            title="동급 시세 분석 콕핏으로 이동"
                          >
                            시세
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => {
                            if (window.confirm(`[${item.carNumber}] 차량의 판매가 완료되었습니까? '판매완료 정산' 탭으로 이동합니다.`)) {
                              onMarkSold?.(item.id, item.sellPrice);
                            }
                          }}
                          className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold transition flex items-center gap-1 shadow-sm shadow-emerald-600/30"
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
