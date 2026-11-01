import { outerParts, innerParts, matchesDamagePart, DamagePart } from '@/components/BiddingCockpit/Sections/CarDamageDiagram2D';
import { HD_PART_MAP } from '@/services/biddingOptionCatalog';

export interface AccidentDepreciationInput {
  repairs?: any[] | null;
  accidentType?: string;
  isAccidentKnown?: boolean;
  basePriceMan: number; // 감가 전 카드값 (aiRetailPrice, 만원)
}

export interface PartDepreciationDetail {
  rawPart: string;
  matchedPartCode: string;
  koreanName: string;
  category: 'OUTER' | 'FRAME' | 'BUMPER' | 'UNKNOWN';
  repairType: 'EXCHANGE' | 'SHEET_METAL' | 'UNKNOWN';
  rate: number;
  minPriceMan: number;
  amountMan: number;
  note?: string;
}

export interface AccidentDepreciationResult {
  hasKnownHistory: boolean;
  isAccidentFree: boolean;
  totalDepreciationMan: number;
  itemDetails: PartDepreciationDetail[];
  unknownParts: string[];
}

/**
 * 부위 명칭 정규화
 * - HD_PART_MAP 변환
 * - 운전석/조수석 -> 좌/우 치환
 * - driver/passenger -> left/right 치환
 */
export function normalizePartName(rawPart: string): string {
  if (!rawPart) return '';
  let s = String(rawPart).trim().toLowerCase();

  // 1. HD_PART_MAP 직접 일치 변환
  if (HD_PART_MAP[s]) {
    s = HD_PART_MAP[s].toLowerCase();
  }

  // 2. 운전석/조수석 -> 좌/우 치환
  s = s.replace(/운전석/g, '좌').replace(/조수석/g, '우');
  // driver -> left, passenger -> right
  s = s.replace(/driver/g, 'left').replace(/passenger/g, 'right');

  return s;
}

/**
 * CarDamageDiagram2D 외판/골격 부위 목록 기준 부위 판정
 */
export function resolvePartCategory(rawPart: string): {
  category: 'OUTER' | 'FRAME' | 'BUMPER' | 'UNKNOWN';
  matchedPart?: DamagePart;
} {
  const rawLower = String(rawPart || '').toLowerCase().trim();
  const norm = normalizePartName(rawPart);

  // 1. 범퍼 우선 판정 (범퍼는 감가 0원)
  if (rawLower.includes('bumper') || norm.includes('범퍼')) {
    return { category: 'BUMPER' };
  }

  // 다양한 표기 변형 후보 생성
  const enReplaced = rawLower.replace(/driver/g, 'left').replace(/passenger/g, 'right');
  const hdMapped = HD_PART_MAP[rawLower] ? HD_PART_MAP[rawLower].toLowerCase() : '';
  const hdReplaced = hdMapped ? hdMapped.replace(/운전석/g, '좌').replace(/조수석/g, '우') : '';

  const candidates = Array.from(new Set([rawPart, rawLower, enReplaced, hdMapped, hdReplaced, norm].filter(Boolean)));

  // 2. 외판 판정 (outerParts: 14개)
  for (const part of outerParts) {
    if (candidates.some(c => matchesDamagePart(part, c))) {
      return { category: 'OUTER', matchedPart: part };
    }
  }

  // 3. 골격 판정 (innerParts: 20개)
  for (const part of innerParts) {
    if (candidates.some(c => matchesDamagePart(part, c))) {
      return { category: 'FRAME', matchedPart: part };
    }
  }

  return { category: 'UNKNOWN' };
}

/**
 * 수리/교환 상태 판정 (교환 vs 판금/용접)
 */
export function resolveRepairType(rawRepair: string): 'EXCHANGE' | 'SHEET_METAL' | 'UNKNOWN' {
  const s = String(rawRepair || '').trim().toLowerCase();
  if (s.includes('exchange') || s.includes('replace') || s.includes('교환')) {
    return 'EXCHANGE';
  }
  if (s.includes('sheet_metal') || s.includes('weld') || s.includes('판금') || s.includes('용접')) {
    return 'SHEET_METAL';
  }
  return 'UNKNOWN';
}

/**
 * 목표차 사고 부품별 감가 계산 (제이 최종 확정 감가 일정)
 * - 부품당 감가 = max(원화 하한, % × 가격)
 * - 외판 교환·판금: 3.5% · 하한 35만원
 * - 골격 판금: 5.0% · 하한 50만원
 * - 골격 교체: 6.5% · 하한 65만원
 * - 범퍼: 0원
 * - 세 항목 전환점: 모두 1,000만원
 * - 가격 기준: 감가 전 카드값 (aiRetailPrice, 만원)
 */
