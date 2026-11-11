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
from typing import Optional, Any

# 전역 옵션 별칭 사전 (11-03-50): 원천(헤이딜러/차얼마/엔카) 옵션 표기 -> 카탈로그 공식 표기.
# 키는 실제 원문 문자열과 띄어쓰기까지 정확히 일치해야 한다.
# 주의: normalize_opt_name은 차명 매칭에도 쓰이므로 이 별칭은 거기에 넣지 않고,
#       옵션 매칭 함수(get_catalog_option_detail, find_official_catalog_option)에서만 적용한다.
OPTION_ALIAS_MAP = {
    "스타일 (7인승)": "스타일",
    "스타일(7인승)": "스타일",
    "12.3인치 UVO 내비게이션": "12.3인치 내비게이션",
    "12.3인치 KGM 링크 내비게이션 패키지": "12.3인치 KGM링크 내비게이션 패키지",
    "14인치 알로이 휠": "14인치 알로이휠",
    "16인치 휠 + 전자식 파킹 브레이크": "16인치 휠+ 전자식 파킹 브레이크",
    "4단자동변속기 & 후드인슐레이션": "4단자동변속기 & 후드 인슐레이션",
    "4단자동변속기& 후드인슐레이션": "4단자동변속기 & 후드 인슐레이션",
    "7인치 디스플레이 오디오": "7인치 디스플레이오디오",
    "7인치 컬러디스플레이 최고급 오디오 & 후방카메라": "7인치 컬러 디스플레이 최고급 오디오&후방카메라",
    "8인치 내비게이션 패키지 Ⅲ": "8인치 내비게이션 패키지Ⅲ",
    "8인치 내비게이션 패키지Ⅱ": "8인치 내비게이션 패키지 Ⅱ",
    "9.2인치 HD 스마트 미러링 내비게이션": "9.2인치 HD스마트 미러링 내비게이션",
    "EASY CONNECT 1.2 패키지Ⅱ": "EASY CONNECT 1.2 패키지 II",
    "EASY LIFE 인포테인먼트 팩 Ⅲ": "EASY LIFE 인포테인먼트 팩Ⅲ",
    "ECM 룸미러+톨게이트 자동결제 시스템(ETCS)": "ECM 룸미러 + 톨게이트 자동 결제 시스템(ETCS)",
    "ECM 룸미러+톨게이트자동 결제 시스템(ETCS)": "ECM 룸미러 + 톨게이트 자동 결제 시스템(ETCS)",
    "ECM룸미러 & 톨게이트 자동결제시스템(ETCS)": "ECM룸미러 & 톨게이트 자동결제시스템 (ETCS)",
    "ECM룸미러 & 톨게이트\u00a0자동결제시스템(ETCS)": "ECM룸미러 & 톨게이트 자동결제시스템 (ETCS)",
    "HUD + 빌트인캠 2": "HUD + 빌트인 캠 2",
    "HUD팩": "HUD 팩",
    "JBL사운드 패키지": "JBL 사운드 패키지",
    "LED 라이팅 패키지 Ⅰ": "LED 라이팅 패키지Ⅰ",
    "LED 라이팅 패키지 Ⅱ": "LED 라이팅 패키지Ⅱ",
    "LED 라이팅 패키지 Ⅲ": "LED 라이팅 패키지Ⅲ",
    "MP3 CDP&블루투스": "MP3 CDP & 블루투스",
    "My 스마트 Fit\u00a0베이직": "My 스마트 Fit 베이직",
    "My 컨비니언스 Fit\u00a0베이직": "My 컨비니언스 Fit 베이직",
    "N Line 디자인 패키지\u00a0Ⅲ": "N Line 디자인 패키지Ⅲ",
    "N Line 디자인 패키지\u00a0Ⅳ": "N Line 디자인 패키지Ⅳ",
    "TUIX 블랙 포인트Ⅰ": "TUIX 블랙 포인트 Ⅰ",
    "TUIX 블랙 포인트Ⅱ": "TUIX 블랙 포인트 Ⅱ",
    "내비게이션 패키지1": "내비게이션 패키지 1",
    "내비게이션 패키지2": "내비게이션 패키지 2",
    "내비게이션 패키지3": "내비게이션 패키지 3",
    "내비게이션 팩(제스쳐 UI 기능 포함)": "내비게이션 팩 (제스쳐 UI 기능 포함)",
    "내비게이션+ 사운드 시스템 & 세이프티팩": "내비게이션 + 사운드 시스템 & 세이프티팩",
    "내비게이션+ 사운드 시스템팩": "내비게이션 + 사운드 시스템팩",
    "내비게이션+사운드 시스템 & 세이프티팩": "내비게이션 + 사운드 시스템 & 세이프티팩",
    "내비게이션\u00a0II": "내비게이션 II",
    "내비게이션Ⅱ": "내비게이션 II",
    "드라이브 어시스트\u00a0패키지": "드라이브 어시스트 패키지",
    "드라이브 와이즈 2": "드라이브 와이즈2",
    "드라이빙 어시스트 패키지 Ⅰ": "드라이빙 어시스트 패키지Ⅰ",
    "디스플레이 오디오 패키지 Ⅱ": "디스플레이 오디오 패키지Ⅱ",
    "디자인 플러스 Ⅰ": "디자인 플러스Ⅰ",
    "디자인 플러스 Ⅱ": "디자인 플러스Ⅱ",
    "디자인 플러스 Ⅲ": "디자인 플러스Ⅲ",
    "딥 컨트롤 패키지 Ⅰ": "딥 컨트롤 패키지Ⅰ",
    "라이팅 패키지 Ⅰ": "라이팅 패키지Ⅰ",
    "레드가죽시트 패키지": "레드 가죽 시트 패키지",
    "레이디 케어A": "레이디 케어 A",
    "레이디 케어B": "레이디 케어 B",
    "렉시콘팩": "렉시콘 팩",
    "마이링크(후방카메라 포함)": "마이링크 (후방카메라 포함)",
    "멀티미디어 내비\u00a0Ⅱ": "멀티미디어 내비Ⅱ",
    "멀티미디어 내비플러스": "멀티미디어 내비 플러스",
    "멀티미디어 내비플러스\u00a0Ⅱ": "멀티미디어 내비플러스Ⅱ",
    "모니터링팩": "모니터링 팩",
    "모던 초이스\u00a0II": "모던 초이스 II",
    "미드나잇 패키지Ⅰ": "미드나잇 패키지 I",
    "버튼시동 스마트키시스템": "버튼시동 스마트키 시스템",
    "베스트 셀렉션 Ⅳ(HEV)": "베스트 셀렉션Ⅳ(HEV)",
    "블랙핏": "블랙 핏",
    "블루링크 패키지Ⅱ": "블루링크 패키지 Ⅱ",
    "빌트인 캠 2  플러스": "빌트인 캠 2 플러스",
    "세이프티 패키지Ⅰ": "세이프티 패키지 Ⅰ",
    "세이프티 패키지Ⅱ": "세이프티 패키지 Ⅱ",
    "셀렉티브 슬림 패키지 Ⅱ": "셀렉티브 슬림 패키지 II",
    "셀렉티브 슬림 패키지Ⅰ": "셀렉티브 슬림 패키지 I",
    "셀렉티브 슬림 패키지Ⅱ": "셀렉티브 슬림 패키지 II",
    "셀렉티브 패키지 Ⅱ": "셀렉티브 패키지 II",
    "셀렉티브 패키지Ⅰ": "셀렉티브 패키지 I",
    "셀렉티브 패키지Ⅱ": "셀렉티브 패키지 II",
    "쉐보레 인포테인먼트 시스템(후방카메라 포함)": "쉐보레 인포테인먼트 시스템 (후방카메라 포함)",
    "스마트 드라이빙 패키지": "스마트드라이빙 패키지",
    "스마트 초이스 Ⅰ": "스마트 초이스Ⅰ",
    "스마트 초이스\u00a0Ⅲ": "스마트 초이스Ⅲ",
    "스마트 패키지Ⅱ": "스마트 패키지 Ⅱ",
    "스마트 패키지Ⅲ": "스마트 패키지 Ⅲ",
    "스마트 패키지Ⅳ": "스마트 패키지 Ⅳ",
    "스마트초이스": "스마트 초이스",
    "스마트커넥트": "스마트 커넥트",
    "스타일 Ⅱ": "스타일 I I",
    "스타일 업 패키지 Ⅰ": "스타일 업 패키지Ⅰ",
    "스타일 업 패키지 Ⅱ": "스타일 업 패키지Ⅱ",
    "스타일 업 패키지 Ⅲ": "스타일 업 패키지Ⅲ",
    "스타일 케어Ⅲ": "스타일 케어 Ⅲ",
    "스타일 패키지Ⅱ": "스타일 패키지 II",
    "스타일 패키지Ⅳ": "스타일 패키지 Ⅳ",
    "시그니처 패키지 Ⅲ": "시그니처 패키지 III",
    "시에나 브라운 가죽시트 패키지": "시에나 브라운 가죽 시트 패키지",
    "시트 컴포트 Ⅰ": "시트 컴포트Ⅰ",
    "시트 컴포트 Ⅱ": "시트 컴포트Ⅱ",
    "시트 패키지 Ⅱ": "시트 패키지Ⅱ",
    "시트 패키지 Ⅲ": "시트 패키지Ⅲ",
    "시트 플러스 I": "시트 플러스Ⅰ",
    "시트 플러스 Ⅰ": "시트 플러스Ⅰ",
    "시트 플러스\u00a0Ⅱ": "시트 플러스Ⅱ",
    "시트플러스 Ⅰ": "시트플러스Ⅰ",
    "시트플러스 Ⅱ": "시트플러스Ⅱ",
    "시트플러스\u00a0Ⅱ": "시트플러스Ⅱ",
    "열선패키지": "열선 패키지",
    "올시즌 케어A": "올시즌 케어 A",
    "올시즌 케어B": "올시즌 케어 B",
    "원터치 세이프티 전동썬루프": "원터치 세이프티 전동 썬루프",
    "원터치 세이프티\u00a0전동 선루프": "원터치 세이프티 전동 선루프",
    "익스테리어 Ⅰ": "익스테리어Ⅰ",
    "익스테리어 디자인 Ⅲ": "익스테리어 디자인Ⅲ",
    "익스테리어 디자인\u00a0Ⅲ": "익스테리어 디자인Ⅲ",
    "익스테리어 패키지Ⅰ": "익스테리어 패키지 I",
    "익스테리어 패키지Ⅱ": "익스테리어 패키지 II",
    "익스테리어\u00a0Ⅱ": "익스테리어Ⅱ",
    "익스테리어\u00a0Ⅲ": "익스테리어Ⅲ",
    "인테리어 디자인 Ⅰ": "인테리어 디자인Ⅰ",
    "인테리어 디자인\u00a0Ⅱ": "인테리어 디자인Ⅱ",
    "인포테인먼트 내비 Ⅱ": "인포테인먼트 내비 II",
    "인포테인먼트 내비\u00a0II": "인포테인먼트 내비 II",
    "인포테인먼트 내비Ⅰ": "인포테인먼트 내비 I",
    "인포테인먼트 패키지 I": "인포테인먼트 패키지Ⅰ",
    "인포테인먼트 패키지 II": "인포테인먼트 패키지Ⅱ",
    "인포테인먼트\u00a0라이트": "인포테인먼트 라이트",
    "인포테인먼트\u00a0패키지": "인포테인먼트 패키지",
    "인피니티 프리미엄 사운드시스템": "인피니티 프리미엄 사운드 시스템",
    "전자식 4WD시스템": "전자식 4WD 시스템",
    "주차보조 시스템 Ⅰ": "주차보조 시스템Ⅰ",
    "주차보조 시스템\u00a0Ⅱ": "주차보조 시스템Ⅱ",
    "주차조향 보조 시스템": "주차조향보조시스템",
    "주행 보조 패키지 IV": "주행 보조 패키지IV",
    "주행 보조 패키지\u00a0V": "주행 보조 패키지 V",
    "주행보조 패키지 C": "주행보조패키지 C",
    "캠핑 패키지 Ⅰ": "캠핑 패키지Ⅰ",
    "커튼 에어백": "커튼에어백",
    "컨비니언스 패키지 Ⅱ": "컨비니언스 패키지Ⅱ",
    "컨비니언스 패키지 Ⅲ": "컨비니언스 패키지Ⅲ",
    "컨비니언스 패키지1": "컨비니언스 패키지 1",
    "컨비니언스 패키지2": "컨비니언스 패키지 2",
    "컨비니언스3": "컨비니언스 3",
    "컴포트 Ⅲ": "컴포트Ⅲ",
    "컴포트 패키지 Ⅳ": "컴포트 패키지Ⅳ",
    "컴포트 패키지\u00a0II": "컴포트 패키지 II",
    "컴포트 패키지Ⅰ": "컴포트 패키지 I",
    "컴포트 패키지Ⅱ": "컴포트 패키지 II",
    "컴포트 패키지Ⅲ": "컴포트 패키지 III",
    "컴포트 플러스Ⅱ": "컴포트 플러스 II",
    "컴포트(7인승)": "컴포트",
    "컴포트\u00a0III (뒷좌석 편의)": "컴포트 III (뒷좌석 편의)",
    "컴포트\u00a0Ⅲ(뒷좌석 편의)": "컴포트Ⅲ(뒷좌석 편의)",
    "테크 Ⅰ": "테크 I",
    "파킹 어시스트 Ⅱ(HEV)": "파킹 어시스트Ⅱ(HEV)",
    "파킹 어시스트 Ⅳ(HEV)": "파킹 어시스트Ⅳ(HEV)",
    "파킹 어시스트 플러스 Ⅰ": "파킹 어시스트 플러스Ⅰ",
    "파킹 어시스트 플러스 Ⅱ": "파킹 어시스트 플러스Ⅱ",
    "파킹 어시스트 플러스\u00a0Ⅱ": "파킹 어시스트 플러스Ⅱ",
    "파킹 어시스트 플러스\u00a0Ⅲ": "파킹 어시스트 플러스Ⅲ",
    "파킹 어시스트\u00a0Ⅳ(HEV)": "파킹 어시스트Ⅳ(HEV)",
    "패밀리 II": "패밀리Ⅱ",
    "프리미엄 1": "프리미엄1",
    "프리미엄 2": "프리미엄2",
    "프리미엄 가죽시트 패키지Ⅱ": "프리미엄 가죽 시트 패키지Ⅱ",
    "프리미엄 가죽시트 패키지Ⅲ": "프리미엄 가죽 시트 패키지Ⅲ",
    "프리미엄 시트 Ⅰ": "프리미엄 시트Ⅰ",
    "프리미엄 시트 Ⅱ": "프리미엄 시트Ⅱ",
    "프리미엄 시트 패키지 III": "프리미엄 시트 패키지Ⅲ",
    "프리미엄 시트 패키지 Ⅱ": "프리미엄 시트 패키지Ⅱ",
    "프리미엄 패키지Ⅱ": "프리미엄 패키지 Ⅱ",
    "프리미엄 팩2": "프리미엄 팩 2",
    "프리미엄컬렉션": "프리미엄 컬렉션",
    "플래티넘 Ⅱ": "플래티넘Ⅱ",
    "플래티넘 Ⅲ": "플래티넘Ⅲ",
    "플래티넘 Ⅳ": "플래티넘Ⅳ",
    "플래티넘 에디션 Ⅰ": "플래티넘 에디션Ⅰ",
    "플래티넘 에디션 Ⅱ": "플래티넘 에디션Ⅱ",
    "플러스 패키지 I": "플러스 패키지Ⅰ",
    "플러스 패키지 II": "플러스 패키지Ⅱ",
    "플러스 패키지 III": "플러스 패키지Ⅲ",
    "현대 스마트센스 I": "현대 스마트 센스Ⅰ",
    "현대 스마트센스 Ⅲ": "현대 스마트센스Ⅲ",
    "현대 스마트센스 패키지 Ⅰ": "현대 스마트 센스 패키지Ⅰ",
    "현대 스마트센스 패키지 Ⅳ": "현대 스마트센스 패키지 IV",
    "현대 스마트센스 패키지Ⅰ": "현대 스마트 센스 패키지 Ⅰ",
    "현대 스마트센스\u00a0Ⅳ": "현대 스마트센스 Ⅳ",
    "현대 스마트센스Ⅱ": "현대 스마트센스 II",
    "현대\u00a0스마트센스 패키지 II": "현대 스마트센스 패키지 II",
    "현대\u00a0스마트센스 패키지 III": "현대 스마트센스 패키지 III",
    "현대스마트 센스 ll": "현대 스마트 센스 ll",
    "현대스마트센스 MT": "현대 스마트센스 MT",
    "히팅패키지": "히팅 패키지",
}

