import React, { useState, useEffect, useMemo } from 'react';
import {
  splitOptionString,
  NewCarCatalogData,
  stripOptionPriceText,
  MASTER_PACKAGE_CATALOG,
} from '@/services/biddingOptionCatalog';
import {
  matchOptionsSingle,
  BackendMatchedOption,
  compareOptionToOpposites,
} from '@/services/optionMatchingService';
import { OptionItem } from '@/services/chaolmaService';
import { EncarItem, KcarCarItem } from '@/components/BiddingCockpit/types';

// 💡 [11-03-26]: 케이카 상세 options.items name 목록 캐시 (중복 호출 방지)
const kcarDetailItemsCache: Record<string, string[]> = {};
const kcarDetailInflight: Record<string, Promise<string[]>> = {};

export async function fetchKcarDetailItemNames(carCd: string): Promise<string[]> {
  if (!carCd) return [];
  if (kcarDetailItemsCache[carCd]) {
    return kcarDetailItemsCache[carCd];
  }
  // 전역 window 캐시 확인 (상세 패널 등에서 이미 조회한 데이터 재사용)
  const winCache = typeof window !== 'undefined' ? (window as any).__KCAR_DETAIL_CACHE__?.[carCd] : null;
  if (winCache?.options?.items) {
    const names = winCache.options.items.map((it: any) => it.name).filter(Boolean);
    kcarDetailItemsCache[carCd] = names;
    return names;
  }

  if (carCd in kcarDetailInflight) {
    return kcarDetailInflight[carCd];
  }

  const promise = (async () => {
    try {
      const res = await fetch('/api/kcar/detail', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ carCd, include3d: false }),
        signal: AbortSignal.timeout(7000),
      });
      if (!res.ok) return [];
      const json = await res.json();
      if (json.success && json.data) {
        if (typeof window !== 'undefined') {
          if (!(window as any).__KCAR_DETAIL_CACHE__) (window as any).__KCAR_DETAIL_CACHE__ = {};
          (window as any).__KCAR_DETAIL_CACHE__[carCd] = json.data;
        }
        const items = json.data.options?.items || [];
        const names: string[] = items.map((it: any) => it.name).filter(Boolean);
        kcarDetailItemsCache[carCd] = names;
        return names;
      }
      return [];
    } catch {
      return [];
    } finally {
      delete kcarDetailInflight[carCd];
    }
  })();

  kcarDetailInflight[carCd] = promise;
  return promise;
}

export interface EffectiveCompCar {
  id?: string;
  year?: string | number;
  optionsText: string;
  options?: Array<{ name: string }>;
  color?: string;
  carName: string;
  isLoading?: boolean;
}

export const resolveEffectiveComp = (
  activeCompTab?: 'encar' | 'kcar' | string,
  selectedEncar?: EncarItem | null,
  selectedKcar?: KcarCarItem | null,
  kcarDetailOptions?: string[] | null,
  isKcarLoading?: boolean
): EffectiveCompCar | null => {
  if (activeCompTab === 'kcar' && selectedKcar) {
    // 💡 [11-03-26]: 케이카 비교차 옵션 원문으로 목록 optnNm(기본 편의사양) 대신 상세 options.items 사용
    const opts = (kcarDetailOptions && kcarDetailOptions.length > 0)
      ? kcarDetailOptions.map((name) => ({ name }))
      : undefined;

    return {
      id: selectedKcar.carCd,
      year: selectedKcar.year || '',
      optionsText: '', // optnNm 기본 편의사양 대조 폐지
      options: opts,
      color: selectedKcar.color,
      carName: selectedKcar.carName || selectedKcar.modelName || '케이카 매물',
      isLoading: Boolean(isKcarLoading || kcarDetailOptions === null),
    };
  }
  if (selectedEncar) {
    return {
      id: selectedEncar.id,
      year: selectedEncar.year || '',
      optionsText: selectedEncar.optionsText || '',
      options: selectedEncar.options,
      color: selectedEncar.color,
      carName: selectedEncar.carName || '엔카 매물',
      isLoading: false,
    };
  }
  return null;
};

