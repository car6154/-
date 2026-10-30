export interface CarColorStyle {
  dot: string;
  textColor: string;
  bgColor: string;
  borderColor: string;
  displayName: string;
}

/**
 * 차량 색상 문자열을 판정하여 점(이모지), 글자색, 배경색, 테두리색을 반환하는 공용 유틸리티
 * 
 * [설계 원칙]
 * 1. 계열 순서: 은색, 쥐색, 차콜, 검정 4단계를 명암 순으로 명확히 구분
 *    - 은색: 밝은 은빛 배경 (#e2e8f0) + 진한 텍스트 (#0f172a)
 *    - 쥐색/회색: 중간 회색 배경 (#475569) + 밝은 텍스트 (#f8fafc)
 *    - 차콜/진회색: 딥 차콜 배경 (#1e293b) + 연한 텍스트 (#e2e8f0)
 *    - 검정: 순수 블랙 배경 (#050505) + 흰색 텍스트 (#ffffff)
 * 2. 대비 보장: 밝은 배경(흰색, 진주, 은색, 노랑, 베이지, 하늘)에는 반드시 어두운 글자,
 *              어두운 배경(검정, 차콜, 쥐색, 네이비, 와인, 갈색, 초록)에는 반드시 밝은 글자 적용
 * 3. 우선순위: 구체적인 단어(은회색, 다크그레이, 차콜 등)를 광범위한 단어(회색, 그레이)보다 먼저 검사
 */