# [11-06-75] 커스터마이징 액세서리 약칭/별칭 사전 (엔카·케이카 매물 약칭 -> 카탈로그 공식 액세서리명)
ACCESSORY_ALIAS_MAP = {
    # 트레일러 패키지 변형
    "트레일러21": "트레일러 패키지(21인치 휠)",
    "트레일러 21": "트레일러 패키지(21인치 휠)",
    "트레일러패키지21": "트레일러 패키지(21인치 휠)",
    "트레일러 패키지 21": "트레일러 패키지(21인치 휠)",
    "트레일러패키지(21인치)": "트레일러 패키지(21인치 휠)",
    "트레일러패키지(21인치휠)": "트레일러 패키지(21인치 휠)",
    "트레일러 패키지(21인치)": "트레일러 패키지(21인치 휠)",
    "트레일러19": "트레일러 패키지(19인치 휠)",
    "트레일러 19": "트레일러 패키지(19인치 휠)",
    "트레일러패키지19": "트레일러 패키지(19인치 휠)",
    "트레일러 패키지 19": "트레일러 패키지(19인치 휠)",
    "트레일러패키지(19인치)": "트레일러 패키지(19인치 휠)",
    "트레일러패키지(19인치휠)": "트레일러 패키지(19인치 휠)",
    "트레일러 패키지(19인치)": "트레일러 패키지(19인치 휠)",
    "트레일러": "트레일러 패키지",
    "토우히치": "트레일러 패키지",
    "토우 히치": "트레일러 패키지",
    # 라운지 패키지
    "라운지": "라운지 패키지",
    "라운지패키지": "라운지 패키지",
    # 사이드 스텝
    "사이드스텝": "사이드 스텝",
    "고정식사이드스텝": "사이드 스텝",
    "고정식 사이드 스텝": "사이드 스텝",
    "전동식사이드스텝": "전동식 사이드 스텝",
    "전동식 사이드스텝": "전동식 사이드 스텝",
    # 캠핑 패키지
    "캠핑": "캠핑 패키지",
    "캠핑패키지": "캠핑 패키지",
    # 공기청정기
    "공기청정기": "빌트인 공기청정기",
    "빌트인공기청정기": "빌트인 공기청정기",
    # 러기지
    "러기지패키지": "러기지 패키지",
    "러기지매트": "리버서블 러기지 매트",
    "리버서블러기지매트": "리버서블 러기지 매트",
    "리버서블 러기지매트": "리버서블 러기지 매트",
    # 차량보호필름
    "차량보호필름": "차량 보호 필름",
    "차량 보호필름": "차량 보호 필름",
    "차량보호필름1": "차량 보호 필름 I",
    "차량보호필름2": "차량 보호 필름 II",
    "차량보호필름 1": "차량 보호 필름 I",
    "차량보호필름 2": "차량 보호 필름 II",
    "차량보호필름I": "차량 보호 필름 I",
    "차량보호필름II": "차량 보호 필름 II",
    # 후석 스마트 엔터테인먼트
    "후석엔터테인먼트": "후석 스마트 엔터테인먼트 시스템",
    "후석스마트엔터테인먼트": "후석 스마트 엔터테인먼트 시스템",
    "후석 엔터테인먼트": "후석 스마트 엔터테인먼트 시스템",
    "후석 스마트 엔터테인먼트": "후석 스마트 엔터테인먼트 시스템",
    "후석엔터": "후석 스마트 엔터테인먼트 시스템",
    "스마트엔터테인먼트": "후석 스마트 엔터테인먼트 시스템",
}
OPTION_ALIAS_MAP.update(ACCESSORY_ALIAS_MAP)

