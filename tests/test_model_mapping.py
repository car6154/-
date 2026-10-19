# tests/test_model_mapping.py
"""
국산 전 차종 엔카 모델명 정규화 회귀 테스트
- 차얼마(오토플러스 원부) 입력 vs 헤이딜러 입력 시 동일한 엔카 모델(Model, ModelGroup)로 매핑되는지 15대 대표 차종 검증
"""
import os
import sys

# Windows cp949 콘솔 인코딩 대응
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.master_mapping import MasterMappingService

# 대표 15종 회귀 테스트 세트 (차량번호 하드코딩 금지)
REGRESSION_15_CARS = [
    {
        "name": "아반떼(CN7)",
        "year": 2021,
        "chaolma": ("아반떼 (CN7)", "가솔린 1.6 인스퍼레이션"),
        "heydealer": ("아반떼", "1.6 가솔린 인스퍼레이션"),
        "expected_model": "아반떼 (CN7)",
        "expected_group": "아반떼",
    },
    {
        "name": "쏘나타(DN8)",
        "year": 2020,
        "chaolma": ("쏘나타 (DN8)", "2.0 가솔린 프리미엄"),
        "heydealer": ("쏘나타", "2.0 가솔린 프리미엄"),
        "expected_model": "쏘나타 (DN8_)",
        "expected_group": "쏘나타",
    },
    {
        "name": "그랜저(IG)",
        "year": 2018,
        "chaolma": ("그랜저 IG", "2.4 GDi 프리미엄"),
        "heydealer": ("그랜저", "2.4 프리미엄"),
        "expected_model": "그랜저 IG",
        "expected_group": "그랜저",
    },
    {
        "name": "카니발(KA4)",
        "year": 2021,
        "chaolma": ("카니발 4세대", "9인승 디젤 프레스티지"),
        "heydealer": ("카니발", "9인승 디젤 프레스티지"),
        "expected_model": "카니발 4세대",
        "expected_group": "카니발",
    },
    {
        "name": "쏘렌토(MQ4)",
        "year": 2021,
        "chaolma": ("쏘렌토 4세대", "디젤 2.2 2WD 노블레스"),
        "heydealer": ("쏘렌토", "2.2 디젤 노블레스"),
        "expected_model": "쏘렌토 4세대",
        "expected_group": "쏘렌토",
    },
    {
        "name": "스포티지(NQ5)",
        "year": 2022,
        "chaolma": ("스포티지 5세대", "1.6 터보 2WD 노블레스"),
        "heydealer": ("스포티지", "1.6T 노블레스"),
        "expected_model": "스포티지 5세대",
        "expected_group": "스포티지",
    },
    {
        "name": "투싼(NX4)",
        "year": 2021,
        "chaolma": ("디 올 뉴 투싼 (NX4)", "1.6 터보 2WD 인스퍼레이션"),
        "heydealer": ("투싼", "1.6 터보 인스퍼레이션"),  # 트림명 '인스퍼레이션'의 '레이' 오매칭 방지
        "expected_model": "투싼 (NX4_)",
        "expected_group": "투싼",
    },
    {
        "name": "레이",
        "year": 2022,
        "chaolma": ("더 뉴 레이", "가솔린 시그니처"),
        "heydealer": ("더 뉴 기아 레이", "시그니처"),
        "expected_model": "더 뉴 레이",
        "expected_group": "레이",
    },
    {
        "name": "모닝",
        "year": 2018,
        "chaolma": ("올 뉴 모닝 (JA)", "가솔린 럭셔리"),
        "heydealer": ("모닝", "럭셔리"),
        "expected_model": "올 뉴 모닝 (JA_)",
        "expected_group": "모닝",
    },
    {
        "name": "스파크",
        "year": 2019,
        "chaolma": ("더 뉴 스파크", "LT"),
        "heydealer": ("스파크", "LT"),
        "expected_model": "더 뉴 스파크",
        "expected_group": "스파크",
    },
    {
        "name": "K5(DL3)",
        "year": 2021,
        "chaolma": ("K5 3세대", "2.0 가솔린 노블레스"),
        "heydealer": ("K5", "2.0 가솔린"),
        "expected_model": "K5 3세대",
        "expected_group": "K5",
    },
    {
        "name": "K3",
        "year": 2022,
        "chaolma": ("더 뉴 K3 2세대", "1.6 가솔린 프레스티지"),
        "heydealer": ("K3", "프레스티지"),
        "expected_model": "더 뉴 K3 2세대",
        "expected_group": "K3",
    },
    {
        "name": "K8",
        "year": 2022,
        "chaolma": ("K8", "2.5 가솔린 노블레스"),
        "heydealer": ("K8", "2.5 노블레스"),
        "expected_model": "K8",
        "expected_group": "K8",
    },
    {
        "name": "셀토스",
        "year": 2021,
        "chaolma": ("셀토스", "1.6 터보 2WD 노블레스"),
        "heydealer": ("셀토스", "1.6 터보"),
        "expected_model": "셀토스",
        "expected_group": "셀토스",
    },
    {
        "name": "캐스퍼",
        "year": 2022,
        "chaolma": ("캐스퍼", "1.0 터보 인스퍼레이션"),
        "heydealer": ("캐스퍼", "인스퍼레이션"),
        "expected_model": "캐스퍼",
        "expected_group": "캐스퍼",
    },
]


