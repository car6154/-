/**
 * J-PRO 비딩 칵핏 신차 옵션 카탈로그 및 정규화 / 매칭 엔진
 * - 헤이딜러 부위 및 수리 매핑
 * - 헤이딜러 상대 시점 일자 포맷터 & 신차 추가옵션 파서
 * - 전 차종 패키지 마스터 카탈로그 (현대/기아/쉐보레/르노/KGM)
 * - 문자 바이그램(Bi-gram) 자카드 유사도 및 양방향 분해 매칭
 */

export const HD_PART_MAP: Record<string, string> = {
  bumper_front: '앞범퍼', bumper_rear: '뒤범퍼',
  fender_front_driver: '앞휀더(운전석)', fender_front_passenger: '앞휀더(조수석)',
  fender_rear_driver: '뒤휀더(운전석)', fender_rear_passenger: '뒤휀더(조수석)',
  door_front_driver: '앞도어(운전석)', door_front_passenger: '앞도어(조수석)',
  door_rear_driver: '뒤도어(운전석)', door_rear_passenger: '뒤도어(조수석)',
  hood: '후드(보닛)', trunk_lid: '트렁크리드', roof: '루프',
  radiator_support: '라디에이터 서포트', panel_front: '프론트패널', panel_rear: '리어패널',
  front_panel: '프론트패널', rear_panel: '리어패널', trunk_floor: '트렁크플로어',
  side_member: '사이드멤버', cross_member: '크로스멤버', inside_panel: '인사이드패널',
  inside_panel_front_driver: '인사이드패널(앞/운전석)', inside_panel_front_passenger: '인사이드패널(앞/조수석)',
  inside_panel_rear_driver: '인사이드패널(뒤/운전석)', inside_panel_rear_passenger: '인사이드패널(뒤/조수석)',
  side_member_front_driver: '사이드멤버(앞/운전석)', side_member_front_passenger: '사이드멤버(앞/조수석)',
  side_member_rear_driver: '사이드멤버(뒤/운전석)', side_member_rear_passenger: '사이드멤버(뒤/조수석)',
  pillar_a: 'A필러', pillar_b: 'B필러', pillar_c: 'C필러',
  pillar_a_driver: 'A필러(운전석)', pillar_a_passenger: 'A필러(조수석)',
  pillar_b_driver: 'B필러(운전석)', pillar_b_passenger: 'B필러(조수석)',
  pillar_c_driver: 'C필러(운전석)', pillar_c_passenger: 'C필러(조수석)',
  quarter_panel_driver: '쿼터패널(운전석)', quarter_panel_passenger: '쿼터패널(조수석)',
  wheel_house_front_driver: '휠하우스(앞/운전석)', wheel_house_front_passenger: '휠하우스(앞/조수석)',
  wheel_house_rear_driver: '휠하우스(뒤/운전석)', wheel_house_rear_passenger: '휠하우스(뒤/조수석)',
};

export const HD_REPAIR_MAP: Record<string, string> = {
  exchange: '교환', replace: '교환', weld: '판금/용접', sheet_metal: '판금'
};

