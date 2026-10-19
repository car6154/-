import sys
import os
import io
import json
import time
import urllib.parse

sys.path.insert(0, os.path.abspath("."))

from services.master_mapping import MasterMappingService
from services.encar_service import Scraper

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_k5_hybrid():
    print("==================================================================")
    print("1. K5 하이브리드 3세대 노블레스 실제 조회 검증")
    print("==================================================================")
    car_name = "K5 하이브리드 3세대"
    sub_model = "노블레스"
    year = 2022
    mileage = 50000
    car_no = "TEST_CAR_NO"

    url = MasterMappingService.generate_smart_encar_url(car_name, sub_model, year, mileage, car_number=car_no)
    print(f"생성된 URL: {url}")
    
    df, msg = Scraper.run(url, "")
    print(f"Scraper 결과: 매물 수={len(df)}대, msg={msg}")
    assert len(df) > 0, "K5 하이브리드 3세대 매물 수집 실패!"
    print(f"[OK] K5 하이브리드 3세대 엔카 매물 {len(df)}대 정상 수집 성공!\n")

def test_other_hybrids():
    print("==================================================================")
    print("2. 다른 하이브리드 차종 검증 (그랜저, 쏘나타)")
    print("==================================================================")
    cases = [
        ("더 뉴 그랜저 IG 하이브리드", "익스클루시브", 2020, 60000),
        ("쏘나타 하이브리드 (DN8)", "프리미엄", 2020, 50000),
        ("아반떼 하이브리드 (CN7)", "인스퍼레이션", 2021, 40000),
    ]
    for c_name, sub, yr, mil in cases:
        time.sleep(1)
        url = MasterMappingService.generate_smart_encar_url(c_name, sub, yr, mil)
        df, msg = Scraper.run(url, "")
        print(f"[{c_name} {sub}] -> 매물 수: {len(df)}대, msg: {msg}")
        assert len(df) > 0, f"{c_name} 매물 수집 실패!"
        print(f"  [OK] {c_name} 정상 수집 확인 (URL={url[:80]}...)")
    print("[OK] 모든 하이브리드 차종 테스트 통과!\n")

def test_gasoline_diesel():
    print("==================================================================")
    print("3. 기존 가솔린/디젤 차종 영향도 검증 (K5 3세대, 아반떼 CN7, 투싼 NX4)")
    print("==================================================================")
    cases = [
        ("K5 3세대", "2.0 가솔린 노블레스", 2021, 50000),
        ("아반떼 (CN7)", "1.6 가솔린 인스퍼레이션", 2021, 40000),
        ("투싼 (NX4)", "1.6 터보 2WD 인스퍼레이션", 2021, 50000),
    ]
    for c_name, sub, yr, mil in cases:
        time.sleep(1)
        url = MasterMappingService.generate_smart_encar_url(c_name, sub, yr, mil)
        df, msg = Scraper.run(url, "")
        print(f"[{c_name} {sub}] -> 매물 수: {len(df)}대, msg: {msg}")
        assert len(df) > 0, f"{c_name} 매물 수집 실패!"
        # 가솔린/디젤의 경우 BadgeGroup이 정상 포함되어 있는지 확인
        decoded = urllib.parse.unquote_plus(url)
        assert "BadgeGroup" in decoded, f"{c_name} 가솔린/디젤에 BadgeGroup이 누락되었습니다!"
        print(f"  [OK] {c_name} BadgeGroup 정상 유지 및 매물 수집 확인 (매물 {len(df)}대)")
    print("[OK] 가솔린/디젤 차종 영향도 없음 확인!\n")

if __name__ == "__main__":
    try:
        test_k5_hybrid()
        test_other_hybrids()
        test_gasoline_diesel()
        print("🎉 [ALL TESTS PASSED] 모든 검증 케이스 통과!")
    except Exception as e:
        print(f"❌ [TEST FAILED] {e}")
        sys.exit(1)
