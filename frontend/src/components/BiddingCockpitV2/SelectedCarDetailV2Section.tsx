import React, { useState, useEffect, useRef } from 'react';
import { ExternalLink, RefreshCw, AlertCircle, Info, CheckCircle2, ChevronUp, ChevronDown } from 'lucide-react';
import { EncarItem } from '@/components/BiddingCockpit/types';
import { CarDamageDiagram2D, getDamagePartKoreanName } from '@/components/BiddingCockpit/Sections/CarDamageDiagram2D';
import { getCarColorStyle } from '@/utils/carColor';
import { splitOptionString } from '@/services/biddingOptionCatalog';

export interface MatchedOptionItem {
  raw_name: string;
  clean_name: string;
  official_name: string;
  price?: number | null;
  desc?: string;
  match_type: 'exact' | 'fuzzy' | 'none';
  source: 'danawa' | 'encar' | 'none';
}

export interface SelectedCarDetailV2SectionProps {
  selectedEncar: EncarItem | null;
  isInspectionLoading: boolean;
}

// 사고구분 라벨 헬퍼 (기존 콕핏 배지 스타일과 100% 일치)
const formatAccident = (rawType?: string) => {
  if (!rawType || (rawType.includes('완전무사고') && !rawType.includes('교환') && !rawType.includes('판금'))) {
    return { text: '🟢 완전무사고', style: 'text-emerald-300 bg-emerald-500/20 border-emerald-500/40 font-bold' };
  }
  if (rawType.includes('사고') && !rawType.includes('무사고')) {
    return { text: '🔴 프레임사고', style: 'text-rose-300 bg-rose-500/20 border-rose-500/40 font-bold' };
  }
  const repMatch = rawType.match(/교환\s*[:\s]?\s*(\d+)/);
  const fixMatch = rawType.match(/판금\s*[:\s]?\s*(\d+)/);
  const rCnt = repMatch ? parseInt(repMatch[1], 10) : 0;
  const fCnt = fixMatch ? parseInt(fixMatch[1], 10) : 0;
  const total = rCnt + fCnt;
  if (total > 0) {
    return { text: `🟡 단순수리 (${total})`, style: 'text-amber-300 bg-amber-500/20 border-amber-500/40 font-bold' };
  }
  if (rawType.includes('교환') && rawType.includes('판금')) {
    return { text: '🟡 단순(교/판)', style: 'text-amber-300 bg-amber-500/20 border-amber-500/40 font-bold' };
  }
  if (rawType.includes('판금')) {
    return { text: '🟡 단순판금', style: 'text-amber-300 bg-amber-500/20 border-amber-500/40 font-bold' };
  }
  if (rawType.includes('교환')) {
    return { text: '🟡 단순교환', style: 'text-amber-300 bg-amber-500/20 border-amber-500/40 font-bold' };
  }
  return { text: `🟡 ${rawType.slice(0, 8)}`, style: 'text-amber-300 bg-amber-500/20 border-amber-500/40 font-bold' };
};

