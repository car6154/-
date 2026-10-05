import { InventorySettlementItem } from "@/types";

export const INITIAL_SETTLEMENT_ITEMS: InventorySettlementItem[] = [
  {
    id: "settle_1840",
    order: 2,
    buyDate: "10. 01",
    status: "보유/상품화중",
    carNumber: "37다1840",
    carName: "기아 올뉴카니발 디젤 9인승 프레스티지",
    sellPrice: 980,
    stockDays: 1,
    buyPrice: 654,
    outerRepairs: 2,
    repairCost: 26,
    heydealerFee: 55,
    baseExpenses: 15,
    contributionMargin: 193,
    netProfit: 19,
    feeRate: 0.1,
    salesCommission: 7,
    finalProfit: 19,
    isMine: true,
    encarUrl: ""
  },
  {
    id: "settle_2620",
    order: 1,
    buyDate: "09. 07",
    status: "판매완료",
    carNumber: "297로2620",
    carName: "기아 더뉴레이 시그니처",
    sellPrice: 1190,
    stockDays: 24,
    buyPrice: 956,
    outerRepairs: 5,
    repairCost: 65,
    heydealerFee: 0,
    baseExpenses: 15,
    contributionMargin: 125,
    netProfit: 12,
    feeRate: 0.1,
    salesCommission: 8,
    finalProfit: 12,
    isMine: true,
    encarUrl: "https://fem.encar.com/cars/detail/42722039"
  }
];
