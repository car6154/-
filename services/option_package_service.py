# services/option_package_service.py
"""
옵션 패키지 지능형 매칭 및 툴팁/팝업 서비스
- 엔카 신차 패키지 옵션(예: 컴포트 패키지 III, 셀렉티브 패키지 II, 드라이브 와이즈)의 세부 품목 사전 관리
- 헤이딜러의 풀어진 낱개 옵션(예: 통풍시트, 전동시트, 사각지대경고, 전동트렁크 등)과 지능형 매칭
- 마우스 커서 호버 시 세부 품목 및 매칭 여부 팝업(툴팁) 텍스트 생성
"""

import os
import json
import re
import unicodedata

CRAWLED_CATALOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "encar_newcar_catalog.json")
_CRAWLED_CACHE = None
_CACHE_MTIME = 0

def load_crawled_catalog() -> dict:
    global _CRAWLED_CACHE, _CACHE_MTIME
    if os.path.exists(CRAWLED_CATALOG_FILE):
        try:
            mtime = os.path.getmtime(CRAWLED_CATALOG_FILE)
            if _CRAWLED_CACHE is None or mtime > _CACHE_MTIME:
                with open(CRAWLED_CATALOG_FILE, "r", encoding="utf-8") as f:
                    _CRAWLED_CACHE = json.load(f)
                    _CACHE_MTIME = mtime
            return _CRAWLED_CACHE or {}
        except Exception:
            return _CRAWLED_CACHE or {}
    return {}

