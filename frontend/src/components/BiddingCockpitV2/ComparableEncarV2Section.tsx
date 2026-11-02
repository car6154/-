import React, { useMemo, useState } from 'react';
import { ExternalLink, RefreshCw, Car, AlertCircle } from 'lucide-react';
import { EncarItem } from '@/components/BiddingCockpit/types';
import { OptionItem } from '@/services/chaolmaService';
import { splitOptionString, getOptionMatchDetail, NewCarCatalogData } from '@/services/biddingOptionCatalog';

export interface ComparableEncarV2SectionProps {
  encarList: EncarItem[];
  selectedEncarId: string | null;
  onSelectCar: (carId: string) => void | Promise<void>;
  isLoading: boolean;
  totalModelCount: number;
  filteredCount: number;
  isInitialState: boolean;
  targetMileageKm?: number;
  cohortNoAccAvg?: number;
  errorMessage?: string | null;
  encarYearStats?: Array<{ year: number; avg: number; count: number; isTarget: boolean }>;
  encarSourceUrl?: string;
  targetOptions?: OptionItem[];
  optionsTag?: string;
  targetCatalog?: NewCarCatalogData | null;
}

// 사고구분 라벨 헬퍼 (무사고/단순수리/사고 배지)
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

// 연식 문자열에서 2자리 연도 숫자 추출 (useBiddingCockpit encarYearStats 생성 로직과 100% 동일)
const parseYearTo2Digit = (yrStr?: string): number | null => {
  if (!yrStr) return null;
  const match = String(yrStr).trim().match(/(\d{2,4})/);
  if (!match) return null;
  const parsed = parseInt(match[1], 10);
  if (parsed > 2000) return parsed - 2000;
  if (parsed > 100) return parsed % 100;
  if (parsed > 0) return parsed;
  return null;
};

