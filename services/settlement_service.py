# services/settlement_service.py
from datetime import datetime
import pandas as pd

def get_auto_fee_rate(volume):
    if volume <= 12: return 0.10
    elif volume <= 18: return 0.30
    elif volume <= 31: return 0.40
    else: return 0.50

def recalc_settlement_df(df, default_rate):
    if df.empty:
        return df
    now_date = datetime.now()
    for idx, row in df.iterrows():
        if df.at[idx, '순차'] == 0:
            df.at[idx, '순차'] = idx + 1

        p_sell = row.get('판매가', 0)
        p_buy = row.get('매입가', 0)
        ext_cnt = row.get('외판수리', 0)

        # 기본제경비가 없으면 15만원
        if row.get('기본제경비', 0) == 0:
            df.at[idx, '기본제경비'] = 15

        # 외판수가 있고 상품화가 0이면 판수 * 13만원
        if row.get('상품화', 0) == 0 and ext_cnt > 0:
            df.at[idx, '상품화'] = int(ext_cnt * 13)

        # 판매수수료: 판매가의 0.7% (0일 때 자동 계산)
        p_fee = row.get('판매수수료', 0)
        calc_fee = int(round(p_sell * 0.007)) if p_sell > 0 else 0
        if p_fee == 0 and calc_fee > 0:
            p_fee = calc_fee
            df.at[idx, '판매수수료'] = p_fee

        # 수수료율: 사용자가 직접 수정한 값이 있으면 그 값을 우선 유지
        curr_rate = row.get('수수료율', 0)
        try: curr_rate = float(curr_rate)
        except: curr_rate = 0.0

        if curr_rate <= 0:
            curr_rate = default_rate
            df.at[idx, '수수료율'] = curr_rate

        # 공헌손익 및 실수익 계산 (상태는 강제로 덮어쓰지 않음)
        if p_sell > 0:
            vat_margin = (p_sell - p_buy) / 1.1
            expenses = row.get('헤딜수수료', 0) + row.get('상품화', 0) + df.at[idx, '기본제경비'] + p_fee
            net_profit = int(round(vat_margin - expenses))
            df.at[idx, '공헌이익'] = net_profit
            df.at[idx, '실수익'] = int(round(net_profit * curr_rate))
        else:
            df.at[idx, '공헌이익'] = 0
            df.at[idx, '실수익'] = 0

        # 상태 기본값 세팅 (기존 값이 없으면 '보유재고')
        if not str(row.get('상태', '')).strip() or str(row.get('상태', '')) == 'nan':
            df.at[idx, '상태'] = '보유재고'

        # 재고일 계산
        m_date_str = str(row.get('매입일', '')).strip()
        try:
            parts = m_date_str.replace(" ", "").split(".")
            if len(parts) >= 2:
                m_dt = datetime(now_date.year, int(parts[0]), int(parts[1]))
                if m_dt > now_date:
                    m_dt = datetime(now_date.year - 1, int(parts[0]), int(parts[1]))
                df.at[idx, '재고일'] = max(0, (now_date - m_dt).days)
        except:
            pass
    return df