# ═══════════════════════════════════════════════════════════════
# 📦 신차 패키지 옵션 마스터 카탈로그 (쉐보레, 현대, 기아, 르노, KGM)
# ═══════════════════════════════════════════════════════════════
PACKAGE_CATALOG = [
    # ── 쉐보레 (Chevrolet) ──
    {
        "id": "chevy_comfort_3",
        "aliases": ["컴포트패키지iii", "컴포트패키지3", "컴포트패키지", "컴포트3", "컴포트iii", "comfort3", "comfortiii"],
        "name": "컴포트 패키지 III",
        "brand": "쉐보레",
        "description": "천공 천연가죽 시트, 운전석 8way 전동시트, 운전석 파워 요추 받침, 1열 통풍시트",
        "items": ["천공 천연가죽 시트", "운전석 8way 전동시트", "운전석 파워 요추 받침", "1열 통풍시트"],
        "match_keywords": ["통풍시트", "통풍", "전동시트", "가죽시트", "천연가죽시트", "요추받침", "파워시트"],
        "min_matches": 1
    },
    {
        "id": "chevy_comfort_2",
        "aliases": ["컴포트패키지ii", "컴포트패키지2", "컴포트2", "컴포트ii", "comfort2"],
        "name": "컴포트 패키지 II",
        "brand": "쉐보레",
        "description": "천공 가죽시트, 운전석 8way 전동시트, 파워 요추받침, 1열 통풍시트, 열선시트",
        "items": ["천공 가죽시트", "운전석 전동시트", "파워 요추받침", "1열 통풍시트"],
        "match_keywords": ["통풍시트", "통풍", "전동시트", "가죽시트", "요추받침"],
        "min_matches": 1
    },
    {
        "id": "chevy_selective_2",
        "aliases": ["셀렉티브패키지ii", "셀렉티브패키지2", "셀렉티브패키지", "셀렉티브2", "셀렉티브ii", "selective2", "selectiveii"],
        "name": "셀렉티브 패키지 II",
        "brand": "쉐보레",
        "description": "LED 헤드램프, 차선 변경 및 사각지대 경고 시스템, 후측방 경고 시스템, 쉐보레 보타이 프로젝션 핸즈프리 파워 리프트게이트, 레인센싱 와이퍼, 2열 듀얼 USB 포트, 스마트폰 무선충전 시스템",
        "items": ["LED 헤드램프", "사각지대 경고 시스템", "후측방 경고 시스템", "핸즈프리 파워 리프트게이트", "레인센싱 와이퍼", "스마트폰 무선충전"],
        "match_keywords": ["파워테일게이트", "파워리프트게이트", "전동트렁크", "사각지대", "후측방", "led헤드램프", "무선충전"],
        "min_matches": 1
    },
    {
        "id": "chevy_selective_1",
        "aliases": ["셀렉티브패키지i", "셀렉티브패키지1", "셀렉티브1", "selective1"],
        "name": "셀렉티브 패키지 I",
        "brand": "쉐보레",
        "description": "LED 헤드램프, 사각지대 경고, 후측방 경고, 전동 파워 리프트게이트",
        "items": ["LED 헤드램프", "사각지대 경고", "후측방 경고", "파워 리프트게이트"],
        "match_keywords": ["파워테일게이트", "파워리프트게이트", "전동트렁크", "사각지대", "후측방", "led헤드램프"],
        "min_matches": 1
    },
    {
        "id": "chevy_premium",
        "aliases": ["프리미엄패키지", "프리미엄팩", "premiumpackage"],
        "name": "프리미엄 패키지",
        "brand": "쉐보레",
        "description": "내비게이션 시스템, 디지털 후방 카메라, 슈퍼비전 4.2\" 컬러 클러스터, 어댑티브 크루즈 컨트롤(정차 & 재출발), 컴바이너 헤드업 디스플레이, 무선 폰 프로젝션",
        "items": ["내비게이션 시스템", "디지털 후방 카메라", "슈퍼비전 컬러 클러스터", "어댑티브 크루즈 컨트롤(ACC)", "컴바이너 헤드업 디스플레이(HUD)", "무선 폰 프로젝션"],
        "match_keywords": ["내비게이션", "네비게이션", "후방카메라", "어댑티브", "크루즈컨트롤", "acc", "헤드업", "hud"],
        "min_matches": 1
    },
    {
        "id": "chevy_skyfull_sunroof",
        "aliases": ["skyfull파노라마선루프", "스카이풀파노라마선루프", "스카이풀선루프", "파노라마선루프", "선루프", "skyfull선루프"],
        "name": "SkyFull(스카이풀) 파노라마 선루프",
        "brand": "쉐보레",
        "description": "SkyFull(스카이풀) 파노라마 선루프, 쉐도우 루프랙",
        "items": ["파노라마 선루프", "루프랙"],
        "match_keywords": ["파노라마선루프", "선루프", "썬루프"],
        "min_matches": 1
    },
    {
        "id": "chevy_bose_sound",
        "aliases": ["bose프리미엄사운드", "bose프리미엄스피커", "bose사운드", "보스사운드", "보스프리미엄사운드패키지", "bosesound"],
        "name": "Bose 프리미엄 사운드 패키지",
        "brand": "쉐보레",
        "description": "Bose 프리미엄 7스피커/9스피커 사운드 시스템 및 외장 앰프",
        "items": ["Bose 프리미엄 스피커"],
        "match_keywords": ["bose", "보스", "프리미엄스피커", "스피커"],
        "min_matches": 1
    },
    {
        "id": "chevy_drive_assist",
        "aliases": ["드라이브어시스트패키지", "드라이빙어시스트", "세이프티패키지", "쉐보레세이프티"],
        "name": "드라이브 어시스트 패키지",
        "brand": "쉐보레",
        "description": "어댑티브 크루즈 컨트롤(ACC, 정차&재출발), 차선변경 및 사각지대 경고, 후측방 경고",
        "items": ["어댑티브 크루즈 컨트롤(ACC)", "사각지대 경고시스템", "후측방 경고"],
        "match_keywords": ["어댑티브", "크루즈컨트롤", "acc", "사각지대", "차선변경"],
        "min_matches": 1
    },
    {
        "id": "chevy_tech_pack",
        "aliases": ["테크패키지", "테크놀로지패키지", "techpackage"],
        "name": "테크 패키지",
        "brand": "쉐보레",
        "description": "헤드업 디스플레이(컴바이너 HUD), 어댑티브 크루즈 컨트롤, 스마트폰 무선충전, Bose 사운드",
        "items": ["헤드업 디스플레이(HUD)", "어댑티브 크루즈 컨트롤", "스마트폰 무선충전"],
        "match_keywords": ["헤드업", "hud", "어댑티브", "무선충전"],
        "min_matches": 1
    },
    {
        "id": "chevy_comfort_1",
        "aliases": ["컴포트패키지i", "컴포트패키지1", "컴포트1", "컴포트i", "comfort1"],
        "name": "컴포트 패키지 I",
        "brand": "쉐보레",
        "description": "열선 스티어링 휠, 1열 열선시트, 인조가죽 시트",
        "items": ["열선 스티어링 휠", "1열 열선시트", "인조가죽 시트"],
        "match_keywords": ["열선핸들", "열선스티어링", "열선시트", "가죽시트"],
        "min_matches": 1
    },
    {
        "id": "chevy_hit_cool",
        "aliases": ["힛앤쿨", "힛앤쿨패키지", "힛앤쿨테크놀로지", "hitandcool", "hitcool"],
        "name": "힛 & 쿨 패키지",
        "brand": "쉐보레",
        "description": "앞좌석 3단 통풍시트, 운전석 8way 전동시트, 파워 요추받침",
        "items": ["앞좌석 통풍시트", "운전석 8way 전동시트", "파워 요추받침"],
        "match_keywords": ["통풍시트", "통풍", "전동시트", "요추받침"],
        "min_matches": 1
    },
    {
        "id": "chevy_acc",
        "aliases": ["어댑티브크루즈", "어댑티브크루즈컨트롤", "acc", "adaptivecruise"],
        "name": "어댑티브 크루즈 컨트롤",
        "brand": "쉐보레",
        "description": "정차 및 재출발 기능을 지원하는 어댑티브 크루즈 컨트롤 (ACC)",
        "items": ["어댑티브 크루즈 컨트롤"],
        "match_keywords": ["어댑티브", "크루즈컨트롤", "acc", "스마트크루즈"],
        "min_matches": 1
    },
    {
        "id": "chevy_smart_driving",
        "aliases": ["스마트드라이빙팩", "시티드라이빙팩", "스마트드라이빙", "시티드라이빙"],
        "name": "스마트 / 시티 드라이빙 팩",
        "brand": "쉐보레",
        "description": "지능형 어댑티브 크루즈 컨트롤, 자동 긴급제동, 차선 유지 보조, 사각지대 경고",
        "items": ["어댑티브 크루즈 컨트롤", "자동 긴급제동", "차선 유지 보조", "사각지대 경고"],
        "match_keywords": ["어댑티브", "크루즈", "사각지대", "차선유지"],
        "min_matches": 1
    },

    # ── 현대자동차 (Hyundai) ──
    {
        "id": "hyundai_smart_sense",
        "aliases": ["현대스마트센스", "스마트센스", "스마트센스1", "스마트센스2", "스마트센스3", "스마트센스i", "스마트센스ii", "스마트센스iii"],
        "name": "현대 스마트센스",
        "brand": "현대",
        "description": "전방 충돌방지 보조, 스마트 크루즈 컨트롤(Stop & Go), 고속도로 주행 보조(HDA), 후측방 충돌방지 보조, 안전 하차 보조",
        "items": ["스마트 크루즈 컨트롤", "고속도로 주행 보조(HDA)", "후측방 충돌방지 보조", "안전 하차 보조"],
        "match_keywords": ["스마트크루즈", "크루즈", "ascc", "scc", "hda", "후측방", "차로유지", "스마트센스"],
        "min_matches": 1
    },
    {
        "id": "hyundai_comfort",
        "aliases": ["컴포트", "컴포트1", "컴포트2", "컴포트i", "컴포트ii", "컴포트플러스"],
        "name": "컴포트",
        "brand": "현대",
        "description": "1열 통풍시트, 운전석/동승석 전동시트, 동승석 릴렉션 컴포트 시트, 2열 열선시트, 스마트 전동식 트렁크",
        "items": ["1열 통풍시트", "운전석/동승석 전동시트", "2열 열선시트", "스마트 전동트렁크"],
        "match_keywords": ["통풍시트", "통풍", "전동시트", "2열열선", "파워테일게이트", "전동트렁크"],
        "min_matches": 1
    },
    {
        "id": "hyundai_style",
        "aliases": ["스타일", "스타일1", "스타일2", "스타일i", "스타일ii", "익스테리어디자인"],
        "name": "스타일 / 익스테리어 디자인",
        "brand": "현대",
        "description": "Full LED 헤드램프(프로젝션 타입), LED 리어 콤비램프, LED 방향지시등, 대구경 알로이 휠",
        "items": ["Full LED 헤드램프", "LED 리어콤비램프", "대구경 알로이 휠"],
        "match_keywords": ["led헤드램프", "led램프", "프로젝션", "스타일"],
        "min_matches": 1
    },
    {
        "id": "hyundai_hitech",
        "aliases": ["하이테크", "하이테크패키지", "테크1", "테크2", "테크i", "테크ii", "플래티넘"],
        "name": "하이테크 / 플래티넘",
        "brand": "현대",
        "description": "12.3인치 컬러 풀 LCD 클러스터, 헤드업 디스플레이(HUD), 스마트폰 무선충전, 디지털 키",
        "items": ["12.3인치 LCD 클러스터", "헤드업 디스플레이(HUD)", "스마트폰 무선충전", "디지털 키"],
        "match_keywords": ["헤드업", "hud", "무선충전", "디지털키", "클러스터", "하이테크"],
        "min_matches": 1
    },
    {
        "id": "hyundai_parking_assist",
        "aliases": ["파킹어시스트", "파킹어시스트플러스", "서라운드뷰", "서라운드뷰모니터", "모니터링팩"],
        "name": "파킹 어시스트 / 서라운드 뷰",
        "brand": "현대",
        "description": "서라운드 뷰 모니터(SVM), 후측방 모니터(BVM), 원격 스마트 주차 보조(RSPA), 후방 주차 충돌방지 보조",
        "items": ["서라운드 뷰 모니터(SVM)", "후측방 모니터(BVM)", "원격 스마트 주차보조"],
        "match_keywords": ["서라운드뷰", "어라운드뷰", "모니터링", "svm", "bvm", "원격주차"],
        "min_matches": 1
    },
    {
        "id": "hyundai_builtin_cam",
        "aliases": ["빌트인캠", "빌트인캠1", "빌트인캠2", "빌트인캠i", "빌트인캠ii"],
        "name": "빌트인 캠",
        "brand": "현대",
        "description": "빌트인 캠(주행/주차 녹화), 보조배터리",
        "items": ["빌트인 캠", "보조배터리"],
        "match_keywords": ["빌트인캠", "블랙박스"],
        "min_matches": 1
    },

    # ── 기아자동차 (Kia) ──
    {
        "id": "kia_drive_wise",
        "aliases": ["드라이브와이즈", "드라이브와이즈1", "드라이브와이즈2", "드라이브와이즈i", "드라이브와이즈ii", "drivewise"],
        "name": "드라이브 와이즈",
        "brand": "기아",
        "description": "전방 충돌방지 보조, 스마트 크루즈 컨트롤(정차&재출발), 후측방 충돌방지 보조, 고속도로 주행 보조(HDA), 안전 하차 보조",
        "items": ["스마트 크루즈 컨트롤", "고속도로 주행 보조(HDA)", "후측방 충돌방지", "안전 하차 보조"],
        "match_keywords": ["스마트크루즈", "크루즈", "ascc", "scc", "hda", "후측방", "차로유지", "드라이브와이즈"],
        "min_matches": 1
    },
    {
        "id": "kia_comfort",
        "aliases": ["컴포트", "컴포트1", "컴포트2", "컴포트i", "컴포트ii", "시트패키지"],
        "name": "컴포트",
        "brand": "기아",
        "description": "1열 통풍시트, 운전석 파워시트, 전동식 허리지지대, 2열 열선시트, 스마트 파워테일게이트",
        "items": ["1열 통풍시트", "파워시트", "2열 열선시트", "스마트 파워테일게이트"],
        "match_keywords": ["통풍시트", "통풍", "전동시트", "2열열선", "파워테일게이트", "전동트렁크"],
        "min_matches": 1
    },
    {
        "id": "kia_monitoring_pack",
        "aliases": ["모니터링팩", "서라운드뷰모니터링", "모니터링패키지"],
        "name": "모니터링 팩",
        "brand": "기아",
        "description": "서라운드 뷰 모니터, 후측방 모니터(BVM), 원격 스마트 주차 보조, 후방 주차 충돌방지",
        "items": ["서라운드 뷰 모니터", "후측방 모니터", "원격 스마트 주차보조"],
        "match_keywords": ["서라운드뷰", "어라운드뷰", "모니터링", "svm", "bvm", "원격주차"],
        "min_matches": 1
    },
    {
        "id": "kia_hud_pack",
        "aliases": ["hud팩", "헤드업디스플레이", "hud패키지"],
        "name": "HUD 팩 / 헤드업 디스플레이",
        "brand": "기아",
        "description": "헤드업 디스플레이(HUD), 레인센서, 빌트인 공기청정기",
        "items": ["헤드업 디스플레이(HUD)", "레인센서"],
        "match_keywords": ["헤드업", "hud"],
        "min_matches": 1
    },
    {
        "id": "kia_smart_connect",
        "aliases": ["스마트커넥트", "기아디지털키"],
        "name": "스마트 커넥트",
        "brand": "기아",
        "description": "기아 디지털 키, 스마트폰 무선충전, 터치타입 아웃사이드 도어핸들",
        "items": ["기아 디지털 키", "스마트폰 무선충전"],
        "match_keywords": ["디지털키", "무선충전"],
        "min_matches": 1
    },

    # ── 르노코리아 (Renault) ──
    {
        "id": "renault_slink",
        "aliases": ["slink패키지", "slink패키지1", "slink패키지2", "slink패키지i", "slink패키지ii", "s링크패키지", "s링크"],
        "name": "S-Link 패키지",
        "brand": "르노코리아",
        "description": "8.7인치 내비게이션, Bose 서라운드 사운드 시스템, 엠비언트 라이트, 후방카메라",
        "items": ["8.7인치 내비게이션", "Bose 서라운드 사운드", "후방카메라"],
        "match_keywords": ["slink", "s링크", "내비", "보스", "bose"],
        "min_matches": 1
    },
    {
        "id": "renault_driving_assist",
        "aliases": ["드라이빙어시스트패키지", "드라이빙어시스트1", "드라이빙어시스트2", "드라이빙어시스트i", "드라이빙어시스트ii"],
        "name": "드라이빙 어시스트 패키지",
        "brand": "르노코리아",
        "description": "사각지대 경보(BSW), 차선이탈 경보, 긴급제동 보조(AEBS), 어댑티브 크루즈 컨트롤",
        "items": ["사각지대 경보(BSW)", "차선이탈 경보", "어댑티브 크루즈"],
        "match_keywords": ["사각지대", "어댑티브", "차선이탈"],
        "min_matches": 1
    },
    {
        "id": "renault_magic_tailgate",
        "aliases": ["매직테일게이트", "매직테일", "스마트테일게이트"],
        "name": "매직 테일게이트",
        "brand": "르노코리아",
        "description": "핸즈프리 전동식 파워 트렁크 (매직 테일게이트)",
        "items": ["핸즈프리 전동식 파워 트렁크"],
        "match_keywords": ["매직테일게이트", "전동트렁크", "파워테일"],
        "min_matches": 1
    },

    # ── KGM / 쌍용 (KG Mobility) ──
    {
        "id": "kgm_deep_control",
        "aliases": ["딥컨트롤패키지", "딥컨트롤1", "딥컨트롤2", "딥컨트롤i", "딥컨트롤ii", "딥컨트롤"],
        "name": "딥컨트롤 패키지",
        "brand": "KGM",
        "description": "인텔리전트 어댑티브 크루즈 컨트롤(IACC), 후측방 경고, 후측방 접근 충돌보조, 차선 유지 보조",
        "items": ["인텔리전트 어댑티브 크루즈(IACC)", "후측방 경고", "차선 유지 보조"],
        "match_keywords": ["iacc", "어댑티브", "스마트크루즈", "후측방"],
        "min_matches": 1
    },
    {
        "id": "kgm_smart_tailgate",
        "aliases": ["스마트파워테일게이트", "파워테일게이트"],
        "name": "스마트 파워 테일게이트",
        "brand": "KGM",
        "description": "스마트 전동식 파워 테일게이트",
        "items": ["스마트 전동식 트렁크"],
        "match_keywords": ["파워테일게이트", "전동트렁크", "스마트테일게이트"],
        "min_matches": 1
    }
]


