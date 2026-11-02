import React, { useState, useEffect, useRef, useMemo } from 'react';
import { ExternalLink, RefreshCw, Car, AlertCircle } from 'lucide-react';
import { KcarCarItem, KcarDetailData } from '@/components/BiddingCockpit/types';
import { compareEncarItemsByBackendRule } from '@/services/cockpitService';
import { OptionItem } from '@/services/chaolmaService';
import { splitOptionString, getOptionMatchDetail, NewCarCatalogData } from '@/services/biddingOptionCatalog';

export interface ComparableKcarV2SectionProps {
  kcarList: KcarCarItem[];
  selectedCarCd?: string | null;
  onSelectCar?: (carCd: string) => void;
  yearModel?: number;
  isLoading: boolean;
  totalCount: number;
  strictCount: number;
  isInitialState: boolean;
  errorMessage?: string | null;
  kcarYearStats?: Array<{ year: number; avg: number; count: number; isTarget: boolean }>;
  kcarSearchUrl?: string;
  targetOptions?: OptionItem[];
  optionsTag?: string;
  targetCatalog?: NewCarCatalogData | null;
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
  selectedCarCd = null,
  onSelectCar,
  yearModel,
  isLoading,
  totalCount,
  strictCount,
  isInitialState,
  errorMessage,
  kcarYearStats = [],
  kcarSearchUrl,
  targetOptions,
  optionsTag,
  targetCatalog,
}) => {
  // 1. 케이카 프리패치 캐시 및 상세 맵
  const [kcarInspectionMap, setKcarInspectionMap] = useState<Record<string, KcarDetailData>>({});
  const kcarDetailCacheRef = useRef<Record<string, KcarDetailData>>({});

  // 2. 케이카 목록 준비 시 상위 20대 성능점검일·재고일 순차 프리패치 (100ms 간격, 실패는 무음 처리)
  useEffect(() => {
    if (!kcarList || kcarList.length === 0) return;

    let isCancelled = false;
    const prefetchList = kcarList.slice(0, 20);

    const runPrefetch = async () => {
      for (const car of prefetchList) {
        if (isCancelled) break;
        const cd = car.carCd;
        if (!cd || kcarDetailCacheRef.current[cd]) continue;

        try {
          const res = await fetch('/api/kcar/detail', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ carCd: cd, include3d: false }),
          });
          if (isCancelled) break;
          const json = await res.json();
          if (json.success && json.data && !isCancelled) {
            kcarDetailCacheRef.current[cd] = json.data;
            setKcarInspectionMap(prev => ({
              ...prev,
              [cd]: json.data,
            }));
          }
        } catch {
          // 백그라운드 프리패치 실패는 무음 처리하여 목록 렌더링에 영향 없도록 함
        }

        await new Promise(r => setTimeout(r, 100));
      }
    };

    runPrefetch();

    return () => {
      isCancelled = true;
    };
  }, [kcarList]);

  // 케이카 optnNm 파이프 기준 옵션 매칭 및 배지 데이터 사전 계산 (행 렌더링 최적화 Map)
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

    for (const car of kcarList) {
      if (!car.carCd) continue;

      const compOpts: string[] = (car.optnNm || '')
        .split('|')
        .map((s) => s.trim())
        .filter(Boolean);

      if (compOpts.length === 0) {
        map.set(car.carCd, {
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
        `[비교 차량 추가옵션 총 ${compOpts.length}개 · 목록 optnNm 기준]`,
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

      map.set(car.carCd, {
        hasOptions: true,
        totalCount: compOpts.length,
        symbol,
        tooltip: tooltipLines.join('\n'),
      });
    }

    return map;
  }, [kcarList, targetOptions, optionsTag, targetCatalog]);

  // 3. 프리패치 결과와 원본 목록 병합 (checkDate, holdingDays 보완) 후 백엔드 규칙(엔카와 동일)으로 정렬
  const displayKcarList = useMemo(() => {
    const merged = kcarList.map(car => {
      const det = kcarInspectionMap[car.carCd];
      if (!det) return car;

      let checkDate = det.checkDate && det.checkDate !== '-' ? det.checkDate : car.checkDate;
      const holdingDays = typeof det.holdingDays === 'number' && !isNaN(det.holdingDays) && det.holdingDays >= 0
        ? det.holdingDays
        : car.holdingDays;

      const pfmncRaw = det.dates?.pfmncDate || '';
      const pDigits = pfmncRaw.replace(/\D/g, '');
      if ((!checkDate || checkDate === '-') && pDigits.length >= 8) {
        checkDate = `${pDigits.slice(2, 4)}-${pDigits.slice(4, 6)}-${pDigits.slice(6, 8)}`;
      }

      return {
        ...car,
        checkDate: checkDate || '-',
        holdingDays: holdingDays !== undefined ? holdingDays : null,
      };
    });

    return merged.sort(compareEncarItemsByBackendRule);
  }, [kcarList, kcarInspectionMap]);

  // 4. 목표 연식 2자리 문자열 (비교용)
  const targetYrStr = yearModel ? String(yearModel % 100).padStart(2, '0') : '';

  // 5. 엄격 + 무사고 subset 필터링 및 날통계 집계 (보정 없음)
  const { summaryCount, minPrice, maxPrice, avgPrice } = useMemo(() => {
    if (!kcarList || kcarList.length === 0) {
      return { summaryCount: 0, minPrice: 0, maxPrice: 0, avgPrice: 0 };
    }

    // 1) 엄격 매물 우선 추출
    const strictCars = kcarList.filter((c) => Boolean(c.isStrict));
    const baseList = strictCars.length > 0 ? strictCars : kcarList;

    // 2) 무사고 매물 추출 (기존 formatKcarAccident 로직과 동일: 미기재 또는 '무사고' 포함)
    const noAccCars = baseList.filter((c) => {
      const acc = String(c.accidentType || '').trim();
      return !acc || acc.includes('무사고');
    });

    const targetList = noAccCars.length > 0 ? noAccCars : baseList;
    const prices = targetList
      .map((c) => Number(c.price))
      .filter((p) => !isNaN(p) && p > 0);

    const count = targetList.length;
    const minP = prices.length > 0 ? Math.min(...prices) : 0;
    const maxP = prices.length > 0 ? Math.max(...prices) : 0;
    const avgP = prices.length > 0 ? Math.round(prices.reduce((sum, cur) => sum + cur, 0) / prices.length) : 0;

    return {
      summaryCount: count,
      minPrice: minP,
      maxPrice: maxP,
      avgPrice: avgP,
    };
  }, [kcarList]);

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

      {/* 0-1. 케이카 연식별 호가 평균 칩 행 */}
      <div className="p-3 bg-[#0f1015] border border-[#1e2029] rounded-xl flex items-center gap-2.5 flex-wrap text-xs">
        <span className="text-[11px] font-bold text-rose-400 shrink-0">평균</span>
        <div className="flex items-center gap-1.5 flex-wrap">
          {kcarYearStats && kcarYearStats.length > 0 ? (
            kcarYearStats.map((st) => (
              <span
                key={st.year}
                className={`px-2 py-0.5 rounded text-[11px] font-mono flex items-center gap-1 ${
                  st.isTarget
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 font-bold'
                    : 'bg-[#1b1016] text-zinc-300 border border-[#2d1823]'
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
        {kcarSearchUrl && (
          <a
            href={kcarSearchUrl}
            target="_blank"
            rel="noreferrer"
            className="ml-auto px-1.5 py-1 rounded bg-rose-500/15 text-rose-300 border border-rose-500/35 hover:bg-rose-500/25 transition shrink-0"
            title="K-Car 필터 검색 바로가기"
          >
            <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>

      {/* 1. 케이카 비교 매물 목록 테이블 박스 */}
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
        /* 2-2) 조회 전 초기 상태 */
        <div className="p-12 flex flex-col items-center justify-center gap-3 text-zinc-500">
          <Car className="w-8 h-8 text-zinc-600 stroke-[1.5]" />
          <p className="text-xs sm:text-sm font-medium text-zinc-400">
            조회하면 케이카 비교 목록이 여기에 표시됩니다
          </p>
          <p className="text-[11px] text-zinc-600">
            상단에서 헤이딜러 URL 또는 차량번호를 입력하고 조회해 주세요.
          </p>
        </div>
      ) : displayKcarList.length === 0 ? (
        /* 2-3) 조회 완료 후 0건 */
        <div className="p-12 flex flex-col items-center justify-center gap-2 text-zinc-400">
          <AlertCircle className="w-7 h-7 text-amber-500/80 stroke-[1.5]" />
          <p className="text-xs sm:text-sm font-bold text-zinc-200">해당 없음</p>
          <p className="text-[11px] text-zinc-500">
            검색 조건에 부합하는 케이카 비교 매물이 존재하지 않습니다.
          </p>
        </div>
      ) : (
        /* 2-4) 목록 렌더링 (가로 스크롤 및 sticky thead 지원) */
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-200">
            <thead className="bg-[#14151b] border-b border-[#262833] text-[11px] text-[#8b8e9d] uppercase font-semibold sticky top-0 z-10">
              <tr>
                <th className="py-2.5 px-2 text-center w-8 whitespace-nowrap bg-[#14151b]">선택</th>
                <th className="py-2.5 px-2 text-center w-20 whitespace-nowrap bg-[#14151b]">성능일</th>
                <th className="py-2.5 px-2 text-center w-16 whitespace-nowrap bg-[#14151b]">재고일</th>
                <th className="py-2.5 px-3 whitespace-nowrap bg-[#14151b]">차량명</th>
                <th className="py-2.5 px-2 text-center w-14 whitespace-nowrap bg-[#14151b]">연식</th>
                <th className="py-2.5 px-2 text-right w-24 whitespace-nowrap bg-[#14151b]">주행(km)</th>
                <th className="py-2.5 px-2 text-right w-20 whitespace-nowrap bg-[#14151b]">가격</th>
                <th className="py-2.5 px-2 text-left w-24 whitespace-nowrap bg-[#14151b]">사고유무</th>
                <th className="py-2.5 px-2 text-center w-14 whitespace-nowrap bg-[#14151b]">색상</th>
                <th className="py-2.5 px-2 text-center min-w-[100px] whitespace-nowrap bg-[#14151b]">옵션</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2029]">
              {displayKcarList.map((car, idx) => {
                const isSelected = selectedCarCd === car.carCd;
                const accInfo = formatKcarAccident(car.accident);
                const detailUrl = car.detailUrl || `https://www.kcar.com/bc/detail/carInfoDtl?i_sCarCd=${car.carCd}`;

                // 재고일 색상 밴드: 14일 이하 초록, 60일 이상 빨강, 그 외 노랑
                const hasHoldingDays = car.holdingDays !== undefined && car.holdingDays !== null && !isNaN(Number(car.holdingDays));
                const holdingDaysVal = Number(car.holdingDays);

                // 연식 표시 (fullYear 끝 2자리, 없으면 year 끝 2자리, 없으면 '-')
                const yearText = car.fullYear
                  ? String(car.fullYear).slice(-2)
                  : car.year
                  ? String(car.year).slice(-2)
                  : '-';

                // 목표 연식과 일치 여부 판정 (일치 시 amber-300 bold)
                const regYrMatch = String(car.fullYear || car.year || '').match(/(?:20)?(\d{2})/);
                const isTargetYear = Boolean(targetYrStr && regYrMatch && regYrMatch[1] === targetYrStr);

                return (
                  <tr
                    key={car.carCd || idx}
                    onClick={() => onSelectCar && onSelectCar(car.carCd)}
                    className={`cursor-pointer transition select-none ${
                      isSelected
                        ? 'bg-blue-950/40 text-white font-medium border-l-2 border-blue-500'
                        : 'hover:bg-[#161822]'
                    }`}
                  >
                    {/* 1) 선택 라디오 (클릭 시 활성화 및 선택 강조) */}
                    <td className="py-2 px-2 text-center whitespace-nowrap">
                      <input
                        type="radio"
                        name="kcarSelectV2"
                        checked={isSelected}
                        onChange={() => onSelectCar && onSelectCar(car.carCd)}
                        className="text-blue-500 focus:ring-0 focus:ring-offset-0 bg-[#161822] border-[#262938] cursor-pointer"
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

                    {/* 4) 차량명 (자체에 원문 링크, 행 클릭과 분리) */}
                    <td className="py-2 px-3 whitespace-nowrap">
                      <a
                        href={detailUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="hover:underline font-bold text-white hover:text-sky-400 transition-colors inline-flex items-center gap-1 group"
                        title="새 탭에서 케이카 원문 매물 열기"
                      >
                        <span className="truncate max-w-[200px]">{car.modelName || car.carName}</span>
                        <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition shrink-0" />
                      </a>
                    </td>

                    {/* 5) 연식 (목표 연식 일치 시 amber-300 font-bold) */}
                    <td className="py-2 px-2 text-center font-mono text-[11px] whitespace-nowrap">
                      <span className={isTargetYear ? 'text-amber-300 font-bold' : 'text-zinc-300'}>
                        {yearText}
                      </span>
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
                    <td className="py-2 px-2 text-center whitespace-nowrap">
                      {(() => {
                        const badgeData = car.carCd ? optionBadgeMap.get(car.carCd) : null;
                        if (!badgeData || !badgeData.hasOptions) {
                          return <span className="text-zinc-500 text-[11px]">-</span>;
                        }
                        return (
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
                        );
                      })()}
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
