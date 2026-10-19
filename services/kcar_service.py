# -*- coding: utf-8 -*-
"""
services/kcar_service.py
K-Car 공식 직영 매물 검색 및 실시간 소매 시세 통계 서비스
- K-Car 공식 직영 검색 API (POST https://api.kcar.com/bc/search/list/drct)
- AES-128-CBC 암호화 (Key: SKFJ2424DasfaJRI, IV: sfq241sf3dscs321)
- 백엔드 단일 진실 공급원(SSOT): 통계(평균, 최저, 최고, 중앙값, 연식별, 가격분포) 일괄 산출
"""
import os
import re
import json
import base64
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

KEY = b"SKFJ2424DasfaJRI"
IV = b"sfq241sf3dscs321"

# KCar 제조사 및 모델 코드 매핑 테이블 (https://market-api.kcar.com/api/v1/ds/getModelListCount 실측 기준)
# [필수 규칙] 하이브리드 모델 등록 시 양방향 어순 등록:
# 1. '[차종] [N세대] 하이브리드'와 '[차종] 하이브리드 [N세대]' 양방향 모두 등록할 것.
# 2. '더 뉴 [차종] [N세대] 하이브리드' vs '더 뉴 [차종] 하이브리드 [N세대]' 등 수식어 포함형도 대칭 등록.
# 3. frontend/src/utils/kcarUrl.ts의 KCAR_MODEL_GROUPS와 100% 동일하게 유지할 것.
# 4. 신규 추가 후 tests/test_kcar_hybrid_variants.py 실행 필수.
KCAR_MNUFTR_MAP = {
    "현대": "001",
    "기아": "002",
    "쉐보레": "003",
    "쉐보레(GM대우)": "003",
    "쉐보레(대우)": "003",
    "GM대우": "003",
    "KGM": "004",
    "KG모빌리티": "004",
    "KG모빌리티(쌍용)": "004",
    "쌍용": "004",
    "르노코리아": "005",
    "르노코리아(삼성)": "005",
    "르노삼성": "005",
    "제네시스": "007",
    "아우디": "011",
    "BMW": "012",
    "벤츠": "013",
    "볼보": "017",
    "렉서스": "035",
    "테슬라": "087",
}

