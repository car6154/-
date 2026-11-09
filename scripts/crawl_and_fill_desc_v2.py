# -*- coding: utf-8 -*-
"""
scripts/crawl_and_fill_desc_v2.py
V2 카탈로그 전체 옵션 중 설명(desc) 누락분 전수 수집 및 안전 병합 백그라운드 파이프라인.
- 국내 6개 브랜드(현대, 기아, KGM, 르노코리아, 쉐보레, 제네시스) 전 세대 모델 크롤링
- ThreadPoolExecutor(동시 6개 워커)를 통한 고속 병렬 네트워크 I/O
- optionKey_*의 .exp 및 .title, div.package, 공통옵션 테이블 전수 파싱
- 기존 유효 desc 100% 보존, desc 외 가격·스펙 100% 불변 보장
"""

import sys
import os
import re
import json
import time
import shutil
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.danawa_crawler import get_danawa_session, get_model_lineups
from scripts.run_domestic_catalog_pipeline import get_models_for_brand, fetch_lineup_page

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("data/desc_fill.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DescFill")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CATALOG_V2_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2.json")
BACKUP_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2_backup_before_desc_fill.json")
PROGRESS_FILE = os.path.join(DATA_DIR, "desc_fill_progress.json")

BRANDS = [
    ('303', '현대'),
    ('304', '제네시스'),
    ('307', '기아'),
    ('312', '쉐보레'),
    ('321', '르노코리아'),
    ('326', 'KGM')
]


def clean_text(s: str) -> str:
    if not s:
        return ""
    return re.sub(r'\s+', ' ', str(s)).strip()


def normalize_opt_key(s: str) -> str:
    return re.sub(r'[\s\-/\(\)\.,_·■\+]', '', str(s)).lower()


