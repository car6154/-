import sys

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_ledger = -1
end_ledger = -1
for i, line in enumerate(lines):
    if line.startswith('# =========================================='):
        if i + 1 < len(lines) and '📝 실시간 장부 자동 계산기' in lines[i+1]:
            start_ledger = i
    if line.startswith('st.markdown("## J-PRO Valuation Dashboard")'):
        end_ledger = i
        break

if start_ledger == -1 or end_ledger == -1:
    print("Could not find blocks.")
    sys.exit(1)

print(f"Ledger lines: {start_ledger} to {end_ledger}")

ledger_lines = lines[start_ledger:end_ledger]
new_ledger_lines = []
for line in ledger_lines:
    line = line.replace('st.sidebar.', 'st.')
    new_ledger_lines.append('    ' + line)

dashboard_idx = end_ledger
dashboard_title = lines[dashboard_idx]

rest_of_file = []
for line in lines[dashboard_idx+1:]:
    rest_of_file.append('    ' + line if line.strip() else line)

new_lines = lines[:start_ledger]
new_lines.append(dashboard_title)
new_lines.append('tab_main, tab_ledger = st.tabs(["📊 시세 조회 및 스캔", "📝 내 장부 관리"])\n\n')
new_lines.append('with tab_ledger:\n')
new_lines.extend(new_ledger_lines)
new_lines.append('    st.markdown("### 📂 내 장부 목록")\n')
new_lines.append('    st.dataframe(st.session_state.my_ledger_data, use_container_width=True)\n\n')
new_lines.append('with tab_main:\n')
new_lines.extend(rest_of_file)

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Success")