# (제조사코드, 모델그룹코드): {모델명: 모델코드}
KCAR_MODEL_GROUP_MAP = {
    # 기아 (002)
    ("002", "036"): {  # 카니발
        "그랜드 카니발": "074",
        "뉴카니발": "075",
        "카니발 R": "090",
        "올 뉴 카니발": "113",
        "더 뉴 카니발": "137",
        "카니발 (4세대)": "166",
        "카니발 4세대": "166",
        "신형 카니발": "166",
        "더 뉴 카니발 4세대": "190",
        "더 뉴 카니발 하이브리드 4세대": "191",
        "더 뉴 카니발 4세대 하이브리드": "191",
        "더 뉴 카니발 하이브리드": "191",
        "카니발 하이브리드 4세대": "191",
        "카니발 4세대 하이브리드": "191",
        "카니발 하이브리드": "191",
        "하이브리드 4세대": "191",
    },
    ("002", "027"): {  # 쏘렌토
        "쏘렌토 R": "087",
        "뉴 쏘렌토 R": "102",
        "올 뉴 쏘렌토": "114",
        "더 뉴 쏘렌토": "133",
        "쏘렌토 4세대": "163",
        "신형 쏘렌토 (MQ4)": "163",
        "쏘렌토 4세대 하이브리드": "164",
        "쏘렌토 하이브리드 4세대": "164",
        "쏘렌토 하이브리드 (4세대)": "164",
        "신형 쏘렌토 하이브리드": "164",
        "더 뉴 쏘렌토 4세대": "185",
        "더 뉴 쏘렌토 4세대 하이브리드": "186",
        "더 뉴 쏘렌토 하이브리드 4세대": "186",
        "더 뉴 쏘렌토 하이브리드": "186",
    },
    ("002", "025"): {  # 스포티지
        "스포티지 R": "091",
        "더 뉴 스포티지 R": "107",
        "스포티지 4세대": "119",
        "스포티지 더 볼드": "141",
        "디 올 뉴 스포티지": "175",
        "스포티지 5세대": "175",
        "디 올 뉴 스포티지 하이브리드": "176",
        "디 올 뉴 스포티지 하이브리드 5세대": "176",
        "스포티지 5세대 하이브리드": "176",
        "스포티지 하이브리드 5세대": "176",
        "더 뉴 스포티지": "198",
        "더 뉴 스포티지 하이브리드": "199",
        "더 뉴 스포티지 5세대 하이브리드": "199",
        "더 뉴 스포티지 하이브리드 5세대": "199",
    },
    ("002", "065"): {  # 셀토스
        "셀토스": "155",
        "더 뉴 셀토스": "181",
        "디 올 뉴 셀토스": "204",
        "디 올 뉴 셀토스 하이브리드": "205",
        "셀토스 하이브리드": "205",
    },
    ("002", "061"): {  # 니로
        "니로": "126",
        "니로 하이브리드": "126",
        "니로 EV": "140",
        "니로 플러그인 하이브리드": "149",
        "더 뉴 니로": "150",
        "더 뉴 니로 하이브리드": "150",
        "디 올 뉴 니로": "177",
        "디 올 뉴 니로 하이브리드": "177",
        "니로 하이브리드 2세대": "177",
        "니로 2세대 하이브리드": "177",
        "디 올 뉴 니로 EV": "179",
        "니로 플러스": "180",
        "더 뉴 니로 (SG2)": "206",
    },
    ("002", "058"): {  # 레이
        "레이": "099",
        "더 뉴 레이": "134",
        "레이 EV": "153",
        "더 뉴 기아 레이": "182",
        "더 뉴 기아 레이 EV": "187",
    },
    ("002", "013"): {  # 모닝
        "뉴모닝": "083",
        "올 뉴 모닝": "095",
        "더 뉴 모닝": "116",
        "올 뉴 모닝 (JA)": "130",
        "모닝 어반": "165",
        "더 뉴 모닝 (JA)": "184",
    },
    ("002", "015"): {  # 모하비
        "모하비": "080",
        "더 뉴 모하비": "123",
        "모하비 더 마스터": "156",
    },
    ("002", "063"): {"스토닉": "132"},
    ("002", "037"): {"뉴카렌스": "076", "올 뉴 카렌스": "105", "더 뉴 카렌스": "127"},
    ("002", "060"): {  # K3
        "K3": "103",
        "더 뉴 K3": "120",
        "올 뉴 K3": "136",
        "K3 GT": "142",
        "더 뉴 K3 2세대": "171",
        "더 뉴 K3 GT 2세대": "172",
    },
    ("002", "001"): {  # K5
        "K5": "092",
        "K5 하이브리드": "097",
        "더 뉴 K5": "106",
        "K5 2세대": "118",
        "K5 하이브리드 2세대": "121",
        "K5 2세대 하이브리드": "121",
        "더 뉴 K5 2세대": "135",
        "더 뉴 K5 하이브리드 2세대": "139",
        "더 뉴 K5 2세대 하이브리드": "139",
        "K5 3세대": "157",
        "신형 K5": "157",
        "K5 3세대 하이브리드": "162",
        "K5 하이브리드 3세대": "162",
        "더 뉴 K5 3세대": "188",
        "더 뉴 K5 3세대 하이브리드": "189",
        "더 뉴 K5 하이브리드 3세대": "189",
    },
    ("002", "002"): {  # K7
        "K7": "089",
        "더 프레스티지 K7": "096",
        "더 뉴 K7": "104",
        "K7 하이브리드": "111",
        "올 뉴 K7": "122",
        "올 뉴 K7 하이브리드": "129",
        "올 뉴 K7 하이브리드 2세대": "129",
        "K7 하이브리드 2세대": "129",
        "K7 2세대 하이브리드": "129",
        "K7 프리미어": "152",
        "K7 프리미어 하이브리드": "154",
    },
    ("002", "066"): {  # K8
        "K8": "169",
        "K8 하이브리드": "173",
        "더 뉴 K8": "196",
        "더 뉴 K8 하이브리드": "197",
    },
    ("002", "059"): {"K9": "101", "더 뉴 K9": "117", "더 K9": "138", "더 뉴 K9 2세대": "174"},
    ("002", "062"): {"스팅어": "131", "스팅어 마이스터": "167"},
    ("002", "067"): {"EV6": "170", "더 뉴 EV6": "195"},
    ("002", "068"): {"EV9": "183"},
    ("002", "069"): {"EV3": "194"},
    ("002", "071"): {"EV4": "201"},
    ("002", "073"): {"EV5": "203"},
    # 현대 (001)
    ("001", "004"): {  # 그랜저
        "그랜저 TG": "040",
        "더 럭셔리 그랜저": "101",
        "그랜저 뉴 럭셔리": "103",
        "그랜저 HG": "106",
        "그랜저 HG 하이브리드": "125",
        "그랜저 IG": "141",
        "그랜저 IG 하이브리드": "143",
        "그랜저 6세대 하이브리드": "143",
        "그랜저 하이브리드 6세대": "143",
        "더 뉴 그랜저": "171",
        "더 뉴 그랜저 IG": "171",
        "더 뉴 그랜저 하이브리드": "174",
        "더 뉴 그랜저 IG 하이브리드": "174",
        "그랜저 (GN7)": "199",
        "그랜저 하이브리드 (GN7)": "200",
        "그랜저 (GN7) 하이브리드": "200",
        "그랜저 7세대 하이브리드": "200",
        "그랜저 하이브리드 7세대": "200",
        "디 올 뉴 그랜저 하이브리드": "200",
        "디 올 뉴 그랜저 (GN7) 하이브리드": "200",
        "디 올 뉴 그랜저 하이브리드 (GN7)": "200",
        "더 뉴 그랜저 (GN7)": "230",
        "더 뉴 그랜저 하이브리드 (GN7)": "231",
        "더 뉴 그랜저 (GN7) 하이브리드": "231",
    },
    ("001", "019"): {  # 아반떼
        "아반떼 HD": "081",
        "아반떼 하이브리드": "095",
        "아반떼 MD": "104",
        "아반떼 쿠페": "121",
        "더 뉴 아반떼": "123",
        "아반떼 AD": "136",
        "더 뉴 아반떼 AD": "154",
        "아반떼 (CN7)": "176",
        "아반떼 하이브리드 (CN7)": "181",
        "아반떼 (CN7) 하이브리드": "181",
        "아반떼 7세대 하이브리드": "181",
        "아반떼 하이브리드 7세대": "181",
        "아반떼 N": "195",
        "더 뉴 아반떼 (CN7)": "206",
        "더 뉴 아반떼 하이브리드 (CN7)": "207",
        "더 뉴 아반떼 (CN7) 하이브리드": "207",
        "더 뉴 아반떼 하이브리드": "207",
        "더 뉴 아반떼 7세대 하이브리드": "207",
        "더 뉴 아반떼 N": "211",
        "디 올 뉴 아반떼 (CN8)": "232",
        "디 올 뉴 아반떼 하이브리드 (CN8)": "233",
        "디 올 뉴 아반떼 (CN8) 하이브리드": "233",
    },
    ("001", "018"): {  # 쏘나타
        "NF 쏘나타": "039",
        "NF 쏘나타 트랜스폼": "092",
        "YF 쏘나타": "098",
        "쏘나타 하이브리드": "108",
        "쏘나타 더 브릴리언트": "115",
        "LF 쏘나타": "126",
        "LF 쏘나타 하이브리드": "128",
        "쏘나타 하이브리드 (LF)": "128",
        "쏘나타 하이브리드 LF": "128",
        "쏘나타 뉴 라이즈": "142",
        "쏘나타 뉴 라이즈 하이브리드": "144",
        "쏘나타 DN8": "163",
        "쏘나타 (DN8)": "163",
        "쏘나타 DN8 하이브리드": "169",
        "쏘나타 (DN8) 하이브리드": "169",
        "쏘나타 하이브리드 (DN8)": "169",
        "쏘나타 하이브리드 DN8": "169",
        "쏘나타 8세대 하이브리드": "169",
        "쏘나타 하이브리드 8세대": "169",
        "쏘나타 디 엣지": "203",
        "쏘나타 디 엣지 하이브리드": "204",
        "쏘나타 하이브리드 디 엣지": "204",
        "쏘나타 (DN8) 하이브리드 디 엣지": "204",
    },
    ("001", "017"): {  # 싼타페
        "싼타페 CM": "080",
        "싼타페 DM": "111",
        "싼타페 더 프라임": "134",
        "싼타페 TM": "150",
        "더 뉴 싼타페": "177",
        "더 뉴 싼타페 하이브리드": "191",
        "더 뉴 싼타페 하이브리드 (TM)": "191",
        "더 뉴 싼타페 (TM) 하이브리드": "191",
        "싼타페 하이브리드 (TM)": "191",
        "디 올 뉴 싼타페": "208",
        "디 올 뉴 싼타페 하이브리드": "209",
        "디 올 뉴 싼타페 (MX5) 하이브리드": "209",
        "디 올 뉴 싼타페 하이브리드 (MX5)": "209",
        "싼타페 5세대 하이브리드": "209",
        "싼타페 하이브리드 5세대": "209",
        "싼타페 (MX5) 하이브리드": "209",
        "싼타페 하이브리드 (MX5)": "209",
    },
    ("001", "032"): {  # 투싼
        "투싼 ix": "096",
        "뉴 투싼 ix": "122",
        "올 뉴 투싼": "133",
        "더 올뉴투싼": "133",
        "올 뉴 투싼 TL": "155",
        "투싼 (4세대)": "179",
        "투싼 4세대": "179",
        "투싼 (NX4)": "179",
        "투싼 하이브리드 (4세대)": "183",
        "투싼 4세대 하이브리드": "183",
        "투싼 하이브리드 4세대": "183",
        "투싼 (NX4) 하이브리드": "183",
        "투싼 하이브리드 (NX4)": "183",
        "투싼 NX4 하이브리드": "183",
        "더 뉴 투싼": "213",
        "더 뉴 투싼 하이브리드": "214",
        "더 뉴 투싼 4세대 하이브리드": "214",
        "더 뉴 투싼 하이브리드 4세대": "214",
    },
    ("001", "058"): {  # 팰리세이드
        "팰리세이드": "157",
        "더 뉴 팰리세이드": "197",
        "디 올 뉴 팰리세이드": "221",
        "디 올 뉴 팰리세이드 하이브리드": "222",
        "팰리세이드 하이브리드": "222",
    },
    ("001", "055"): {  # 코나
        "코나": "146",
        "코나 일렉트릭": "152",
        "코나 하이브리드": "173",
        "더 뉴 코나": "180",
        "더 뉴 코나 하이브리드": "182",
        "코나 N": "194",
        "코나 (SX2)": "201",
        "코나 하이브리드 (SX2)": "202",
        "코나 (SX2) 하이브리드": "202",
        "코나 2세대 하이브리드": "202",
        "코나 하이브리드 2세대": "202",
        "디 올 뉴 코나 하이브리드": "202",
        "디 올 뉴 코나 (SX2) 하이브리드": "202",
        "디 올 뉴 코나 하이브리드 (SX2)": "202",
        "코나 일렉트릭 (SX2)": "205",
    },
    ("001", "067"): {"캐스퍼": "196", "캐스퍼 일렉트릭": "219", "더 뉴 캐스퍼": "220"},
    ("001", "053"): {  # 아이오닉
        "아이오닉 하이브리드": "138",
        "아이오닉 일렉트릭": "139",
        "더 뉴 아이오닉 하이브리드": "161",
        "더 뉴 아이오닉 일렉트릭": "172",
        "아이오닉 5": "186",
        "아이오닉 6": "198",
        "아이오닉 5 N": "210",
        "더 뉴 아이오닉 5": "216",
        "아이오닉 9": "223",
        "더 뉴 아이오닉 6": "225",
    },
    ("001", "063"): {"스타리아": "185", "스타리아 하이브리드": "217", "더 뉴 스타리아": "227", "더 뉴 스타리아 하이브리드": "228"},
    ("001", "015"): {"그랜드 스타렉스": "083", "더 뉴 그랜드 스타렉스": "148"},
    ("001", "059"): {"베뉴": "167"},
    ("001", "056"): {"넥쏘": "151", "디 올 뉴 넥쏘": "224"},
    ("001", "001"): {"i30": "084", "i30(신형)": "117", "더 뉴 i30": "130", "i30 (PD)": "140"},
    ("001", "049"): {"i40": "109", "i40 살룬": "110", "더 뉴 i40": "131", "더 뉴 i40 살룬": "132"},
    ("001", "048"): {"벨로스터": "107", "더 뉴 벨로스터": "129", "벨로스터 (JS)": "149", "벨로스터-N": "156"},
    ("001", "050"): {"맥스크루즈": "118", "더 뉴 맥스크루즈": "135"},
    ("001", "025"): {"제네시스 DH": "124"},
    # 쉐보레 (003)
    ("003", "043"): {"스파크": "075", "스파크 EV": "083", "더 넥스트 스파크": "086", "더 뉴 스파크": "096"},
    ("003", "046"): {"말리부": "079", "올 뉴 말리부": "088", "더 뉴 말리부": "098"},
    ("003", "048"): {"트랙스": "082", "더 뉴 트랙스": "092", "트랙스 크로스오버": "108"},
    ("003", "055"): {"트레일블레이저": "102", "더 뉴 트레일블레이저": "109"},
    ("003", "041"): {"크루즈": "073", "크루즈5": "078", "어메이징 뉴 크루즈": "084", "올 뉴 크루즈": "093"},
    ("003", "040"): {"올란도": "072"},
    ("003", "052"): {"이쿼녹스": "097", "더 넥스트 이쿼녹스": "107"},
    ("003", "054"): {"트래버스": "101", "더 뉴 트래버스": "111"},
    ("003", "053"): {"콜로라도": "100", "리얼 뉴 콜로라도": "103", "올 뉴 콜로라도": "110"},
    ("003", "051"): {"볼트 EV": "095", "뉴 볼트 EV": "104"},
    ("003", "056"): {"볼트 EUV": "105"},
    # KGM (004)
    ("004", "013"): {"토레스": "121", "토레스 EVX": "123", "더 뉴 토레스": "128", "더 뉴 토레스 하이브리드": "134", "토레스 하이브리드": "134", "뉴 토레스": "137", "뉴 토레스 하이브리드": "138"},
    ("004", "012"): {"티볼리": "107", "티볼리 에어": "108", "티볼리 아머": "112", "베리 뉴 티볼리": "116", "더 뉴 티볼리": "124", "더 뉴 티볼리 에어": "125"},
    ("004", "003"): {
        "렉스턴 W": "103",
        "G4 렉스턴": "111",
        "렉스턴 스포츠": "113",
        "렉스턴 스포츠 칸": "114",
        "올 뉴 렉스턴": "117",
        "더 뉴 렉스턴 스포츠": "118",
        "더 뉴 렉스턴 스포츠 칸": "119",
        "렉스턴 뉴 아레나": "122",
        "더 뉴 렉스턴 스포츠 쿨멘": "126",
        "더 뉴 렉스턴 스포츠 칸 쿨멘": "127",
    },
    ("004", "011"): {
        "코란도 C": "099",
        "코란도 스포츠": "102",
        "코란도 투리스모": "105",
        "뉴코란도 C": "106",
        "더 뉴 코란도 스포츠": "109",
        "뉴 스타일 코란도 C": "110",
        "뷰티풀 코란도": "115",
        "코란도 이모션": "120",
        "코란도 EV": "129",
    },
    ("004", "006"): {"액티언 (J120)": "130", "액티언 하이브리드 (J120)": "135", "액티언 (J120) 하이브리드": "135", "액티언 하이브리드": "135"},
    # 르노코리아 (005)
    ("005", "011"): {"QM6": "066", "더 뉴 QM6": "071", "뉴 QM6": "077", "더 뉴 QM6 F/L": "079"},
    ("005", "010"): {"SM6": "065", "더 뉴 SM6": "074"},
    ("005", "015"): {"XM3": "072", "XM3 하이브리드": "078", "XM3 E-TECH 하이브리드": "078"},
    ("005", "019"): {"그랑 콜레오스": "082", "그랑 콜레오스 하이브리드": "083", "그랑 콜레오스 E-TECH 하이브리드": "083"},
    ("005", "018"): {"아르카나 하이브리드": "080", "아르카나 E-TECH 하이브리드": "080", "아르카나": "081"},
    ("005", "009"): {"QM3": "059", "뉴QM3": "067"},
    ("005", "001"): {"SM3": "002", "뉴SM3": "054", "SM3 네오": "062"},
    ("005", "002"): {"뉴SM5(신형)": "055", "뉴SM5 플래티넘": "058", "SM5 노바": "064"},
    ("005", "003"): {"All New SM7": "057", "SM7 노바": "063"},
    ("005", "014"): {"마스터": "070", "뉴 마스터": "075"},
    # 제네시스 (007)
    ("007", "001"): {"EQ900": "001"},
    ("007", "003"): {"G70": "003", "더 뉴 G70": "008"},
    ("007", "002"): {
        "G80": "002",
        "G80 (RG3)": "007",
        "G80 (RG3) 일렉트리파이드": "010",
        "G80 (RG3 F/L)": "015",
        "G80 (RG3 F/L) 일렉트리파이드": "018",
    },
    ("007", "004"): {"G90": "005", "G90 (RS4)": "012"},
    ("007", "007"): {"GV60": "011", "더 뉴 GV60": "020"},
    ("007", "006"): {"GV70": "009", "eGV70": "013", "GV70 (F/L)": "017", "eGV70 (F/L)": "019"},
    ("007", "005"): {"GV80": "006", "GV80 쿠페": "014", "GV80 (F/L)": "016", "GV80 하이브리드": "022"},
    # 아우디 (011)
    ("011", "001"): {"A3 (8Y)": "063", "뉴 A3": "024"},
    ("011", "002"): {"A4 (B9)": "041", "뉴 A4 (B8)": "011"},
    ("011", "021"): {"A5 (B10)": "078", "A5 (F5)": "047"},
    ("011", "004"): {"A6 (C9)": "083", "A6 (C8)": "048", "뉴 A6 (C7)": "004"},
    ("011", "025"): {"A7 (4K)": "051", "A7": "030"},
    ("011", "003"): {"A8 (D5)": "052", "뉴 A8 (D4)": "013"},
    ("011", "026"): {"Q3 (F3)": "049", "Q3": "031"},
    ("011", "039"): {"Q4 e-트론": "067"},
    ("011", "020"): {"Q5 (FY)": "053", "Q5": "025"},
    ("011", "013"): {"Q7 (4M)": "040", "Q7": "016"},
    ("011", "034"): {"Q8 (4M)": "050"},
    ("011", "036"): {"e-트론": "058"},
    # BMW (012)
    ("012", "001"): {"1시리즈 (F70)": "103", "1시리즈 (F40)": "076", "1시리즈 (F20)": "020"},
    ("012", "018"): {"2시리즈 그란쿠페 (F44)": "072", "2시리즈 액티브 투어러 (U06)": "090"},
    ("012", "002"): {"3시리즈 (G20)": "069", "3시리즈 (F30)": "038", "3시리즈 (E90)": "001"},
    ("012", "017"): {"4시리즈 (G22)": "082", "4시리즈 (F32)": "012"},
    ("012", "003"): {"5시리즈 (G60)": "095", "5시리즈 (G30)": "060", "5시리즈 (F10)": "039"},
    ("012", "004"): {"6시리즈 (F12)": "018"},
    ("012", "015"): {"6시리즈 GT (G32)": "061", "3시리즈 GT (F34)": "029", "5시리즈 GT (F07)": "026"},
    ("012", "005"): {"7시리즈 (G70)": "091", "7시리즈 (G11 F/L)": "066", "7시리즈 (G11)": "036", "7시리즈 (F01)": "003"},
    ("012", "006"): {"8시리즈 (G15)": "077"},
    ("012", "014"): {"X1 (U11)": "094", "X1 (F48)": "037"},
    ("012", "007"): {"X3 (G45)": "100", "X3 (G01)": "062", "X3 (F25)": "028"},
    ("012", "020"): {"X4 (G02)": "068", "X4 (F26)": "033"},
    ("012", "008"): {"X5 (G05)": "065", "X5 (F15)": "030", "X5 (E70)": "022"},
    ("012", "011"): {"X6 (G06)": "078", "X6 (F16)": "023"},
    ("012", "032"): {"X7 (G07)": "071"},
    ("012", "038"): {"i4 (G26)": "087"},
    ("012", "042"): {"i5 (G60)": "097"},
    ("012", "036"): {"iX3 (G08)": "085"},
    # 벤츠 (013)
    ("013", "029"): {"A-클래스 W177": "087", "A-클래스 W176": "064"},
    ("013", "001"): {"C-클래스 W206": "096", "C-클래스 W205": "067", "C-클래스 W204": "012"},
    ("013", "031"): {"CLA-클래스 C118": "088", "CLA-클래스 C117": "066"},
    ("013", "003"): {"CLS-클래스 C257": "083", "CLS-클래스 W218": "062"},
    ("013", "004"): {"E-클래스 W214": "104", "E-클래스 W213": "072", "E-클래스 W212": "001"},
    ("013", "005"): {"S-클래스 W223": "092", "S-클래스 W222": "065", "S-클래스 W221": "002"},
    ("013", "032"): {"GLA-클래스 H247": "091", "GLA-클래스 X156": "068"},
    ("013", "038"): {"GLB-클래스 X247": "089"},
    ("013", "034"): {"GLC-클래스 X254": "101", "GLC-클래스 X253": "071"},
    ("013", "035"): {"GLE-클래스 W167": "086", "GLE-클래스 W166": "070"},
    ("013", "037"): {"GLS-클래스 X167": "093", "GLS-클래스 X166": "074"},
    ("013", "013"): {"G-클래스 W465": "106", "G-클래스 W463b": "085", "G-클래스 W463": "010"},
    ("013", "040"): {"EQA H243": "094"},
    ("013", "042"): {"EQB X243": "097"},
    ("013", "044"): {"EQE V295": "098", "EQE SUV X294": "102"},
    ("013", "041"): {"EQS V297": "095", "EQS SUV X296": "099"},
    # 볼보 (017)
    ("017", "009"): {"S60 3세대": "028", "S60": "008"},
    ("017", "015"): {"S90": "016"},
    ("017", "017"): {"V60 크로스컨트리 2세대": "029", "V60 크로스컨트리": "022"},
    ("017", "022"): {"V90 크로스컨트리": "025"},
    ("017", "023"): {"XC40 리차지": "031", "XC40": "027"},
    ("017", "016"): {"XC60 2세대": "026", "XC60": "017"},
    ("017", "010"): {"XC90 2세대": "024", "XC90": "010"},
    # 렉서스 (035)
    ("035", "001"): {"올 뉴 ES": "066", "ES300h 7세대": "053", "뉴 ES300h": "037", "뉴 ES350": "036"},
    ("035", "013"): {"NX350h": "058", "NX450h+": "059", "NX300h": "034", "NX300": "048"},
    ("035", "005"): {"RX 5세대": "060", "RX450hL 4세대": "055", "RX450h 4세대": "044", "RX350 4세대": "043", "RX450h": "028"},
    ("035", "016"): {"UX300h": "063", "UX250h": "054"},
    # 테슬라 (087)
    ("087", "003"): {"모델 3 하이랜드": "005", "모델 3": "003"},
    ("087", "004"): {"모델 Y 주니퍼": "006", "모델 Y": "004"},
    ("087", "001"): {"모델 S": "001"},
    ("087", "002"): {"모델 X": "002"},
    ("087", "005"): {"사이버트럭": "007"},
}


