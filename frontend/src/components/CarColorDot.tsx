import React, { useId } from 'react';
import { getCarColorHex } from '@/utils/carColorMap';

export interface CarColorDotProps {
  color?: string;
  showName?: boolean;
  className?: string;
  dotClassName?: string;
  fallbackText?: string;
  /** 🌟 [11-06-64] 색상 칩(바탕 채우기 + 글자색 대비 뱃지) 모드 */
  asBadge?: boolean;
}

/**
 * 16진수 색상 코드에서 상대 휘도(Luminance)를 계산하여 밝은 색상인지 판별합니다.
 * (흰색, 밝은 실버, 아이보리, 바닐라, 노란색, 크림 등)
 */
function isLightHexColor(hex: string): boolean {
  const clean = hex.replace('#', '');
  if (clean.length === 6) {
    const r = parseInt(clean.substring(0, 2), 16);
    const g = parseInt(clean.substring(2, 4), 16);
    const b = parseInt(clean.substring(4, 6), 16);
    if (!isNaN(r) && !isNaN(g) && !isNaN(b)) {
      // 상대 휘도 공식: 0.299*R + 0.587*G + 0.114*B (175 이상이면 밝은 색상)
      const lum = 0.299 * r + 0.587 * g + 0.114 * b;
      return lum >= 175;
    }
  }
  const lower = hex.toLowerCase();
  return lower === '#ffffff' || lower.startsWith('#f') || lower === '#c0c0c0';
}

/**
 * 차량 외장 색상 견본 동그라미 (지름 14px, 테두리 1px) 및 색상 칩 뱃지
 * 
 * [규칙 및 버그 방지 설계 - 11-06-64]
 * 1. 그라디언트 ID 고유성 보장 (React useId):
 *    - 같은 색(빨간색, 흰색 등)의 점이 화면에 여러 개 있어도 SVG defs ID 충돌을 원천 차단합니다.
 *    - 인스턴스마다 고유한 linearGradient ID를 생성하여 바탕(fill)이 100% 온전히 채워집니다.
 * 2. 다크모드/Dark Reader SVG fill 투명화 강제 치환 방지:
 *    - forcedColorAdjust: 'none' 및 fillOpacity: 1 유지.
 * 3. 휘도(Luminance) 기반 글자색 대비:
 *    - 밝은 바탕(흰색·아이보리·노란색 등) ➔ 검정 글자 (#09090b)
 *    - 어두운 바탕(검정·빨강·파랑·자주 등) ➔ 흰색 글자 (#ffffff)
 * 4. asBadge 모드 지원:
 *    - hex값으로 뱃지 바탕을 가득 채우고 글자색은 대비되는 색으로 선명하게 표시합니다.
 * 5. 색상이 없는 차량(결측값, '-', '미확인' 등)은 점을 절대 표시하지 않습니다.
 */
export const CarColorDot: React.FC<CarColorDotProps> = ({
  color,
  showName = true,
  className = '',
  dotClassName = '',
  fallbackText = '-',
  asBadge = false,
}) => {
  const reactId = useId();
  const colorInfo = getCarColorHex(color);

  // 색상이 유효하지 않거나 없는 경우 ➔ 점을 표시하지 않음
  if (!colorInfo) {
    if (fallbackText) {
      if (asBadge) {
        return (
          <span className={`px-2.5 py-0.5 rounded font-medium border text-xs text-zinc-400 bg-[#1f222e] border-zinc-700/60 inline-flex items-center shrink-0 ${className}`}>
            {fallbackText}
          </span>
        );
      }
      return <span className={`text-zinc-400 ${className}`}>{fallbackText}</span>;
    }
    return null;
  }

  // 밝은 색상인지 판별 (흰색, 밝은 실버, 아이보리 등)
  const isLight = isLightHexColor(colorInfo.hex);

  // 글자색 대비: 밝은 바탕에는 검정 글자, 어두운 바탕에는 흰색 글자
  const contrastTextColor = isLight ? '#09090b' : '#ffffff';

  // 다크모드/라이트모드 모두에서 잘 보이도록 테두리 색상 지정
  const borderColor = isLight
    ? 'rgba(156, 163, 175, 0.7)' // gray-400 (다크모드에서도 흰색 원형 윤곽 선명)
    : 'rgba(255, 255, 255, 0.25)';

  // [11-06-64] 인스턴스마다 100% 고유한 그라디언트 ID 생성 (특수문자 제거)
  const safeId = reactId.replace(/[^a-zA-Z0-9]/g, '');
  const gradientId = `car-dot-grad-${safeId}`;

  // SVG 원형 점 그래픽
  const dotSvg = (
    <svg
      className={`w-[14px] h-[14px] min-w-[14px] min-h-[14px] shrink-0 ${dotClassName}`}
      viewBox="0 0 14 14"
      xmlns="http://www.w3.org/2000/svg"
      style={{
        display: 'inline-block',
        verticalAlign: 'middle',
        colorScheme: 'only light',
        forcedColorAdjust: 'none',
      }}
    >
      <title>{`${colorInfo.name} (${colorInfo.hex})`}</title>
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor={colorInfo.hex} stopOpacity="1" />
          <stop offset="100%" stopColor={colorInfo.hex} stopOpacity="1" />
        </linearGradient>
      </defs>
      <circle
        cx="7"
        cy="7"
        r="6"
        fill={`url(#${gradientId})`}
        stroke={asBadge ? (isLight ? 'rgba(0, 0, 0, 0.3)' : 'rgba(255, 255, 255, 0.4)') : borderColor}
        strokeWidth="1"
        style={{
          fill: `url(#${gradientId})`,
          fillOpacity: 1,
          forcedColorAdjust: 'none',
        }}
      />
    </svg>
  );

  // 🌟 [11-06-64] 색상 칩(asBadge) 모드: 바탕을 hex 색상으로 가득 채우고 글자색은 대비되는 색으로 표시
  if (asBadge) {
    return (
      <span
        className={`px-2.5 py-0.5 rounded font-medium border text-xs inline-flex items-center gap-1.5 shrink-0 ${className}`}
        style={{
          backgroundColor: colorInfo.hex,
          color: contrastTextColor,
          borderColor: borderColor,
          forcedColorAdjust: 'none',
        }}
      >
        {dotSvg}
        {showName && (
          <span className="truncate font-semibold" style={{ color: contrastTextColor }}>
            {colorInfo.name}
          </span>
        )}
      </span>
    );
  }

  // 기본 인라인 점 + 텍스트 모드
  return (
    <span className={`inline-flex items-center gap-1.5 align-middle shrink-0 ${className}`}>
      {dotSvg}
      {showName && (
        <span className="truncate">{colorInfo.name}</span>
      )}
    </span>
  );
};

export default CarColorDot;
