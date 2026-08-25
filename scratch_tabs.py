import sys

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

dash_start = -1
ledger_list_start = -1

for i, line in enumerate(lines):
    if line.startswith('st.markdown("## J-PRO Valuation Dashboard")'):
        dash_start = i
    if line.startswith('st.markdown("### 📋 내 실전 장부 리스트")'):
        ledger_list_start = i

if dash_start == -1 or ledger_list_start == -1:
    print("Could not find targets")
    sys.exit(1)

# we want to insert tabs at dash_start + 1
# wrap lines[dash_start+1 : ledger_list_start - 1] in with tab1:
# wrap lines[ledger_list_start : end] in with tab2:

new_lines = lines[:dash_start+1]
new_lines.append('\ntab_main, tab_ledger = st.tabs(["📊 시세 조회 및 스캔", "📋 내 실전 장부 리스트"])\n\n')
new_lines.append('with tab_main:\n')

# indent main dashboard
for line in lines[dash_start+1:ledger_list_start]:
    if line.startswith('st.markdown("---")') and (ledger_list_start - i) < 5: 
        # ignore the separator just before ledger list
        pass 
    if line.strip() == '':
        new_lines.append(line)
    elif line == 'st.markdown("---")\n' and lines.index(line) == ledger_list_start - 1:
        pass
    else:
        new_lines.append('    ' + line)

new_lines.append('\nwith tab_ledger:\n')
for line in lines[ledger_list_start:]:
    if line.strip() == '':
        new_lines.append(line)
    else:
        new_lines.append('    ' + line)

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Tabs created successfully")
