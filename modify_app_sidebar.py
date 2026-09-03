import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the ai_status handling at the bottom of the sidebar area.
# Specifically, around line 1424 (under the text_inputs in the sidebar).

sidebar_addition = """
    st.session_state.hd_target_plate = st.sidebar.text_input("차량번호", value=str(st.session_state.hd_target_plate))

ai_status = st.session_state.get("ai_status")
if ai_status == "진행중":
    st.sidebar.info("🤖 AI가 매입 견적을 산출 중입니다... (약 5~10초 소요)")
elif ai_status in ["완료", "표시됨"]:
    st.sidebar.success("✅ AI 매입 견적 산출 완료! 우측 하단을 확인하세요.")
elif ai_status == "오류":
    st.sidebar.error("❌ AI 매입 견적 산출 실패")
"""

content = content.replace(
    '    st.session_state.hd_target_plate = st.sidebar.text_input("차량번호", value=str(st.session_state.hd_target_plate))\n',
    sidebar_addition
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("app.py updated with sidebar status")
