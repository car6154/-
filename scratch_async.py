import streamlit as st
import threading
import time
from streamlit.runtime.scriptrunner import add_script_run_ctx

def ai_background_task(prompt):
    time.sleep(5)
    st.session_state.ai_status = "완료"
    st.session_state.ai_estimate_result = f"계산 완료: {prompt}"

if st.button("계산 시작"):
    st.session_state.ai_status = "진행중"
    t = threading.Thread(target=ai_background_task, args=("프롬프트",))
    add_script_run_ctx(t)
    t.start()

@st.fragment(run_every=2)
def poll_ai_status():
    if st.session_state.get("ai_status") == "진행중":
        st.info("AI가 계산 중입니다... (다른 작업을 하셔도 됩니다)")
    elif st.session_state.get("ai_status") == "완료":
        st.success(st.session_state.get("ai_estimate_result"))
        # We might want to stop the auto-run. We can just set status to "표시됨"
        st.session_state.ai_status = "표시됨"
        st.rerun() # Rerun the whole app to show the result normally

if st.session_state.get("ai_status") in ["진행중", "완료"]:
    poll_ai_status()
elif st.session_state.get("ai_status") == "표시됨":
    st.success(st.session_state.get("ai_estimate_result"))
