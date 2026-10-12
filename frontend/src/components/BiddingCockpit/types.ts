import { ComparableSaleItem, CarLedgerItem, CockpitPresetData } from '@/types';

export interface BiddingCockpitTabProps {
  initialCarName?: string;
  initialSellPrice?: number;
  presetCarName?: string;
  presetSellPrice?: number;
  preset?: CockpitPresetData | null;
  comparables?: ComparableSaleItem[];
  onSaveToLedger: (item: Omit<CarLedgerItem, 'id' | 'regDate'>) => void;
}

export interface EncarItem {
  id: string;
  checkDate: string;
  holdingDays: number;
  carName: string;
  modelName?: string;
  subModel?: string;
  year: string;
  mileage: number;
  price: number;
  accidentType: string;
  color: string;
  optionsText: string;
  replaces: string[];
  repairs: string[];
  encarUrl?: string;
  photo?: string;
  isLive?: boolean;
}

export interface EncarSoldItem {
  id: string;
  carId?: string;
  carName: string;
  subModel: string;
  year: string;
  mileage: number;
  finalPrice: number;
  daysTaken: number;
  soldDate: string;
  accident: string;
  encarUrl?: string;
}

export interface EncarSoldStats {
  has_data: boolean;
  total_sold_count: number;
  count_30d: number;
  daily_rate: number;
  velocity_badge: string;
  velocity_color: string;
  avg_mileage: number;
  latest_sold_date: string;
  target_year?: string;
  is_year_filtered?: boolean;
  matched_hits: number;
  sold_avg_price: number;
  sold_avg_days: number;
  enriched_cars: any[];
}

export interface HeydealerBidItem {
  id: string;
  model: string;
  year: string;
  yearNum: number;
  mileage: number;
  bidPrice: number;
  bidDate: string;
  accident: string;
  accidentType: '완전무사고' | '단순수리' | '유사고';
  options: string;
  isExport: boolean;
  repairs: { part: string; repair: string; desc: string }[];
  keyOptions: string[];
  link?: string;
}
