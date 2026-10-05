import React, { useState, useEffect } from 'react';
import { CarLedgerItem } from '@/types';
import { X, Wrench, DollarSign, Check, Trash2, Tag, Calendar, ShieldAlert, ExternalLink } from 'lucide-react';

interface CarDetailModalProps {
  car: CarLedgerItem | null;
  onClose: () => void;
  onUpdate: (updatedCar: CarLedgerItem) => void;
  onDelete: (id: string) => void;
}

export const CarDetailModal: React.FC<CarDetailModalProps> = ({
  car,
  onClose,
  onUpdate,
  onDelete,
}) => {
  if (!car) return null;

  const [buyPrice, setBuyPrice] = useState(car.buyPrice);
  const [sellPrice, setSellPrice] = useState(car.sellPrice);
  const [outerRepairs, setOuterRepairs] = useState(car.outerRepairs);
  const [repairCost, setRepairCost] = useState(car.repairCost);
  const [heydealerFee, setHeydealerFee] = useState(car.heydealerFee);
  const [status, setStatus] = useState(car.status);
  const [memo, setMemo] = useState(car.memo);

  useEffect(() => {
    if (car) {
      setBuyPrice(car.buyPrice);
      setSellPrice(car.sellPrice);
      setOuterRepairs(car.outerRepairs);
      setRepairCost(car.repairCost);
      setHeydealerFee(car.heydealerFee);
      setStatus(car.status);
      setMemo(car.memo);
    }
  }, [car]);

  const encarMatch = car.memo?.match(/https?:\/\/[^\s\n\r]+/);
  const cleanCarId = String(car.id || '').replace(/[^\d]/g, '');
  const encarDetailUrl = encarMatch 
    ? encarMatch[0] 
    : cleanCarId.length >= 7 
      ? `https://fem.encar.com/cars/detail/${cleanCarId}`
      : null;

  const margin = sellPrice - buyPrice - repairCost - heydealerFee;

  const handleSave = () => {
    onUpdate({
      ...car,
      buyPrice,
      sellPrice,
      outerRepairs,
      repairCost,
      heydealerFee,
      status,
      memo,
    });
    onClose();
  };

  const handleOuterRepairsChange = (panels: number) => {
    setOuterRepairs(panels);
    setRepairCost(panels * 13);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 overflow-y-auto">
      <div className="bg-[#0e0f13] border border-[#1c1d22] rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in duration-200">
        
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-[#1c1d22] flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-white tracking-wide">
                {car.carNumber}
              </h3>
              <span className="text-xs px-2 py-0.5 rounded-full bg-[#cc9166]/15 text-[#cc9166] border border-[#cc9166]/30 font-semibold">
                {car.status}
              </span>
              {encarDetailUrl && (
                <a
                  href={encarDetailUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[11px] px-2.5 py-1 rounded bg-blue-500/10 hover:bg-blue-500/20 text-cyan-400 border border-blue-500/30 flex items-center gap-1 font-semibold transition"
                  title="엔카 공식 상세페이지 새창 열기"
                >
                  <span>엔카 원본 상세</span>
                  <ExternalLink className="w-3 h-3 text-cyan-400" />
                </a>
              )}
            </div>
            <p className="text-xs text-[#9194a1] mt-0.5">
              {car.manufacturer} {car.carName} {car.detailModel} ({car.year}년식 · {car.mileage})
            </p>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-[#121317] hover:bg-[#1c1d22] border border-[#1c1d22] text-[#9194a1] hover:text-white flex items-center justify-center transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body Form */}
        <div className="p-4 sm:p-5 space-y-4 max-h-[75vh] overflow-y-auto">
          
          {/* Options Display */}
          {car.options && (
            <div className="bg-[#121317] border border-[#1c1d22] rounded-xl p-3">
              <div className="text-[11px] text-[#9194a1] mb-1.5 flex items-center gap-1">
                <Tag className="w-3 h-3 text-[#cc9166]" />
                장착 옵션 목록
              </div>
              <div className="flex flex-wrap gap-1.5">
                {car.options.split(/[\/,+]/).map((opt, i) => (
                  <span
                    key={i}
                    className="text-[11px] px-2 py-0.5 rounded bg-[#1c1d22] text-[#e2e3e9] border border-white/5"
                  >
                    {opt.trim()}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Pricing Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">매입가 (만원)</label>
              <input
                type="number"
                value={buyPrice}
                onChange={(e) => setBuyPrice(Number(e.target.value))}
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-sm font-semibold text-white focus:outline-none focus:border-[#cc9166]"
              />
            </div>

            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">예상/실제 판매가 (만원)</label>
              <input
                type="number"
                value={sellPrice}
                onChange={(e) => setSellPrice(Number(e.target.value))}
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-sm font-semibold text-[#cc9166] focus:outline-none focus:border-[#cc9166]"
              />
            </div>
          </div>

          {/* Repairs & Fees */}
          <div className="grid grid-cols-3 gap-2 sm:gap-3">
            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">외판수리 (판수)</label>
              <input
                type="number"
                value={outerRepairs}
                onChange={(e) => handleOuterRepairsChange(Number(e.target.value))}
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#cc9166]"
              />
            </div>

            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">외판수리비 (만원)</label>
              <input
                type="number"
                value={repairCost}
                onChange={(e) => setRepairCost(Number(e.target.value))}
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-xs text-amber-300 focus:outline-none focus:border-[#cc9166]"
              />
            </div>

            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">헤딜수수료 (만원)</label>
              <input
                type="number"
                step="0.5"
                value={heydealerFee}
                onChange={(e) => setHeydealerFee(Number(e.target.value))}
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-xs text-[#c7c9d1] focus:outline-none focus:border-[#cc9166]"
              />
            </div>
          </div>

          {/* Status & Memo */}
          <div className="space-y-3">
            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">진행 상태</label>
              <div className="grid grid-cols-3 gap-2">
                {['장부저장', '보유중', '판매완료'].map((st) => (
                  <button
                    key={st}
                    type="button"
                    onClick={() => setStatus(st)}
                    className={`py-2 rounded-lg text-xs font-semibold border transition ${
                      status === st
                        ? 'bg-[#cc9166]/20 text-[#cc9166] border-[#cc9166]'
                        : 'bg-[#121317] text-[#9194a1] border-[#1c1d22] hover:text-white'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">특이사항 / 메모</label>
              <textarea
                rows={2}
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
                placeholder="예: [셀프(기본) / 마진: 120만] 하부 부식 없음, 타이어 80% 잔여"
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-xs text-white placeholder-[#5e616e] focus:outline-none focus:border-[#cc9166]"
              />
            </div>
          </div>

          {/* Live Calculated Margin */}
          <div className="bg-gradient-to-r from-[#121317] to-[#16171d] border border-[#cc9166]/30 rounded-xl p-3.5 flex items-center justify-between">
            <div>
              <div className="text-[11px] text-[#9194a1]">현재 계산된 순마진</div>
              <div className="text-xs text-[#5e616e]">
                판매가 - 매입가 - 외판비 - 헤딜수수료
              </div>
            </div>
            <div className="text-right">
              <span className={`text-xl font-bold ${margin >= 100 ? 'text-[#cc9166]' : margin > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                +{margin.toLocaleString()}
              </span>
              <span className="text-xs text-[#9194a1] ml-0.5">만원</span>
            </div>
          </div>

        </div>

        {/* Footer Actions */}
        <div className="p-4 sm:p-5 border-t border-[#1c1d22] flex items-center justify-between gap-3 bg-[#0a0a0c]">
          <button
            type="button"
            onClick={() => {
              if (confirm(`'${car.carNumber}' 차량을 원장에서 삭제하시겠습니까?`)) {
                onDelete(car.id);
                onClose();
              }
            }}
            className="px-3 py-2 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 text-xs font-medium flex items-center gap-1.5 transition"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>삭제</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-[#121317] hover:bg-[#1c1d22] text-[#9194a1] hover:text-white border border-[#1c1d22] text-xs font-medium transition"
            >
              취소
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-5 py-2 rounded-lg bg-[#cc9166] hover:bg-[#dba177] text-black text-xs font-bold flex items-center gap-1.5 transition shadow"
            >
              <Check className="w-4 h-4 stroke-[2.5]" />
              <span>수정 완료</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
