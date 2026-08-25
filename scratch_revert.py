import sys

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

tab_idx = -1
end_ledger_idx = -1
main_tab_idx = -1
for i, line in enumerate(lines):
    if 'tab_main, tab_ledger = st.tabs' in line:
        tab_idx = i
    if line.startswith('with tab_main:\n'):
        main_tab_idx = i
        break

if tab_idx == -1 or main_tab_idx == -1:
    print("Could not find tabs")
    sys.exit(1)

# Extract ledger lines
# tab_idx + 1 is \n
# tab_idx + 2 is with tab_ledger:\n
# Ledger lines are from tab_idx + 3 to main_tab_idx - 1 (excluding the dataframe display we added)
# Wait, let's find the start of the dataframe display
df_display_idx = -1
for i in range(tab_idx, main_tab_idx):
    if 'st.markdown("### 📂 내 장부 목록")' in line or 'st.markdown("### 📂 내 장부 목록")' in lines[i]:
        df_display_idx = i
        break

if df_display_idx == -1:
    df_display_idx = main_tab_idx - 1

ledger_lines = lines[tab_idx + 3:df_display_idx]

# revert ledger lines: remove 4 spaces indent, replace 'st.' with 'st.sidebar.' (except where it already was st.sidebar., but we replaced all of them)
# Wait, replacing all 'st.' with 'st.sidebar.' is dangerous because of things like st.session_state!
# Ah, st.session_state wasn't replaced because it was st.sidebar., we replaced 'st.sidebar.' with 'st.'. 
# So to revert, we replace 'st.' with 'st.sidebar.', but ONLY for the UI components.
# Let's just restore them by replacing 'st.success', 'st.text_input', 'st.number_input', 'st.radio', 'st.markdown', 'st.info', 'st.text_area', 'st.button', 'st.error' with 'st.sidebar...'
ui_components = ['success', 'text_input', 'number_input', 'radio', 'markdown', 'info', 'text_area', 'button', 'error']
reverted_ledger_lines = []
for line in ledger_lines:
    if line.startswith('    '):
        line = line[4:] # unindent
    for comp in ui_components:
        line = line.replace(f'st.{comp}', f'st.sidebar.{comp}')
    reverted_ledger_lines.append(line)

# Now extract the main block
main_lines = []
for line in lines[main_tab_idx + 1:]:
    if line.startswith('    '):
        main_lines.append(line[4:])
    else:
        main_lines.append(line)

# Now assemble
new_lines = lines[:tab_idx] + reverted_ledger_lines + main_lines

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Reverted successfully")
