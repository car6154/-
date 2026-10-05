export interface CarLedgerItem {
  id: string;
  regDate: string;        // 등록일 (예: 26-10-02)
  carNumber: string;      // 차량번호 (예: 149소7481)
  manufacturer: string;   // 제조사 (현대, 기아 등)
  carName: string;        // 차량명 (캐스퍼, 레이, 쏘나타 등)
  detailModel: string;    // 세부모델 (1.0 터보 인스퍼레이션 등)
  year: string;           // 연식 (22, 23 등)
  mileage: string;        // 주행거리 (41,486 km)
  options: string;        // 옵션 목록
  buyPrice: number;       // 매입가 (만원)
  sellPrice: number;      // 판매가 (만원)
  outerRepairs: number;   // 외판수리 판수
  repairCost: number;     // 외판수리비 (만원)
  heydealerFee: number;   // 헤딜수수료 (만원)
  memo: string;           // 특이사항 (예: [셀프(기본) / 마진: 120만])
  status: string;         // 상태 (장부저장, 판매완료, 보유중 등)
}

export interface InventorySettlementItem {
  id: string;
  order: number;
  buyDate: string;
  status: string;
  carNumber: string;
  carName: string;
  sellPrice: number;
  stockDays: number;
  buyPrice: number;
  outerRepairs: number;
  repairCost: number;
  heydealerFee: number;
  baseExpenses: number;
  contributionMargin: number;
  netProfit: number;
  feeRate: number;
  salesCommission: number;
  finalProfit: number;
  isMine: boolean;
  encarUrl?: string;
}

export interface AuctionCarItem {
  id: string;
  fullName: string;
  mileage: number;
  approvedAt: string;
  mainImageUrl: string | null;
}

export interface DealerBidItem {
  price: number;
  location: string;
  modelPartName: string;
  dealerName: string;
  createdAt: string;
}

export interface ComparableSaleItem {
  id: string;
  model: string;
  year: number;
  mileage: number;
  sellPrice: number;
  soldDays: number;
  soldDate: string;
}

export interface CockpitPresetData {
  carNumber?: string;
  manufacturer?: string;
  carName?: string;
  detailModel?: string;
  year?: number | string;
  mileage?: number | string;
  sellPrice?: number;
  buyPrice?: number;
  outerRepairs?: number;
  options?: string;
  memo?: string;
  auctionType?: string;
  targetMargin?: number;
}
