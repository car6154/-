/**
 * 옵션 매칭 엔진 백엔드 단일화 공유 서비스 (깔때기 3단계)
 * - 카탈로그 진실(공식명·가격·출처·매칭연식)은 Python 백엔드(/api/encar/match-options, match-options-batch)만 담당
 * - 프론트엔드는 대조 표시(✓/~ /+)와 패키지 안내 UI 렌더링만 담당
 */

export interface BackendMatchedOption {
  raw_name: string;
  clean_name: string;
  official_name: string;
  price: number | null;
  desc?: string;
  match_type: 'exact' | 'fuzzy' | 'none';
  source: 'danawa' | 'encar' | 'none';
  matched_year?: string;
}

export interface BatchCarInput {
  id: string;
  carName: string;
  year: number | string;
  optionsList?: string[];
  optionsText?: string;
  grade?: string;
}

// 차량 id (또는 고유 캐시 키) 기준 매칭 결과 메모리 캐시
const optionMatchCache = new Map<string, BackendMatchedOption[]>();

// 진행 중인 단건 호출 Promise 공유
const inFlightSingleMap = new Map<string, Promise<BackendMatchedOption[]>>();

/**
 * 단건 옵션 카탈로그 표준명 매칭 (SelectedCarDetailV2Section, Sidebar 목표차 등)
 */
export async function matchOptionsSingle(car: {
  id?: string;
  carName: string;
  year: number | string;
  optionsList?: string[];
  optionsText?: string;
  grade?: string;
}): Promise<BackendMatchedOption[]> {
  const rawList = car.optionsList || [];
  const rawText = car.optionsText || '';
  const cleanListStr = rawList.join('|');
  const gradePart = car.grade ? `_grade:${car.grade.trim()}` : '';
  const cacheKey = car.id
    ? `${car.id}_${car.carName}_${car.year}${gradePart}_${cleanListStr || rawText}`
    : `${car.carName}_${car.year}${gradePart}_${cleanListStr || rawText}`;

  if (optionMatchCache.has(cacheKey)) {
    return optionMatchCache.get(cacheKey)!;
  }

  if (inFlightSingleMap.has(cacheKey)) {
    return inFlightSingleMap.get(cacheKey)!;
  }

  const promise = (async () => {
    try {
      const payload: Record<string, any> = {
        carName: car.carName,
        year: car.year,
        optionsList: rawList,
        optionsText: rawText,
      };
      if (car.grade && car.grade.trim()) {
        payload.grade = car.grade.trim();
      }

      const res = await fetch('/api/encar/match-options', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        optionMatchCache.delete(cacheKey);
        return [];
      }

      const data = await res.json();
      if (data && data.success && Array.isArray(data.data)) {
        optionMatchCache.set(cacheKey, data.data);
        return data.data as BackendMatchedOption[];
      }

      optionMatchCache.delete(cacheKey);
      return [];
    } catch (e) {
      console.warn('[optionMatchingService] 단건 매칭 실패:', e);
      optionMatchCache.delete(cacheKey);
      return [];
    } finally {
      inFlightSingleMap.delete(cacheKey);
    }
  })();

  inFlightSingleMap.set(cacheKey, promise);
  return promise;
}

/**
 * 다수 차량 옵션 카탈로그 표준명 매칭 배치 함수 (ComparableEncarV2Section, ComparableKcarV2Section 등)
 * - 이미 캐시된 차량은 캐시에서 즉시 반환
 * - 미캐시 차량들만 모아 백엔드 /api/encar/match-options-batch로 1회 요청
 * - 실패한 id는 캐시에 남기지 않아 재조회 시 재요청
 */