export const formatHdRelativeDate = (item: any): string => {
  if (!item) return '-';
  if (typeof item === 'string') {
    const s = item.trim();
    if (!s) return '-';
    // 이미 상대시점 텍스트인 경우 (예: "4일 전", "1주 전", "어제", "오늘")
    if (s.includes('전') || s.includes('오늘') || s.includes('어제') || s.includes('방금') || s.includes('진행중')) {
      return s;
    }
    try {
      const d = new Date(s);
      if (isNaN(d.getTime())) return s;
      const now = new Date();
      const diffDays = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
      if (diffDays <= 0) return '오늘';
      if (diffDays === 1) return '어제';
      if (diffDays < 7) return `${diffDays}일 전`;
      const weeks = Math.floor(diffDays / 7);
      if (weeks < 4) return `${weeks}주 전`;
      const months = Math.floor(diffDays / 30);
      return `${Math.max(1, months)}달 전`;
    } catch {
      return s;
    }
  }

  // 객체인 경우 (item, auction, detail 등에서 8501과 100% 동일 우선순위로 추출)
  const auc = item.auction || {};
  const d = item.detail || {};
  const bid = auc.highest_bid || {};

  // 1. tags 확인 (헤이딜러 공식 상대 시점 태그 최우선)
  const timeKeywords = ['일 전', '일전', '주 전', '주전', '달 전', '달전', '개월 전', '개월전', '년 전', '년전', '시간 전', '시간전', '오늘', '어제', '방금', '진행중'];
  for (const container of [auc, item, d, bid]) {
    if (container && typeof container === 'object') {
      const tags = Array.isArray(container.tags) ? container.tags : [];
      for (const t of tags) {
        let txt = '';
        if (typeof t === 'object' && t !== null) {
          txt = t.short_text || t.text || t.name || t.label || '';
        } else if (typeof t === 'string') {
          txt = t;
        }
        txt = String(txt).trim();
        if (txt && timeKeywords.some(k => txt.includes(k))) {
          return txt;
        }
      }
    }
  }

  // 2. 날짜/시간 필드 우선순위 검사 (8501과 동일)
  const dateKeys = [
    'ended_at_display', 'end_at_display', 'auction_end_at_display', 'auction_ended_at_display',
    'selected_at_display', 'closed_at_display', 'approved_at_display',
    'ended_at', 'end_at', 'auction_end_at', 'auction_ended_at',
    'selected_at', 'closed_at', 'sold_at', 'finished_at', 'completed_at',
    'deal_date', 'auction_date', 'date', 'bidded_at', 'approved_at',
    'created_at', 'registered_at', 'updated_at'
  ];

  for (const container of [auc, item, bid, d]) {
    if (container && typeof container === 'object') {
      for (const k of dateKeys) {
        const val = container[k];
        if (val) {
          return formatHdRelativeDate(String(val));
        }
      }
    }
  }

  return '-';
};

// 🌟 헤이딜러 car_spec.description 에서 순수 '신차 추가옵션'만 정확하게 파싱 (8501과 100% 동일 알고리즘)
export const parseHeydealerOptions = (specDesc: string): string[] => {
  if (!specDesc) return [];
  const lines = String(specDesc).split('\n').map(l => l.trim()).filter(Boolean);
  
  let optMarkerIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes('신차 추가옵션') || lines[i].includes('신차추가옵션') || lines[i].includes('신차 추가 옵션')) {
      optMarkerIdx = i;
      break;
    }
  }

  let baseMarkerIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes('기본옵션') || lines[i].includes('기본 사양') || lines[i].includes('기본사양') || lines[i].includes('기본품목')) {
      baseMarkerIdx = i;
      break;
    }
  }

  const parseNumberedList = (lineArr: string[]) => {
    const res: string[] = [];
    for (const l of lineArr) {
      const m = l.match(/^\d+\)\s*(.*?)(?:\s*\(|$)/);
      if (m && m[1]?.trim()) {
        res.push(m[1].trim());
      }
    }
    return res;
  };

  if (optMarkerIdx !== -1) {
    const above = parseNumberedList(lines.slice(0, optMarkerIdx));
    const end = baseMarkerIdx !== -1 && baseMarkerIdx > optMarkerIdx ? baseMarkerIdx : lines.length;
    const below = parseNumberedList(lines.slice(optMarkerIdx + 1, end));
    if (above.length > 0) return above;
    if (below.length > 0) return below;
  } else {
    const end = baseMarkerIdx !== -1 ? baseMarkerIdx : lines.length;
    return parseNumberedList(lines.slice(0, end));
  }
  return [];
};

// ═══════════════════════════════════════════════════════════════
// 📦 전체적 옵션 정규화 & 유사도 매칭 엔진
// 1. 신차 패키지 마스터 카탈로그 (현대/기아/쉐보레/르노/KGM 전 차종 패키지 분해)
// 2. 영문 약어 및 동의어 전역 매핑 (HUD, ACC, SVM, BSD, LDW, EPB, IMS 등)
// 3. 문자 바이그램(Bi-gram) 자카드 유사도 계수 (Jaccard Index >= 0.42)
// 4. 패키지 ↔ 세부 품목 양방향 분해 매칭 (Decomposition Matching)
// ═══════════════════════════════════════════════════════════════

export interface MasterPackageDef {
  id: string;
  name: string;
  brand?: string;
  aliases: string[];
  items: string[];
  matchKeywords: string[];
}

