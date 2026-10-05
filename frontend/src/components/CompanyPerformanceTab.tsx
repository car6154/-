import React, { useState, useMemo } from 'react';
import { Search, TrendingUp, Clock, DollarSign, Filter, ArrowUpDown } from 'lucide-react';
import salesDataRaw from '../data/real_autoplus_sold.json';

interface SaleRecord {
  id: string;
  plate: string;
  carName: string;
  subModel: string;
  color?: string;
  mileage: number;
  regDate: string;
  stockDays: number;
  newCarPrice: number;
  buyPrice: number;
  sellPrice: number;
  deprecRate?: number;
  realizedProfit?: number;
}

export interface CompanyPerformanceTabProps {
  onAnalyzeInCockpit?: (record: SaleRecord) => void;
}

export const CompanyPerformanceTab: React.FC<CompanyPerformanceTabProps> = ({
  onAnalyzeInCockpit,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [modelFilter, setModelFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState<'stockDays' | 'margin' | 'sellPrice'>('margin');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const salesData = salesDataRaw as SaleRecord[];

  // Top summary metrics
  const totalCount = salesData.length;
  const avgStockDays = Math.round(
    salesData.reduce((sum, item) => sum + (item.stockDays || 0), 0) / (totalCount || 1)
  );
  const avgMargin = Math.round(
    salesData.reduce((sum, item) => sum + ((item.sellPrice || 0) - (item.buyPrice || 0)), 0) /
      (totalCount || 1)
  );
  const totalVolumeBillion = (
    salesData.reduce((sum, item) => sum + (item.sellPrice || 0), 0) / 10000
  ).toFixed(1);

  // Distinct car names for filter
  const carNames = useMemo(() => {
    const set = new Set<string>();
    salesData.forEach((s) => {
      if (s.carName) set.add(s.carName);
    });
    return Array.from(set).slice(0, 15);
  }, [salesData]);

  // Filtered & sorted data
  const filteredData = useMemo(() => {
    return salesData
      .filter((item) => {
        const matchesSearch =
          !searchTerm ||
          item.plate.includes(searchTerm) ||
          item.carName.toLowerCase().includes(searchTerm.toLowerCase()) ||
          item.subModel.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesModel = modelFilter === 'ALL' || item.carName === modelFilter;
        return matchesSearch && matchesModel;
      })
      .sort((a, b) => {
        let diff = 0;
        if (sortBy === 'stockDays') {
          diff = a.stockDays - b.stockDays;
        } else if (sortBy === 'margin') {
          diff = a.sellPrice - a.buyPrice - (b.sellPrice - b.buyPrice);
        } else if (sortBy === 'sellPrice') {
          diff = a.sellPrice - b.sellPrice;
        }
        return sortOrder === 'desc' ? -diff : diff;
      })
      .slice(0, 100); // display top 100 for fast UI performance
  }, [salesData, searchTerm, modelFilter, sortBy, sortOrder]);

  return (
    <div className="space-y-6">
      {/* Metrics Banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-4 rounded-xl bg-[#0E1015] border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-blue-400" />
            내수 완판 실적 DB
          </div>
          <div className="text-xl sm:text-2xl font-bold text-white">
            {totalCount.toLocaleString()}<span className="text-xs font-normal text-slate-400 ml-1">건 축적</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0E1015] border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-emerald-400" />
            평균 재고 회전일수
          </div>
          <div className="text-xl sm:text-2xl font-bold text-emerald-400">
            {avgStockDays}<span className="text-xs font-normal text-slate-400 ml-1">일 (초고속 회전)</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0E1015] border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <DollarSign className="w-3.5 h-3.5 text-[#cc9166]" />
            대당 평균 실현마진
          </div>
          <div className="text-xl sm:text-2xl font-bold text-[#cc9166]">
            +{avgMargin}<span className="text-xs font-normal text-slate-400 ml-1">만원</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0E1015] border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <DollarSign className="w-3.5 h-3.5 text-purple-400" />
            누적 완판 규모
          </div>
          <div className="text-xl sm:text-2xl font-bold text-purple-400">
            {totalVolumeBillion}<span className="text-xs font-normal text-slate-400 ml-1">억원</span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-[#0E1015] border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="차량번호, 차종 검색 (예: 그랜저, 쏘렌토)..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-700/80 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-[#cc9166]"
            />
          </div>

          <div className="flex items-center gap-1 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={modelFilter}
              onChange={(e) => setModelFilter(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none"
            >
              <option value="ALL">전체 차종</option>
              {carNames.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Sort Controls */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400 flex items-center gap-1">
            <ArrowUpDown className="w-3 h-3" />
            정렬:
          </span>
          <button
            onClick={() => {
              if (sortBy === 'margin') setSortOrder((o) => (o === 'desc' ? 'asc' : 'desc'));
              else {
                setSortBy('margin');
                setSortOrder('desc');
              }
            }}
            className={`px-2.5 py-1 rounded-lg border transition ${
              sortBy === 'margin'
                ? 'bg-[#cc9166]/20 text-[#cc9166] border-[#cc9166]/40 font-semibold'
                : 'bg-slate-900 text-slate-400 border-slate-700'
            }`}
          >
            마진순 {sortBy === 'margin' ? (sortOrder === 'desc' ? '↓' : '↑') : ''}
          </button>
          <button
            onClick={() => {
              if (sortBy === 'stockDays') setSortOrder((o) => (o === 'desc' ? 'asc' : 'desc'));
              else {
                setSortBy('stockDays');
                setSortOrder('asc');
              }
            }}
            className={`px-2.5 py-1 rounded-lg border transition ${
              sortBy === 'stockDays'
                ? 'bg-[#cc9166]/20 text-[#cc9166] border-[#cc9166]/40 font-semibold'
                : 'bg-slate-900 text-slate-400 border-slate-700'
            }`}
          >
            회전일수 {sortBy === 'stockDays' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
          </button>
        </div>
      </div>

      {/* Results Table */}
      <div className="rounded-xl bg-[#0E1015] border border-slate-800 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-300">검색 결과 (상위 {filteredData.length}건 표시)</span>
          <span className="text-slate-400">오토플러스 리본카 내수 판매 확정 데이터</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-4 font-semibold">차량번호 / 모델</th>
                <th className="py-2.5 px-4 font-semibold">세부 등급 / 색상</th>
                <th className="py-2.5 px-4 font-semibold text-right">주행거리</th>
                <th className="py-2.5 px-4 font-semibold text-center">회전일수</th>
                <th className="py-2.5 px-4 font-semibold text-right">매입가</th>
                <th className="py-2.5 px-4 font-semibold text-right">판매가</th>
                <th className="py-2.5 px-4 font-semibold text-right">실현 마진</th>
                <th className="py-2.5 px-4 font-semibold text-center">작업</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {filteredData.map((item) => {
                const margin = item.sellPrice - item.buyPrice;
                return (
                  <tr key={item.id} className="hover:bg-slate-900/50 transition">
                    <td className="py-2.5 px-4">
                      <div className="font-bold text-white">{item.plate}</div>
                      <div className="text-[11px] text-slate-400">{item.carName}</div>
                    </td>
                    <td className="py-2.5 px-4">
                      <div className="text-slate-300">{item.subModel}</div>
                      <div className="text-[10px] text-slate-500">{item.color || '무채색'} · {item.regDate}</div>
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-slate-300">
                      {item.mileage?.toLocaleString()}km
                    </td>
                    <td className="py-2.5 px-4 text-center">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                          item.stockDays <= 20
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : item.stockDays <= 45
                            ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                            : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        }`}
                      >
                        {item.stockDays}일
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-right font-medium text-slate-400">
                      {item.buyPrice?.toLocaleString()}만원
                    </td>
                    <td className="py-2.5 px-4 text-right font-bold text-white">
                      {item.sellPrice?.toLocaleString()}만원
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      <span
                        className={`font-bold ${
                          margin >= 100
                            ? 'text-[#cc9166]'
                            : margin >= 0
                            ? 'text-emerald-400'
                            : 'text-rose-400'
                        }`}
                      >
                        {margin >= 0 ? `+${margin.toLocaleString()}` : margin.toLocaleString()}만원
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-center">
                      {onAnalyzeInCockpit && (
                        <button
                          type="button"
                          onClick={() => onAnalyzeInCockpit(item)}
                          className="px-2.5 py-1 rounded bg-[#1e2029] hover:bg-[#2a2d3b] text-slate-300 border border-slate-700 text-[10px] font-semibold transition cursor-pointer"
                          title="이 차량 제원으로 시세 분석 콕핏 이동"
                        >
                          시세
                        </button>
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