export async function matchOptionsBatch(
  cars: BatchCarInput[]
): Promise<Record<string, BackendMatchedOption[]>> {
  if (!cars || cars.length === 0) return {};

  const results: Record<string, BackendMatchedOption[]> = {};
  const uncachedCars: BatchCarInput[] = [];

  const buildBatchCacheKey = (car: BatchCarInput) => {
    const carId = String(car.id).trim();
    const gradePart = car.grade ? `_grade:${car.grade.trim()}` : '';
    const optPart = (car.optionsList && car.optionsList.length > 0)
      ? car.optionsList.join('|')
      : (car.optionsText || '');
    return `${carId}${gradePart}_${optPart}`;
  };

  for (const car of cars) {
    const carId = String(car.id).trim();
    const cacheKey = buildBatchCacheKey(car);
    if (optionMatchCache.has(cacheKey)) {
      results[carId] = optionMatchCache.get(cacheKey)!;
    } else {
      uncachedCars.push(car);
    }
  }

  if (uncachedCars.length === 0) {
    return results;
  }

  try {
    const res = await fetch('/api/encar/match-options-batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cars: uncachedCars.map((c) => {
          const item: Record<string, any> = {
            id: String(c.id).trim(),
            carName: c.carName,
            year: c.year,
            optionsList: c.optionsList || [],
            optionsText: c.optionsText || '',
          };
          if (c.grade && c.grade.trim()) {
            item.grade = c.grade.trim();
          }
          return item;
        }),
      }),
    });

    if (!res.ok) {
      console.warn('[optionMatchingService] 배치 매칭 HTTP 오류:', res.status);
      return results;
    }

    const data = await res.json();
    if (data && data.success && data.data) {
      for (const car of uncachedCars) {
        const carId = String(car.id).trim();
        const cacheKey = buildBatchCacheKey(car);
        const matchedList = data.data[carId];
        if (Array.isArray(matchedList) && matchedList.length > 0) {
          optionMatchCache.set(cacheKey, matchedList as BackendMatchedOption[]);
          results[carId] = matchedList as BackendMatchedOption[];
        }
      }
    }
  } catch (e) {
    console.warn('[optionMatchingService] 배치 매칭 조회 실패:', e);
  }

  return results;
}

/**
 * 캐시에서 특정 차량의 옵션 매칭 결과 동기적 조회 (이미 배치 조회된 결과 재사용용)
 */
export function getCachedCarMatchedOptions(carId: string): BackendMatchedOption[] | null {
  return optionMatchCache.get(String(carId).trim()) || null;
}

const ROMAN_MAP: Record<string, string> = {
  'Ⅰ': '1', 'Ⅱ': '2', 'Ⅲ': '3', 'Ⅳ': '4', 'Ⅴ': '5',
  'Ⅵ': '6', 'Ⅶ': '7', 'Ⅷ': '8', 'Ⅸ': '9', 'Ⅹ': '10',
  'ⅰ': '1', 'ⅱ': '2', 'ⅲ': '3', 'ⅳ': '4', 'ⅴ': '5',
  'ⅵ': '6', 'ⅶ': '7', 'ⅷ': '8', 'ⅸ': '9', 'ⅹ': '10',
};

/**
 * 문자열 정규화 (로마 숫자 통일 후 공백·특수문자 제거, 소문자화)
 */
