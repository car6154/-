import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  RefreshCw,
  Search,
} from 'lucide-react';
import {
  splitOptionString,
  getOptionMatchDetail,
  fetchNewCarCatalog,
  NewCarCatalogData,
  findOfficialCatalogOption,
  stripOptionPriceText
} from '@/services/biddingOptionCatalog';
import { OptionItem } from '@/services/chaolmaService';
import { copyToClipboard } from '@/utils/clipboard';
import { EncarItem } from './ComparableEncarSection';

interface ExtraOptionPriceResult {
  badgeText: string;
  tooltip: string;
}

/**
 * 추가옵션 총 가격 판정 (5단계 출처 순서)
 * 1순위: targetOptions 합계 (price_man 또는 price/10000)
 * 2순위 (신규): historyOptionTotalMan (차얼마 옵션 총액, 상단 신차대비와 동일 출처)
 * 3순위: optionsTag 안의 [옵션총액] 정규식
 * 4순위: 카탈로그 공식가 합계 (targetCatalog, 없으면 compCatalog 순)
 * 5순위: 위 모두 불가 시 '가격 미확인'
 */
function calculateExtraOptionsTotalPrice(
  targetOptions?: OptionItem[],
  optionsTag?: string,
  targetCatalog?: NewCarCatalogData | null,
  compCatalog?: NewCarCatalogData | null,
  historyOptionTotalMan?: number
): ExtraOptionPriceResult {
  // 1순위: targetOptions 합계가 0보다 크면 그대로 쓴다 (기존 차량번호 경로 동작 유지)
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

  // 2순위 (신규): 1순위가 0이거나 비어 있고, historyOptionTotalMan이 0보다 크면 총 {historyOptionTotalMan}만을 표시한다.
  // 단, 옵션이 하나도 없을 때(targetOptions도 비어 있고 optionsTag도 비어 있거나 옵션 없음이면)는 이 순위를 쓰지 않고 가격 미확인으로 떨어진다.
  const hasOptions = (targetOptions && targetOptions.length > 0) || (optionsTag && optionsTag.trim() && !optionsTag.includes('옵션 없음'));
  if (hasOptions && typeof historyOptionTotalMan === 'number' && historyOptionTotalMan > 0) {
    return {
      badgeText: `총 ${historyOptionTotalMan.toLocaleString()}만`,
      tooltip: `[차얼마 옵션 총액 (상단 신차대비와 동일 출처)] 합계: ${historyOptionTotalMan.toLocaleString()}만원`
    };
  }

  // 3순위: optionsTag 안의 [옵션총액] 정규식 (기존 그대로)
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

    if (matchedLines.length > 0 && catalogSumMan > 0) {
      let tooltip = `[신차 카탈로그 공식가 합계: ${catalogSumMan.toLocaleString()}만]\n${matchedLines.join('\n')}`;
      if (unpricedOptions.length > 0) {
        tooltip += `\n\n(공식가 미확인 옵션: ${unpricedOptions.join(', ')})`;
      }
      return {
        badgeText: `총 ${catalogSumMan.toLocaleString()}만`,
        tooltip
      };
    }
  }

  // 5순위: 가격 미확인
  return {
    badgeText: '가격 미확인',
    tooltip: '가격 출처가 없습니다 (실제 신차가 미제공)'
  };
}

export interface CockpitSidebarProps {
  heydealerUrl: string;
  setHeydealerUrl: (url: string) => void;
  isAiEstimating: boolean;
  handleHeydealerAiEstimate: () => void;
  setIsQuickPasteOpen: (open: boolean) => void;
  carNumber: string;
  setCarNumber: (num: string) => void;
  isSearchingCar: boolean;
  handleLookupCarNumber: (num?: string) => void;
  aiEstimateStep?: string | null;
  searchStatus: { type: 'error' | 'warning' | 'info' | 'success'; message: string } | null;
  setSearchStatus: (st: { type: 'error' | 'warning' | 'info' | 'success'; message: string } | null) => void;
  manufacturer: string;
  setManufacturer: (m: string) => void;
  carName: string;
  setCarName: (name: string) => void;
  detailModel: string;
  setDetailModel: (m: string) => void;
  yearModel: number;
  setYearModel: (yr: number) => void;
  mileageKm: number;
  setMileageKm: (km: number) => void;
  optionsTag: string;
  targetOptions?: OptionItem[];
  unclassifiedBalance?: number;
  selectedEncar: EncarItem | null;
  expectedSellPrice: number;
  setExpectedSellPrice: (p: number) => void;
  outerRepairCount: number;
  setOuterRepairCount: (cnt: number) => void;
  auctionType: string;
  setAuctionType: (t: string) => void;
  targetMargin: number;
  setTargetMargin: (m: number) => void;
  userBid: number;
  setUserBid: (bid: number) => void;
  safeBidCeiling: number;
  actualMargin: number;
  actualPurchaseFee: number;
  repairCostTotal: number;
  memo: string;
  setMemo: (memo: string) => void;
  savedSuccess: boolean;
  handleSaveToLedger: () => void;
  targetCatalog?: NewCarCatalogData | null;
  historyOptionTotalMan?: number;
}