export const SelectedCarDetailV2Section: React.FC<SelectedCarDetailV2SectionProps> = ({
  selectedEncar,
  isInspectionLoading,
}) => {
  // 상세 패널 숨김/펼침 상태 (기본값: 펼침)
  const [isCollapsed, setIsCollapsed] = useState(false);

  // 💡 [2026-11-02 제이 규칙]: 선택 차량의 옵션에 대해서만 신차 카탈로그 매칭(다나와 1순위 -> 엔카 2순위 -> 퍼지 3순위) 비동기 조회
  // 💡 [Rules of Hooks]: 모든 리액트 훅은 early return(조기 반환) 이전에 컴포넌트 최상단에서 무조건 실행되어야 함
  const [matchedOptions, setMatchedOptions] = useState<MatchedOptionItem[]>([]);
  const [, setIsOptionsMatching] = useState<boolean>(false);
  const optionsCacheRef = useRef<Record<string, MatchedOptionItem[]>>({});

  useEffect(() => {
    if (!selectedEncar) {
      setMatchedOptions([]);
      return;
    }

    const rawOptText = selectedEncar.optionsText || '';
    const cleanOptText = rawOptText.replace(/\s+/g, '');
    const isNoOptionPlaceholder =
      cleanOptText === '추가옵션없음' ||
      cleanOptText === '기본출고사양(추가옵션없음)';

    if (!rawOptText || isNoOptionPlaceholder) {
      setMatchedOptions([]);
      return;
    }

    const cacheKey = `${selectedEncar.id}_${selectedEncar.carName}_${selectedEncar.year}_${rawOptText}`;
    if (optionsCacheRef.current[cacheKey]) {
      setMatchedOptions(optionsCacheRef.current[cacheKey]);
      return;
    }

    let isMounted = true;
    setIsOptionsMatching(true);

    fetch('/api/encar/match-options', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        carName: selectedEncar.carName,
        year: selectedEncar.year,
        optionsText: rawOptText,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (isMounted && data.success && Array.isArray(data.data)) {
          optionsCacheRef.current[cacheKey] = data.data;
          setMatchedOptions(data.data);
        }
      })
      .catch((e) => {
        console.warn('옵션 카탈로그 매칭 조회 실패:', e);
      })
      .finally(() => {
        if (isMounted) setIsOptionsMatching(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedEncar?.id, selectedEncar?.carName, selectedEncar?.year, selectedEncar?.optionsText]);

  // 💡 [2026-11-01 제이 규칙]: 선택된 차량이 없으면 안내 한 줄만 보여준다 (예시 차량 생성 금지)
  if (!selectedEncar) {
    return (
      <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-8 shadow-sm flex items-center justify-center text-zinc-500 text-xs sm:text-sm">
        <Info className="w-4 h-4 mr-2 text-zinc-600" />
        <span>목록에서 차량을 선택하면 상세 정보가 여기에 표시됩니다</span>
      </div>
    );
  }

  // 💡 [2026-11-02 제이 규칙]: 접힘 상태일 때 간결한 복원 바 표시 (상세 보기 버튼으로 언제든 복원)
  if (isCollapsed) {
    return (
      <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-3.5 shadow-sm flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs sm:text-sm font-bold text-zinc-200 truncate">
            {selectedEncar.carName} {selectedEncar.subModel || ''}
          </span>
          <span className="text-[11px] text-zinc-500 font-mono shrink-0">
            (상세 정보 숨김)
          </span>
        </div>
        <button
          type="button"
          onClick={() => setIsCollapsed(false)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-sky-400 hover:text-sky-300 bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/30 rounded-lg transition shrink-0 cursor-pointer"
          title="선택 차량 상세 패널 다시 펼치기"
        >
          <ChevronDown className="w-3.5 h-3.5" />
          <span>상세 보기</span>
        </button>
      </div>
    );
  }

  // 1. 스펙 항목 정리
  const accInfo = formatAccident(selectedEncar.accidentType);
  const detailUrl = selectedEncar.encarUrl || `https://fem.encar.com/cars/detail/${selectedEncar.id}`;
  const inspectionDateText =
    (selectedEncar.inspectionDate && selectedEncar.inspectionDate !== '-')
      ? selectedEncar.inspectionDate
      : (selectedEncar.checkDate && selectedEncar.checkDate !== '-')
      ? selectedEncar.checkDate
      : null;

  // 💡 [2026-11-01 제이 규칙]: 보정가 필드가 항목에 있으면 표시하되, 없으면 계산하지 않고 표시에서 제외(V2에서 계산 금지)
  const adjustedPriceVal = (selectedEncar as any).adjustedPrice;
  const hasAdjustedPrice = adjustedPriceVal !== undefined && adjustedPriceVal !== null;

  // 색상 칩 스타일 (기존 콕핏과 100% 동일)
  const colorStyle = getCarColorStyle(selectedEncar.color);

  // 2. 사고/점검 내역 부위 추출
  const repList = ((selectedEncar.replaceNames && selectedEncar.replaceNames.length > 0)
    ? selectedEncar.replaceNames
    : selectedEncar.replaces) || [];
  const fixList = ((selectedEncar.repairNames && selectedEncar.repairNames.length > 0)
    ? selectedEncar.repairNames
    : selectedEncar.repairs) || [];
  const mappedRepList = repList.map(getDamagePartKoreanName).filter(Boolean);
  const mappedFixList = fixList.map(getDamagePartKoreanName).filter(Boolean);
  const hasRep = mappedRepList.length > 0;
  const hasFix = mappedFixList.length > 0;

  // 점검 정보 존재 여부 판정
  const hasDamageData = selectedEncar.damageData && Object.keys(selectedEncar.damageData).length > 0;
  const hasInspectionInfo = Boolean(
    inspectionDateText ||
    hasRep ||
    hasFix ||
    hasDamageData ||
    (selectedEncar.accidentType && selectedEncar.accidentType !== '미확인' && selectedEncar.accidentType !== '-')
  );

  return (
    <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl overflow-hidden shadow-sm space-y-0">
      {/* 1. 상단 바 (차명 원본링크, 세부모델, 보정가 뱃지, 우측 신차가 표기) */}
      <div className="px-5 py-3.5 border-b border-[#1e2029] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          <a
            href={detailUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-base sm:text-lg font-black text-white hover:text-sky-400 transition underline underline-offset-2 flex items-center gap-1.5 truncate group"
            title="엔카 매물 원본 상세페이지 열기"
          >
            <span>{selectedEncar.carName}</span>
            <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100 transition shrink-0" />
          </a>
          {selectedEncar.subModel && (
            <span className="text-xs sm:text-sm text-zinc-300 font-semibold">
              {selectedEncar.subModel}
            </span>
          )}
          {/* 상단 보정가 뱃지 */}
          {hasAdjustedPrice && (
            <span className="text-xs font-bold text-sky-300 font-mono shrink-0 px-2 py-0.5 rounded bg-sky-500/20 border border-sky-400">
              보정가: {Number(adjustedPriceVal).toLocaleString()}만원
            </span>
          )}
          {isInspectionLoading && (
            <span className="text-[11px] text-amber-400 font-mono animate-pulse">
              ⚡ 점검표 수신 중...
            </span>
          )}
        </div>

        {/* 우측 영역: 신차가(선택옵션가) 뱃지 + 상세 접기 버튼 */}
        <div className="flex items-center gap-2 shrink-0">
          {Boolean((selectedEncar as any).newCarPrice || (selectedEncar as any).originPrice) && (
            <span
              className="text-xs sm:text-sm font-bold text-amber-300 font-mono shrink-0 px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/30"
              title={
                typeof (selectedEncar as any).optionPrice === 'number'
                  ? `엔카 신차가: ${(((selectedEncar as any).newCarPrice || (selectedEncar as any).originPrice) || 0).toLocaleString()}만원 (출고 등급가: ${((selectedEncar as any).originPrice || 0).toLocaleString()}만 + 선택옵션: ${(selectedEncar as any).optionPrice.toLocaleString()}만)`
                  : `엔카 신차가: ${(((selectedEncar as any).newCarPrice || (selectedEncar as any).originPrice) || 0).toLocaleString()}만원`
              }
            >
              신차 {(((selectedEncar as any).newCarPrice || (selectedEncar as any).originPrice) || 0).toLocaleString()}만
              {typeof (selectedEncar as any).optionPrice === 'number' && (
                <span className="text-xs sm:text-sm font-semibold text-amber-200/90 ml-1">
                  ({(selectedEncar as any).optionPrice.toLocaleString()}만)
                </span>
              )}
            </span>
          )}

          {/* 상세 숨김 버튼 */}
          <button
            type="button"
            onClick={() => setIsCollapsed(true)}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-zinc-400 hover:text-white bg-[#151926] hover:bg-[#20283d] border border-[#262938] rounded-lg transition cursor-pointer"
            title="선택 차량 상세 패널 숨기기"
          >
            <ChevronUp className="w-3.5 h-3.5" />
            <span>상세 숨김</span>
          </button>
        </div>
      </div>

      {/* 2. 본문 한 박스 (스펙 위 · 2D 아래 세로 쌓기: 절반 너비 100% 활용) */}
      <div className="p-5 space-y-4">
        {/* [상단 스펙 영역: 기존 콕핏 카드 칩스 & 가격 레이아웃] */}
        <div className="space-y-3">
          {/* 2-1) 칩스 바: 연식 / 주행 km / 색상(점 형태) / 점검일 / 사고 배지 */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            {/* 연식 칩 */}
            <span className="px-2.5 py-1 rounded bg-[#1f222e] text-white font-bold font-mono">
              {selectedEncar.year}년식
            </span>

            {/* 주행거리 칩 */}
            <span className="px-2.5 py-1 rounded bg-[#1f222e] text-emerald-400 font-bold font-mono">
              {selectedEncar.mileage.toLocaleString()}km
            </span>

            {/* 색상 칩 (점 형태, getCarColorStyle 적용) */}
            <span
              className="px-2.5 py-1 rounded font-medium border text-xs"
              style={{
                backgroundColor: colorStyle.bgColor,
                color: colorStyle.textColor,
                borderColor: colorStyle.borderColor,
              }}
            >
              {colorStyle.dot} {colorStyle.displayName}
            </span>

            {/* 점검일 칩 */}
            {inspectionDateText ? (
              <span
                className="px-2.5 py-1 rounded bg-blue-500/20 text-blue-300 font-bold font-mono"
                title="법정 성능점검일자"
              >
                📋 점검: {inspectionDateText}
                {typeof selectedEncar.holdingDays === 'number' &&
                !isNaN(selectedEncar.holdingDays) &&
                selectedEncar.holdingDays >= 0
                  ? ` (${selectedEncar.holdingDays}일 전)`
                  : ''}
              </span>
            ) : null}

            {/* 사고 구분 배지 */}
            <span className={`px-2.5 py-1 rounded border text-xs font-bold ${accInfo.style}`}>
              {accInfo.text}
            </span>
          </div>

          {/* 2-2) 사고 부위 요약 텍스트 (배지 바로 아래, 기존 위치) */}
          {(hasRep || hasFix) && (
            <div className="pt-1 pb-0.5 text-xs flex flex-col gap-1">
              {hasRep && (
                <div className="text-rose-400 font-medium flex items-start gap-1">
                  <span className="font-bold shrink-0">🔴 교환(X):</span>
                  <span className="font-semibold text-rose-300">{mappedRepList.join(', ')}</span>
                </div>
              )}
              {hasFix && (
                <div className="text-amber-400 font-medium flex items-start gap-1">
                  <span className="font-bold shrink-0">🟡 판금/용접(W):</span>
                  <span className="font-semibold text-amber-300">{mappedFixList.join(', ')}</span>
                </div>
              )}
            </div>
          )}

          {/* 2-3) 대형 가격 표시 (Large Price Display) */}
          <div className="flex items-baseline gap-1.5 pt-1">
            <span className="text-2xl sm:text-3xl font-black text-amber-400 font-mono tracking-tight">
              {selectedEncar.price.toLocaleString()}
            </span>
            <span className="text-sm font-bold text-zinc-300">만원</span>
            {hasAdjustedPrice && (
              <span className="ml-3 text-xs sm:text-sm font-bold text-sky-400 font-mono">
                (보정가: {Number(adjustedPriceVal).toLocaleString()}만원)
              </span>
            )}
          </div>

          {/* 2-4) 옵션 정보 (신차 카탈로그 통합규격 매칭 및 상태별 색상 표시) */}
          {(() => {
            const rawOptText = selectedEncar.optionsText || '';
            const cleanOptText = rawOptText.replace(/\s+/g, '');
            const isNoOptionPlaceholder =
              cleanOptText === '추가옵션없음' ||
              cleanOptText === '기본출고사양(추가옵션없음)';

            if (!rawOptText || isNoOptionPlaceholder) {
              return (
                <div className="p-3 bg-[#0c0e14] rounded-lg border border-[#232634] text-xs space-y-1.5">
                  <span className="text-[11px] font-semibold text-[#8b8e9d] uppercase block">
                    주요 옵션
                  </span>
                  <p className="text-zinc-500 text-xs italic">
                    추가옵션 없음 또는 기본 트림 사양
                  </p>
                </div>
              );
            }

            // 매칭 데이터가 있으면 사용, 아직 수신 전이면 원문 리스트 폴백
            const fallbackList = splitOptionString(rawOptText);
            const displayList: Array<{
              displayName: string;
              rawName: string;
              matchType: 'exact' | 'fuzzy' | 'none';
              source: 'danawa' | 'encar' | 'none';
              price?: number | null;
            }> = matchedOptions.length > 0
              ? matchedOptions.map((m) => ({
                  displayName: m.match_type !== 'none' ? m.official_name : m.raw_name,
                  rawName: m.raw_name,
                  matchType: m.match_type,
                  source: m.source,
                  price: m.price,
                }))
              : fallbackList.map((raw) => ({
                  displayName: raw,
                  rawName: raw,
                  matchType: 'none',
                  source: 'none',
                }));

            return (
              <div className="p-3 bg-[#0c0e14] rounded-lg border border-[#232634] text-xs space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-[#8b8e9d] uppercase block">
                    주요 옵션 ({displayList.length}개)
                  </span>
                  <div className="flex items-center gap-2 text-[10px] text-zinc-500 font-medium">
                    <span className="flex items-center gap-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
                      정확
                    </span>
                    <span className="flex items-center gap-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />
                      퍼지
                    </span>
                    <span className="flex items-center gap-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 inline-block" />
                      미매칭
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap gap-1.5 pt-0.5">
                  {displayList.map((item, i) => {
                    let chipStyle = 'bg-[#1a1c26] text-zinc-300 border-[#2d3142]';
                    let titleText = `[미매칭 옵션] 원문: ${item.rawName}`;

                    if (item.matchType === 'exact') {
                      chipStyle = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40 font-semibold';
                      const srcLabel = item.source === 'danawa' ? '다나와' : '엔카';
                      titleText = `[${srcLabel} 카탈로그 정확 매칭] 표준명: ${item.displayName}${item.price ? ` (${Math.round(item.price / 10000)}만원)` : ''}`;
                    } else if (item.matchType === 'fuzzy') {
                      chipStyle = 'bg-amber-500/15 text-amber-300 border-amber-500/40 font-semibold';
                      const srcLabel = item.source === 'danawa' ? '다나와' : '엔카';
                      titleText = `[${srcLabel} 카탈로그 퍼지 매칭] 표준명: ${item.displayName} (원문: ${item.rawName})`;
                    }

                    return (
                      <span
                        key={i}
                        className={`px-2 py-0.5 rounded text-[11px] border flex items-center gap-1 transition select-none ${chipStyle}`}
                        title={titleText}
                      >
                        <span>{item.displayName}</span>
                      </span>
                    );
                  })}
                </div>
              </div>
            );
          })()}
        </div>

        {/* [하단 영역: 사고·점검 2D 상태도 (절반 너비 전체 100% 활용)] */}
        <div className="bg-[#14151b] border border-[#232634] rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-[#232634] pb-2">
            <span className="text-xs font-bold text-white">
              외판 및 주요골격 상태도
            </span>
            {inspectionDateText && (
              <span className="text-[11px] text-zinc-400 font-mono">
                점검일자: {inspectionDateText}
              </span>
            )}
          </div>

          {/* 분기 1: 점검 정보 불러오는 중 */}
          {isInspectionLoading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-400">
              <RefreshCw className="w-5 h-5 animate-spin text-[#cc9166]" />
              <span className="text-xs">점검 정보를 불러오는 중입니다...</span>
            </div>
          ) : !hasInspectionInfo ? (
            /* 분기 2: 점검 정보 없음 안내 */
            <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-500">
              <AlertCircle className="w-6 h-6 text-zinc-600 stroke-[1.5]" />
              <span className="text-xs font-bold text-zinc-400">점검 정보 없음</span>
              <p className="text-[11px] text-zinc-600">
                해당 차량의 온라인 성능상태점검기록부가 제공되지 않거나 조회가 불가합니다.
              </p>
            </div>
          ) : (
            /* 분기 3: 점검 정보 있음 -> 2D 상태도 렌더링 */
            <div className="pt-1">
              <CarDamageDiagram2D selectedEncar={selectedEncar} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
