/**
 * 국산차 및 수입차 외장 색상 ➔ 헥스값(Hex) 변환 표 및 매핑 엔진
 * 
 * [규칙]
 * 1. 아메시스트 블랙: 검은 보라색 (#1a1a2e) 필수 지정
 * 2. 흰색 계열: 스노우 화이트 펄, 그랜드 화이트, 크리미 화이트, 폴라 화이트 등 (#FFFFFF 계열)
 * 3. 검정 계열: 팬텀 블랙, 어비스 블랙 펄, 오로라 블랙 펄 등 (#111111~#1a1a2e)
 * 4. 은색/회색 계열: 스틸 그레이, 그라파이트 그레이, 타이거 아이즈 그레이, 문라이트 블루 등
 * 5. 빨강/파랑/기타: 시그널 레드, 마리나 블루, 딥 씨 블루 등
 * 6. "펄", "메탈릭", "투톤" 등의 수식어가 붙어도 기본 색상으로 정규화 매핑
 * 7. 모르는 색상은 중립 회색 (#808080)
 * 8. 결측값('-', '', '미확인' 등) 또는 색상이 없는 경우 null 반환
 */

export const CAR_COLOR_MAP: Record<string, string> = {
  // 1. 흰색 / 진주 계열 (#FFFFFF 계열)
  '스노우 화이트 펄': '#FFFFFF',
  '그랜드 화이트': '#FFFFFF',
  '크리미 화이트': '#FFFFFF',
  '폴라 화이트': '#FFFFFF',
  '클리어 화이트': '#FFFFFF',
  '아틀라스 화이트': '#FFFFFF',
  '세라믹 화이트': '#F8F9FA',
  '퓨어 화이트': '#FFFFFF',
  '순백색': '#FFFFFF',
  '백색': '#FFFFFF',
  '흰색': '#FFFFFF',
  '화이트': '#FFFFFF',
  '스노우 화이트': '#FFFFFF',
  '화이트 크림': '#FAF8F5',
  '진주색': '#FAF8F5',
  '진주': '#FAF8F5',
  '펄화이트': '#FFFFFF',
  '밀키 화이트': '#FDFBF7',
  '글래시어 화이트': '#F8F9FA',
  '스노우 펄': '#FFFFFF',
  '스노우펄': '#FFFFFF',
  '바닐라 화이트': '#FBF9F1',
  '아이보리': '#FFFFF0',
  '크림': '#FAF8F5',

  // 2. 검정 계열 (#111111 ~ #1a1a2e)
  // 🌟 핵심 요구사항: 아메시스트 블랙은 검은 보라색 (#1a1a2e)
  '아메시스트 블랙': '#1a1a2e',
  '아메시스트 블랙 펄': '#1a1a2e',
  '아메시스트': '#1a1a2e',
  '팬텀 블랙': '#111111',
  '팬텀 블랙 펄': '#111111',
  '어비스 블랙 펄': '#0D0F12',
  '어비스 블랙': '#0D0F12',
  '오로라 블랙 펄': '#0C0D0E',
  '오로라 블랙': '#0C0D0E',
  '비크 블랙': '#151516',
  '체리 블랙': '#1B1218',
  '에보니 블랙': '#111111',
  '미드나잇 블랙': '#111111',
  '오닉스 블랙': '#111111',
  '카본 블랙': '#161616',
  '네라 블랙': '#111111',
  '다이아몬드 블랙': '#111111',
  '스페이스 블랙': '#111111',
  '검정색': '#111111',
  '검정': '#111111',
  '블랙': '#111111',
  '흑색': '#111111',

  // 3. 은색 / 회색 계열
  '스틸 그레이': '#71767B',
  '그라파이트 그레이': '#4A4D52',
  '타이거 아이즈 그레이': '#5C5854',
  '문라이트 블루': '#2C3E50', // 청회색/달빛블루
  '플래티넘 실버': '#C5C7C9',
  '슬릭 실버': '#D2D4D7',
  '하이퍼 메탈릭': '#A8ADB2',
  '하이퍼 실버': '#B8BCC0',
  '사이버 그레이': '#9CA3AF',
  '사이버 그레이 메탈릭': '#9CA3AF',
  '아마존 그레이': '#4B5358',
  '햄프턴 그레이': '#5E646B',
  '인터스텔라 그레이': '#4B5056',
  '판테라 메탈': '#4E5359',
  '그래비티 그레이': '#43484E',
  '세라믹 실버': '#B8BCC0',
  '아이언 그레이': '#5E6367',
  '카본 그레이': '#3E4246',
  '마그네틱 그레이': '#4D5156',
  '플래티넘 그레이': '#63666A',
  '미네랄 실버': '#A3A8AD',
  '어반 그레이': '#54585E',
  '메탈릭 실버': '#BEC2C7',
  '실버': '#C0C0C0',
  '은색': '#C0C0C0',
  '밝은 실버': '#D2D4D7',
  '밝은 은색': '#D2D4D7',
  '은회색': '#C5CBD3',
  '그레이': '#6B7280',
  '회색': '#6B7280',
  '쥐색': '#4B5563',
  '진회색': '#374151',
  '차콜': '#374151',
  '다크그레이': '#374151',
  '먹색': '#2E3440',
  '티타늄 실버': '#8A8D8F',
  '티타늄 그레이': '#595C5F',

  // 4. 빨강 / 와인 / 주황 계열
  '시그널 레드': '#C41E3A',
  '런웨이 레드': '#A81C26',
  '파이어리 레드': '#B91C1C',
  '패션 레드': '#D92534',
  '마그마 레드': '#C53030',
  '크림슨 레드': '#990000',
  '벨벳 레드': '#8B1E2B',
  '레드': '#DC2626',
  '빨강': '#DC2626',
  '적색': '#DC2626',
  '빨간색': '#DC2626',
  '버건디': '#722F37',
  '와인': '#722F37',
  '자주': '#701A75',
  '보라': '#6B21A8',
  '퍼플': '#6B21A8',
  '주황': '#EA580C',
  '오렌지': '#EA580C',

  // 5. 파랑 / 네이비 / 하늘 계열
  '마리나 블루': '#1E40AF',
  '딥 씨 블루': '#102A45',
  '옥스포드 블루': '#1B365D',
  '코스모스 블루': '#1E3A8A',
  '미드나잇 블루': '#191970',
  '인텐스 블루': '#1D4ED8',
  '모닝 블루': '#3B82F6',
  '블루': '#2563EB',
  '파랑': '#2563EB',
  '청색': '#2563EB',
  '파란색': '#2563EB',
  '네이비': '#1E3A8A',
  '남색': '#1E3A8A',
  '다크블루': '#1E3A8A',
  '하늘색': '#38BDF8',
  '하늘': '#38BDF8',
  '스카이 블루': '#38BDF8',
  '스카이': '#38BDF8',
  '청옥색': '#008B8B',
  '청록': '#008B8B',

  // 6. 갈색 / 베이지 / 기타
  '듄 베이지': '#D4C5B9',
  '사하라 베이지': '#E1D5C1',
  '골든 베이지': '#D8C3A5',
  '마운틴 브라운': '#5C4033',
  '리치 에스프레소': '#3D2B1F',
  '카푸치노 브라운': '#6F4E37',
  '베이지': '#D2B48C',
  '브라운': '#78350F',
  '갈색': '#78350F',
  '밤색': '#5C3A21',
  '초코': '#5C3A21',
  '초록': '#15803D',
  '녹색': '#15803D',
  '그린': '#15803D',
  '카키': '#4D533C',
  '올리브': '#556B2F',
  '노랑': '#EAB308',
  '노란색': '#EAB308',
  '옐로우': '#EAB308',
  '골드': '#EAB308',
  '금색': '#EAB308',
};

