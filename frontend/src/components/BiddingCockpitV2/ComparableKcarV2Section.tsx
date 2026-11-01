import React from 'react';
import { ExternalLink, RefreshCw, Car, AlertCircle } from 'lucide-react';
import { KcarCarItem } from '@/components/BiddingCockpit/types';

export interface ComparableKcarV2SectionProps {
  kcarList: KcarCarItem[];
  isLoading: boolean;
  totalCount: number;
  strictCount: number;
  isInitialState: boolean;
  errorMessage?: string | null;
}

// 사고구분 라벨 헬퍼 (케이카 무사고/단순수리/사고 배지)
const formatKcarAccident = (rawType?: string) => {
  if (!rawType || rawType.includes('무사고')) {
    return { text: '🟢 무사고', style: 'text-emerald-400 font-bold' };
  }
  if (rawType.includes('단순수리')) {
    return { text: '🟡 단순수리', style: 'text-amber-400 font-bold' };
  }
  if (rawType.includes('사고')) {
    return { text: '🔴 사고', style: 'text-rose-400 font-bold' };
  }
  return { text: rawType || '-', style: 'text-zinc-300 font-medium' };
};

export const ComparableKcarV2Section: React.FC<ComparableKcarV2SectionProps> = ({
  kcarList,
  isLoading,
  totalCount,
  strictCount,
  isInitialState,
  errorMessage,
}) => {
  return (
    <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl overflow-hidden shadow-sm space-y-0">
      {/* 1. 상단 헤더 (제목 및 매물 수) */}
      <div className="px-5 py-3.5 border-b border-[#1e2029] flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[#8b8e9d] uppercase tracking-wider">
            케이카 비교 매물
          </span>
          {!isInitialState && !isLoading && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-[#1f222e] text-zinc-300 font-mono">
              전체 {totalCount.toLocaleString()}대 중 {strictCount.toLocaleString()}대 일치
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
          <RefreshCw className="w-6 h-6 animate-spin text-amber-500" />
          <p className="text-xs sm:text-sm">케이카 비교 매물을 불러오는 중입니다...</p>
        </div>
      ) : isInitialState ? (
        /* 2-2) 조회 전 초기 상태: "조회하면 비교 목록이 여기에 표시됩니다" */
        <div className="p-12 flex flex-col items-center justify-center gap-3 text-zinc-500">
          <Car className="w-8 h-8 text-zinc-600 stroke-[1.5]" />
          <p className="text-xs sm:text-sm font-medium text-zinc-400">
            조회하면 케이카 비교 목록이 여기에 표시됩니다
          </p>
          <p className="text-[11px] text-zinc-600">
            상단에서 헤이딜러 URL 또는 차량번호를 입력하고 조회해 주세요.
          </p>
        </div>
      ) : kcarList.length === 0 ? (
        /* 2-3) 조회 완료 후 0건: "해당 없음" */
        <div className="p-12 flex flex-col items-center justify-center gap-2 text-zinc-400">
          <AlertCircle className="w-7 h-7 text-amber-500/80 stroke-[1.5]" />
          <p className="text-xs sm:text-sm font-bold text-zinc-200">해당 없음</p>
          <p className="text-[11px] text-zinc-500">
            검색 조건에 부합하는 케이카 비교 매물이 존재하지 않습니다.
          </p>
        </div>
      ) : (
        /* 2-4) 목록 렌더링 (가로 스크롤 보존) */
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-200">
            <thead className="bg-[#14151b] border-b border-[#262833] text-[11px] text-[#8b8e9d] uppercase font-semibold">
              <tr>
                <th className="py-2.5 px-2 text-center w-8 whitespace-nowrap">선택</th>
                <th className="py-2.5 px-2 text-center w-20 whitespace-nowrap">성능일</th>
                <th className="py-2.5 px-2 text-center w-16 whitespace-nowrap">재고일</th>
                <th className="py-2.5 px-3 min-w-[130px] whitespace-nowrap">차량명</th>
                <th className="py-2.5 px-2 text-center w-14 whitespace-nowrap">연식</th>
                <th className="py-2.5 px-2 text-right w-24 whitespace-nowrap">주행(km)</th>
                <th className="py-2.5 px-2 text-right w-20 whitespace-nowrap">가격</th>
                <th className="py-2.5 px-2 text-left w-24 whitespace-nowrap">사고유무</th>
                <th className="py-2.5 px-2 text-center w-14 whitespace-nowrap">색상</th>
                <th className="py-2.5 px-2 text-center min-w-[100px] whitespace-nowrap">옵션</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2029]">
              {kcarList.map((car, idx) => {
                const accInfo = formatKcarAccident(car.accident);
                const detailUrl = car.detailUrl || `https://www.kcar.com/bc/detail/carInfoDtl?i_sCarCd=${car.carCd}`;

                // 재고일 색상 밴드: 14일 이하 초록, 60일 이상 빨강, 그 외 노랑
                const hasHoldingDays = car.holdingDays !== undefined && car.holdingDays !== null && !isNaN(Number(car.holdingDays));
                const holdingDaysVal = Number(car.holdingDays);

                // 연식 표시: fullYear 끝 2자리, 없으면 year 끝 2자리, 없으면 '-'
                const yearText = car.fullYear
                  ? String(car.fullYear).slice(-2)
                  : car.year
                  ? String(car.year).slice(-2)
                  : '-';

                return (
                  <tr
                    key={car.carCd || idx}
                    className="hover:bg-[#161822] transition select-none"
                  >
                    {/* 1) 선택 라디오 (이번 단계에서는 표시만) */}
                    <td className="py-2 px-2 text-center whitespace-nowrap">
                      <input
                        type="radio"
                        name="kcarSelectV2"
                        disabled
                        className="text-zinc-600 bg-[#161822] border-[#262938] cursor-not-allowed opacity-50"
                        title="케이카 상세 연결은 다음 단계에서 지원됩니다."
                      />
                    </td>

                    {/* 2) 성능일 */}
                    <td className="py-2 px-2 text-center font-mono text-[11px] text-zinc-300 whitespace-nowrap">
                      {car.checkDate || '-'}
                    </td>

                    {/* 3) 재고일 (14일 이하 초록, 60일 이상 빨강, 그 외 노랑) */}
                    <td className="py-2 px-2 text-center whitespace-nowrap">
                      {hasHoldingDays ? (
                        <span
                          className={`px-1.5 py-0.5 rounded text-[11px] font-black font-mono border ${
                            holdingDaysVal <= 14
                              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                              : holdingDaysVal >= 60
                              ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                              : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                          }`}
                        >
                          {holdingDaysVal}일
                        </span>
                      ) : (
                        <span className="text-zinc-500 font-mono text-[11px]">-</span>
                      )}
                    </td>

                    {/* 4) 차량명 (자체에 원문 링크) */}
                    <td className="py-2 px-3 whitespace-nowrap">
                      <a
                        href={detailUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:underline font-bold text-white hover:text-sky-400 transition-colors inline-flex items-center gap-1 group"
                        title="새 탭에서 케이카 원문 매물 열기"
                      >
                        <span className="truncate max-w-[200px]">{car.modelName || car.carName}</span>
                        <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition shrink-0" />
                      </a>
                    </td>

                    {/* 5) 연식 */}
                    <td className="py-2 px-2 text-center font-mono text-[11px] text-zinc-300 whitespace-nowrap">
                      {yearText}
                    </td>

                    {/* 6) 주행(km) */}
                    <td className="py-2 px-2 text-right font-mono text-[11px] text-zinc-200 whitespace-nowrap">
                      {car.mileage ? `${Number(car.mileage).toLocaleString()}km` : '-'}
                    </td>

                    {/* 7) 가격 */}
                    <td className="py-2 px-2 text-right font-mono font-bold text-amber-300 text-[12px] whitespace-nowrap">
                      {car.price ? `${Number(car.price).toLocaleString()}만` : '-'}
                    </td>

                    {/* 8) 사고유무 */}
                    <td className="py-2 px-2 text-left whitespace-nowrap">
                      <span className={`text-[11px] ${accInfo.style}`}>
                        {accInfo.text}
                      </span>
                    </td>

                    {/* 9) 색상 */}
                    <td className="py-2 px-2 text-center text-[11px] text-zinc-300 whitespace-nowrap">
                      {car.color || '-'}
                    </td>

                    {/* 10) 옵션 */}
                    <td className="py-2 px-2 text-center text-[11px] text-zinc-400 whitespace-nowrap max-w-[140px] truncate" title={car.optnNm || ''}>
                      {car.optnNm && car.optnNm.trim() ? car.optnNm : '-'}
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
