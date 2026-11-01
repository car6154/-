import React from 'react';
import {
  splitOptionString,
  getOptionMatchDetail,
  NewCarCatalogData,
  findOfficialCatalogOption,
  stripOptionPriceText,
} from '@/services/biddingOptionCatalog';
import { OptionItem } from '@/services/chaolmaService';
import { EncarItem } from '@/components/BiddingCockpit/types';

export interface SidebarOptionSectionProps {
  targetOptions?: OptionItem[];
  optionsTag?: string;
  selectedEncar?: EncarItem | null;
  targetCatalog?: NewCarCatalogData | null;
  compCatalog?: NewCarCatalogData | null;
  historyOptionTotalMan?: number;
  unclassifiedBalance?: number;
}

interface ExtraOptionPriceResult {
  badgeText: string;
  tooltip: string;
}

/**
 * 추가옵션 총 가격 판정 (기존 CockpitSidebar.tsx calculateExtraOptionsTotalPrice와 100% 동일)
 */
function calculateExtraOptionsTotalPrice(
  targetOptions?: OptionItem[],
  optionsTag?: string,
  targetCatalog?: NewCarCatalogData | null,
  compCatalog?: NewCarCatalogData | null,
  historyOptionTotalMan?: number
): ExtraOptionPriceResult {
  // 1순위: targetOptions 합계가 0보다 크면 그대로 쓴다
  if (targetOptions && targetOptions.length > 0) {
    const sum1 = targetOptions.reduce((acc, c) => {
      const pMan = typeof c.price_man === 'number' && !isNaN(c.price_man) && c.price_man > 0
        ? c.price_man
        : (typeof c.price === 'number' && !isNaN(c.price) && c.price > 0 ? Math.round(c.price / 10000) : 0);
      return acc + pMan;
    }, 0);

    if (sum1 > 0) {
      const lines = targetOptions.map(c => {
        const pMan = (typeof c.price_man === 'number' && !isNaN(c.price_man) && c.price_man > 0)
          ? c.price_man
          : (typeof c.price === 'number' && !isNaN(c.price) && c.price > 0 ? Math.round(c.price / 10000) : 0);
        return `- ${c.name}: ${pMan > 0 ? `${pMan.toLocaleString()}만` : '가격미확인'}`;
      });
      return {
        badgeText: `총 ${sum1.toLocaleString()}만`,
        tooltip: `[옵션 상세 가격 (실차 데이터)]\n${lines.join('\n')}\n합계: ${sum1.toLocaleString()}만원`
      };
    }
  }

  // 2순위: 1순위가 0이거나 비어 있고, historyOptionTotalMan이 0보다 크면 총 {historyOptionTotalMan}만을 표시한다.
  const hasOptions = (targetOptions && targetOptions.length > 0) || (optionsTag && optionsTag.trim() && !optionsTag.includes('옵션 없음'));
  if (hasOptions && typeof historyOptionTotalMan === 'number' && historyOptionTotalMan > 0) {
    return {
      badgeText: `총 ${historyOptionTotalMan.toLocaleString()}만`,
      tooltip: `[차얼마 옵션 총액] 합계: ${historyOptionTotalMan.toLocaleString()}만원`
    };
  }

  // 3순위: optionsTag 안의 [옵션총액] 정규식
  if (optionsTag && optionsTag.trim()) {
    const match = optionsTag.match(/\[(?:순정)?옵션총액:?\s*([0-9,]+만?)\]/);
    if (match && match[1]) {
      const rawVal = match[1].trim();
      const badgeText = rawVal.endsWith('만') ? `총 ${rawVal}` : `총 ${rawVal}만`;
      return {
        badgeText,
        tooltip: `옵션 정보에 기재된 총액: ${rawVal}`
      };
    }
  }

  // 4순위: 카탈로그 공식가 합계 (targetCatalog -> compCatalog)
  const optNames: string[] = (targetOptions && targetOptions.length > 0)
    ? targetOptions.map(o => o.name)
    : splitOptionString(optionsTag || '');

  if (optNames.length > 0) {
    let catalogSumMan = 0;
    const matchedLines: string[] = [];
    const unpricedOptions: string[] = [];

    for (const name of optNames) {
      const clean = stripOptionPriceText(name);
      if (!clean) continue;
      const official = findOfficialCatalogOption(clean, targetCatalog) || findOfficialCatalogOption(clean, compCatalog);
      if (official && typeof official.price === 'number' && official.price > 0) {
        const man = Math.round(official.price / 10000);
        catalogSumMan += man;
        matchedLines.push(`- ${clean}: ${man.toLocaleString()}만 (${official.officialName})`);
      } else {
        unpricedOptions.push(clean);
      }
    }

    if (catalogSumMan > 0) {
      const unpricedNote = unpricedOptions.length > 0 ? `\n(가격 미확인 옵션 ${unpricedOptions.length}개 제외)` : '';
      return {
        badgeText: `총 ${catalogSumMan.toLocaleString()}만`,
        tooltip: `[신차 공식 카탈로그 기준가 합계]\n${matchedLines.join('\n')}${unpricedNote}\n합계: ${catalogSumMan.toLocaleString()}만원`
      };
    }
  }

  return {
    badgeText: '가격 미확인',
    tooltip: '옵션 가격 정보를 확인할 수 없습니다.'
  };
}

