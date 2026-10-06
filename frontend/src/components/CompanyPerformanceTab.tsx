import React, { useState, useMemo } from 'react';
import { Search, TrendingUp, Clock, DollarSign, Filter, ArrowUpDown } from 'lucide-react';
import salesDataRaw from '../data/real_autoplus_sold.json';

export interface SaleRecord {
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
  const [scanInputCarNo, setScanInputCarNo] = useState('');
  const [selectedScanCarId, setSelectedScanCarId] = useState<string>('');

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

  // Candidates for scanning
  const scanCandidates = useMemo(() => {
    if (!scanInputCarNo) return salesData.slice(0, 30);
    return salesData.filter(c => c.plate.includes(scanInputCarNo)).slice(0, 30);
  }, [salesData, scanInputCarNo]);

  const handleTriggerScan = () => {
    let target = salesData.find(c => c.id === selectedScanCarId);
    if (!target && scanInputCarNo) {
      target = salesData.find(c => c.plate === scanInputCarNo || c.plate.includes(scanInputCarNo));
    }
    if (!target && scanCandidates.length > 0) {
      target = scanCandidates[0];
    }

    if (target && onAnalyzeInCockpit) {
      onAnalyzeInCockpit(target);
    }
  };

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
      .slice(0, 100);
  }, [salesData, searchTerm, modelFilter, sortBy, sortOrder]);

  return (
    <div className="space-y-4">
      {/* 1. Header */}
      <div className="border-b border-[#1f2433] pb-3">
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <span>📋 자사 판매 실적 (판매완료)</span>
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          오토플러스 리본카 {totalCount.toLocaleString()}건 내수 완판 실적 참고 DB 및 동급 시세 역추적
        </p>
      </div>

      {/* 2. Metrics Banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-[#12151e] border border-[#232733] space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-blue-400" />
            내수 완판 실적 DB
          </div>
          <div className="text-lg font-bold text-white">
            {totalCount.toLocaleString()}<span className="text-xs font-normal text-slate-400 ml-1">건 축적</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#12151e] border border-[#232733] space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-emerald-400" />
            평균 재고 회전일수
          </div>
          <div className="text-lg font-bold text-emerald-400">
            {avgStockDays}<span className="text-xs font-normal text-slate-400 ml-1">일 (초고속 회전)</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#12151e] border border-[#232733] space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <DollarSign className="w-3.5 h-3.5 text-amber-400" />
            대당 평균 실현마진
          </div>
          <div className="text-lg font-bold text-amber-400">
            +{avgMargin}<span className="text-xs font-normal text-slate-400 ml-1">만원</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#12151e] border border-[#232733] space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <DollarSign className="w-3.5 h-3.5 text-purple-400" />
            누적 완판 규모
          </div>
          <div className="text-lg font-bold text-purple-400">
            {totalVolumeBillion}<span className="text-xs font-normal text-slate-400 ml-1">억원</span>
          </div>
        </div>
      </div>

      {/* 3. Live Market Scan Bar (tab_ledger.py render_sales_tab L1011-L1063) */}
      <div className="bg-[#12151e] border border-blue-500/50 rounded-xl p-3.5 shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2">
          <span className="text-xs font-bold text-blue-400">
            🔍 차량번호로 판매완료 차량 시세 분석 (메인 콕핏 연동)
          </span>
          <span className="text-[11px] text-slate-400">
            차량번호를 직접 입력(예: 뒷4자리 또는 번호)하거나 목록에서 선택 시 즉시 동급 시세를 스캔합니다.
          </span>
        </div>

        <div className="flex flex-col sm:flex-row gap-2 items-center">
          <input
            type="text"
            placeholder="🚘 차량번호 직접 입력 (예: 123가4567, 4567)..."
            value={scanInputCarNo}
            onChange={(e) => setScanInputCarNo(e.target.value.trim())}
            className="w-full sm:w-60 bg-[#0a0b0e] border border-[#282c3c] rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-bold"
          />

          <select
            value={selectedScanCarId || scanCandidates[0]?.id || ''}
            onChange={(e) => setSelectedScanCarId(e.target.value)}
            className="flex-1 bg-[#0a0b0e] border border-[#282c3c] rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500 font-medium"
          >
            {scanCandidates.map(c => (
              <option key={c.id} value={c.id}>
                {c.plate} | {c.carName} {c.subModel} ({c.regDate} / {c.mileage.toLocaleString()}km / {c.sellPrice}만)
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={handleTriggerScan}
            className="px-4 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-lg text-xs font-bold transition shadow-md flex items-center gap-1.5 shrink-0"
          >
            <span>🚀 동급 시세 분석</span>
          </button>
        </div>
      </div>

      {/* 4. Filter and Search Bar */}
      <div className="p-3 rounded-xl bg-[#0f1117] border border-[#232733] flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="차량번호, 차종 검색 (예: 그랜저, 쏘렌토)..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-[#181b24] border border-[#282c3c] rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex items-center gap-1 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={modelFilter}
              onChange={(e) => setModelFilter(e.target.value)}
              className="bg-[#181b24] border border-[#282c3c] rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none"
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
            className={`px-2.5 py-1 rounded-lg border transition font-medium ${
              sortBy === 'margin'
                ? 'bg-blue-600 text-white border-blue-500'
                : 'bg-[#181b24] text-slate-400 border-[#282c3c]'
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
            className={`px-2.5 py-1 rounded-lg border transition font-medium ${
              sortBy === 'stockDays'
                ? 'bg-blue-600 text-white border-blue-500'
                : 'bg-[#181b24] text-slate-400 border-[#282c3c]'
            }`}
          >
            회전일수 {sortBy === 'stockDays' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
          </button>
        </div>
      </div>

      {/* 5. Results Table */}
      <div className="rounded-xl bg-[#0f1117] border border-[#232733] overflow-hidden">
        <div className="px-4 py-2.5 border-b border-[#232733] flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-300">검색 결과 (상위 {filteredData.length}건 표시)</span>
          <span className="text-slate-400">오토플러스 리본카 내수 판매 확정 데이터</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#181b24] text-slate-400 border-b border-[#282c3c] font-bold">
              <tr>
                <th className="py-2.5 px-3">차량번호 / 모델</th>
                <th className="py-2.5 px-3">세부 등급 / 색상</th>
                <th className="py-2.5 px-3 text-right">주행거리</th>
                <th className="py-2.5 px-3 text-center">회전일수</th>
                <th className="py-2.5 px-3 text-right">매입가</th>
                <th className="py-2.5 px-3 text-right">판매가</th>
                <th className="py-2.5 px-3 text-right">실현 마진</th>
                <th className="py-2.5 px-3 text-center">시세 분석</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1a1d27] text-slate-200">
              {filteredData.map((item) => {
                const margin = item.sellPrice - item.buyPrice;
                return (
                  <tr key={item.id} className="hover:bg-[#151824] transition">
                    <td className="py-2.5 px-3">
                      <div className="font-bold text-white">{item.plate}</div>
                      <div className="text-[11px] text-slate-400">{item.carName}</div>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="text-slate-300">{item.subModel}</div>
                      <div className="text-[10px] text-slate-500">{item.color || '무채색'} · {item.regDate}</div>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-slate-300">
                      {item.mileage?.toLocaleString()}km
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                          item.stockDays <= 20
                            ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                            : item.stockDays <= 45
                            ? 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                            : 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                        }`}
                      >
                        {item.stockDays}일
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-medium text-slate-400">
                      {item.buyPrice?.toLocaleString()}만원
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-white">
                      {item.sellPrice?.toLocaleString()}만원
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <span
                        className={`font-bold ${
                          margin >= 100
                            ? 'text-sky-400'
                            : margin >= 0
                            ? 'text-emerald-400'
                            : 'text-rose-400'
                        }`}
                      >
                        {margin >= 0 ? `+${margin.toLocaleString()}` : margin.toLocaleString()}만원
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {onAnalyzeInCockpit && (
                        <button
                          type="button"
                          onClick={() => onAnalyzeInCockpit(item)}
                          className="px-2 py-1 rounded bg-[#1e2230] hover:bg-[#282d3e] text-slate-300 border border-slate-700 text-[10px] font-semibold transition"
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
