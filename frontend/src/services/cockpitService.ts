import { ChaolmaResult, OptionItem } from './chaolmaService';
import { EncarItem, KcarMarketStats } from '../components/BiddingCockpit/types';

export interface EncarValuationData {
  hasData?: boolean;
  individualPrice?: number;
  minPrice?: number;
  maxPrice?: number;
  score?: number;
  bubbleGap?: number;
  bubblePct?: number;
  safeCeiling?: number;
  [key: string]: any;
}

export interface CockpitSearchRequest {
  carNumber?: string;
  carName?: string;
  detailModel?: string;
  gradeName?: string;
  gradeDetailName?: string;
  manufacturer?: string;
  year?: number;
  mileage?: number;
  targetOptions?: string | OptionItem[];
  sources?: ('chaolma' | 'encar' | 'kcar')[];
  skipDetail?: boolean;
  encarUrl?: string;
}

export interface CockpitEncarResult {
  success: boolean;
  items: EncarItem[];
  valuation?: EncarValuationData | null;
  stats?: any;
  totalModelCount?: number;
  filteredCount?: number;
  filterStats?: any;
  directSearchUrl?: string;
  strictAdjAvg?: number;
  strictAdjMin?: number;
  strictAdjMax?: number;
  strictAdjMedian?: number;
  strictAdjCount?: number;
  strictAdjExcludedCount?: number;
  failReason?: string;
  message?: string;
  options?: OptionItem[];
}

export interface CockpitSearchResponse {
  success: boolean;
  sources: string[];
  chaolma?: ChaolmaResult | null;
  encar?: CockpitEncarResult | null;
  kcar?: KcarMarketStats | any | null;
  statusMessage?: {
    type: 'success' | 'warning' | 'error' | 'info';
    message: string;
  };
  warning?: string | null;
  failReasons?: Record<string, string>;
}

export interface UnifiedSearchOptions {
  timeoutMs?: number;
  maxRetries?: number;
}

/**
 * 콕핏 통합 검색 API (Phase 2 & 5: 단일 진실 공급원)
 * - AbortController 기반 30초 타임아웃 기본 적용
 * - 타임아웃/네트워크 단절 시 1회 자동 재시도 (4xx, 5xx HTTP 오류는 재시도 제외)
 */
export async function searchCockpitUnified(
  req: CockpitSearchRequest,
  options?: UnifiedSearchOptions
): Promise<CockpitSearchResponse> {
  const timeoutMs = options?.timeoutMs ?? 30000;
  const maxRetries = options?.maxRetries ?? 1;

  let attempt = 0;
  while (attempt <= maxRetries) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      controller.abort();
    }, timeoutMs);

    try {
      const res = await fetch('/api/cockpit/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!res.ok) {
        // 429, 403, 407, 500 등 HTTP 에러는 재시도 없이 즉시 throw
        throw new Error(`통합 검색 서버 오류 (HTTP ${res.status})`);
      }

      return await res.json();
    } catch (err: any) {
      clearTimeout(timeoutId);

      const isAbort = err?.name === 'AbortError' || controller.signal.aborted;
      const isHttpError = err?.message && err.message.includes('통합 검색 서버 오류 (HTTP');

      // 4xx, 5xx HTTP 에러는 절대 재시도하지 않음
      if (isHttpError) {
        throw err;
      }

      const isNetworkError = err instanceof TypeError && (
        err.message.includes('fetch') ||
        err.message.includes('network') ||
        err.message.includes('Failed to fetch')
      );

      // 타임아웃 또는 네트워크 단절 시에만 1회 재시도
      if ((isAbort || isNetworkError) && attempt < maxRetries) {
        attempt++;
        console.warn(`[searchCockpitUnified] ${isAbort ? '요청 시간 초과(30초)' : '네트워크 연결 오류'} 감지 -> 1회 자동 재시도 시작 (시도 ${attempt}/${maxRetries})`);
        continue;
      }

      if (isAbort) {
        const timeoutErr = new Error('요청 시간 초과 (30초 동안 응답이 없습니다)');
        (timeoutErr as any).isTimeout = true;
        throw timeoutErr;
      }

      throw err;
    }
  }

  const finalTimeoutErr = new Error('요청 시간 초과 (재시도 실패)');
  (finalTimeoutErr as any).isTimeout = true;
  throw finalTimeoutErr;
}

/**
 * 백엔드 DataProcessor.sort_by_perf_and_year와 1:1 완벽 일치하는 단일 정렬 규칙:
 * 1순위: 성능점검 유무 (점검 완료 우선, 내림차순: 1 -> 0)
 * 2순위: 연식 최신순 (내림차순, 예: 2024 -> 2020)
 * 3순위: 성능점검일 최신순 (내림차순, 예: '24-05-10' -> '22-01-01' -> '00-00-00')
 * 4순위: 가격 낮은순 (오름차순, 결측치는 999999로 뒤로)
 */
export function compareEncarItemsByBackendRule(a: any, b: any): number {
  const isNormalPerf = (d: any): boolean => {
    if (!d) return false;
    const str = String(d).trim();
    if (['미검사/사진', '⚠️미등록', '⚠️조회실패', '-'].includes(str)) return false;
    return /^\d{2}-\d{2}-\d{2}/.test(str);
  };

  const checkA = String(a.checkDate || a.inspectionDate || (a as any).성능일 || '').trim();
  const checkB = String(b.checkDate || b.inspectionDate || (b as any).성능일 || '').trim();

  const hasPerfA = isNormalPerf(checkA) ? 1 : 0;
  const hasPerfB = isNormalPerf(checkB) ? 1 : 0;

  // 1순위: 점검 완료 우선 (내림차순)
  if (hasPerfA !== hasPerfB) {
    return hasPerfB - hasPerfA;
  }

  // 2순위: 연식 최신순 (내림차순)
  const parseYearNum = (y: any): number => {
    if (typeof y === 'number') return y < 100 ? 2000 + y : y;
    const str = String(y || '').trim();
    const m = str.match(/(?:20)?(\d{2})/);
    return m ? Number('20' + m[1]) : 0;
  };
  const yrA = parseYearNum(a.regYear ?? a.year);
  const yrB = parseYearNum(b.regYear ?? b.year);
  if (yrA !== yrB) {
    return yrB - yrA;
  }

  // 3순위: 성능점검일 최신순 (내림차순)
  const perfA = hasPerfA ? checkA : '00-00-00';
  const perfB = hasPerfB ? checkB : '00-00-00';
  if (perfA !== perfB) {
    return perfB.localeCompare(perfA);
  }

  // 4순위: 가격 낮은순 (오름차순, 결측치는 999999로 뒤로)
  const priceA = Number(a.price) > 0 ? Number(a.price) : 999999;
  const priceB = Number(b.price) > 0 ? Number(b.price) : 999999;
  return priceA - priceB;
}