export function normalizeOptionName(name: string): string {
  if (!name) return '';
  let s = String(name);
  for (const [rk, rv] of Object.entries(ROMAN_MAP)) {
    if (s.includes(rk)) {
      s = s.split(rk).join(rv);
    }
  }
  s = s.replace(/(?<=[가-힣\s])III(?=\b|$|\s|\()/g, '3');
  s = s.replace(/(?<=[가-힣\s])II(?=\b|$|\s|\()/g, '2');
  s = s.replace(/(?<=[가-힣\s])IV(?=\b|$|\s|\()/g, '4');
  s = s.replace(/(?<=[가-힣\s])I(?=\b|$|\s|\()/g, '1');
  return s.replace(/[^a-zA-Z0-9가-힣]/g, '').toLowerCase();
}

export type OptionCompareSymbol = '✓' | '~' | '+';

export interface OptionCompareDetail {
  symbol: OptionCompareSymbol;
  confidence: 'exact' | 'fuzzy' | 'none';
  matchedName: string;
  matchedOption?: BackendMatchedOption;
}

/**
 * 글자 바이그램 집합 추출
 */
function getBigrams(str: string): Set<string> {
  const s = new Set<string>();
  for (let i = 0; i < str.length - 1; i++) {
    s.add(str.slice(i, i + 2));
  }
  return s;
}

/**
 * 글자 바이그램 자카드 유사도 (0.0 ~ 1.0)
 */
function bigramJaccard(str1: string, str2: string): number {
  if (str1 === str2) return 1.0;
  if (str1.length < 2 || str2.length < 2) return 0.0;
  const b1 = getBigrams(str1);
  const b2 = getBigrams(str2);
  let intersection = 0;
  for (const b of b1) {
    if (b2.has(b)) intersection++;
  }
  const union = b1.size + b2.size - intersection;
  return union === 0 ? 0.0 : intersection / union;
}

/**
 * 문자열에서 숫자 묶음(소수점 포함) 추출
 */
function extractNumberGroups(str: string): string[] {
  const matches = str.match(/\d+(?:\.\d+)?/g);
  return matches || [];
}

/**
 * 대조 규칙 4-d 구현 및 11-03-14 승격 규칙 적용:
 * - 양쪽 옵션의 백엔드 official_name이 같으면 ✓ (exact)
 * - 정규화 이름 완전 일치 시 ✓ (exact)
 * - [11-03-14 승격 규칙]: 완전 일치가 아니더라도 아래 4개 조건을 모두 만족하면 ✓로 승격:
 *   (a) 이름 유사: 정규화 이름 기준 짧은 쪽이 긴 쪽에 포함되거나 바이그램 자카드 0.7 이상
 *   (b) 양쪽 가격이 둘 다 있음 (매칭 항목 price > 0)
 *   (c) 가격 차이 10만 원(100,000원) 이내
 *   (d) 숫자 가드: 양쪽 이름에서 추출한 숫자 묶음이 둘 다 있고 다르면 승격하지 않음 (10.25 vs 12.3 등)
 * - 그 외 정규화 상호 포함 관계면 ~ (fuzzy)
 * - 그 외 + (none)
 */
export function compareOptionToOpposites(
  target: BackendMatchedOption | string,
  opposites: (BackendMatchedOption | string)[]
): OptionCompareDetail {
  const getOptNames = (opt: BackendMatchedOption | string) => {
    if (typeof opt === 'string') {
      const clean = opt.replace(/\s+/g, ' ').trim();
      return { official: '', clean, raw: opt };
    }
    return {
      official: (opt.official_name || '').trim(),
      clean: (opt.clean_name || opt.raw_name || '').trim(),
      raw: opt.raw_name || '',
    };
  };

  const tgt = getOptNames(target);
  const tgtStd = tgt.official || tgt.clean || tgt.raw;
  const normTgtStd = normalizeOptionName(tgtStd);

  // 1. 정확 일치 (✓) 검사: official_name이 같거나 정규화 이름이 완전 일치
  for (const opp of opposites) {
    const oppNames = getOptNames(opp);
    const oppStd = oppNames.official || oppNames.clean || oppNames.raw;

    if (tgt.official && oppNames.official && tgt.official === oppNames.official) {
      return {
        symbol: '✓',
        confidence: 'exact',
        matchedName: oppStd,
        matchedOption: typeof opp !== 'string' ? opp : undefined,
      };
    }

    if (normTgtStd && normTgtStd === normalizeOptionName(oppStd)) {
      return {
        symbol: '✓',
        confidence: 'exact',
        matchedName: oppStd,
        matchedOption: typeof opp !== 'string' ? opp : undefined,
      };
    }
  }

  // 2. [11-03-14 승격 규칙]: 완전 일치가 아닐 때 4가지 조건 만족 시 ✓로 승격
  for (const opp of opposites) {
    const oppNames = getOptNames(opp);
    const oppStd = oppNames.official || oppNames.clean || oppNames.raw;
    const normOppStd = normalizeOptionName(oppStd);

    // (b) 양쪽 가격이 둘 다 있다 (매칭 항목의 price, 원 단위). 원문 문자열이라 가격이 없으면 승격하지 않는다.
    if (typeof target !== 'object' || typeof opp !== 'object') continue;
    if (typeof target.price !== 'number' || typeof opp.price !== 'number') continue;
    if (target.price <= 0 || opp.price <= 0) continue;

    // (c) 가격 차이 10만 원(100,000원) 이내
    if (Math.abs(target.price - opp.price) > 100000) continue;

    // (d) 숫자 가드: 양쪽 이름에서 추출한 숫자 묶음이 둘 다 있고 다르면 승격하지 않는다 (10.25인치와 12.3인치 등).
    const nums1 = extractNumberGroups(tgtStd || tgt.raw);
    const nums2 = extractNumberGroups(oppStd || oppNames.raw);
    if (nums1.length > 0 && nums2.length > 0) {
      if (nums1.join(',') !== nums2.join(',')) continue;
    }

    // (a) 이름 유사: 정규화 이름 기준, 짧은 쪽이 긴 쪽에 포함되거나 글자 바이그램 자카드 0.7 이상
    if (!normTgtStd || !normOppStd) continue;
    const shorter = normTgtStd.length <= normOppStd.length ? normTgtStd : normOppStd;
    const longer = normTgtStd.length <= normOppStd.length ? normOppStd : normTgtStd;
    const isSubstring = longer.includes(shorter);
    const jaccardScore = bigramJaccard(normTgtStd, normOppStd);

    if (isSubstring || jaccardScore >= 0.7) {
      return {
        symbol: '✓',
        confidence: 'exact',
        matchedName: oppStd,
        matchedOption: opp,
      };
    }
  }

  // 3. 퍼지 추정 매칭 (~) 검사: 정규화 문자열 상호 포함 관계
  if (normTgtStd && normTgtStd.length >= 2) {
    for (const opp of opposites) {
      const oppNames = getOptNames(opp);
      const oppStd = oppNames.official || oppNames.clean || oppNames.raw;
      const normOppStd = normalizeOptionName(oppStd);

      if (normOppStd && normOppStd.length >= 2) {
        if (normTgtStd.includes(normOppStd) || normOppStd.includes(normTgtStd)) {
          return {
            symbol: '~',
            confidence: 'fuzzy',
            matchedName: oppStd,
            matchedOption: typeof opp !== 'string' ? opp : undefined,
          };
        }
      }
    }
  }

  // 4. 미매칭 / 전용 옵션 (+)
  return {
    symbol: '+',
    confidence: 'none',
    matchedName: '',
  };
}

// ═══════════════════════════════════════════════════════════════
// 💡 [11-06-69]: 엔카·케이카 옵션 툴팁·라벨·개수 공용 단일화 엔진
// ═══════════════════════════════════════════════════════════════

/**
 * 옵션 개수 산출 공용 함수 (가격 있는 유료 선택옵션만 카운트, 기본옵션/0원/미확인 제외)
 * - 엔카·케이카·사이드바·목록 전부 동일한 단일 진실 로직 적용
 */
export function countPricedOptions(
  items?: Array<{ price?: number | null; price_man?: number | null } | BackendMatchedOption | any> | null
): number {
  if (!items || !Array.isArray(items)) return 0;
  return items.filter((item) => {
    if (!item) return false;
    const p = typeof item.price === 'number' ? item.price : 0;
    const pMan = typeof item.price_man === 'number' ? item.price_man : 0;
    return p > 0 || pMan > 0;
  }).length;
}

/**
 * 옵션 단건 툴팁 포맷팅 공용 함수 (단일 진실 공급원)
 * - 1행: "신차가격표: 옵션명 (가격)"
 * - 2행: desc가 있으면 항상 표시 (단, '설명 없음', '미확인' 등 무의미 텍스트 제외)
 * - 3행: 원문과 공식명이 다르면 "원문: 원문명"
 */
export function formatOptionTooltip(params: {
  officialName?: string;
  cleanName?: string;
  rawName?: string;
  price?: number | null;
  price_man?: number | null;
  desc?: string;
}): string {
  const stdName = params.officialName || params.cleanName || params.rawName || '';
  const pMan = typeof params.price_man === 'number' && params.price_man > 0
    ? params.price_man
    : (typeof params.price === 'number' && params.price > 0 ? Math.round(params.price / 10000) : 0);
  const priceStr = pMan > 0 ? ` (${pMan.toLocaleString()}만원)` : '';

  const lines: string[] = [`신차가격표: ${stdName}${priceStr}`];

  // desc가 있으면 바로 다음 줄에 표시 (단, '설명 없음' 등 무의미 텍스트 제외)
  const cleanDesc = (params.desc || '').trim();
  if (cleanDesc && cleanDesc !== '설명 없음' && cleanDesc !== '미확인') {
    lines.push(cleanDesc);
  }

  // 원문과 공식명이 다를 때 원문 표시
  if (params.rawName && params.rawName !== stdName && params.rawName !== params.officialName) {
    lines.push(`원문: ${params.rawName}`);
  }

  return lines.join('\n');
}

export interface FormattedOptionChip {
  origIdx: number;
  rawName: string;
  displayName: string;
  priceStr: string;
  priceMan: number;
  titleText: string;
  symbol: '✓' | '~' | '+';
  symbolRank: number;
  chipStyle: string;
}

/**
 * 상세 패널(SelectedCarDetailV2Section / SelectedKcarDetailV2Section) 옵션 칩 구성 공용 함수
 * - 가격 있는 선택옵션만 선별하거나, 가격 있는 옵션 우선 정렬
 * - formatOptionTooltip을 사용하여 desc가 항상 포함된 툴팁 생성
 * - compareOptionToOpposites로 일치(✓)/추정(~)/전용(+) 배지 및 색상 통일
 */
export function buildOptionChips(
  rawOptionNames: string[],
  matchedList: BackendMatchedOption[],
  targetMatchedList: (BackendMatchedOption | string)[],
  filterPricedOnly: boolean = false
): {
  chips: FormattedOptionChip[];
  pricedCount: number;
  totalPriceMan: number;
} {
  const mapped: FormattedOptionChip[] = rawOptionNames.map((rawName, origIdx) => {
    const mi = matchedList.find((m) => m.raw_name === rawName);
    const stdName = mi?.official_name || mi?.clean_name || rawName;
    const priceMan = mi?.price ? Math.round(mi.price / 10000) : 0;
    const priceStr = priceMan > 0 ? ` (${priceMan.toLocaleString()}만원)` : '';

    const titleText = formatOptionTooltip({
      officialName: mi?.official_name,
      cleanName: mi?.clean_name,
      rawName,
      price: mi?.price,
      desc: mi?.desc,
    });

    const compareRes = compareOptionToOpposites(mi || rawName, targetMatchedList);
    const symbol = compareRes.symbol; // '✓' | '~' | '+'
    const symbolRank = symbol === '✓' ? 1 : symbol === '~' ? 2 : 3;

    let chipStyle = 'bg-orange-500/30 text-orange-300 border-orange-500/60 font-bold';
    if (symbol === '✓') {
      chipStyle = 'bg-emerald-500/30 text-emerald-300 border-emerald-500/60 font-bold';
    } else if (symbol === '~') {
      chipStyle = 'bg-amber-500/30 text-amber-300 border-amber-500/60 font-bold';
    }

    return {
      origIdx,
      rawName,
      displayName: stdName,
      priceStr,
      priceMan,
      titleText,
      symbol,
      symbolRank,
      chipStyle,
    };
  });

  const pricedChips = mapped.filter((c) => c.priceMan > 0);
  const pricedCount = pricedChips.length;
  const totalPriceMan = pricedChips.reduce((sum, c) => sum + c.priceMan, 0);

  // filterPricedOnly가 true이면 유료 옵션만 반환 (케이카의 45개 기본옵션 등 필터링)
  // 단, 유료 옵션이 0개면 원본 칩 목록 유지
  const targetChips = (filterPricedOnly && pricedCount > 0) ? pricedChips : mapped;

  // 공식 일치(✓) -> 추정(~) -> 전용(+) 순 정렬 (그룹 내 원문 순서 유지)
  const sortedChips = targetChips.slice().sort((a, b) => a.symbolRank - b.symbolRank || a.origIdx - b.origIdx);

  return {
    chips: sortedChips,
    pricedCount,
    totalPriceMan,
  };
}

/**
 * 비교 목록(ComparableEncarV2Section / ComparableKcarV2Section) 옵션 요약 정보 생성 공용 함수
 * - 엔카·케이카 동일 양식 및 동일 툴팁 규칙 적용
 * - 가격 있는 선택옵션만 세고 기본옵션 제외 (케이카의 45개 기본옵션 문제 해결)
 * - 옵션별 툴팁에 desc 설명 포함
 */
export function buildComparableOptionsSummary(
  rawOptionNames: string[],
  compMatchedList: BackendMatchedOption[],
  targetMatchedList: (BackendMatchedOption | string)[],
  targetOptNamesCount: number
): {
  hasOptions: boolean;
  totalCount: number;
  pricedCount: number;
  symbol: '✓' | '~' | null;
  tooltip: string;
} {
  if (!rawOptionNames || rawOptionNames.length === 0) {
    return {
      hasOptions: false,
      totalCount: 0,
      pricedCount: 0,
      symbol: null,
      tooltip: '',
    };
  }

  const compDetails = rawOptionNames.map((o) => {
    const matchedItem = compMatchedList.find((m) => m.raw_name === o);
    const compTarget = matchedItem || o;
    const compareRes = compareOptionToOpposites(compTarget, targetMatchedList);
    return {
      raw: o,
      matchedItem,
      compareRes,
    };
  });

  // 가격 있는 유료 선택옵션만 추출 (케이카의 45개 기본옵션 등 필터링)
  const pricedDetails = compDetails.filter((d) => {
    if (!d.matchedItem) return false;
    const p = typeof d.matchedItem.price === 'number' ? d.matchedItem.price : 0;
    return p > 0;
  });

  // 매칭 전이거나 유료옵션이 없는 경우 전체 리스트를 fallback으로 하되 유료 옵션 우선
  const effectiveDetails = pricedDetails.length > 0 ? pricedDetails : compDetails;
  const pricedCount = pricedDetails.length;

  const exactCount = effectiveDetails.filter((d) => d.compareRes.symbol === '✓').length;
  const fuzzyCount = effectiveDetails.filter((d) => d.compareRes.symbol === '~').length;
  const extraCount = effectiveDetails.length - (exactCount + fuzzyCount);

  const symbol: '✓' | '~' | null = exactCount > 0 ? '✓' : (fuzzyCount > 0 ? '~' : null);

  const headerTitle = pricedCount > 0
    ? `[비교 차량 추가옵션 총 ${pricedCount}개 (신차가격표 기준)]`
    : `[비교 차량 옵션 총 ${rawOptionNames.length}개]`;

  const tooltipLines = [
    headerTitle,
    ...effectiveDetails.map((d) => {
      const o = d.raw;
      const mi = d.matchedItem;
      const stdName = mi?.official_name || mi?.clean_name || o;
      const pMan = mi?.price ? Math.round(mi.price / 10000) : 0;
      const priceLabel = pMan > 0 ? ` (${pMan.toLocaleString()}만원)` : '';
      const detailLabel = `${stdName}${priceLabel}`;

      let line = '';
      if (d.compareRes.symbol === '✓') {
        line = `✓ ${o} (신차가격표: ${detailLabel})`;
      } else if (d.compareRes.symbol === '~') {
        line = `~ ${o} (신차가격표 추정: ${detailLabel})`;
      } else {
        line = mi && mi.official_name
          ? `+ ${o} (신차가격표: ${detailLabel})`
          : `+ ${o} (비교차 전용 옵션)`;
      }

      // desc가 있으면 다음 줄에 들여쓰기로 표시
      const cleanDesc = (mi?.desc || '').trim();
      if (cleanDesc && cleanDesc !== '설명 없음' && cleanDesc !== '미확인') {
        line = `${line}\n  └ ${cleanDesc}`;
      }
      return line;
    }),
    '──────────────────────────────',
    targetOptNamesCount > 0
      ? `공식 일치: ${exactCount}개 / 추정 매칭: ${fuzzyCount}개 / 비교차 전용: ${extraCount}개`
      : '내 차 옵션 정보 없음',
  ];

  return {
    hasOptions: true,
    totalCount: pricedCount > 0 ? pricedCount : rawOptionNames.length,
    pricedCount,
    symbol,
    tooltip: tooltipLines.join('\n'),
  };
}
