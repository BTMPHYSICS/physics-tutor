import os
import datetime
import streamlit as st
from google import genai
from google.genai import types

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="과학고 물리 AI 튜터",
    page_icon="⚛️",
    layout="centered"
)

st.title("⚛️ 과학고 물리 AI 튜터")
st.caption("선생님의 강의와 교재 내용을 기반으로 심화 물리 탐구를 돕습니다.")

# 2. API 키 설정
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY가 설정되지 않았습니다.")
    st.stop()

client = genai.Client(api_key=api_key)

# 3. 추출된 강의록(lecture_notes.md) 불러오기
lecture_knowledge = ""
if os.path.exists("lecture_notes.md"):
    with open("lecture_notes.md", "r", encoding="utf-8") as f:
        lecture_knowledge = f.read()

# 4. 물리 교사 시스템 지침
PHYSICS_INSTRUCTION = f"""
당신은 과학고등학교 학생들을 지도하는 탁월한 물리 교사이자 멘토입니다.

[지식 활용 가이드]
1. 학생의 질문이 아래 [선생님 전용 강의록]에 포함된 내용이라면, 반드시 강의록의 판서 유도 순서, 핵심 직관, 오개념 주의사항을 최우선 기준으로 삼아 지도하세요.
2. 강의록에 없는 다른 단원이나 심화 물리 질문이라도 일반물리학/고급물리 지식을 총동원하여 친절하고 깊이 있게 지도하세요.

[선생님 전용 심화 강의록]
{lecture_knowledge}

[수식 표기 및 렌더링 규칙]
1. 문장 속 인라인 수식: $mg \\sin\\theta$ 와 같이 달러 기호 양 끝에 공백 없이 작성.
2. 독립 블록 수식: 중요한 유도 공식은 줄바꿈 후 $$...$$ 사용.

[지도 원칙]
1. 정답을 바로 주지 말고 소크라테스식 발문으로 유도할 것.
2. 강의록에 수록된 핵심 직관과 판서 유도 순서를 존중하여 힌트를 제공할 것.
"""

# 5. 세션 및 이전 대화 화면 출력
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. 학생 질문 처리
if prompt := st.chat_input("강의 내용이나 물리 문제에 대해 질문하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
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

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
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
            response_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            error_msg = f"응답 생성 중 오류가 발생했습니다: {str(e)}"
            response_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

# 7. 좌측 사이드바: 학습 기록 다운로드 및 초기화
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
