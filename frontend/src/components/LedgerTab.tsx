import React, { useState, useMemo } from 'react';
import { CarLedgerItem } from '@/types';
import { 
  FileSpreadsheet,
  Search,
  CheckCircle2,
  Clock,
  Car,
  Trash2,
  RotateCcw,
  Sparkles,
  ExternalLink,
  ChevronRight
} from 'lucide-react';

interface LedgerTabProps {
  cars: CarLedgerItem[];
  searchQuery: string;
  onSelectCar: (car: CarLedgerItem) => void;
  onUpdateStatus: (id: string, newStatus: string) => void;
  onConfirmPurchase?: (car: CarLedgerItem, actualBuyPrice: number) => void;
  onAnalyzeInCockpit?: (car: CarLedgerItem) => void;
  onDeleteCar?: (carNumber: string) => void;
  onRestoreBackup?: () => void;
}

export const LedgerTab: React.FC<LedgerTabProps> = ({
  cars,
  searchQuery: externalSearchQuery,
  onSelectCar,
  onUpdateStatus,
  onConfirmPurchase,
  onAnalyzeInCockpit,
  onDeleteCar,
  onRestoreBackup,
}) => {
  // tab_ledger.py states
  const [internalSearch, setInternalSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'전체' | '진행중 (미확정)' | '매입완료'>('전체');
  const [pageSizeSel, setPageSizeSel] = useState<string>('전체 보기');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [delTargetCar, setDelTargetCar] = useState<string>('');

  // Top selection & confirmation form states
  const [selectedCarNum, setSelectedCarNum] = useState<string>(cars[0]?.carNumber || '');
  
  // If selected car isn't in list, reset to first
  const currentSelectedCar = useMemo(() => {
    return cars.find(c => c.carNumber === selectedCarNum) || cars[0];
  }, [cars, selectedCarNum]);

  const [actualBuyPrice, setActualBuyPrice] = useState<number>(currentSelectedCar?.buyPrice || 0);

  // Sync actual buy price when selection changes
  React.useEffect(() => {
    if (currentSelectedCar) {
      setActualBuyPrice(currentSelectedCar.buyPrice || 0);
    }
  }, [currentSelectedCar]);

  // Overall KPI statistics (tab_ledger.py L349-L379)
  const totalLedgerCount = cars.length;
  const completedCount = useMemo(() => {
    return cars.filter(c => c.status === '매입완료').length;
  }, [cars]);
  const pendingCount = totalLedgerCount - completedCount;

  // Filtered list (tab_ledger.py L390-L406)
  const filteredCars = useMemo(() => {
    const q = (externalSearchQuery || internalSearch).toLowerCase().trim();
    return cars.filter((car) => {
      // 1. Search Query
      if (q) {
        const match =
          car.carNumber.toLowerCase().includes(q) ||
          car.carName.toLowerCase().includes(q) ||
          car.detailModel.toLowerCase().includes(q) ||
          car.manufacturer.toLowerCase().includes(q) ||
          (car.memo && car.memo.toLowerCase().includes(q)) ||
          (car.options && car.options.toLowerCase().includes(q));
        if (!match) return false;
      }

      // 2. Status Filter
      if (statusFilter === '진행중 (미확정)') {
        if (car.status === '매입완료') return false;
      } else if (statusFilter === '매입완료') {
        if (car.status !== '매입완료') return false;
      }

      return true;
    });
  }, [cars, externalSearchQuery, internalSearch, statusFilter]);

  // Pagination (tab_ledger.py L409-L422)
  const pageSize = useMemo(() => {
    if (pageSizeSel === '전체 보기') return Math.max(1, filteredCars.length);
    const num = parseInt(pageSizeSel.replace(/[^\d]/g, ''), 10);
    return isNaN(num) ? 50 : num;
  }, [pageSizeSel, filteredCars.length]);

  const totalPages = Math.max(1, Math.ceil(filteredCars.length / pageSize));
  
  const pagedCars = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredCars.slice(start, start + pageSize);
  }, [filteredCars, currentPage, pageSize]);

  // Options parsing for badges (tab_ledger.py L314-L334)
  const currentOptionsList = useMemo(() => {
    if (!currentSelectedCar?.options) return [];
    return currentSelectedCar.options
      .split(/[,|\n/]+/)
      .map(o => o.trim())
      .filter(o => o.length > 0 && o !== 'nan');
  }, [currentSelectedCar]);

  // CSV Export (tab_ledger.py L535-L543)
  const handleExportCSV = () => {
    const headers = [
      '등록일', '차량번호', '제조사', '차량명', '세부모델', '연식', '주행거리', '옵션',
      '외판수리', '매입가', '판매가', '외판수리비', '헤딜수수료', '특이사항', '상태'
    ];

    const rows = filteredCars.map(c => [
      c.regDate || '',
      c.carNumber || '',
      c.manufacturer || '',
      c.carName || '',
      c.detailModel || '',
      c.year || '',
      `"${(c.mileage || '').replace(/"/g, '""')}"`,
      `"${(c.options || '').replace(/"/g, '""')}"`,
      c.outerRepairs ?? 0,
      c.buyPrice ?? 0,
      c.sellPrice ?? 0,
      c.repairCost ?? 0,
      c.heydealerFee ?? 0,
      `"${(c.memo || '').replace(/"/g, '""')}"`,
      c.status || '보유중'
    ].join(','));

    const csvContent = '\uFEFF' + [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const now = new Date();
    const ymd = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`;
    link.setAttribute('download', `my_car_ledger_${ymd}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-4">
      {/* 1. Header & Title Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#1f2433] pb-3">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <span>📋 내 실전 장부 리스트</span>
            <span className="text-[11px] font-normal text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
              동기화 완료
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            💡 낙찰/매입된 차량의 [🚀 매입 확정]을 누르면 `💰 실전 재고 및 정산 관리` 탭으로 이동하여 실제 판매 및 내 실수익을 정산합니다.
          </p>
        </div>
      </div>

      {/* 2. Top Purchase Confirmation Form (tab_ledger.py L59-L162) */}
      <div className="bg-[#12151e] border border-[#232733] p-4 rounded-xl shadow-lg">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 items-end">
          <div>
            <label className="text-xs font-semibold text-sky-400 block mb-1">
              📦 차량번호 선택:
            </label>
            <select
              value={selectedCarNum}
              onChange={(e) => setSelectedCarNum(e.target.value)}
              className="w-full bg-[#0a0b0e] border border-[#2b2f42] rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-blue-500 font-bold"
            >
              {cars.map((c) => (
                <option key={c.id} value={c.carNumber}>
                  {c.carNumber} | {c.carName} {c.detailModel} ({c.year}년 / {c.buyPrice}만)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">
              실제 낙찰/매입가 (만원):
            </label>
            <input
              type="number"
              value={actualBuyPrice}
              onChange={(e) => setActualBuyPrice(Number(e.target.value))}
              step={10}
              min={0}
              className="w-full bg-[#0a0b0e] border border-[#2b2f42] rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-blue-500 font-bold text-amber-400"
            />
          </div>

          <div>
            <button
              type="button"
              onClick={() => {
                if (currentSelectedCar && onConfirmPurchase) {
                  onConfirmPurchase(currentSelectedCar, actualBuyPrice);
                }
              }}
              className="w-full py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-lg text-xs font-bold transition shadow-md shadow-blue-500/20 cursor-pointer flex items-center justify-center gap-1.5"
            >
              <span>🚀 매입 확정</span>
            </button>
          </div>

          <div>
            <button
              type="button"
              onClick={() => {
                if (currentSelectedCar && onAnalyzeInCockpit) {
                  onAnalyzeInCockpit(currentSelectedCar);
                }
              }}
              className="w-full py-2 bg-[#1c202d] hover:bg-[#252a3b] text-slate-200 border border-slate-700 rounded-lg text-xs font-bold transition cursor-pointer flex items-center justify-center gap-1.5"
              title="메인 시세 분석 화면으로 이동하여 이 차량의 동급 매물을 자동 스캔합니다."
            >
              <span>🔍 동급 시세 분석</span>
            </button>
          </div>
        </div>

        {/* Selected Car Options Badge Strip (tab_ledger.py L314-L334) */}
        <div className="mt-3 pt-2.5 border-t border-[#1e2230] flex items-center gap-2 overflow-x-auto text-xs">
          <span className="font-bold text-sky-400 shrink-0 text-[11px]">🏷️ 장착 옵션:</span>
          <div className="flex flex-wrap items-center gap-1.5 py-0.5">
            {currentOptionsList.length > 0 ? (
              currentOptionsList.map((opt, i) => (
                <span
                  key={i}
                  className="bg-sky-950/60 border border-sky-600/40 text-sky-300 px-2 py-0.5 rounded text-[11px] font-semibold flex items-center gap-1"
                >
                  🏷️ {opt}
                </span>
              ))
            ) : (
              <span className="text-slate-500 italic text-[11px]">등록된 옵션 없음</span>
            )}
          </div>
        </div>
      </div>

      {/* 3. Core Status KPI Dashboard (tab_ledger.py L355-L379) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="bg-[#12151e] border border-[#232733] rounded-xl p-3.5 flex items-center gap-3.5 shadow-sm">
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-lg">
            📋
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">총 등록 장부</div>
            <div className="text-lg font-bold text-white mt-0.5">{totalLedgerCount.toLocaleString()} 대</div>
          </div>
        </div>

        <div className="bg-[#12151e] border border-[#232733] rounded-xl p-3.5 flex items-center gap-3.5 shadow-sm">
          <div className="w-10 h-10 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-lg">
            ⏳
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">진행 중 (미확정)</div>
            <div className="text-lg font-bold text-sky-400 mt-0.5">{pendingCount.toLocaleString()} 대</div>
          </div>
        </div>

        <div className="bg-[#12151e] border border-[#232733] rounded-xl p-3.5 flex items-center gap-3.5 shadow-sm">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-lg">
            ✅
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">매입 확정 완료</div>
            <div className="text-lg font-bold text-emerald-400 mt-0.5">{completedCount.toLocaleString()} 대</div>
          </div>
        </div>
      </div>

      {/* 4. Real-time Search & Filter Toolbar (tab_ledger.py L381-L424) */}
      <div className="bg-[#0f1117] border border-[#232733] p-3 rounded-xl flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5 flex-1 min-w-[280px]">
          {/* Search Input */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={internalSearch}
              onChange={(e) => {
                setInternalSearch(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="🔍 실시간 검색 (차량번호 / 차종 / 특이사항)..."
              className="w-full bg-[#181b24] border border-[#282c3c] rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as any);
              setCurrentPage(1);
            }}
            className="bg-[#181b24] border border-[#282c3c] rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
          >
            <option value="전체">상태: 전체</option>
            <option value="진행중 (미확정)">진행중 (미확정)</option>
            <option value="매입완료">매입완료</option>
          </select>

          {/* Page Size Selector */}
          <select
            value={pageSizeSel}
            onChange={(e) => {
              setPageSizeSel(e.target.value);
              setCurrentPage(1);
            }}
            className="bg-[#181b24] border border-[#282c3c] rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
          >
            <option value="전체 보기">전체 보기</option>
            <option value="50개씩 보기">50개씩 보기</option>
            <option value="30개씩 보기">30개씩 보기</option>
            <option value="100개씩 보기">100개씩 보기</option>
          </select>
        </div>

        {/* Counter and CSV Download */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">
            검색 결과: <strong className="text-white font-bold">{filteredCars.length}</strong>대
          </span>
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#181b24] hover:bg-[#222634] border border-[#282c3c] text-white text-xs font-semibold transition"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            <span>CSV 다운로드</span>
          </button>
        </div>
      </div>

      {/* 5. Responsive Ledger Table (tab_ledger.py L426-L531) */}
      <div className="bg-[#0f1117] border border-[#232733] rounded-xl overflow-hidden">
        {/* Header */}
        <div className="hidden md:flex items-center bg-[#181b24] px-3 py-2.5 border-b border-[#282c3c] text-[11px] font-bold text-slate-400">
          <div className="w-20">📅 등록일</div>
          <div className="w-28">🚘 차량번호</div>
          <div className="w-20">🏭 제조사</div>
          <div className="flex-1 min-w-[120px]">🚗 차량명</div>
          <div className="w-32">🏷️ 세부모델</div>
          <div className="w-14 text-center">연식</div>
          <div className="w-24 text-right">주행거리</div>
          <div className="w-16 text-center">외판</div>
          <div className="w-24 text-right">매입가</div>
          <div className="w-24 text-right">판매가</div>
          <div className="w-20 text-center">상태</div>
          <div className="w-24 text-center">선택/관리</div>
        </div>

        {/* Rows */}
        <div className="divide-y divide-[#1a1d27]">
          {pagedCars.map((car) => {
            const isSelected = car.carNumber === currentSelectedCar?.carNumber;
            const extText = car.outerRepairs > 0 ? `${car.outerRepairs}판` : '0판';
            const buyPriceText = car.buyPrice > 0 ? `${car.buyPrice.toLocaleString()}만` : '-';
            const sellPriceText = car.sellPrice > 0 ? `${car.sellPrice.toLocaleString()}만` : '-';
            const isCompleted = car.status === '매입완료';

            return (
              <div
                key={car.id}
                onClick={() => {
                  setSelectedCarNum(car.carNumber);
                  onSelectCar(car);
                }}
                className={`p-3 md:py-2.5 md:px-3 flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs transition cursor-pointer ${
                  isSelected
                    ? 'bg-[#1d233a] border-l-4 border-l-blue-500'
                    : 'bg-[#12151e] hover:bg-[#1a1e2b]'
                }`}
              >
                {/* Desktop layout */}
                <div className="hidden md:flex items-center flex-1 gap-2">
                  <div className="w-20 text-slate-400 text-[11px] whitespace-nowrap">{car.regDate}</div>
                  <div className={`w-28 font-bold whitespace-nowrap ${isSelected ? 'text-blue-400' : 'text-white'}`}>
                    {car.carNumber}
                  </div>
                  <div className="w-20 text-slate-300 truncate">{car.manufacturer}</div>
                  <div className="flex-1 min-w-[120px] font-semibold text-slate-100 truncate">{car.carName}</div>
                  <div className="w-32 text-slate-400 text-[11px] truncate">{car.detailModel}</div>
                  <div className="w-14 text-center text-slate-400">{car.year}년</div>
                  <div className="w-24 text-right font-medium text-slate-200">{car.mileage}</div>
                  <div className="w-16 text-center text-amber-400 font-semibold">{extText}</div>
                  <div className="w-24 text-right font-bold text-emerald-400">{buyPriceText}</div>
                  <div className="w-24 text-right font-bold text-sky-400">{sellPriceText}</div>
                  <div className="w-20 text-center">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                        isCompleted
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : 'bg-slate-800 text-slate-300 border border-slate-700'
                      }`}
                    >
                      {car.status || '보유중'}
                    </span>
                  </div>
                </div>

                {/* Mobile Card Layout */}
                <div className="flex md:hidden flex-col gap-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-white">{car.carNumber}</span>
                      <span className="text-[11px] text-slate-400">{car.manufacturer} {car.carName}</span>
                    </div>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                        isCompleted
                          ? 'bg-emerald-950 text-emerald-400'
                          : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {car.status || '보유중'}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-slate-400">
                    <span>{car.year}년</span>
                    <span>{car.mileage}</span>
                    <span className="text-amber-400">외판 {extText}</span>
                    <span className="text-emerald-400 font-semibold">매입 {buyPriceText}</span>
                    <span className="text-sky-400 font-semibold">판매 {sellPriceText}</span>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center justify-end gap-1.5 shrink-0" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedCarNum(car.carNumber);
                      onSelectCar(car);
                    }}
                    className={`px-2.5 py-1 rounded text-[11px] font-bold transition ${
                      isSelected
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'bg-[#1e2230] hover:bg-[#2a2f42] text-slate-300'
                    }`}
                  >
                    {isSelected ? '✅ 선택됨' : '👉 선택'}
                  </button>
                  {onAnalyzeInCockpit && (
                    <button
                      type="button"
                      onClick={() => onAnalyzeInCockpit(car)}
                      className="px-2 py-1 rounded bg-[#1e2230] hover:bg-[#2a2f42] text-slate-300 text-[11px] font-medium"
                      title="동급 매물 시세 분석"
                    >
                      시세
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Pagination Bar (tab_ledger.py L416-L422) */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2 text-xs">
          <button
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="px-3 py-1 rounded bg-[#181b24] border border-[#282c3c] text-slate-300 disabled:opacity-40"
          >
            이전
          </button>
          <span className="text-slate-400">
            {currentPage} / {totalPages} 페이지
          </span>
          <button
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="px-3 py-1 rounded bg-[#181b24] border border-[#282c3c] text-slate-300 disabled:opacity-40"
          >
            다음
          </button>
        </div>
      )}

      {/* 6. Vehicle Deletion & Backup Management (tab_ledger.py L545-L585) */}
      <div className="bg-[#12151e] border border-[#232733] p-4 rounded-xl">
        <div className="flex items-center gap-2 text-xs font-bold text-rose-400 mb-1">
          <Trash2 className="w-3.5 h-3.5" />
          <span>장부 차량 삭제 및 복원 관리</span>
        </div>
        <p className="text-[11px] text-slate-400 mb-3">
          선택한 차량을 매입 장부에서 삭제하거나 백업 데이터에서 복원합니다.
        </p>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[200px]">
            <select
              value={delTargetCar}
              onChange={(e) => setDelTargetCar(e.target.value)}
              className="w-full bg-[#0a0b0e] border border-[#282c3c] rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-rose-500"
            >
              <option value="">삭제할 장부 차량 선택...</option>
              {cars.map((c) => (
                <option key={c.id} value={c.carNumber}>
                  {c.carNumber} | {c.carName} ({c.year}년)
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            disabled={!delTargetCar}
            onClick={() => {
              if (delTargetCar && onDeleteCar) {
                if (window.confirm(`정말 [${delTargetCar}] 차량을 장부에서 삭제하시겠습니까?`)) {
                  onDeleteCar(delTargetCar);
                  setDelTargetCar('');
                }
              }
            }}
            className="px-3 py-1.5 bg-rose-950/80 hover:bg-rose-900 border border-rose-700/60 text-rose-300 rounded-lg text-xs font-bold transition disabled:opacity-40 flex items-center gap-1"
          >
            <Trash2 className="w-3 h-3" />
            <span>선택 차량 장부 삭제</span>
          </button>

          {onRestoreBackup && (
            <button
              type="button"
              onClick={onRestoreBackup}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-200 rounded-lg text-xs font-semibold transition flex items-center gap-1"
            >
              <RotateCcw className="w-3 h-3" />
              <span>최근 백업으로 장부 복원</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
