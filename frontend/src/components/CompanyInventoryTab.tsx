import React, { useState, useMemo } from 'react';
import { Warehouse, Search, AlertCircle, Clock, ExternalLink, Filter, MapPin } from 'lucide-react';
import inventoryDataRaw from '../data/real_autoplus_inventory.json';

interface InventoryRecord {
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

export const CompanyInventoryTab: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [branchFilter, setBranchFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [stockDaysFilter, setStockDaysFilter] = useState<'ALL' | 'NORMAL' | 'WARNING' | 'CRITICAL'>('ALL');

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

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 sm:gap-4">
        <div className="p-4 rounded-xl bg-[#0E1015] border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Warehouse className="w-3.5 h-3.5 text-blue-400" />
            현재 보유 재고
          </div>
          <div className="text-xl sm:text-2xl font-bold text-white">
            {totalCount.toLocaleString()}<span className="text-xs font-normal text-slate-400 ml-1">대 보유</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0E1015] border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Warehouse className="w-3.5 h-3.5 text-purple-400" />
            총 재고 매입규모
          </div>
          <div className="text-xl sm:text-2xl font-bold text-purple-400">
            {totalBuyBillion}<span className="text-xs font-normal text-slate-400 ml-1">억원</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0E1015] border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-emerald-400" />
            정상 회전 (&lt;60일)
          </div>
          <div className="text-xl sm:text-2xl font-bold text-emerald-400">
            {normalCount.toLocaleString()}<span className="text-xs font-normal text-slate-400 ml-1">대</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0E1015] border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
            주의 재고 (60~89일)
          </div>
          <div className="text-xl sm:text-2xl font-bold text-amber-400">
            {warningCount.toLocaleString()}<span className="text-xs font-normal text-slate-400 ml-1">대</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0E1015] border border-slate-800 space-y-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
            90일 장기재고
          </div>
          <div className="text-xl sm:text-2xl font-bold text-rose-400">
            {criticalCount.toLocaleString()}<span className="text-xs font-normal text-slate-400 ml-1">대 (긴급처분)</span>
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
              placeholder="차량번호, 차종, 담당자 검색 (예: 140너9372)..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-700/80 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-[#cc9166]"
            />
          </div>

          <div className="flex items-center gap-1 text-xs">
            <MapPin className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={branchFilter}
              onChange={(e) => setBranchFilter(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none"
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
              className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none"
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
            className={`px-2.5 py-1 rounded-lg border transition ${
              stockDaysFilter === 'ALL'
                ? 'bg-[#cc9166]/20 text-[#cc9166] border-[#cc9166]/40 font-semibold'
                : 'bg-slate-900 text-slate-400 border-slate-700'
            }`}
          >
            전체 ({totalCount})
          </button>
          <button
            onClick={() => setStockDaysFilter('NORMAL')}
            className={`px-2.5 py-1 rounded-lg border transition ${
              stockDaysFilter === 'NORMAL'
                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40 font-semibold'
                : 'bg-slate-900 text-slate-400 border-slate-700'
            }`}
          >
            &lt;60일
          </button>
          <button
            onClick={() => setStockDaysFilter('WARNING')}
            className={`px-2.5 py-1 rounded-lg border transition ${
              stockDaysFilter === 'WARNING'
                ? 'bg-amber-500/20 text-amber-400 border-amber-500/40 font-semibold'
                : 'bg-slate-900 text-slate-400 border-slate-700'
            }`}
          >
            60~89일
          </button>
          <button
            onClick={() => setStockDaysFilter('CRITICAL')}
            className={`px-2.5 py-1 rounded-lg border transition ${
              stockDaysFilter === 'CRITICAL'
                ? 'bg-rose-500/20 text-rose-400 border-rose-500/40 font-semibold'
                : 'bg-slate-900 text-slate-400 border-slate-700'
            }`}
          >
            90일+
          </button>
        </div>
      </div>

      {/* Grid of Real Inventory Cards */}
      <div className="rounded-xl bg-[#0E1015] border border-slate-800 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-300">
            보유 재고 목록 (총 {filtered.length.toLocaleString()}건 중 상위 100건 표시)
          </span>
          <span className="text-slate-400">실시간 보유 현황 및 경과일수</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-4 font-semibold">차량번호 / 모델</th>
                <th className="py-2.5 px-4 font-semibold">세부 등급 / 색상</th>
                <th className="py-2.5 px-4 font-semibold text-right">주행거리</th>
                <th className="py-2.5 px-4 font-semibold text-center">경과일수</th>
                <th className="py-2.5 px-4 font-semibold text-right">매입원가</th>
                <th className="py-2.5 px-4 font-semibold text-right">지점판매가</th>
                <th className="py-2.5 px-4 font-semibold text-right">예상 마진</th>
                <th className="py-2.5 px-4 font-semibold">지점 / 담당</th>
                <th className="py-2.5 px-4 font-semibold text-center">엔카</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {filtered.slice(0, 100).map((car) => {
                const isCritical = car.stockDays >= 90;
                const isWarning = car.stockDays >= 60 && car.stockDays < 90;
                return (
                  <tr key={car.id} className="hover:bg-slate-900/50 transition">
                    <td className="py-3 px-4">
                      <div className="font-bold text-white">{car.plate}</div>
                      <div className="text-[11px] text-slate-400">{car.carName}</div>
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      <div>{car.subModel}</div>
                      <div className="text-[10px] text-slate-500">{car.color || '무채색'} · {car.regDate}</div>
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-slate-300">
                      {car.mileage?.toLocaleString()}km
                    </td>
                    <td className="py-3 px-4 text-center">
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
                    <td className="py-3 px-4 text-right font-medium text-slate-400">
                      {car.buyPrice.toLocaleString()}만원
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-white">
                      {car.sellPrice.toLocaleString()}만원
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span
                        className={`font-bold ${
                          car.expectedProfit >= 100
                            ? 'text-[#cc9166]'
                            : car.expectedProfit >= 0
                            ? 'text-emerald-400'
                            : 'text-rose-400'
                        }`}
                      >
                        {car.expectedProfit >= 0 ? `+${car.expectedProfit.toLocaleString()}` : car.expectedProfit.toLocaleString()}만원
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      <div className="text-[11px]">{car.branch || '-'}</div>
                      <div className="text-[10px] text-slate-500">{car.manager || '-'}</div>
                    </td>
                    <td className="py-3 px-4 text-center">
                      {car.encarUrl ? (
                        <a
                          href={car.encarUrl}
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