from services.kcar_grade_data import KCAR_GRADE_TREE


def resolve_kcar_grade_codes(m_cd: str, grp_cd: str, mod_cd: str, sub_model: str = "", raw_car_name: str = ""):
    """(m_cd, grp_cd, mod_cd) 모델 내에서 sub_model에 부합하는 (grd_cd, grd_dtl_cd) 반환."""
    if not sub_model or str(sub_model).strip() in ("", "전체", "-"):
        return "", ""

    m_key = f"{m_cd},{grp_cd},{mod_cd}"
    grd_map = KCAR_GRADE_TREE.get(m_key)
    if not grd_map:
        return "", ""

    def _norm(s: str) -> str:
        return re.sub(r'[\s\(\)\-_\/]+', '', str(s)).upper()

    sub_str = str(sub_model).strip()
    combined_src = f"{raw_car_name} {sub_str}".strip()
    comb_norm = _norm(combined_src)

    has_turbo = ("터보" in comb_norm) or bool(re.search(r'\d\.\d\s*T(?![A-Z])', combined_src.upper()))
    has_van = ("밴" in comb_norm) or ("카고" in comb_norm)
    has_lpg = ("LPG" in comb_norm) or ("LPI" in comb_norm) or ("LPE" in comb_norm)
    has_diesel = ("디젤" in comb_norm) or ("VGT" in comb_norm) or ("TDI" in comb_norm) or ("CDI" in comb_norm) or bool(re.search(r'\d\.\d\s*D(?![A-Z])', combined_src.upper()))
    has_gasoline = ("가솔린" in comb_norm) or ("GDI" in comb_norm) or ("GDE" in comb_norm) or ("GTE" in comb_norm) or ("MPI" in comb_norm) or ("휘발유" in comb_norm)

    has_4wd = ("4WD" in comb_norm) or ("AWD" in comb_norm) or ("4MATIC" in comb_norm) or ("XDRIVE" in comb_norm) or ("QUATTRO" in comb_norm)
    has_2wd = ("2WD" in comb_norm) or ("FF" in comb_norm)

    seat_m = re.search(r'(\d+)\s*인승', combined_src)
    target_seat = f"{seat_m.group(1)}인승" if seat_m else ""

    disp_m = re.findall(r'(\d\.\d)', combined_src)
    if not disp_m:
        m_hg = re.search(r'(?:HG|TG|IG|K7|K5|SM[3567])\s*(\d)(\d)0', comb_norm)
        if m_hg:
            disp_m = [f"{m_hg.group(1)}.{m_hg.group(2)}"]
    target_disp = disp_m[0] if disp_m else ""

    special_keywords = ["하이리무진", "아웃도어", "캠핑", "특장", "택시", "장애인", "렌터카", "수출", "운전교습", "어린이", "킨더", "구급", "휠체어", "N라인", "NLINE", "GT"]

    non_van_grds = [k for k in grd_map.keys() if "밴" not in _norm(k) and "카고" not in _norm(k)] or list(grd_map.keys())
    turbo_flags = [("터보" in _norm(k) or bool(re.search(r'\d\.\d\s*T(?![A-Z])', k.upper()))) for k in non_van_grds]
    has_both_turbo_and_na = any(turbo_flags) and not all(turbo_flags)

    spec_ignore = {
        "가솔린", "디젤", "전기", "EV", "하이브리드", "HEV", "LPG", "LPI", "LPE",
        "2WD", "4WD", "AWD", "FF", "FR", "터보", "일반인판매용", "일반판매용", "일반인",
        "롱레인지", "스탠다드"
    }
    extra_suffixes = ["스페셜", "플러스", "PLUS", "스포츠", "베이직", "라이트", "초이스", "어드밴스", "프리미어", "익스트림", "TUIX", "살롱"]

    best_grd_cd = ""
    best_dtl_cd = ""
    best_score = -999

    for grd_nm, g_obj in grd_map.items():
        grd_cd = g_obj["cd"]
        dtl_map = g_obj.get("dtl", {})
        g_norm = _norm(grd_nm)

        g_is_van = ("밴" in g_norm) or ("카고" in g_norm)
        if has_van != g_is_van:
            continue

        g_is_turbo = ("터보" in g_norm) or bool(re.search(r'\d\.\d\s*T(?![A-Z])', grd_nm.upper()))
        if has_both_turbo_and_na and (has_turbo != g_is_turbo):
            continue

        g_seat_m = re.search(r'(\d+)\s*인승', grd_nm)
        g_seat = f"{g_seat_m.group(1)}인승" if g_seat_m else ""
        if target_seat and g_seat and target_seat != g_seat:
            continue

        g_disp_m = re.findall(r'(\d\.\d)', grd_nm)
        g_disp = g_disp_m[0] if g_disp_m else ""
        if target_disp and g_disp and target_disp != g_disp:
            continue

        g_is_lpg = ("LPG" in g_norm) or ("LPI" in g_norm) or ("LPE" in g_norm)
        g_is_diesel = ("디젤" in g_norm) or ("VGT" in g_norm) or ("TDI" in g_norm)
        g_is_gas = ("가솔린" in g_norm) or ("GDI" in g_norm) or ("GDE" in g_norm) or ("GTE" in g_norm) or ("MPI" in g_norm) or ("VVT" in g_norm)

        if has_lpg and not g_is_lpg and (g_is_diesel or g_is_gas):
            continue
        if not has_lpg and g_is_lpg:
            continue
        if has_diesel and g_is_gas:
            continue
        if has_gasoline and g_is_diesel:
            continue
        if not has_gasoline and g_is_gas and any(not ("가솔린" in _norm(k)) for k in grd_map.keys()):
            if has_diesel or any("9인승" in k or "11인승" in k for k in grd_map.keys()):
                continue

        g_is_4wd = ("4WD" in g_norm) or ("AWD" in g_norm)
        g_is_2wd = ("2WD" in g_norm)
        if has_4wd and g_is_2wd:
            continue
        if has_2wd and g_is_4wd:
            continue
        if not has_4wd and not has_2wd and (g_is_4wd or g_is_2wd):
            continue

        skip_special = False
        for sp in special_keywords:
            sp_n = _norm(sp)
            if sp_n in g_norm and sp_n not in comb_norm:
                skip_special = True
                break
        if skip_special:
            continue
        if "리무진" in g_norm and "하이리무진" not in g_norm and "리무진" not in comb_norm:
            continue

        score = 0
        if len(grd_map) == 1:
            score += 5
        if target_disp and g_disp == target_disp:
            score += 10
        if target_seat and g_seat == target_seat:
            score += 10
        if has_turbo and g_is_turbo:
            score += 8
        if has_2wd and g_is_2wd:
            score += 6
        if has_4wd and g_is_4wd:
            score += 6
        if has_diesel and g_is_diesel:
            score += 5
        if has_gasoline and g_is_gas:
            score += 5
        if has_lpg and g_is_lpg:
            score += 5
        if "일반" in g_norm:
            score += 2

        grd_tokens = [_norm(t) for t in re.split(r'[\s\(\)\/\-]+', grd_nm) if _norm(t) and _norm(t) not in spec_ignore]
        non_spec_tokens = [t for t in grd_tokens if not re.match(r'^(\d+\.\d+T?|\d+인승|GDI|GDE|GTE|VGT|EVGT|VVT|MPI|LPE|TDI)$', t)]
        if non_spec_tokens:
            if all(t in comb_norm for t in non_spec_tokens):
                bad_suffix = False
                for ex in extra_suffixes:
                    if ex in g_norm and ex not in comb_norm:
                        bad_suffix = True
                        break
                if bad_suffix:
                    continue
                score += 20 + sum(len(t) for t in non_spec_tokens)
            else:
                continue

        matched_dtl_cd = ""
        dtl_best_len = 0
        if dtl_map:
            for d_nm, d_cd in dtl_map.items():
                d_norm = _norm(d_nm)
                if not d_norm:
                    continue
                if d_norm in comb_norm:
                    if len(d_norm) > dtl_best_len:
                        dtl_best_len = len(d_norm)
                        matched_dtl_cd = d_cd

        total_score = score + (15 + dtl_best_len if matched_dtl_cd else 0)
        if total_score > best_score:
            best_score = total_score
            best_grd_cd = grd_cd
            best_dtl_cd = matched_dtl_cd

    if best_score <= 0 and not best_dtl_cd:
        return "", ""
    return best_grd_cd, best_dtl_cd


