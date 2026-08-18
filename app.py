import os
import re
import time
import json
import datetime
import streamlit as st
import streamlit.components.v1 as components
import matplotlib.pyplot as plt
from google import genai
from google.genai import types

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="BTMPhysics AI Tutor",
    page_icon="⚛️",
    layout="centered"
)

# 2. 동적 애니메이션 및 복사 스타일 CSS 주입
st.markdown("""
<style>
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

.tutor-active-icon {
    font-size: 24px;
    display: inline-block;
    animation: tutorPulse 1.4s infinite ease-in-out;
}

.tutor-atom-icon {
    font-size: 22px;
    display: inline-block;
    animation: spinSlow 3s linear infinite;
}

.thinking-text {
    color: #4A90E2;
    font-weight: 600;
    font-size: 0.95rem;
}
</style>
""", unsafe_allow_html=True)

# 클립보드 복사 버튼 컴포넌트
def copy_button_widget(text_to_copy, button_label="📋 복사"):
    clean_json = json.dumps(text_to_copy)
    html_code = f"""
    <div style="margin-top: 4px; margin-bottom: 8px;">
        <button id="copy-btn" onclick="copyText()" style="
            background-color: #f0f2f6;
            border: 1px solid #d0d7de;
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 500;
            color: #333;
            cursor: pointer;
            transition: all 0.2s ease;
        ">{button_label}</button>
    </div>
    <script>
    function copyText() {{
        const text = {clean_json};
        navigator.clipboard.writeText(text).then(function() {{
            const btn = document.getElementById('copy-btn');
            const originalText = btn.innerText;
            btn.innerText = '✅ 복사 완료!';
            btn.style.backgroundColor = '#d1e7dd';
            btn.style.color = '#0f5132';
            setTimeout(() => {{
                btn.innerText = originalText;
                btn.style.backgroundColor = '#f0f2f6';
                btn.style.color = '#333';
            }}, 2000);
        }}).catch(function(err) {{
            console.error('복사 실패: ', err);
        }});
    }}
    </script>
    """
    components.html(html_code, height=38)

st.title("⚛️ BTMPhysics AI Tutor")
st.caption("선생님의 강의와 교재 내용을 기반으로 심화 물리 탐구를 돕습니다.")

# 3. API 키 설정
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY가 설정되지 않았습니다.")
    st.stop()

client = genai.Client(api_key=api_key)

# 4. 추출된 강의록(lecture_notes.md) 불러오기
lecture_knowledge = ""
if os.path.exists("lecture_notes.md"):
    with open("lecture_notes.md", "r", encoding="utf-8") as f:
        lecture_knowledge = f.read()

# 5. 물리 교사 시스템 지침
PHYSICS_INSTRUCTION = f"""
당신은 과학고등학교 학생들을 지도하는 탁월한 물리 교사이자 멘토입니다.

[지식 활용 가이드]
1. 학생의 질문이 아래 [선생님 전용 강의록]에 포함된 내용이라면, 반드시 강의록의 판서 유도 순서, 핵심 직관, 오개념 주의사항을 최우선 기준으로 삼아 지도하세요.
2. 강의록에 없는 다른 단원이나 심화 물리 질문이라도 일반물리학/고급물리 지식을 총동원하여 친절하고 깊이 있게 지도하세요.

[선생님 전용 심화 강의록]
{lecture_knowledge}

[시각 자료 및 시뮬레이션 작성 필수 원칙]
1. 단순 정적 그래프/도식: Python matplotlib 코드를 ```python ... ``` 코드 블록으로 작성하세요. (plt.show() 제외)
2. 동적 인터랙티브 시뮬레이션: HTML5 Canvas와 JavaScript로 작성된 독립 실행형 웹 시뮬레이터를 ```html ... ``` 코드 블록으로 작성하세요.
3. 텍스트 기호(ASCII 아트)로 그림을 그리는 것은 절대 금지합니다.

[수식 표기 및 렌더링 규칙]
1. 문장 속 인라인 수식: $mg \\sin\\theta$ 와 같이 달러 기호 양 끝에 공백 없이 작성.
2. 독립 블록 수식: 중요한 유도 공식은 줄바꿈 후 $$...$$ 사용.

[지도 원칙]
1. 정답을 바로 주지 말고 소크라테스식 발문으로 유도할 것.
2. 강의록에 수록된 핵심 직관과 판서 유도 순서를 존중하여 힌트를 제공할 것.
"""

# 6. 복합 콘텐츠 렌더링 함수
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

    for html_code in html_blocks:
        components.html(html_code.strip(), height=420, scrolling=True)

# 7. 이전 대화 화면 렌더링
if "messages" not in st.session_state:
    st.session_state.messages = []

AVATAR_USER = "🧑‍🎓"
AVATAR_ASSISTANT = "👨‍🏫"

for message in st.session_state.messages:
    avatar = AVATAR_USER if message["role"] == "user" else AVATAR_ASSISTANT
    with st.chat_message(message["role"], avatar=avatar):
        if message["role"] == "assistant":
            render_assistant_content(message["content"])
            copy_button_widget(message["content"], button_label="📋 답변 전체 복사")
        else:
            st.markdown(message["content"])
            copy_button_widget(message["content"], button_label="📋 내 질문 복사")

# 8. 학생 질문 처리 (503 / 429 자동 재시도 로직 포함)
if prompt := st.chat_input("물리 개념이나 문제에 대해 질문하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=AVATAR_USER):
        st.markdown(prompt)
        copy_button_widget(prompt, button_label="📋 내 질문 복사")

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
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=config
                )
                for chunk in response_stream:
                    if chunk.text:
                        full_response += chunk.text
                        response_placeholder.markdown(full_response + "▌")
                        
                response_placeholder.empty()
                render_assistant_content(full_response)
                copy_button_widget(full_response, button_label="📋 답변 전체 복사")
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

# 9. 좌측 사이드바: 학습 기록 다운로드 및 초기화
with st.sidebar:
    st.header("📚 나의 학습 관리")
    
    if len(st.session_state.messages) > 0:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        export_text = f"# ⚛️ 과학고 물리 AI 튜터 학습 기록\n- **학습 일시**: {current_time}\n\n---\n\n"
        
        for msg in st.session_state.messages:
            role_title = "👤 **학생 질문**" if msg["role"] == "user" else "🤖 **AI 튜터 피드백**"
            export_text += f"### {role_title}\n\n{msg['content']}\n\n---\n\n"
        
        file_date = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        st.download_button(
            label="📥 오늘 학습 기록 다운로드 (.md)",
            data=export_text,
            file_name=f"물리학습기록_{file_date}.md",
            mime="text/markdown",
            use_container_width=True
        )
        
        if st.button("🗑️ 대화 기록 초기화", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    else:
        st.info("질문을 입력하면 여기에 학습 기록 다운로드 버튼이 활성화됩니다.")
