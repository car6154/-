import React, { useMemo } from 'react';
import { TrendingUp } from 'lucide-react';

export interface ScatterPlotCarItem {
  id: string;
  carName: string;
  price: number;
  mileage: number;
  year: number | string;
  accidentType?: string;
}

export interface ScatterPlotSectionProps {
  encarList: ScatterPlotCarItem[];
  mileageKm: number;
  expectedSellPrice: number;
  effectiveSellPrice: number;
  carName: string;
  selectedEncarId: string | null;
  onSelectEncarCar: (carId: string) => void;
}

export const ScatterPlotSection: React.FC<ScatterPlotSectionProps> = ({
  encarList,
  mileageKm,
  expectedSellPrice,
  effectiveSellPrice,
  carName,
  selectedEncarId,
  onSelectEncarCar,
}) => {
  // 가격-주행거리 산점도 & 회귀 추세선 자동 스케일링 계산
  const scatterPlotData = useMemo(() => {
    const validPoints = encarList.filter(c => c.mileage > 0 && c.price > 0);
    const allMil = [...validPoints.map(p => p.mileage), mileageKm].filter(m => m > 0);
    const allPr = [...validPoints.map(p => p.price), expectedSellPrice].filter(p => p > 0);

    if (allMil.length === 0 || allPr.length === 0) {
      return {
        minX: 80000, maxX: 160000, rangeX: 80000,
        minY: 200, maxY: 600, rangeY: 400,
        trendPoints: null,
        points: validPoints
      };
    }

    const rawMinX = Math.min(...allMil);
    const rawMaxX = Math.max(...allMil);
    const padX = Math.max(8000, Math.round((rawMaxX - rawMinX) * 0.15));
    const minX = Math.max(0, Math.floor((rawMinX - padX) / 10000) * 10000);
    const maxX = Math.ceil((rawMaxX + padX) / 10000) * 10000;
    const rangeX = maxX - minX || 1;

    const rawMinY = Math.min(...allPr);
    const rawMaxY = Math.max(...allPr);
    const padY = Math.max(20, Math.round((rawMaxY - rawMinY) * 0.15));
    const minY = Math.max(0, Math.floor((rawMinY - padY) / 50) * 50);
    const maxY = Math.ceil((rawMaxY + padY) / 50) * 50;
    const rangeY = maxY - minY || 1;

    // Linear Regression (y = slope * x + intercept)
    let trendPoints: { x1: number; y1: number; x2: number; y2: number } | null = null;
    if (validPoints.length >= 2) {
      const n = validPoints.length;
      const sumX = validPoints.reduce((a, b) => a + b.mileage, 0);
      const sumY = validPoints.reduce((a, b) => a + b.price, 0);
      const sumXY = validPoints.reduce((a, b) => a + b.mileage * b.price, 0);
      const sumXX = validPoints.reduce((a, b) => a + b.mileage * b.mileage, 0);
      const denom = n * sumXX - sumX * sumX;
      if (denom !== 0) {
        const slope = (n * sumXY - sumX * sumY) / denom;
        const intercept = (sumY - slope * sumX) / n;

        const yAtMinX = slope * minX + intercept;
        const yAtMaxX = slope * maxX + intercept;

        trendPoints = {
          x1: minX,
          y1: yAtMinX,
          x2: maxX,
          y2: yAtMaxX
        };
      }
    }

    return {
      minX,
      maxX,
      rangeX,
      minY,
      maxY,
      rangeY,
      trendPoints,
      points: validPoints
    };
  }, [encarList, mileageKm, expectedSellPrice]);

  return (
    <div className="bg-[#0e0f13] border border-[#1c1d22] rounded-xl p-4 sm:p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-[#1c1d22]">
        <div className="flex items-center gap-1.5 text-xs sm:text-sm font-bold text-white">
          <TrendingUp className="w-4 h-4 text-emerald-400" />
          <span>가격-주행거리 산점도</span>
        </div>
        <div className="flex items-center gap-3 text-[11px]">
          <span className="flex items-center gap-1 text-slate-300">
            <span className="w-2.5 h-2.5 rounded bg-blue-500 inline-block" /> 엔카 매물
          </span>
          <span className="flex items-center gap-1 text-[#cc9166]">
            <span className="w-3 h-0.5 border-t border-dashed border-[#cc9166]" /> 추세선
          </span>
          <span className="flex items-center gap-1 text-yellow-400 font-bold">
            ⭐ 선택차량
          </span>
        </div>
      </div>

      {/* SVG Interactive Scatter Plot (Streamlit 8501 100% 동일 와이드 풀사이즈 산점도) */}
      <div className="p-4 bg-[#0a0b0e] rounded-xl border border-[#1c1d22] overflow-x-auto">
        <svg className="w-full min-w-[700px] h-80 sm:h-96 select-none" viewBox="0 0 960 360">
          {/* Axes and Grid Lines */}
          <line x1="70" y1="30" x2="70" y2="310" stroke="#22242e" strokeWidth="1.2" />
          <line x1="70" y1="310" x2="930" y2="310" stroke="#22242e" strokeWidth="1.2" />

          {/* Y Axis Labels (만원) */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((ratio, idx) => {
            const yVal = Math.round(scatterPlotData.minY + scatterPlotData.rangeY * (1 - ratio));
            const yPos = 30 + ratio * 280;
            return (
              <g key={`y-${idx}`}>
                <text x="58" y={yPos + 4} fill="#828594" fontSize="11" fontWeight="600" textAnchor="end">{yVal}만</text>
                <line x1="70" y1={yPos} x2="930" y2={yPos} stroke="#181a24" strokeWidth="1" strokeDasharray="4,4" />
              </g>
            );
          })}

          {/* X Axis Labels (주행거리 km) */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((ratio, idx) => {
            const xVal = Math.round(scatterPlotData.minX + scatterPlotData.rangeX * ratio);
            const xPos = 70 + ratio * 850;
            return (
              <g key={`x-${idx}`}>
                <text x={xPos} y={332} fill="#828594" fontSize="11" fontWeight="600" textAnchor="middle">
                  {Math.round(xVal / 1000)}k
                </text>
                <line x1={xPos} y1="30" x2={xPos} y2="310" stroke="#181a24" strokeWidth="1" strokeDasharray="3,3" />
              </g>
            );
          })}

          {/* Linear Regression Trendline (점선) */}
          {scatterPlotData.trendPoints && (() => {
            const tp = scatterPlotData.trendPoints;
            const x1Svg = 70 + ((tp.x1 - scatterPlotData.minX) / scatterPlotData.rangeX) * 850;
            const y1Svg = 310 - Math.min(1, Math.max(0, (tp.y1 - scatterPlotData.minY) / scatterPlotData.rangeY)) * 280;
            const x2Svg = 70 + ((tp.x2 - scatterPlotData.minX) / scatterPlotData.rangeX) * 850;
            const y2Svg = 310 - Math.min(1, Math.max(0, (tp.y2 - scatterPlotData.minY) / scatterPlotData.rangeY)) * 280;

            return (
              <line
                x1={x1Svg}
                y1={y1Svg}
                x2={x2Svg}
                y2={y2Svg}
                stroke="#cc9166"
                strokeWidth="2.5"
                strokeDasharray="6,4"
                opacity="0.9"
              />
            );
          })()}

          {/* Encar Data Dots */}
          {scatterPlotData.points.map((c) => {
            const cx = 70 + Math.min(1, Math.max(0, (c.mileage - scatterPlotData.minX) / scatterPlotData.rangeX)) * 850;
            const cy = 310 - Math.min(1, Math.max(0, (c.price - scatterPlotData.minY) / scatterPlotData.rangeY)) * 280;
            const isSelected = c.id === selectedEncarId;

            const dotColor = c.accidentType === '완전무사고'
              ? '#10b981'
              : c.accidentType === '유사고'
              ? '#ef4444'
              : '#f97316';

            return (
              <g key={c.id} className="cursor-pointer group" onClick={() => onSelectEncarCar(c.id)}>
                <circle
                  cx={cx}
                  cy={cy}
                  r={isSelected ? 8 : 6}
                  fill={dotColor}
                  stroke={isSelected ? '#ffffff' : '#0a0b0e'}
                  strokeWidth={isSelected ? 2.5 : 1.5}
                  className="transition-all hover:scale-150"
                />
                <title>{`${c.year}년식 ${c.carName}\n주행거리: ${c.mileage.toLocaleString()}km\n판매가: ${c.price}만원\n사고유무: ${c.accidentType}`}</title>
              </g>
            );
          })}

          {/* 🎯 선택된 차량 산점도 강조 표시 (별 모양 및 외곽선 - Streamlit과 동일하게 선택된 엔카 차량의 실제 좌표에 렌더링) */}
          {(() => {
            const targetCar = selectedEncarId ? encarList.find(c => c.id === selectedEncarId) : null;
            const activeMil = targetCar ? targetCar.mileage : mileageKm;
            const activePrice = targetCar ? targetCar.price : effectiveSellPrice;
            const activeName = targetCar ? targetCar.carName : (carName || '선택차량');

            if (activeMil <= 0 || activePrice <= 0) return null;

            const selCx = 70 + Math.min(1, Math.max(0, (activeMil - scatterPlotData.minX) / scatterPlotData.rangeX)) * 850;
            const selCy = 310 - Math.min(1, Math.max(0, (activePrice - scatterPlotData.minY) / scatterPlotData.rangeY)) * 280;

            return (
              <g>
                {/* Pulsing ring */}
                <circle cx={selCx} cy={selCy} r="16" fill="#eab308" opacity="0.25" className="animate-pulse" />
                
                {/* Star Marker */}
                <path
                  d="M 0 -11 L 3.2 -3.4 L 11 -3.1 L 4.9 2.2 L 6.8 9.8 L 0 5.5 L -6.8 9.8 L -4.9 2.2 L -11 -3.1 L -3.2 -3.4 Z"
                  transform={`translate(${selCx}, ${selCy}) scale(1.3)`}
                  fill="#facc15"
                  stroke="#dc2626"
                  strokeWidth="2"
                />

                {/* Label */}
                <text
                  x={selCx}
                  y={selCy - 16}
                  fill="#ffffff"
                  fontSize="11"
                  fontWeight="bold"
                  textAnchor="middle"
                  className="drop-shadow-md"
                >
                  ⭐ {activeName}
                </text>
              </g>
            );
          })()}
        </svg>
      </div>
      <p className="text-[11px] text-[#717482] text-center">
        💡 주행거리가 짧을수록 가격이 상승하는 자연스러운 감가 곡선(추세선) 대비, 선택 차량({carName || '선택 차량'}{effectiveSellPrice > 0 ? ` ${effectiveSellPrice.toLocaleString()}만` : ''})의 포지셔닝을 실시간 비교합니다.
      </p>
    </div>
  );
};
