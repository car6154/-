# scripts/merge_alias_options.py
"""
[11-11-18] 제이책(C) 약칭 옵션 중복 병합 스크립트
- 같은 등급 안에서 약칭 vs 풀어쓴 형태인 중복 옵션 병합 (긴 이름 유지)
- 백업: data/catalog_c_v5_backup_2026-11-12.json
- 산출: data/catalog_c.json
- 병합 로그: data/catalog_c_option_alias_merge_log_2026-11-12.json
- 검토 목록: data/catalog_c_option_alias_review_2026-11-12.json
"""

import os
import sys
import json
import re
import shutil
from datetime import datetime

# 콘솔 UTF-8 출력 보장
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

CATALOG_C_FILE = os.path.join(DATA_DIR, "catalog_c.json")
BACKUP_FILE = os.path.join(DATA_DIR, "catalog_c_v5_backup_2026-11-12.json")
MERGE_LOG_FILE = os.path.join(DATA_DIR, "catalog_c_option_alias_merge_log_2026-11-12.json")
REVIEW_FILE = os.path.join(DATA_DIR, "catalog_c_option_alias_review_2026-11-12.json")


def log(msg: str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] {msg}", flush=True)


def classify_option_pair(name_a: str, name_b: str, price_a: int, price_b: int) -> tuple:
    """
    약칭 vs 풀어쓴 형태 정밀 판정 함수
    반환: (is_mergeable, longer_name, shorter_name, reason)
    """
    if price_a != price_b or not price_a:
        return False, None, None, "가격 상이"

    s_a = str(name_a).strip()
    s_b = str(name_b).strip()

    # 1. UVO 표기 차이 정규화
    u_a = re.sub(r'(?i)\buvo\s*(?:2\.0|3\.0)?\b', '', s_a)
    u_a = re.sub(r'(?i)uvo\s*(?:2\.0|3\.0)?', '', u_a)
    u_b = re.sub(r'(?i)\buvo\s*(?:2\.0|3\.0)?\b', '', s_b)
    u_b = re.sub(r'(?i)uvo\s*(?:2\.0|3\.0)?', '', u_b)

    # 2. 약칭 표준형 변환
    def to_canonical(text: str) -> str:
        t = text.lower()
        t = re.sub(r'전자식\s*룸미러\s*\(\s*ecm\s*\)|전자식\s*룸미러|ecm\s*룸미러', 'ecm', t)
        t = re.sub(r'자동\s*요금\s*징수\s*시스템\s*\(\s*etcs\s*\)|자동\s*요금징수\s*시스템|톨게이트\s*자동결제시스템\s*\(\s*etcs\s*\)|톨게이트\s*자동결제시스템|하이패스\s*시스템|하이패스|etcs', 'etcs', t)
        t = re.sub(r'전자식\s*파킹\s*브레이크\s*\(\s*epb\s*\)|전자식\s*파킹\s*브레이크|e\-?pkb|epb', 'epb', t)
        t = re.sub(r'[\s\-_/·・\.\(\)\&+,]+', '', t)
        return t

    c_a = to_canonical(u_a)
    c_b = to_canonical(u_b)

    if c_a == c_b:
        # 긴 이름을 남기고 짧은 이름을 제거
        if len(s_a) >= len(s_b):
            return True, s_a, s_b, "약칭 vs 풀어쓴 형태 단일화 (긴 이름 유지)"
        else:
            return True, s_b, s_a, "약칭 vs 풀어쓴 형태 단일화 (긴 이름 유지)"

    return False, None, None, "약칭 관계 아님"