export function calculateAccidentDepreciation(input: AccidentDepreciationInput): AccidentDepreciationResult {
  const { repairs, accidentType, isAccidentKnown, basePriceMan } = input;

  const hasArray = Array.isArray(repairs);
  const hasAccType = Boolean(accidentType && accidentType.trim() !== '' && accidentType.trim() !== '-');

  // 1. 교환 내역 정보가 아예 없는(모르는) 경우: 감가하지 않고 빈칸으로 둠
  if (!hasArray && !hasAccType && !isAccidentKnown) {
    return {
      hasKnownHistory: false,
      isAccidentFree: false,
      totalDepreciationMan: 0,
      itemDetails: [],
      unknownParts: []
    };
  }

  // 2. 알려진 무사고 판정 (감가 0원)
  const isDeclaredAccidentFree = Boolean(
    (accidentType && (accidentType.includes('무사고') || accidentType.includes('완무') || accidentType.toLowerCase() === 'none')) &&
    (!hasArray || repairs.length === 0)
  );

  if (isDeclaredAccidentFree) {
    return {
      hasKnownHistory: true,
      isAccidentFree: true,
      totalDepreciationMan: 0,
      itemDetails: [],
      unknownParts: []
    };
  }

  // 3. 수리 목록이 비어 있거나 없는 경우
  if (!hasArray || repairs.length === 0) {
    return {
      hasKnownHistory: Boolean(isAccidentKnown || hasAccType),
      isAccidentFree: false,
      totalDepreciationMan: 0,
      itemDetails: [],
      unknownParts: []
    };
  }

  // 4. 수리/교환 목록이 있을 때 부위별 감가 계산
  const basePrice = Math.max(0, basePriceMan || 0);
  const itemDetails: PartDepreciationDetail[] = [];
  const unknownParts: string[] = [];
  let totalDepreciationMan = 0;

  for (const rep of repairs) {
    const pStr = rep?.part || rep?.part_name || rep?.name || (typeof rep === 'string' ? rep : '');
    const rStr = rep?.repair || rep?.type_name || rep?.type || rep?.status || '';

    const { category, matchedPart } = resolvePartCategory(pStr);
    const repairType = resolveRepairType(rStr);

    let rate = 0;
    let minPriceMan = 0;
    let amountMan = 0;
    let note = '';

    if (category === 'BUMPER') {
      rate = 0;
      minPriceMan = 0;
      amountMan = 0;
      note = '범퍼 (감가 0원)';
    } else if (category === 'OUTER') {
      // 외판 교환·판금: 3.5%, 하한 35만
      rate = 0.035;
      minPriceMan = 35;
      if (basePrice > 0) {
        amountMan = Math.max(35, Math.round(basePrice * 0.035));
      }
      note = '외판 감가 (3.5% · 하한 35만)';
    } else if (category === 'FRAME') {
      if (repairType === 'SHEET_METAL') {
        // 골격 판금: 5%, 하한 50만
        rate = 0.050;
        minPriceMan = 50;
        if (basePrice > 0) {
          amountMan = Math.max(50, Math.round(basePrice * 0.050));
        }
        note = '골격 판금 감가 (5.0% · 하한 50만)';
      } else {
        // 골격 교체: 6.5%, 하한 65만 (교환이거나 불명일 때)
        rate = 0.065;
        minPriceMan = 65;
        if (basePrice > 0) {
          amountMan = Math.max(65, Math.round(basePrice * 0.065));
        }
        note = '골격 교체 감가 (6.5% · 하한 65만)';
      }
    } else {
      // UNKNOWN: 부위 구분이 애매하면 감가하지 않음
      unknownParts.push(pStr);
      note = '부위 구분 애매 (감가 제외)';
    }

    totalDepreciationMan += amountMan;

    itemDetails.push({
      rawPart: pStr,
      matchedPartCode: matchedPart?.code || (category === 'BUMPER' ? 'BUMPER' : 'UNKNOWN'),
      koreanName: matchedPart?.full || pStr,
      category,
      repairType,
      rate,
      minPriceMan,
      amountMan,
      note
    });
  }

  return {
    hasKnownHistory: true,
    isAccidentFree: false,
    totalDepreciationMan,
    itemDetails,
    unknownParts
  };
}
