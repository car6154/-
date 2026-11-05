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

  for (const car of cars) {
    const carId = String(car.id).trim();
    const cacheKey = car.grade ? `${carId}_grade:${car.grade.trim()}` : carId;
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
        const cacheKey = car.grade ? `${carId}_grade:${car.grade.trim()}` : carId;
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

/**
 * 문자열 정규화 (공백, 특수문자 제거, 소문자화)
 */
export function normalizeOptionName(name: string): string {
  if (!name) return '';
  return name.replace(/[^a-zA-Z0-9가-힣]/g, '').toLowerCase();
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