export const ComparableEncarV2Section: React.FC<ComparableEncarV2SectionProps> = ({
  encarList,
  selectedEncarId,
  onSelectCar,
  isLoading,
  totalModelCount,
  filteredCount,
  isInitialState,
  targetMileageKm = 0,
  cohortNoAccAvg = 0,
  errorMessage,
  encarYearStats = [],
  encarSourceUrl,
  targetOptions,
  optionsTag,
  targetCatalog,
}) => {
  // 세부등급 줄 표시/숨김 토글 상태 (기본값: 보임)
  const [showSubModel, setShowSubModel] = useState<boolean>(true);

  // 목표 연식(2자리) 추출 (encarYearStats의 isTarget: true 항목 기준)
  const targetYear = useMemo(() => {
    const targetStat = encarYearStats.find((st) => st.isTarget);
    return targetStat ? targetStat.year : null;
  }, [encarYearStats]);

  // 비교 차량 옵션 매칭 및 배지 데이터 사전 계산 (행 렌더링 최적화 Map)
  const optionBadgeMap = useMemo(() => {
    const map = new Map<string, {
      hasOptions: boolean;
      totalCount: number;
      symbol: '✓' | '~' | null;
      tooltip: string;
    }>();

    const targetOptNames: string[] = (targetOptions && targetOptions.length > 0)
      ? targetOptions.map((o) => o.name)
      : splitOptionString(optionsTag || '');

    for (const car of encarList) {
      const compOpts: string[] = (car.options && car.options.length > 0)
        ? car.options.map((o) => o.name)
        : splitOptionString(car.optionsText || '');

      if (compOpts.length === 0) {
        map.set(car.id, {
          hasOptions: false,
          totalCount: 0,
          symbol: null,
          tooltip: '',
        });
        continue;
      }

      const compDetails = compOpts.map((o) =>
        getOptionMatchDetail(o, targetOptNames, 'comp_vs_target', targetCatalog, undefined)
      );
      const exactCount = compDetails.filter((d) => d.confidence === 'exact').length;
      const fuzzyCount = compDetails.filter((d) => d.confidence === 'fuzzy').length;
      const commonCount = compDetails.filter((d) => d.isMatched).length;
      const extraCount = compOpts.length - commonCount;

      const symbol: '✓' | '~' | null = exactCount > 0 ? '✓' : (fuzzyCount > 0 ? '~' : null);

      const tooltipLines = [
        `[비교 차량 추가옵션 총 ${compOpts.length}개]`,
        ...compDetails.map((d, i) => {
          const o = compOpts[i];
          if (d.confidence === 'exact') return `✓ ${o} (신차 공식 일치: ${d.matchedOppositeName})`;
          if (d.confidence === 'fuzzy') return `~ ${o} (퍼지 추정 매칭: ${d.matchedOppositeName})`;
          return `+ ${o} (비교차 전용 옵션)`;
        }),
        '──────────────────────────────',
        targetOptNames.length > 0
          ? `공식 일치: ${exactCount}개 / 추정 매칭: ${fuzzyCount}개 / 비교차 전용: ${extraCount}개`
          : '내 차 옵션 정보 없음',
      ];

      map.set(car.id, {
        hasOptions: true,
        totalCount: compOpts.length,
        symbol,
        tooltip: tooltipLines.join('\n'),
      });
    }

    return map;
  }, [encarList, targetOptions, optionsTag, targetCatalog]);

  // 엄격 + 무사고 subset 필터링 및 날통계 집계 (보정 없음)
  const { summaryCount, minPrice, maxPrice, avgPrice } = useMemo(() => {
    if (!encarList || encarList.length === 0) {
      return { summaryCount: 0, minPrice: 0, maxPrice: 0, avgPrice: 0 };
    }

    // 무사고 매물 추출: accidentType에 '무사고' 포함되고 유사고/프레임사고가 아닌 매물
    const noAccCars = encarList.filter((item) => {
      const acc = String(item.accidentType || '').trim();
      if (!acc) return true;
      if (acc.includes('사고') && !acc.includes('무사고')) return false;
      return acc.includes('무사고') || acc.includes('완전무사고');
    });

    const targetList = noAccCars.length > 0 ? noAccCars : encarList;
    const prices = targetList
      .map((c) => Number(c.price))
      .filter((p) => !isNaN(p) && p > 0);

    const count = targetList.length;
    const minP = prices.length > 0 ? Math.min(...prices) : 0;
    const maxP = prices.length > 0 ? Math.max(...prices) : 0;

    // 평균가는 훅의 cohortNoAccAvg가 유효하면 그대로 사용, 없으면 subset 판매가 단순 평균
    let avgP = 0;
    if (cohortNoAccAvg && cohortNoAccAvg > 0) {
      avgP = cohortNoAccAvg;
    } else if (prices.length > 0) {
      avgP = Math.round(prices.reduce((sum, cur) => sum + cur, 0) / prices.length);
    }

    return {
      summaryCount: count,
      minPrice: minP,
      maxPrice: maxP,
      avgPrice: avgP,
    };
  }, [encarList, cohortNoAccAvg]);

  // 💡 [2026-11-01 제이 규칙]: 보정가 필드가 항목에 있으면 표시하되, 없으면 계산하지 않고 표시에서 제외(V2에서 계산 금지)
  const hasAdjustedPrice = encarList.some(
    (item) => (item as any).adjustedPrice !== undefined && (item as any).adjustedPrice !== null
  );

  return (
    <div className="space-y-3">
      {/* 0. 엄격+무사고 요약 행 (총 매물 수 · 최저가 · 최고가 · 평균가) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-3">
          <span className="text-[10px] text-zinc-400 block font-medium">총 매물 수</span>
          <div className="flex items-baseline gap-1 mt-1">
            <span className="text-lg font-black text-white font-mono">
              {summaryCount > 0 ? `${summaryCount.toLocaleString()}대` : '-'}
            </span>
            <span className="text-[10px] text-zinc-500 truncate">(무사고)</span>
          </div>
        </div>

        <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-3">
          <span className="text-[10px] text-zinc-400 block font-medium">최저가</span>
          <div className="text-lg font-black text-sky-400 font-mono mt-1 flex items-center gap-0.5">
            {minPrice > 0 ? `${minPrice.toLocaleString()}만` : '-'} <span>⬇</span>
          </div>
        </div>

        <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-3">
          <span className="text-[10px] text-zinc-400 block font-medium">최고가</span>
          <div className="text-lg font-black text-rose-400 font-mono mt-1 flex items-center gap-0.5">
            {maxPrice > 0 ? `${maxPrice.toLocaleString()}만` : '-'} <span>⬆</span>
          </div>
        </div>

        <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-3">
          <span className="text-[10px] text-zinc-400 block font-medium">평균가</span>
          <div className="text-lg font-black text-white font-mono mt-1">
            {avgPrice > 0 ? `${avgPrice.toLocaleString()}만` : '-'}
          </div>
        </div>
      </div>

      {/* 0-1. 엔카 연식별 호가 평균 칩 행 */}
      <div className="p-3 bg-[#0f1015] border border-[#1e2029] rounded-xl flex items-center gap-2.5 flex-wrap text-xs">
        <span className="text-[11px] font-bold text-sky-400 shrink-0">평균</span>
        <div className="flex items-center gap-1.5 flex-wrap">
          {encarYearStats && encarYearStats.length > 0 ? (
            encarYearStats.map((st) => (
              <span
                key={st.year}
                className={`px-2 py-0.5 rounded text-[11px] font-mono flex items-center gap-1 ${
                  st.isTarget
                    ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 font-bold'
                    : 'bg-[#151926] text-zinc-300 border border-[#20283d]'
                }`}
              >
                <span>{st.year}년</span>
                <strong className="text-white">{st.avg.toLocaleString()}만</strong>
                <span className="text-zinc-400 text-[10px]">({st.count}대)</span>
                {st.isTarget && <span className="text-[10px] text-amber-300">★</span>}
              </span>
            ))
          ) : (
            <span className="text-zinc-500 text-[11px] font-mono">-</span>
          )}
        </div>
        {encarSourceUrl && (
          <a
            href={encarSourceUrl}
            target="_blank"
            rel="noreferrer"
            className="ml-auto px-1.5 py-1 rounded bg-blue-500/15 text-sky-300 border border-blue-500/35 hover:bg-blue-500/25 transition shrink-0"
            title="엔카 필터 검색 바로가기"
          >
            <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>

      {/* 1. 엔카 비교 매물 목록 테이블 박스 */}
      <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl overflow-hidden shadow-sm space-y-0">
      {/* 1. 상단 헤더 (제목 및 매물 수) */}
      <div className="px-5 py-3.5 border-b border-[#1e2029] flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[#8b8e9d] uppercase tracking-wider">
            엔카 비교 매물
          </span>
          {!isInitialState && !isLoading && (
            <>
              <span className="text-xs px-2 py-0.5 rounded-full bg-[#1f222e] text-zinc-300 font-mono">
                전체 {totalModelCount.toLocaleString()}대 중 {filteredCount || encarList.length}대 일치
              </span>
              <button
                type="button"
                onClick={() => setShowSubModel((prev) => !prev)}
                className="text-[11px] px-2 py-0.5 rounded bg-[#161822] hover:bg-[#20283d] text-zinc-400 hover:text-zinc-200 border border-[#262938] transition cursor-pointer font-medium"
                title={showSubModel ? '세부등급 줄을 숨겨 행 높이를 축소합니다' : '세부등급 줄을 표시합니다'}
              >
                {showSubModel ? '세부등급 숨기기' : '세부등급 보기'}
              </button>
            </>
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
        /* 2-4) 목록 렌더링 (기존 칸 직관성 1:1 이전 및 가로 스크롤 보존) */
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-200">
            <thead className="bg-[#14151b] border-b border-[#262833] text-[11px] text-[#8b8e9d] uppercase font-semibold">
              <tr>
                <th className="py-2.5 px-2 text-center w-8 whitespace-nowrap">선택</th>
                <th className="py-2.5 px-2 text-center w-20 whitespace-nowrap">성능일</th>
                <th className="py-2.5 px-2 text-center w-16 whitespace-nowrap">재고일</th>
                <th className="py-2.5 px-3 whitespace-nowrap">차량명</th>
                <th className="py-2.5 px-2 text-center w-14 whitespace-nowrap">연식</th>
                <th className="py-2.5 px-2 text-right w-24 whitespace-nowrap">주행(km)</th>
                <th className="py-2.5 px-2 text-right w-20 whitespace-nowrap">가격</th>
                {hasAdjustedPrice && (
                  <th className="py-2.5 px-2 text-right w-20 whitespace-nowrap">보정가</th>
                )}
                <th className="py-2.5 px-2 text-left w-28 whitespace-nowrap">사고유무</th>
                <th className="py-2.5 px-2 text-center w-14 whitespace-nowrap">색상</th>
                <th className="py-2.5 px-2 text-center w-14 whitespace-nowrap">옵션</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2029]">
              {encarList.map((car) => {
                const isSelected = selectedEncarId === car.id;
                const accInfo = formatAccident(car.accidentType);
                const detailUrl = car.encarUrl || `https://fem.encar.com/cars/detail/${String(car.id).replace(/\D/g, '')}`;

                // 재고일 색상 밴드: 14일 이하 초록, 60일 이상 빨강, 그 외 노랑
                const hasHoldingDays = car.holdingDays !== undefined && car.holdingDays !== null && !isNaN(Number(car.holdingDays));
                const holdingDaysVal = Number(car.holdingDays);

                // 주행 차이 계산 (표시 전용)
                const hasDiff = targetMileageKm > 0;
                const diffKm = hasDiff ? car.mileage - targetMileageKm : 0;

                // 옵션 배지 데이터 조회 (Map 기반)
                const badgeData = optionBadgeMap.get(car.id);
                const hasOptions = badgeData?.hasOptions ?? false;

                // 목표 연식 일치 여부 판정 (연식 칩 ★과 동일 기준)
                const carYear2Digit = parseYearTo2Digit(car.year);
                const isTargetYear = targetYear !== null && carYear2Digit === targetYear;

                return (
                  <tr
                    key={car.id}
                    onClick={() => onSelectCar(car.id)}
                    className={`cursor-pointer transition select-none ${
                      isSelected
                        ? 'bg-blue-950/40 text-white font-medium border-l-2 border-blue-500'
                        : isTargetYear
                        ? 'bg-amber-950/20 hover:bg-amber-950/35 border-l-2 border-amber-500/70'
                        : 'hover:bg-[#161822]'
                    }`}
                  >
                    {/* 1) 선택 라디오 */}
                    <td className="py-2 px-2 text-center whitespace-nowrap">
                      <input
                        type="radio"
                        checked={isSelected}
                        onChange={() => onSelectCar(car.id)}
                        className="text-blue-500 focus:ring-0 focus:ring-offset-0 bg-[#161822] border-[#262938] cursor-pointer"
                      />
                    </td>

                    {/* 2) 성능일 */}
                    <td className="py-2 px-2 text-center font-mono text-[11px] text-zinc-300 whitespace-nowrap">
                      {car.checkDate || car.inspectionDate || '-'}
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

                    {/* 4) 차량명 (자체에 원문 링크, 클릭 전파 중단) */}
                    <td className="py-2 px-3 whitespace-nowrap">
                      <div className="flex flex-col">
                        <a
                          href={detailUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="font-bold text-sky-400 hover:text-sky-300 hover:underline transition truncate max-w-xs block"
                          title={`엔카 상세 새 창 열기 (ID: ${car.id})`}
                        >
                          {car.carName}
                        </a>
                        {showSubModel && car.subModel && (
                          <span className="text-[11px] text-zinc-400 truncate max-w-xs">
                            {car.subModel}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* 5) 연식 */}
                    <td className="py-2 px-2 text-center font-mono whitespace-nowrap">
                      <span className={isTargetYear ? 'text-amber-300 font-bold' : 'text-zinc-300'}>
                        {car.year}
                      </span>
                      {isTargetYear && (
                        <span className="ml-1 text-[10px] text-amber-400 font-bold" title="목표 연식">
                          ★
                        </span>
                      )}
                    </td>

                    {/* 6) 주행(km) 및 주행 차이 (표시 전용) */}
                    <td className="py-2 px-2 text-right font-mono whitespace-nowrap">
                      <div className="text-zinc-200 font-bold">
                        {car.mileage.toLocaleString()}km
                      </div>
                      {hasDiff && (
                        <div
                          className={`text-[10px] leading-tight pt-0.5 font-mono ${
                            diffKm === 0
                              ? 'text-zinc-400'
                              : diffKm > 0
                              ? 'text-amber-400'
                              : 'text-emerald-400'
                          }`}
                        >
                          {diffKm === 0
                            ? '동일km'
                            : diffKm > 0
                            ? `+${diffKm.toLocaleString()}km`
                            : `${diffKm.toLocaleString()}km`}
                        </div>
                      )}
                    </td>

                    {/* 7) 가격 */}
                    <td className="py-2 px-2 text-right font-mono font-bold text-amber-400 whitespace-nowrap">
                      {car.price.toLocaleString()}만
                    </td>

                    {/* 8) 보정가 (필드 존재 시에만 표시) */}
                    {hasAdjustedPrice && (
                      <td className="py-2 px-2 text-right font-mono text-sky-400 font-semibold whitespace-nowrap">
                        {(car as any).adjustedPrice !== undefined && (car as any).adjustedPrice !== null
                          ? `${Number((car as any).adjustedPrice).toLocaleString()}만`
                          : '-'}
                      </td>
                    )}

                    {/* 9) 사고유무 */}
                    <td className="py-2 px-2 text-left whitespace-nowrap">
                      <span className={`text-[11px] ${accInfo.style}`}>
                        {accInfo.text}
                      </span>
                    </td>

                    {/* 10) 색상 */}
                    <td className="py-2 px-2 text-center text-[11px] text-zinc-300 whitespace-nowrap">
                      {car.color || '-'}
                    </td>

                    {/* 11) 옵션 유무 */}
                    <td className="py-2 px-2 text-center whitespace-nowrap">
                      {hasOptions && badgeData ? (
                        <span
                          title={badgeData.tooltip}
                          className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40 text-[10.5px] cursor-help hover:bg-amber-500/30 transition inline-flex items-center gap-0.5"
                        >
                          {badgeData.symbol === '✓' && (
                            <span className="text-sky-400 text-[10px]">✓</span>
                          )}
                          {badgeData.symbol === '~' && (
                            <span className="text-amber-400 text-[10px]">~</span>
                          )}
                          <span>{badgeData.totalCount}개</span>
                        </span>
                      ) : (
                        <span className="text-zinc-500 text-[11px]">기본</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      </div>
    </div>
  );
};
