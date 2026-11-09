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
 * 차량 외장 색상 견본 동그라미 (지름 14px, 테두리 1px)
 * 
 * [규칙]
 * 1. 지름 14px, 1px 테두리 원형 점 (헤이딜러 스타일)
 * 2. 아메시스트 블랙은 #1a1a2e(검은 보라색), 스노우 화이트 펄은 #ffffff 등 실제 색상 반영
 * 3. 흰색 계열은 배경에서 안 보이지 않도록 1px 테두리 필수
 * 4. 색상이 없는 차량(결측값, '-', '미확인' 등)은 점을 절대 표시하지 않음
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
  const hexLower = colorInfo.hex.toLowerCase();
  const isLight =
    hexLower === '#ffffff' ||
    hexLower.startsWith('#f') ||
    hexLower === '#c0c0c0' ||
    hexLower === '#c5c7c9' ||
    hexLower === '#d2d4d7';

  // 다크모드/라이트모드 모두에서 잘 보이도록 테두리 색상 지정
  // 밝은 색상은 약간 어두운 테두리, 어두운 색상은 은은한 밝은 테두리
  const borderColor = isLight
    ? 'rgba(156, 163, 175, 0.7)' // gray-400
    : 'rgba(255, 255, 255, 0.25)';

  return (
    <span className={`inline-flex items-center gap-1.5 align-middle shrink-0 ${className}`}>
      <span
        className={`w-[14px] h-[14px] min-w-[14px] min-h-[14px] rounded-full shrink-0 shadow-sm ${dotClassName}`}
        style={{
          backgroundColor: colorInfo.hex,
          border: `1px solid ${borderColor}`,
        }}
        title={`${colorInfo.name} (${colorInfo.hex})`}
      />
      {showName && (
        <span className="truncate">{colorInfo.name}</span>
      )}
    </span>
  );
};

export default CarColorDot;