def resolve_kcar_model_codes(raw_base_name: str, brand_hint: str = "", sub_model: str = ""):
    """base_name에서 제조사와 모델명을 추출하여 K-Car (mnuftr_cd, model_grp_cd, model_cd) 반환. 매핑 없으면 None."""
    if not raw_base_name or not str(raw_base_name).strip():
        return None

    text = str(raw_base_name).strip()
    detected_mnuftr_cd = ""

    # 1. base_name 앞부분 또는 brand_hint에서 제조사 추출
    for b_name in sorted(KCAR_MNUFTR_MAP.keys(), key=len, reverse=True):
        if text.startswith(b_name):
            detected_mnuftr_cd = KCAR_MNUFTR_MAP[b_name]
            text = text[len(b_name):].strip()
            break
    if not detected_mnuftr_cd and brand_hint and str(brand_hint).strip() != "전체":
        b_hint = str(brand_hint).strip()
        for b_name, m_cd in sorted(KCAR_MNUFTR_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            if b_name in b_hint or b_hint in b_name:
                detected_mnuftr_cd = m_cd
                break

    def _norm(s: str) -> str:
        return re.sub(r'[\s\(\)\-_\/]+', '', str(s)).upper()

    norm_text = _norm(text)
    if not norm_text:
        return None

    sub_norm = _norm(sub_model)
    is_hev_sub = ("HEV" in sub_norm or "하이브리드" in sub_norm) and ("하이브리드" not in norm_text)

    # 2. 괄호 포함 원문 및 괄호 제거 텍스트 기준 최장 일치(Longest Prefix Match) 탐색
    candidates = []
    for (m_cd, grp_cd), models_dict in KCAR_MODEL_GROUP_MAP.items():
        if detected_mnuftr_cd and m_cd != detected_mnuftr_cd:
            continue
        for m_name, mod_cd in models_dict.items():
            # '하이브리드 4세대' 단독 키는 원문에 '카니발'이 포함된 경우에만 매칭 허용
            if m_name == "하이브리드 4세대" and "카니발" not in raw_base_name:
                continue
            nm = _norm(m_name)
            if nm and (norm_text == nm or norm_text.startswith(nm)):
                candidates.append((len(nm), m_cd, grp_cd, mod_cd))
            elif is_hev_sub and "하이브리드" in nm:
                nm_no_hev = nm.replace("하이브리드", "")
                if nm_no_hev and (norm_text == nm_no_hev or norm_text.startswith(nm_no_hev)):
                    candidates.append((len(nm) + 10, m_cd, grp_cd, mod_cd))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        _, m_cd, grp_cd, mod_cd = candidates[0]
        return m_cd, grp_cd, mod_cd

    return None


def encrypt_kcar_payload(data: dict) -> str:
    """K-Car 공식 API용 AES-128-CBC PKCS7 암호화 (Base64 인코딩)"""
    filtered = {k: v for k, v in data.items() if v is not None and v != ""}
    raw_str = json.dumps(filtered, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(raw_str) + padder.finalize()
    cipher = Cipher(algorithms.AES(KEY), modes.CBC(IV))
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(ct).decode('utf-8')


def build_kcar_web_url(car_name: str, year: int = 0, detail_model: str = "", mileage: int = 0, manufacturer: str = "") -> str:
    """K-Car 공식 웹사이트 직영차 검색 바로가기 URL 동적 생성"""
    codes = resolve_kcar_model_codes(car_name, brand_hint=manufacturer, sub_model=detail_model)
    cond: Dict[str, Any] = {}
    if codes:
        cond["wr_eq_mnuftr_cd"] = codes[0]
        cond["wr_eq_model_grp_cd"] = codes[1]
        cond["wr_eq_model_cd"] = codes[2]
    elif car_name:
        cond["wr_txt_idx"] = car_name
        cond["wr_in_model_nm"] = car_name

    if year and year > 0:
        k_yr = 2000 + year if year < 100 else year
        cond["wr_gt_mfg_dt"] = f"{k_yr - 1}01"
        cond["wr_lt_mfg_dt"] = f"{k_yr + 1}12"

    if mileage and mileage > 0:
        rounded = round(mileage / 10000) * 10000
        cond["wr_gt_milg"] = max(0, rounded - 30000)
        cond["wr_lt_milg"] = rounded + 30000

    if cond:
        return f"https://www.kcar.com/bc/search?searchCond={urllib.parse.quote(json.dumps(cond))}"
    return "https://www.kcar.com/bc/search"


def fetch_kcar_market_stats(
    car_name: str,
    year: int = 0,
    detail_model: str = "",
    mileage: int = 0,
    manufacturer: str = ""
) -> Dict[str, Any]:
    """
    K-Car 실시간 직영 매물 검색 및 시세 통계 산출
    반환:
      - success: bool
      - count: 총 매물수
      - min, max, avg, median: 가격 통계 (만원 정수)
      - yearStats: 연식별 평균가 및 대수 리스트
      - priceBins: 가격 구간별 대수 및 비율
      - cars: 대표 매물 리스트
      - modelName, searchUrl: 부가 정보
    """
    search_url = build_kcar_web_url(car_name, year, detail_model, mileage, manufacturer)
    empty_res = {
        "success": False,
        "count": 0,
        "min": 0,
        "max": 0,
        "avg": 0,
        "median": 0,
        "yearStats": [],
        "priceBins": [],
        "cars": [],
        "modelName": "",
        "searchUrl": search_url,
        "message": ""
    }

    if not car_name or not str(car_name).strip():
        empty_res["message"] = "차량명이 지정되지 않았습니다."
        return empty_res

    codes = resolve_kcar_model_codes(car_name, brand_hint=manufacturer, sub_model=detail_model)
    if not codes:
        empty_res["message"] = f"K-Car 모델 코드 매핑 없음 ('{car_name}')"
        return empty_res

    m_cd, grp_cd, mod_cd = codes

    # K-Car 직영 검색 API 파라미터 구성 (최대 100대 전수 취득)
    param = {
        "wr_eq_mnuftr_cd": m_cd,
        "wr_eq_model_grp_cd": grp_cd,
        "wr_eq_model_cd": mod_cd,
        "pageno": 1,
        "limit": 100
    }

    enc_val = encrypt_kcar_payload(param)
    req_body = json.dumps({"enc": enc_val}).encode('utf-8')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://www.kcar.com',
        'Referer': 'https://www.kcar.com/'
    }

    try:
        req = urllib.request.Request('https://api.kcar.com/bc/search/list/drct', data=req_body, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=5) as resp:
            data_raw = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        empty_res["message"] = f"K-Car API 통신 오류: {str(e)}"
        return empty_res

    rows = data_raw.get('data', {}).get('rows', [])
    if not rows:
        empty_res["success"] = True
        empty_res["message"] = "현재 판매 중인 K-Car 직영 매물이 없습니다."
        return empty_res

    # 매물 유효 데이터 추출
    valid_cars = []
    prices = []
    for r in rows:
        try:
            prc = int(r.get('prc') or 0)
            if prc <= 0:
                continue
            milg = int(r.get('milg') or 0)
            yr_str = str(r.get('prdcnYr') or '')
            yr_match = re.search(r'(\d{2,4})', yr_str)
            yr_num = 0
            if yr_match:
                parsed_y = int(yr_match.group(1))
                yr_num = parsed_y % 100 if parsed_y > 100 else parsed_y

            car_cd = r.get('carCd') or ''
            valid_cars.append({
                "carCd": car_cd,
                "carName": r.get('carWhlNm') or r.get('modelNm') or '',
                "price": prc,
                "mileage": milg,
                "year": yr_num,
                "fullYear": yr_str,
                "grade": r.get('grdNm') or '',
                "gradeDetail": r.get('grdDtlNm') or '',
                "center": r.get('cntrNm') or '',
                "color": r.get('extrColorNm') or '',
                "accident": r.get('acdtHistCnts') or '무사고',
                "detailUrl": f"https://www.kcar.com/bc/detail/carInfoPrsn?i_sCarCd={car_cd}" if car_cd else ""
            })
            prices.append(prc)
        except Exception:
            continue

    if not prices:
        empty_res["success"] = True
        empty_res["message"] = "유효한 가격의 직영 매물이 없습니다."
        return empty_res

    prices.sort()
    count = len(prices)
    min_p = prices[0]
    max_p = prices[-1]
    avg_p = int(sum(prices) / count)
    mid_idx = count // 2
    median_p = round((prices[mid_idx - 1] + prices[mid_idx]) / 2) if count % 2 == 0 else prices[mid_idx]

    # 타겟 연식 계산
    target_yr = 0
    if year and year > 0:
        target_yr = year % 100 if year > 100 else year

    # 연식별 통계 (yearStats)
    year_map: Dict[int, Dict[str, int]] = {}
    for c in valid_cars:
        y = c["year"]
        if y <= 0:
            continue
        if y not in year_map:
            year_map[y] = {"count": 0, "sum": 0}
        year_map[y]["count"] += 1
        year_map[y]["sum"] += c["price"]

    sorted_years = sorted(year_map.keys(), reverse=True)
    year_stats = []
    for y in sorted_years:
        cnt = year_map[y]["count"]
        s = year_map[y]["sum"]
        year_stats.append({
            "year": y,
            "avg": int(s / cnt),
            "count": cnt,
            "isTarget": (y == target_yr) if target_yr > 0 else False
        })

    # 가격 분포 구간 (priceBins) - 균등 4개 구간 산출
    price_bins = []
    if count >= 3 and max_p > min_p:
        span = max_p - min_p
        raw_bin_step = span / 4
        bin_step = max(50, round(raw_bin_step / 50) * 50)
        curr = min_p
        for i in range(4):
            is_last = (i == 3)
            next_limit = max_p + 1 if is_last else curr + bin_step
            b_cnt = sum(1 for p in prices if (curr <= p <= max_p if is_last else curr <= p < next_limit))
            ratio = round((b_cnt / count) * 100) if count > 0 else 0
            label = f"{curr:,}~{max_p:,}만" if is_last else f"{curr:,}~{next_limit:,}만"
            price_bins.append({
                "label": label,
                "min": curr,
                "max": max_p if is_last else next_limit,
                "count": b_cnt,
                "ratio": ratio
            })
            curr = next_limit
            if curr > max_p:
                break
    elif count > 0:
        price_bins.append({
            "label": f"{min_p:,}~{max_p:,}만",
            "min": min_p,
            "max": max_p,
            "count": count,
            "ratio": 100
        })

    # 차량 정렬 (가격 오름차순, 최대 20대)
    valid_cars.sort(key=lambda x: x["price"])

    return {
        "success": True,
        "count": count,
        "min": min_p,
        "max": max_p,
        "avg": avg_p,
        "median": median_p,
        "yearStats": year_stats,
        "priceBins": price_bins,
        "cars": valid_cars[:20],
        "modelName": rows[0].get('modelNm') or '',
        "searchUrl": search_url,
        "message": ""
    }