def normalize_opt_name(text: str) -> str:
    """패키지/옵션 명칭 정규화 (공백, 기호, 괄호, 로마숫자 통일)"""
    if not text:
        return ""
    # 유니코드 정규화 (Ⅰ, Ⅱ, Ⅲ -> I, II, III 등)
    t = unicodedata.normalize('NFKC', str(text))
    # 괄호 안의 가격 정보나 부가설명 제거: '컴포트 패키지 III (79만)' -> '컴포트 패키지 III'
    # 단, 전체가 괄호로 감싸진 경우('(캘리그래피)') 괄호만 벗겨서 알맹이 보존
    sub_t = re.sub(r'\(.*?\)', '', t).strip().lower()
    if sub_t:
        t = sub_t
    else:
        t = t.replace('(', '').replace(')', '').strip().lower()
    # 공백 및 특수기호 제거
    t = re.sub(r'[\s\-_/.]', '', t)
    # 로마숫자 통일
    t = t.replace('iv', '4').replace('iii', '3').replace('ii', '2').replace('i', '1')
    return t


def extract_keywords_from_description(desc: str) -> list:
    """공식 설명문에서 헤이딜러 매칭용 핵심 부품 키워드 자동 추출"""
    KEYWORD_CANDIDATES = [
        "통풍시트", "통풍", "전동시트", "파워시트", "요추받침", "가죽시트", "열선시트", "열선핸들",
        "어댑티브", "스마트크루즈", "크루즈컨트롤", "acc", "scc", "ascc", "hda", "hda2",
        "차선변경", "사각지대", "후측방", "차로유지", "차로이탈", "긴급제동",
        "헤드업", "hud", "내비게이션", "네비게이션", "후방카메라", "어라운드뷰", "서라운드뷰", "svm", "bvm",
        "전동트렁크", "파워테일게이트", "스마트테일게이트", "리프트게이트", "무선충전", "선루프", "썬루프",
        "파노라마선루프", "디지털키", "빌트인캠", "블랙박스", "bose", "보스", "크렐", "krell", "jbl", "스피커"
    ]
    norm_desc = normalize_opt_name(desc)
    found = []
    for kw in KEYWORD_CANDIDATES:
        if normalize_opt_name(kw) in norm_desc:
            found.append(kw)
    return found


