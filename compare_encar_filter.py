from services.master_mapping import MasterMappingService
from services.encar_service import Scraper
from services.data_processor import DataProcessor

url = MasterMappingService.generate_smart_encar_url('디 올 뉴 투싼', '가솔린 1.6T 2WD 인스퍼레이션', 2021, 48000)
print('Generated URL:', url)
df, msg = Scraper.run(url, '')
print('Scraped raw count:', len(df))
df = DataProcessor.standardize(df)
df = Scraper.dedupe_after_scan(df)
print('After dedupe:', len(df))
df = DataProcessor.filter_strictly_by_submodel(df, target_car_name='디 올 뉴 투싼', target_sub_model='가솔린 1.6T 2WD 인스퍼레이션')
print('After filter_strictly_by_submodel:', len(df))
df = DataProcessor.sort_by_perf_and_year(df)

print(f"Prices: min={df['판매가'].min()}, max={df['판매가'].max()}, mean={int(df['판매가'].astype(float).mean())}")
for i, (_, row) in enumerate(df.iterrows()):
    print(f"[{i+1}] {row.get('연식')} | {row.get('판매가')}만 | {row.get('세부모델')} | 점검일:{row.get('성능일')} | 사고:{row.get('사고유무')}")