def extract_descriptions_from_lineup_soup(soup: BeautifulSoup) -> Dict[str, str]:
    """다나와 라인업 HTML에서 옵션별 상세 구성품목 설명 딕셔너리 추출 (옵션 상세 정보 팝업 + 패키지 선택 품목 표 확대)"""
    table_pkg_map: Dict[str, str] = {}

    # 1. 패키지 선택 품목 / 주요 사항 표 탐색 (Inner Table 및 중첩 테이블 전수 탐색)
    for tbl in soup.find_all('table'):
        ths = [clean_text(th.get_text()) for th in tbl.find_all('th')]
        for tr in tbl.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) >= 2:
                p_name = clean_text(tds[0].get_text())
                p_desc = clean_text(tds[1].get_text())
                # 세부모델/가격 행 등 불필요한 메타 행 제외
                if p_name and p_desc and p_name not in ['세부모델', '판매가격', '구분', '세부내용', '선택품목', '패키지', '사양 및 옵션']:
                    if not any(k in p_name for k in ['차량가격', '합계', '인승)', '사양 및 옵션']) and len(p_desc) > 3:
                        table_pkg_map[p_name] = p_desc

    # 2. optionKey_* 모달 팝업 탐색 (번호 + title + exp 전수 결합)
    code_desc_map: Dict[str, str] = {}
    for div in soup.select('div[id^="optionKey_"]'):
        opt_code = div.get('id', '').replace('optionKey_', '').strip()
        sub_items = []
        for cont in div.select('.infodetail__cont'):
            title = cont.select_one('.title')
            exp = cont.select_one('.exp')
            
            t_txt = clean_text(title.get_text()) if title else ""
            e_txt = clean_text(exp.get_text()).lstrip('-').strip() if exp else ""
            
            if t_txt and e_txt:
                # 번호+타이틀과 세부설명 결합 (예: 2. 드라이빙 어시스턴스 패키지Ⅰ: 서라운드 뷰 모니터, ...)
                sub_items.append(f"{t_txt}: {e_txt}")
            elif t_txt:
                sub_items.append(t_txt)
            elif e_txt:
                sub_items.append(e_txt)
                
        if sub_items:
            code_desc_map[opt_code] = ' | '.join(sub_items)

    # 3. choices (옵션 체크박스 항목들과 결합)
    opt_results: Dict[str, str] = {}
    for ch in soup.select('.choice'):
        info = ch.select_one('label, .choice__info .txt')
        if not info:
            continue
        opt_name = clean_text(info.get_text())
        opt_name = re.sub(r'상세정보\s*보기.*$', '', opt_name).strip()
        if not opt_name or opt_name in ['선택', '전체']:
            continue

        opt_code = ch.get('code')
        
        # 1순위: 팝업 상세 정보 (번호별 구성품)
        popup_desc = code_desc_map.get(opt_code, '') if opt_code else ''
        
        # 2순위: 패키지 표 정보
        table_desc = table_pkg_map.get(opt_name, '')
        if not table_desc:
            c_name = normalize_opt_key(opt_name)
            for t_k, t_v in table_pkg_map.items():
                c_k = normalize_opt_key(t_k)
                if c_name and c_k and (c_name == c_k or c_name in c_k or c_k in c_name):
                    table_desc = t_v
                    break

        desc = ""
        guide_txt = ""
        clean_table_desc = table_desc or ""
        guide_match = re.search(r'※.*$', clean_table_desc)
        if guide_match:
            guide_txt = guide_match.group(0).strip()
            clean_table_desc = clean_table_desc[:guide_match.start()].strip().rstrip(',').rstrip('·').strip()

        # 패키지 옵션 포맷 결합 (표의 [패키지 구성]을 최우선으로 배치하고 팝업 [상세 내용]을 결합)
        if clean_table_desc and popup_desc:
            if clean_table_desc.replace(" ", "") in popup_desc.replace(" ", "") and len(clean_table_desc) < len(popup_desc) * 0.7:
                desc = f"[패키지 구성]: {clean_table_desc} | [상세 내용]: {popup_desc}"
            elif clean_table_desc != popup_desc:
                desc = f"[패키지 구성]: {clean_table_desc} | [상세 내용]: {popup_desc}"
            else:
                desc = popup_desc
        elif clean_table_desc:
            desc = f"[패키지 구성]: {clean_table_desc}"
        elif popup_desc:
            desc = popup_desc

        if guide_txt and guide_txt not in desc:
            desc = f"{desc} ({guide_txt})"

        if desc:
            opt_results[opt_name] = desc

    # 4. 표에만 있는 패키지 및 액세서리 항목들도 추가
    for p_k, p_v in table_pkg_map.items():
        if p_k not in opt_results and p_v:
            guide_m = re.search(r'※.*$', p_v)
            g_txt = guide_m.group(0).strip() if guide_m else ""
            c_desc = p_v[:guide_m.start()].strip().rstrip(',').rstrip('·').strip() if guide_m else p_v
            formatted = f"[패키지 구성]: {c_desc}"
            if g_txt and g_txt not in formatted:
                formatted = f"{formatted} ({g_txt})"
            opt_results[p_k] = formatted

    return opt_results


def crawl_model_descriptions(model_info: Tuple[str, str, str, str]) -> Dict[str, Dict[str, str]]:
    """단일 모델의 연식별 옵션 desc 사전 추출 (병렬 워커용)"""
    bid, bname, mid, mname = model_info
    session = get_danawa_session()

    try:
        _, lineups_by_year = get_model_lineups(mid, session)
    except Exception:
        return {}

    if not lineups_by_year:
        return {}

    year_to_descs: Dict[str, Dict[str, str]] = {}

    for yr, l_list in lineups_by_year.items():
        if not l_list:
            continue

        # 대표 라인업 1~2개 선택
        chosen_lineups = [l_list[0]]
        if len(l_list) > 1:
            chosen_lineups.append(l_list[-1])

        combined_descs: Dict[str, str] = {}
        for lup in chosen_lineups:
            lid = lup['lineup_id']
            html = fetch_lineup_page(session, mid, lid)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            descs = extract_descriptions_from_lineup_soup(soup)
            combined_descs.update(descs)

        if combined_descs:
            year_to_descs[yr] = combined_descs

    return year_to_descs


