import React from 'react';
import { BiddingCockpitTabProps } from './BiddingCockpit/types';
import { useBiddingCockpit } from './BiddingCockpit/hooks/useBiddingCockpit';
import { CockpitSidebar } from './BiddingCockpit/Sections/CockpitSidebar';
import { ValuationSummarySection } from './BiddingCockpit/Sections/ValuationSummarySection';
import { ComparableEncarSection } from './BiddingCockpit/Sections/ComparableEncarSection';
import { ScatterPlotSection } from './BiddingCockpit/Sections/ScatterPlotSection';
import { HeydealerBidsSection } from './BiddingCockpit/Sections/HeydealerBidsSection';
import { QuickPasteModal } from './BiddingCockpit/Sections/QuickPasteModal';
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
        targetCatalog={cockpit.targetNewCarCatalog}
        targetOptions={cockpit.targetOptions}
        unclassifiedBalance={cockpit.unclassifiedBalance}
        historyOptionTotalMan={cockpit.targetCarHistory?.totalOptionPrice ?? 0}
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
          aiRetailPrice={cockpit.aiRetailPrice}
          aiSafeBidCeiling={cockpit.aiSafeBidCeiling}
          targetMargin={cockpit.targetMargin}
          repairCostTotal={cockpit.repairCostTotal}
          safeBidCeiling={cockpit.safeBidCeiling}
          optionsTag={cockpit.optionsTag}
          outerRepairCount={cockpit.outerRepairCount}
          biddingVerdict={cockpit.biddingVerdict}
          isEncarLoading={cockpit.isEncarLoading}
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
          matchedAuctionList={cockpit.matchedAuctionList}
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
          onOpenHistoryModal={() => cockpit.setShowCarHistoryModal(true)}
          kcarStats={cockpit.kcarStats}
          isKcarLoading={cockpit.isKcarLoading}
          onRescanKcar={() => cockpit.fetchKcarMarket({
            carName: cockpit.carName,
            detailModel: cockpit.detailModel,
            manufacturer: cockpit.manufacturer,
            year: cockpit.yearModel,
            mileage: cockpit.mileageKm,
          })}
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
          kcarStats={cockpit.kcarStats}
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
      <QuickPasteModal
        isOpen={cockpit.isQuickPasteOpen}
        quickPasteText={cockpit.quickPasteText}
        setQuickPasteText={cockpit.setQuickPasteText}
        onClose={() => cockpit.setIsQuickPasteOpen(false)}
        onParse={cockpit.handleQuickParseText}
      />

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
