
import pandas as pd
df = pd.read_csv('autoplus_inventory.csv', encoding='utf-8-sig')
col_map = {}
for col in df.columns:
    clean_col = str(col).replace(' ', '').lower()
    if '차종' in clean_col or '차량명' in clean_col: col_map[col] = '차량명'
    elif '세부모델' in clean_col: col_map[col] = '세부모델'
    elif '최초등록일' in clean_col: col_map[col] = '연식'
df = df.rename(columns=col_map)
full_names = df['차량명'].astype(str) + ' ' + df['세부모델'].astype(str)
full_names_clean = full_names.str.replace(' ', '').str.lower()
m1 = full_names_clean.str.contains('렉스턴스포츠', na=False)
sub_parts = '디젤 2.2 4WD 프레스티지'.split()
m2 = m1.copy()
for part in sub_parts:
    p_clean = part.replace(' ', '').lower()
    m2 = m2 & full_names_clean.str.contains(p_clean, na=False)

matched_df = df[m2]
print('Years in matched_df:', matched_df['연식'].tolist())

# Now test current_f_year = '19'
for yr in ['19', '2019', '18', '20']:
    print(f'Match for year {yr}:', matched_df['연식'].astype(str).str.contains(yr, na=False).sum())
