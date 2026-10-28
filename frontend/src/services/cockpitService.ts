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