def find_package_definition(pkg_str: str, car_name: str = "", year: str = "") -> dict:
    """
    엔카 옵션 문자열이 신차 패키지인지 식별하여 패키지 정보 반환
    1순위: 엔카 공식 신차가격표 크롤링 DB (차종+연식 1:1 매칭)
    2순위: 기본 마스터 패키지 카탈로그 (FALLBACK)
    """
    if not pkg_str:
        return None
    norm = normalize_opt_name(pkg_str)
    if not norm or len(norm) < 2:
        return None

    # 1. 크롤링된 공식 엔카 신차가격표 DB 우선 검색
    crawled_db = load_crawled_catalog()
    if crawled_db:
        # 1-1. 차종명이 지정된 경우 해당 차종 우선 검색
        target_models = []
        if car_name and car_name != "전체":
            norm_car = normalize_opt_name(car_name)
            for m_key in crawled_db:
                norm_m = normalize_opt_name(m_key)
                if norm_car in norm_m or norm_m in norm_car:
                    target_models.append(m_key)
        
        # 차종 지정이 없거나 못 찾은 경우 전체 모델 검색
        if not target_models:
            target_models = list(crawled_db.keys())

        # 연식 정규화 (예: '2021', '2021년형', '21/03', '21년03월' -> '2021')
        clean_yr = ""
        if year:
            yr_str = str(year).strip()
            m4 = re.search(r'20\d{2}', yr_str)
            if m4:
                clean_yr = m4.group(0)
            else:
                m2 = re.search(r'(?:^|[^\d])([12]\d)(?:년|/|\.|$)', yr_str)
                if m2:
                    clean_yr = f"20{m2.group(1)}"

        for m_key in target_models:
            yr_dict = crawled_db[m_key]
            # 연식이 일치하는 연식 우선 탐색
            search_years = [clean_yr] if clean_yr and clean_yr in yr_dict else list(yr_dict.keys())
            for y in search_years:
                yr_val = yr_dict.get(y, {})
                items_to_search = {}
                if isinstance(yr_val, dict):
                    if "packages" in yr_val or "options" in yr_val:
                        # 1) 패키지 세부 구성 설명
                        for p_name, p_desc in yr_val.get("packages", {}).items():
                            if p_desc:
                                items_to_search[p_name] = p_desc
                        # 2) 개별 옵션 (설명 또는 가격 포함)
                        for o_name, o_info in yr_val.get("options", {}).items():
                            if isinstance(o_info, dict):
                                desc = o_info.get("desc")
                                price = o_info.get("price")
                                if not desc and price:
                                    desc = f"선택옵션 (출고가: {price:,}원)"
                                if desc and o_name not in items_to_search:
                                    items_to_search[o_name] = desc
                            elif isinstance(o_info, str) and o_name not in items_to_search:
                                items_to_search[o_name] = o_info
                    else:
                        items_to_search = yr_val

                for p_name, p_desc in items_to_search.items():
                    norm_p = normalize_opt_name(p_name)
                    if not norm_p or len(norm_p) < 2:
                        continue
                    if norm == norm_p or (len(norm) >= 3 and len(norm_p) >= 3 and (norm_p in norm or norm in norm_p)):
                        # 공식 DB에서 완벽 매칭 성공!
                        matched_kw = extract_keywords_from_description(p_desc)
                        return {
                            "id": f"crawled_{m_key}_{y}_{p_name}",
                            "name": p_name,
                            "brand": m_key,
                            "description": p_desc,
                            "items": [it.strip() for it in p_desc.split(",") if it.strip()],
                            "match_keywords": matched_kw if matched_kw else [p_name],
                            "min_matches": 1
                        }

    # 2. 기본 마스터 카탈로그 검색 (Fallback)
    for pkg in PACKAGE_CATALOG:
        for alias in pkg["aliases"]:
            norm_alias = normalize_opt_name(alias)
            if not norm_alias or len(norm_alias) < 2:
                continue
            if norm == norm_alias or (len(norm) >= 3 and len(norm_alias) >= 3 and (norm_alias in norm or norm in norm_alias)):
                return pkg

    for pkg in PACKAGE_CATALOG:
        norm_name = normalize_opt_name(pkg["name"])
        if not norm_name or len(norm_name) < 2:
            continue
        if norm == norm_name or (len(norm) >= 3 and len(norm_name) >= 3 and (norm_name in norm or norm in norm_name)):
            return pkg

    return None