export const CockpitSidebar: React.FC<CockpitSidebarProps> = ({
  heydealerUrl,
  setHeydealerUrl,
  isAiEstimating,
  handleHeydealerAiEstimate,
  setIsQuickPasteOpen,
  carNumber,
  setCarNumber,
  isSearchingCar,
  handleLookupCarNumber,
  aiEstimateStep,
  searchStatus,
  setSearchStatus,
  manufacturer,
  setManufacturer,
  carName,
  setCarName,
  detailModel,
  setDetailModel,
  yearModel,
  setYearModel,
  mileageKm,
  setMileageKm,
  optionsTag,
  targetOptions = [],
  unclassifiedBalance = 0,
  selectedEncar,
  expectedSellPrice,
  setExpectedSellPrice,
  outerRepairCount,
  setOuterRepairCount,
  auctionType,
  setAuctionType,
  targetMargin,
  setTargetMargin,
  userBid,
  setUserBid,
  safeBidCeiling,
  actualMargin,
  actualPurchaseFee,
  repairCostTotal,
  memo,
  setMemo,
  savedSuccess,
  handleSaveToLedger,
  targetCatalog: propTargetCatalog,
  historyOptionTotalMan = 0,
}) => {
  const [internalCatalog, setInternalCatalog] = useState<NewCarCatalogData | null>(null);
  const [compCatalog, setCompCatalog] = useState<NewCarCatalogData | null>(null);
  const targetCatalog = propTargetCatalog !== undefined && propTargetCatalog !== null ? propTargetCatalog : internalCatalog;

  useEffect(() => {
    let isMounted = true;
    if (carName) {
      fetchNewCarCatalog(carName, yearModel ? String(yearModel) : undefined).then((cat) => {
        if (isMounted) setInternalCatalog(cat);
      });
    } else {
      setInternalCatalog(null);
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

  return (
      <div className="w-full lg:w-[320px] xl:w-[340px] shrink-0 space-y-4 lg:sticky lg:top-4 self-start max-h-[calc(100vh-2rem)] overflow-y-auto scrollbar-thin scrollbar-thumb-zinc-700 pr-1">
        <div className="bg-[#0e0f13] border border-[#262833] rounded-xl p-4 shadow-xl space-y-4">
          
          {/* Logo */}
          <div className="flex items-center justify-between">
            <div>
              <div className="text-base font-black text-blue-400 font-serif-display tracking-wider">
                J-PRO
              </div>
              <div className="text-[11px] text-zinc-300 uppercase tracking-wider font-bold">
                AUTO VALUATION INTELLIGENCE
              </div>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold border border-blue-500/30">
              비딩 콕핏 v2
            </span>
          </div>

          {/* URL Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-zinc-200 block">매물 주소</label>
            <input
              type="text"
              placeholder="매물 URL 또는 ID 입력"
              value={heydealerUrl}
              onChange={(e) => setHeydealerUrl(e.target.value)}
              className="w-full bg-[#14151b] border border-[#2c2f3d] rounded-lg px-3 py-2 text-xs sm:text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 font-mono"
            />
            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                type="button"
                onClick={handleHeydealerAiEstimate}
                disabled={isAiEstimating}
                className="py-2 rounded-lg bg-gradient-to-r from-amber-600/40 to-[#cc9166]/50 hover:from-amber-600/60 hover:to-[#cc9166]/70 text-xs sm:text-sm font-bold text-white border border-[#cc9166]/60 transition cursor-pointer flex items-center justify-center gap-1.5 shadow-sm"
              >
                {isAiEstimating ? <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-300" /> : <Sparkles className="w-3.5 h-3.5 text-amber-300" />}
                <span>{isAiEstimating ? '산출 중...' : 'AI 견적 산출'}</span>
              </button>
              <button
                type="button"
                onClick={() => setIsQuickPasteOpen(true)}
                className="py-2 rounded-lg bg-[#1a1c24] hover:bg-[#252836] text-xs sm:text-sm font-bold text-emerald-300 hover:text-emerald-200 border border-emerald-500/40 transition cursor-pointer flex items-center justify-center gap-1"
                title="헤이딜러/카카오톡 텍스트 복사 후 1초 자동 분석"
              >
                <span>📋 텍스트 분석</span>
              </button>
            </div>
          </div>

          {/* Car Number Search (차얼마 & 엔카 통합 조회) */}
          <div className="space-y-1.5 pt-1">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-zinc-200 block">차량번호 (필수)</label>
              <span className="text-[11px] text-zinc-400">Enter로 조회</span>
            </div>
            <div className="flex gap-1.5">
              <input
                type="text"
                value={carNumber}
                onChange={(e) => setCarNumber(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleLookupCarNumber();
                }}
                placeholder="예: 37다1840, 240어8733"
                className="flex-1 bg-[#14151b] border border-[#2c2f3d] rounded-lg px-3 py-2 text-sm font-bold text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 font-mono tracking-wider"
              />
              <button
                type="button"
                onClick={() => handleLookupCarNumber()}
                disabled={isSearchingCar}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs sm:text-sm font-bold text-white transition shadow-sm cursor-pointer flex items-center gap-1.5 shrink-0"
              >
                {isSearchingCar ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                <span>{isSearchingCar ? '조회중' : '조회'}</span>
              </button>
            </div>


            {aiEstimateStep && (
              <div className="text-xs text-amber-300 bg-amber-500/15 border border-amber-500/30 px-2.5 py-1.5 rounded-lg animate-pulse font-medium">
                {aiEstimateStep}
              </div>
            )}
            {searchStatus && (
              <div
                className={`text-xs px-3 py-2 rounded-lg border leading-relaxed flex items-start gap-1.5 shadow-sm font-medium ${
                  searchStatus.type === 'error'
                    ? 'text-rose-200 bg-rose-950/60 border-rose-500/50'
                    : searchStatus.type === 'warning'
                    ? 'text-amber-200 bg-amber-950/60 border-amber-500/50'
                    : searchStatus.type === 'info'
                    ? 'text-blue-200 bg-blue-950/60 border-blue-500/50'
                    : 'text-emerald-200 bg-emerald-950/60 border-emerald-500/50'
                }`}
              >
                <span>{searchStatus.message}</span>
              </div>
            )}
          </div>

          {/* Form Fields */}
          <div className="space-y-3 pt-2 border-t border-[#262833] text-xs">
            
            {/* Manufacturer */}
            <div>
              <label className="text-[11px] font-medium text-zinc-400 block mb-1">제조사/브랜드</label>
              <select
                value={manufacturer}
                onChange={(e) => setManufacturer(e.target.value)}
                className="w-full bg-[#14151b] border border-[#2c2f3d] rounded-lg px-3 py-1.5 text-zinc-100 font-semibold text-xs sm:text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="기아">기아</option>
                <option value="현대">현대</option>
                <option value="제네시스">제네시스</option>
                <option value="르노코리아">르노코리아</option>
                <option value="KG모빌리티">KG모빌리티</option>
                <option value="쉐보레">쉐보레</option>
                <option value="BMW">BMW / 수입</option>
                {!['기아', '현대', '제네시스', '르노코리아', 'KG모빌리티', '쉐보레', 'BMW'].includes(manufacturer) && manufacturer && (
                  <option value={manufacturer}>{manufacturer}</option>
                )}
              </select>
            </div>

            {/* Car Name */}
            <div>
              <label className="text-[11px] font-medium text-zinc-400 block mb-1">차량명</label>
              <input
                type="text"
                list="cockpit-car-names"
                value={carName}
                onChange={(e) => setCarName(e.target.value)}
                placeholder="예: 올 뉴 카니발, 더 뉴 팰리세이드"
                className="w-full bg-[#14151b] border border-[#2c2f3d] rounded-lg px-3 py-1.5 text-white font-bold text-xs sm:text-sm focus:outline-none focus:border-blue-500"
              />
              <datalist id="cockpit-car-names">
                <option value="더 뉴 팰리세이드" />
                <option value="팰리세이드" />
                <option value="올 뉴 카니발" />
                <option value="더 뉴 카니발" />
                <option value="카니발 4세대" />
                <option value="쏘나타 (DN8)" />
                <option value="그랜저 IG" />
                <option value="캐스퍼" />
                <option value="K5 3세대" />
                <option value="제네시스 G80" />
                <option value="XM3" />
                <option value="토레스" />
              </datalist>
            </div>

            {/* Detail Model */}
            <div>
              <label className="text-[11px] font-medium text-zinc-400 block mb-1">세부모델</label>
              <input
                type="text"
                list="cockpit-sub-models"
                value={detailModel}
                onChange={(e) => setDetailModel(e.target.value)}
                placeholder="세부모델명 입력"
                className="w-full bg-[#14151b] border border-[#2c2f3d] rounded-lg px-3 py-1.5 text-zinc-100 font-medium text-xs sm:text-sm focus:outline-none focus:border-blue-500"
              />
              <datalist id="cockpit-sub-models">
                <option value="디젤 2.2 4WD 프레스티지 (7인승)" />
                <option value="가솔린 3.8 2WD 캘리그래피" />
                <option value="럭셔리" />
                <option value="프레스티지" />
                <option value="디젤 9인승 프레스티지" />
                <option value="1.6 가솔린 스마트" />
                <option value="1.0 터보 인스퍼레이션" />
                <option value="시그니처" />
                <option value="스마트" />
                <option value="모던" />
                <option value="인스퍼레이션" />
                <option value="노블레스" />
              </datalist>
            </div>

            {/* Year */}
            <div className="flex justify-between items-center bg-[#14151b] px-3 py-2 rounded-lg border border-[#232634]">
              <span className="text-[11px] font-medium text-zinc-400">연식 (0=전체)</span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setYearModel(Math.max(0, yearModel - 1))}
                  className="w-6 h-6 rounded bg-[#232634] hover:bg-[#323646] text-white font-bold transition cursor-pointer flex items-center justify-center text-xs"
                >-</button>
                <input
                  type="number"
                  value={yearModel === 0 ? '' : yearModel}
                  onChange={(e) => setYearModel(Number(e.target.value) || 0)}
                  placeholder="0"
                  className="w-12 text-center bg-[#1e212b] border border-[#2a2d3d] focus:border-sky-400 rounded px-1 py-0.5 font-black text-white text-sm font-mono focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => setYearModel(yearModel + 1)}
                  className="w-6 h-6 rounded bg-[#232634] hover:bg-[#323646] text-white font-bold transition cursor-pointer flex items-center justify-center text-xs"
                >+</button>
              </div>
            </div>

            {/* Mileage */}
            <div className="flex justify-between items-center bg-[#14151b] px-3 py-2 rounded-lg border border-[#232634]">
              <span className="text-[11px] font-medium text-zinc-400">
                주행거리 <span className="text-amber-400 font-bold">(필수, km)</span>
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setMileageKm(Math.max(0, mileageKm - 1000))}
                  className="w-6 h-6 rounded bg-[#232634] hover:bg-[#323646] text-white font-bold transition cursor-pointer flex items-center justify-center text-xs"
                >-</button>
                <input
                  type="text"
                  value={mileageKm === 0 ? '' : mileageKm.toLocaleString()}
                  onChange={(e) => {
                    const raw = e.target.value.replace(/[^\d]/g, '');
                    setMileageKm(raw ? parseInt(raw, 10) : 0);
                  }}
                  placeholder="0"
                  className="w-24 text-center bg-[#1e212b] border border-[#2a2d3d] focus:border-sky-400 rounded px-1.5 py-0.5 font-black text-white text-xs sm:text-sm font-mono focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => setMileageKm(mileageKm + 1000)}
                  className="w-6 h-6 rounded bg-[#232634] hover:bg-[#323646] text-white font-bold transition cursor-pointer flex items-center justify-center text-xs"
                >+</button>
              </div>
            </div>



            {/* Options */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between gap-1.5">
                {/* 1. 왼쪽: 추가 옵션 라벨 + 신차 옵션 N개 배지 */}
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-[11px] font-medium text-zinc-400">추가 옵션</span>
                  {((targetOptions && targetOptions.length > 0) || (optionsTag && optionsTag.trim() && !optionsTag.includes('옵션 없음'))) && (() => {
                    const optCount = targetOptions && targetOptions.length > 0 ? targetOptions.length : splitOptionString(optionsTag).length;
                    return (
                      <span className="inline-flex items-center text-[10px] px-1.5 py-1 rounded bg-blue-500/15 text-blue-300 font-bold border border-blue-500/30">
                        신차 옵션 {optCount}개
                      </span>
                    );
                  })()}
                </div>

                {/* 2. 가운데: 추가옵션 총 가격 배지 (1곳으로 일원화, flex flex-1 items-center justify-center) */}
                {((targetOptions && targetOptions.length > 0) || (optionsTag && optionsTag.trim() && !optionsTag.includes('옵션 없음'))) && (() => {
                  const priceInfo = calculateExtraOptionsTotalPrice(targetOptions, optionsTag, targetCatalog, compCatalog, historyOptionTotalMan);
                  return (
                    <div className="flex flex-1 items-center justify-center min-w-0">
                      <span
                        title={priceInfo.tooltip}
                        className="inline-flex items-center text-[10px] px-1.5 py-1 rounded bg-amber-500/20 text-amber-200 font-bold border border-amber-500/40 cursor-help truncate max-w-full"
                      >
                        {priceInfo.badgeText}
                      </span>
                    </div>
                  );
                })()}

                {/* 3. 오른쪽: 우세 또는 조회차량 순정 배지 */}
                <div className="flex items-center shrink-0">
                  {(() => {
                    if (!selectedEncar?.optionsText || !optionsTag || !optionsTag.trim()) {
                      return <span className="inline-flex items-center text-[10px] px-1.5 py-1 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">조회차량 순정</span>;
                    }
                    const compOpts = splitOptionString(selectedEncar.optionsText);
                    const tgtOpts = splitOptionString(optionsTag);
                    if (compOpts.length === 0 || tgtOpts.length === 0) {
                      return <span className="inline-flex items-center text-[10px] px-1.5 py-1 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">조회차량 순정</span>;
                    }
                    const matchDetails = tgtOpts.map(to => getOptionMatchDetail(to, compOpts, 'target_vs_comp', targetCatalog, compCatalog));
                    const winCount = matchDetails.filter(d => !d.isMatched).length;
                    const exactCount = matchDetails.filter(d => d.confidence === 'exact').length;
                    const fuzzyCount = matchDetails.filter(d => d.confidence === 'fuzzy').length;

                    if (winCount > 0) {
                      return (
                        <span
                          title={`비교 매물(${selectedEncar.carName}) 대비 내 차 우세/고유 옵션: ${winCount}개\n공식 일치: ${exactCount}개 / 추정 매칭: ${fuzzyCount}개`}
                          className="inline-flex items-center text-[10px] px-1.5 py-1 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500 cursor-help"
                        >
                          🟢 우세 {winCount}개
                        </span>
                      );
                    }
                    return (
                      <span
                        title={`비교 매물(${selectedEncar.carName})과 핵심 옵션 일치 (공식 일치: ${exactCount}개, 추정: ${fuzzyCount}개)`}
                        className="inline-flex items-center text-[10px] px-1.5 py-1 rounded bg-sky-500/20 text-sky-300 font-bold border border-sky-400/50 cursor-help"
                      >
                        🔵 공통 사양
                      </span>
                    );
                  })()}
                </div>
              </div>

              {/* 🎨 옵션 색상 범례 안내 (비교차 선택 시 자동 전환) */}
              {optionsTag && optionsTag.trim().length > 0 && (
                <div className="flex items-center gap-2 text-[10px] text-zinc-400 bg-zinc-900/60 px-2 py-0.5 rounded border border-zinc-800">
                  <span className="text-zinc-500 font-medium">범례:</span>
                  {selectedEncar?.optionsText ? (
                    <>
                      <span className="flex items-center gap-1 text-emerald-400 font-semibold" title="비교차에는 없고 내 차에만 있는 고유/우세 옵션">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>내차우세(+)
                      </span>
                      <span className="flex items-center gap-1 text-amber-400 font-semibold" title="공식 명칭 차이로 스펙 유사로 추정 매칭된 옵션">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>추정(~)
                      </span>
                      <span className="flex items-center gap-1 text-sky-400 font-semibold" title="비교차와 내 차 모두 동일하게 장착된 공통 옵션">
                        <span className="w-1.5 h-1.5 rounded-full bg-sky-400"></span>공통(✓)
                      </span>
                    </>
                  ) : (
                    <span className="text-sky-300 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-sky-400"></span>장착 순정 옵션 (비교 매물 클릭 시 우세 대조)
                    </span>
                  )}
                </div>
              )}

              {/* Parsed Option Chips (백엔드 일원화 OptionItem 배열 직접 렌더링 + 미분류 잔액 뱃지) */}
              {(targetOptions && targetOptions.length > 0) || (optionsTag && optionsTag.trim().length > 0) ? (
                <div className="flex flex-wrap gap-1.5 py-1">
                  {(() => {
                    const compOpts = (selectedEncar?.options && selectedEncar.options.length > 0)
                      ? selectedEncar.options.map((o: OptionItem) => o.name)
                      : splitOptionString(selectedEncar?.optionsText || '');
                    const hasComp = compOpts.length > 0;

                    if (targetOptions && targetOptions.length > 0) {
                      return (
                        <>
                          {targetOptions.map((opt, idx) => {
                            const pMan = opt.price_man || Math.round(opt.price / 10000);
                            const displayName = pMan > 0 ? `${opt.name}(${pMan}만)` : opt.name;
                            const detail = getOptionMatchDetail(opt.name, compOpts, 'target_vs_comp', targetCatalog, compCatalog);

                            if (hasComp && !detail.isMatched) {
                              return (
                                <span
                                  key={idx}
                                  title={detail.tooltipText || opt.desc || `${opt.name} (${pMan}만)`}
                                  className="px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500 text-emerald-400 font-bold text-[11px] flex items-center gap-1 shadow-[0_0_6px_rgba(34,197,94,0.25)] cursor-help hover:brightness-110 transition"
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
                                  className="px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/60 text-amber-300 font-semibold text-[11px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
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
                                className="px-2 py-0.5 rounded bg-sky-500/20 border border-sky-400/60 text-sky-300 font-semibold text-[11px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                              >
                                <span className="text-sky-400 text-[10px]">{hasComp ? '✓' : '•'}</span>
                                <span>{displayName}</span>
                              </span>
                            );
                          })}

                          {unclassifiedBalance > 0 && (
                            <span
                              title={`카탈로그 옵션가 합계와 출고가 차액 간의 미분류 잔액입니다. 특정 옵션에 임의 배정되지 않은 순수 잔액입니다.`}
                              className="px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/50 text-amber-300 font-medium text-[11px] flex items-center gap-1 cursor-help font-mono"
                            >
                              <span>ℹ️ 미분류 잔액 ({unclassifiedBalance}만)</span>
                            </span>
                          )}
                        </>
                      );
                    }

                    const tgtOpts = splitOptionString(optionsTag);
                    if (tgtOpts.length === 0) {
                      return (
                        <div className="text-[11px] text-zinc-500 py-1 italic">
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
                            className="px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500 text-emerald-400 font-bold text-[11px] flex items-center gap-1 shadow-[0_0_6px_rgba(34,197,94,0.25)] cursor-help hover:brightness-110 transition"
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
                            className="px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/60 text-amber-300 font-semibold text-[11px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
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
                          className="px-2 py-0.5 rounded bg-sky-500/20 border border-sky-400/60 text-sky-300 font-semibold text-[11px] flex items-center gap-1 cursor-help hover:brightness-110 transition"
                        >
                          <span className="text-sky-400 text-[10px]">{hasComp ? '✓' : '•'}</span>
                          <span>{opt}</span>
                        </span>
                      );
                    });
                  })()}
                </div>
              ) : (
                <div className="text-[11px] text-zinc-500 py-1 italic">
                  추가 옵션 없음 (기본 출고 사양)
                </div>
              )}
            </div>

            {/* Expected Sell Price */}
            <div className="flex justify-between items-center bg-[#14151b] px-3 py-2 rounded-lg border border-[#232634]">
              <span className="text-[11px] font-medium text-zinc-400">예상 소매가 (만원)</span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setExpectedSellPrice(Math.max(0, expectedSellPrice - 10))}
                  className="w-6 h-6 rounded bg-[#232634] hover:bg-[#323646] text-white font-bold transition cursor-pointer flex items-center justify-center text-xs"
                >-</button>
                <input
                  type="number"
                  value={expectedSellPrice === 0 ? '' : expectedSellPrice}
                  onChange={(e) => setExpectedSellPrice(Number(e.target.value) || 0)}
                  placeholder="0"
                  className="w-16 text-center bg-[#1e212b] border border-[#2a2d3d] focus:border-sky-400 rounded px-1 py-0.5 font-black text-sky-400 text-sm sm:text-base font-mono focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => setExpectedSellPrice(expectedSellPrice + 10)}
                  className="w-6 h-6 rounded bg-[#232634] hover:bg-[#323646] text-white font-bold transition cursor-pointer flex items-center justify-center text-xs"
                >+</button>
              </div>
            </div>

            {/* Outer Repairs */}
            <div className="flex justify-between items-center bg-[#14151b] px-3 py-2 rounded-lg border border-[#232634]">
              <span className="text-[11px] font-medium text-zinc-400">외판 수리 갯수</span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setOuterRepairCount(Math.max(0, outerRepairCount - 1))}
                  className="w-6 h-6 rounded bg-[#232634] hover:bg-[#323646] text-white font-bold transition cursor-pointer flex items-center justify-center text-xs"
                >-</button>
                <input
                  type="number"
                  value={outerRepairCount}
                  onChange={(e) => setOuterRepairCount(Math.max(0, Number(e.target.value) || 0))}
                  min={0}
                  className="w-12 text-center bg-[#1e212b] border border-[#2a2d3d] focus:border-sky-400 rounded px-1 py-0.5 font-black text-white text-sm font-mono focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => setOuterRepairCount(outerRepairCount + 1)}
                  className="w-6 h-6 rounded bg-[#232634] hover:bg-[#323646] text-white font-bold transition cursor-pointer flex items-center justify-center text-xs"
                >+</button>
              </div>
            </div>

            {/* Auction Type */}
            <div>
              <label className="text-[11px] font-medium text-zinc-400 block mb-1">매입 경로</label>
              <select
                value={auctionType}
                onChange={(e) => setAuctionType(e.target.value)}
                className="w-full bg-[#14151b] border border-[#2c2f3d] rounded-lg px-3 py-1.5 text-zinc-200 font-semibold text-xs sm:text-sm"
              >
                <option value="셀프(기본)">셀프(기본)</option>
                <option value="제로">제로</option>
              </select>
            </div>

            {/* Target Margin */}
            <div className="flex justify-between items-center bg-[#14151b] px-3 py-2 rounded-lg border border-[#232634]">
              <span className="text-[11px] font-medium text-zinc-400">목표 마진 (만원)</span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setTargetMargin(Math.max(0, targetMargin - 10))}
                  className="w-6 h-6 rounded bg-[#232634] hover:bg-[#323646] text-white font-bold transition cursor-pointer flex items-center justify-center text-xs"
                >-</button>
                <input
                  type="number"
                  value={targetMargin === 0 ? '' : targetMargin}
                  onChange={(e) => setTargetMargin(Number(e.target.value) || 0)}
                  placeholder="0"
                  className="w-14 text-center bg-[#1e212b] border border-[#2a2d3d] focus:border-emerald-400 rounded px-1 py-0.5 font-black text-emerald-400 text-sm sm:text-base font-mono focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => setTargetMargin(targetMargin + 10)}
                  className="w-6 h-6 rounded bg-[#232634] hover:bg-[#323646] text-white font-bold transition cursor-pointer flex items-center justify-center text-xs"
                >+</button>
              </div>
            </div>



            {/* 🎯 가로 1행: [입찰가 수정 입력창] + [📋 복사 버튼] */}
            {expectedSellPrice > 0 && (
              <div className="space-y-2.5 pt-1">
                <div className="flex items-center gap-1.5">
                  <div className="flex-1">
                    <label className="text-[11px] font-medium text-zinc-400 block mb-1">최종 입찰가 (만원)</label>
                    <input
                      type="number"
                      value={userBid}
                      onChange={(e) => setUserBid(Number(e.target.value) || 0)}
                      className="w-full bg-[#14151b] border border-emerald-500/60 rounded-lg px-3 py-2 text-emerald-400 font-black text-lg focus:outline-none focus:border-emerald-400 font-mono"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={async () => {
                      const success = await copyToClipboard(String(userBid));
                      if (success) {
                        setSearchStatus({
                          type: 'success',
                          message: `📋 입찰가 ${userBid.toLocaleString()}만원 클립보드 복사 완료!`
                        });
                      } else {
                        setSearchStatus({
                          type: 'error',
                          message: `❌ 클립보드 복사 실패: 브라우저 권한을 확인해주세요.`
                        });
                      }
                      setTimeout(() => setSearchStatus(null), 2500);
                    }}
                    className="self-end px-3.5 py-2.5 rounded-lg bg-[#1f222e] hover:bg-[#2c3040] text-zinc-200 hover:text-white border border-[#35394a] text-xs sm:text-sm font-bold transition whitespace-nowrap cursor-pointer flex items-center gap-1"
                    title="클립보드에 복사"
                  >
                    <span>📋 복사</span>
                  </button>
                </div>

                {/* 🏷️ 가로 2행: 권장매입가 및 실시간 마진 노출 (녹색 창 클릭 시 장부 즉시 저장) */}
                <div 
                  onClick={handleSaveToLedger}
                  className="bg-emerald-500/15 hover:bg-emerald-500/20 border border-emerald-500/40 hover:border-emerald-400/70 p-3.5 rounded-xl space-y-2 transition cursor-pointer shadow-md group"
                  title="클릭 시 내 장부에 즉시 저장됩니다"
                >
                  <div className="flex justify-between items-baseline">
                    <div className="text-xs sm:text-sm font-bold text-zinc-200">
                      {userBid !== safeBidCeiling ? (
                        <span>최종 매입가 <small className="text-zinc-400 font-normal">(권장 {safeBidCeiling.toLocaleString()}만)</small></span>
                      ) : (
                        <span className="text-zinc-200">권장 매입가</span>
                      )}
                    </div>
                    <div className="text-2xl sm:text-3xl font-black text-emerald-400 tracking-tight font-mono">
                      {userBid.toLocaleString()} <span className="text-xs font-bold text-zinc-300">만원</span>
                    </div>
                  </div>

                  <div className="flex justify-between items-center pt-2 border-t border-dashed border-emerald-500/30 text-xs sm:text-sm">
                    <span className="text-zinc-300 font-semibold">예상마진</span>
                    <span className="text-blue-400 font-black text-base font-mono">+{Math.round(actualMargin).toLocaleString()}만원</span>
                  </div>

                  <div className="flex justify-between items-center text-[11px] text-zinc-400 pt-0.5">
                    <span>수수료: {actualPurchaseFee}만 · 수리: {repairCostTotal}만 · 잡비: 15만</span>
                    <span className="text-emerald-300 font-bold group-hover:underline">💾 클릭 저장</span>
                  </div>
                </div>
              </div>
            )}

            {/* Memo */}
            <div>
              <label className="text-[11px] font-medium text-zinc-400 block mb-1">특이사항 / 메모</label>
              <input
                type="text"
                placeholder="특이사항 메모 (보조키, 틴팅, 블박 등)"
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
                className="w-full bg-[#14151b] border border-[#2c2f3d] rounded-lg px-3 py-1.5 text-zinc-200 text-xs sm:text-sm font-medium focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* Save to Ledger Button */}
            <button
              type="button"
              onClick={handleSaveToLedger}
              className={`w-full py-3 rounded-lg text-xs sm:text-sm font-bold transition flex items-center justify-center gap-1.5 shadow-md cursor-pointer ${
                savedSuccess
                  ? 'bg-emerald-600 text-white'
                  : 'bg-[#1f222e] hover:bg-[#2c3040] text-white border border-[#35394a]'
              }`}
            >
              {savedSuccess ? '✓ 저장 완료!' : '💾 내 장부 및 구글시트에 저장'}
            </button>

          </div>

        </div>
      </div>
  );
};
