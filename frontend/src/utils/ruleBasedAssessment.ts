/**
 * 5단계 전체 규칙 기반 상태 판정 (Comprehensive Rule-Based Vehicle Assessment)
 * - 13년 차 실무 기준 및 AGENTS.md 무결성 규칙 준수
 * - 5대 검증: 권리 상태, 사고/손상, 소유/용도, 주행거리 무결성, 정기검사 유효성
 * - 최종 종합 등급: S (특S급) / A (우수) / B (보통) / C (주의) / D (결격/위험)
 */

export interface VehicleAssessmentInput {
  carNumber: string;
  yearModel?: number; // 연식 (예: 18)
  regYear?: number;   // 등록년 (예: 2017)
  currentMileage: number; // 현재 주행거리 (km)
  ownerChangedCount: number;
  isSingleOwner: boolean;
  hasRentHistory: boolean;
  myCarAccidentCount: number;
  myCarAccidentCostMan: number;
  otherCarAccidentCount: number;
  totalLossCount: number;
  floodedCount: number;
  stolenCount: number;
  seizureCount?: number;   // 압류
  mortgageCount?: number;  // 저당
  tuningCount?: number;    // 구조변경
  inspectionValidEnd?: string; // 정기검사 만료일 (YYYY-MM-DD)
  inspectionMileage?: number;  // 검사소 실측 주행거리 (km)
  lastHistoryMileage?: number; // 카히스토리 마지막 실측 주행거리 (km)
  outerRepairCount?: number;   // 외판 교환 부위 수
  frameDamage?: boolean;       // 골격 사고 유무
}

export interface RuleAssessmentResult {
  overallGrade: 'S' | 'A' | 'B' | 'C' | 'D';
  gradeName: string;
  gradeBadgeColor: string;
  isEligibleForBidding: boolean; // 입찰 적격 여부 (D등급은 결격/신중)
  
  // 5대 핵심 규칙 판정
  legalRights: {
    status: 'CLEAN' | 'WARNING';
    label: string;
    details: string;
    isPass: boolean;
  };
  accidentDamage: {
    status: 'PERFECT' | 'MINOR' | 'FRAME' | 'FATAL';
    label: string;
    details: string;
    isPass: boolean;
  };
  ownershipUsage: {
    status: 'SINGLE' | 'NORMAL' | 'MULTI' | 'RENT';
    label: string;
    details: string;
    isPass: boolean;
  };
  mileageIntegrity: {
    status: 'EXCELLENT' | 'NORMAL' | 'HIGH';
    label: string;
    details: string;
    isPass: boolean;
  };
  inspectionValidity: {
    status: 'VALID' | 'EXPIRING_SOON' | 'EXPIRED' | 'UNKNOWN';
    label: string;
    details: string;
    isPass: boolean;
  };

  // 실무 감가/가산 요약 (만원)
  ruleAdjustments: {
    item: string;
    amountMan: number;
    reason: string;
  }[];
  totalAdjustmentMan: number;
}