def match_package_with_decomposed(pkg_str: str, target_opts: list, car_name: str = "", year: str = "") -> tuple:
    """
    엔카 패키지와 헤이딜러의 풀어진 낱개 옵션 리스트 간의 지능형 매칭 판정
    """
    if not pkg_str or not target_opts:
        return False, [], None

    pkg_def = find_package_definition(pkg_str, car_name, year)
    
    # 1. 패키지 사전에 등록된 패키지인 경우
    if pkg_def:
        matched_sub_items = []
        target_norm_list = [normalize_opt_name(t) for t in target_opts if t]
        
        # 키워드 매칭
        for kw in pkg_def.get("match_keywords", []):
            norm_kw = normalize_opt_name(kw)
            for raw_t, norm_t in zip(target_opts, target_norm_list):
                if norm_kw in norm_t or norm_t in norm_kw:
                    if raw_t not in matched_sub_items:
                        matched_sub_items.append(raw_t)

        min_req = pkg_def.get("min_matches", 1)
        is_matched = len(matched_sub_items) >= min_req
        return is_matched, matched_sub_items, pkg_def

    # 2. 패키지 사전에 없는 일반 옵션인 경우 (기존 동의어 매칭 로직 활용)
    norm_opt = normalize_opt_name(pkg_str)
    for t in target_opts:
        norm_t = normalize_opt_name(t)
        if norm_opt and norm_t:
            if norm_opt in norm_t or norm_t in norm_opt:
                return True, [t], None

    return False, [], None


def build_option_tooltip(pkg_str: str, target_opts: list = None, car_name: str = "", year: str = "") -> tuple:
    """
    마우스 호버 시 표출할 툴팁 텍스트와 매칭 여부 생성
    반환값: (is_matched: bool, tooltip_text: str)
    """
    is_matched, matched_items, pkg_def = match_package_with_decomposed(pkg_str, target_opts, car_name, year)

    if pkg_def:
        # 패키지 정보가 있는 경우
        title_line = f"[{pkg_def['name']}]"
        desc_line = f"구성: {pkg_def['description']}"
        
        if is_matched:
            matched_str = ", ".join(matched_items[:4])
            status_line = f"──────────────────────────────\n✓ 기준 차량 장착 확인됨! ({matched_str})"
        else:
            status_line = "──────────────────────────────\n(기준 차량에는 미장착된 옵션입니다)"
            
        tooltip_text = f"{title_line}\n{desc_line}\n{status_line}"
        return is_matched, tooltip_text

    # 일반 단일 옵션인 경우
    if is_matched:
        return True, f"[{pkg_str}]\n✓ 기준 차량 장착 옵션과 일치함"
    else:
        return False, f"[{pkg_str}]"
