import os
import re
import glob
import time
import datetime
import streamlit as st
import streamlit.components.v1 as components
import matplotlib.pyplot as plt
from google import genai
from google.genai import types

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="과학고 물리 AI 튜터",
    page_icon="⚛️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# 2. 모바일 친화적 반응형 CSS (DOM 충돌 유발 코드 완전 배제)
st.markdown("""
<style>
/* 메인 타이틀 크기 조정 */
h1 { font-size: 1.45rem !important; font-weight: 700 !important; margin-bottom: 0.2rem !important; }

/* 단계별 소제목 크기 단정하게 축소 */
.stMarkdown h1 { font-size: 1.15rem !important; font-weight: 700 !important; margin-top: 10px !important; margin-bottom: 4px !important; }
.stMarkdown h2 { font-size: 1.05rem !important; font-weight: 600 !important; margin-top: 8px !important; margin-bottom: 4px !important; }
.stMarkdown h3 { font-size: 0.98rem !important; font-weight: 600 !important; margin-top: 6px !important; margin-bottom: 3px !important; }
.stMarkdown h4 { font-size: 0.92rem !important; font-weight: 600 !important; }

/* 상단/하단 불필요한 기본 UI 숨김 */
#MainMenu { visibility: hidden !important; display: none !important; }
.stDeployButton, .stAppDeployButton { display: none !important; }
div[data-testid="stDecoration"] { display: none !important; }
div[data-testid="stToolbar"] { visibility: hidden !important; display: none !important; }
div[data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }
footer { display: none !important; visibility: hidden !important; height: 0px !important; }
div[data-testid="stFooter"] { display: none !important; visibility: hidden !important; height: 0px !important; }
div[data-testid="stBottom"] footer { display: none !important; visibility: hidden !important; }

/* 모바일 가상 키보드 팝업 시 입력창 떨림 방지 */
.stChatInputContainer {
    padding-bottom: 10px !important;
}

/* 대기 시간 애니메이션 */
@keyframes tutorPulse {
    0% { transform: scale(1); opacity: 0.8; }
    50% { transform: scale(1.18); opacity: 1; filter: drop-shadow(0 0 8px #4A90E2); }
    100% { transform: scale(1); opacity: 0.8; }
}
@keyframes spinSlow {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
.thinking-box {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    background-color: rgba(74, 144, 226, 0.08);
    border-radius: 10px;
    margin-bottom: 12px;
}
.tutor-active-icon { font-size: 24px; display: inline-block; animation: tutorPulse 1.4s infinite ease-in-out; }
.tutor-atom-icon { font-size: 22px; display: inline-block; animation: spinSlow 3s linear infinite; }
.thinking-text { color: #4A90E2; font-weight: 600; font-size: 0.95rem; }
</style>
""", unsafe_allow_html=True)

# 3. API 키 설정
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY가 설정되지 않았습니다.")
    st.stop()

client = genai.Client(api_key=api_key)

# 4. 저장소 내 모든 강의록 자동 탐색 및 병합
def load_all_lecture_notes():
    combined_notes = ""
    all_files = glob.glob("lecture_*.md") + glob.glob("data/*.md") + glob.glob("*.md")
    loaded_files = set()

    for file_path in all_files:
        if file_path in loaded_files or "README" in file_path:
            continue
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    combined_notes += f"\n\n========================================\n"
                    combined_notes += f"--- [단원 강의록: {os.path.basename(file_path)}] ---\n"
                    combined_notes += f"========================================\n"
                    combined_notes += content
                    loaded_files.add(file_path)
        except Exception:
            pass

    return combined_notes, list(loaded_files)

lecture_knowledge, loaded_file_list = load_all_lecture_notes()

