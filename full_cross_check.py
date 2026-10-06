import sys
import json
import pandas as pd
from sales_analysis import SalesDataAnalyzer, get_car_market_stats
from services.master_mapping import MasterMappingService
from services.encar_service import Scraper
from services.data_processor import DataProcessor
from services.sold_out_tracker import SoldOutTracker

out_lines = []

def log(s=""):
    out_lines.append(str(s))

log("=== 8501 vs 3000 A-Z FULL CROSS-CHECK ===")
car_name = "디 올 뉴 투싼"
sub_model = "가솔린 1.6T 2WD 인스퍼레이션"
year_num = 2021
mileage_num = 48000

def calculate_fees_8501(target_price, is_zero=False):
    if not is_zero:
        if target_price <= 100: return 7.5
        elif target_price <= 500: return 18.5
        elif target_price <= 1000: return 24.5
        elif target_price <= 3000: return 25.0
        else: return 36.0
    else:
        if target_price <= 100: return 14.0
        elif target_price <= 500: return 30.0
        elif target_price <= 1000: return 36.5
        elif target_price <= 1500: return 36.5
        elif target_price <= 3000: return 39.5
        elif target_price <= 4000: return 47.5
        else: return 50.5

fee_8501_self = calculate_fees_8501(2000, False)
fee_8501_zero = calculate_fees_8501(2000, True)
log(f"[A] Fees at 2000man: Self={fee_8501_self}man, Zero={fee_8501_zero}man")

# C. 엔카 실시간 동급 매물
url = MasterMappingService.generate_smart_encar_url(car_name, sub_model, year_num, mileage_num)
log(f"[C] Generated Encar URL: {url}")

df_raw, msg = Scraper.run(url, "")
log(f"[C] Scraped Raw Count: {len(df_raw)}")

df_std = DataProcessor.standardize(df_raw)
df_dedupe = Scraper.dedupe_after_scan(df_std)
log(f"[C] After Dedupe: {len(df_dedupe)}")

df_filtered = DataProcessor.filter_strictly_by_submodel(df_dedupe, target_car_name=car_name, target_sub_model=sub_model)
log(f"[C] After Strict Submodel Filter: {len(df_filtered)}")

prices = pd.to_numeric(df_filtered['판매가'], errors='coerce')
avg_p = int(prices.mean()) if not prices.empty else 0
min_p = int(prices.min()) if not prices.empty else 0
max_p = int(prices.max()) if not prices.empty else 0
med_p = int(prices.median()) if not prices.empty else 0

is_no = df_filtered['사고유무'].astype(str).str.contains('무사고')
no_acc_avg = int(prices[is_no].mean()) if is_no.any() else 0
acc_avg = int(prices[~is_no].mean()) if (~is_no).any() else 0
acc_gap = no_acc_avg - acc_avg

log(f"[C] Stats: Min={min_p}, Max={max_p}, Mean={avg_p}, Median={med_p}")
log(f"[C] Accident Gap: NoAccAvg={no_acc_avg}, AccAvg={acc_avg}, Gap={acc_gap}")

df_8501 = DataProcessor.sort_by_perf_and_year(df_filtered)
df_3000 = DataProcessor.sort_by_price_year_perf(df_filtered)

log("\n[C - 8501 Sort: Perf -> Year -> Date] Top 5:")
for i, (_, r) in enumerate(df_8501.head(5).iterrows()):
    log(f"  8501 #{i+1}: {r.get('연식')} | {r.get('판매가')}man | checkDate={r.get('성능일')} | acc={r.get('사고유무')}")

log("\n[C - 3000 Sort: Option 2 (Price -> Year -> Perf)] Top 5:")
for i, (_, r) in enumerate(df_3000.head(5).iterrows()):
    log(f"  3000 #{i+1}: {r.get('연식')} | {r.get('판매가')}man | checkDate={r.get('성능일')} | acc={r.get('사고유무')}")

# D. 자사 오토플러스 실적
analyzer = SalesDataAnalyzer.get_instance()
m_stats = analyzer.get_market_stats(car_name, sub_model, 2021)
log(f"\n[D] Autoplus Stats (8501): total_count={m_stats.get('total_count')}, avg_days={m_stats.get('avg_days')}, avg_sell_price={m_stats.get('avg_sell_price')}, profit={m_stats.get('avg_profit')}")

# E. 엔카 완판
cids = [str(x) for x in df_filtered['_carid'] if str(x).strip()]
sold_res = Scraper.fetch_sold_out_cars(cids, target_year="2021", expected_model=car_name)
log(f"\n[E] SoldOut Stats: has_data={sold_res.get('has_data')}, count_30d={sold_res.get('count_30d')}, daily_rate={sold_res.get('daily_rate')}, badge={sold_res.get('velocity_badge')}, latest_date={sold_res.get('latest_sold_date')}, avg_mil={sold_res.get('avg_mileage')}")

with open("cross_check_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))

print("Results written to cross_check_result.txt")
