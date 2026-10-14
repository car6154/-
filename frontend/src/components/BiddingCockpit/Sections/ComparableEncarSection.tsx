import React, { useState, useEffect, useMemo } from 'react';
import { AlertTriangle, ExternalLink, Car } from 'lucide-react';
import {
  isOptionMatched,
  splitOptionString,
  getOptionMatchDetail,
  fetchNewCarCatalog,
  NewCarCatalogData
} from '@/services/biddingOptionCatalog';
import { CarDamageDiagram2D } from './CarDamageDiagram2D';

export interface EncarItem {
  id: string;
  carName: string;
  subModel?: string;
  modelName?: string;
  year: number | string;
  mileage: number;
  price: number;
  accidentType: string;
  color?: string;
  checkDate?: string;
  holdingDays?: number;
  optionsText?: string;
  [key: string]: any;
}

export type EncarSortOption =
  | 'price_asc'
  | 'price_desc'
  | 'recent_reg'
  | 'year_desc'
  | 'mileage_asc'
  | 'complex';

export interface EncarFilterStats {
  targetBadge?: string;
  totalModelCount?: number;
  excludedByBadge?: number;
  validCount?: number;
  filterMethod?: string;
  reason?: string;
}

export interface ComparableEncarSectionProps {
  encarList: EncarItem[];
  encarTotalModelCount: number;
  encarFilteredCount: number;
  encarFilterStats?: EncarFilterStats | null;
  selectedEncarId: string;
  selectedEncar: EncarItem | null;
  isEncarLoading: boolean;
  isInspectionLoading: boolean;
  encarErrorMessage?: string;
  encarSourceUrl?: string;
  carName?: string;
  carNumber?: string;
  detailModel?: string;
  yearModel: number;
  mileageKm: number;
  optionsTag?: string;
  showTrimColumn?: boolean;
  onToggleTrimColumn?: () => void;
  onSelectEncar: (id: string) => void;
}