# 5. 유연하고 깊이 있는 물리 AI 튜터 지침
PHYSICS_INSTRUCTION = f"""
당신은 과학고등학교 물리 교사의 강의 지식과 교육 철학을 계승한 전용 AI 튜터입니다.

[지식 활용 가이드]
1. 학생의 질문이 아래 [선생님 전용 강의록]에 포함된 내용이라면, 반드시 강의록의 판서 유도 순서, 핵심 직관, 오개념 주의사항을 최우선 기준으로 삼아 지도하세요.
2. 강의록에 없는 다른 단원이나 심화 물리 질문이라도 일반물리학/고급물리 지식을 총동원하여 친절하고 깊이 있게 지도하세요.

[선생님 전용 강의록 (누적 데이터)]
{lecture_knowledge}

[시각 자료 및 시뮬레이션 작성 규칙]
1. 단순 정적 그래프/도식: Python matplotlib 코드를 ```python ... ``` 코드 블록으로 작성하세요. (plt.show() 제외)
2. 동적 인터랙티브 시뮬레이션: HTML5 Canvas와 JavaScript로 작성된 독립 실행형 웹 시뮬레이터를 ```html ... ``` 코드 블록으로 작성하세요.
3. 텍스트 기호(ASCII 아트)로 그림을 그리는 것은 절대 금지합니다.

[수식 및 발문 원칙]
1. 문장 속 인라인 수식($...$), 독립 블록 수식($$...$$) 규칙을 철저히 지키세요.
2. 학생에게 정답을 바로 주지 말고, 과학적 발상과 판서 단계를 바탕으로 소크라테스식 힌트를 단계별로 제공하세요.
"""

