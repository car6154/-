# analysis.py
import pandas as pd
import re
import matplotlib.pyplot as plt
import matplotlib
from utils import logger

matplotlib.rcParams['font.family'] = 'Malgun Gothic'
matplotlib.rcParams['axes.unicode_minus'] = False

class PriceAnalyzer:
    @staticmethod
    def analyze(df, target_mileage=None):
        if df.empty: return None
        price_col = PriceAnalyzer._find_price_column(df.columns)
        if not price_col: return None

        try:
            # [버그 수정 1] 소수점(.)을 보존하여 10배 뻥튀기 오류 방지
            prices_str = df[price_col].astype(str).str.replace(r'[^0-9.]', '', regex=True)
            prices = pd.to_numeric(prices_str, errors='coerce').dropna()
            
            if prices.empty: return None

            # [버그 수정 2] 가격 중앙값이 20,000 이상이면 '원' 단위로 판단하고 '만원' 단위로 자동 축소
            if prices.median() > 20000:
                prices = prices / 10000

            Q1 = prices.quantile(0.25)
            Q3 = prices.quantile(0.75)
            IQR = Q3 - Q1
            normal_prices = prices[(prices >= (Q1 - 1.5 * IQR)) & (prices <= (Q3 + 1.5 * IQR))]
            
            if normal_prices.empty:
                normal_prices = prices

            stats = {
                'min': int(normal_prices.min()),
                'max': int(normal_prices.max()),
                'mean': int(normal_prices.mean()),
                'median': int(normal_prices.median()),
                'count': len(normal_prices)
            }
            
            base_suggested = stats['median'] * 0.90
            
            if target_mileage and str(target_mileage).isdigit():
                target_km = int(target_mileage)
                mileage_col = next((c for c in df.columns if '주행' in str(c) or 'km' in str(c).lower()), None)
                if mileage_col:
                    km_series = pd.to_numeric(df[mileage_col].astype(str).str.replace(r'[^0-9]', '', regex=True), errors='coerce').dropna()
                    if not km_series.empty:
                        median_km = km_series.median()
                        diff_km = median_km - target_km
                        adjustment = (diff_km / 10000) * (stats['median'] * 0.015)
                        base_suggested += adjustment
                        
            stats['suggested'] = int(base_suggested)
            return stats
        except Exception as e:
            logger.error(f"시세 분석 중 오류 발생: {e}")
            return None

    @staticmethod
    def draw_price_distribution_chart(df):
        price_col = PriceAnalyzer._find_price_column(df.columns)
        if not price_col or df.empty: return None
        try:
            prices_str = df[price_col].astype(str).str.replace(r'[^0-9.]', '', regex=True)
            prices = pd.to_numeric(prices_str, errors='coerce').dropna()
            if prices.empty: return None
            
            if prices.median() > 20000:
                prices = prices / 10000
                
            fig, ax = plt.subplots(figsize=(5, 3.5))
            ax.hist(prices, bins=15, color='#2E86C1', edgecolor='black', alpha=0.7)
            ax.set_title("시세 가격 분포 현황", fontsize=11, fontweight='bold')
            ax.set_xlabel("가격 (만원)", fontsize=9)
            ax.set_ylabel("매물 수", fontsize=9)
            plt.tight_layout()
            return fig
        except Exception as e:
            logger.error(f"그래프 생성 실패: {e}")
            return None

    @staticmethod
    def _find_price_column(columns):
        keywords = ['가격', '판매가', '시세', '금액', 'price', '입찰가', '시작가', '매각가', '최고가', '매입가']
        for col in columns:
            col_str = str(col).lower()
            for kw in keywords:
                if kw in col_str: return col
        return None