export const SidebarOptionSection: React.FC<SidebarOptionSectionProps> = ({
  targetOptions,
  optionsTag,
  selectedEncar,
  targetCatalog,
  compCatalog,
  historyOptionTotalMan,
  unclassifiedBalance = 0,
}) => {
  const hasOptions = (targetOptions && targetOptions.length > 0) || (optionsTag && optionsTag.trim().length > 0 && !optionsTag.includes('옵션 없음'));

  // 1. 옵션 개수
  const optCount = targetOptions && targetOptions.length > 0
    ? targetOptions.length
    : splitOptionString(optionsTag || '').length;

  // 2. 추가옵션 총 가격
  const priceInfo = calculateExtraOptionsTotalPrice(
    targetOptions,
    optionsTag,
    targetCatalog,
    compCatalog,
    historyOptionTotalMan
  );

  // 3. 비교차 옵션 파싱 및 매칭
  const compOpts = (selectedEncar?.options && selectedEncar.options.length > 0)
    ? selectedEncar.options.map((o: any) => o.name || o)
    : splitOptionString(selectedEncar?.optionsText || '');
  const hasComp = compOpts.length > 0;

  // 우세/순정 배지 판정
  const renderMatchBadge = () => {
    if (!selectedEncar?.optionsText || !optionsTag || !optionsTag.trim()) {
      return (
        <span className="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">
          조회차량 순정
        </span>
      );
    }
    const tgtOpts = (targetOptions && targetOptions.length > 0)
      ? targetOptions.map(o => o.name)
      : splitOptionString(optionsTag);

    if (compOpts.length === 0 || tgtOpts.length === 0) {
      return (
        <span className="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">
          조회차량 순정
        </span>
      );
    }

    const matchDetails = tgtOpts.map(to => getOptionMatchDetail(to, compOpts, 'target_vs_comp', targetCatalog, compCatalog));
    const winCount = matchDetails.filter(d => !d.isMatched).length;
    const exactCount = matchDetails.filter(d => d.confidence === 'exact').length;
    const fuzzyCount = matchDetails.filter(d => d.confidence === 'fuzzy').length;

    if (winCount > 0) {
      return (
        <span
          title={`비교 매물(${selectedEncar.carName}) 대비 내 차 우세/고유 옵션: ${winCount}개\n공식 일치: ${exactCount}개 / 추정 매칭: ${fuzzyCount}개`}
          className="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500 cursor-help"
        >
          🟢 우세 {winCount}개
        </span>
      );
    }
    return (
      <span
        title={`비교 매물(${selectedEncar.carName})과 핵심 옵션 일치 (공식 일치: ${exactCount}개, 추정: ${fuzzyCount}개)`}
        className="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 font-bold border border-sky-400/50 cursor-help"
      >
        🔵 공통 사양
      </span>
    );
  };

  return (
    <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-3.5 space-y-2 text-xs">
      {/* 1. 상단 라인: '추가 옵션' 라벨 + 신차 옵션 N개 + 총 가격 + 우세/순정 배지 */}
      <div className="flex items-center justify-between gap-1.5 flex-wrap">
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[11px] font-semibold text-[#8b8e9d] uppercase">추가 옵션</span>
          {hasOptions && (
            <span className="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-300 font-bold border border-blue-500/30">
              신차 옵션 {optCount}개
            </span>
          )}
        </div>

        {hasOptions && (
          <div className="flex items-center gap-1.5 shrink-0">
            <span
              title={priceInfo.tooltip}
              className="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-200 font-bold border border-amber-500/40 cursor-help truncate max-w-[120px]"
            >
              {priceInfo.badgeText}
            </span>
            {renderMatchBadge()}
          </div>
        )}
      </div>

      {/* 2. 🎨 옵션 색상 범례 안내 */}
      {hasOptions && (
        <div className="flex items-center gap-1.5 text-[9.5px] text-zinc-400 bg-zinc-900/60 px-2 py-1 rounded border border-zinc-800 flex-wrap">
          <span className="text-zinc-500 font-medium">범례:</span>
          {selectedEncar?.optionsText ? (
            <>
              <span className="flex items-center gap-0.5 text-emerald-400 font-semibold" title="비교차에는 없고 내 차에만 있는 고유/우세 옵션">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0"></span>내차우세(+)
              </span>
              <span className="flex items-center gap-0.5 text-amber-400 font-semibold" title="스펙 유사로 추정 매칭된 옵션">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0"></span>추정(~)
              </span>
              <span className="flex items-center gap-0.5 text-sky-400 font-semibold" title="비교차와 내 차 모두 동일한 공통 옵션">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-400 shrink-0"></span>공통(✓)
              </span>
            </>
          ) : (
            <span className="text-sky-300 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 shrink-0"></span>장착 순정 옵션 (비교 매물 선택 시 우세 대조)
            </span>
          )}
        </div>
      )}

      {/* 3. 옵션 칩 목록 */}
      {hasOptions ? (
        <div className="flex flex-wrap gap-1.5 pt-0.5 max-h-[160px] overflow-y-auto">
          {(() => {
            if (targetOptions && targetOptions.length > 0) {
              return (
                <>
                  {targetOptions.map((opt, idx) => {
                    const pMan = opt.price_man || Math.round((opt.price || 0) / 10000);
                    const displayName = pMan > 0 ? `${opt.name}(${pMan}만)` : opt.name;
                    const detail = getOptionMatchDetail(opt.name, compOpts, 'target_vs_comp', targetCatalog, compCatalog);

                    if (hasComp && !detail.isMatched) {
                      return (
                        <span
                          key={idx}
                          title={detail.tooltipText || opt.desc || `${opt.name} (${pMan}만)`}
                          className="px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500 text-emerald-400 font-bold text-[10.5px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                        >
                          <span className="text-emerald-400 text-[10px] font-black">+</span>
                          <span>{displayName}</span>
                        </span>
                      );
                    }

                    if (hasComp && detail.confidence === 'fuzzy') {
                      return (
                        <span
                          key={idx}
                          title={detail.tooltipText || opt.desc || `${opt.name} (${pMan}만)`}
                          className="px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/60 text-amber-300 font-semibold text-[10.5px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                        >
                          <span className="text-amber-400 text-[10px] font-black">~</span>
                          <span>{displayName}</span>
                        </span>
                      );
                    }

                    return (
                      <span
                        key={idx}
                        title={detail.tooltipText || opt.desc || `[${opt.name}]\n조회 차량의 장착 순정 옵션입니다.`}
                        className="px-2 py-0.5 rounded bg-sky-500/20 border border-sky-400/60 text-sky-300 font-semibold text-[10.5px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                      >
                        <span className="text-sky-400 text-[10px]">{hasComp ? '✓' : '•'}</span>
                        <span>{displayName}</span>
                      </span>
                    );
                  })}

                  {unclassifiedBalance > 0 && (
                    <span
                      title={`카탈로그 옵션가 합계와 출고가 차액 간의 미분류 잔액입니다.`}
                      className="px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/50 text-amber-300 font-medium text-[10.5px] flex items-center gap-1 cursor-help font-mono"
                    >
                      <span>ℹ️ 미분류 ({unclassifiedBalance}만)</span>
                    </span>
                  )}
                </>
              );
            }

            const tgtOpts = splitOptionString(optionsTag || '');
            if (tgtOpts.length === 0) {
              return (
                <div className="text-[11px] text-zinc-500 py-0.5 italic">
                  추가 옵션 없음 (기본 출고 사양)
                </div>
              );
            }

            return tgtOpts.map((opt, idx) => {
              const detail = getOptionMatchDetail(opt, compOpts, 'target_vs_comp', targetCatalog, compCatalog);

              if (hasComp && !detail.isMatched) {
                return (
                  <span
                    key={idx}
                    title={detail.tooltipText}
                    className="px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500 text-emerald-400 font-bold text-[10.5px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                  >
                    <span className="text-emerald-400 text-[10px] font-black">+</span>
                    <span>{opt}</span>
                  </span>
                );
              }

              if (hasComp && detail.confidence === 'fuzzy') {
                return (
                  <span
                    key={idx}
                    title={detail.tooltipText}
                    className="px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/60 text-amber-300 font-semibold text-[10.5px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                  >
                    <span className="text-amber-400 text-[10px] font-black">~</span>
                    <span>{opt}</span>
                  </span>
                );
              }

              return (
                <span
                  key={idx}
                  title={detail.tooltipText || `[${opt}]\n조회 차량의 장착 순정 옵션입니다.`}
                  className="px-2 py-0.5 rounded bg-sky-500/20 border border-sky-400/60 text-sky-300 font-semibold text-[10.5px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                >
                  <span className="text-sky-400 text-[10px]">{hasComp ? '✓' : '•'}</span>
                  <span>{opt}</span>
                </span>
              );
            });
          })()}
        </div>
      ) : (
        <div className="text-[11px] text-zinc-500 italic">
          추가 옵션 정보 없음
        </div>
      )}
    </div>
  );
};
