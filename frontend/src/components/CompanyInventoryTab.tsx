import React, { useState, useMemo } from 'react';
import { Warehouse, Search, AlertCircle, Clock, ExternalLink, Filter, MapPin, Sparkles } from 'lucide-react';
import inventoryDataRaw from '../data/real_autoplus_inventory.json';

export interface InventoryRecord {
  id: string;
  plate: string;
  carName: string;
  subModel: string;
  color?: string;
  mileage: number;
  regDate: string;
  stockDays: number;
  buyPrice: number;
  sellPrice: number;
  newCarPrice: number;
  expectedProfit: number;
  status: string;
  branch: string;
  manager: string;
  encarUrl?: string;
}

interface CompanyInventoryTabProps {
  onAnalyzeInCockpit?: (car: {
    carNumber: string;
    manufacturer?: string;
    carName: string;
    detailModel: string;
    year: number;
    mileage: number;
    sellPrice?: number;
    buyPrice?: number;
  }) => void;
}

export const CompanyInventoryTab: React.FC<CompanyInventoryTabProps> = ({ onAnalyzeInCockpit }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [branchFilter, setBranchFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [stockDaysFilter, setStockDaysFilter] = useState<'ALL' | 'NORMAL' | 'WARNING' | 'CRITICAL'>('ALL');
  const [scanInputCarNo, setScanInputCarNo] = useState('');

  const inventoryCars = inventoryDataRaw as InventoryRecord[];

  // Branches list
  const branches = useMemo(() => {
    const set = new Set<string>();
    inventoryCars.forEach((c) => {
      if (c.branch) set.add(c.branch);
    });
    return Array.from(set).sort();
  }, [inventoryCars]);

  // Aggregate stats
  const totalCount = inventoryCars.length;
  const normalCount = inventoryCars.filter((c) => c.stockDays < 60).length;
  const warningCount = inventoryCars.filter((c) => c.stockDays >= 60 && c.stockDays < 90).length;
  const criticalCount = inventoryCars.filter((c) => c.stockDays >= 90).length;
  const totalBuyBillion = (
    inventoryCars.reduce((sum, c) => sum + (c.buyPrice || 0), 0) / 10000
  ).toFixed(1);

  // Filtered cars
  const filtered = useMemo(() => {
    return inventoryCars.filter((c) => {
      const matchesSearch =
        !searchTerm ||
        c.plate.includes(searchTerm) ||
        c.carName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.subModel.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.manager.includes(searchTerm);

      const matchesBranch = branchFilter === 'ALL' || c.branch === branchFilter;
      const matchesStatus = statusFilter === 'ALL' || c.status === statusFilter;

      let matchesStockDays = true;
      if (stockDaysFilter === 'NORMAL') matchesStockDays = c.stockDays < 60;
      else if (stockDaysFilter === 'WARNING') matchesStockDays = c.stockDays >= 60 && c.stockDays < 90;
      else if (stockDaysFilter === 'CRITICAL') matchesStockDays = c.stockDays >= 90;

      return matchesSearch && matchesBranch && matchesStatus && matchesStockDays;
    });
  }, [inventoryCars, searchTerm, branchFilter, statusFilter, stockDaysFilter]);

  // Candidates for scanning
  const scanCandidates = useMemo(() => {
    if (!scanInputCarNo) return inventoryCars.slice(0, 30);
    return inventoryCars.filter(c => c.plate.includes(scanInputCarNo)).slice(0, 30);
  }, [inventoryCars, scanInputCarNo]);

  const [selectedScanCarId, setSelectedScanCarId] = useState<string>('');

  const handleTriggerScan = () => {
    let target = inventoryCars.find(c => c.id === selectedScanCarId);
    if (!target && scanInputCarNo) {
      target = inventoryCars.find(c => c.plate === scanInputCarNo || c.plate.includes(scanInputCarNo));
    }
    if (!target && scanCandidates.length > 0) {
      target = scanCandidates[0];
    }

    if (target && onAnalyzeInCockpit) {
      let yr = 20;
      const yrMatch = (target.regDate || '').match(/\d{2,4}/);
      if (yrMatch) {
        let parsed = parseInt(yrMatch[0], 10);
        if (parsed > 2000) parsed -= 2000;
        yr = parsed;
      }

      onAnalyzeInCockpit({
        carNumber: target.plate,
        carName: target.carName,
        detailModel: target.subModel,
        year: yr,
        mileage: target.mileage,
        sellPrice: target.sellPrice,
        buyPrice: target.buyPrice,
      });
    }
  };

  return (
    <div className="space-y-4">
      {/* 1. Header */}
      <div className="border-b border-[#1f2433] pb-3">
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <span>📦 자사 보유 재고 (판매중)</span>
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          실시간 자사 보유 매물 {totalCount.toLocaleString()}대의 경과일수, 매입원가, 판매가 및 시세 분석 연동
        </p>
      </div>

      {/* 2. Top Banner Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-xl bg-[#12151e] border border-[#232733] space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Warehouse className="w-3.5 h-3.5 text-blue-400" />
            현재 보유 재고
          </div>
          <div className="text-lg font-bold text-white">
            {totalCount.toLocaleString()}<span className="text-xs font-normal text-slate-400 ml-1">대 보유</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#12151e] border border-[#232733] space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Warehouse className="w-3.5 h-3.5 text-purple-400" />
            총 재고 매입규모
          </div>
          <div className="text-lg font-bold text-purple-400">
            {totalBuyBillion}<span className="text-xs font-normal text-slate-400 ml-1">억원</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#12151e] border border-[#232733] space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-emerald-400" />
            정상 회전 (&lt;60일)
          </div>
          <div className="text-lg font-bold text-emerald-400">
            {normalCount.toLocaleString()}<span className="text-xs font-normal text-slate-400 ml-1">대</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#12151e] border border-[#232733] space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
            주의 재고 (60~89일)
          </div>
          <div className="text-lg font-bold text-amber-400">
            {warningCount.toLocaleString()}<span className="text-xs font-normal text-slate-400 ml-1">대</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-[#12151e] border border-[#232733] space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
            90일 장기재고
          </div>
          <div className="text-lg font-bold text-rose-400">
            {criticalCount.toLocaleString()}<span className="text-xs font-normal text-slate-400 ml-1">대 (긴급처분)</span>
          </div>
        </div>
      </div>

      {/* 3. Live Market Scan Bar (tab_ledger.py render_inventory_tab L1086-L1130) */}
      <div className="bg-[#12151e] border border-emerald-500/50 rounded-xl p-3.5 shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2">
          <span className="text-xs font-bold text-emerald-400">
            🚘 차량번호로 보유 재고 시세 분석 (메인 콕핏 연동)
          </span>
          <span className="text-[11px] text-slate-400">
            차량번호를 직접 입력(예: 뒷4자리 또는 번호)하거나 선택 시 메인 화면으로 이동하여 즉시 동급 시세를 스캔합니다.
          </span>
        </div>

        <div className="flex flex-col sm:flex-row gap-2 items-center">
          <input
            type="text"
            placeholder="🚘 차량번호 직접 입력 (예: 140너9372, 9372)..."
            value={scanInputCarNo}
            onChange={(e) => setScanInputCarNo(e.target.value.trim())}
            className="w-full sm:w-60 bg-[#0a0b0e] border border-[#282c3c] rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-bold"
          />

          <select
            value={selectedScanCarId || scanCandidates[0]?.id || ''}
            onChange={(e) => setSelectedScanCarId(e.target.value)}
            className="flex-1 bg-[#0a0b0e] border border-[#282c3c] rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-emerald-500 font-medium"
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
            className="px-4 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg text-xs font-bold transition shadow-md flex items-center gap-1.5 shrink-0"
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
              placeholder="차량번호, 차종, 담당자 검색..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-[#181b24] border border-[#282c3c] rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex items-center gap-1 text-xs">
            <MapPin className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={branchFilter}
              onChange={(e) => setBranchFilter(e.target.value)}
              className="bg-[#181b24] border border-[#282c3c] rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none"
            >
              <option value="ALL">전체 지점</option>
              {branches.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-[#181b24] border border-[#282c3c] rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none"
            >
              <option value="ALL">전체 상태</option>
              <option value="판매중">판매중</option>
              <option value="계약중">계약중</option>
            </select>
          </div>
        </div>

        {/* Stock Days Filter Tabs */}
        <div className="flex items-center gap-1.5 text-xs">
          <button
            onClick={() => setStockDaysFilter('ALL')}
            className={`px-2.5 py-1 rounded-lg border transition font-medium ${
              stockDaysFilter === 'ALL'
                ? 'bg-blue-600 text-white border-blue-500'
                : 'bg-[#181b24] text-slate-400 border-[#282c3c]'
            }`}
          >
            전체 ({totalCount})
          </button>
          <button
            onClick={() => setStockDaysFilter('NORMAL')}
            className={`px-2.5 py-1 rounded-lg border transition font-medium ${
              stockDaysFilter === 'NORMAL'
                ? 'bg-emerald-600 text-white border-emerald-500'
                : 'bg-[#181b24] text-emerald-400 border-[#282c3c]'
            }`}
          >
            &lt;60일
          </button>
          <button
            onClick={() => setStockDaysFilter('WARNING')}
            className={`px-2.5 py-1 rounded-lg border transition font-medium ${
              stockDaysFilter === 'WARNING'
                ? 'bg-amber-600 text-white border-amber-500'
                : 'bg-[#181b24] text-amber-400 border-[#282c3c]'
            }`}
          >
            60~89일
          </button>
          <button
            onClick={() => setStockDaysFilter('CRITICAL')}
            className={`px-2.5 py-1 rounded-lg border transition font-medium ${
              stockDaysFilter === 'CRITICAL'
                ? 'bg-rose-600 text-white border-rose-500'
                : 'bg-[#181b24] text-rose-400 border-[#282c3c]'
            }`}
          >
            90일+
          </button>
        </div>
      </div>

      {/* 5. Inventory Table */}
      <div className="rounded-xl bg-[#0f1117] border border-[#232733] overflow-hidden">
        <div className="px-4 py-2.5 border-b border-[#232733] flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-300">
            보유 재고 목록 (총 {filtered.length.toLocaleString()}건 중 상위 100건 표시)
          </span>
          <span className="text-slate-400">실시간 보유 현황 및 경과일수</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#181b24] text-slate-400 border-b border-[#282c3c] font-bold">
              <tr>
                <th className="py-2.5 px-3">차량번호 / 모델</th>
                <th className="py-2.5 px-3">세부 등급 / 색상</th>
                <th className="py-2.5 px-3 text-right">주행거리</th>
                <th className="py-2.5 px-3 text-center">경과일수</th>
                <th className="py-2.5 px-3 text-right">매입원가</th>
                <th className="py-2.5 px-3 text-right">지점판매가</th>
                <th className="py-2.5 px-3 text-right">예상 마진</th>
                <th className="py-2.5 px-3">지점 / 담당</th>
                <th className="py-2.5 px-3 text-center">시세 분석</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1a1d27] text-slate-200">
              {filtered.slice(0, 100).map((car) => {
                const isCritical = car.stockDays >= 90;
                const isWarning = car.stockDays >= 60 && car.stockDays < 90;
                return (
                  <tr key={car.id} className="hover:bg-[#151824] transition">
                    <td className="py-2.5 px-3">
                      <div className="font-bold text-white">{car.plate}</div>
                      <div className="text-[11px] text-slate-400">{car.carName}</div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-300">
                      <div>{car.subModel}</div>
                      <div className="text-[10px] text-slate-500">{car.color || '무채색'} · {car.regDate}</div>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-slate-300">
                      {car.mileage?.toLocaleString()}km
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                          isCritical
                            ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
                            : isWarning
                            ? 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                            : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                        }`}
                      >
                        {car.stockDays}일
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-medium text-slate-400">
                      {car.buyPrice.toLocaleString()}만원
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-white">
                      {car.sellPrice.toLocaleString()}만원
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <span
                        className={`font-bold ${
                          car.expectedProfit >= 100
                            ? 'text-sky-400'
                            : car.expectedProfit >= 0
                            ? 'text-emerald-400'
                            : 'text-rose-400'
                        }`}
                      >
                        {car.expectedProfit >= 0 ? `+${car.expectedProfit.toLocaleString()}` : car.expectedProfit.toLocaleString()}만
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-300">
                      <div className="text-[11px]">{car.branch || '-'}</div>
                      <div className="text-[10px] text-slate-500">{car.manager || '-'}</div>
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        {onAnalyzeInCockpit && (
                          <button
                            type="button"
                            onClick={() => {
                              let yr = 20;
                              const yrMatch = (car.regDate || '').match(/\d{2,4}/);
                              if (yrMatch) {
                                let parsed = parseInt(yrMatch[0], 10);
                                if (parsed > 2000) parsed -= 2000;
                                yr = parsed;
                              }
                              onAnalyzeInCockpit({
                                carNumber: car.plate,
                                carName: car.carName,
                                detailModel: car.subModel,
                                year: yr,
                                mileage: car.mileage,
                                sellPrice: car.sellPrice,
                                buyPrice: car.buyPrice,
                              });
                            }}
                            className="px-2 py-1 rounded bg-[#1e2230] hover:bg-[#282d3e] text-slate-300 border border-slate-700 text-[10px] font-semibold transition"
                            title="동급 시세 분석"
                          >
                            시세
                          </button>
                        )}
                        {car.encarUrl && (
                          <a
                            href={car.encarUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1 text-blue-400 hover:text-blue-300"
                            title="엔카 링크"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
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
