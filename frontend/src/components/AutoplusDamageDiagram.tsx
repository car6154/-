import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp, X, Wrench, AlertCircle } from 'lucide-react';
import type { ChaolmaCarHistory } from '@/services/chaolmaService';

export interface AutoplusDamageDiagramProps {
  history?: ChaolmaCarHistory;
}

// 28개 승용차 부위 매핑 (오토플러스 carmap 1:1)
export const CARMAP_NAMES: Record<string, string> = {
  '01': '앞범퍼',
  '02': '뒤범퍼',
  '03': '보닛',
  '04': '트렁크리드',
  '05': '백도어',
  '06': '앞도어(좌)',
  '07': '앞도어(우)',
  '08': '뒷도어(좌)',
  '09': '뒷도어(우)',
  '10': '앞펜더(좌)',
  '11': '앞펜더(우)',
  '12': '뒤펜더(좌)',
  '13': '뒤펜더(우)',
  '14': '앞유리',
  '15': '선루프',
  '16': '루프',
  '17': '슬라이딩도어(좌)',
  '18': '슬라이딩도어(우)',
  '19': '뒷유리',
  '20': '라디에이터 그릴',
  '21': '헤드램프(좌)',
  '22': '헤드램프(우)',
  '23': '리어컴비네이션램프(좌)',
  '24': '리어컴비네이션램프(우)',
  '25': '사이드스텝(좌)',
  '26': '사이드스텝(우)',
  '27': '센터필러(좌)',
  '28': '센터필러(우)',
};

// 28개 승용차 부위 CSS 위치 매핑 (오토플러스 style.css 1:1)
export const CARMAP_STYLES: Record<string, React.CSSProperties> = {
  '01': { top: '6.3%', left: 0, right: 0, margin: '0 auto' },
  '02': { bottom: '-0.5rem', left: 0, right: 0, margin: '0 auto' },
  '03': { top: '21%', left: 0, right: 0, margin: '0 auto' },
  '04': { bottom: '2rem', left: 0, right: 0, margin: '0 auto' },
  '05': { top: 'auto', left: 0, right: 0, margin: '0 auto', bottom: '17%' },
  '06': { top: '43%', left: '50%', right: 'auto', marginLeft: '-42%' },
  '07': { top: '43%', right: '50%', left: 'auto', marginRight: '-42%' },
  '08': { top: '54%', left: '50%', right: 'auto', marginLeft: '-42%' },
  '09': { top: '54%', right: '50%', left: 'auto', marginRight: '-42%' },
  '10': { top: '25%', left: '50%', right: 'auto', marginLeft: '-37.8%' },
  '11': { top: '25%', right: '50%', left: 'auto', marginRight: '-37.8%' },
  '12': { top: 'auto', left: '50%', right: 'auto', marginLeft: '-38%', bottom: '22%' },
  '13': { top: 'auto', right: '50%', left: 'auto', marginRight: '-38%', bottom: '22%' },
  '14': { top: '37%', right: 0, left: 0, margin: '0 auto' },
  '15': { top: '50%', right: 0, left: 0, margin: '0 auto' },
  '16': { bottom: '37%', right: 0, left: 0, margin: '0 auto' },
  '17': { top: '59%', left: '50%', right: 'auto', marginLeft: '-42%' },
  '18': { top: '59%', right: '50%', left: 'auto', marginRight: '-42%' },
  '19': { bottom: '26%', right: 0, left: 0, margin: '0 auto' },
  '20': { top: '0.8rem', left: 0, right: 0, margin: '0 auto' },
  '21': { top: '0.8rem', left: '50%', marginLeft: '-6rem' },
  '22': { top: '0.8rem', right: '50%', marginRight: '-6rem' },
  '23': { top: 'auto', left: '50%', marginLeft: '-14%', bottom: '5.8%' },
  '24': { top: 'auto', right: '50%', marginRight: '-14%', bottom: '5.8%' },
  '25': { top: '51%', left: '50%', marginLeft: '-49%' },
  '26': { top: '51%', right: '50%', marginRight: '-49%' },
  '27': { top: '52%', left: '50%', marginLeft: '-31%' },
  '28': { top: '52%', right: '50%', marginRight: '-31%' },
};

