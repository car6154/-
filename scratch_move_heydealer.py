import sys

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find start of Heydealer block
start_idx = -1
for i, line in enumerate(lines):
    if 'st.subheader("🤖 헤이딜러 AI 매입 견적 (자동 수집)")' in line:
        start_idx = i - 1 # Include the st.markdown("---") before it
        break

# Find end of Heydealer block
end_idx = -1
for i, line in enumerate(lines[start_idx:]):
    if line.startswith('# 강제 리로드 트리거'):
        end_idx = start_idx + i
        break

if start_idx == -1 or end_idx == -1:
    print("Could not find block boundaries")
    sys.exit(1)

heydealer_block = lines[start_idx:end_idx]

# Find tabs definition
tabs_idx = -1
for i, line in enumerate(lines):
    if 'tab_main, tab_sales, tab_inventory, tab_ledger = st.tabs' in line:
        tabs_idx = i
        break

if tabs_idx == -1:
    print("Could not find tabs definition")
    sys.exit(1)

# Find ai_summary_placeholder definition
placeholder_idx = -1
for i, line in enumerate(lines):
    if 'ai_summary_placeholder = st.sidebar.empty()' in line:
        placeholder_idx = i
        break

if placeholder_idx == -1:
    print("Could not find placeholder definition")
    sys.exit(1)

# Now we need to reassemble the file.
# We remove the heydealer_block from its original position
new_lines_1 = lines[:start_idx] + lines[end_idx:]

# We need to find the new indices in new_lines_1
new_tabs_idx = -1
new_placeholder_idx = -1
for i, line in enumerate(new_lines_1):
    if 'tab_main, tab_sales, tab_inventory, tab_ledger = st.tabs' in line:
        new_tabs_idx = i
    if 'ai_summary_placeholder = st.sidebar.empty()' in line:
        new_placeholder_idx = i

if new_tabs_idx == -1 or new_placeholder_idx == -1:
    print("Could not find indices after removing block")
    sys.exit(1)

# Remove the placeholder definition
placeholder_line = new_lines_1.pop(new_placeholder_idx)

# Recalculate tabs_idx as it might have shifted
new_tabs_idx = -1
for i, line in enumerate(new_lines_1):
    if 'tab_main, tab_sales, tab_inventory, tab_ledger = st.tabs' in line:
        new_tabs_idx = i
        break

# Insert placeholder and heydealer_block before tabs_idx
final_lines = new_lines_1[:new_tabs_idx] + [placeholder_line] + heydealer_block + new_lines_1[new_tabs_idx:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(final_lines)

print("Successfully moved Heydealer block.")