export interface CarColorHexInfo {
  hex: string;
  name: string;
}

/**
 * 외장 색상 이름을 분석하여 실제 색깔 헥스값(Hex)과 정규화된 이름을 반환합니다.
 * 결측값(빈 값, '-', '미확인' 등)인 경우 null을 반환하여 점을 표시하지 않도록 합니다.
 */
export function getCarColorHex(rawColor?: string): CarColorHexInfo | null {
  if (!rawColor) return null;
  const trimmed = rawColor.trim();
  if (
    !trimmed ||
    trimmed === '-' ||
    trimmed === '미확인' ||
    trimmed === '정보없음' ||
    trimmed === '미기재' ||
    trimmed === '색상' ||
    trimmed === '무채색'
  ) {
    return null;
  }

  // 1. 1:1 완벽 일치 검사
  if (CAR_COLOR_MAP[trimmed]) {
    return { hex: CAR_COLOR_MAP[trimmed], name: trimmed };
  }

  // 2. 대소문자 무시 일치 검사
  const lower = trimmed.toLowerCase();
  for (const [k, v] of Object.entries(CAR_COLOR_MAP)) {
    if (k.toLowerCase() === lower) {
      return { hex: v, name: trimmed };
    }
  }

  // 3. 접미사 ("펄", "메탈릭", "투톤" 등) 제거 후 매칭
  // "이름에 '펄', '메탈릭'이 붙어도 기본 색으로 봅니다."
  const stripped = trimmed
    .replace(/(펄|메탈릭|투톤|pearl|metallic|two-tone)/gi, '')
    .trim();
  if (stripped && CAR_COLOR_MAP[stripped]) {
    return { hex: CAR_COLOR_MAP[stripped], name: trimmed };
  }

  // 4. 핵심 고유명사 및 브랜드 대표 컬러 우선 검사
  // 🌟 [최우선] 아메시스트 블랙은 검은 보라색 (#1a1a2e)
  if (lower.includes('아메시스트') || lower.includes('amethyst')) {
    return { hex: '#1a1a2e', name: trimmed };
  }
  if (
    lower.includes('스노우 화이트') ||
    lower.includes('그랜드 화이트') ||
    lower.includes('크리미 화이트') ||
    lower.includes('폴라 화이트') ||
    lower.includes('클리어 화이트') ||
    lower.includes('아틀라스 화이트')
  ) {
    return { hex: '#FFFFFF', name: trimmed };
  }
  if (
    lower.includes('팬텀 블랙') ||
    lower.includes('어비스 블랙') ||
    lower.includes('오로라 블랙') ||
    lower.includes('비크 블랙')
  ) {
    return { hex: '#111111', name: trimmed };
  }
  if (lower.includes('스틸 그레이') || lower.includes('steel gray')) {
    return { hex: '#71767B', name: trimmed };
  }
  if (lower.includes('그라파이트') || lower.includes('graphite')) {
    return { hex: '#4A4D52', name: trimmed };
  }
  if (lower.includes('타이거 아이즈') || lower.includes('tiger eyes')) {
    return { hex: '#5C5854', name: trimmed };
  }
  if (lower.includes('문라이트 블루') || lower.includes('문라이트')) {
    return { hex: '#2C3E50', name: trimmed };
  }
  if (lower.includes('시그널 레드') || lower.includes('signal red')) {
    return { hex: '#C41E3A', name: trimmed };
  }
  if (lower.includes('런웨이 레드') || lower.includes('runway red')) {
    return { hex: '#A81C26', name: trimmed };
  }
  if (lower.includes('마리나 블루') || lower.includes('marina blue')) {
    return { hex: '#1E40AF', name: trimmed };
  }
  if (lower.includes('딥 씨 블루') || lower.includes('deep sea')) {
    return { hex: '#102A45', name: trimmed };
  }

  // 5. 일반 색상 계열 키워드 포함 검사
  // 5-1. 검정 계열
  if (lower.includes('검정') || lower.includes('블랙') || lower.includes('black') || lower.includes('흑색')) {
    return { hex: '#111111', name: trimmed };
  }
  // 5-2. 흰색 / 진주 계열
  if (
    lower.includes('흰색') ||
    lower.includes('화이트') ||
    lower.includes('white') ||
    lower.includes('백색') ||
    lower.includes('진주') ||
    lower.includes('아이보리') ||
    lower.includes('크림')
  ) {
    return { hex: '#FFFFFF', name: trimmed };
  }
  // 5-3. 은색 계열
  if (lower.includes('은회색') || lower.includes('은색') || lower.includes('실버') || lower.includes('silver')) {
    return { hex: '#C0C0C0', name: trimmed };
  }
  // 5-4. 차콜 / 쥐색 / 다크그레이
  if (lower.includes('차콜') || lower.includes('charcoal') || lower.includes('진회색') || lower.includes('다크그레이') || lower.includes('먹색')) {
    return { hex: '#374151', name: trimmed };
  }
  // 5-5. 회색 / 그레이
  if (lower.includes('쥐색') || lower.includes('회색') || lower.includes('그레이') || lower.includes('gray') || lower.includes('메탈') || lower.includes('티타늄')) {
    return { hex: '#6B7280', name: trimmed };
  }
  // 5-6. 빨강 계열
  if (lower.includes('빨강') || lower.includes('레드') || lower.includes('red') || lower.includes('적색')) {
    return { hex: '#DC2626', name: trimmed };
  }
  // 5-7. 와인 / 버건디 / 자주 / 보라 계열
  if (lower.includes('와인') || lower.includes('버건디') || lower.includes('자주') || lower.includes('보라') || lower.includes('퍼플')) {
    return { hex: '#722F37', name: trimmed };
  }
  // 5-8. 남색 / 네이비
  if (lower.includes('남색') || lower.includes('네이비') || lower.includes('navy')) {
    return { hex: '#1E3A8A', name: trimmed };
  }
  // 5-9. 파랑 / 블루
  if (lower.includes('파랑') || lower.includes('블루') || lower.includes('blue') || lower.includes('청색')) {
    return { hex: '#2563EB', name: trimmed };
  }
  // 5-10. 하늘색 / 스카이
  if (lower.includes('하늘') || lower.includes('스카이') || lower.includes('sky')) {
    return { hex: '#38BDF8', name: trimmed };
  }
  // 5-11. 베이지 계열
  if (lower.includes('베이지') || lower.includes('beige')) {
    return { hex: '#D2B48C', name: trimmed };
  }
  // 5-12. 갈색 / 브라운
  if (lower.includes('갈색') || lower.includes('브라운') || lower.includes('brown') || lower.includes('밤색') || lower.includes('초코')) {
    return { hex: '#78350F', name: trimmed };
  }
  // 5-13. 초록 / 녹색 / 그린
  if (lower.includes('초록') || lower.includes('녹색') || lower.includes('그린') || lower.includes('green') || lower.includes('카키') || lower.includes('올리브')) {
    return { hex: '#15803D', name: trimmed };
  }
  // 5-14. 노랑 / 골드
  if (lower.includes('노랑') || lower.includes('옐로우') || lower.includes('yellow') || lower.includes('골드') || lower.includes('금색')) {
    return { hex: '#EAB308', name: trimmed };
  }
  // 5-15. 주황 / 오렌지
  if (lower.includes('주황') || lower.includes('오렌지') || lower.includes('orange')) {
    return { hex: '#EA580C', name: trimmed };
  }

  // 6. 모르는 색상은 중립 회색 (#808080)
  return { hex: '#808080', name: trimmed };
}