export interface SidebarOptionSectionProps {
  targetOptions?: OptionItem[];
  optionsTag?: string;
  targetCarName?: string;
  targetYear?: string | number;
  selectedEncar?: EncarItem | null;
  selectedKcar?: KcarCarItem | null;
  activeCompTab?: 'encar' | 'kcar' | string;
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
 * 추가옵션 총 가격 판정 (백엔드 카탈로그 매칭 결과 기준, 11-03-11 백엔드 단일화)
 */
function calculateExtraOptionsTotalPrice(
  targetOptions?: OptionItem[],
  optionsTag?: string,
  targetMatchedOpts: BackendMatchedOption[] = []
): ExtraOptionPriceResult {
  const optNames: string[] = (targetOptions && targetOptions.length > 0)
    ? targetOptions.map((o) => o.name)
    : splitOptionString(optionsTag || '');

  // 1순위: 백엔드 카탈로그 공식가 합계
  if (targetMatchedOpts && targetMatchedOpts.length > 0) {
    let catalogSumMan = 0;
    const matchedLines: string[] = [];
    const unpricedOptions: string[] = [];

    for (const mi of targetMatchedOpts) {
      const clean = mi.clean_name || mi.raw_name;
      if (!clean) continue;
      if (typeof mi.price === 'number' && mi.price > 0) {
        const man = Math.round(mi.price / 10000);
        catalogSumMan += man;
        const srcLabel = mi.source === 'danawa' ? '다나와' : mi.source === 'encar' ? '엔카' : (mi.source || '');
        const yrLabel = mi.matched_year ? `${mi.matched_year}년` : '';
        const meta = [srcLabel, yrLabel].filter(Boolean).join(' ');
        matchedLines.push(`- ${clean}: ${man.toLocaleString()}만 (${mi.official_name}${meta ? ` · ${meta}` : ''})`);
      } else {
        unpricedOptions.push(clean);
      }
    }

    if (catalogSumMan > 0) {
      const unpricedNote = unpricedOptions.length > 0 ? `\n(가격 미확인 옵션 ${unpricedOptions.length}개 제외)` : '';
      return {
        badgeText: `총 ${catalogSumMan.toLocaleString()}만`,
        tooltip: `[신차 공식 카탈로그 기준가 합계]\n${matchedLines.join('\n')}${unpricedNote}\n합계: ${catalogSumMan.toLocaleString()}만원`,
      };
    }
  }

  // 2순위: targetOptions 합계가 0보다 크면 그대로 쓴다
  if (targetOptions && targetOptions.length > 0) {
    const sum1 = targetOptions.reduce((acc, c) => {
      const pMan = typeof c.price_man === 'number' && !isNaN(c.price_man) && c.price_man > 0
        ? c.price_man
        : (typeof c.price === 'number' && !isNaN(c.price) && c.price > 0 ? Math.round(c.price / 10000) : 0);
      return acc + pMan;
    }, 0);

    if (sum1 > 0) {
      const lines = targetOptions.map((c) => {
        const pMan = (typeof c.price_man === 'number' && !isNaN(c.price_man) && c.price_man > 0)
          ? c.price_man
          : (typeof c.price === 'number' && !isNaN(c.price) && c.price > 0 ? Math.round(c.price / 10000) : 0);
        return `- ${c.name}: ${pMan > 0 ? `${pMan.toLocaleString()}만` : '가격미확인'}`;
      });
      return {
        badgeText: `총 ${sum1.toLocaleString()}만`,
        tooltip: `[옵션 상세 가격 (실차 데이터)]\n${lines.join('\n')}\n합계: ${sum1.toLocaleString()}만원`,
      };
    }
  }

  return {
    badgeText: '가격 미확인',
    tooltip: '옵션 가격 정보가 제공되지 않았습니다.',
  };
}

export const SidebarOptionSection: React.FC<SidebarOptionSectionProps> = ({
  targetOptions,
  optionsTag,
  targetCarName,
  targetYear,
  selectedEncar,
  selectedKcar,
  activeCompTab,
  targetCatalog,
  unclassifiedBalance = 0,
}) => {
  // 💡 [11-03-11]: 목표차 옵션 백엔드 매칭 조회 (단건 함수 사용)
  const [targetMatchedOpts, setTargetMatchedOpts] = useState<BackendMatchedOption[]>([]);
  // 💡 [11-03-19]: 비교차 옵션 백엔드 단건 매칭 조회 상태
  const [compMatchedOpts, setCompMatchedOpts] = useState<BackendMatchedOption[]>([]);

  const targetOptNames: string[] = useMemo(() => {
    return (targetOptions && targetOptions.length > 0)
      ? targetOptions.map((o) => o.name)
      : splitOptionString(optionsTag || '');
  }, [targetOptions, optionsTag]);

  // 💡 [11-03-34]: 신차 카탈로그 뷰어 링크 (목표차 모델명/연식 동적 바인딩)
  const catalogHref = useMemo(() => {
    const params: string[] = [];
    // 💡 [11-03-48]: 뷰어는 카탈로그 키(matched_key)로 모델을 찾는다. 표시명(예: "신형 카니발(KA4)")이 아니라
    // 백엔드가 반환한 targetCatalog.model(예: "카니발 4세대")을 우선 사용하고, 없으면 표시명으로 폴백.
    const viewerModel = (targetCatalog?.model || targetCarName || '').toString().trim();
    if (viewerModel) {
      params.push(`model=${encodeURIComponent(viewerModel)}`);
    }
    if (targetYear && String(targetYear).trim()) {
      const yrStr = String(targetYear).trim();
      const mYr = yrStr.match(/(?:20)?(\d{2})/);
      const fullYr = yrStr.match(/20\d{2}/) ? yrStr.match(/20\d{2}/)![0] : (mYr ? `20${mYr[1]}` : yrStr);
      params.push(`year=${encodeURIComponent(fullYr)}`);
    }
    if (params.length > 0) {
      return `/newcar-catalog.html#${params.join('&')}`;
    }
    return '/newcar-catalog.html';
  }, [targetCarName, targetYear, targetCatalog?.model]);

  useEffect(() => {
    if (targetOptNames.length === 0 || !targetCarName) {
      setTargetMatchedOpts([]);
      return;
    }

    let isMounted = true;
    matchOptionsSingle({
      carName: targetCarName,
      year: targetYear || '',
      optionsList: targetOptNames,
    }).then((res) => {
      if (isMounted) setTargetMatchedOpts(res);
    });

    return () => {
      isMounted = false;
    };
  }, [targetCarName, targetYear, targetOptNames]);

  // 1. 추가 옵션 보유 여부 및 개수 판정
  const hasOptions = (targetOptions && targetOptions.length > 0) || Boolean(optionsTag && optionsTag.trim());
  const optCount = (targetOptions && targetOptions.length > 0)
    ? targetOptions.length
    : (optionsTag ? splitOptionString(optionsTag).length : 0);

  // 2. 추가 옵션 총 가격 판정
  const priceInfo = useMemo(() => {
    return calculateExtraOptionsTotalPrice(
      targetOptions,
      optionsTag,
      targetMatchedOpts
    );
  }, [targetOptions, optionsTag, targetMatchedOpts]);

  // 💡 [11-03-26]: 케이카 탭일 때 선택 차량의 상세 API(/api/kcar/detail) options.items 목록 조회 (캐시 재사용)
  const isKcarTab = activeCompTab === 'kcar';
  const selectedKcarCd = isKcarTab ? selectedKcar?.carCd : undefined;

  const [kcarDetailOptions, setKcarDetailOptions] = useState<string[] | null>(() => {
    if (selectedKcarCd && kcarDetailItemsCache[selectedKcarCd]) {
      return kcarDetailItemsCache[selectedKcarCd];
    }
    return null;
  });
  const [isKcarDetailLoading, setIsKcarDetailLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!isKcarTab || !selectedKcarCd) {
      setKcarDetailOptions(null);
      setIsKcarDetailLoading(false);
      return;
    }

    if (kcarDetailItemsCache[selectedKcarCd]) {
      setKcarDetailOptions(kcarDetailItemsCache[selectedKcarCd]);
      setIsKcarDetailLoading(false);
      return;
    }

    let isMounted = true;
    setIsKcarDetailLoading(true);
    fetchKcarDetailItemNames(selectedKcarCd).then((names) => {
      if (isMounted) {
        setKcarDetailOptions(names);
        setIsKcarDetailLoading(false);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [isKcarTab, selectedKcarCd]);

  const effectiveComp = resolveEffectiveComp(
    activeCompTab,
    selectedEncar,
    selectedKcar,
    kcarDetailOptions,
    isKcarDetailLoading
  );

  // 3. 비교차 옵션 파싱 (색상 제외 원문 옵션 문자열 목록, 11-03-21 단건 호출 입력용)
  const rawCompOpts: string[] = useMemo(() => {
    if (!effectiveComp || effectiveComp.isLoading) return [];
    return (effectiveComp.options && effectiveComp.options.length > 0)
      ? effectiveComp.options.map((o: any) => o.name || o)
      : splitOptionString(effectiveComp.optionsText || '');
  }, [effectiveComp]);

  const compColor = effectiveComp?.color?.trim();
  const compOpts = (compColor && compColor !== '-' && compColor !== '미확인')
    ? [...rawCompOpts, compColor]
    : rawCompOpts;

  // 💡 [11-03-26]: 상세 조회 로딩 중이거나 실패했을 때는 잘못된 +를 확정 표시하지 않음
  const hasComp = Boolean(effectiveComp && !effectiveComp.isLoading && compOpts.length > 0);

  // 💡 [11-03-19/21]: 비교차 변경 시 단건 매칭(matchOptionsSingle) 실행 (분리된 optionsList 전달, 언마운트 가드 포함)
  useEffect(() => {
    if (!effectiveComp || !effectiveComp.carName) {
      setCompMatchedOpts([]);
      return;
    }

    const hasOpts = rawCompOpts.length > 0 || Boolean(effectiveComp.optionsText && effectiveComp.optionsText.trim());

    if (!hasOpts) {
      setCompMatchedOpts([]);
      return;
    }

    let isMounted = true;
    matchOptionsSingle({
      id: effectiveComp.id,
      carName: effectiveComp.carName,
      year: effectiveComp.year || '',
      optionsList: rawCompOpts.length > 0 ? rawCompOpts : undefined,
      optionsText: rawCompOpts.length === 0 ? (effectiveComp.optionsText || '') : undefined,
    }).then((res) => {
      if (isMounted) {
        setCompMatchedOpts(res || []);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [
    effectiveComp?.id,
    effectiveComp?.carName,
    effectiveComp?.year,
    effectiveComp?.optionsText,
    rawCompOpts,
  ]);

  // 💡 [11-03-19]: 비교차 옵션 대조를 단건 매칭 객체(BackendMatchedOption[])로 통일 (원문 문자열 대조 폐지)
  const compOpposites: BackendMatchedOption[] = useMemo(() => {
    if (!effectiveComp || compOpts.length === 0) return [];
    return compOpts.map((co) => {
      const found = compMatchedOpts.find((m) => m.raw_name === co);
      if (found) return found;
      return {
        raw_name: co,
        clean_name: co,
        official_name: '',
        price: null,
        match_type: 'none',
        source: 'none',
      };
    });
  }, [effectiveComp, compOpts, compMatchedOpts]);

  // 우세/순정 배지 판정 (규칙 4-d 기반)
  const renderMatchBadge = () => {
    if (!effectiveComp?.optionsText || !optionsTag || !optionsTag.trim()) {
      return (
        <span className="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">
          조회차량 순정
        </span>
      );
    }

    if (compOpts.length === 0 || targetOptNames.length === 0) {
      return (
        <span className="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">
          조회차량 순정
        </span>
      );
    }

    const matchDetails = targetOptNames.map((to) => {
      const tgtTarget = targetMatchedOpts.find((m) => m.raw_name === to) || to;
      return compareOptionToOpposites(tgtTarget, compOpposites);
    });

    const winCount = matchDetails.filter((d) => d.symbol === '+').length;
    const exactCount = matchDetails.filter((d) => d.symbol === '✓').length;
    const fuzzyCount = matchDetails.filter((d) => d.symbol === '~').length;

    if (winCount > 0) {
      return (
        <span
          title={`비교 매물(${effectiveComp.carName}) 대비 내 차 우세/고유 옵션: ${winCount}개\n공식 일치: ${exactCount}개 / 추정 매칭: ${fuzzyCount}개`}
          className="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded bg-blue-500/30 text-blue-300 font-bold border border-blue-500/60 cursor-help"
        >
          🔵 우세 {winCount}개
        </span>
      );
    }
    return (
      <span
        title={`비교 매물(${effectiveComp.carName})과 핵심 옵션 일치 (공식 일치: ${exactCount}개, 추정: ${fuzzyCount}개)`}
        className="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/30 text-emerald-300 font-bold border border-emerald-500/60 cursor-help"
      >
        🟢 공통 사양
      </span>
    );
  };

  return (
    <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-3.5 space-y-2 text-xs">
      {/* 1. 상단 라인: '추가 옵션' 라벨 + 신차 옵션 N개 + 총 가격 + 우세/순정 배지 (1행 묶음, 왼쪽부터 gap-1 균일 배치, 줄바꿈 금지) */}
      <div className="flex items-center gap-1 flex-nowrap whitespace-nowrap min-h-[22px]">
        <a
          href={catalogHref}
          target="_blank"
          rel="noopener"
          className="text-[11px] font-semibold text-[#8b8e9d] uppercase shrink-0 hover:underline cursor-pointer"
          title="새 탭에서 신차 공식 카탈로그 열기"
        >
          추가 옵션
        </a>
        {hasOptions && (
          <>
            <span className="inline-flex items-center text-[10px] px-1 py-0.5 rounded bg-blue-500/15 text-blue-300 font-bold border border-blue-500/30 shrink-0">
              신차 옵션 {optCount}개
            </span>
            <span
              title={priceInfo.tooltip}
              className="inline-flex items-center text-[10px] px-1 py-0.5 rounded bg-amber-500/20 text-amber-200 font-bold border border-amber-500/40 cursor-help shrink-0"
            >
              {priceInfo.badgeText}
            </span>
            {renderMatchBadge()}
          </>
        )}
      </div>

      {/* 2. 중단 라인: 패키지 포함 안내 (MASTER_PACKAGE_CATALOG 기반, 백엔드 매칭 없음일 때만 표시) */}
      {(() => {
        const pkgTooltips: Array<{ pkgName: string; tip: string }> = [];
        for (const pkg of MASTER_PACKAGE_CATALOG) {
          const hasInTarget = targetOptNames.some((opt) => opt.includes(pkg.name));
          const hasInMatched = targetMatchedOpts.some((m) => (m.official_name || '').includes(pkg.name));
          if (hasInTarget && !hasInMatched && pkg.items && pkg.items.length > 0) {
            pkgTooltips.push({ pkgName: pkg.name, tip: `[${pkg.name} 포함 품목]\n- ${pkg.items.join('\n- ')}` });
          }
        }
        if (pkgTooltips.length === 0) return null;
        return (
          <div className="flex flex-wrap gap-1 pt-0.5">
            {pkgTooltips.map(({ pkgName, tip }) => (
              <span
                key={pkgName}
                title={tip}
                className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800/80 text-zinc-300 border border-zinc-700/60 cursor-help inline-flex items-center gap-1"
              >
                <span>📦</span>
                <span className="font-semibold">{pkgName} 포함</span>
              </span>
            ))}
          </div>
        );
      })()}

      {/* 3. 옵션 칩 목록 */}
      {hasOptions ? (
        <div className="flex flex-wrap gap-1.5 pt-0.5 max-h-[160px] overflow-y-auto">
          {(() => {
            if (targetOptions && targetOptions.length > 0) {
              const mapped = targetOptions.map((opt, idx) => {
                const pMan = opt.price_man || Math.round((opt.price || 0) / 10000);
                const mi = targetMatchedOpts.find((m) => m.raw_name === opt.name);
                const optDisplayName = mi?.official_name || opt.name;
                const displayName = pMan > 0 ? `${optDisplayName}(${pMan}만)` : optDisplayName;
                const compareRes = compareOptionToOpposites(mi || opt.name, compOpposites);

                let tipText = opt.desc || `${opt.name} (${pMan}만)`;
                if (mi && mi.official_name) {
                  const srcLabel = mi.source === 'danawa' ? '다나와' : mi.source === 'encar' ? '엔카' : (mi.source || '');
                  const yrLabel = mi.matched_year ? `${mi.matched_year}년` : '';
                  const meta = [srcLabel, yrLabel].filter(Boolean).join(' ');
                  tipText = `[신차 공식 표준명: ${mi.official_name}${meta ? ` · ${meta}` : ''}]\n${tipText}`;
                }
                if (mi?.desc && mi.desc.trim() && !tipText.includes(mi.desc.trim())) {
                  tipText = `${tipText}\n${mi.desc.trim()}`;
                }

                const symbolRank = !hasComp ? 4 : compareRes.symbol === '✓' ? 1 : compareRes.symbol === '~' ? 2 : 3;

                return {
                  idx,
                  displayName,
                  tipText,
                  compareRes,
                  symbolRank,
                };
              });

              // 💡 [11-03-14]: 공식 일치(✓) -> 추정(~) -> 내 차만 있음(+) 순 정렬 (그룹 내 원문 순서 유지)
              const sorted = hasComp
                ? mapped.slice().sort((a, b) => a.symbolRank - b.symbolRank || a.idx - b.idx)
                : mapped;

              return (
                <>
                  {sorted.map((item) => {
                    const { idx, displayName, tipText, compareRes } = item;

                    if (hasComp && compareRes.symbol === '+') {
                      return (
                        <span
                          key={idx}
                          title={tipText}
                          className="px-2 py-0.5 rounded bg-blue-500/30 border border-blue-500/60 text-blue-300 font-bold text-[10.5px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                        >
                          <span className="text-blue-300 text-[10px] font-bold">+</span>
                          <span>{displayName}</span>
                        </span>
                      );
                    }

                    if (hasComp && compareRes.symbol === '~') {
                      return (
                        <span
                          key={idx}
                          title={tipText}
                          className="px-2 py-0.5 rounded bg-amber-500/30 border border-amber-500/60 text-amber-300 font-bold text-[10.5px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                        >
                          <span className="text-amber-300 text-[10px] font-bold">~</span>
                          <span>{displayName}</span>
                        </span>
                      );
                    }

                    if (hasComp && compareRes.symbol === '✓') {
                      return (
                        <span
                          key={idx}
                          title={tipText}
                          className="px-2 py-0.5 rounded bg-emerald-500/30 border border-emerald-500/60 text-emerald-300 font-bold text-[10.5px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                        >
                          <span className="text-emerald-300 text-[10px] font-bold">✓</span>
                          <span>{displayName}</span>
                        </span>
                      );
                    }

                    // 비교 대상 없을 때 (비교가 아니므로 회색 계열)
                    return (
                      <span
                        key={idx}
                        title={tipText}
                        className="px-2 py-0.5 rounded bg-zinc-800/60 border border-zinc-700 text-zinc-300 font-medium text-[10.5px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                      >
                        <span className="text-zinc-500 text-[10px]">•</span>
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

            const mappedOpts = tgtOpts.map((opt, idx) => {
              const mi = targetMatchedOpts.find((m) => m.raw_name === opt);
              const compareRes = compareOptionToOpposites(mi || opt, compOpposites);
              const displayName = mi?.official_name || opt;

              let tipText = `[${opt}]\n조회 차량의 장착 순정 옵션입니다.`;
              if (mi && mi.official_name) {
                const srcLabel = mi.source === 'danawa' ? '다나와' : mi.source === 'encar' ? '엔카' : (mi.source || '');
                const yrLabel = mi.matched_year ? `${mi.matched_year}년` : '';
                const pLabel = mi.price ? ` (${Math.round(mi.price / 10000)}만)` : '';
                const meta = [srcLabel, yrLabel].filter(Boolean).join(' ');
                tipText = `[신차 공식 표준명: ${mi.official_name}${pLabel}${meta ? ` · ${meta}` : ''}]\n원문: ${opt}`;
              }
              if (mi?.desc && mi.desc.trim()) {
                tipText = `${tipText}\n${mi.desc.trim()}`;
              }

              const symbolRank = !hasComp ? 4 : compareRes.symbol === '✓' ? 1 : compareRes.symbol === '~' ? 2 : 3;

              return {
                idx,
                opt,
                displayName,
                tipText,
                compareRes,
                symbolRank,
              };
            });

            // 💡 [11-03-14]: 공식 일치(✓) -> 추정(~) -> 내 차만 있음(+) 순 정렬
            const sortedOpts = hasComp
              ? mappedOpts.slice().sort((a, b) => a.symbolRank - b.symbolRank || a.idx - b.idx)
              : mappedOpts;

            return sortedOpts.map((item) => {
              const { idx, opt, displayName, tipText, compareRes } = item;

              if (hasComp && compareRes.symbol === '+') {
                return (
                  <span
                    key={idx}
                    title={tipText}
                    className="px-2 py-0.5 rounded bg-blue-500/30 border border-blue-500/60 text-blue-300 font-bold text-[10.5px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                  >
                    <span className="text-blue-300 text-[10px] font-bold">+</span>
                    <span>{displayName}</span>
                  </span>
                );
              }

              if (hasComp && compareRes.symbol === '~') {
                return (
                  <span
                    key={idx}
                    title={tipText}
                    className="px-2 py-0.5 rounded bg-amber-500/30 border border-amber-500/60 text-amber-300 font-bold text-[10.5px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                  >
                    <span className="text-amber-300 text-[10px] font-bold">~</span>
                    <span>{displayName}</span>
                  </span>
                );
              }

              if (hasComp && compareRes.symbol === '✓') {
                return (
                  <span
                    key={idx}
                    title={tipText}
                    className="px-2 py-0.5 rounded bg-emerald-500/30 border border-emerald-500/60 text-emerald-300 font-bold text-[10.5px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                  >
                    <span className="text-emerald-300 text-[10px] font-bold">✓</span>
                    <span>{displayName}</span>
                  </span>
                );
              }

              return (
                <span
                  key={idx}
                  title={tipText}
                  className="px-2 py-0.5 rounded bg-zinc-800/60 border border-zinc-700 text-zinc-300 font-medium text-[10.5px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                >
                  <span className="text-zinc-500 text-[10px]">•</span>
                  <span>{displayName}</span>
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