export const ComparableEncarSection: React.FC<ComparableEncarSectionProps> = ({
  encarList,
  encarTotalModelCount,
  encarFilteredCount,
  encarFilterStats,
  selectedEncarId,
  selectedEncar,
  isEncarLoading,
  isInspectionLoading,
  encarErrorMessage,
  encarSourceUrl,
  carName,
  carNumber,
  detailModel,
  yearModel,
  mileageKm,
  optionsTag,
  showTrimColumn: externalShowTrimColumn,
  onToggleTrimColumn,
  onSelectEncar,
}) => {
  const [internalShowTrim, setInternalShowTrim] = useState<boolean>(false);
  const showTrimColumn = externalShowTrimColumn !== undefined ? externalShowTrimColumn : internalShowTrim;
  const [sortOption, setSortOption] = useState<EncarSortOption>('complex');

  const sortedEncarList = useMemo(() => {
    if (!encarList || encarList.length === 0) return [];
    const list = [...encarList];

    const parseYearNum = (y: any): number => {
      if (typeof y === 'number') return y < 100 ? 2000 + y : y;
      const str = String(y || '').trim();
      const m = str.match(/(?:20)?(\d{2})/);
      return m ? Number('20' + m[1]) : 0;
    };

    const getValidDateStr = (item: EncarItem): string => {
      const d = item.checkDate || item.registrationDate || item.regDate || '';
      return String(d).replace(/[^\d]/g, '');
    };

    switch (sortOption) {
      case 'price_asc':
        return list.sort((a, b) => (Number(a.price) || 0) - (Number(b.price) || 0));
      case 'price_desc':
        return list.sort((a, b) => (Number(b.price) || 0) - (Number(a.price) || 0));
      case 'recent_reg':
        return list.sort((a, b) => {
          const dateA = getValidDateStr(a);
          const dateB = getValidDateStr(b);
          if (dateA !== dateB) return dateB.localeCompare(dateA);
          return (Number(a.price) || 0) - (Number(b.price) || 0);
        });
      case 'year_desc':
        return list.sort((a, b) => {
          const yrDiff = parseYearNum(b.year) - parseYearNum(a.year);
          if (yrDiff !== 0) return yrDiff;
          return (Number(a.price) || 0) - (Number(b.price) || 0);
        });
      case 'mileage_asc':
        return list.sort((a, b) => {
          const milA = Number(a.mileage ?? a.km ?? 0);
          const milB = Number(b.mileage ?? b.km ?? 0);
          if (milA !== milB) return milA - milB;
          return (Number(a.price) || 0) - (Number(b.price) || 0);
        });
      case 'complex':
        return list.sort((a, b) => {
          // 1차: 성능일/등록일 최신순 (내림차순)
          const dateA = getValidDateStr(a);
          const dateB = getValidDateStr(b);
          if (dateA !== dateB) return dateB.localeCompare(dateA);
          // 2차: 가격 낮은 순 (오름차순)
          const priceDiff = (Number(a.price) || 0) - (Number(b.price) || 0);
          if (priceDiff !== 0) return priceDiff;
          // 3차: 연식 최신순 (내림차순)
          return parseYearNum(b.year) - parseYearNum(a.year);
        });
      default:
        return list;
    }
  }, [encarList, sortOption]);

  const [targetCatalog, setTargetCatalog] = useState<NewCarCatalogData | null>(null);
  const [compCatalog, setCompCatalog] = useState<NewCarCatalogData | null>(null);

  useEffect(() => {
    let isMounted = true;
    if (carName) {
      fetchNewCarCatalog(carName, yearModel ? String(yearModel) : undefined).then((cat) => {
        if (isMounted) setTargetCatalog(cat);
      });
    } else {
      setTargetCatalog(null);
    }
    return () => {
      isMounted = false;
    };
  }, [carName, yearModel]);

  useEffect(() => {
    let isMounted = true;
    if (selectedEncar?.carName) {
      fetchNewCarCatalog(selectedEncar.carName, selectedEncar.year ? String(selectedEncar.year) : undefined).then((cat) => {
        if (isMounted) setCompCatalog(cat);
      });
    } else {
      setCompCatalog(null);
    }
    return () => {
      isMounted = false;
    };
  }, [selectedEncar?.carName, selectedEncar?.year]);
  const toggleTrim = onToggleTrimColumn || (() => setInternalShowTrim(prev => !prev));

  return (
    <div className="bg-[#0e0f13] border-2 border-amber-500/30 rounded-xl p-4 sm:p-5 shadow-xl space-y-4">
      {/* 비교 매물 영역 상단 명확한 구분 배너 */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-[#262833] bg-amber-500/5 -mx-4 -mt-4 p-4 rounded-t-xl">
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded bg-amber-500/25 text-amber-300 font-black text-xs border border-amber-500/40 shadow-sm">
            🔍 시장 비교 매물 영역
          </span>
          <span className="text-white font-bold text-sm sm:text-base">
            엔카 실시간 등록 매물 리스트 ({encarFilteredCount || encarList.length}대)
          </span>
        </div>
        <div className="text-xs text-zinc-400">
          ⚠️ 아래 목록은 시장 시세 비교군이며, <strong className="text-sky-300">{carNumber || carName || '타겟차량'}</strong>의 성능/점검 정보가 아닙니다.
        </div>
      </div>

      {/* Encar List + 2D Detail Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 items-stretch">
        {/* Table (Left 7 cols) */}
        <div className="xl:col-span-7 space-y-2 flex flex-col">
          <div className="flex items-center justify-between text-xs sm:text-sm font-bold text-white px-1">
            <span>📰 엔카 동급 매물 (전체 {encarTotalModelCount}대 중 유효 {encarFilteredCount || encarList.length}대)</span>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] text-zinc-400 font-medium hidden sm:inline">정렬:</span>
                <select
                  value={sortOption}
                  onChange={(e) => setSortOption(e.target.value as EncarSortOption)}
                  className="text-xs px-2.5 py-1 rounded bg-[#1c1e28] hover:bg-[#282c3c] text-zinc-200 border border-[#35394a] transition cursor-pointer font-bold focus:outline-none focus:border-amber-400"
                >
                  <option value="price_asc">가격 낮은 순</option>
                  <option value="price_desc">가격 높은 순</option>
                  <option value="recent_reg">최신 등록순</option>
                  <option value="year_desc">연식 신순</option>
                  <option value="mileage_asc">주행거리 적은 순</option>
                  <option value="complex">복합 정렬</option>
                </select>
              </div>
              <button
                type="button"
                onClick={toggleTrim}
                className="text-xs px-2.5 py-1 rounded bg-[#1c1e28] hover:bg-[#282c3c] text-zinc-200 border border-[#35394a] transition cursor-pointer font-bold"
              >
                <span>세부등급 {showTrimColumn ? '숨김' : '표시'}</span>
              </button>
              <span className="text-xs text-amber-300/90 font-medium hidden sm:inline">👆 행 클릭 시 해당 비교 매물 점검표 열림</span>
            </div>
          </div>

          {/* [필터링 원칙 준수 안내 배너: 기준 등급 일치 매물만 포함, 제외 대수 및 사유 실시간 표시] */}
          {encarFilterStats ? (
            <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 bg-gradient-to-r from-amber-500/10 via-indigo-500/10 to-transparent border border-amber-500/30 rounded-lg text-xs">
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-extrabold border border-amber-500/40">
                  🎯 기준 등급: {encarFilterStats.targetBadge || detailModel || '동급'}
                </span>
                <span className="text-zinc-300 text-xs">
                  전체 <strong className="text-white font-mono">{encarFilterStats.totalModelCount || encarTotalModelCount}대</strong> 중
                  {encarFilterStats.excludedByBadge && encarFilterStats.excludedByBadge > 0 ? (
                    <> <strong className="text-amber-400 font-mono font-bold">등급 불일치로 {encarFilterStats.excludedByBadge.toLocaleString()}대 제외</strong> (하이리무진·타인승·타트림 배제) ➔</>
                  ) : (
                    <> 기준 등급 100% 일치 ➔</>
                  )}
                  {" "}최종 유효 표본 <strong className="text-emerald-400 font-mono font-bold">{encarFilterStats.validCount || encarList.length}대</strong>
                </span>
              </div>
              <span className="text-[11px] text-zinc-400 font-medium">
                ⚡ {encarFilterStats.filterMethod === 'API' ? '엔카 API 배지 필터 적용' : '로컬 엄격 일치 필터 적용'}
              </span>
            </div>
          ) : (
            encarTotalModelCount > (encarFilteredCount || encarList.length) && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/10 border border-amber-500/25 rounded-lg text-xs text-amber-300">
                <span>💡 필터링 기준: 등급 불일치로 {(encarTotalModelCount - (encarFilteredCount || encarList.length)).toLocaleString()}대 제외 ➔ 유효 {encarFilteredCount || encarList.length}대 표본 채택</span>
              </div>
            )
          )}

          <div className="overflow-x-auto h-[560px] max-h-[560px] overflow-y-auto border border-[#262833] rounded-xl scrollbar-thin scrollbar-thumb-zinc-700 bg-[#0a0b0e] flex-1">
            {isEncarLoading ? (
              <div className="flex flex-col items-center justify-center h-full space-y-3 py-12 bg-[#0e0f13]/80">
                <div className="w-9 h-9 border-3 border-blue-500/30 border-t-blue-400 rounded-full animate-spin" />
                <div className="text-sm font-bold text-white flex items-center gap-1.5">
                  <span>🚗 엔카 실시간 동급 매물 정밀 크롤링 중...</span>
                </div>
                <div className="text-xs text-zinc-400">
                  성능점검 기록부 및 추가옵션 전수 스캔 &amp; 2D 도면 연동 중
                </div>
              </div>
            ) : encarList.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full space-y-3 py-16 px-4 bg-[#0a0b0e] text-center">
                <div className="w-12 h-12 rounded-full bg-rose-500/10 flex items-center justify-center text-rose-400">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div className="text-sm font-bold text-rose-300">
                  {encarErrorMessage || '엔카 실시간 매물을 불러오지 못했습니다.'}
                </div>
                <div className="text-xs text-zinc-400 max-w-[340px] leading-relaxed">
                  현재 조건(차종/연식/주행거리)에 일치하는 등록 매물이 없거나 실시간 통신이 원활하지 않습니다.
                </div>
                {encarSourceUrl && (
                  <a
                    href={encarSourceUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 text-xs font-semibold transition mt-2 cursor-pointer"
                  >
                    <span>엔카 웹사이트에서 직접 조회하기</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            ) : (
              <table className="w-full text-left text-[12px] text-zinc-200">
                <thead className="bg-[#14151b] sticky top-0 z-10 text-[11px] text-zinc-300 font-bold uppercase border-b border-[#262833]">
                  <tr>
                    <th className="py-2 px-1 text-center w-7 bg-[#14151b] whitespace-nowrap">선택</th>
                    <th className="py-2 px-1 text-center bg-[#14151b] whitespace-nowrap w-[72px]">성능일</th>
                    <th className="py-2 px-1 text-center bg-[#14151b] whitespace-nowrap w-[52px]">재고일</th>
                    <th className="py-2 px-1.5 bg-[#14151b] whitespace-nowrap w-[82px]">차량명</th>
                    {showTrimColumn && <th className="py-2 px-1.5 bg-[#14151b] whitespace-nowrap w-[95px]">세부등급</th>}
                    <th className="py-2 px-1 text-center bg-[#14151b] whitespace-nowrap w-[58px]">연식</th>
                    <th className="py-2 px-1.5 text-right bg-[#14151b] whitespace-nowrap w-[84px]">주행(km)</th>
                    <th className="py-2 px-1.5 text-right bg-[#14151b] whitespace-nowrap w-[78px]">💰 가격</th>
                    <th className="py-2 px-2 text-left bg-[#14151b] whitespace-nowrap w-[125px] min-w-[125px]">사고유무</th>
                    <th className="py-2 px-1 text-center bg-[#14151b] whitespace-nowrap w-[50px]">색상</th>
                    <th className="py-2 px-1 text-center bg-[#14151b] whitespace-nowrap w-[72px]">옵션</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#232634]">
                  {sortedEncarList.map((car) => {
                    const isSelected = car.id === selectedEncarId;
                    const targetYrStr = String(yearModel % 100).padStart(2, '0');
                    const regYrMatch = String(car.year || '').match(/^\s*(\d{2})/);
                    const isTargetYear = regYrMatch ? regYrMatch[1] === targetYrStr : false;
                    const parsedCarOpts = splitOptionString(car.optionsText || '');
                    const hasAddedOptions = parsedCarOpts.length > 0;

                    // 사고유무 5~6글자 간결 규격화 (왼쪽 정렬용)
                    const formatAccident = (rawType: string) => {
                      if (!rawType || (rawType.includes('완전무사고') && !rawType.includes('교환') && !rawType.includes('판금'))) {
                        return { text: '🟢 완전무사고', style: 'text-emerald-400 font-bold' };
                      }
                      if (rawType.includes('사고') && !rawType.includes('무사고')) {
                        return { text: '🔴 프레임사고', style: 'text-rose-400 font-bold' };
                      }
                      const repMatch = rawType.match(/교환\s*[:\s]?\s*(\d+)/);
                      const fixMatch = rawType.match(/판금\s*[:\s]?\s*(\d+)/);
                      const rCnt = repMatch ? parseInt(repMatch[1], 10) : 0;
                      const fCnt = fixMatch ? parseInt(fixMatch[1], 10) : 0;
                      const total = rCnt + fCnt;
                      if (total > 0) {
                        return { text: `🟡 단순수리 (${total})`, style: 'text-amber-400 font-bold' };
                      }
                      if (rawType.includes('교환') && rawType.includes('판금')) {
                        return { text: '🟡 단순(교/판)', style: 'text-amber-400 font-bold' };
                      }
                      if (rawType.includes('판금')) {
                        return { text: '🟡 단순판금', style: 'text-amber-400 font-bold' };
                      }
                      if (rawType.includes('교환')) {
                        return { text: '🟡 단순교환', style: 'text-amber-400 font-bold' };
                      }
                      return { text: `🟡 ${rawType.slice(0, 6)}`, style: 'text-amber-400 font-bold' };
                    };
                    const accInfo = formatAccident(car.accidentType);

                    return (
                      <tr
                        key={car.id}
                        onClick={() => onSelectEncar(car.id)}
                        className={`cursor-pointer transition ${
                          isSelected
                            ? 'bg-blue-600/30 text-white font-bold'
                            : 'hover:bg-[#14151c]'
                        }`}
                      >
                        <td className="py-1.5 px-1 text-center whitespace-nowrap">
                          <input
                            type="radio"
                            name="encarSelect"
                            checked={isSelected}
                            onChange={() => onSelectEncar(car.id)}
                            className="accent-blue-500 cursor-pointer w-3.5 h-3.5"
                          />
                        </td>
                        <td className="py-1.5 px-1 text-center text-[12px] text-zinc-100 font-mono font-medium whitespace-nowrap">
                          {car.checkDate || '-'}
                        </td>
                        <td className="py-1.5 px-1 text-center whitespace-nowrap">
                          <span className={`px-1.5 py-0.5 rounded text-[11px] font-black font-mono border ${
                            (car.holdingDays ?? 0) <= 14 
                              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' 
                              : (car.holdingDays ?? 0) >= 60 
                                ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' 
                                : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                          }`}>
                            {car.holdingDays}일
                          </span>
                        </td>
                        <td className="py-1.5 px-1.5 text-[12px] whitespace-nowrap">
                          <a
                            href={`https://fem.encar.com/cars/detail/${String(car.id).replace(/\D/g, '')}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-sky-400 hover:text-sky-300 hover:underline font-bold text-[12px] whitespace-nowrap transition-colors"
                            title={`엔카 공식 상세페이지 새창 열기 (매물코드: ${car.id})`}
                          >
                            {car.modelName || car.carName}
                          </a>
                        </td>
                        {showTrimColumn && (
                          <td className="py-1.5 px-1.5 text-[11px] text-zinc-300 font-medium whitespace-nowrap">
                            {car.subModel || '-'}
                          </td>
                        )}
                        <td className="py-1.5 px-1 text-center text-[12px] whitespace-nowrap font-mono">
                          <span className={isTargetYear ? 'text-sky-400 font-black' : 'text-zinc-300 font-semibold'}>
                            {car.year}
                          </span>
                        </td>
                        <td className="py-1.5 px-1.5 text-right text-[12px] text-white font-bold font-mono whitespace-nowrap">
                          <div>{car.mileage.toLocaleString()}</div>
                          {mileageKm > 0 && (() => {
                            const diffKm = car.mileage - mileageKm;
                            if (diffKm === 0) return <div className="text-[10px] text-zinc-400 font-mono">동일km</div>;
                            return (
                              <div className={`text-[10px] font-mono leading-none pt-0.5 ${diffKm > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                                {diffKm > 0 ? `+${diffKm.toLocaleString()}km` : `${diffKm.toLocaleString()}km`}
                              </div>
                            );
                          })()}
                        </td>
                        <td className="py-1.5 px-1.5 text-right font-black text-amber-400 font-mono text-[13px] whitespace-nowrap">
                          {car.price.toLocaleString()}만
                        </td>
                        <td className="py-1.5 px-2 text-left whitespace-nowrap" title={car.accidentType}>
                          <span className={`inline-flex items-center gap-1 text-[11.5px] ${accInfo.style}`}>
                            {accInfo.text}
                          </span>
                        </td>
                        <td className="py-1.5 px-1 text-center text-[11px] text-zinc-300 whitespace-nowrap">
                          {car.color || '흰색'}
                        </td>
                        <td className="py-1.5 px-1 text-center whitespace-nowrap">
                          {hasAddedOptions ? (() => {
                            const targetOpts = splitOptionString(optionsTag || '');
                            const compDetails = parsedCarOpts.map(o => getOptionMatchDetail(o, targetOpts, 'comp_vs_target', targetCatalog, compCatalog));
                            const exactCount = compDetails.filter(d => d.confidence === 'exact').length;
                            const fuzzyCount = compDetails.filter(d => d.confidence === 'fuzzy').length;
                            const commonCount = compDetails.filter(d => d.isMatched).length;
                            const extraCount = parsedCarOpts.length - commonCount;

                            const tooltipLines = [
                              `[비교 차량 추가옵션 총 ${parsedCarOpts.length}개]`,
                              ...compDetails.map((d, i) => {
                                const o = parsedCarOpts[i];
                                if (d.confidence === 'exact') return `✓ ${o} (신차 공식 일치: ${d.matchedOppositeName})`;
                                if (d.confidence === 'fuzzy') return `~ ${o} (퍼지 추정 매칭: ${d.matchedOppositeName})`;
                                return `+ ${o} (비교차 전용 옵션)`;
                              }),
                              '──────────────────────────────',
                              targetOpts.length > 0
                                ? `공식 일치: ${exactCount}개 / 추정 매칭: ${fuzzyCount}개 / 비교차 전용: ${extraCount}개`
                                : '내 차 옵션 정보 없음'
                            ];

                            return (
                              <span 
                                title={tooltipLines.join('\n')}
                                className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40 text-[10.5px] cursor-help hover:bg-amber-500/30 transition inline-flex items-center gap-0.5"
                              >
                                {exactCount > 0 ? (
                                  <span className="text-sky-400 text-[10px]">✓</span>
                                ) : fuzzyCount > 0 ? (
                                  <span className="text-amber-400 text-[10px]">~</span>
                                ) : null}
                                <span>{parsedCarOpts.length}개</span>
                              </span>
                            );
                          })() : (
                            <span title="기본 출고 사양 (추가옵션 없음)" className="text-zinc-500 text-[10.5px] cursor-help">기본</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right: Detailed Inspection Card + 2D Car Diagram (Right 5 cols) - 비교 매물 선택 시에만 표출 */}
        <div className="xl:col-span-5 bg-[#14151b] border border-[#262833] rounded-xl p-4 sm:p-5 space-y-4 h-auto flex flex-col justify-between">
          {!selectedEncar ? (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-3 py-16 px-4 bg-[#0a0b0e] rounded-xl border border-dashed border-[#2a2d3d]">
              <div className="w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-400">
                <Car className="w-6 h-6" />
              </div>
              <div className="text-sm font-bold text-white">비교 매물이 선택되지 않았습니다</div>
              <div className="text-xs text-zinc-400 max-w-[280px] leading-relaxed">
                좌측 <span className="text-amber-300 font-semibold">엔카 비교 매물 목록</span>에서 확인하고 싶은 차량의 행을 클릭하면, 해당 비교 매물의 <span className="text-sky-300 font-semibold">외판/골격 2D 상태도와 성능점검 기록부</span>가 여기에 표시됩니다.
              </div>
              {carNumber && (
                <div className="mt-2 px-3 py-1.5 rounded bg-[#161822] border border-[#282a3a] text-[11px] text-zinc-400">
                  현재 조회 차량: <strong className="text-emerald-400 font-mono">{carNumber}</strong> ({carName} / {mileageKm.toLocaleString()}km)
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between pb-2 border-b border-[#262833]">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold text-[11px] border border-amber-500/30">
                    엔카 비교 차량
                  </span>
                  <span className="text-sm font-bold text-white">비교 매물 상세 사양 &amp; 성능점검</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-400 font-mono">
                    {isInspectionLoading ? '⚡ 점검표 수신 중...' : `ID: ${selectedEncar.id}`}
                  </span>
                  <button
                    type="button"
                    onClick={() => onSelectEncar('')}
                    className="text-[11px] px-2 py-0.5 rounded bg-[#232634] hover:bg-[#323646] text-zinc-300 hover:text-white font-medium transition cursor-pointer"
                    title="비교 매물 선택 해제"
                  >
                    선택 해제 ✕
                  </button>
                </div>
              </div>

              {/* Title & Badges */}
              <div className="space-y-1.5">
                <div className="text-base sm:text-lg font-black text-white">{selectedEncar.carName}</div>
                <div className="text-xs sm:text-sm text-zinc-300 font-semibold">{selectedEncar.subModel || detailModel}</div>

                <div className="flex flex-wrap gap-1.5 pt-0.5 text-xs">
                  <span className="px-2.5 py-1 rounded bg-[#1f222e] text-white font-bold font-mono">
                    {selectedEncar.year}년식
                  </span>
                  <span className="px-2.5 py-1 rounded bg-[#1f222e] text-emerald-400 font-bold font-mono">
                    {selectedEncar.mileage.toLocaleString()}km
                  </span>
                  <span className="px-2.5 py-1 rounded bg-[#1f222e] text-zinc-300 font-medium">
                    ⚫ {selectedEncar.color || '색상'}
                  </span>
                  {selectedEncar.inspectionDate && selectedEncar.inspectionDate !== '-' && (
                    <span className="px-2.5 py-1 rounded bg-blue-500/20 text-blue-300 font-bold font-mono" title="법정 성능점검일자">
                      📋 점검: {selectedEncar.inspectionDate}
                    </span>
                  )}
                  {selectedEncar.registrationDate && selectedEncar.registrationDate !== '-' ? (
                    <span className="px-2.5 py-1 rounded bg-indigo-500/20 text-indigo-300 font-bold font-mono" title="엔카 최초 매물등록일자">
                      📅 등록: {selectedEncar.registrationDate} ({selectedEncar.holdingDays}일 전)
                    </span>
                  ) : (
                    <span className="px-2.5 py-1 rounded bg-blue-500/20 text-blue-300 font-bold font-mono">
                      📅 {selectedEncar.checkDate} ({selectedEncar.holdingDays}일 전)
                    </span>
                  )}
                  {selectedEncar.accidentType.includes('완전무사고') && !selectedEncar.accidentType.includes('교환') && !selectedEncar.accidentType.includes('판금') ? (
                    <span className="px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40">
                      🟢 {selectedEncar.accidentType}
                    </span>
                  ) : selectedEncar.accidentType.includes('사고') && !selectedEncar.accidentType.includes('무사고') ? (
                    <span className="px-2.5 py-1 rounded bg-rose-500/20 text-rose-300 font-bold border border-rose-500/40">
                      🔴 {selectedEncar.accidentType}
                    </span>
                  ) : (
                    <span className="px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40">
                      🟡 {selectedEncar.accidentType}
                    </span>
                  )}
                </div>
              </div>

              {/* Large Price Display */}
              <div className="flex items-baseline gap-1.5 pt-1 pb-0.5">
                <span className="text-2xl sm:text-3xl font-black text-amber-400 font-mono tracking-tight">
                  {selectedEncar.price.toLocaleString()}
                </span>
                <span className="text-sm font-bold text-zinc-300">만원</span>
              </div>

              {/* Parsed Individual Option Badges */}
              {(() => {
                const optItems = splitOptionString(selectedEncar.optionsText || '');

                if (optItems.length === 0) {
                  return (
                    <div className="p-2.5 bg-[#0c0e14] rounded-lg border border-[#232634] text-xs text-zinc-500 italic">
                      추가옵션 없음 또는 기본 트림 사양
                    </div>
                  );
                }

                const targetOpts = splitOptionString(optionsTag || '');

                const exactOpts: { name: string; tooltip: string; detail: any }[] = [];
                const fuzzyOpts: { name: string; tooltip: string; detail: any }[] = [];
                const extraOpts: { name: string; tooltip: string; detail: any }[] = [];

                for (const opt of optItems) {
                  const detail = getOptionMatchDetail(opt, targetOpts, 'comp_vs_target', targetCatalog, compCatalog);
                  if (detail.confidence === 'exact') {
                    exactOpts.push({ name: opt, tooltip: detail.tooltipText, detail });
                  } else if (detail.confidence === 'fuzzy') {
                    fuzzyOpts.push({ name: opt, tooltip: detail.tooltipText, detail });
                  } else {
                    extraOpts.push({ name: opt, tooltip: detail.tooltipText, detail });
                  }
                }

                // 공식 일치(하늘색 ✓) -> 퍼지 추정(주황색 ~) -> 비교차 전용(오렌지 +) 순 정렬
                const sortedOptItems = [
                  ...exactOpts,
                  ...fuzzyOpts,
                  ...extraOpts
                ];

                const displayOpts = sortedOptItems.slice(0, 8);
                const overflowCount = sortedOptItems.length - 8;

                return (
                  <div className="flex flex-wrap gap-1.5 p-2 bg-[#0c0e14] rounded-lg border border-[#232634]">
                    {displayOpts.map((item, idx) => {
                      if (item.detail.confidence === 'exact') {
                        return (
                          <span
                            key={idx}
                            title={item.tooltip}
                            className="px-2 py-0.5 rounded text-[11px] font-bold bg-sky-500/20 text-sky-300 border border-sky-400 shadow-[0_0_6px_rgba(14,165,233,0.2)] flex items-center gap-1 cursor-help hover:brightness-110 transition max-w-[210px]"
                          >
                            <span className="text-sky-400 font-black shrink-0">✓</span>
                            <span className="truncate">{item.name}</span>
                          </span>
                        );
                      }
                      if (item.detail.confidence === 'fuzzy') {
                        return (
                          <span
                            key={idx}
                            title={item.tooltip}
                            className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/60 flex items-center gap-1 cursor-help hover:brightness-110 transition max-w-[210px]"
                          >
                            <span className="text-amber-400 font-black shrink-0">~</span>
                            <span className="truncate">{item.name}</span>
                          </span>
                        );
                      }
                      return (
                        <span
                          key={idx}
                          title={item.tooltip}
                          className="px-2 py-0.5 rounded text-[11px] font-bold bg-orange-500/20 text-orange-400 border border-orange-500/60 flex items-center gap-1 cursor-help hover:brightness-110 transition max-w-[210px]"
                        >
                          <span className="text-orange-400 font-black shrink-0">+</span>
                          <span className="truncate">{item.name}</span>
                        </span>
                      );
                    })}
                    {overflowCount > 0 && (
                      <span
                        className="px-2 py-0.5 rounded text-[11px] font-medium bg-[#1e222d] text-slate-400 border border-[#2e384d] cursor-help hover:brightness-110 transition"
                        title={`추가 옵션:\n${sortedOptItems.slice(8).map(o => `- ${o.name}`).join('\n')}`}
                      >
                        +{overflowCount}
                      </span>
                    )}
                  </div>
                );
              })()}

              {/* 2D Car Damage Diagram Component */}
              <CarDamageDiagram2D selectedEncar={selectedEncar} />
            </>
          )}
        </div>
      </div>
    </div>
  );
};