export const MASTER_PACKAGE_CATALOG: MasterPackageDef[] = [
  // ── 현대자동차 (Hyundai) ──
  {
    id: 'hyundai_smart_sense',
    name: '현대 스마트센스',
    brand: '현대',
    aliases: ['현대스마트센스', '스마트센스', '스마트센스1', '스마트센스2', '스마트센스3', '스마트센스i', '스마트센스ii', '스마트센스iii', '스마트센스ⅳ', '스마트센스ⅲ', '스마트센스ⅱ', '스마트센스ⅰ'],
    items: ['스마트 크루즈 컨트롤', '전방 충돌방지 보조', '고속도로 주행 보조(HDA)', '후측방 충돌방지 보조', '차로 유지 보조', '안전 하차 보조'],
    matchKeywords: ['스마트크루즈', '크루즈컨트롤', '크루즈', 'ascc', 'scc', 'hda', 'hda2', '후측방', '차로유지', '차선유지', '전방충돌', '차선이탈', '차로이탈', '충돌방지', '충돌경고', 'fca', 'lka', 'lfa', '주행보조', '반자율']
  },
  {
    id: 'hyundai_multimedia_navi',
    name: '멀티미디어 내비 플러스',
    brand: '현대',
    aliases: ['멀티미디어내비플러스', '멀티미디어내비플러스1', '멀티미디어내비플러스2', '멀티미디어내비1', '멀티미디어내비2', '내비플러스', '내비게이션패키지', '8인치내비게이션', '10.25인치내비게이션', '12.3인치내비게이션'],
    items: ['10.25인치 내비게이션', '후방 모니터', '풀오토 에어컨', '블루링크', '샤크핀 안테나'],
    matchKeywords: ['내비게이션', '네비게이션', '내비', '네비', 'navigation', '후방카메라', '후방모니터', '풀오토에어컨', '멀티미디어', '블루링크']
  },
  {
    id: 'hyundai_comfort',
    name: '컴포트',
    brand: '현대',
    aliases: ['컴포트', '컴포트1', '컴포트2', '컴포트i', '컴포트ii', '컴포트플러스', '시트패키지'],
    items: ['1열 통풍시트', '운전석 전동시트', '동승석 전동시트', '2열 열선시트', '동승석 릴렉션', '스마트 전동트렁크'],
    matchKeywords: ['통풍시트', '통풍', '전동시트', '파워시트', '2열열선', '뒷좌석열선', '요추받침', '파워테일게이트', '전동트렁크', '릴렉션']
  },
  {
    id: 'hyundai_style',
    name: '스타일',
    brand: '현대',
    aliases: ['스타일', '스타일1', '스타일2', '스타일i', '스타일ii', '익스테리어', '익스테리어디자인'],
    items: ['Full LED 헤드램프', 'LED 주간주행등', 'LED 리어 콤비램프', '대구경 알로이 휠'],
    matchKeywords: ['스타일', 'led헤드램프', 'led램프', '헤드램프', '프로젝션', '알로이휠', '익스테리어']
  },
  {
    id: 'hyundai_parking_assist',
    name: '파킹 어시스트 / 서라운드뷰',
    brand: '현대',
    aliases: ['파킹어시스트', '파킹어시스트플러스', '파킹어시스트1', '파킹어시스트2', '서라운드뷰모니터', '어라운드뷰', '모니터링팩'],
    items: ['서라운드 뷰 모니터(SVM)', '후측방 모니터(BVM)', '원격 스마트 주차 보조', '후방 주차 충돌방지'],
    matchKeywords: ['서라운드뷰', '어라운드뷰', '360도뷰', 'svm', 'bvm', '후측방모니터', '모니터링', '원격주차', '주차보조']
  },
  {
    id: 'hyundai_hitech',
    name: '하이테크',
    brand: '현대',
    aliases: ['하이테크', '하이테크플러스', '테크', '테크패키지'],
    items: ['헤드업 디스플레이(HUD)', '12.3인치 컬러 클러스터', '스마트폰 무선충전', '현대 디지털키'],
    matchKeywords: ['hud', '헤드업디스플레이', '헤드업', '클러스터', '계기판', '무선충전', '디지털키']
  },
  {
    id: 'hyundai_builtin_cam',
    name: '빌트인 캠',
    brand: '현대',
    aliases: ['빌트인캠', '빌트인캠1', '빌트인캠2', 'builtincam'],
    items: ['빌트인 캠(주행/주차 녹화)', '보조배터리'],
    matchKeywords: ['빌트인캠', '블랙박스', '주행영상']
  },

  // ── 기아 (Kia) ──
  {
    id: 'kia_drive_wise',
    name: '드라이브 와이즈',
    brand: '기아',
    aliases: ['드라이브와이즈', '드라이브와이즈1', '드라이브와이즈2', '드라이브와이즈i', '드라이브와이즈ii', 'drivewise', 'drivewise1', 'drivewise2'],
    items: ['전방 충돌방지 보조(FCA)', '스마트 크루즈 컨트롤(SCC/Stop&Go)', '고속도로 주행 보조(HDA)', '차로 유지 보조(LFA)', '후측방 충돌방지 보조(BCA)', '안전 하차 보조'],
    matchKeywords: ['드라이브와이즈', '스마트크루즈', '크루즈컨트롤', '크루즈', 'scc', 'ascc', 'hda', 'hda2', '후측방', '차로유지', '차선유지', '전방충돌', '차선이탈', '차로이탈', '충돌방지', '충돌경고', 'fca', 'lka', 'lfa', '반자율']
  },
  {
    id: 'kia_monitoring_pack',
    name: '모니터링 팩 / 서라운드 뷰',
    brand: '기아',
    aliases: ['모니터링팩', '모니터링패키지', '서라운드뷰모니터링', '서라운드뷰', '어라운드뷰'],
    items: ['서라운드 뷰 모니터(SVM)', '후측방 모니터(BVM)', '원격 스마트 주차 보조', '후방 주차 충돌방지'],
    matchKeywords: ['모니터링', '모니터링팩', '서라운드뷰', '어라운드뷰', 'svm', 'bvm', '후측방모니터', '360도뷰', '원격주차']
  },
  {
    id: 'kia_comfort',
    name: '컴포트',
    brand: '기아',
    aliases: ['컴포트', '컴포트패키지', '시트패키지'],
    items: ['1열 통풍시트', '운전석 파워시트', '전동 요추받침', '동승석 워크인 디바이스'],
    matchKeywords: ['통풍시트', '통풍', '전동시트', '파워시트', '요추받침', '워크인']
  },
  {
    id: 'kia_style',
    name: '스타일',
    brand: '기아',
    aliases: ['스타일', '스타일패키지', '스타일1', '스타일2'],
    items: ['프로젝션 LED 헤드램프', 'LED 리어 콤비네이션 램프', '전면 가니쉬', '알로이 휠'],
    matchKeywords: ['스타일', 'led헤드램프', 'led램프', '프로젝션', '알로이휠']
  },
  {
    id: 'kia_uvo_navi',
    name: 'UVO / 기아 커넥트 내비게이션',
    brand: '기아',
    aliases: ['내비게이션', '10.25인치내비게이션', '12.3인치내비게이션', 'uvo내비게이션', '기아커넥트내비게이션'],
    items: ['10.25/12.3인치 내비게이션', '기아 커넥트(UVO)', '후방 모니터', '샤크핀 안테나'],
    matchKeywords: ['내비게이션', '네비게이션', '내비', '네비', '후방카메라', 'uvo', '기아커넥트']
  },

  // ── 쉐보레 (Chevrolet) ──
  {
    id: 'chevy_comfort_3',
    name: '컴포트 패키지 III',
    brand: '쉐보레',
    aliases: ['컴포트패키지iii', '컴포트패키지3', '컴포트패키지', '컴포트3', '컴포트iii', 'comfort3'],
    items: ['천공 천연가죽 시트', '운전석 8way 전동시트', '운전석 파워 요추 받침', '1열 통풍시트'],
    matchKeywords: ['통풍시트', '통풍', '전동시트', '가죽시트', '요추받침', '파워시트']
  },
  {
    id: 'chevy_selective_2',
    name: '셀렉티브 패키지 II',
    brand: '쉐보레',
    aliases: ['셀렉티브패키지ii', '셀렉티브패키지2', '셀렉티브패키지', '셀렉티브2', '셀렉티브ii', 'selective2'],
    items: ['LED 헤드램프', '사각지대 경고 시스템', '후측방 경고 시스템', '핸즈프리 파워 리프트게이트', '레인센싱 와이퍼', '스마트폰 무선충전'],
    matchKeywords: ['파워테일게이트', '파워리프트게이트', '전동트렁크', '사각지대', '후측방', 'led헤드램프', '무선충전']
  },
  {
    id: 'chevy_premium_pack',
    name: '프리미엄 패키지',
    brand: '쉐보레',
    aliases: ['프리미엄패키지', '프리미엄팩', 'premiumpackage'],
    items: ['내비게이션 시스템', '디지털 후방 카메라', '슈퍼비전 컬러 클러스터', '어댑티브 크루즈 컨트롤(ACC)', '컴바이너 HUD'],
    matchKeywords: ['내비게이션', '네비게이션', '후방카메라', '어댑티브', '크루즈컨트롤', 'acc', '헤드업', 'hud']
  },
  {
    id: 'chevy_safety_2',
    name: '세이프티 패키지 II',
    brand: '쉐보레',
    aliases: ['세이프티패키지ii', '세이프티패키지2', '세이프티2', '세이프티ii', '세이프티패키지', '세이프티팩'],
    items: ['사각지대 경고시스템(SBZA)', '후측방 경고시스템(RCTA)', '전방충돌 경고시스템', '차선이탈 경고시스템'],
    matchKeywords: ['사각지대', '후측방', '전방충돌', '차선이탈', 'sbza', 'rcta', 'ldws', 'fcw', '세이프티']
  },
  {
    id: 'chevy_hit_cool',
    name: '힛 & 쿨 패키지',
    brand: '쉐보레',
    aliases: ['힛앤쿨', '힛앤쿨패키지', 'hitandcool'],
    items: ['앞좌석 통풍시트', '운전석 8way 전동시트', '파워 요추받침'],
    matchKeywords: ['통풍시트', '통풍', '전동시트', '요추받침']
  },

  // ── 르노코리아 (Renault) & KGM (SsangYong) ──
  {
    id: 'renault_slink',
    name: 'S-Link 패키지',
    brand: '르노',
    aliases: ['slink', 's링크', 's-link', 'slink패키지', '이지커넥트'],
    items: ['8.7인치 S-Link 내비게이션', '후방 카메라', '엠비언트 라이트'],
    matchKeywords: ['slink', 's-link', 's링크', '내비게이션', '네비게이션', '내비', '후방카메라', '이지커넥트']
  },
  {
    id: 'renault_magic_tailgate',
    name: '매직 테일게이트',
    brand: '르노',
    aliases: ['매직테일게이트', '매직테일', '전동트렁크'],
    items: ['스마트 파워 테일게이트 (핸즈프리 열림)'],
    matchKeywords: ['매직테일게이트', '전동트렁크', '파워테일게이트', '스마트테일게이트']
  },
  {
    id: 'kgm_deep_control',
    name: '딥 컨트롤 패키지',
    brand: 'KGM',
    aliases: ['딥컨트롤', '딥컨트롤1', '딥컨트롤2', '딥컨트롤i', '딥컨트롤ii', '스마트드라이브'],
    items: ['인텔리전트 어댑티브 크루즈(IACC)', '후측방 경고', '차선 유지 보조', '자동 긴급제동'],
    matchKeywords: ['딥컨트롤', '어댑티브크루즈', '크루즈', 'iacc', '후측방', '차로유지', '차선유지', '긴급제동']
  },

  // ── 공통 필수 순정 옵션군 (사운드/선루프/트렁크 등) ──
  {
    id: 'common_sunroof',
    name: '선루프 / 파노라마 선루프',
    aliases: ['선루프', '썬루프', '파노라마선루프', '파노라마썬루프', '와이드선루프', '듀얼선루프', '스카이풀선루프'],
    items: ['파노라마 선루프', '원터치 세이프티 선루프'],
    matchKeywords: ['선루프', '썬루프', '파노라마선루프', '파노라마썬루프']
  },
  {
    id: 'common_sound',
    name: '프리미엄 사운드 시스템',
    aliases: ['프리미엄사운드', '사운드패키지', '보스', '크렐', 'jbl', '렉시콘', '액튠', '하만카돈', 'bose', 'krell', 'lexicon'],
    items: ['Bose/KRELL/JBL 프리미엄 스피커', '외장 앰프', '서브우퍼'],
    matchKeywords: ['사운드', '프리미엄사운드', '보스', 'bose', '크렐', 'krell', 'jbl', '렉시콘', '하만카돈', '스피커']
  },
  {
    id: 'common_tailgate',
    name: '스마트 / 파워 전동트렁크',
    aliases: ['전동트렁크', '파워테일게이트', '스마트테일게이트', '파워리프트게이트', '스마트파워테일게이트'],
    items: ['스마트 전동식 트렁크 (파워 리프트게이트)'],
    matchKeywords: ['전동트렁크', '파워테일게이트', '스마트테일게이트', '파워리프트게이트', '매직테일게이트']
  }
];

