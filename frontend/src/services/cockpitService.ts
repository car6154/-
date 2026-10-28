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

/**
 * 콕핏 통합 검색 API (Phase 2: 단일 진실 공급원)
 * - sources: ['chaolma', 'encar', 'kcar'] 지정 호출
 * - 백엔드가 제원, 매물, 밸류에이션, 경고문 및 상태메시지를 일괄 조립하여 반환
 */
export async function searchCockpitUnified(req: CockpitSearchRequest): Promise<CockpitSearchResponse> {
  const res = await fetch('/api/cockpit/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    throw new Error(`통합 검색 서버 오류 (HTTP ${res.status})`);
  }
  return res.json();
}

/**
 * 백엔드 DataProcessor.sort_by_perf_and_year와 1:1 완벽 일치하는 단일 정렬 규칙 (Phase 3):
 * 1순위: 성능점검 유무 (점검 완료 우선, 내림차순: 1 -> 0)
 * 2순위: 성능점검일 최신순 (내림차순, 예: '24-05-10' -> '22-01-01' -> '00-00-00')
 * 3순위: 가격 낮은순 (오름차순, 결측치는 999999로 뒤로)
 * 4순위: 연식 최신순 (내림차순, 예: 2024 -> 2020)
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

  // 2순위: 성능점검일 최신순 (내림차순)
  const perfA = hasPerfA ? checkA : '00-00-00';
  const perfB = hasPerfB ? checkB : '00-00-00';
  if (perfA !== perfB) {
    return perfB.localeCompare(perfA);
  }

  // 3순위: 가격 낮은순 (오름차순, 결측치는 999999로 뒤로)
  const priceA = Number(a.price) > 0 ? Number(a.price) : 999999;
  const priceB = Number(b.price) > 0 ? Number(b.price) : 999999;
  if (priceA !== priceB) {
    return priceA - priceB;
  }

  // 4순위: 연식 최신순 (내림차순)
  const parseYearNum = (y: any): number => {
    if (typeof y === 'number') return y < 100 ? 2000 + y : y;
    const str = String(y || '').trim();
    const m = str.match(/(?:20)?(\d{2})/);
    return m ? Number('20' + m[1]) : 0;
  };
  const yrA = parseYearNum(a.year);
  const yrB = parseYearNum(b.year);
  return yrB - yrA;
}

