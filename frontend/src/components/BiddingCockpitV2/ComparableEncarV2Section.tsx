import React from 'react';
import { ExternalLink, RefreshCw, Car, AlertCircle, CheckCircle2 } from 'lucide-react';
import { EncarItem } from '@/components/BiddingCockpit/types';

export interface ComparableEncarV2SectionProps {
  encarList: EncarItem[];
  selectedEncarId: string | null;
  onSelectCar: (carId: string) => void | Promise<void>;
  isLoading: boolean;
  totalModelCount: number;
  filteredCount: number;
  isInitialState: boolean;
  errorMessage?: string | null;
}

// 사고구분 라벨 헬퍼 (무사고/단순수리/사고)
const formatAccident = (rawType?: string) => {
  if (!rawType || (rawType.includes('완전무사고') && !rawType.includes('교환') && !rawType.includes('판금'))) {
    return { text: '🟢 완전무사고', style: 'text-emerald-400 font-bold' };
  }
  if (rawType.includes('사고') && !rawType.includes('무사고')) {
    return { text: '🔴 프레임사고', style: 'text-rose-400 font-bold' };
  }
  const repMatch = rawType.match(/교환\s*[:\s]?\s*(\d+)/);
  const fixMatch = rawType.match(/판금\s*[:\s]?\s*(\d+)/);
  const rCnt = repMatch ? parseInt(repMatch[1], 10) : 0;
  const fCnt = fixMatch ? parseInt(fixMatch[1], 10) : 0;
  const total = rCnt + fCnt;
  if (total > 0) {
    return { text: `🟡 단순수리 (${total})`, style: 'text-amber-400 font-bold' };
  }
  if (rawType.includes('교환') && rawType.includes('판금')) {
    return { text: '🟡 단순(교/판)', style: 'text-amber-400 font-bold' };
  }
  if (rawType.includes('판금')) {
    return { text: '🟡 단순판금', style: 'text-amber-400 font-bold' };
  }
  if (rawType.includes('교환')) {
    return { text: '🟡 단순교환', style: 'text-amber-400 font-bold' };
  }
  return { text: `🟡 ${rawType.slice(0, 8)}`, style: 'text-amber-400 font-bold' };
};