export function getCarColorStyle(rawColor?: string): CarColorStyle {
  const trimmed = (rawColor || '').trim();
  
  // 1. 결측값 / 미확인 / 중립 기본값
  if (!trimmed || trimmed === '-' || trimmed === '색상' || trimmed === '미확인' || trimmed === '정보없음' || trimmed === '미기재') {
    return {
      dot: '⚫',
      textColor: '#94a3b8',
      bgColor: '#1f222e',
      borderColor: '#334155',
      displayName: trimmed || '색상'
    };
  }

  const c = trimmed.toLowerCase();

  // 2. 은색 계열 (회색보다 먼저 검사하여 뭉개짐 방지)
  if (c.includes('은회색') || c.includes('은색') || c.includes('실버') || c.includes('silver')) {
    return {
      dot: '💿',
      textColor: '#0f172a',
      bgColor: '#e2e8f0',
      borderColor: '#cbd5e1',
      displayName: trimmed
    };
  }

  // 3. 차콜 / 다크그레이 / 진회색 (회색보다 먼저 검사, 검정보다 한 톤 밝고 쥐색보다 어두움)
  if (c.includes('차콜') || c.includes('charcoal') || c.includes('다크그레이') || c.includes('darkgray') || c.includes('dark gray') || c.includes('진회색') || c.includes('먹색')) {
    return {
      dot: '⬛',
      textColor: '#e2e8f0',
      bgColor: '#1e293b',
      borderColor: '#334155',
      displayName: trimmed
    };
  }

  // 4. 쥐색 / 회색 계열 (중간 회색 배경)
  if (c.includes('쥐색') || c.includes('회색') || c.includes('그레이') || c.includes('gray') || c.includes('grey') || c.includes('메탈') || c.includes('metal') || c.includes('티타늄') || c.includes('titanium')) {
    return {
      dot: '🩶',
      textColor: '#f8fafc',
      bgColor: '#475569',
      borderColor: '#64748b',
      displayName: trimmed
    };
  }

  // 5. 검정 계열 (순수 블랙)
  if (c.includes('검정') || c.includes('블랙') || c.includes('black') || c.includes('흑색')) {
    return {
      dot: '⚫',
      textColor: '#ffffff',
      bgColor: '#050505',
      borderColor: '#27272a',
      displayName: trimmed
    };
  }

  // 6. 진주 / 아이보리 / 펄 계열 (흰색보다 먼저 검사하여 따뜻한 크림톤 부여)
  if (c.includes('진주') || c.includes('펄') || c.includes('pearl') || c.includes('아이보리') || c.includes('ivory') || c.includes('크림') || c.includes('cream')) {
    return {
      dot: '🦪',
      textColor: '#1c1917',
      bgColor: '#fef3c7',
      borderColor: '#fde047',
      displayName: trimmed
    };
  }

  // 7. 흰색 계열 (순백 배경)
  if (c.includes('흰색') || c.includes('화이트') || c.includes('white') || c.includes('백색')) {
    return {
      dot: '⚪',
      textColor: '#09090b',
      bgColor: '#ffffff',
      borderColor: '#e4e4e7',
      displayName: trimmed
    };
  }

  // 8. 하늘빛 계열 (파랑보다 먼저 검사하여 밝은 배경 처리)
  if (c.includes('하늘') || c.includes('스카이') || c.includes('sky')) {
    return {
      dot: '🩵',
      textColor: '#0f172a',
      bgColor: '#bae6fd',
      borderColor: '#7dd3fc',
      displayName: trimmed
    };
  }

  // 9. 남색 / 네이비 계열 (파랑보다 어두운 미드나잇 네이비)
  if (c.includes('남색') || c.includes('네이비') || c.includes('navy') || c.includes('다크블루') || c.includes('dark blue')) {
    return {
      dot: '🔷',
      textColor: '#f8fafc',
      bgColor: '#0f172a',
      borderColor: '#1e3a8a',
      displayName: trimmed
    };
  }

  // 10. 파랑 계열 (중간 로얄 블루)
  if (c.includes('파랑') || c.includes('블루') || c.includes('blue') || c.includes('청색')) {
    return {
      dot: '🔵',
      textColor: '#ffffff',
      bgColor: '#1d4ed8',
      borderColor: '#3b82f6',
      displayName: trimmed
    };
  }

  // 11. 와인 / 자주 / 버건디 계열 (빨강보다 어두운 계열 먼저 검사)
  if (c.includes('와인') || c.includes('wine') || c.includes('자주') || c.includes('버건디') || c.includes('burgundy') || c.includes('보라') || c.includes('퍼플') || c.includes('purple')) {
    return {
      dot: '🍷',
      textColor: '#fce7f3',
      bgColor: '#701a75',
      borderColor: '#86198f',
      displayName: trimmed
    };
  }

  // 12. 빨강 / 주황 계열
  if (c.includes('빨강') || c.includes('레드') || c.includes('red') || c.includes('적색') || c.includes('주황') || c.includes('오렌지') || c.includes('orange')) {
    return {
      dot: '🔴',
      textColor: '#ffffff',
      bgColor: '#dc2626',
      borderColor: '#ef4444',
      displayName: trimmed
    };
  }

  // 13. 베이지 계열 (갈색보다 먼저 검사하여 밝은 배경 처리)
  if (c.includes('베이지') || c.includes('beige')) {
    return {
      dot: '🍦',
      textColor: '#451a03',
      bgColor: '#fef3c7',
      borderColor: '#f59e0b',
      displayName: trimmed
    };
  }

  // 14. 갈색 계열 (어두운 브라운/초코)
  if (c.includes('갈색') || c.includes('브라운') || c.includes('brown') || c.includes('초코') || c.includes('밤색')) {
    return {
      dot: '🟤',
      textColor: '#fef3c7',
      bgColor: '#78350f',
      borderColor: '#92400e',
      displayName: trimmed
    };
  }

  // 15. 초록 계열 (포레스트 그린/카키)
  if (c.includes('초록') || c.includes('그린') || c.includes('green') || c.includes('국방') || c.includes('카키') || c.includes('khaki') || c.includes('올리브') || c.includes('olive') || c.includes('연두')) {
    return {
      dot: '🟢',
      textColor: '#f0fdf4',
      bgColor: '#14532d',
      borderColor: '#22c55e',
      displayName: trimmed
    };
  }

  // 16. 노랑 / 골드 계열 (밝은 배경)
  if (c.includes('노랑') || c.includes('노란') || c.includes('옐로우') || c.includes('yellow') || c.includes('골드') || c.includes('gold') || c.includes('금색')) {
    return {
      dot: '🟡',
      textColor: '#713f12',
      bgColor: '#fde047',
      borderColor: '#eab308',
      displayName: trimmed
    };
  }

  // 17. 기타 미분류 색상 (중립 회색 스타일 유지)
  return {
    dot: '⚫',
    textColor: '#e2e8f0',
    bgColor: '#1f222e',
    borderColor: '#334155',
    displayName: trimmed
  };
}
