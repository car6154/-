/**
 * J-PRO 차얼마 (오토플러스 purchase.autoplus.co.kr) 신차 출고가 & 순정 옵션 감가 서비스
 * 깃허브 원본 services/chaolma_service.py 1:1 완벽 이식
 */

export interface GenuineOption {
  name: string;
  price: number;
  depreciated_price?: number;
  rate?: number;
}

export interface ChaolmaCarHistory {
  success: boolean;
  car_no: string;
  owner_changed_count: number;
  is_single_owner: boolean;
  plate_change_count: number;
  has_rent_history: boolean;
  is_business: boolean;
  is_government: boolean;
  my_car_accident_count: number;
  my_car_accident_cost: number;
  my_car_accident_cost_man: number;
  other_car_accident_count: number;
  other_car_accident_cost: number;
  other_car_accident_cost_man: number;
  total_loss_count: number;
  flooded_count: number;
  stolen_count: number;
  uninsured_period?: string;
  mileage_records?: { date: string; source: string; mileage: number }[];
  accident_histories?: {
    date: string;
    repair_cost: number;
    parts_cost: number;
    labor_cost: number;
    paint_cost: number;
    insurance_paid: number;
  }[];
  market_price_range?: string;
  first_reg_date?: string;
}

export interface ChaolmaOriginDoc {
  success: boolean;
  car_no: string;
  seizure_count: number; // 압류 건수
  mortgage_count: number; // 저당 건수
  tuning_count: number; // 구조변경 건수
  inspection_valid_end?: string; // 정기검사 만료일 (예: 2027-06-15)
  inspection_valid_start?: string;
  last_regist_date?: string; // 최종 명의이전일 (예: 2026-09-23)
  first_regist_date?: string; // 최초 등록일 (예: 2017-06-16)
  inspection_mileage?: number; // 검사소 실측 주행거리 (km)
  is_resurrected?: boolean; // 부활차 여부
  is_cbu?: boolean; // 수입완성차 여부
  engine_type?: string; // 엔진 형식 (예: D4HB)
  car_form?: string; // 차량 형식 (예: YP9ABE-S-9)
  seating_capacity?: number; // 승차정원 (예: 7)
  plate_issue_ext?: string;
  raw_doc?: any;
}

export interface ChaolmaResult {
  success: boolean;
  message?: string;
  car_no: string;
  vin?: string;
  maker?: string;
  model_name?: string;
  model_detail_name?: string;
  grade_name?: string;
  grade_detail_name?: string;
  trim_name?: string;
  year?: string;
  release_date?: string;
  new_car_price: number;
  base_car_price: number;
  total_option_price: number;
  total_depreciated_opt_price: number;
  depreciation_rate: number;
  remain_rate: number;
  age_years: number;
  options: GenuineOption[];
  car_history?: ChaolmaCarHistory;
  origin_doc?: ChaolmaOriginDoc;
}

export const DEFAULT_OPTION_PRICES: Record<string, number> = {
  "7인치내비": 800000,
  "8인치내비": 950000,
  "내비": 850000,
  "내비게이션": 850000,
  "ecm&etcs": 250000,
  "ecm": 250000,
  "하이패스": 250000,
  "etcs": 200000,
  "컴포트": 600000,
  "컴포트시트": 600000,
  "기본형-컴포트시트": 600000,
  "기본형-컨비니언스": 1000000,
  "컨비니언스": 1000000,
  "시트": 500000,
  "통풍시트": 400000,
  "스타일": 850000,
  "스타일1": 850000,
  "스타일2": 950000,
  "선루프": 800000,
  "와이드선루프": 790000,
  "듀얼선루프": 800000,
  "파노라마선루프": 1150000,
  "드라이브와이즈": 1100000,
  "드라이브와이즈1": 1000000,
  "드라이브와이즈2": 1690000,
  "스마트센스": 1050000,
  "현대스마트센스": 1050000,
  "후측방경보": 450000,
  "후측방": 450000,
  "hud": 1200000,
  "헤드업디스플레이": 1200000,
  "서라운드뷰": 800000,
  "어라운드뷰": 800000,
  "모니터링팩": 700000,
  "스마트키": 350000,
  "버튼시동": 350000,
  "사운드": 600000,
  "크렐": 600000,
  "jbl": 600000,
  "보스": 600000,
  "렉시콘": 1200000,
  "프리미엄사운드": 600000,
  "led헤드램프": 650000,
};

