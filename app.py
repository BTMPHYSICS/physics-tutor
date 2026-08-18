import os
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
st.caption("물리 개념 탐구, 유도 과정 검토, 오개념 교정을 돕는 인공지능 교사입니다.")

# 2. 안전한 API 키 로드 (Streamlit Secrets 사용)
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("GEMINI_API_KEY가 설정되지 않았습니다. Streamlit 설정(Secrets)에서 등록해 주세요.")
    st.stop()

client = genai.Client(api_key=api_key)

# 3. 물리 교사 시스템 지침
PHYSICS_INSTRUCTION = """
당신은 과학고등학교 학생들을 지도하는 탁월한 물리 교사이자 멘토입니다.
고전역학, 전자기학, 열역학, 파동 및 광학, 현대물리학 전반에 걸쳐 학문적 엄밀성과 직관을 제공하세요.

[수식 표기 및 렌더링 규칙]
1. 문장 속 인라인 수식(Inline Math) 작성 규칙:
   - 반드시 단일 달러 기호($)를 사용하되, 달러 기호와 내부 수식 사이에 절대 공백을 두지 마세요.
     * 올바른 예: $mg \\sin\\theta$, $a = R\\alpha$, $m_1 + m_2$
     * 잘못된 예: $ mg \\sin\\theta $, $ a = R\\alpha $
   - 문장 속 부등호는 HTML 태그 충돌을 방지하기 위해 \\gt, \\lt 사용을 권장합니다.
     * 올바른 예: $a \\gt 0$, $v \\lt c$

2. 독립 블록 수식(Block Math) 작성 규칙:
   - 중요한 유도 공식이나 핵심 방정식은 반드시 앞뒤 줄바꿈 후 더블 달러 기호($$)를 사용하세요.
     * 예시:
       $$\\Sigma \\tau = I\\alpha$$

3. 교육 및 지도 원칙:
   - 정답을 바로 주지 말고 소크라테스식 발문으로 핵심 물리 법칙(보존 법칙, 운동 방정식 등)을 먼저 생각하게 유도하세요.
   - 단위 분석(Dimensional Analysis) 및 극한 조건에서의 물리적 타당성을 함께 짚어주세요.
   - 오개념이 발견되면 원인을 논리적으로 짚어주세요.
"""

# 4. 세션 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 5. 이전 대화 화면 렌더링
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. 학생 질문 입력 및 응답 생성
if prompt := st.chat_input("물리 개념이나 문제에 대해 질문하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    contents = []
    for msg in st.session_state.messages:
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
                model="gemini-2.5-flash",
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
