import React from 'react';
import { getCarColorHex } from '@/utils/carColorMap';

export interface CarColorDotProps {
  color?: string;
  showName?: boolean;
  className?: string;
  dotClassName?: string;
  fallbackText?: string;
}

/**
 * 16진수 색상 코드에서 상대 휘도(Luminance)를 계산하여 밝은 색상인지 판별합니다.
 * (흰색, 밝은 실버, 아이보리, 바닐라, 크림 등)
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
 * 차량 외장 색상 견본 동그라미 (지름 14px, 테두리 1px)
 * 
 * [규칙 및 버그 방지 설계]
 * 1. HTML span의 background-color 대신 SVG <circle> 벡터 그래픽을 사용합니다.
 *    - 브라우저 다크모드/Dark Reader 확장 프로그램이 backgroundColor: #FFFFFF를
 *      검정색(rgb(24, 26, 27))으로 강제 반전시키는 버그를 100% 원천 차단합니다.
 *    - SVG fill은 배경색이 아닌 그래픽 색상이므로 다크모드 엔진이 임의 변경하지 않습니다.
 * 2. 지름 14px, 1px 테두리 원형 점 (헤이딜러 스타일)
 * 3. 밝은 색상(흰색, 아이보리, 실버 등)은 다크모드에서도 선명하게 보이도록
 *    1px 테두리(rgba(156, 163, 175, 0.7))를 보장합니다.
 * 4. 어두운 색상(자주색, 검정, 아메시스트 블랙 등)은 은은한 밝은 테두리(rgba(255, 255, 255, 0.25))를 적용합니다.
 * 5. 색상이 없는 차량(결측값, '-', '미확인' 등)은 점을 절대 표시하지 않습니다.
 */
export const CarColorDot: React.FC<CarColorDotProps> = ({
  color,
  showName = true,
  className = '',
  dotClassName = '',
  fallbackText = '-',
}) => {
  const colorInfo = getCarColorHex(color);

  // 색상이 유효하지 않거나 없는 경우 ➔ 점을 표시하지 않음
  if (!colorInfo) {
    if (fallbackText) {
      return <span className={`text-zinc-400 ${className}`}>{fallbackText}</span>;
    }
    return null;
  }

  // 밝은 색상인지 판별 (흰색, 밝은 실버, 아이보리 등)
  const isLight = isLightHexColor(colorInfo.hex);

  // 다크모드/라이트모드 모두에서 잘 보이도록 테두리 색상 지정
  // 밝은 색상은 명확한 테두리(gray-400), 어두운 색상은 은은한 밝은 테두리
  const borderColor = isLight
    ? 'rgba(156, 163, 175, 0.7)' // gray-400 (다크모드에서도 흰색 원형 윤곽 선명)
    : 'rgba(255, 255, 255, 0.25)';

  // 🌟 다크모드/Dark Reader의 SVG fill 투명화(transparent) 강제 치환 방지:
  // Dark Reader는 단색 fill="#FFFFFF"을 투명으로 날려버리지만, url(#gradient) 그라디언트는 그래픽으로 인식하여 우회(Bypass)합니다.
  const gradientId = `car-dot-grad-${colorInfo.hex.replace(/[^a-zA-Z0-9]/g, '')}`;

  return (
    <span className={`inline-flex items-center gap-1.5 align-middle shrink-0 ${className}`}>
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
          stroke={borderColor}
          strokeWidth="1"
          style={{
            fill: `url(#${gradientId})`,
            fillOpacity: 1,
            forcedColorAdjust: 'none',
          }}
        />
      </svg>
      {showName && (
        <span className="truncate">{colorInfo.name}</span>
      )}
    </span>
  );
};

export default CarColorDot;
