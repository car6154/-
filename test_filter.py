
import sys
import pandas as pd

df = pd.read_csv('autoplus_inventory.csv', encoding='utf-8-sig')
col_map = {}
for col in df.columns:
    clean_col = str(col).replace(' ', '').lower()
    if '차종' in clean_col or '차량명' in clean_col: col_map[col] = '차량명'
    elif '세부모델' in clean_col: col_map[col] = '세부모델'
    elif '최초등록일' in clean_col: col_map[col] = '연식'
    elif '경과일수' in clean_col: col_map[col] = '재고'
    elif '할인적용가' in clean_col: col_map[col] = '판매가_할인'
    elif '지점판매가' in clean_col: col_map[col] = '판매가_지점'
    elif 'eurl' in clean_col: col_map[col] = '링크'

df = df.rename(columns=col_map)
print('Total rows:', len(df))
print('홈페이지상태 distribution:', df['홈페이지상태'].value_counts().to_dict())

full_names = df['차량명'].astype(str) + ' ' + df['세부모델'].astype(str)
full_names_clean = full_names.str.replace(' ', '').str.lower()

# Test with 렉스턴스포츠
name_clean = '렉스턴스포츠'
m1 = full_names_clean.str.contains(name_clean, na=False)
print(f'Matches for {name_clean}:', m1.sum())

# Test with submodel 디젤 2.2 4WD 프레스티지
sub_parts = '디젤 2.2 4WD 프레스티지'.split()
m2 = m1.copy()
for part in sub_parts:
    p_clean = part.replace(' ', '').lower()
    m2 = m2 & full_names_clean.str.contains(p_clean, na=False)
print(f'Matches after all subparts of {sub_parts}:', m2.sum())

# Let us print the actual names in autoplus for rexton sports
rexton_names = df.loc[m1, ['차량명', '세부모델', '연식', '홈페이지상태']].head(10)
print('Rexton sample:')
print(rexton_names.to_string())
