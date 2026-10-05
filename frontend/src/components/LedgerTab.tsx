import React, { useState, useMemo } from 'react';
import { CarLedgerItem } from '@/types';
import { 
  Download, 
  Filter, 
  ArrowUpDown, 
  Wrench, 
  Tag, 
  ExternalLink, 
  Edit3, 
  CheckCircle,
  FileSpreadsheet
} from 'lucide-react';

interface LedgerTabProps {
  cars: CarLedgerItem[];
  searchQuery: string;
  onSelectCar: (car: CarLedgerItem) => void;
  onUpdateStatus: (id: string, newStatus: string) => void;
  onConfirmPurchase?: (car: CarLedgerItem, actualBuyPrice: number) => void;
  onAnalyzeInCockpit?: (car: CarLedgerItem) => void;
}

export const LedgerTab: React.FC<LedgerTabProps> = ({
  cars,
  searchQuery,
  onSelectCar,
  onUpdateStatus,
  onConfirmPurchase,
  onAnalyzeInCockpit,
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [makerFilter, setMakerFilter] = useState<string>('all');
  const [sortKey, setSortKey] = useState<'date' | 'margin' | 'sell' | 'buy'>('date');
  
  // Top confirmation form states
  const [selectedCarNum, setSelectedCarNum] = useState<string>(cars[0]?.carNumber || '');
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

  // Filtered & Sorted cars
  const filteredCars = useMemo(() => {
    return cars.filter((car) => {
      // Search
      const query = searchQuery.toLowerCase().trim();
      const matchSearch =
        !query ||
        car.carNumber.toLowerCase().includes(query) ||
        car.carName.toLowerCase().includes(query) ||
        car.manufacturer.toLowerCase().includes(query) ||
        car.detailModel.toLowerCase().includes(query) ||
        car.options.toLowerCase().includes(query);

      // Status
      const matchStatus = statusFilter === 'all' || car.status === statusFilter;

      // Manufacturer
      const matchMaker = makerFilter === 'all' || car.manufacturer.includes(makerFilter);

      return matchSearch && matchStatus && matchMaker;
    }).sort((a, b) => {
      if (sortKey === 'margin') {
        const marginA = a.sellPrice - a.buyPrice - a.repairCost - a.heydealerFee;
        const marginB = b.sellPrice - b.buyPrice - b.repairCost - b.heydealerFee;
        return marginB - marginA;
      }
      if (sortKey === 'sell') return b.sellPrice - a.sellPrice;
      if (sortKey === 'buy') return b.buyPrice - a.buyPrice;
      // Default: date (latest first by id/index or regDate)
      return 0;
    });
  }, [cars, searchQuery, statusFilter, makerFilter, sortKey]);

  // Export to Google Sheet standard CSV
  const handleExportCSV = () => {
    const headers = [
      '등록일', '차량번호', '제조사', '차량명', '세부모델', '연식', '주행거리', '매입가', '판매가', '특이사항'
    ];

    const rows = filteredCars.map(c => [
      c.regDate || '',
      c.carNumber || '',
      c.manufacturer || '',
      c.carName || '',
      c.detailModel || '',
      c.year || '',
      `"${(c.mileage || '').replace(/"/g, '""')}"`,
      c.buyPrice ?? '',
      c.sellPrice ?? '',
      `"${(c.memo || '').replace(/"/g, '""')}"`
    ].join(','));

    const csvContent = '\uFEFF' + [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `JPRO_구글시트_차량원장_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-4">

      {/* 📦 실전 매입 확정 처리 폼 (tab_ledger.py 원본 1:1 완벽 복원) */}
      <div className="bg-[#121317] border border-[#2b2d3a] p-4 rounded-xl shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-blue-400">📦 실전 매입 확정 처리</span>
            <span className="text-[11px] bg-blue-950 text-blue-300 border border-blue-800/60 px-2 py-0.5 rounded">원클릭 재고 이관</span>
          </div>
          <span className="text-xs text-[#9194a1]">
            낙찰/매입된 차량의 [🚀 매입 확정]을 누르면 `💰 실전 재고 및 정산 관리` 탭으로 이동하여 실제 판매 및 내 실수익을 정산합니다.
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 items-end">
          <div>
            <label className="text-xs text-[#8b8e9d] block mb-1">차량번호 선택:</label>
            <select
              value={selectedCarNum}
              onChange={(e) => setSelectedCarNum(e.target.value)}
              className="w-full bg-[#0a0b0e] border border-[#22242c] rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-blue-500 font-semibold"
            >
              {cars.map((c) => (
                <option key={c.id} value={c.carNumber}>
                  {c.carNumber} | {c.carName} {c.detailModel} ({c.year}년 / {c.buyPrice}만)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs text-[#8b8e9d] block mb-1">실제 낙찰/매입가 (만원):</label>
            <input
              type="number"
              value={actualBuyPrice}
              onChange={(e) => setActualBuyPrice(Number(e.target.value))}
              className="w-full bg-[#0a0b0e] border border-[#22242c] rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-blue-500 font-bold text-amber-400"
            />
          </div>

          <button
            type="button"
            onClick={() => {
              if (currentSelectedCar && onConfirmPurchase) {
                onConfirmPurchase(currentSelectedCar, actualBuyPrice);
              }
            }}
            className="w-full py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-lg text-xs font-bold transition shadow-md shadow-blue-500/20 cursor-pointer flex items-center justify-center gap-1.5"
          >
            <span>🚀 매입 확정 (재고 등록)</span>
          </button>

          <button
            type="button"
            onClick={() => {
              if (currentSelectedCar && onAnalyzeInCockpit) {
                onAnalyzeInCockpit(currentSelectedCar);
              }
            }}
            className="w-full py-2 bg-[#1c1d24] hover:bg-[#252732] text-slate-200 border border-slate-700/80 rounded-lg text-xs font-bold transition cursor-pointer flex items-center justify-center gap-1.5"
          >
            <span>🔍 동급 시세 분석</span>
          </button>
        </div>
      </div>
      
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 bg-[#0e0f13] border border-[#1c1d22] p-3 rounded-xl">
        <div className="flex flex-wrap items-center gap-2">
          
          {/* Status Filter */}
          <div className="flex items-center gap-1 bg-[#121317] border border-[#1c1d22] rounded-lg p-0.5 text-xs">
            {['all', '장부저장', '보유중', '판매완료'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-2.5 py-1 rounded-md transition ${
                  statusFilter === st
                    ? 'bg-[#cc9166] text-black font-semibold'
                    : 'text-[#9194a1] hover:text-white'
                }`}
              >
                {st === 'all' ? '전체상태' : st}
              </button>
            ))}
          </div>

          {/* Maker Filter */}
          <select
            value={makerFilter}
            onChange={(e) => setMakerFilter(e.target.value)}
            className="bg-[#121317] border border-[#1c1d22] text-xs text-white px-2.5 py-1.5 rounded-lg focus:outline-none focus:border-[#cc9166]"
          >
            <option value="all">모든 제조사</option>
            <option value="현대">현대</option>
            <option value="기아">기아</option>
            <option value="르노">르노코리아</option>
            <option value="쉐보레">쉐보레</option>
            <option value="KG">KG모빌리티</option>
            <option value="BMW">BMW / 벤츠 / 수입</option>
          </select>

          {/* Sort */}
          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as any)}
            className="bg-[#121317] border border-[#1c1d22] text-xs text-white px-2.5 py-1.5 rounded-lg focus:outline-none focus:border-[#cc9166]"
          >
            <option value="date">최근 등록순</option>
            <option value="margin">예상 마진 높은순</option>
            <option value="sell">판매가 높은순</option>
            <option value="buy">매입가 높은순</option>
          </select>
        </div>

        {/* Counter & CSV Download */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-[#9194a1]">
            조회 <strong className="text-white font-semibold">{filteredCars.length}</strong>대
          </span>
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#121317] hover:bg-[#1c1d22] border border-[#1c1d22] text-white font-medium transition"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-[#cc9166]" />
            <span>CSV 저장</span>
          </button>
        </div>
      </div>

      {/* Mobile Card List View (< 768px) */}
      <div className="grid grid-cols-1 gap-3 md:hidden">
        {filteredCars.map((car) => {
          const margin = car.sellPrice - car.buyPrice - car.repairCost - car.heydealerFee;
          return (
            <div
              key={car.id}
              onClick={() => onSelectCar(car)}
              className="bg-[#0e0f13] hover:bg-[#121317] border border-[#1c1d22] hover:border-[#cc9166]/50 rounded-xl p-3.5 transition active:scale-[0.99] cursor-pointer"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-white tracking-wide">
                      {car.carNumber}
                    </span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                      car.status === '판매완료'
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'bg-[#cc9166]/15 text-[#cc9166] border border-[#cc9166]/30'
                    }`}>
                      {car.status}
                    </span>
                  </div>
                  <div className="text-xs text-[#c7c9d1] font-medium mt-1">
                    {car.manufacturer} {car.carName} {car.detailModel}
                  </div>
                  <div className="text-[11px] text-[#9194a1] mt-0.5">
                    {car.year}년식 · {car.mileage}
                  </div>
                </div>

                {/* Net Margin Badge */}
                <div className="text-right">
                  <div className="text-[10px] text-[#9194a1]">예상 마진</div>
                  <div className={`text-sm font-bold ${margin >= 100 ? 'text-[#cc9166]' : margin > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    +{margin}만원
                  </div>
                </div>
              </div>

              {/* Price Details Grid */}
              <div className="grid grid-cols-4 gap-1.5 mt-3 pt-2.5 border-t border-[#1c1d22] text-center text-xs">
                <div className="bg-[#121317] rounded-lg py-1 px-1">
                  <div className="text-[10px] text-[#9194a1]">매입가</div>
                  <div className="font-semibold text-white">{car.buyPrice}만</div>
                </div>
                <div className="bg-[#121317] rounded-lg py-1 px-1">
                  <div className="text-[10px] text-[#9194a1]">판매가</div>
                  <div className="font-semibold text-white">{car.sellPrice}만</div>
                </div>
                <div className="bg-[#121317] rounded-lg py-1 px-1">
                  <div className="text-[10px] text-[#9194a1]">외판 {car.outerRepairs}판</div>
                  <div className="font-semibold text-[#c7c9d1]">{car.repairCost}만</div>
                </div>
                <div className="bg-[#121317] rounded-lg py-1 px-1">
                  <div className="text-[10px] text-[#9194a1]">헤딜 수수료</div>
                  <div className="font-semibold text-[#c7c9d1]">{car.heydealerFee}만</div>
                </div>
              </div>

              {/* Memo / Notes */}
              {car.memo && (
                <div className="mt-2 text-[11px] text-[#9194a1] bg-[#121317]/60 rounded-md px-2 py-1 truncate">
                  {car.memo}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Desktop Table View (>= 768px) */}
      <div className="hidden md:block overflow-hidden rounded-xl border border-[#1c1d22] bg-[#0e0f13]">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-[#e2e3e9]">
            <thead className="bg-[#121317] text-[#9194a1] border-b border-[#1c1d22] font-medium">
              <tr>
                <th className="py-3 px-3">등록일</th>
                <th className="py-3 px-3">차량번호</th>
                <th className="py-3 px-3">차종 / 세부모델</th>
                <th className="py-3 px-3">연식/주행</th>
                <th className="py-3 px-3 text-right">매입가</th>
                <th className="py-3 px-3 text-right">판매가</th>
                <th className="py-3 px-3 text-center">외판수리</th>
                <th className="py-3 px-3 text-right">헤딜수수료</th>
                <th className="py-3 px-3 text-right">예상마진</th>
                <th className="py-3 px-3">특이사항</th>
                <th className="py-3 px-3 text-center">상태</th>
                <th className="py-3 px-3 text-center">관리</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1c1d22]">
              {filteredCars.map((car) => {
                const margin = car.sellPrice - car.buyPrice - car.repairCost - car.heydealerFee;
                return (
                  <tr 
                    key={car.id} 
                    className="hover:bg-[#121317]/80 transition group cursor-pointer"
                    onClick={() => onSelectCar(car)}
                  >
                    <td className="py-3 px-3 text-[#9194a1] whitespace-nowrap">
                      {car.regDate}
                    </td>
                    <td className="py-3 px-3 font-semibold text-white whitespace-nowrap">
                      {car.carNumber}
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-medium text-white">
                        {car.manufacturer} {car.carName}
                      </div>
                      <div className="text-[11px] text-[#9194a1] truncate max-w-xs">
                        {car.detailModel}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-[#c7c9d1] whitespace-nowrap">
                      <div>{car.year}년식</div>
                      <div className="text-[11px] text-[#9194a1]">{car.mileage}</div>
                    </td>
                    <td className="py-3 px-3 text-right font-medium text-white whitespace-nowrap">
                      {car.buyPrice.toLocaleString()}만
                    </td>
                    <td className="py-3 px-3 text-right font-bold text-white whitespace-nowrap">
                      {car.sellPrice.toLocaleString()}만
                    </td>
                    <td className="py-3 px-3 text-center whitespace-nowrap">
                      {car.outerRepairs > 0 ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 text-[11px]">
                          <Wrench className="w-3 h-3" />
                          {car.outerRepairs}판 ({car.repairCost}만)
                        </span>
                      ) : (
                        <span className="text-[#5e616e] text-[11px]">무수리</span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-right text-[#c7c9d1] whitespace-nowrap">
                      {car.heydealerFee}만
                    </td>
                    <td className="py-3 px-3 text-right whitespace-nowrap">
                      <span className={`font-bold px-2 py-0.5 rounded text-xs ${
                        margin >= 100
                          ? 'bg-[#cc9166]/15 text-[#cc9166] border border-[#cc9166]/30'
                          : margin > 0
                          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                          : 'bg-red-500/15 text-red-400 border border-red-500/30'
                      }`}>
                        +{margin.toLocaleString()}만
                      </span>
                    </td>
                    <td className="py-3 px-3 text-[#9194a1] max-w-xs truncate text-[11px]">
                      {car.memo || '-'}
                    </td>
                    <td className="py-3 px-3 text-center whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => {
                          const nextStatus = car.status === '장부저장' ? '보유중' : car.status === '보유중' ? '판매완료' : '장부저장';
                          onUpdateStatus(car.id, nextStatus);
                        }}
                        className={`text-[11px] px-2.5 py-1 rounded-full font-medium transition cursor-pointer ${
                          car.status === '판매완료'
                            ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/30'
                            : car.status === '보유중'
                            ? 'bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 border border-blue-500/30'
                            : 'bg-[#cc9166]/15 text-[#cc9166] hover:bg-[#cc9166]/25 border border-[#cc9166]/30'
                        }`}
                      >
                        {car.status}
                      </button>
                    </td>
                    <td className="py-3 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-center gap-1.5">
                        {onConfirmPurchase && car.status !== '판매완료' && (
                          <button
                            type="button"
                            onClick={() => onConfirmPurchase(car, car.buyPrice)}
                            className="px-2 py-1 rounded bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/40 text-[10px] font-bold transition flex items-center gap-0.5"
                            title="재고 관리로 이관 (매입 확정)"
                          >
                            <span>확정</span>
                          </button>
                        )}
                        {onAnalyzeInCockpit && (
                          <button
                            type="button"
                            onClick={() => onAnalyzeInCockpit(car)}
                            className="px-2 py-1 rounded bg-[#1e2029] hover:bg-[#2a2d3b] text-slate-300 border border-slate-700 text-[10px] font-semibold transition flex items-center gap-0.5"
                            title="동급 매물 시세 분석 화면으로 이동"
                          >
                            <span>시세</span>
                          </button>
                        )}
                        <button
                          onClick={() => onSelectCar(car)}
                          className="p-1 rounded hover:bg-[#1c1d22] text-[#9194a1] hover:text-white transition"
                          title="상세보기 및 편집"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
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