// 영문 약어 및 동의어 전역 매핑 테이블 (양방향 연결)
export const CORE_EQUIVALENCE_GROUPS: string[][] = [
  ['내비', '네비', 'navigation', '내비게이션', '네비게이션', 'slink', 's링크', 's-link', '멀티미디어', '멀티미디어패키지', '멀티미디어팩', '내비패키지', '네비패키지', 'uvo', '블루링크', '기아커넥트'],
  ['선루프', '썬루프', '파노라마선루프', '파노라마썬루프', '듀얼선루프', '와이드선루프'],
  ['드라이브와이즈', '스마트센스', 'ascc', 'scc', '스마트크루즈', '어댑티브크루즈', '반자율', '주행보조', 'hda', 'hda2', '드라이빙어시스트', '전방충돌', '차선이탈', '차로이탈', '충돌방지', '충돌경고', 'fca', 'fcw', 'lka', 'ldw', 'bcw'],
  ['hud', '헤드업디스플레이', '헤드업'],
  ['어라운드뷰', '서라운드뷰', '모니터링', '모니터링팩', 'svm', 'bvm', '360도뷰', '스카이뷰'],
  ['통풍시트', '통풍', '앞좌석통풍', '1열통풍', '쿨링시트'],
  ['열선시트', '2열열선', '뒷좌석열선', '히팅시트'],
  ['열선핸들', '열선스티어링', '히티드스티어링'],
  ['메모리시트', '메모리', 'ims', '운전석메모리'],
  ['krell', '크렐', 'jbl', 'bose', '보스', '렉시콘', 'lexicon', '사운드', '프리미엄사운드'],
  ['스타일', '스타일팩', '익스테리어', '익스테리어디자인'],
  ['컴포트', '컴포트팩', '시트패키지', '컴포트시트'],
  ['스마트커넥트', '디지털키', '현대디지털키', '기아디지털키'],
  ['빌트인캠', '블랙박스', '주행영상기록'],
  ['테크', '테크팩', '하이테크', '테크놀로지'],
  ['패밀리', '패밀리팩'],
  ['매직테일게이트', '스마트테일게이트', '전동트렁크', '파워테일게이트', '파워리프트게이트', '매직테일'],
  ['세이프티', '세이프티패키지', '세이프티팩', '사각지대', '후측방', '전방충돌', '차선이탈', 'sbza', 'rcta', 'ldws', 'fcw', 'bsd', 'bca'],
  ['무선충전', '스마트폰무선충전', '휴대폰무선충전'],
  ['전자파킹', '전자식파킹', 'epb', '오토홀드'],
  ['스마트키', '버튼시동', '스마트엔트리']
];