# 6. 메인 타이틀 및 상단 컨트롤 대시보드
st.title("⚛️ 과학고 물리 AI 튜터")
st.caption("선생님의 강의 영상과 교재 내용을 기반으로 심화 물리 탐구를 돕습니다.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# 메인 화면 상단 접이식 관리 패널
with st.expander("🛠️ 탑재된 강의 단원 확인 및 나의 학습 관리 열기", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.write("📂 **현재 학습 완료된 단원 목록**")
        if loaded_file_list:
            for f_name in loaded_file_list:
                st.markdown(f"- 📄 `{os.path.basename(f_name)}`")
        else:
            st.info("등록된 강의록 파일이 없습니다.")
            
    with col2:
        st.write("📚 **학습 기록 관리**")
        if len(st.session_state.messages) > 0:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            export_text = f"# ⚛️ 과학고 물리 AI 튜터 학습 기록\n- 학습 일시: {current_time}\n\n---\n\n"
            for msg in st.session_state.messages:
                role_title = "👤 학생 질문" if msg["role"] == "user" else "🤖 AI 튜터 피드백"
                export_text += f"### {role_title}\n\n{msg['content']}\n\n---\n\n"
            
            file_date = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            st.download_button(
                label="📥 오늘 학습 기록 다운로드 (.md)",
                data=export_text,
                file_name=f"물리학습기록_{file_date}.md",
                mime="text/markdown",
                key="main_download_btn",
                use_container_width=True
            )
            if st.button("🗑️ 대화 기록 초기화", key="main_reset_btn", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        else:
            st.caption("대화가 시작되면 학습 기록 다운로드 버튼이 활성화됩니다.")

st.markdown("---")

# 7. 좌측 사이드바
with st.sidebar:
    st.header("📂 탑재된 강의 단원")
    if loaded_file_list:
        for f_name in loaded_file_list:
            st.markdown(f"- 📄 `{os.path.basename(f_name)}`")
    else:
        st.info("등록된 강의록 파일이 없습니다.")

    st.markdown("---")
    st.header("📚 나의 학습 관리")
    if len(st.session_state.messages) > 0:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        export_text = f"# ⚛️ 과학고 물리 AI 튜터 학습 기록\n- 학습 일시: {current_time}\n\n---\n\n"
        for msg in st.session_state.messages:
            role_title = "👤 학생 질문" if msg["role"] == "user" else "🤖 AI 튜터 피드백"
            export_text += f"### {role_title}\n\n{msg['content']}\n\n---\n\n"
        
        file_date = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        st.download_button(
            label="📥 오늘 학습 기록 다운로드 (.md)",
            data=export_text,
            file_name=f"물리학습기록_{file_date}.md",
            mime="text/markdown",
            key="sidebar_download_btn",
            use_container_width=True
        )
        if st.button("🗑️ 대화 기록 초기화", key="sidebar_reset_btn", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    else:
        st.caption("대화가 시작되면 다운로드 버튼이 활성화됩니다.")

# 8. 복합 콘텐츠 렌더링 함수
def render_assistant_content(content):
    html_blocks = re.findall(r"```html(.*?)```", content, re.DOTALL)
    py_blocks = re.findall(r"```python(.*?)```", content, re.DOTALL)
    
    clean_text = re.sub(r"```(html|python).*?```", "", content, flags=re.DOTALL).strip()
    if clean_text:
        st.markdown(clean_text)
        
    for py_code in py_blocks:
        try:
            local_vars = {"plt": plt}
            exec(py_code.strip(), {}, local_vars)
            fig = plt.gcf()
            st.pyplot(fig)
            plt.clf()
        except Exception:
            pass

    for idx, html_code in enumerate(html_blocks):
        raw_html = html_code.strip()
        responsive_wrapper = f"""
        <style>
            * {{ box-sizing: border-box !important; }}
            body {{ margin: 0; padding: 4px; font-family: sans-serif; }}
            canvas {{ max-width: 100% !important; height: auto !important; display: block; }}
            div, fieldset, form {{ max-width: 100% !important; }}
            .controls, div[class*="control"], div[style*="flex"] {{
                display: flex !important;
                flex-wrap: wrap !important;
                gap: 8px !important;
                width: 100% !important;
            }}
            input[type="range"] {{ max-width: 140px; }}
            button, select, input {{ margin: 2px 0; }}
        </style>
        {raw_html}
        """
        col1, col2 = st.columns([2, 3])
        with col1:
            st.download_button(
                label="🖥️ 시뮬레이터 전체화면 다운로드 (.html)",
                data=raw_html,
                file_name=f"physics_simulation_{idx+1}.html",
                mime="text/html",
                key=f"sim_down_{idx}_{len(raw_html)}"
            )
        with col2:
            st.caption("다운로드한 파일을 브라우저로 열면 모니터 전체 크기로 실행됩니다.")

        components.html(responsive_wrapper, height=620, scrolling=True)

# 9. 이전 대화 화면 렌더링
AVATAR_USER = "🧑‍🎓"
AVATAR_ASSISTANT = "👨‍🏫"

for message in st.session_state.messages:
    avatar = AVATAR_USER if message["role"] == "user" else AVATAR_ASSISTANT
    with st.chat_message(message["role"], avatar=avatar):
        if message["role"] == "assistant":
            render_assistant_content(message["content"])
        else:
            st.markdown(message["content"])

# 10. 학생 질문 처리 (gemini-3.6-flash 및 안전한 재시도)
if prompt := st.chat_input("물리 개념이나 문제에 대해 질문하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=AVATAR_USER):
        st.markdown(prompt)

    recent_messages = st.session_state.messages[-6:]
    contents = []
    for msg in recent_messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })

    config = types.GenerateContentConfig(
        system_instruction=PHYSICS_INSTRUCTION,
        temperature=0.2
    )

    with st.chat_message("assistant", avatar=AVATAR_ASSISTANT):
        response_placeholder = st.empty()
        response_placeholder.markdown("""
        <div class="thinking-box">
            <span class="tutor-active-icon">👨‍🏫</span>
            <span class="tutor-atom-icon">⚛️</span>
            <span class="thinking-text">선생님이 유도 과정과 시뮬레이션을 준비하고 있습니다...</span>
        </div>
        """, unsafe_allow_html=True)
        
        full_response = ""
        max_retries = 3
        retry_delay = 1.5

        for attempt in range(max_retries):
            try:
                response_stream = client.models.generate_content_stream(
                    model="gemini-3.6-flash",
                    contents=contents,
                    config=config
                )
                for chunk in response_stream:
                    if chunk.text:
                        full_response += chunk.text
                        response_placeholder.markdown(full_response + "▌")
                        
                response_placeholder.empty()
                render_assistant_content(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                break

            except Exception as e:
                err_str = str(e)
                if ("503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str) and attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    error_msg = f"일시적으로 서버 연결이 불안정합니다. 잠시 후 다시 시도해 주세요. (오류: {err_str})"
                    response_placeholder.markdown(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    break