# 전역 모델 별칭 사전 (11-03-51): 표시명(차얼마/헤이딜러 등 외부 차명) -> 카탈로그 공식 키.
# 공용 메커니즘(차종 전용 분기 아님). 새 차 표시명은 항목으로만 추가한다.
MODEL_ALIAS_MAP = {
    "신형 카니발(KA4)": "카니발 4세대",
    "G80 F/L": "더 뉴 G80",
    "G80 FL": "더 뉴 G80",
    "G80 페이스리프트": "더 뉴 G80",
    "G80(RG3) F/L": "더 뉴 G80",
    "G80(RG3) FL": "더 뉴 G80",
    "GV70 F/L": "더 뉴 GV70",
    "GV70 FL": "더 뉴 GV70",
    "GV70 페이스리프트": "더 뉴 GV70",
    "GV70(JK1) F/L": "더 뉴 GV70",
    "GV70(JK1) FL": "더 뉴 GV70",
    "GV80 F/L": "더 뉴 GV80",
    "GV80 FL": "더 뉴 GV80",
    "GV80 페이스리프트": "더 뉴 GV80",
    "GV80(JX1) F/L": "더 뉴 GV80",
    "GV80(JX1) FL": "더 뉴 GV80",
    "K5 F/L": "더 뉴 K5 3세대",
    "K5 FL": "더 뉴 K5 3세대",
    "K5 페이스리프트": "더 뉴 K5 3세대",
    "K5(DL3)": "K5 3세대",
    "K5(DL3) F/L": "더 뉴 K5 3세대",
    "K5(DL3) FL": "더 뉴 K5 3세대",
    "K8 F/L": "더 뉴 K8",
    "K8 FL": "더 뉴 K8",
    "K8 페이스리프트": "더 뉴 K8",
    "그랜저(HG)": "그랜저 HG",
    "그랜저(IG)": "그랜저 IG",
    "그랜저(IG) F/L": "더 뉴 그랜저",
    "그랜저(IG) FL": "더 뉴 그랜저",
    "그랜저(IG) 페이스리프트": "더 뉴 그랜저",
    "더 뉴 K5 F/L": "더 뉴 K5 3세대",
    "더 뉴 K5 FL": "더 뉴 K5 3세대",
    "더 뉴 K5(DL3)": "더 뉴 K5 3세대",
    "더 뉴 쏘렌토 F/L": "더 뉴 쏘렌토 4세대",
    "더 뉴 쏘렌토 FL": "더 뉴 쏘렌토 4세대",
    "더 뉴 쏘렌토(MQ4)": "더 뉴 쏘렌토 4세대",
    "더 뉴 카니발(KA4)": "더 뉴 카니발 4세대",
    "더 뉴K5(DL3)": "더 뉴 K5 3세대",
    "더 뉴쏘렌토(MQ4)": "더 뉴 쏘렌토 4세대",
    "더 뉴카니발(KA4)": "더 뉴 카니발 4세대",
    "스포티지 F/L": "더 뉴 스포티지 5세대",
    "스포티지 FL": "더 뉴 스포티지 5세대",
    "스포티지 페이스리프트": "더 뉴 스포티지 5세대",
    "스포티지(NQ5)": "스포티지 5세대",
    "스포티지(NQ5) F/L": "더 뉴 스포티지 5세대",
    "스포티지(NQ5) FL": "더 뉴 스포티지 5세대",
    "신형 K5 하이브리드": "K5 하이브리드",
    "신형 K5(DL3)": "K5 3세대",
    "신형 쏘렌토 (MQ4)": "쏘렌토 4세대",
    "쏘렌토 F/L": "더 뉴 쏘렌토 4세대",
    "쏘렌토 FL": "더 뉴 쏘렌토 4세대",
    "쏘렌토 페이스리프트": "더 뉴 쏘렌토 4세대",
    "쏘렌토(MQ4)": "쏘렌토 4세대",
    "쏘렌토(MQ4) F/L": "더 뉴 쏘렌토 4세대",
    "쏘렌토(MQ4) FL": "더 뉴 쏘렌토 4세대",
    "아반떼 F/L": "더 뉴 아반떼 (CN7)",
    "아반떼 FL": "더 뉴 아반떼 (CN7)",
    "아반떼 페이스리프트": "더 뉴 아반떼 (CN7)",
    "아반떼(CN7) F/L": "더 뉴 아반떼 (CN7)",
    "아반떼(CN7) FL": "더 뉴 아반떼 (CN7)",
    "카니발 F/L": "더 뉴 카니발 4세대",
    "카니발 FL": "더 뉴 카니발 4세대",
    "카니발 페이스리프트": "더 뉴 카니발 4세대",
    "카니발(KA4)": "카니발 4세대",
    "카니발(KA4) F/L": "더 뉴 카니발 4세대",
    "카니발(KA4) FL": "더 뉴 카니발 4세대",
    "투싼 F/L": "더 뉴 투싼",
    "투싼 FL": "더 뉴 투싼",
    "투싼 페이스리프트": "더 뉴 투싼",
    "투싼(NX4) F/L": "더 뉴 투싼",
    "투싼(NX4) FL": "더 뉴 투싼",
    "팰리세이드 F/L": "더 뉴 팰리세이드",
    "팰리세이드 FL": "더 뉴 팰리세이드",
    "팰리세이드 페이스리프트": "더 뉴 팰리세이드",
    "팰리세이드(LX2) F/L": "더 뉴 팰리세이드",
    "팰리세이드(LX2) FL": "더 뉴 팰리세이드",
}

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
        "id": "chevy_safety_2",
        "aliases": ["세이프티패키지ii", "세이프티패키지2", "세이프티2", "세이프티ii", "safety2", "safetyii", "세이프티패키지", "세이프티팩"],
        "name": "세이프티 패키지 II",
        "brand": "쉐보레",
        "description": "사각지대 경고시스템(SBZA), 후측방 경고시스템(RCTA), 전방충돌 경고시스템(RLAD/FCA), 차선이탈 경고시스템(LDWS)",
        "items": ["사각지대 경고시스템", "후측방 경고시스템", "전방충돌 경고시스템", "차선이탈 경고시스템"],
        "match_keywords": ["사각지대", "후측방", "전방충돌", "차선이탈", "sbza", "rcta", "ldws", "fcw", "rlad", "세이프티"],
        "min_matches": 1
    },
    {
        "id": "chevy_safety_1",
        "aliases": ["세이프티패키지i", "세이프티패키지1", "세이프티1", "세이프티i", "safety1", "safetyi"],
        "name": "세이프티 패키지 I",
        "brand": "쉐보레",
        "description": "사각지대 경고시스템(SBZA), 후측방 경고시스템(RCTA)",
        "items": ["사각지대 경고시스템", "후측방 경고시스템"],
        "match_keywords": ["사각지대", "후측방", "sbza", "rcta", "세이프티"],
        "min_matches": 1
    },
    {
        "id": "chevy_mylink_safety",
        "aliases": ["마이링크&세이프티패키지", "마이링크세이프티패키지", "마이링크세이프티", "쉐보레인포테인먼트시스템&세이프티패키지"],
        "name": "마이링크 & 세이프티 패키지",
        "brand": "쉐보레",
        "description": "마이링크/인포테인먼트, 후방카메라, 사각지대 경고시스템(SBZA), 후측방 경고시스템(RCTA)",
        "items": ["마이링크", "후방카메라", "사각지대 경고시스템", "후측방 경고시스템"],
        "match_keywords": ["마이링크", "후방카메라", "사각지대", "후측방", "sbza", "rcta", "세이프티"],
        "min_matches": 1
    },
    {
        "id": "chevy_style",
        "aliases": ["스타일패키지", "스타일팩"],
        "name": "스타일 패키지",
        "brand": "쉐보레",
        "description": "프로젝션 헤드램프, LED DRL & 포지셔닝 램프, 듀얼 시그니처 LED 테일램프, 18인치 알로이 휠",
        "items": ["프로젝션 헤드램프", "LED DRL", "LED 테일램프", "18인치 알로이 휠"],
        "match_keywords": ["스타일", "led", "헤드램프", "알로이휠"],
        "min_matches": 1
    },
    {
        "id": "chevy_drive_assist",
        "aliases": ["드라이브어시스트패키지", "드라이빙어시스트", "쉐보레세이프티"],
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
        "aliases": ["현대스마트센스", "스마트센스", "스마트센스1", "스마트센스2", "스마트센스3", "스마트센스i", "스마트센스ii", "스마트센스iii", "스마트센스ⅰ", "스마트센스ⅱ", "스마트센스ⅲ"],
        "name": "현대 스마트센스",
        "brand": "현대",
        "description": "전방 충돌방지 보조(FCA), 스마트 크루즈 컨트롤(Stop & Go), 고속도로 주행 보조(HDA), 후측방 충돌방지 보조, 차로 이탈방지 보조(LKA), 안전 하차 보조",
        "items": ["스마트 크루즈 컨트롤", "전방 충돌방지 보조", "고속도로 주행 보조(HDA)", "후측방 충돌방지 보조", "안전 하차 보조"],
        "match_keywords": ["스마트크루즈", "크루즈", "ascc", "scc", "hda", "후측방", "차로유지", "차선유지", "전방충돌", "차선이탈", "차로이탈", "충돌방지", "충돌경고", "fca", "lka", "주행보조", "스마트센스"],
        "min_matches": 1
    },
    {
        "id": "hyundai_multimedia_navi_plus_2",
        "aliases": ["멀티미디어내비플러스ii", "멀티미디어내비플러스2", "멀티미디어내비ii", "멀티미디어내비2", "멀티미디어내비플러스ⅱ"],
        "name": "멀티미디어 내비 플러스 II",
        "brand": "현대",
        "description": "10.25인치/8인치 내비게이션, 후방 모니터, 풀오토 에어컨, 공기청정 모드",
        "items": ["10.25인치 내비게이션", "후방 모니터", "풀오토 에어컨"],
        "match_keywords": ["내비게이션", "네비게이션", "내비", "네비", "후방카메라", "후방모니터", "풀오토에어컨", "멀티미디어"],
        "min_matches": 1
    },
    {
        "id": "hyundai_multimedia_navi_plus_1",
        "aliases": ["멀티미디어내비플러스i", "멀티미디어내비플러스1", "멀티미디어내비i", "멀티미디어내비1", "멀티미디어내비플러스", "내비플러스", "멀티미디어내비플러스ⅰ"],
        "name": "멀티미디어 내비 플러스 I",
        "brand": "현대",
        "description": "8인치 디스플레이 오디오/내비게이션, 후방 모니터, 샤크핀 안테나",
        "items": ["8인치 내비게이션", "후방 모니터"],
        "match_keywords": ["내비게이션", "네비게이션", "내비", "네비", "후방카메라", "후방모니터", "멀티미디어"],
        "min_matches": 1
    },
    {
        "id": "hyundai_navi_package",
        "aliases": ["내비게이션패키지", "네비게이션패키지", "내비패키지", "스마트내비게이션", "8인치내비게이션", "10.25인치내비게이션", "12.3인치내비게이션"],
        "name": "내비게이션 패키지",
        "brand": "현대",
        "description": "정품 내비게이션 시스템, 후방 모니터, 샤크핀 안테나",
        "items": ["내비게이션", "후방카메라"],
        "match_keywords": ["내비게이션", "네비게이션", "내비", "네비", "후방카메라", "후방모니터"],
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
        "id": "kia_multimedia_2",
        "aliases": ["멀티미디어패키지ii", "멀티미디어패키지2", "멀티미디어2", "멀티미디어ii", "멀티미디어패키지", "내비게이션패키지ii", "내비게이션패키지2", "멀티미디어팩2", "멀티미디어팩ii", "멀티미디어패키지ⅱ"],
        "name": "멀티미디어 패키지 II",
        "brand": "기아",
        "description": "8인치 UVO 내비게이션(정품), 후방 모니터(카메라), 샤크핀 안테나, 풀오토 에어컨",
        "items": ["8인치 UVO 내비게이션", "후방 모니터", "풀오토 에어컨", "샤크핀 안테나"],
        "match_keywords": ["내비게이션", "네비게이션", "내비", "네비", "후방카메라", "후방모니터", "풀오토에어컨", "에어컨", "멀티미디어", "uvo"],
        "min_matches": 1
    },
    {
        "id": "kia_multimedia_1",
        "aliases": ["멀티미디어패키지i", "멀티미디어패키지1", "멀티미디어1", "멀티미디어i", "내비게이션패키지i", "내비게이션패키지1", "멀티미디어팩1", "멀티미디어팩i", "멀티미디어패키지ⅰ"],
        "name": "멀티미디어 패키지 I",
        "brand": "기아",
        "description": "7인치/8인치 스마트 내비게이션, 후방 모니터(후방카메라), 샤크핀 안테나",
        "items": ["스마트 내비게이션", "후방 모니터", "샤크핀 안테나"],
        "match_keywords": ["내비게이션", "네비게이션", "내비", "네비", "후방카메라", "후방모니터", "멀티미디어"],
        "min_matches": 1
    },
    {
        "id": "kia_uvo_navi",
        "aliases": ["uvo내비게이션", "uvo내비", "uvo네비", "uvo", "스마트내비게이션"],
        "name": "UVO / 스마트 내비게이션",
        "brand": "기아",
        "description": "정품 내비게이션, UVO 원격제어, 후방 모니터, 샤크핀 안테나",
        "items": ["정품 내비게이션", "후방 모니터"],
        "match_keywords": ["내비게이션", "네비게이션", "내비", "네비", "후방카메라", "uvo"],
        "min_matches": 1
    },
    {
        "id": "kia_drive_wise",
        "aliases": ["드라이브와이즈", "드라이브와이즈1", "드라이브와이즈2", "드라이브와이즈i", "드라이브와이즈ii", "드라이브와이즈ⅰ", "드라이브와이즈ⅱ", "drivewise"],
        "name": "드라이브 와이즈",
        "brand": "기아",
        "description": "전방 충돌방지 보조(FCA), 스마트 크루즈 컨트롤(정차&재출발), 후측방 충돌방지 보조, 차로 이탈방지 보조(LKA), 고속도로 주행 보조(HDA), 안전 하차 보조",
        "items": ["스마트 크루즈 컨트롤", "전방 충돌방지 보조", "차로 이탈방지 보조", "고속도로 주행 보조(HDA)", "후측방 충돌방지", "안전 하차 보조"],
        "match_keywords": ["스마트크루즈", "크루즈", "ascc", "scc", "hda", "후측방", "차로유지", "차선유지", "전방충돌", "차선이탈", "차로이탈", "충돌방지", "충돌경고", "fca", "fcw", "lka", "ldw", "bcw", "주행보조", "사각지대", "드라이브와이즈"],
        "min_matches": 1
    },
    {
        "id": "kia_style",
        "aliases": ["스타일", "스타일패키지", "스타일1", "스타일2", "스타일i", "스타일ii", "스타일ⅰ", "스타일ⅱ", "익스테리어"],
        "name": "스타일 / 익스테리어",
        "brand": "기아",
        "description": "프로젝션 헤드램프, LED DRL, LED 리어콤비네이션 램프, 대구경 알로이 휠",
        "items": ["LED 헤드램프", "LED 테일램프", "알로이 휠"],
        "match_keywords": ["스타일", "led", "헤드램프", "프로젝션", "알로이휠"],
        "min_matches": 1
    },
    {
        "id": "kia_comfort",
        "aliases": ["컴포트", "컴포트1", "컴포트2", "컴포트i", "컴포트ii", "컴포트ⅰ", "컴포트ⅱ", "시트패키지"],
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
    """패키지/옵션 명칭 정규화 (공백, 기호, 괄호, 로마숫자 통일) - 단일 진실 공급원"""
    if not text:
        return ""
    # 1. 유니코드 NFKC 정규화 (전각, 호환 문자 표준화)
    t = unicodedata.normalize('NFKC', str(text))
    # 2. 로마자 특수문자 직접 치환 (유니코드 및 소문자 대응)
    ROMAN_MAP = {
        'Ⅰ': '1', 'Ⅱ': '2', 'Ⅲ': '3', 'Ⅳ': '4', 'Ⅴ': '5',
        'ⅰ': '1', 'ⅱ': '2', 'ⅲ': '3', 'ⅳ': '4', 'ⅴ': '5',
    }
    for r, d in ROMAN_MAP.items():
        t = t.replace(r, d)
    # 3. 괄호 안의 가격 정보 분리 및 규격 식별자(인치, 휠, 인승 등) 보존
    # 3-1. 가격 표기 괄호 우선 분리/제거: (79만), (1,360,000원), [354만] 등
    t = re.sub(r'\([0-9,]+(?:\s*만|\s*원)?\)', '', t)
    t = re.sub(r'\[[0-9,]+(?:\s*만|\s*원)?\]', '', t)

    # 3-2. 괄호 안에 규격 식별자(인치, 휠, 인승, 구동방식 등)가 포함된 경우 알맹이 보존 (11-06-75 근본 구조)
    def _strip_or_preserve_paren(m):
        inner = m.group(1).strip()
        if re.search(r'\d+\s*(?:인치|인승|wd|단|v)|휠|awd|4wd|2wd', inner, re.I):
            return f" {inner} "
        return ""

    sub_t = re.sub(r'\((.*?)\)', _strip_or_preserve_paren, t).strip()
    sub_t = re.sub(r'\[(.*?)\]', _strip_or_preserve_paren, sub_t).strip()
    if sub_t:
        t = sub_t
    else:
        t = t.replace('(', '').replace(')', '').replace('[', '').replace(']', '').strip()
    t = t.lower()
    # 4. 공백 및 특수기호 제거 (앰퍼샌드, 따옴표, 쉼표, 슬래시, 플러스 등 전수 클리닝)
    t = re.sub(r'[\s\-_/·+.&"\'\',]', '', t)
    # 5. 로마숫자 통일 (끝자리 또는 패키지 키워드 뒤: iv->4, iii->3, ii->2, i->1)
    t = re.sub(r'iv$', '4', t)
    t = re.sub(r'iii$', '3', t)
    t = re.sub(r'ii$', '2', t)
    t = re.sub(r'i$', '1', t)
    t = re.sub(r'(패키지|플러스|팩|센스|와이즈|컨트롤|어시스트|액티브|컴포트|셀렉티브|스타일|세이프티)iv', r'\g<1>4', t)
    t = re.sub(r'(패키지|플러스|팩|센스|와이즈|컨트롤|어시스트|액티브|컴포트|셀렉티브|스타일|세이프티)iii', r'\g<1>3', t)
    t = re.sub(r'(패키지|플러스|팩|센스|와이즈|컨트롤|어시스트|액티브|컴포트|셀렉티브|스타일|세이프티)ii', r'\g<1>2', t)
    t = re.sub(r'(패키지|플러스|팩|센스|와이즈|컨트롤|어시스트|액티브|컴포트|셀렉티브|스타일|세이프티)i', r'\g<1>1', t)
    # 6. '패키지', '팩' 접미어 제거
    t = t.replace("패키지", "").replace("팩", "")
    # 7. 음운/표기 변이 공통 표준화 ('썬' -> '선') (11-03-16 제이 규칙)
    t = t.replace("썬", "선")
    return t


# ═══════════════════════════════════════════════════════════════
# 💰 단일 가격 규칙 및 표준 옵션 항목 (OptionItem) 구조
# 규칙: 카탈로그 정가(catalog) -> API 가격(api) -> 미가격(unpriced)
# ═══════════════════════════════════════════════════════════════

def _find_in_v2_options(v2_options: dict, clean: str) -> Optional[tuple]:
    """
    V2 카탈로그 옵션 매칭 헬퍼:
    1. 직접 일치 (exact)
    2. 별칭 사전 적용 후 직접/정규화 일치 (exact)
    3. 정규화 완전 일치 (exact)
    4. 접두어(기본형-, 고급형- 등) 제거 후 일치 (exact)
    5. 유일 포함 매칭 (Unique Substring Match, exact, 2개 이상이면 매칭 안 함)
    6. 바이그램 자카드 퍼지 매칭 (>= 0.35, fuzzy)
    반환: (official_key, val_dict, match_type) 또는 None
    """
    if not v2_options or not clean:
        return None

    # [11-06-75] 매물 옵션명 '+' 접두사(예: '+트레일러21') 제거
    clean = re.sub(r'^\++', '', str(clean)).strip()
    if not clean:
        return None

    # 1. 직접 일치
    if clean in v2_options:
        return (clean, v2_options[clean], "exact")

    # 2. 별칭 적용 (직접 및 정규화 기준)
    clean_opt = OPTION_ALIAS_MAP.get(clean, clean)
    norm_opt = normalize_opt_name(clean_opt)
    for _alias_key, _alias_val in OPTION_ALIAS_MAP.items():
        if normalize_opt_name(_alias_key) == norm_opt:
            clean_opt = _alias_val
            norm_opt = normalize_opt_name(clean_opt)
            break

    if clean_opt in v2_options:
        return (clean_opt, v2_options[clean_opt], "exact")

    # 3. 정규화 완전 일치
    for off_key, val in v2_options.items():
        if normalize_opt_name(off_key) == norm_opt:
            return (off_key, val, "exact")

    # 4. 접두어(기본형- 등) 제거 후 재탐색
    clean_prefix = re.sub(r'^(?:기본형|고급형|스마트형|모던형|프리미엄형|디럭스형|최고급형)[-_ ]*', '', norm_opt)
    clean_prefix = re.sub(r'팩(?=[0-9])', '', clean_prefix)
    if clean_prefix and clean_prefix != norm_opt:
        for off_key, val in v2_options.items():
            if normalize_opt_name(off_key) == clean_prefix:
                return (off_key, val, "exact")

    # 5. 유일 포함 매칭 (Unique Substring Match)
    # 정규화된 원문이 카탈로그 옵션들 중 유일하게 1개 옵션에만 포함되는 경우 exact 매칭
    if norm_opt:
        cands = [off_key for off_key in v2_options if norm_opt in normalize_opt_name(off_key)]
        if len(cands) == 1:
            off_key = cands[0]
            return (off_key, v2_options[off_key], "exact")

    # 5-2. 옵션 묶음 매칭 (첫 번째 조각이 책 옵션이고, 나머지 조각 중 책 옵션이 없는 경우)
    # 예: "빌트인 캠 2, 증강현실 내비게이션" -> "빌트인 캠 2" exact
    parts = [p.strip() for p in re.split(r'[,+·]', clean) if p.strip()]
    if len(parts) >= 2:
        norm_first = normalize_opt_name(parts[0])
        matched_off_key = None
        for off_key in v2_options:
            if normalize_opt_name(off_key) == norm_first:
                matched_off_key = off_key
                break

        if matched_off_key:
            any_rest_matched = False
            for rp in parts[1:]:
                norm_rp = normalize_opt_name(rp)
                for off_key in v2_options:
                    if normalize_opt_name(off_key) == norm_rp:
                        any_rest_matched = True
                        break
                if any_rest_matched:
                    break

            if not any_rest_matched:
                return (matched_off_key, v2_options[matched_off_key], "exact")

    # 6. 바이그램 자카드 퍼지 매칭 (자카드 >= 0.35)
    best_candidate = None
    best_score = 0.0
    for official_key, val in v2_options.items():
        norm_official = normalize_opt_name(official_key)
        # 핵심 등급 수식어가 한쪽에만 있으면 매칭 배제
        mismatch = any((kw in norm_opt) != (kw in norm_official) for kw in SPEC_QUALIFIER_KEYWORDS)
        if mismatch:
            continue
        # 버전 식별자 불일치 방지 (1 vs 2)
        nums_a = re.findall(r'[1-9]', norm_opt)
        nums_b = re.findall(r'[1-9]', norm_official)
        if nums_a and nums_b and "".join(nums_a) != "".join(nums_b):
            continue
        jaccard = max(
            compute_bigram_jaccard(norm_opt, norm_official),
            compute_bigram_jaccard(clean_prefix, norm_official) if clean_prefix else 0.0
        )
        if jaccard > best_score and jaccard >= 0.35:
            best_score = jaccard
            best_candidate = (official_key, val, "fuzzy")

    return best_candidate


def resolve_option_item(
    raw_name: str,
    raw_price: int = 0,
    code: str = "",
    catalog_data: dict = None,
    price_by_name: dict = None
) -> dict:
    """
    단일 옵션에 대해 백엔드 단일 가격 규칙을 적용하여 표준 OptionItem 딕셔너리 생성
    규칙: 카탈로그 정가(catalog) -> API 가격(api) -> 미가격(unpriced, 0원)
    """
    name_clean = str(raw_name or "").strip()
    name_clean = re.sub(r'^\++', '', name_clean).strip()
    if not name_clean:
        return {
            "code": str(code or ""),
            "name": "",
            "raw_name": "",
            "price": 0,
            "price_man": 0,
            "source": "unpriced",
            "match_status": "unmatched",
            "desc": ""
        }

    standard_name = name_clean
    price = 0
    source = "unpriced"
    match_status = "unmatched"
    desc = ""

    # 1순위: 공식 신차가격표 카탈로그 매칭 (catalog)
    matched = None
    if catalog_data:
        # V2 옵션 매칭 우선 탐색
        v2_res = _find_in_v2_options(catalog_data, name_clean)
        if v2_res:
            off_name, val_dict, m_type = v2_res
            val_p = val_dict.get("price") if isinstance(val_dict, dict) else val_dict
            if val_p and val_p > 0:
                matched = {
                    "official_name": off_name,
                    "price": int(val_p),
                    "desc": val_dict.get("desc", "") if isinstance(val_dict, dict) else "",
                    "match_type": m_type
                }
        if not matched:
            matched = find_official_catalog_option(name_clean, catalog_data)

    if matched and matched.get("price") and matched["price"] > 0:
        standard_name = matched.get("official_name") or name_clean
        price = int(matched["price"])
        source = "catalog"
        match_status = matched.get("match_type") or ("exact" if normalize_opt_name(standard_name) == normalize_opt_name(name_clean) else "fuzzy")
        desc = matched.get("desc") or ""

    # 2순위: 원천 API 가격 매칭 (api - 차얼마 price_by_name 또는 명시된 raw_price)
    if price == 0 and price_by_name:
        n_norm = normalize_opt_name(name_clean)
        # 2-1: 완전/포함 일치
        for cname, cprice in price_by_name.items():
            cn_norm = normalize_opt_name(cname)
            if n_norm == cn_norm or (n_norm in cn_norm) or (cn_norm in n_norm):
                price = int(cprice)
                standard_name = cname
                source = "api"
                match_status = "exact" if n_norm == cn_norm else "fuzzy"
                break
        # 2-2: 바이그램 자카드 유사도 매칭 (기호/단어 차이 극복)
        if price == 0:
            best_score = 0.0
            best_price = 0
            best_cname = ""
            for cname, cprice in price_by_name.items():
                score = compute_bigram_jaccard(name_clean, cname)
                if score > best_score and score >= 0.45:
                    best_score = score
                    best_price = int(cprice)
                    best_cname = cname
            if best_price > 0:
                price = best_price
                standard_name = best_cname
                source = "api"
                match_status = "fuzzy"

    # 2순위-B: raw_price가 직접 주어진 경우 (예: 엔카/케이카 상세 데이터의 가격)
    if price == 0 and raw_price > 0:
        price = raw_price if raw_price >= 10000 else raw_price * 10000
        source = "api"
        match_status = "exact"

    # 3순위: 미가격 (unpriced, 0원) - 추정치 폴백(DEFAULT_OPTION_PRICES) 완전 제거
    if price == 0:
        source = "unpriced"
        match_status = "unmatched"

    price_man = round(price / 10000) if price >= 10000 else (price if price > 0 else 0)

    return {
        "code": str(code or ""),
        "name": standard_name,
        "raw_name": name_clean,
        "price": price,
        "price_man": price_man,
        "source": source,
        "match_status": match_status,
        "desc": desc
    }


def get_bigram_set(s: str) -> set:
    """문자 바이그램(2글자 음절 단위 슬라이딩 윈도우) 집합 생성"""
    if not s or len(s) < 2:
        return set()
    return {s[i:i+2] for i in range(len(s) - 1)}


def compute_bigram_jaccard(s1: str, s2: str) -> float:
    """바이그램 자카드 유사도 (Jaccard Index) 계산 (0.0 ~ 1.0)"""
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    set1 = get_bigram_set(s1)
    set2 = get_bigram_set(s2)
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


# 🌟 핵심 등급/스펙 수식어 목록 (한쪽에만 존재할 경우 동일 옵션으로 판정 금지)
SPEC_QUALIFIER_KEYWORDS = [
    '스마트', 'uvo', '유보', '어라운드뷰', 'avm', '서라운드뷰', 'svm',
    'jbl', '크렐', 'krell', '보스', 'bose', '렉시콘', 'lexicon',
    '드라이브와이즈', '스마트센스'
]


def _find_model_in_catalog(db: dict, car_name: str, year: Any = None):
    """단일 카탈로그 DB에서 차종명과 연식으로 모델 데이터(연식별 dict) 검색 -> (best_model_key, model_data)"""
    if not db or not car_name:
        return None

    def _norm_car_key(s: str) -> str:
        s = re.sub(r'^(현대|기아|제네시스|쉐보레|르노코리아|르노삼성|KG모빌리티|쌍용)\s*', '', str(s)).strip()
        s = re.sub(r'[\(\)\[\]\{\}]', '', s)
        return re.sub(r'\s+', '', s).lower()

    def _base_car_name(s: str) -> str:
        # 1. 브랜드 제거
        s = re.sub(r'^(현대|기아|제네시스|쉐보레|르노코리아|르노삼성|KG모빌리티|쌍용)\s*', '', str(s)).strip()
        # 2. 접두어 ('디 올 뉴', '더 뉴', '신형', '올 뉴') 제거
        s = re.sub(r'^(디\s*올\s*뉴|더\s*뉴|신형|올\s*뉴)\s*', '', s).strip()
        # 3. 페이스리프트/FL 수식어 제거 (11-06-59)
        s = re.sub(r'(?i)\b(f/l|fl|facelift|페이스리프트)\b', ' ', s)
        s = re.sub(r'(?i)(f/l|fl|facelift|페이스리프트)', ' ', s)
        # 4. 괄호 코드 ('(SX2)', '(MX5)', '(CN7)' 등) 제거
        s = re.sub(r'\([^\)]*\)|\[[^\]]*\]|\{[^\}]*\}', '', s).strip()
        # 5. 공백 제거 후 소문자화
        return re.sub(r'\s+', '', s).lower()

    def _norm_year(s_year: Any) -> str:
        if not s_year:
            return ""
        s = str(s_year).strip()
        m4 = re.search(r'\b(19\d{2}|20\d{2})\b', s) or re.search(r'(19\d{2}|20\d{2})', s)
        if m4:
            return m4.group(1)
        m2 = re.search(r'(\d{2})', s)
        if m2:
            return f"20{m2.group(1)}"
        return s

    orig_input_name = str(car_name).strip()

    # 전역 모델 별칭 우선 적용 (11-03-51, 11-06-01):
    # 1. 원문 직접 일치
    alias_applied = MODEL_ALIAS_MAP.get(car_name)

    # 2. 브랜드 제거 후 직접 일치
    clean_name = re.sub(r'^(현대|기아|제네시스|쉐보레|르노코리아|르노삼성|KG모빌리티|쌍용)\s*', '', str(car_name)).strip()
    if not alias_applied:
        alias_applied = MODEL_ALIAS_MAP.get(clean_name)

    # 3. 공백/특수문자 무시 정규화 별칭 조회 (11-06-01):
    # 공백 없는 표시명('신형쏘렌토(MQ4)')도 별칭('신형 쏘렌토 (MQ4)')에 매칭되도록 공통 정규화 비교
    if not alias_applied:
        norm_input = _norm_car_key(car_name)
        if norm_input:
            alias_cands = []
            for alias_k, alias_v in MODEL_ALIAS_MAP.items():
                norm_ak = _norm_car_key(alias_k)
                if norm_ak == norm_input:
                    alias_cands.append(alias_v)
            unique_cands = list(dict.fromkeys(alias_cands))
            if len(unique_cands) == 1:
                alias_applied = unique_cands[0]

    if alias_applied:
        car_name = alias_applied
        clean_name = re.sub(r'^(현대|기아|제네시스|쉐보레|르노코리아|르노삼성|KG모빌리티|쌍용)\s*', '', str(car_name)).strip()

    best_model_key = None
    if car_name in db:
        best_model_key = car_name
    elif clean_name in db:
        best_model_key = clean_name
    else:
        norm_target = normalize_opt_name(clean_name)
        for m_key in db.keys():
            if normalize_opt_name(m_key) == norm_target:
                best_model_key = m_key
                break
        if not best_model_key:
            for m_key in db.keys():
                norm_m = normalize_opt_name(m_key)
                if norm_target in norm_m or norm_m in norm_target:
                    best_model_key = m_key
                    break

    # 💡 [11-03-26 제이 규칙]: 기존 정확 매칭 실패 시에만 동작하는 차명 정규화 폴백
    # 정규화: 브랜드 제거 + 공백 제거 + 괄호 문자(()[]{}) 자체만 제거 (내용물 보존: (4세대) -> 4세대)
    # 정규화된 카탈로그 키가 정규화된 입력 차명에 포함되는 경우 매칭.
    # 후보가 2개 이상이면 임의 추측하지 않고 매칭하지 않음(none 유지).
    if not best_model_key:
        norm_input = _norm_car_key(car_name)
        if norm_input:
            candidates = []
            for m_key in db.keys():
                norm_k = _norm_car_key(m_key)
                # 2자 이하 키는 부분일치 후보에서 제외 (11-03-51): 'A4'('a4')가 '신형카니발ka4' 안에 있어 오매칭된 실측 사례 방지.
                if len(norm_k) < 3:
                    continue
                if norm_k and norm_k in norm_input:
                    candidates.append(m_key)

            if len(candidates) == 1:
                best_model_key = candidates[0]
            elif len(candidates) > 1:
                # 후보가 2개 이상이면 추측하지 않고 매칭하지 않는다(none 유지)
                pass

    # 💡 [11-06-37]: 모델 조회에 연식 기반 세대 구분 추가 (구조 수정, 차종별 하드코딩 금지)
    # - 기본 이름: 브랜드 제거 + 접두어('디 올 뉴', '더 뉴', '신형', '올 뉴') 제거 + 괄호 코드('(SX2)', '(MX5)' 등) 제거 + 공백 제거 후 소문자화
    # - 기존 매칭으로 찾은 모델에 주어진 연식이 없는 경우: 기본 이름이 같은 책 모델 중 주어진 연식을 포함하는 모델이 정확히 1개면 교체
    # - 기존 매칭으로 모델을 못 찾았을 때: 기본 이름이 같은 책 모델 중 주어진 연식을 포함하는 모델이 정확히 1개면 채택
    target_year_norm = _norm_year(year)
    if target_year_norm:
        input_base = _base_car_name(orig_input_name) or _base_car_name(car_name)
        if best_model_key:
            model_years = db.get(best_model_key, {})
            if isinstance(model_years, dict) and target_year_norm not in model_years:
                if input_base:
                    matched_models = [
                        m_key for m_key, m_val in db.items()
                        if _base_car_name(m_key) == input_base and isinstance(m_val, dict) and target_year_norm in m_val
                    ]
                    if len(matched_models) == 1:
                        best_model_key = matched_models[0]
        else:
            if input_base:
                matched_models = [
                    m_key for m_key, m_val in db.items()
                    if _base_car_name(m_key) == input_base and isinstance(m_val, dict) and target_year_norm in m_val
                ]
                if len(matched_models) == 1:
                    best_model_key = matched_models[0]

    if not best_model_key:
        return None
    return best_model_key, db[best_model_key]


def get_ordered_model_years(model_data: dict, year_str: str) -> list:
    """
    카탈로그 모델 데이터의 연식들을 요청 연식 기반으로 우선순위 정렬:
    1. 요청 연식에서 추출된 후보 연식(extract_year_candidates 순서) 먼저
    2. 나머지 모델 연식은 요청 연식과의 거리(절대값) 오름차순, 동거리면 최신 연식 내림차순
    """
    if not model_data:
        return []

    all_years = [str(y) for y in model_data.keys() if model_data.get(y)]
    if not all_years:
        return []

    cands = extract_year_candidates(year_str)
    ordered = []

    # 1. 후보 연식 먼저
    for c in cands:
        if c in all_years and c not in ordered:
            ordered.append(c)

    # 후보 연식 숫자 목록 (거리 계산 기준)
    cand_ints = [int(c) for c in cands if c.isdigit()]

    # 2. 나머지 연식 (요청 연식과의 거리순, 동거리면 최신 연식 먼저)
    remaining = [y for y in all_years if y not in ordered]
    if remaining:
        if cand_ints:
            def _sort_key(y_str: str):
                y_val = int(y_str) if y_str.isdigit() else 0
                min_dist = min(abs(y_val - c) for c in cand_ints)
                return (min_dist, -y_val)
            remaining.sort(key=_sort_key)
        else:
            remaining.sort(key=lambda y: -int(y) if y.isdigit() else 0)
        ordered.extend(remaining)

    return ordered


def _search_in_catalog(db: dict, car_name: str, year: str = "") -> dict:
    """단일 카탈로그 DB에서 차종명과 연식으로 검색 (기존 호출처 보존)"""
    found = _find_model_in_catalog(db, car_name)
    if not found:
        return {}

    _, model_data = found
    yr_cands = extract_year_candidates(year)

    target_yr = None
    for y in yr_cands:
        if y in model_data:
            target_yr = y
            break

    if not target_yr and model_data:
        target_yr = sorted(model_data.keys(), reverse=True)[0]

    if not target_yr:
        return {}

    res = model_data.get(target_yr, {})
    # 빈 껍데기 체크 (grades 또는 options가 있을 때만 유효 반환)
    if res and (res.get("options") or res.get("grades")):
        return res
    return {}


def get_catalog_for_car(car_name: str, year: str = "") -> dict:
    """하위 호환성 유지: 캐노니컬 카탈로그 파일 삭제로 빈 딕셔너리 반환"""
    return {}


def match_car_options_detail(car_name: str, year: Any, options_text_or_list: Any, grade: Optional[str] = None) -> list:
    """
    선택 차량의 옵션 목록(원문)을 카탈로그 V2(새 책)와 매칭하여
    표준명, 매칭상태(exact/fuzzy/none), 출처(danawa/none), 매칭연식(matched_year) 목록 반환
    - V2에 없거나 등급이 없으면 미가격(price=None, source="none", match_type="none") 반환 (옛날 길 폴백 제거)
    """
    if not options_text_or_list:
        return []

    if isinstance(options_text_or_list, str):
        if re.search(r'\s+/\s+|\s+·\s+|\||\([0-9,]+\s*만\)', options_text_or_list):
            raw_list = [s.strip() for s in re.split(r'\s+/\s+|[·|\n]', options_text_or_list) if s.strip()]
        else:
            raw_list = [s.strip() for s in re.split(r'[,·\/\n]', options_text_or_list) if s.strip()]
    elif isinstance(options_text_or_list, list):
        raw_list = [str(s).strip() for s in options_text_or_list if str(s).strip()]
    else:
        return []

    # 💡 [11-05-07]: 등급이 주어진 경우 카탈로그 V2(새 책) 우선 확인
    v2_spec = None
    if grade and str(grade).strip():
        try:
            from services.catalog_by_source_service import get_pilot_catalog_spec
            v2_spec = get_pilot_catalog_spec(source="danawa", car_name=car_name, year=year, grade=str(grade).strip())
        except Exception:
            v2_spec = None

    v2_options = {}
    if v2_spec and v2_spec.get("found"):
        from services.catalog_by_source_service import merge_options_and_accessories
        # [11-06-75 & 11-11-02] options와 accessories를 안전하게 병합 (accessories의 0원이 options의 정상 가격을 덮어쓰지 않음)
        v2_options = merge_options_and_accessories(
            v2_spec.get("options", {}),
            v2_spec.get("accessories", {})
        )

    # 💡 [11-06-34]: 등급 인승 모호(get_pilot_catalog_spec found: False) 시 등급 패밀리(인승 제외 6개 키 일치) 옵션 합집합 폴백
    # 옵션은 트림 단위라 인승이 달라도 이름·가격이 동일하므로, 인승 누락/모호 등급도 옵션 매칭은 정상 수행
    # 💡 [11-06-35]: grade가 누락되거나 비어 있어도(None/빈문자열) 차종+연식의 전체 등급 옵션 합집합으로 매칭 수행
    if not v2_options and car_name and year:
        try:
            from services.catalog_by_source_service import (
                load_catalog_by_source_v2,
                SPEC_COMPARE_KEYS,
            )
            from services.data_processor import DataProcessor

            cat_v2 = load_catalog_by_source_v2()
            source_book = cat_v2.get("danawa", {})

            s_car = str(car_name).strip()
            car_book = None
            if s_car in source_book and isinstance(source_book[s_car], dict):
                # 직접 일치한 모델이라도 연식이 없으면 연식 기반 세대 구분으로 보정
                res_model = _find_model_in_catalog(source_book, s_car, year=year)
                if res_model:
                    _, car_book = res_model
                else:
                    car_book = source_book[s_car]
            else:
                res_model = _find_model_in_catalog(source_book, s_car, year=year)
                if res_model:
                    _, car_book = res_model

            if car_book and isinstance(car_book, dict):
                s_year = str(year).strip()
                m4 = re.search(r'\b(19\d{2}|20\d{2})\b', s_year) or re.search(r'(19\d{2}|20\d{2})', s_year)
                if m4:
                    norm_year = m4.group(1)
                else:
                    m2 = re.search(r'(\d{2})', s_year)
                    norm_year = f"20{m2.group(1)}" if m2 else s_year

                year_book = car_book.get(norm_year)
                if year_book and isinstance(year_book, dict):
                    has_grade = bool(grade and str(grade).strip())
                    target_6_tuple = None
                    if has_grade:
                        target_spec = DataProcessor.build_car_spec(text=str(grade).strip())
                        keys_no_seats = tuple(k for k in SPEC_COMPARE_KEYS if k != "seats")
                        target_6_tuple = tuple(target_spec.get(k) for k in keys_no_seats)

                    for cand_g_key, cand_g_spec in year_book.items():
                        if isinstance(cand_g_spec, dict):
                            is_matched_grade = False
                            if has_grade and target_6_tuple:
                                cand_spec = DataProcessor.build_car_spec(text=cand_g_key)
                                cand_6_tuple = tuple(cand_spec.get(k) for k in keys_no_seats)
                                if target_6_tuple == cand_6_tuple:
                                    is_matched_grade = True
                            else:
                                # grade가 없거나 특정 불가 시 해당 연식의 모든 등급 옵션 합집합 사용
                                is_matched_grade = True

                            if is_matched_grade:
                                from services.catalog_by_source_service import merge_options_and_accessories
                                cand_opts = cand_g_spec.get("options", {})
                                cand_accs = cand_g_spec.get("accessories", {})
                                cand_merged = merge_options_and_accessories(cand_opts, cand_accs)
                                for opt_k, opt_v in cand_merged.items():
                                    if opt_k not in v2_options:
                                        v2_options[opt_k] = opt_v
                                    else:
                                        # 이미 있는 경우에도 0원이 유효한 가격을 덮지 않도록 안전 병합
                                        cur_p = v2_options[opt_k].get("price") if isinstance(v2_options[opt_k], dict) else v2_options[opt_k]
                                        new_p = opt_v.get("price") if isinstance(opt_v, dict) else opt_v
                                        cur_valid = cur_p is not None and isinstance(cur_p, (int, float)) and cur_p > 0
                                        new_valid = new_p is not None and isinstance(new_p, (int, float)) and new_p > 0
                                        if not cur_valid and new_valid:
                                            v2_options[opt_k] = opt_v
        except Exception:
            pass

    results = []
    for raw in raw_list:
        clean = re.sub(r'\([0-9,]+(?:\s*만|\s*원)?\)', '', raw)
        clean = re.sub(r'\[[^\]]*\]', '', clean).strip()
        clean = re.sub(r'^\++', '', clean).strip()

        matched_v2 = None
        if v2_options:
            matched_v2 = _find_in_v2_options(v2_options, clean)

        if matched_v2:
            v2_k, v2_val, v2_match_type = matched_v2
            p_val = v2_val.get("price") if isinstance(v2_val, dict) else v2_val
            p_man = v2_val.get("price_man") if isinstance(v2_val, dict) else None
            if p_man is None and p_val is not None:
                try:
                    p_man = round(int(p_val) / 10000)
                except Exception:
                    p_man = None
            results.append({
                "raw_name": raw,
                "clean_name": clean,
                "official_name": v2_k,
                "price": p_val,
                "price_man": p_man,
                "desc": v2_val.get("desc", "") if isinstance(v2_val, dict) else "",
                "match_type": v2_match_type,
                "source": "danawa",
                "matched_year": str(v2_spec.get("year", year)) if isinstance(v2_spec, dict) else str(year)
            })
            continue

        # V2에 없거나 등급이 없는 경우: 가격 없음(none)으로 반환 (옛날 길 폴백 완전 제거)
        results.append({
            "raw_name": raw,
            "clean_name": clean,
            "official_name": raw,
            "price": None,
            "price_man": None,
            "desc": "",
            "match_type": "none",
            "source": "none",
            "matched_year": ""
        })
    return results



def find_official_catalog_option(opt_name: str, catalog_data_or_options: Any = None) -> Optional[dict]:
    """
    주어진 옵션명에서 카탈로그 내 공식 신차 옵션을 탐색 (프론트엔드 findOfficialCatalogOption과 동일)
    반환값: {"official_name": str, "price": Optional[int], "desc": Optional[str]} 또는 None
    """
    if not opt_name or not str(opt_name).strip():
        return None

    if isinstance(catalog_data_or_options, dict):
        if "options" in catalog_data_or_options or "accessories" in catalog_data_or_options:
            from services.catalog_by_source_service import merge_options_and_accessories
            options_dict = merge_options_and_accessories(
                catalog_data_or_options.get("options", {}),
                catalog_data_or_options.get("accessories", {})
            )
        else:
            options_dict = catalog_data_or_options
    else:
        options_dict = {}

    if not options_dict:
        return None

    clean = re.sub(r'\([0-9,]+(?:\s*만|\s*원)?\)', '', str(opt_name))
    clean = re.sub(r'\[[^\]]*\]', '', clean).strip()
    clean = re.sub(r'^\++', '', clean).strip()
    # 전역 별칭 적용 (정규화 비교보다 먼저)
    clean = OPTION_ALIAS_MAP.get(clean, clean)
    norm_clean = normalize_opt_name(clean)
    # 별칭 정규화 조회 (11-03-51): 띄어쓰기 변형도 별칭 키와 정규화 기준으로 맞춘다. 새 키 추가 없음.
    for _alias_key, _alias_val in OPTION_ALIAS_MAP.items():
        if normalize_opt_name(_alias_key) == norm_clean:
            clean = _alias_val
            norm_clean = normalize_opt_name(clean)
            break
    if not norm_clean:
        return None

    # 1. 완전 일치 (정규화 후)
    for official_key, val in options_dict.items():
        norm_official = normalize_opt_name(official_key)
        if norm_official == norm_clean:
            price = val.get("price") if isinstance(val, dict) else None
            desc = val.get("desc") if isinstance(val, dict) else (val if isinstance(val, str) else "")
            return {"official_name": official_key, "price": price, "desc": desc}

    # 2. 접두어(기본형-, 고급형-, 디럭스- 등) 제거 후 재탐색
    clean_prefix = re.sub(r'^(?:기본형|고급형|스마트형|모던형|프리미엄형|디럭스형|최고급형)[-_ ]*', '', norm_clean)
    clean_prefix = re.sub(r'팩(?=[0-9])', '', clean_prefix)
    if clean_prefix and clean_prefix != norm_clean:
        for official_key, val in options_dict.items():
            norm_official = normalize_opt_name(official_key)
            if norm_official == clean_prefix:
                price = val.get("price") if isinstance(val, dict) else None
                desc = val.get("desc") if isinstance(val, dict) else (val if isinstance(val, str) else "")
                return {"official_name": official_key, "price": price, "desc": desc}

    # 3. 바이그램 자카드 유사도 (>= 0.35) 기반 최적 후보 탐색 (수식어 & 버전 불일치 차단)
    best_candidate = None
    best_score = 0.0

    for official_key, val in options_dict.items():
        norm_official = normalize_opt_name(official_key)

        # 핵심 등급 수식어가 한쪽에만 있으면 매칭 배제
        mismatch = any((kw in norm_clean) != (kw in norm_official) for kw in SPEC_QUALIFIER_KEYWORDS)
        if mismatch:
            continue

        # 버전 식별자 불일치 방지 (1 vs 2)
        nums_a = re.findall(r'[1-9]', norm_clean)
        nums_b = re.findall(r'[1-9]', norm_official)
        if nums_a and nums_b and "".join(nums_a) != "".join(nums_b):
            continue

        jaccard = max(
            compute_bigram_jaccard(norm_clean, norm_official),
            compute_bigram_jaccard(clean_prefix, norm_official) if clean_prefix else 0.0
        )
        if jaccard > best_score and jaccard >= 0.35:
            best_score = jaccard
            price = val.get("price") if isinstance(val, dict) else None
            desc = val.get("desc") if isinstance(val, dict) else (val if isinstance(val, str) else "")
            best_candidate = {"official_name": official_key, "price": price, "desc": desc}

    return best_candidate


def normalize_chaolma_options(
    chaolma_options: list,
    catalog_data: dict = None,
    car_name: str = "",
    year: str = ""
) -> list:
    """
    차얼마(오토플러스) 옵션 목록을 엔카 공식 신차가격표 카탈로그 기준으로 정규화
    (프론트엔드 normalizeChaolmaOptions와 100% 동일)
    """
    if not chaolma_options or not isinstance(chaolma_options, list):
        return []

    if catalog_data is None and car_name:
        catalog_data = get_catalog_for_car(car_name, year)

    normalized_list = []
    for opt in chaolma_options:
        if isinstance(opt, dict):
            raw_name = str(opt.get("name") or opt.get("option_name") or "").strip()
            orig_price = int(opt.get("price") or 0)
            dep_price = int(opt.get("depreciated_price") or 0)
            rate = float(opt.get("rate") or 0.2)
        elif isinstance(opt, str):
            raw_name = str(opt).strip()
            orig_price = 0
            dep_price = 0
            rate = 0.2
        else:
            continue

        if not raw_name or raw_name in ('없음', '-', '⚠️정보없음', '⚠️조회실패', '코드매칭실패'):
            continue

        matched = find_official_catalog_option(raw_name, catalog_data)

        standard_name = raw_name
        standard_price_man = round(orig_price / 10000) if orig_price > 0 else round(dep_price / 10000)
        is_catalog_matched = False
        desc = ""

        if matched:
            standard_name = matched.get("official_name") or raw_name
            m_price = matched.get("price")
            if m_price and m_price > 0:
                standard_price_man = round(m_price / 10000)
            is_catalog_matched = True
            desc = matched.get("desc") or ""
        else:
            # 매칭 실패 시 접두어만 제거
            standard_name = re.sub(r'^(?:기본형|고급형|디럭스형)[-_ ]*', '', raw_name)

        normalized_list.append({
            "original_name": raw_name,
            "original_price": orig_price,
            "depreciated_price": dep_price,
            "rate": rate,
            "standard_name": standard_name,
            "standard_price_man": standard_price_man,
            "is_catalog_matched": is_catalog_matched,
            "desc": desc
        })

    return normalized_list


def calculate_catalog_option_value(
    target_opts: Any,
    car_name: str = "",
    year: str = ""
) -> int:
    """
    타겟 옵션(문자열 또는 리스트)의 카탈로그 기준 총 신차 출고가(만원) 산출
    - 1순위: 카탈로그 공식 옵션 가격 매칭
    - 2순위: 괄호 내 명시 가격 '(xx만)'
    - 3순위: 차얼마 원본 가격
    """
    if not target_opts:
        return 0

    catalog_data = get_catalog_for_car(car_name, year) if car_name else None

    # 리스트로 변환
    if isinstance(target_opts, str):
        # 쉼표, 슬래시 또는 개행 구분
        raw_items = [x.strip() for x in re.split(r'[/,\n]+', target_opts) if x.strip()]
    elif isinstance(target_opts, (list, tuple, set)):
        raw_items = list(target_opts)
    else:
        return 0

    total_val_man = 0
    matched_catalog_keys = set()

    for item in raw_items:
        item_str = ""
        explicit_price = 0
        if isinstance(item, dict):
            item_str = str(item.get("standard_name") or item.get("name") or "")
            if item.get("standard_price_man"):
                explicit_price = int(item["standard_price_man"])
            elif item.get("price"):
                explicit_price = int(item["price"]) // 10000 if int(item["price"]) >= 10000 else int(item["price"])
        else:
            item_str = str(item).strip()

        if not item_str or item_str in ('없음', '-', '⚠️정보없음', '⚠️조회실패', '코드매칭실패'):
            continue

        # 괄호 안의 가격 추출
        p_match = re.search(r'\((\d+)\s*만(?:원)?\)', item_str)
        if p_match:
            explicit_price = int(p_match.group(1))

        # 카탈로그 매칭 시도
        catalog_price_man = 0
        if catalog_data:
            matched = find_official_catalog_option(item_str, catalog_data)
            if matched and matched.get("price"):
                off_name = matched.get("official_name")
                # 동일 카탈로그 옵션 중복 가산 방지
                if off_name not in matched_catalog_keys:
                    catalog_price_man = round(matched["price"] / 10000)
                    matched_catalog_keys.add(off_name)

        if catalog_price_man > 0:
            total_val_man += catalog_price_man
        elif explicit_price > 0:
            total_val_man += explicit_price

    return total_val_man


def extract_keywords_from_description(desc: str) -> list:
    """공식 설명문에서 헤이딜러 매칭용 핵심 부품 키워드 자동 추출"""
    KEYWORD_CANDIDATES = [
        "통풍시트", "통풍", "전동시트", "파워시트", "요추받침", "가죽시트", "열선시트", "열선핸들",
        "어댑티브", "스마트크루즈", "크루즈컨트롤", "acc", "scc", "ascc", "hda", "hda2",
        "차선변경", "사각지대", "후측방", "차로유지", "차로이탈", "긴급제동",
        "전방충돌", "차선이탈", "충돌경고", "충돌방지", "안전하차", "sbza", "rcta", "ldws", "fcw", "rlad",
        "헤드업", "hud", "내비게이션", "네비게이션", "마이링크", "후방카메라", "어라운드뷰", "서라운드뷰", "svm", "bvm",
        "전동트렁크", "파워테일게이트", "스마트테일게이트", "리프트게이트", "무선충전", "선루프", "썬루프",
        "파노라마선루프", "디지털키", "빌트인캠", "블랙박스", "bose", "보스", "크렐", "krell", "jbl", "스피커",
        "스마트센스", "드라이브와이즈", "세이프티"
    ]
    norm_desc = normalize_opt_name(desc)
    found = []
    for kw in KEYWORD_CANDIDATES:
        if normalize_opt_name(kw) in norm_desc:
            found.append(kw)
    return found


def extract_year_candidates(year_str: str) -> list:
    """연식 문자열에서 검색 가능한 4자리 연도 후보 목록 추출 (예: '16(17)' -> ['2016', '2017'])"""
    if not year_str:
        return []
    s = str(year_str).strip()
    cands = []
    # 4자리 연도 (2016 등)
    for m in re.findall(r'20\d{2}', s):
        if m not in cands:
            cands.append(m)
    # 2자리 연도 (10~26 범위: '16(17)' -> 2016, 2017)
    for m in re.findall(r'(?<!\d)(\d{2})(?!\d)', s):
        val = int(m)
        if 10 <= val <= 26:
            y4 = f"20{m}"
            if y4 not in cands:
                cands.append(y4)
    return cands


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

        # 연식 후보 리스트 순회 (일치하는 연식 우선)
        yr_cands = extract_year_candidates(year)

        for m_key in target_models:
            yr_dict = crawled_db[m_key]
            search_years = [y for y in yr_cands if y in yr_dict]
            if not search_years:
                search_years = list(yr_dict.keys())
            for y in search_years:
                yr_val = yr_dict.get(y, {})
                items_to_search = {}
                if isinstance(yr_val, dict):
                    if "packages" in yr_val or "options" in yr_val:
                        # 1) 패키지 세부 구성 설명 (순수 금액/숫자는 설명이 아니므로 스킵)
                        for p_name, p_desc in yr_val.get("packages", {}).items():
                            if p_desc and not re.match(r'^[\d,\s원만원]+$', str(p_desc).strip()):
                                items_to_search[p_name] = p_desc
                        # 2) 개별 옵션 (설명 또는 가격 포함)
                        for o_name, o_info in yr_val.get("options", {}).items():
                            if isinstance(o_info, dict):
                                desc = o_info.get("desc")
                                price = o_info.get("price")
                                if not desc and price:
                                    desc = f"선택옵션 (출고가: {price:,}원)"
                                if desc and not re.match(r'^[\d,\s원만원]+$', str(desc).strip()) and o_name not in items_to_search:
                                    items_to_search[o_name] = desc
                            elif isinstance(o_info, str) and not re.match(r'^[\d,\s원만원]+$', str(o_info).strip()) and o_name not in items_to_search:
                                items_to_search[o_name] = o_info
                    else:
                        items_to_search = {k: v for k, v in yr_val.items() if not re.match(r'^[\d,\s원만원]+$', str(v).strip())}

                # 1단계: 완전 일치(Exact Match) 우선 탐색
                for p_name, p_desc in items_to_search.items():
                    norm_p = normalize_opt_name(p_name)
                    if norm_p and norm == norm_p:
                        matched_kw = extract_keywords_from_description(p_desc)
                        if not matched_kw:
                            for master_pkg in PACKAGE_CATALOG:
                                for a in master_pkg.get("aliases", []):
                                    if normalize_opt_name(a) == norm_p:
                                        return master_pkg
                        return {
                            "id": f"crawled_{m_key}_{y}_{p_name}",
                            "name": p_name,
                            "brand": m_key,
                            "description": p_desc,
                            "items": [it.strip() for it in p_desc.split(",") if it.strip()],
                            "match_keywords": matched_kw if matched_kw else [p_name],
                            "min_matches": 1
                        }

                # 2단계: 부분 일치(Substring Match) 탐색
                for p_name, p_desc in items_to_search.items():
                    norm_p = normalize_opt_name(p_name)
                    if not norm_p or len(norm_p) < 2:
                        continue
                    if len(norm) >= 3 and len(norm_p) >= 3 and (norm_p in norm or norm in norm_p):
                        matched_kw = extract_keywords_from_description(p_desc)
                        if not matched_kw:
                            for master_pkg in PACKAGE_CATALOG:
                                for a in master_pkg.get("aliases", []):
                                    if normalize_opt_name(a) == norm_p:
                                        return master_pkg
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
    # 2-1단계: 별칭(alias) 완전 일치 우선 탐색
    for pkg in PACKAGE_CATALOG:
        for alias in pkg.get("aliases", []):
            norm_alias = normalize_opt_name(alias)
            if norm_alias and norm == norm_alias:
                return pkg

    # 2-2단계: 패키지 공식 명칭 완전 일치 탐색
    for pkg in PACKAGE_CATALOG:
        norm_name = normalize_opt_name(pkg.get("name", ""))
        if norm_name and norm == norm_name:
            return pkg

    # 2-3단계: 부분 일치 탐색 (단, 숫자 1/2/3 등 번호가 다르면 오매칭 방지)
    norm_num = re.findall(r'[1-9]', norm)
    for pkg in PACKAGE_CATALOG:
        for alias in pkg.get("aliases", []):
            norm_alias = normalize_opt_name(alias)
            if not norm_alias or len(norm_alias) < 2:
                continue
            if len(norm) >= 3 and len(norm_alias) >= 3 and (norm_alias in norm or norm in norm_alias):
                alias_num = re.findall(r'[1-9]', norm_alias)
                if norm_num and alias_num and norm_num != alias_num:
                    continue
                return pkg

    for pkg in PACKAGE_CATALOG:
        norm_name = normalize_opt_name(pkg.get("name", ""))
        if not norm_name or len(norm_name) < 2:
            continue
        if len(norm) >= 3 and len(norm_name) >= 3 and (norm_name in norm or norm in norm_name):
            name_num = re.findall(r'[1-9]', norm_name)
            if norm_num and name_num and norm_num != name_num:
                continue
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
        return True, f"[{pkg_str}]\n──────────────────────────────\n✓ 기준 차량 장착 옵션과 일치함"
    else:
        return False, f"[{pkg_str}]\n──────────────────────────────\n(기준 차량에는 미장착된 옵션입니다)"