// 정규화 텍스트 처리 (NFKC, 괄호/금액 제거, 로마숫자 변환)
export const normalizeOpt = (text: string): string => {
  if (!text) return '';
  // 1. 유니코드 NFKC 정규화 (로마숫자 Ⅰ, Ⅱ, Ⅲ, Ⅳ -> I, II, III, IV 변환)
  let t = text.normalize('NFKC');
  // 2. 괄호 안의 가격이나 수식어 제거: '컴포트 패키지 III (79만)' -> '컴포트 패키지 III'
  t = t.replace(/\(.*?\)/g, '').replace(/\[.*?\]/g, '').trim().toLowerCase();
  // 3. 특수문자 및 공백 제거
  t = t.replace(/[\s\-_·+,\/.]/g, '');
  // 4. 로마숫자 통일 (끝자리 또는 패키지 키워드 뒤: iv->4, iii->3, ii->2, i->1)
  t = t.replace(/iv$/g, '4').replace(/iii$/g, '3').replace(/ii$/g, '2').replace(/i$/g, '1');
  t = t.replace(/(패키지|플러스|팩|센스|와이즈|컨트롤|어시스트|액티브|컴포트|셀렉티브|스타일|세이프티)iv/g, '$14');
  t = t.replace(/(패키지|플러스|팩|센스|와이즈|컨트롤|어시스트|액티브|컴포트|셀렉티브|스타일|세이프티)iii/g, '$13');
  t = t.replace(/(패키지|플러스|팩|센스|와이즈|컨트롤|어시스트|액티브|컴포트|셀렉티브|스타일|세이프티)ii/g, '$12');
  t = t.replace(/(패키지|플러스|팩|센스|와이즈|컨트롤|어시스트|액티브|컴포트|셀렉티브|스타일|세이프티)i/g, '$11');
  return t;
};