export function computeRuleBasedAssessment(input: VehicleAssessmentInput): RuleAssessmentResult {
  const adjustments: { item: string; amountMan: number; reason: string }[] = [];

  // 1. 법적 권리 상태 판정 (압류 / 저당)
  const seiz = input.seizureCount ?? 0;
  const mort = input.mortgageCount ?? 0;
  const isRightsClean = seiz === 0 && mort === 0;
  const legalRights = {
    status: (isRightsClean ? 'CLEAN' : 'WARNING') as 'CLEAN' | 'WARNING',
    label: isRightsClean ? '🟢 정상 (권리 하자 없음)' : `🚨 권리 하자 (압류 ${seiz}건 / 저당 ${mort}건)`,
    details: isRightsClean ? '압류 및 저당 설정 없음' : `해지 확약서 및 원부 말소 확인 필요`,
    isPass: isRightsClean
  };
  if (!isRightsClean) {
    adjustments.push({ item: '권리 하자', amountMan: 0, reason: '압류/저당 해지 비용 선처리 필요' });
  }

  // 2. 사고 & 손상 판정 (침수, 전손, 도난, 골격, 외판, 내차피해)
  let accidentStatus: 'PERFECT' | 'MINOR' | 'FRAME' | 'FATAL' = 'PERFECT';
  let accidentLabel = '🟢 완전 무사고 (외판/골격 정상)';
  let accidentDetails = '보험 사고 및 외판 교환 이력 없음';

  const isFatal = input.floodedCount > 0 || input.totalLossCount > 0 || input.stolenCount > 0;
  const isFrame = Boolean(input.frameDamage);
  const outerCnt = input.outerRepairCount ?? 0;
  const myAccCnt = input.myCarAccidentCount;
  const myAccCost = input.myCarAccidentCostMan;

  if (isFatal) {
    accidentStatus = 'FATAL';
    const fatalItems: string[] = [];
    if (input.floodedCount > 0) fatalItems.push(`침수 ${input.floodedCount}건`);
    if (input.totalLossCount > 0) fatalItems.push(`전손 ${input.totalLossCount}건`);
    if (input.stolenCount > 0) fatalItems.push(`도난 ${input.stolenCount}건`);
    accidentLabel = `🚨 중대 결격 (${fatalItems.join(', ')})`;
    accidentDetails = '침수/전손/도난 차량은 매입 원칙적 불가/특수 감가';
    adjustments.push({ item: '중대 결격', amountMan: -300, reason: '침수/전손 특수 감가' });
  } else if (isFrame) {
    accidentStatus = 'FRAME';
    accidentLabel = '🔴 주요 골격 프레임 사고';
    accidentDetails = '인사이드패널/휠하우스/필러 등 구조체 손상';
    adjustments.push({ item: '골격 사고', amountMan: -180, reason: '주요 골격 교환 감가' });
  } else if (outerCnt > 0 || myAccCnt > 0 || myAccCost > 0) {
    accidentStatus = 'MINOR';
    accidentLabel = `🟡 단순 수리 (외판 ${outerCnt}부위 / 내차 ${myAccCnt}건 ${myAccCost}만)`;
    accidentDetails = '골격 이상 없는 단순 볼트 체결 외판 교환';
  } else {
    accidentStatus = 'PERFECT';
    accidentLabel = '🟢 완전 무사고 (성능·보험 클린)';
    accidentDetails = '교환 및 보험처리 이력 전무';
    adjustments.push({ item: '완전 무사고', amountMan: +20, reason: '무사고 프리미엄 가산' });
  }

  // 3. 소유자 & 용도 이력 판정
  let ownerStatus: 'SINGLE' | 'NORMAL' | 'MULTI' | 'RENT' = 'NORMAL';
  let ownerLabel = '🟡 일반 소유 (1~2회 변경)';
  let ownerDetails = '통상적인 명의 변경 이력';

  if (input.hasRentHistory) {
    ownerStatus = 'RENT';
    ownerLabel = '⚠️ 렌트(용도) 이력 있음';
    ownerDetails = '대여용도 차량 (재판매 시 감가 요인)';
    adjustments.push({ item: '용도(렌트) 이력', amountMan: -80, reason: '렌트 이력 시장 감가' });
  } else if (input.isSingleOwner || input.ownerChangedCount === 0) {
    ownerStatus = 'SINGLE';
    ownerLabel = '🟢 1인 신조 (소유 변경 0회)';
    ownerDetails = '출고 후 1인 소유 관리 차량 (최고 선호도)';
    adjustments.push({ item: '1인 신조', amountMan: +30, reason: '1인 신조 프리미엄 가산' });
  } else if (input.ownerChangedCount >= 3) {
    ownerStatus = 'MULTI';
    ownerLabel = `🟠 다중 소유 (명의변경 ${input.ownerChangedCount}회)`;
    ownerDetails = '잦은 소유자 변경으로 관리 상태 정밀 점검 필요';
    adjustments.push({ item: '다중 소유', amountMan: -20, reason: '소유자 3회 이상 감가' });
  } else {
    ownerStatus = 'NORMAL';
    ownerLabel = `🟡 소유자 변경 ${input.ownerChangedCount}회`;
    ownerDetails = '정상 자가용 명의 변경 범위';
  }

  // 4. 주행거리 무결성 판정
  let mileageStatus: 'EXCELLENT' | 'NORMAL' | 'HIGH' = 'NORMAL';
  let mileageLabel = '🟢 정상 주행거리';
  let mileageDetails = '공식 기록과 일치하는 주행거리';

  {
    const ageY = input.yearModel ? (new Date().getFullYear() - (input.yearModel > 2000 ? input.yearModel : input.yearModel + 2000)) : 5;
    const annualKm = ageY > 0 ? Math.round(input.currentMileage / ageY) : input.currentMileage;
    if (annualKm > 25000) {
      mileageStatus = 'HIGH';
      mileageLabel = `⚠️ 주행거리 과다 (연간 약 ${annualKm.toLocaleString()}km)`;
      mileageDetails = '연평균 25,000km 초과 다주행 차량';
    } else if (annualKm < 8000 && input.currentMileage < 70000) {
      mileageStatus = 'EXCELLENT';
      mileageLabel = `🟢 짧은 실주행거리 (연간 약 ${annualKm.toLocaleString()}km)`;
      mileageDetails = '연평균 8,000km 미만 저주행 우수 차량';
      adjustments.push({ item: '저주행 가산', amountMan: +20, reason: '저주행 프리미엄 가산' });
    } else {
      mileageStatus = 'NORMAL';
      mileageLabel = `🟢 적정 주행거리 (연간 약 ${annualKm.toLocaleString()}km)`;
      mileageDetails = '연식 대비 표준 주행거리 유지';
    }
  }

  // 5. 정기검사 유효성 판정
  let inspStatus: 'VALID' | 'EXPIRING_SOON' | 'EXPIRED' | 'UNKNOWN' = 'VALID';
  let inspLabel = '🟢 정기검사 유효';
  let inspDetails = '검사 유효기간 충족';

  if (input.inspectionValidEnd) {
    const today = new Date();
    const endDate = new Date(input.inspectionValidEnd);
    const diffDays = Math.round((endDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    if (diffDays < 0) {
      inspStatus = 'EXPIRED';
      inspLabel = `🚨 정기검사 만료 (${Math.abs(diffDays)}일 경과)`;
      inspDetails = '자동차 정기검사 만료 상태 (과태료 발생 및 검사 선이행 필요)';
    } else if (diffDays <= 30) {
      inspStatus = 'EXPIRING_SOON';
      inspLabel = `⚠️ 정기검사 만료 임박 (${diffDays}일 남음)`;
      inspDetails = '30일 이내 정기검사 수검 요망';
    } else {
      inspStatus = 'VALID';
      inspLabel = `🟢 정기검사 유효 (${input.inspectionValidEnd} 까지)`;
      inspDetails = `잔여 ${diffDays}일 정상 유효`;
    }
  } else {
    inspStatus = 'UNKNOWN';
    inspLabel = '⚪ 검사 유효기간 미확인';
    inspDetails = '등록원부 검사일자 확인 필요';
  }

  // 6. 종합 상태 등급 (S / A / B / C / D) 산출
  let overallGrade: 'S' | 'A' | 'B' | 'C' | 'D' = 'A';
  let gradeName = 'A등급 (우수)';
  let gradeBadgeColor = '#10b981';
  let isEligible = true;

  if (accidentStatus === 'FATAL') {
    overallGrade = 'D';
    gradeName = 'D등급 (결격/위험)';
    gradeBadgeColor = '#f43f5e';
    isEligible = false;
  } else if (accidentStatus === 'FRAME' || ownerStatus === 'MULTI' && outerCnt >= 3) {
    overallGrade = 'C';
    gradeName = 'C등급 (주의/골격사고)';
    gradeBadgeColor = '#f97316';
    isEligible = true;
  } else if (ownerStatus === 'RENT' || accidentStatus === 'MINOR' || mileageStatus === 'HIGH') {
    overallGrade = 'B';
    gradeName = 'B등급 (보통/실속형)';
    gradeBadgeColor = '#eab308';
    isEligible = true;
  } else if (accidentStatus === 'PERFECT' && ownerStatus === 'SINGLE' && isRightsClean) {
    overallGrade = 'S';
    gradeName = '특S등급 (최상급)';
    gradeBadgeColor = '#38bdf8';
    isEligible = true;
  } else {
    overallGrade = 'A';
    gradeName = 'A등급 (우수)';
    gradeBadgeColor = '#10b981';
    isEligible = true;
  }

  const totalAdjustmentMan = adjustments.reduce((acc, cur) => acc + cur.amountMan, 0);

  return {
    overallGrade,
    gradeName,
    gradeBadgeColor,
    isEligibleForBidding: isEligible,
    legalRights,
    accidentDamage: {
      status: accidentStatus,
      label: accidentLabel,
      details: accidentDetails,
      isPass: accidentStatus !== 'FATAL' && accidentStatus !== 'FRAME'
    },
    ownershipUsage: {
      status: ownerStatus,
      label: ownerLabel,
      details: ownerDetails,
      isPass: ownerStatus !== 'RENT'
    },
    mileageIntegrity: {
      status: mileageStatus,
      label: mileageLabel,
      details: mileageDetails,
      isPass: true
    },
    inspectionValidity: {
      status: inspStatus,
      label: inspLabel,
      details: inspDetails,
      isPass: inspStatus !== 'EXPIRED'
    },
    ruleAdjustments: adjustments,
    totalAdjustmentMan
  };
}