def test_15_car_models_cross_resolution():
    """15대 대표 국산 차종의 차얼마 vs 헤이딜러 엔카 모델 매핑 일치성 검증"""
    failures = []

    for car in REGRESSION_15_CARS:
        name = car["name"]
        year = car["year"]
        ch_cname, ch_sub = car["chaolma"]
        hd_cname, hd_sub = car["heydealer"]
        exp_m = car["expected_model"]
        exp_g = car["expected_group"]

        res_ch = MasterMappingService.resolve_encar_model("", ch_cname, ch_sub, year)
        res_hd = MasterMappingService.resolve_encar_model("", hd_cname, hd_sub, year)

        m_ch = res_ch.get("encar_model", "")
        m_hd = res_hd.get("encar_model", "")
        g_ch = res_ch.get("model_group", "")
        g_hd = res_hd.get("model_group", "")

        # 1. 차얼마와 헤이딜러의 엔카 모델명이 일치하는지
        if m_ch != m_hd:
            failures.append(f"[{name}] 모델명 불일치: 차얼마='{m_ch}' vs 헤이딜러='{m_hd}'")
            continue

        # 2. 모델그룹이 일치하는지
        if g_ch != g_hd or g_ch != exp_g:
            failures.append(f"[{name}] 모델그룹 불일치: 차얼마='{g_ch}', 헤이딜러='{g_hd}' (기대값: '{exp_g}')")
            continue

        # 3. 기대하는 엔카 모델명과 일치하는지 (DSL 언더바 보정 포함)
        clean_m_ch = m_ch.replace("_", "")
        clean_exp = exp_m.replace("_", "")
        if clean_m_ch != clean_exp:
            failures.append(f"[{name}] 기대 모델명 불일치: 매핑값='{m_ch}' vs 기대값='{exp_m}'")

    if failures:
        print("[FAIL] 테스트 실패 목록:")
        for f in failures:
            print(f"  - {f}")
        assert False, f"총 {len(failures)}건의 모델명 정규화 회귀 실패가 발생했습니다."

    print(f"[OK] 국산 15대 대표 차종 차얼마 vs 헤이딜러 엔카 모델명 100% 일치 검증 완료 ({len(REGRESSION_15_CARS)}종)")


def test_tucson_inspiration_ray_bug_prevention():
    """인스퍼레이션 트림명 내부 '레이' 음절 오매칭 방지 전용 단독 테스트"""
    res = MasterMappingService.resolve_encar_model("", "투싼", "1.6 터보 인스퍼레이션", 2021)
    encar_model = res.get("encar_model", "")
    model_group = res.get("model_group", "")

    assert model_group == "투싼", f"투싼이 레이로 오매칭되었습니다: model_group={model_group}"
    assert "투싼" in encar_model, f"엔카 모델명에 투싼이 포함되지 않았습니다: encar_model={encar_model}"
    print("[OK] 투싼 인스퍼레이션 -> 기아 레이 오매칭 방지 검증 통과!")


if __name__ == "__main__":
    test_15_car_models_cross_resolution()
    test_tucson_inspiration_ray_bug_prevention()
    print("[SUCCESS] 모든 모델명 정규화 회귀 테스트 통과!")