// 문자 바이그램(2글자 음절 단위 슬라이딩 윈도우) 집합 생성
export const getBiGramSet = (str: string): Set<string> => {
  const set = new Set<string>();
  if (!str || str.length < 2) return set;
  for (let i = 0; i < str.length - 1; i++) {
    set.add(str.slice(i, i + 2));
  }
  return set;
};

// 바이그램 자카드 유사도 (Jaccard Index) 계산
export const computeBiGramJaccard = (strA: string, strB: string): number => {
  if (!strA || !strB) return 0;
  if (strA === strB) return 1.0;
  const setA = getBiGramSet(strA);
  const setB = getBiGramSet(strB);
  if (setA.size === 0 || setB.size === 0) return 0;

  let intersection = 0;
  setA.forEach(item => {
    if (setB.has(item)) intersection++;
  });
  const union = setA.size + setB.size - intersection;
  return union > 0 ? intersection / union : 0;
};

// 🌟 전체적 정규화 옵션 매칭 판정 (전체 카탈로그 분해 + 바이그램 자카드 + 약어 동의어 매칭)
export const isOptionMatched = (optA: string, optB: string): boolean => {
  if (!optA || !optB) return false;
  const normA = normalizeOpt(optA);
  const normB = normalizeOpt(optB);
  if (!normA || !normB) return false;

  // 1. 완전 일치 (정규화 후)
  if (normA === normB) {
    return true;
  }

  // 숫자 식별자 추출 (버전 충돌 방지: 예: 스마트센스1 vs 스마트센스2)
  const numsA = normA.match(/[1-9]/g);
  const numsB = normB.match(/[1-9]/g);
  const hasConflictingVersion = numsA && numsB && numsA.join('') !== numsB.join('');

  // 2. 부분 일치 (버전 충돌이 없을 때, 2글자 이상 키워드 상호 포함)
  if (!hasConflictingVersion) {
    if (normA.length >= 2 && normB.includes(normA)) return true;
    if (normB.length >= 2 && normA.includes(normB)) return true;
  }

  // 3. 영문 약어 및 동의어 전역 매핑 검사
  if (!hasConflictingVersion) {
    for (const group of CORE_EQUIVALENCE_GROUPS) {
      const hitA = group.some(g => normA.includes(g));
      const hitB = group.some(g => normB.includes(g));
      if (hitA && hitB) return true;
    }
  }

  // 4. 패키지 마스터 카탈로그 분해 매칭 (Package Decomposition)
  // optA가 패키지이고 optB가 세부 부품이거나, 그 반대인 경우
  for (const pkg of MASTER_PACKAGE_CATALOG) {
    const isPkgA = pkg.aliases.some(a => normA.includes(normalizeOpt(a))) || normA.includes(normalizeOpt(pkg.name));
    const isPkgB = pkg.aliases.some(b => normB.includes(normalizeOpt(b))) || normB.includes(normalizeOpt(pkg.name));

    if (isPkgA && !isPkgB) {
      // optA가 패키지 -> optB가 패키지 매칭 키워드나 품목에 포함되는지 검사
      const hit = pkg.matchKeywords.some(kw => normB.includes(normalizeOpt(kw)) || normalizeOpt(kw).includes(normB)) ||
                  pkg.items.some(it => normB.includes(normalizeOpt(it)) || normalizeOpt(it).includes(normB));
      if (hit) return true;
    } else if (isPkgB && !isPkgA) {
      // optB가 패키지 -> optA가 패키지 매칭 키워드나 품목에 포함되는지 검사
      const hit = pkg.matchKeywords.some(kw => normA.includes(normalizeOpt(kw)) || normalizeOpt(kw).includes(normA)) ||
                  pkg.items.some(it => normA.includes(normalizeOpt(it)) || normalizeOpt(it).includes(normA));
      if (hit) return true;
    }
  }

  // 5. 문자 바이그램 자카드 유사도 (Jaccard Index >= 0.42)
  if (!hasConflictingVersion) {
    const jaccard = computeBiGramJaccard(normA, normB);
    if (jaccard >= 0.42) {
      return true;
    }
  }

  return false;
};

