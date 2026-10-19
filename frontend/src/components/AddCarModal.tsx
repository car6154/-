import React, { useState } from 'react';
import { CarLedgerItem } from '@/types';
import { X, PlusCircle } from 'lucide-react';

interface AddCarModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (newCar: Omit<CarLedgerItem, 'id' | 'regDate'>) => void;
}

export const AddCarModal: React.FC<AddCarModalProps> = ({
  isOpen,
  onClose,
  onAdd,
}) => {
  if (!isOpen) return null;

  const [carNumber, setCarNumber] = useState('');
  const [manufacturer, setManufacturer] = useState('현대');
  const [carName, setCarName] = useState('');
  const [detailModel, setDetailModel] = useState('');
  const [year, setYear] = useState('22');
  const [mileage, setMileage] = useState('50,000 km');
  const [options, setOptions] = useState('');
  const [buyPrice, setBuyPrice] = useState(1000);
  const [sellPrice, setSellPrice] = useState(1250);
  const [outerRepairs, setOuterRepairs] = useState(1);
  const [repairCost, setRepairCost] = useState(13);
  const [heydealerFee, setHeydealerFee] = useState(25.0);
  const [memo, setMemo] = useState('[셀프(기본) / 마진: 120만]');
  const [status] = useState('장부저장');

  const margin = sellPrice - buyPrice - repairCost - heydealerFee;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!carNumber.trim() || !carName.trim()) {
      alert('차량번호와 차량명을 입력해주세요.');
      return;
    }

    onAdd({
      carNumber: carNumber.trim(),
      manufacturer,
      carName: carName.trim(),
      detailModel: detailModel.trim(),
      year: year.trim(),
      mileage: mileage.trim(),
      options: options.trim(),
      buyPrice,
      sellPrice,
      outerRepairs,
      repairCost,
      heydealerFee,
      memo: memo.trim(),
      status,
    });

    onClose();
  };

  const handlePanelsChange = (p: number) => {
    setOuterRepairs(p);
    setRepairCost(p * 13);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 overflow-y-auto">
      <div className="bg-[#0e0f13] border border-[#1c1d22] rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in duration-200">
        
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-[#1c1d22] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#cc9166]/15 border border-[#cc9166]/30 flex items-center justify-center">
              <PlusCircle className="w-4 h-4 text-[#cc9166]" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                원장에 새 차량 등록
              </h3>
              <p className="text-xs text-[#9194a1]">
                매입한 차량이나 관심 차량을 원장에 즉시 저장합니다.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-[#121317] hover:bg-[#1c1d22] border border-[#1c1d22] text-[#9194a1] hover:text-white flex items-center justify-center transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-4 sm:p-5 space-y-4 max-h-[75vh] overflow-y-auto">
          
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">차량번호 *</label>
              <input
                type="text"
                required
                placeholder="예: 149소7481"
                value={carNumber}
                onChange={(e) => setCarNumber(e.target.value)}
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-xs text-white placeholder-[#5e616e] focus:outline-none focus:border-[#cc9166]"
              />
            </div>

            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">제조사</label>
              <select
                value={manufacturer}
                onChange={(e) => setManufacturer(e.target.value)}
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#cc9166]"
              >
                <option value="현대">현대</option>
                <option value="기아">기아</option>
                <option value="르노코리아(삼성)">르노코리아</option>
                <option value="쉐보레(GM대우)">쉐보레</option>
                <option value="KG모빌리티(쌍용)">KG모빌리티</option>
                <option value="제네시스">제네시스</option>
                <option value="BMW">BMW</option>
                <option value="벤츠">벤츠</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">차량명 *</label>
              <input
                type="text"
                required
                placeholder="예: 캐스퍼, 아반떼 AD"
                value={carName}
                onChange={(e) => setCarName(e.target.value)}
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-xs text-white placeholder-[#5e616e] focus:outline-none focus:border-[#cc9166]"
              />
            </div>

            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">세부모델 / 등급</label>
              <input
                type="text"
                placeholder="1.0 터보 인스퍼레이션"
                value={detailModel}
                onChange={(e) => setDetailModel(e.target.value)}
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-xs text-white placeholder-[#5e616e] focus:outline-none focus:border-[#cc9166]"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">연식</label>
              <input
                type="text"
                placeholder="22"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#cc9166]"
              />
            </div>

            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">주행거리</label>
              <input
                type="text"
                placeholder="41,000 km"
                value={mileage}
                onChange={(e) => setMileage(e.target.value)}
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#cc9166]"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] text-[#9194a1] mb-1">주요 옵션</label>
            <input
              type="text"
              placeholder="스마트키 / 내비게이션 / 썬루프 / 통풍시트"
              value={options}
              onChange={(e) => setOptions(e.target.value)}
              className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-xs text-white placeholder-[#5e616e] focus:outline-none focus:border-[#cc9166]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3 pt-2 border-t border-[#1c1d22]">
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
              <label className="block text-[11px] text-[#9194a1] mb-1">판매가 (만원)</label>
              <input
                type="number"
                value={sellPrice}
                onChange={(e) => setSellPrice(Number(e.target.value))}
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-sm font-semibold text-[#cc9166] focus:outline-none focus:border-[#cc9166]"
              />
            </div>
          </div>

          {/* Repairs & Fees (외판수리, 외판수리비, 헤딜수수료, 기타비용 분리 명시) */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">외판수리 (판)</label>
              <input
                type="number"
                value={outerRepairs}
                onChange={(e) => handlePanelsChange(Number(e.target.value))}
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-[#cc9166]"
              />
            </div>

            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">외판수리비</label>
              <input
                type="number"
                value={repairCost}
                onChange={(e) => setRepairCost(Number(e.target.value))}
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-2.5 py-2 text-xs text-amber-300 focus:outline-none focus:border-[#cc9166]"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-[11px] text-emerald-400 font-bold">헤딜수수료</label>
                <span className="text-[10px] text-emerald-500/80">자동표시</span>
              </div>
              <input
                type="number"
                step="any"
                value={heydealerFee || ''}
                placeholder="0"
                onChange={(e) => setHeydealerFee(parseFloat(e.target.value) || 0)}
                className="w-full bg-[#121317] border border-emerald-500/60 rounded-lg px-2.5 py-2 text-xs text-emerald-400 font-bold font-mono focus:outline-none focus:border-emerald-400"
                title="매입연동으로 가져온 헤이딜러 수수료입니다. (값 있으면 자동표시, 없으면 0원 또는 빈칸)"
              />
            </div>

            <div>
              <label className="block text-[11px] text-[#9194a1] mb-1">기타비용 (만원)</label>
              <input
                type="number"
                step="any"
                defaultValue={15}
                placeholder="15"
                className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-2.5 py-2 text-xs text-zinc-300 focus:outline-none focus:border-[#cc9166]"
                title="등록/탁송 등 기본 제경비 (헤딜수수료와 명확히 분리)"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] text-[#9194a1] mb-1">특이사항 / 메모</label>
            <input
              type="text"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              placeholder="예: [셀프(기본) / 마진: 120만]"
              className="w-full bg-[#121317] border border-[#1c1d22] rounded-lg px-3 py-2 text-xs text-white placeholder-[#5e616e] focus:outline-none focus:border-[#cc9166]"
            />
          </div>

          {/* Expected Margin summary */}
          <div className="bg-[#121317] border border-[#1c1d22] rounded-xl p-3 flex items-center justify-between">
            <span className="text-xs text-[#9194a1]">예상 확보 마진</span>
            <span className="text-base font-bold text-[#cc9166]">
              +{margin.toLocaleString()}만원
            </span>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              className="w-full py-2.5 rounded-xl bg-[#cc9166] hover:bg-[#dba177] text-black font-bold text-xs flex items-center justify-center gap-1.5 transition shadow"
            >
              <PlusCircle className="w-4 h-4 stroke-[2.5]" />
              <span>원장에 추가하기</span>
            </button>
          </div>

        </form>

      </div>
    </div>
  );
};