export const ComparableEncarV2Section: React.FC<ComparableEncarV2SectionProps> = ({
  encarList,
  selectedEncarId,
  onSelectCar,
  isLoading,
  totalModelCount,
  filteredCount,
  isInitialState,
  errorMessage,
}) => {
  // 💡 [2026-11-01 제이 규칙]: 보정가 필드가 항목에 있으면 표시하되, 없으면 계산하지 않고 표시에서 제외(V2에서 계산 금지)
  const hasAdjustedPrice = encarList.some(
    (item) => (item as any).adjustedPrice !== undefined && (item as any).adjustedPrice !== null
  );

  return (
    <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl overflow-hidden shadow-sm space-y-0">
      {/* 1. 상단 헤더 (제목 및 매물 수) */}
      <div className="px-5 py-3.5 border-b border-[#1e2029] flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[#8b8e9d] uppercase tracking-wider">
            엔카 비교 매물
          </span>
          {!isInitialState && !isLoading && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-[#1f222e] text-zinc-300 font-mono">
              전체 {totalModelCount.toLocaleString()}대 중 {filteredCount || encarList.length}대 일치
            </span>
          )}
        </div>
        {errorMessage && (
          <div className="text-xs text-rose-400 flex items-center gap-1">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>{errorMessage}</span>
          </div>
        )}
      </div>

      {/* 2. 본문 영역 (상태별 분기) */}
      {/* 2-1) 로딩 상태 */}
      {isLoading ? (
        <div className="p-12 flex flex-col items-center justify-center gap-3 text-zinc-400">
          <RefreshCw className="w-6 h-6 animate-spin text-[#cc9166]" />
          <p className="text-xs sm:text-sm">엔카 비교 매물을 불러오는 중입니다...</p>
        </div>
      ) : isInitialState ? (
        /* 2-2) 조회 전 초기 상태: "조회하면 비교 목록이 여기에 표시됩니다" */
        <div className="p-12 flex flex-col items-center justify-center gap-3 text-zinc-500">
          <Car className="w-8 h-8 text-zinc-600 stroke-[1.5]" />
          <p className="text-xs sm:text-sm font-medium text-zinc-400">
            조회하면 비교 목록이 여기에 표시됩니다
          </p>
          <p className="text-[11px] text-zinc-600">
            상단에서 헤이딜러 URL 또는 차량번호를 입력하고 조회해 주세요.
          </p>
        </div>
      ) : encarList.length === 0 ? (
        /* 2-3) 조회 완료 후 0건: "해당 없음" */
        <div className="p-12 flex flex-col items-center justify-center gap-2 text-zinc-400">
          <AlertCircle className="w-7 h-7 text-amber-500/80 stroke-[1.5]" />
          <p className="text-xs sm:text-sm font-bold text-zinc-200">해당 없음</p>
          <p className="text-[11px] text-zinc-500">
            검색 조건에 부합하는 엔카 비교 매물이 존재하지 않습니다.
          </p>
        </div>
      ) : (
        /* 2-4) 목록 렌더링 */
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-200">
            <thead className="bg-[#14151b] border-b border-[#262833] text-[11px] text-[#8b8e9d] uppercase font-semibold">
              <tr>
                <th className="py-2.5 px-3 text-center w-10">선택</th>
                <th className="py-2.5 px-3">모델 / 세부등급</th>
                <th className="py-2.5 px-3 text-center w-16">연식</th>
                <th className="py-2.5 px-3 text-right w-24">주행거리</th>
                <th className="py-2.5 px-3 text-right w-24">가격</th>
                {hasAdjustedPrice && (
                  <th className="py-2.5 px-3 text-right w-24">보정가</th>
                )}
                <th className="py-2.5 px-3 text-center w-28">사고구분</th>
                <th className="py-2.5 px-3 text-center w-24">점검일</th>
                <th className="py-2.5 px-3 text-center w-14">상세</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2029]">
              {encarList.map((car) => {
                const isSelected = selectedEncarId === car.id;
                const accInfo = formatAccident(car.accidentType);
                const detailUrl = car.encarUrl || `https://fem.encar.com/cars/detail/${car.id}`;

                return (
                  <tr
                    key={car.id}
                    onClick={() => onSelectCar(car.id)}
                    className={`cursor-pointer transition select-none ${
                      isSelected
                        ? 'bg-blue-950/40 text-white font-medium border-l-2 border-blue-500'
                        : 'hover:bg-[#161822]'
                    }`}
                  >
                    {/* 1) 선택 라디오 */}
                    <td className="py-2 px-3 text-center">
                      <input
                        type="radio"
                        checked={isSelected}
                        onChange={() => onSelectCar(car.id)}
                        className="text-blue-500 focus:ring-0 focus:ring-offset-0 bg-[#161822] border-[#262938] cursor-pointer"
                      />
                    </td>

                    {/* 2) 모델 / 세부등급 */}
                    <td className="py-2 px-3">
                      <div className="flex flex-col">
                        <span className="font-semibold text-zinc-100 truncate max-w-xs">
                          {car.carName}
                        </span>
                        {car.subModel && (
                          <span className="text-[11px] text-zinc-400 truncate max-w-xs">
                            {car.subModel}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* 3) 연식 */}
                    <td className="py-2 px-3 text-center font-mono text-zinc-300">
                      {car.year}
                    </td>

                    {/* 4) 주행거리 */}
                    <td className="py-2 px-3 text-right font-mono text-zinc-200">
                      {car.mileage.toLocaleString()}km
                    </td>

                    {/* 5) 가격 */}
                    <td className="py-2 px-3 text-right font-mono font-bold text-amber-400">
                      {car.price.toLocaleString()}만원
                    </td>

                    {/* 6) 보정가 (필드가 존재할 때만 표시) */}
                    {hasAdjustedPrice && (
                      <td className="py-2 px-3 text-right font-mono text-sky-400 font-semibold">
                        {(car as any).adjustedPrice !== undefined && (car as any).adjustedPrice !== null
                          ? `${Number((car as any).adjustedPrice).toLocaleString()}만원`
                          : '-'}
                      </td>
                    )}

                    {/* 7) 사고구분 */}
                    <td className="py-2 px-3 text-center whitespace-nowrap">
                      <span className={`text-[11px] ${accInfo.style}`}>
                        {accInfo.text}
                      </span>
                    </td>

                    {/* 8) 점검일 */}
                    <td className="py-2 px-3 text-center font-mono text-[11px] text-zinc-400 whitespace-nowrap">
                      {car.checkDate || car.inspectionDate || '-'}
                    </td>

                    {/* 9) 엔카 상세 링크 */}
                    <td className="py-2 px-3 text-center">
                      <a
                        href={detailUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        title="엔카 상세 페이지 열기"
                        className="inline-flex items-center justify-center p-1 rounded text-zinc-400 hover:text-white hover:bg-zinc-800 transition"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