/**
 * 괄호 안의 쉼표나 상세 설명을 보존하면서 개별 옵션 단위로 안전하게 분리하는 스마트 파서
 */
export const splitOptionString = (optStr: string): string[] => {
  if (!optStr) return [];
  const str = String(optStr).trim();
  if (!str || ['없음', '-', '없음(구버전점검)', '⚠️조회실패', '코드매칭실패', '기본'].includes(str)) {
    return [];
  }

  const results: string[] = [];
  let current = '';
  let depth = 0;

  for (let i = 0; i < str.length; i++) {
    const ch = str[i];
    if (ch === '(' || ch === '[' || ch === '{') {
      depth++;
      current += ch;
    } else if (ch === ')' || ch === ']' || ch === '}') {
      depth = Math.max(0, depth - 1);
      current += ch;
    } else if (depth === 0 && (ch === '/' || ch === '·' || ch === '\n' || ch === ',')) {
      const trimmed = current.trim();
      if (trimmed) results.push(trimmed);
      current = '';
    } else {
      current += ch;
    }
  }

  const lastTrimmed = current.trim();
  if (lastTrimmed) results.push(lastTrimmed);

  return results
    .map(o => o.trim())
    .filter(o => o.length > 0 && !['없음', '-', '기본'].includes(o));
};

