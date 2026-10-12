import React from 'react';
import { BiddingCockpitTabProps } from './BiddingCockpit/types';
import { useBiddingCockpit } from './BiddingCockpit/hooks/useBiddingCockpit';
import { CockpitSidebar } from './BiddingCockpit/Sections/CockpitSidebar';
import { ValuationSummarySection } from './BiddingCockpit/Sections/ValuationSummarySection';
import { ComparableEncarSection } from './BiddingCockpit/Sections/ComparableEncarSection';
import { ScatterPlotSection } from './BiddingCockpit/Sections/ScatterPlotSection';
import { HeydealerBidsSection } from './BiddingCockpit/Sections/HeydealerBidsSection';
import { CarDetailModal } from '@/components/CarDetailModal';
import { CarHistoryDetailModal } from '@/components/CarHistoryDetailModal';

// 외부 호환성을 위한 타입 Re-export
export type {
  BiddingCockpitTabProps,
  EncarItem,
  EncarSoldItem,
  EncarSoldStats,
  HeydealerBidItem,
} from './BiddingCockpit/types';

export const BiddingCockpitTab: React.FC<BiddingCockpitTabProps> = (props) => {
  const cockpit = useBiddingCockpit(props);

  return (
    <div className="flex flex-col lg:flex-row gap-5 items-start w-full">
      {/* ========================================================
          [좌측 고정 사이드바] 헤이딜러 URL/차량번호 입력 & 파라미터 (고대비 & 확대)
          ======================================================== */}
      <CockpitSidebar
        heydealerUrl={cockpit.heydealerUrl}
        setHeydealerUrl={cockpit.setHeydealerUrl}
        isAiEstimating={cockpit.isAiEstimating}
        handleHeydealerAiEstimate={cockpit.handleHeydealerAiEstimate}
        setIsQuickPasteOpen={cockpit.setIsQuickPasteOpen}
        carNumber={cockpit.carNumber}
        setCarNumber={cockpit.setCarNumber}
        isSearchingCar={cockpit.isSearchingCar}
        handleLookupCarNumber={cockpit.handleLookupCarNumber}
        aiEstimateStep={cockpit.aiEstimateStep}
        searchStatus={cockpit.searchStatus}
        setSearchStatus={cockpit.setSearchStatus}
        manufacturer={cockpit.manufacturer}
        setManufacturer={cockpit.setManufacturer}
        carName={cockpit.carName}
        setCarName={cockpit.setCarName}
        detailModel={cockpit.detailModel}
        setDetailModel={cockpit.setDetailModel}
        yearModel={cockpit.yearModel}
        setYearModel={cockpit.setYearModel}
        mileageKm={cockpit.mileageKm}
        setMileageKm={cockpit.setMileageKm}
        optionsTag={cockpit.optionsTag}
        selectedEncar={cockpit.selectedEncar}
        expectedSellPrice={cockpit.expectedSellPrice}
        setExpectedSellPrice={cockpit.setExpectedSellPrice}
        outerRepairCount={cockpit.outerRepairCount}
        setOuterRepairCount={cockpit.setOuterRepairCount}
        auctionType={cockpit.auctionType}
        setAuctionType={cockpit.setAuctionType}
        targetMargin={cockpit.targetMargin}
        setTargetMargin={cockpit.setTargetMargin}
        userBid={cockpit.userBid}
        setUserBid={cockpit.setUserBid}
        safeBidCeiling={cockpit.safeBidCeiling}
        actualMargin={cockpit.actualMargin}
        actualPurchaseFee={cockpit.actualPurchaseFee}
        repairCostTotal={cockpit.repairCostTotal}
        memo={cockpit.memo}
        setMemo={cockpit.setMemo}
        savedSuccess={cockpit.savedSuccess}
        handleSaveToLedger={cockpit.handleSaveToLedger}
      />

      {/* ========================================================
          [우측 메인 워크플로우 4대 시퀀스]
          1. 자사 팔린매물 및 닷컴 동급 팔린매물 & 핵심 결론
          2. 동급매물 (엔카 시세 & 2D 상태도)
          3. 가격-주행거리 산점도
          4. 헤딜 낙찰시세
          ======================================================== */}
      <div className="flex-1 min-w-0 space-y-4">

        {/* ========================================================
            [1단계 & 핵심 결론] AI 시세 밸류에이션 & 실시간 회전율 통합 제어 센터
            ======================================================== */}
        <ValuationSummarySection
          carName={cockpit.carName}
          carNumber={cockpit.carNumber}
          detailModel={cockpit.detailModel}
          manufacturer={cockpit.manufacturer}
          yearModel={cockpit.yearModel}
          mileageKm={cockpit.mileageKm}
          expectedSellPrice={cockpit.expectedSellPrice}
          effectiveSellPrice={cockpit.effectiveSellPrice}
          targetMargin={cockpit.targetMargin}
          repairCostTotal={cockpit.repairCostTotal}
          purchaseFeeCalculated={cockpit.purchaseFeeCalculated}
          safeBidCeiling={cockpit.safeBidCeiling}
          optionsTag={cockpit.optionsTag}
          outerRepairCount={cockpit.outerRepairCount}
          biddingVerdict={cockpit.biddingVerdict}
          isEncarLoading={cockpit.isEncarLoading}
          isExcelUploading={cockpit.isExcelUploading}
          encarSourceUrl={cockpit.encarSourceUrl}
          autoplusStats={cockpit.autoplusStats}
          currentAssessment={cockpit.currentAssessment}
          targetCarHistory={cockpit.targetCarHistory}
          liveMarketStats={cockpit.liveMarketStats}
          liveEncarSoldStats={cockpit.liveEncarSoldStats}
          encarStats={cockpit.encarStats}
          encarValuation={cockpit.encarValuation}
          encarYearStats={cockpit.encarYearStats}
          encarSoldList={cockpit.encarSoldList}
          matchedAutoplusList={cockpit.matchedAutoplusList}
          encarList={cockpit.encarList}
          soldTabMode={cockpit.soldTabMode}
          setSoldTabMode={cockpit.setSoldTabMode}
          showTrimColumn={cockpit.showTrimColumn}
          onRescanEncar={() => cockpit.fetchEncarComparable({
            url: cockpit.encarSourceUrl,
            carName: cockpit.carName,
            detailModel: cockpit.detailModel,
            manufacturer: cockpit.manufacturer,
            year: cockpit.yearModel,
            mileage: cockpit.mileageKm,
          })}
          onUploadExcel={cockpit.handleUploadAutoplusExcel}
          onOpenHistoryModal={() => cockpit.setShowCarHistoryModal(true)}
        />

        {/* ========================================================
            [2단계] 시장 비교 매물 영역 (엔카 실시간 시세 리스트 & 비교 매물 2D 상태도)
            ======================================================== */}
        <ComparableEncarSection
          encarList={cockpit.encarList}
          encarTotalModelCount={cockpit.encarTotalModelCount}
          encarFilteredCount={cockpit.encarFilteredCount}
          encarFilterStats={cockpit.encarFilterStats}
          selectedEncarId={cockpit.selectedEncarId}
          selectedEncar={cockpit.selectedEncar}
          isEncarLoading={cockpit.isEncarLoading}
          isInspectionLoading={cockpit.isInspectionLoading}
          encarErrorMessage={cockpit.encarErrorMessage}
          encarSourceUrl={cockpit.encarSourceUrl}
          carName={cockpit.carName}
          carNumber={cockpit.carNumber}
          detailModel={cockpit.detailModel}
          yearModel={cockpit.yearModel}
          mileageKm={cockpit.mileageKm}
          optionsTag={cockpit.optionsTag}
          showTrimColumn={cockpit.showTrimColumn}
          onToggleTrimColumn={() => cockpit.setShowTrimColumn(!cockpit.showTrimColumn)}
          onSelectEncar={cockpit.handleSelectEncarCar}
        />

        {/* ========================================================
            [3단계] 가격-주행거리 산점도 (Price-Mileage Scatter Plot)
            ======================================================== */}
        <ScatterPlotSection
          encarList={cockpit.encarList}
          mileageKm={cockpit.mileageKm}
          expectedSellPrice={cockpit.expectedSellPrice}
          effectiveSellPrice={cockpit.effectiveSellPrice}
          carName={cockpit.carName}
          selectedEncarId={cockpit.selectedEncarId}
          onSelectEncarCar={cockpit.handleSelectEncarCar}
        />

        {/* ========================================================
            [4단계] 헤딜 낙찰시세 (도매 실거래가 20대)
            ======================================================== */}
        <HeydealerBidsSection
          heydealerSummary={cockpit.heydealerSummary}
          availableHeydealerGrades={cockpit.availableHeydealerGrades}
          bestMatchHeydealerGrade={cockpit.bestMatchHeydealerGrade}
          heydealerGradeCounts={cockpit.heydealerGradeCounts}
          selectedHeydealerGradeFilter={cockpit.selectedHeydealerGradeFilter}
          setSelectedHeydealerGradeFilter={cockpit.setSelectedHeydealerGradeFilter}
          heydealerBids={cockpit.heydealerBids}
          filteredHeydealerBids={cockpit.filteredHeydealerBids}
          selectedHeydealerBidId={cockpit.selectedHeydealerBidId}
          setSelectedHeydealerBidId={cockpit.setSelectedHeydealerBidId}
          selectedHeydealerBid={cockpit.selectedHeydealerBid}
          mileageKm={cockpit.mileageKm}
        />

      </div>

      {/* Quick Text / Spec Paste Modal */}
      {cockpit.isQuickPasteOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#121317] border border-[#262833] rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-150">
            <div className="p-4 border-b border-[#22242c] flex items-center justify-between bg-[#16171d]">
              <div className="flex items-center gap-2">
                <span className="text-emerald-400 font-bold text-sm">📋 1초 텍스트/스펙 즉시 자동 분석</span>
              </div>
              <button
                type="button"
                onClick={() => cockpit.setIsQuickPasteOpen(false)}
                className="text-[#8b8e9d] hover:text-white p-1 rounded-lg hover:bg-[#22242c] transition"
              >
                ✕
              </button>
            </div>

            <div className="p-4 space-y-3">
              <p className="text-xs text-[#8b8e9d]">
                헤이딜러, 카카오톡, 메모장, 문자 등에서 복사한 차량 정보 텍스트를 그대로 붙여넣으세요.
                차량번호, 차종, 연식, 주행거리, 시세, 사고유무를 즉시 자동 추출합니다.
              </p>

              <textarea
                rows={5}
                value={cockpit.quickPasteText}
                onChange={(e) => cockpit.setQuickPasteText(e.target.value)}
                placeholder="예시: 240어8733 올뉴모닝(JA) 럭셔리 20년식 24,500km 815만원 완전무사고 스마트키"
                className="w-full bg-[#0d0e11] border border-[#22242c] rounded-xl p-3 text-xs text-white placeholder-[#515360] focus:outline-none focus:border-emerald-500 font-mono resize-none"
              />

              <div className="flex justify-between items-center gap-2 pt-2">
                <div className="flex items-center gap-1.5 overflow-x-auto text-[11px]">
                  <span className="text-[#515360]">빠른 예시:</span>
                  <button
                    type="button"
                    onClick={() => cockpit.setQuickPasteText('더 뉴 그랜저 IG 2.5 가솔린 르블랑 21년 42000km 2550만원 무사고')}
                    className="px-2 py-0.5 rounded bg-[#1f2029] text-[#8b8e9d] hover:text-white border border-[#2b2d3a] shrink-0"
                  >
                    그랜저 르블랑
                  </button>
                  <button
                    type="button"
                    onClick={() => cockpit.setQuickPasteText('37다1840 올 뉴 카니발 디젤 9인승 18년식 98000km 980만원')}
                    className="px-2 py-0.5 rounded bg-[#1f2029] text-[#8b8e9d] hover:text-white border border-[#2b2d3a] shrink-0"
                  >
                    카니발
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => cockpit.setIsQuickPasteOpen(false)}
                    className="px-3 py-1.5 rounded-lg bg-[#1f2029] hover:bg-[#2b2d3a] text-xs text-[#8b8e9d] hover:text-white transition"
                  >
                    취소
                  </button>
                  <button
                    type="button"
                    onClick={cockpit.handleQuickParseText}
                    className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white transition shadow-sm"
                  >
                    1초 자동 파싱 & 적용
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CarDetailModal 연동 모달 */}
      <CarDetailModal
        car={cockpit.cockpitModalCar}
        onClose={() => cockpit.setCockpitModalCar(null)}
        onUpdate={(updatedCar) => {
          props.onSaveToLedger(updatedCar);
          cockpit.setCockpitModalCar(null);
          cockpit.setSavedSuccess(true);
          setTimeout(() => cockpit.setSavedSuccess(false), 2500);
        }}
        onDelete={() => cockpit.setCockpitModalCar(null)}
      />

      {/* 🌟 보험사고 & 카히스토리 대형 종합 리포트 모달 */}
      <CarHistoryDetailModal
        isOpen={cockpit.showCarHistoryModal}
        onClose={() => cockpit.setShowCarHistoryModal(false)}
        carNumber={cockpit.carNumber}
        carName={cockpit.carName}
        currentMileage={cockpit.mileageKm}
        data={cockpit.targetCarHistory}
      />

    </div>
  );
};