/**
 * 연식 또는 최초등록일에 따른 순정 옵션 감가 잔존가치 계산 공식 (깃허브 tab_cockpit & chaolma_service)
 * - 1년 미만: 80% (0.80)
 * - 1~3년차: 50% (0.50)
 * - 3~5년차: 35% (0.35)
 * - 5년차 이상: 20% (0.20)
 */
export function calculateOptionDepreciation(options: GenuineOption[], yearOrDate?: string): {
  options: GenuineOption[];
  total_depreciated_opt_price: number;
  depreciation_rate: number;
  age_years: number;
} {
  const currentYear = new Date().getFullYear();
  let ageYears = 3.0;

  if (yearOrDate) {
    const matchYear = yearOrDate.match(/(\d{4})/);
    if (matchYear) {
      const yr = parseInt(matchYear[1], 10);
      ageYears = Math.max(0, currentYear - yr + 0.5);
    }
  }

  let rate = 0.50;
  if (ageYears < 1.0) rate = 0.80;
  else if (ageYears < 3.0) rate = 0.50;
  else if (ageYears < 5.0) rate = 0.35;
  else rate = 0.20;

  let totalDeprec = 0;
  const computedOptions = options.map((opt) => {
    const p = opt.price || 0;
    const dp = Math.round(p * rate);
    totalDeprec += dp;
    return {
      ...opt,
      depreciated_price: dp,
      rate,
    };
  });

  return {
    options: computedOptions,
    total_depreciated_opt_price: totalDeprec,
    depreciation_rate: rate,
    age_years: Number(ageYears.toFixed(1)),
  };
}

/**
 * 차얼마 신차 제원 및 순정옵션 실제 백엔드 API 조회
 */
export async function queryChaolmaCar(carNo: string, mileage: number = 50000): Promise<ChaolmaResult> {
  const cleanCarNo = carNo.replace(/\s+/g, "").trim();
  if (!cleanCarNo) {
    return {
      success: false,
      message: "차량번호를 입력해주세요.",
      car_no: "",
      new_car_price: 0,
      base_car_price: 0,
      total_option_price: 0,
      total_depreciated_opt_price: 0,
      depreciation_rate: 0,
      remain_rate: 0,
      age_years: 0,
      options: [],
    };
  }

  const urls = [
    `http://127.0.0.1:8000/api/chaolma/${encodeURIComponent(cleanCarNo)}?mileage=${mileage}`,
    `/api/chaolma/${encodeURIComponent(cleanCarNo)}?mileage=${mileage}`
  ];

  for (const url of urls) {
    try {
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        if (data && data.success) {
          return {
            success: true,
            car_no: cleanCarNo,
            vin: data.vin,
            maker: data.maker,
            model_name: data.model_detail_name || data.model_name,
            model_detail_name: data.model_detail_name,
            grade_name: data.grade_detail_name || data.grade_name,
            grade_detail_name: data.grade_detail_name,
            trim_name: data.trim_name,
            year: data.year_display || data.model_year || data.reg_year,
            release_date: data.release_date,
            new_car_price: data.new_car_price || 0,
            base_car_price: data.base_car_price || 0,
            total_option_price: data.total_option_price || 0,
            total_depreciated_opt_price: data.total_depreciated_opt_price || 0,
            depreciation_rate: data.depreciation_rate || 0,
            remain_rate: data.remain_rate || 0,
            age_years: data.age_years || 0,
            options: data.options || [],
            car_history: data.car_history,
            origin_doc: data.origin_doc,
          };
        } else if (data && data.message) {
          return {
            success: false,
            message: data.message,
            car_no: cleanCarNo,
            new_car_price: 0,
            base_car_price: 0,
            total_option_price: 0,
            total_depreciated_opt_price: 0,
            depreciation_rate: 0,
            remain_rate: 0,
            age_years: 0,
            options: [],
          };
        }
      }
    } catch (_) {
      // 다음 URL 폴백 시도
    }
  }

  return {
    success: false,
    message: "차얼마 서버 연결 실패",
    car_no: cleanCarNo,
    new_car_price: 0,
    base_car_price: 0,
    total_option_price: 0,
    total_depreciated_opt_price: 0,
    depreciation_rate: 0,
    remain_rate: 0,
    age_years: 0,
    options: [],
  };
}