export interface OptionMatchDetailResult {
  isMatched: boolean;
  matchedOppositeName?: string;
  packageName?: string;
  packageItems?: string[];
  tooltipText: string;
}

/**
 * 양방향 옵션 매칭 판정 및 마우스 호버용 고정밀 툴팁 텍스트 생성
 * @param optName 대상 옵션명
 * @param oppositeOpts 비교 상대 차량의 옵션 목록
 * @param direction 'target_vs_comp'(내 차 기준) | 'comp_vs_target'(비교차 기준)
 */
export const getOptionMatchDetail = (
  optName: string,
  oppositeOpts: string[],
  direction: 'target_vs_comp' | 'comp_vs_target'
): OptionMatchDetailResult => {
  const cleanName = optName.trim();
  if (!cleanName) {
    return { isMatched: false, tooltipText: '' };
  }

  const norm = normalizeOpt(cleanName);

  // 1. 패키지 마스터 카탈로그에서 매칭되는 패키지 정의 탐색
  const pkgDef = MASTER_PACKAGE_CATALOG.find(p =>
    p.aliases.some(a => norm.includes(normalizeOpt(a))) ||
    norm.includes(normalizeOpt(p.name)) ||
    p.matchKeywords.some(k => norm.includes(normalizeOpt(k)) && k.length >= 3)
  );

  // 2. 상대 차량 옵션 목록과 대조하여 매칭 대상 찾기
  let matchedOpposite: string | undefined;
  for (const opp of oppositeOpts) {
    if (isOptionMatched(cleanName, opp)) {
      matchedOpposite = opp;
      break;
    }
  }

  const isMatched = Boolean(matchedOpposite);
  const lines: string[] = [];

  lines.push(`[${cleanName}]`);

  if (pkgDef) {
    lines.push(`📦 패키지 세부 구성: ${pkgDef.items.slice(0, 6).join(', ')}${pkgDef.items.length > 6 ? ' 외' : ''}`);
  }

  lines.push('──────────────────────────────');

  if (direction === 'target_vs_comp') {
    // 내 차(사이드바) 기준
    if (isMatched) {
      lines.push(`✓ 비교 차량 장착 확인됨 (${matchedOpposite})`);
      lines.push('👉 공통 장착 사양으로 시세 동등');
    } else {
      lines.push('🟢 비교 차량에는 미장착 (내 차 우세 사양!)');
      lines.push('👉 비교차 대비 시세 프리미엄 우세 요소');
    }
  } else {
    // 엔카 비교차(우측 카드) 기준
    if (isMatched) {
      lines.push(`✓ 기준 차량(내 차) 장착 확인됨 (${matchedOpposite})`);
      lines.push('👉 공통 장착 사양으로 시세 동등');
    } else {
      lines.push('+ 기준 차량(내 차)에는 미장착된 비교차 전용 옵션');
      lines.push('👉 비교차 시세 상승 요인 (내 차에는 없음)');
    }
  }

  return {
    isMatched,
    matchedOppositeName: matchedOpposite,
    packageName: pkgDef?.name,
    packageItems: pkgDef?.items,
    tooltipText: lines.join('\n')
  };
};