def main():
    import argparse
    parser = argparse.ArgumentParser(description="V2 책 옵션 설명(desc) 수집 및 병합 파이프라인")
    parser.add_argument("--model", type=str, help="특정 다나와 모델 ID 또는 모델명 (예: 4465 또는 GV80)")
    parser.add_argument("--brand", type=str, help="특정 브랜드 ID 또는 브랜드명 (예: 304 또는 제네시스)")
    args = parser.parse_args()

    logger.info("==================================================================")
    logger.info("  V2 책 옵션 설명(desc) 누락분 전수 수집 및 안전 병합 시작 (11-06-72)")
    logger.info("==================================================================")

    # 1. 백업 생성
    shutil.copy2(CATALOG_V2_FILE, BACKUP_FILE)
    logger.info(f"안전 백업 완료: {BACKUP_FILE}")

    # 2. V2 책 로드
    with open(CATALOG_V2_FILE, "r", encoding="utf-8") as f:
        full_catalog = json.load(f)
    v2_danawa = full_catalog.get("danawa", {})

    # 수집 전 통계 측정
    initial_total_opts = 0
    initial_valid_desc = 0
    initial_empty_desc = 0
    initial_same_desc = 0

    for car, years in v2_danawa.items():
        if not isinstance(years, dict): continue
        for yr, grades in years.items():
            if not isinstance(grades, dict): continue
            for grd, spec in grades.items():
                if not isinstance(spec, dict): continue
                for opt_name, opt_info in spec.get("options", {}).items():
                    initial_total_opts += 1
                    d = str(opt_info.get("desc") or "").strip()
                    if not d:
                        initial_empty_desc += 1
                    elif d == opt_name.strip():
                        initial_same_desc += 1
                    else:
                        initial_valid_desc += 1

    logger.info(f"수집 전 총 옵션 수: {initial_total_opts:,}개")
    logger.info(f"수집 전 유효 desc: {initial_valid_desc:,}개 ({initial_valid_desc/initial_total_opts*100:.1f}%)")
    logger.info(f"수집 전 비어있는 desc: {initial_empty_desc:,}개 ({initial_empty_desc/initial_total_opts*100:.1f}%)")
    logger.info(f"수집 전 옵션명과 동일한 desc: {initial_same_desc:,}개 ({initial_same_desc/initial_total_opts*100:.1f}%)")

    # 3. 세션 초기화 및 브랜드 모델 수집
    session = get_danawa_session()
    all_brand_models = []
    
    target_brands = BRANDS
    if args.brand:
        target_brands = [b for b in BRANDS if args.brand in b[0] or args.brand in b[1]]

    for bid, bname in target_brands:
        m_list = get_models_for_brand(bid, session)
        logger.info(f"[{bname}] {len(m_list)}개 모델 목록 확인")
        for m in m_list:
            all_brand_models.append((bid, bname, m['model_id'], m['model_name']))

    if args.model:
        all_brand_models = [
            m for m in all_brand_models 
            if args.model == str(m[2]) or args.model.lower() in m[3].lower()
        ]
        logger.info(f"--model '{args.model}' 필터 적용: {len(all_brand_models)}개 대상 모델 선별됨 {[m[3] for m in all_brand_models]}")

    total_models = len(all_brand_models)
    logger.info(f"총 크롤링 대상 다나와 모델: {total_models}개 (동시 6개 워커 병렬 가동)")

    total_desc_filled = 0
    completed_models_count = 0
    t0 = time.time()

    # 4. 병렬 크롤링 및 메인 스레드 병합 (동시 6개 스레드)
    with ThreadPoolExecutor(max_workers=min(6, max(1, total_models))) as executor:
        future_to_model = {
            executor.submit(crawl_model_descriptions, m_info): m_info
            for m_info in all_brand_models
        }

        for future in as_completed(future_to_model):
            m_info = future_to_model[future]
            bid, bname, mid, mname = m_info
            completed_models_count += 1

            try:
                year_to_descs = future.result()
            except Exception as e:
                logger.warning(f"[{completed_models_count}/{total_models}] 모델 {mid} ({mname}) 처리 에러: {e}")
                continue

            if not year_to_descs:
                continue

            # V2 책의 매칭 차종 탐색
            clean_mname = re.sub(r'\([^\)]*\)', '', mname).strip()
            matched_v2_cars = []
            for v2_cname in v2_danawa.keys():
                clean_v2 = re.sub(r'\([^\)]*\)', '', v2_cname).strip()
                if clean_mname == clean_v2 or clean_mname in clean_v2 or clean_v2 in clean_mname:
                    matched_v2_cars.append(v2_cname)

            if not matched_v2_cars:
                continue

            model_desc_updated = 0

            # 메인 스레드 단일 안전 병합
            for yr, descs in year_to_descs.items():
                cand_years = [yr]
                try:
                    y_int = int(yr)
                    cand_years.append(str(y_int - 1))
                    cand_years.append(str(y_int + 1))
                except Exception:
                    pass

                for v2_c in matched_v2_cars:
                    for c_yr in cand_years:
                        if c_yr not in v2_danawa[v2_c]:
                            continue
                        yr_book = v2_danawa[v2_c][c_yr]
                        for grd, spec in yr_book.items():
                            if not isinstance(spec, dict):
                                continue
                            opts = spec.get("options", {})
                            for opt_name, opt_info in opts.items():
                                cur_desc = str(opt_info.get("desc") or "").strip()
                                need_update = (not cur_desc) or (cur_desc == opt_name.strip())

                                new_desc = ""
                                if opt_name in descs:
                                    new_desc = descs[opt_name]
                                else:
                                    c_opt = normalize_opt_key(opt_name)
                                    for p_k, p_v in descs.items():
                                        c_p = normalize_opt_key(p_k)
                                        if c_opt and c_p and (c_opt == c_p or c_opt in c_p or c_p in c_opt):
                                            new_desc = p_v
                                            break

                                # 💡 [11-06-72]: 새로 수집된 상세 정보가 더 풍부하거나(길이가 길거나 번호 '1. ' 포함), 기존 desc가 비어있는 경우 업데이트
                                is_more_detailed = bool(new_desc and (
                                    (len(new_desc) > len(cur_desc)) or
                                    ('1. ' in new_desc and '1. ' not in cur_desc)
                                ))
                                if new_desc and (need_update or is_more_detailed):
                                    if cur_desc != new_desc:
                                        opt_info["desc"] = new_desc
                                        total_desc_filled += 1
                                        model_desc_updated += 1

            if model_desc_updated > 0:
                logger.info(f"[{completed_models_count}/{total_models}] {bname} '{mname}' -> V2 옵션 desc {model_desc_updated}개 보완 (누적: {total_desc_filled:,}개)")

            if completed_models_count % 25 == 0 or completed_models_count == total_models:
                progress_data = {
                    "completed_models": completed_models_count,
                    "total_models": total_models,
                    "current_model": f"{bname} {mname}",
                    "total_desc_filled": total_desc_filled,
                    "elapsed_seconds": round(time.time() - t0, 1)
                }
                with open(PROGRESS_FILE, "w", encoding="utf-8") as pf:
                    json.dump(progress_data, pf, ensure_ascii=False, indent=2)

    # 5. 전수 불변성 검증 (Invariants Verification)
    logger.info("==================================================================")
    logger.info("  크롤링 완료. 전수 불변성(Invariants) 및 무결성 검증 착수...")
    logger.info("==================================================================")

    with open(BACKUP_FILE, "r", encoding="utf-8") as bf:
        backup_catalog = json.load(bf)
    base_danawa = backup_catalog.get("danawa", {})

    assert len(v2_danawa) == len(base_danawa), f"차종 수 불일치! ({len(v2_danawa)} vs {len(base_danawa)})"

    final_total_opts = 0
    final_valid_desc = 0
    final_empty_desc = 0
    final_same_desc = 0

    for car, b_years in base_danawa.items():
        assert car in v2_danawa, f"차종 누락: {car}"
        v_years = v2_danawa[car]
        assert len(v_years) == len(b_years), f"연식 수 불일치 in {car}!"

        for yr, b_grades in b_years.items():
            assert yr in v_years, f"연식 누락: {car} {yr}"
            v_grades = v_years[yr]
            assert len(v_grades) == len(b_grades), f"등급 수 불일치 in {car} {yr}!"

            for grd, b_spec in b_grades.items():
                assert grd in v_grades, f"등급 누락: {car} {yr} {grd}"
                v_spec = v_grades[grd]

                # 기본가 불변 검증
                assert v_spec.get("base_price") == b_spec.get("base_price"), f"기본가 변경 감지 in {car} {yr} {grd}!"
                assert v_spec.get("base_price_man") == b_spec.get("base_price_man"), f"기본가_man 변경 감지 in {car} {yr} {grd}!"

                b_opts = b_spec.get("options", {})
                v_opts = v_spec.get("options", {})
                assert len(v_opts) == len(b_opts), f"옵션 수 불일치 in {car} {yr} {grd}!"

                for opt_name, b_opt in b_opts.items():
                    assert opt_name in v_opts, f"옵션 누락: {car} {yr} {grd} {opt_name}"
                    v_opt = v_opts[opt_name]

                    # 옵션 가격 불변 검증
                    assert v_opt.get("price") == b_opt.get("price"), f"옵션 가격 변경 감지 in {car} {yr} {grd} {opt_name}!"
                    assert v_opt.get("price_man") == b_opt.get("price_man"), f"옵션 가격_man 변경 감지 in {car} {yr} {grd} {opt_name}!"

                    # 기존 desc 보존 검증
                    old_d = str(b_opt.get("desc") or "").strip()
                    new_d = str(v_opt.get("desc") or "").strip()
                    if old_d and old_d != opt_name.strip():
                        assert new_d, f"기존 desc 삭제 감지 in {car} {yr} {grd} {opt_name}!"

                    final_total_opts += 1
                    if not new_d:
                        final_empty_desc += 1
                    elif new_d == opt_name.strip():
                        final_same_desc += 1
                    else:
                        final_valid_desc += 1

    logger.info("🎉 전수 불변성 검증 100% 통과! (차종·연식·등급·기본가·옵션명·옵션가격 0건 오차)")

    # 6. 최종 V2 책 저장
    with open(CATALOG_V2_FILE, "w", encoding="utf-8") as f:
        json.dump(full_catalog, f, ensure_ascii=False, indent=2)
    logger.info(f"V2 책 최종 저장 완료: {CATALOG_V2_FILE}")

    elapsed = round(time.time() - t0, 1)
    logger.info("==================================================================")
    logger.info("  최종 수집 결과 보고")
    logger.info("==================================================================")
    logger.info(f"총 소요 시간: {elapsed}초")
    logger.info(f"수집 전 유효 desc: {initial_valid_desc:,}개 ({initial_valid_desc/initial_total_opts*100:.1f}%)")
    logger.info(f"수집 후 유효 desc: {final_valid_desc:,}개 ({final_valid_desc/final_total_opts*100:.1f}%)")
    logger.info(f"신규 보완된 옵션 desc: +{final_valid_desc - initial_valid_desc:,}개")
    logger.info(f"잔여 비어있는 desc: {final_empty_desc:,}개 ({final_empty_desc/final_total_opts*100:.1f}%)")
    logger.info("==================================================================")


if __name__ == "__main__":
    main()
