import React from 'react';
import {
  Sparkles,
  RefreshCw,
  Search,
} from 'lucide-react';
import { isOptionMatched, splitOptionString, getOptionMatchDetail } from '@/services/biddingOptionCatalog';
import { EncarItem } from './ComparableEncarSection';

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
}) => {
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
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-medium text-zinc-400">추가 옵션</span>
                  {optionsTag && optionsTag.trim() && !optionsTag.includes('옵션 없음') && (
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-500/15 text-blue-300 font-semibold border border-blue-500/30 font-mono">
                      신차 옵션 {optionsTag.replace(/\[[^\]]*\]/g, '').split(/[·,+,\/]/).filter(s => s.trim().length > 0 && !s.includes('옵션 없음') && !s.includes('기본')).length}개
                    </span>
                  )}
                </div>
                {/* 🌟 비교차 선택 시에만 우세/공통 뱃지 연동, 미선택 시에는 조회차량 순정 표시 */}
                {(() => {
                  if (!selectedEncar?.optionsText || !optionsTag || !optionsTag.trim()) {
                    return <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-medium border border-emerald-500/30">조회차량 순정</span>;
                  }
                  const compOpts = splitOptionString(selectedEncar.optionsText);
                  const tgtOpts = splitOptionString(optionsTag);
                  if (compOpts.length === 0 || tgtOpts.length === 0) {
                    return <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-medium border border-emerald-500/30">조회차량 순정</span>;
                  }
                  const winCount = tgtOpts.filter(to => !compOpts.some(co => isOptionMatched(co, to))).length;
                  if (winCount > 0) {
                    return (
                      <span
                        title={`비교 매물(${selectedEncar.carName}) 대비 내 차에만 있는 우세 옵션: ${winCount}개`}
                        className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500 cursor-help"
                      >
                        🟢 우세 {winCount}개
                      </span>
                    );
                  }
                  return (
                    <span
                      title={`비교 매물(${selectedEncar.carName})과 핵심 옵션 동일 장착 (시세 동등)`}
                      className="text-[10px] px-1.5 py-0.2 rounded bg-sky-500/20 text-sky-300 font-bold border border-sky-400/50 cursor-help"
                    >
                      🔵 공통 사양
                    </span>
                  );
                })()}
              </div>

              {/* Parsed Option Chips (양방향 분해 매칭 + 마우스 호버 상세 툴팁) */}
              {optionsTag && optionsTag.trim().length > 0 ? (
                <div className="flex flex-wrap gap-1.5 py-1">
                  {(() => {
                    const compOpts = splitOptionString(selectedEncar?.optionsText || '');
                    const hasComp = compOpts.length > 0;
                    const tgtOpts = splitOptionString(optionsTag);

                    if (tgtOpts.length === 0) {
                      return (
                        <div className="text-[11px] text-zinc-500 py-1 italic">
                          추가 옵션 없음 (기본 출고 사양)
                        </div>
                      );
                    }

                    return tgtOpts.map((opt, idx) => {
                      const detail = getOptionMatchDetail(opt, compOpts, 'target_vs_comp');

                      if (hasComp && !detail.isMatched) {
                        // 타겟 우세 옵션: 녹색 강조 (+ opt)
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

                      // 공통 옵션 또는 기본: 블루/하늘색 (✓ opt)
                      return (
                        <span
                          key={idx}
                          title={hasComp ? detail.tooltipText : `[${opt}]\n조회 차량의 장착 순정 옵션입니다.`}
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
                    onClick={() => {
                      navigator.clipboard.writeText(String(userBid));
                      setSearchStatus({
                        type: 'success',
                        message: `📋 입찰가 ${userBid.toLocaleString()}만원 클립보드 복사 완료!`
                      });
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