def run_alias_merge():
    log("==================================================")
    log("🚀 [11-11-18] 제이책(C) 약칭 옵션 중복 병합 시작")
    log("==================================================")

    # 1. v5 백업 생성
    if not os.path.exists(BACKUP_FILE):
        log(f"1. v5 백업 생성 중 -> {BACKUP_FILE}")
        shutil.copyfile(CATALOG_C_FILE, BACKUP_FILE)
    else:
        log(f"1. v5 백업 파일 확인됨: {BACKUP_FILE}")

    with open(CATALOG_C_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    before_options = sum(len(g.get('options', {})) for yrs in catalog.values() for grades in yrs.values() for g in grades.values())
    log(f"  - 병합 전 총 옵션 수: {before_options:,}개")

    merged_logs = []
    review_list = []
    shorter_names_to_delete = {} # (model, year, gname) -> set(shorter_names)

    for model, yrs in catalog.items():
        for yr, grades in yrs.items():
            for gname, gdata in grades.items():
                opts = gdata.get('options', {})
                opt_list = list(opts.items())
                
                for i in range(len(opt_list)):
                    na, ia = opt_list[i]
                    pa = ia.get('price')
                    if not pa: continue
                    for j in range(i + 1, len(opt_list)):
                        nb, ib = opt_list[j]
                        pb = ib.get('price')
                        if pa == pb:
                            is_merge, longer, shorter, reason = classify_option_pair(na, nb, pa, pb)
                            
                            if is_merge:
                                key = (model, yr, gname)
                                if key not in shorter_names_to_delete:
                                    shorter_names_to_delete[key] = set()
                                shorter_names_to_delete[key].add(shorter)

                                # 긴 이름에 설명 및 소스 보존
                                longer_info = ia if na == longer else ib
                                shorter_info = ib if na == longer else ia
                                
                                # desc는 긴 쪽 유지
                                desc_l = longer_info.get('desc') or ''
                                desc_s = shorter_info.get('desc') or ''
                                longest_desc = desc_l if len(desc_l) >= len(desc_s) else desc_s
                                longer_info['desc'] = longest_desc or None

                                # encar 포함 시 encar 출처 유지
                                if longer_info.get('source') != 'encar' and shorter_info.get('source') == 'encar':
                                    longer_info['source'] = 'encar'

                                merged_logs.append({
                                    'model': model,
                                    'year': yr,
                                    'grade': gname,
                                    'price': pa,
                                    'retained_name': longer,
                                    'removed_name': shorter,
                                    'retained_source': longer_info.get('source'),
                                    'removed_source': shorter_info.get('source'),
                                    'reason': reason
                                })
                            else:
                                # 이름 유사도가 있어 검토가 필요한 쌍은 review에 기록
                                s_a = re.sub(r'[\s\-_/·・\.\(\)\&+,]+', '', na.lower())
                                s_b = re.sub(r'[\s\-_/·・\.\(\)\&+,]+', '', nb.lower())
                                if s_a in s_b or s_b in s_a or any(k in s_a and k in s_b for k in ['패키지', '스타일', '내비', '룸미러', '시트', '휠', '선루프']):
                                    review_list.append({
                                        'model': model,
                                        'year': yr,
                                        'grade': gname,
                                        'price': pa,
                                        'name_a': na,
                                        'source_a': ia.get('source'),
                                        'name_b': nb,
                                        'source_b': ib.get('source'),
                                        'reason': "이름 상이 및 개별 옵션 판단으로 합치지 않고 보존"
                                    })

    # 2. catalog_c 데이터에서 shorter_name 실제 삭제
    log(f"\n2. 제이책(C) 데이터에서 {len(merged_logs):,}개 약칭 옵션 제거 적용 중...")
    for (model, yr, gname), short_set in shorter_names_to_delete.items():
        grade_opts = catalog[model][yr][gname].get('options', {})
        for s_name in short_set:
            if s_name in grade_opts:
                del grade_opts[s_name]

    after_options = sum(len(g.get('options', {})) for yrs in catalog.values() for grades in yrs.values() for g in grades.values())

    # 3. 파일 저장
    log("\n3. 정제 결과 파일 저장 중...")
    with open(CATALOG_C_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    log(f"  - 갱신된 제이책(C) 저장 완료: {CATALOG_C_FILE} ({os.path.getsize(CATALOG_C_FILE)/(1024*1024):.2f} MB)")

    with open(MERGE_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(merged_logs, f, ensure_ascii=False, indent=2)
    log(f"  - 약칭 옵션 병합 로그 저장: {MERGE_LOG_FILE} ({len(merged_logs):,}쌍)")

    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        json.dump(review_list, f, ensure_ascii=False, indent=2)
    log(f"  - 검토 목록 저장: {REVIEW_FILE} ({len(review_list):,}쌍)")

    # 4. 검증 리포트
    log("\n==================================================")
    log("📋 [11-11-18] 제이책(C) 약칭 옵션 중복 병합 검증 보고서")
    log("==================================================")
    log("1. 수치 요약:")
    log(f"   - 병합한 약칭 옵션 쌍 수: {len(merged_logs):,}쌍")
    log(f"   - 검토 목록에 남긴 쌍 수: {len(review_list):,}쌍")
    log(f"   - 옵션 수 변화: {before_options:,}개 -> {after_options:,}개 (순감소: {before_options - after_options:,}개)")

    # 필수 검증 1: 쏘나타 (DN8) 2023 lpg 2.0 2WD 모던
    log("\n2. [검증 1] 쏘나타 (DN8) 2023 lpg 2.0 2WD 모던 옵션 검증:")
    sonata_opts = catalog.get('쏘나타 (DN8)', {}).get('2023', {}).get('lpg 2.0 2WD 모던', {}).get('options', {})
    for ok, ov in sonata_opts.items():
        if '하이패스' in ok or 'ecm' in ok.lower():
            log(f"     * [{ov.get('source')}] {ok}: {ov.get('price'):,}원")
    assert '하이패스 + ECM' not in sonata_opts, "'하이패스 + ECM' 약칭이 제거되어야 합니다."
    assert '하이패스 시스템 + ECM 룸미러' in sonata_opts, "'하이패스 시스템 + ECM 룸미러' 긴 이름이 유지되어야 합니다."

    # 필수 검증 2: 니로 2016 프레스티지
    log("\n3. [검증 2] 니로 2016 프레스티지 옵션 검증:")
    niro_opts = catalog.get('니로', {}).get('2016', {}).get('프레스티지', {}).get('options', {})
    niro_nav_opts = [k for k in niro_opts if '내비게이션' in k and '1,620,000' in f"{niro_opts[k].get('price'):,}"]
    log(f"   - 1,620,000원 내비게이션 옵션 수: {len(niro_nav_opts)}개")
    for ok in niro_nav_opts:
        log(f"     * [{niro_opts[ok].get('source')}] {ok}: {niro_opts[ok].get('price'):,}원")
    assert len(niro_nav_opts) == 1, f"Expected 1 option for 1,620,000원, got {len(niro_nav_opts)}"
    assert 'UVO 2.0' in niro_nav_opts[0], "UVO 2.0이 포함된 긴 이름이 유지되어야 합니다."

    log("\n✅ [11-11-18] 모든 약칭 옵션 병합 및 필수 검증 100% 성공!")


if __name__ == '__main__':
    run_alias_merge()