export const AutoplusDamageDiagram: React.FC<AutoplusDamageDiagramProps> = ({ history }) => {
  const [selectedAccidentDate, setSelectedAccidentDate] = useState<string | 'all'>('all');
  const [isSummaryExpanded, setIsSummaryExpanded] = useState<boolean>(true);
  const [detailModalData, setDetailModalData] = useState<{ date: string; desc: string } | null>(null);

  const accidents = useMemo(() => history?.accident_histories || [], [history]);

  // 날짜별 파싱 데이터
  const parsedAccidents = useMemo(() => {
    return accidents.map(acc => {
      const rawDate = acc.date || '';
      const formattedDate = rawDate.length >= 8 
        ? `${rawDate.slice(0, 4)}-${rawDate.slice(4, 6)}-${rawDate.slice(6, 8)}` 
        : rawDate;

      // dismantle codes
      const dismantleCodes = (acc.dismantle_codes || '')
        .split(',')
        .map(s => s.trim())
        .filter(Boolean);

      // paint codes
      const paintCodes = (acc.paint_codes || '')
        .split(',')
        .map(s => s.trim())
        .filter(Boolean);

      return {
        rawDate,
        formattedDate,
        dismantleCodes,
        paintCodes,
        dismantleParts: acc.dismantle_parts || [],
        paintParts: acc.paint_parts || [],
        repairDetails: acc.repair_details || '',
        accType: acc.acc_type || 'my',
        repairCost: acc.repair_cost || 0,
      };
    });
  }, [accidents]);

  // 전개도 핀 상태 계산 (누적 또는 선택된 일자 기준)
  const pinStates = useMemo(() => {
    const states: Record<string, 'repair-type01' | 'repair-type02' | 'repair-type03'> = {};

    const targetList = selectedAccidentDate === 'all'
      ? parsedAccidents
      : parsedAccidents.filter(a => a.rawDate === selectedAccidentDate);

    targetList.forEach(item => {
      // 탈착 코드 반영
      item.dismantleCodes.forEach(code => {
        if (states[code] === 'repair-type02') {
          states[code] = 'repair-type03'; // 도장+탈착
        } else if (states[code] !== 'repair-type03') {
          states[code] = 'repair-type01'; // 탈착
        }
      });

      // 도장 코드 반영
      item.paintCodes.forEach(code => {
        if (states[code] === 'repair-type01') {
          states[code] = 'repair-type03'; // 탈착+도장
        } else if (states[code] !== 'repair-type03') {
          states[code] = 'repair-type02'; // 도장
        }
      });
    });

    return states;
  }, [parsedAccidents, selectedAccidentDate]);

  // 탈착/도장 총 건수 계산
  const { totalDismantle, totalPaint } = useMemo(() => {
    let dCount = 0;
    let pCount = 0;
    parsedAccidents.forEach(acc => {
      dCount += acc.dismantleCodes.length;
      pCount += acc.paintCodes.length;
    });

    // fallback으로 백엔드에서 전달된 카운트 우선 사용
    return {
      totalDismantle: history?.total_dismantle_count ?? dCount,
      totalPaint: history?.total_paint_count ?? pCount,
    };
  }, [parsedAccidents, history]);

  // 자세히 보기 팝업 데이터 파싱 (교환/판금은 상단 빨간색, 탈착/도장은 하단 일반)
  const detailModalParts = useMemo(() => {
    if (!detailModalData?.desc) return { major: [], minor: [] };
    const rawParts = detailModalData.desc.split(/(?<=\)),/g).map(s => s.trim()).filter(Boolean);
    const major: string[] = [];
    const minor: string[] = [];

    rawParts.forEach(p => {
      if (!p.includes('탈착') && !p.includes('도장')) {
        major.push(p);
      } else {
        minor.push(p);
      }
    });

    return { major, minor };
  }, [detailModalData]);

  return (
    <div className="w-full bg-white text-zinc-900 rounded-xl overflow-hidden border border-zinc-200 shadow-sm font-sans">
      
      {/* 1. 상단 안내문구 */}
      <div className="px-5 py-2.5 bg-zinc-50 border-b border-zinc-200 text-xs text-zinc-500 flex items-center justify-between">
        <span>· 보험사고 이력은 최근 10건의 사고만 표시됩니다.</span>
        {accidents.length > 0 && (
          <div className="flex items-center gap-1.5 text-[11px] font-mono">
            <span className="text-zinc-400">기준 사고:</span>
            <select
              value={selectedAccidentDate}
              onChange={(e) => setSelectedAccidentDate(e.target.value)}
              className="bg-white border border-zinc-300 rounded px-2 py-0.5 text-xs text-zinc-700 font-medium focus:outline-none"
            >
              <option value="all">전체 누적 사고 ({accidents.length}건)</option>
              {parsedAccidents.map((acc, idx) => (
                <option key={idx} value={acc.rawDate}>
                  {acc.formattedDate} [{acc.accType === 'other' ? '타차가해' : '내차피해'}]
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* 2. 자동차 전개도 헤더 */}
      <div className="py-2.5 px-4 border-b border-zinc-200 bg-white text-center text-xs sm:text-sm font-bold text-zinc-700">
        자동차 전개도
      </div>

      {/* 3. 자동차 전개도 본체 */}
      <div className="relative w-full max-w-[690px] mx-auto p-4 flex flex-col items-center">
        {/* 중앙 전개도 배경 및 핀 컨테이너 */}
        <div className="relative w-full aspect-[760/881] max-w-[550px] mx-auto select-none">
          <img
            src="/images/car_type01_bg.png"
            alt="자동차 전개도"
            className="w-full h-full object-contain pointer-events-none"
          />

          {/* 28개 부위 핀 렌더링 */}
          {Object.entries(CARMAP_STYLES).map(([code, style]) => {
            const state = pinStates[code];
            if (!state) return null;

            const name = CARMAP_NAMES[code] || `부위 ${code}`;
            const isType02 = state === 'repair-type02'; // 도장 (빨강)
            const isType03 = state === 'repair-type03'; // 탈착+도장 (초록)

            let iconSrc = '/images/map_dot01.svg';
            let bgColor = '#579AFF';
            let label = '탈착';

            if (isType02) {
              iconSrc = '/images/map_dot02.svg';
              bgColor = '#FF3F3F';
              label = '도장';
            } else if (isType03) {
              iconSrc = '/images/map_dot03.svg';
              bgColor = '#13B78B';
              label = '탈착+도장';
            }

            return (
              <div
                key={code}
                style={{ ...style, position: 'absolute' }}
                className="w-[28px] h-[28px] sm:w-[33px] sm:h-[33px] flex items-center justify-center cursor-pointer transition-transform duration-150 hover:scale-125 z-10"
                title={`${name} (${label})`}
              >
                <div
                  className="w-full h-full rounded-full flex items-center justify-center shadow-md border border-white"
                  style={{ backgroundColor: bgColor }}
                >
                  <img src={iconSrc} alt={label} className="w-[14px] h-[14px] sm:w-[17px] sm:h-[17px]" />
                </div>
              </div>
            );
          })}
        </div>

        {/* 하단 범례 */}
        <div className="flex items-center justify-center gap-5 mt-4 pt-3 border-t border-zinc-100 w-full text-xs text-zinc-700 font-medium">
          <div className="flex items-center gap-1.5">
            <span className="w-5 h-5 rounded-full bg-[#579AFF] flex items-center justify-center shadow-sm">
              <img src="/images/map_dot01.svg" alt="탈착" className="w-3 h-3" />
            </span>
            <span>탈착</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-5 h-5 rounded-full bg-[#FF3F3F] flex items-center justify-center shadow-sm">
              <img src="/images/map_dot02.svg" alt="도장" className="w-3 h-3" />
            </span>
            <span>도장</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-5 h-5 rounded-full bg-[#13B78B] flex items-center justify-center shadow-sm">
              <img src="/images/map_dot03.svg" alt="탈착+도장" className="w-3 h-3" />
            </span>
            <span>탈착+도장</span>
          </div>
        </div>
      </div>

      {/* 4. 수리내역 요약 테이블 (스크린샷 2 원본 1:1) */}
      <div className="border-t border-zinc-200">
        {/* 타이틀 헤더 */}
        <div className="py-2.5 px-4 bg-zinc-50 border-b border-zinc-200 text-center text-xs sm:text-sm font-bold text-zinc-800">
          수리내역 요약
        </div>

        {/* 통계 요약 (탈착 N건 | 도장 M건) */}
        <div className="grid grid-cols-2 divide-x divide-zinc-200 border-b border-zinc-200 text-xs sm:text-sm">
          <div className="flex items-center justify-between px-6 py-2.5 bg-white">
            <span className="text-zinc-600 font-medium">탈착</span>
            <span className="font-bold text-zinc-900 font-mono">{totalDismantle} 건</span>
          </div>
          <div className="flex items-center justify-between px-6 py-2.5 bg-white">
            <span className="text-zinc-600 font-medium">도장</span>
            <span className="font-bold text-zinc-900 font-mono">{totalPaint} 건</span>
          </div>
        </div>

        {/* 일자별 수리내역 리스트 */}
        {isSummaryExpanded && (
          <div className="divide-y divide-zinc-200">
            {parsedAccidents.map((acc, idx) => {
              const hasDismantle = acc.dismantleParts.length > 0;
              const hasPaint = acc.paintParts.length > 0;
              const isCostUndetermined = !hasDismantle && !hasPaint && acc.repairCost === 0;

              return (
                <div key={idx} className="bg-white">
                  {/* 일자 헤더 + 자세히보기 버튼 */}
                  <div className="flex items-center justify-between px-4 sm:px-6 py-2.5 bg-zinc-50/70 border-b border-zinc-100 text-xs font-semibold text-zinc-800">
                    <span className="font-mono text-zinc-700 tracking-wide">{acc.formattedDate}</span>
                    {acc.repairDetails ? (
                      <button
                        type="button"
                        onClick={() => setDetailModalData({ date: acc.formattedDate, desc: acc.repairDetails })}
                        className="text-zinc-500 hover:text-zinc-900 font-normal hover:underline flex items-center gap-0.5 cursor-pointer text-[11px]"
                      >
                        자세히보기 &gt;
                      </button>
                    ) : (
                      <span className="text-zinc-400 text-[11px] font-normal">자세히보기 &gt;</span>
                    )}
                  </div>

                  {/* 탈착 및 도장 부위 테이블 */}
                  <div className="divide-y divide-zinc-100 text-xs">
                    {/* 탈착 행 */}
                    <div className="grid grid-cols-12 px-4 sm:px-6 py-2.5 items-start">
                      <div className="col-span-3 sm:col-span-2 text-zinc-600 font-medium pt-0.5">
                        탈착
                      </div>
                      <div className="col-span-9 sm:col-span-10 text-zinc-800 space-y-0.5">
                        {hasDismantle ? (
                          acc.dismantleParts.map((part, pIdx) => (
                            <p key={pIdx} className="leading-snug">{part}</p>
                          ))
                        ) : isCostUndetermined ? (
                          <p className="text-zinc-500 leading-snug">수리(견적)비용 : 미확정</p>
                        ) : (
                          <p className="text-zinc-400 leading-snug">-</p>
                        )}
                      </div>
                    </div>

                    {/* 도장 행 */}
                    <div className="grid grid-cols-12 px-4 sm:px-6 py-2.5 items-start">
                      <div className="col-span-3 sm:col-span-2 text-zinc-600 font-medium pt-0.5">
                        도장
                      </div>
                      <div className="col-span-9 sm:col-span-10 text-zinc-800 space-y-0.5">
                        {hasPaint ? (
                          acc.paintParts.map((part, pIdx) => (
                            <p key={pIdx} className="leading-snug">{part}</p>
                          ))
                        ) : isCostUndetermined ? (
                          <p className="text-zinc-500 leading-snug">수리(견적)비용 : 미확정</p>
                        ) : (
                          <p className="text-zinc-400 leading-snug">-</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* 하단 전체 수리내역 접기/펼치기 버튼 */}
        <button
          type="button"
          onClick={() => setIsSummaryExpanded(!isSummaryExpanded)}
          className="w-full py-2.5 bg-zinc-50 hover:bg-zinc-100 border-t border-zinc-200 text-xs text-zinc-600 font-medium flex items-center justify-center gap-1 transition cursor-pointer"
        >
          <span>전체 수리내역</span>
          {isSummaryExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* 5. 자세히 보기 모달 레이어 (오토플러스 layer-repair-record) */}
      {detailModalData && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          onClick={() => setDetailModalData(null)}
        >
          <div 
            className="bg-white rounded-xl shadow-2xl border border-zinc-200 w-full max-w-md overflow-hidden text-zinc-800 animate-in fade-in zoom-in-95 duration-150"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 bg-zinc-50 border-b border-zinc-200">
              <h3 className="font-bold text-sm text-zinc-800 font-mono">
                {detailModalData.date} 수리 상세 내역
              </h3>
              <button
                type="button"
                onClick={() => setDetailModalData(null)}
                className="text-zinc-400 hover:text-zinc-700 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4 max-h-[60vh] overflow-y-auto space-y-3 text-xs">
              {detailModalParts.major.length > 0 && (
                <div>
                  <div className="font-bold text-rose-600 mb-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    교환·판금·조정 작업 부위 ({detailModalParts.major.length}건)
                  </div>
                  <ul className="list-disc list-inside space-y-1 text-rose-600 font-medium bg-rose-50/60 p-2.5 rounded-lg border border-rose-100">
                    {detailModalParts.major.map((m, mIdx) => (
                      <li key={mIdx}>{m}</li>
                    ))}
                  </ul>
                </div>
              )}
              {detailModalParts.minor.length > 0 && (
                <div>
                  <div className="font-bold text-zinc-700 mb-1 flex items-center gap-1">
                    <Wrench className="w-3.5 h-3.5 text-sky-500" />
                    탈착·도장 부위 ({detailModalParts.minor.length}건)
                  </div>
                  <ul className="list-disc list-inside space-y-1 text-zinc-600 bg-zinc-50 p-2.5 rounded-lg border border-zinc-200">
                    {detailModalParts.minor.map((m, mIdx) => (
                      <li key={mIdx}>{m}</li>
                    ))}
                  </ul>
                </div>
              )}
              {detailModalParts.major.length === 0 && detailModalParts.minor.length === 0 && (
                <div className="text-center py-4 text-zinc-400">
                  기록된 세부 부품 정보가 없습니다.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
