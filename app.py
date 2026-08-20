import os
import re
import glob
import time
import json
import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import matplotlib.pyplot as plt
from streamlit_gsheets import GSheetsConnection
from google import genai
from google.genai import types

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="BTMPHYSICS AI Tutor",
    page_icon="⚛️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# 2. UI 스타일 최적화 CSS
st.markdown("""
<style>
/* 메인 타이틀 크기 조정 */
h1 { font-size: 1.5rem !important; font-weight: 700 !important; margin-bottom: 0.2rem !important; }
/* 단계별 소제목 크기 조정 */
.stMarkdown h1 { font-size: 1.2rem !important; font-weight: 700 !important; margin-top: 10px !important; margin-bottom: 4px !important; }
.stMarkdown h2 { font-size: 1.1rem !important; font-weight: 600 !important; margin-top: 8px !important; margin-bottom: 4px !important; }
.stMarkdown h3 { font-size: 1.0rem !important; font-weight: 600 !important; margin-top: 6px !important; margin-bottom: 3px !important; }
.stMarkdown h4 { font-size: 0.95rem !important; font-weight: 600 !important; }

/* 불필요한 기본 UI만 숨김 */
#MainMenu { visibility: hidden !important; display: none !important; }
.stDeployButton, .stAppDeployButton { display: none !important; }
div[data-testid="stDecoration"] { display: none !important; }
div[data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }
footer { display: none !important; visibility: hidden !important; height: 0px !important; }
div[data-testid="stFooter"] { display: none !important; visibility: hidden !important; height: 0px !important; }
div[data-testid="stStatusWidget"], [data-testid="manage-app-button"], div[class*="viewerBadge"], div[class*="ProfileBadge"], div[class*="stCommunityBadge"], div[class*="manageApp"], div[class*="floating"] { display: none !important; visibility: hidden !important; opacity: 0 !important; width: 0px !important; height: 0px !important; pointer-events: none !important; }

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

# 클립보드 복사 컴포넌트
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

# 3. API 키 및 구글 시트 연결 설정
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY가 설정되지 않았습니다.")
    st.stop()

client = genai.Client(api_key=api_key)

GSHEET_URL = st.secrets.get("GSHEET_URL", "")

def log_to_google_sheet(student_id, question, answer, engagement, diligence, score):
    webhook_url = st.secrets.get("WEBHOOK_URL", "")
    if not webhook_url:
        return
    payload = {
        "일시": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "학번이름": student_id,
        "질문내용": question,
        "AI답변요약": answer[:150] + "..." if len(answer) > 150 else answer,
        "참여도": f"{int(engagement * 100)}%",
        "성실도": f"{int(diligence * 100)}%",
        "점수": score
    }
    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception:
        pass
        
# 4. 저장소 내 모든 강의록 탐색 및 로드
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
당신은 학생들의 물리 탐구를 지도하는 'BTMPhysics AI 샘'입니다. 
자신을 소개하거나 언급할 때는 반드시 "BTMPhysics AI 샘"이라는 호칭을 사용하세요. (예: "안녕하세요! BTMPhysics AI 샘입니다.")

[지식 활용 가이드]
1. 학생의 질문이 아래 [선생님 전용 강의록]에 포함된 내용이라면, 반드시 강의록의 판서 유도 순서, 핵심 직관, 오개념 주의사항을 최우선 기준으로 삼아 지도하세요.
2. 강의록에 없는 다른 단원이나 심화 물리 질문이라도 일반물리학/고급물리 지식을 총동원하여 친절하고 깊이 있게 지도하세요.

[선생님 전용 강의록 (누적 데이터)]
{lecture_knowledge}

[시각 자료 생성 엄격 규칙 (위반 금지)]
1. 텍스트 문자, 유니코드 기호, 이모지, ASCII 아트를 사용한 도식화나 그림 그리기는 절대 금지합니다.
2. 정적 도식, 회로도, 그래프, 궤적 등의 시각 자료는 반드시 실행 가능한 Python Matplotlib 코드로 작성하여 ```python ... ``` 블록으로 감싸 출력하세요. (코드 마지막에 plt.show()는 작성하지 마세요)
3. 인터랙티브한 조작이나 애니메이션이 필요한 물리 현상은 반드시 HTML5 Canvas/JavaScript 기반의 독립 실행형 코드로 작성하여 ```html ... ``` 블록으로 감싸 출력하세요.

[수식 및 발문 원칙]
1. 문장 속 인라인 수식($...$), 독립 블록 수식($$...$$) 규칙을 철저히 지키세요.
2. 학생에게 정답을 바로 주지 말고, 과학적 발상과 판서 단계를 바탕으로 소크라테스식 힌트를 단계별로 제공하세요.
"""

# 6. 메인 타이틀
st.title("⚛️ BTMPHYSICS AI Tutor")
st.caption("선생님의 강의 영상과 교재 내용을 기반으로 심화 물리 탐구를 돕습니다.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "student_name" not in st.session_state:
    st.session_state.student_name = ""

# 7. 학습 성취도(성실도, 참여도, 점수) 계산 로직
user_questions = [msg["content"] for msg in st.session_state.messages if msg["role"] == "user"]
q_count = len(user_questions)

engagement_rate = min(1.0, q_count / 5.0)
total_chars = sum(len(q) for q in user_questions)
avg_length = (total_chars / q_count) if q_count > 0 else 0
diligence_rate = min(1.0, (avg_length / 40.0) * 0.7 + (min(q_count, 5) / 5.0) * 0.3)
learning_score = int((engagement_rate * 50) + (diligence_rate * 50))

if learning_score >= 90:
    grade_label = "🏆 마스터 탐구자"
elif learning_score >= 70:
    grade_label = "🌟 열정 물리학도"
elif learning_score >= 40:
    grade_label = "🚀 도약하는 탐구자"
elif learning_score > 0:
    grade_label = "🌱 새싹 탐구자"
else:
    grade_label = "탐구 준비 중"

# 8. 메인 화면 상단 접이식 대시보드
with st.expander("📊 나의 학습 성취도 및 리포트 관리 열기", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="총 학습 점수", value=f"{learning_score}점", delta=f"{grade_label}" if q_count > 0 else None)
        st.write(f"**참여도** (질문 {q_count}회)")
        st.progress(engagement_rate)
        st.write(f"**성실도** ({int(diligence_rate * 100)}%)")
        st.progress(diligence_rate)
    with col2:
        if q_count > 0:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            export_text = f"# ⚛️ BTMPHYSICS AI Tutor 학습 리포트\n"
            export_text += f"- **학습 일시**: {current_time}\n"
            export_text += f"- **최종 점수**: {learning_score}점 ({grade_label})\n"
            export_text += f"- **질문 횟수**: {q_count}회 | **성실도**: {int(diligence_rate * 100)}%\n\n---\n\n"
            
            for msg in st.session_state.messages:
                role_title = "👤 **학생 질문**" if msg["role"] == "user" else "🤖 **AI 튜터 피드백**"
                export_text += f"### {role_title}\n\n{msg['content']}\n\n---\n\n"
            
            file_date = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            st.download_button(
                label="📥 학습 기록 다운로드 (.md)",
                data=export_text,
                file_name=f"물리학습리포트_{file_date}.md",
                mime="text/markdown",
                key="main_download_btn",
                use_container_width=True
            )
            if st.button("🗑️ 대화 기록 초기화", key="main_reset_btn", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        else:
            st.caption("질문을 입력하면 성취도와 점수가 집계됩니다.")
            
    st.markdown("---")
    st.markdown("""
    <div style="background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 10px 12px; text-align: center; margin-top: 5px;">
        <span style="font-size: 0.85rem; color: #6c757d; font-weight: 500;">더 많은 물리 자료와 학습 커뮤니티</span><br>
        <a href="https://cafe.naver.com/btmphysics" target="_blank" style="text-decoration: none; font-weight: 700; color: #03c75a; font-size: 0.95rem;">
            ☕ BTMPHYSICS 공식 카페 바로가기
        </a>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# 9. 좌측 사이드바: 학생 정보 및 학습 관리 대시보드
with st.sidebar:
    st.header("👤 학생 정보")
    input_name = st.text_input("학번과 이름을 입력하세요", value=st.session_state.student_name, placeholder="예: 20105 김물리")
    if input_name:
        st.session_state.student_name = input_name
    st.markdown("---")
    
    st.header("📚 나의 학습 관리")
    st.metric(label="총 학습 점수", value=f"{learning_score}점", delta=f"{grade_label}" if q_count > 0 else None)
    
    st.write(f"**참여도** (질문 {q_count}회)")
    st.progress(engagement_rate)
    
    st.write(f"**성실도** ({int(diligence_rate * 100)}%)")
    st.progress(diligence_rate)
    
    st.markdown("---")
    
    if q_count > 0:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        export_text = f"# ⚛️ BTMPHYSICS AI Tutor 학습 리포트\n"
        export_text += f"- **학습 일시**: {current_time}\n"
        export_text += f"- **최종 점수**: {learning_score}점 ({grade_label})\n"
        export_text += f"- **질문 횟수**: {q_count}회 | **성실도**: {int(diligence_rate * 100)}%\n\n---\n\n"
        
        for msg in st.session_state.messages:
            role_title = "👤 **학생 질문**" if msg["role"] == "user" else "🤖 **AI 튜터 피드백**"
            export_text += f"### {role_title}\n\n{msg['content']}\n\n---\n\n"
        
        file_date = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        st.download_button(
            label="📥 오늘 학습 기록 다운로드 (.md)",
            data=export_text,
            file_name=f"물리학습리포트_{file_date}.md",
            mime="text/markdown",
            key="sidebar_download_btn",
            use_container_width=True
        )
        if st.button("🗑️ 대화 기록 초기화", key="sidebar_reset_btn", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    else:
        st.caption("질문을 남기면 참여도와 학습 점수가 실시간으로 반영됩니다.")
        
    st.markdown("---")
    st.markdown("""
    <div style="background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 10px 12px; text-align: center; margin-top: 5px;">
        <span style="font-size: 0.85rem; color: #6c757d; font-weight: 500;">더 많은 물리 자료와 질문/답변</span><br>
        <a href="https://cafe.naver.com/btmphysics" target="_blank" style="text-decoration: none; font-weight: 700; color: #03c75a; font-size: 0.95rem;">
            ☕ BTMPHYSICS 공식 카페 바로가기
        </a>
    </div>
    """, unsafe_allow_html=True)

# 10. 복합 콘텐츠 렌더링 함수 (KaTeX 수식 렌더링 지원)
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
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
            <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
            <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>
            <style>
                * {{ box-sizing: border-box !important; }}
                body {{ margin: 0; padding: 6px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #222; }}
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
        </head>
        <body>
            {raw_html}
            <script>
                function renderMath() {{
                    if (window.renderMathInElement) {{
                        renderMathInElement(document.body, {{
                            delimiters: [
                                {{left: '$$', right: '$$', display: true}},
                                {{left: '$', right: '$', display: false}}
                            ],
                            throwOnError: false
                        }});
                    }}
                }}
                
                window.addEventListener("load", () => {{
                    renderMath();
                    const observer = new MutationObserver(() => {{
                        observer.disconnect();
                        renderMath();
                        observer.observe(document.body, {{ childList: true, subtree: true, characterData: true }});
                    }});
                    observer.observe(document.body, {{ childList: true, subtree: true, characterData: true }});
                }});
            </script>
        </body>
        </html>
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

# 11. 이전 대화 화면 렌더링
AVATAR_USER = "🧑‍🎓"
AVATAR_ASSISTANT = "👨‍🏫"

for message in st.session_state.messages:
    avatar = AVATAR_USER if message["role"] == "user" else AVATAR_ASSISTANT
    with st.chat_message(message["role"], avatar=avatar):
        if "image" in message and message["image"] is not None:
            st.image(message["image"], caption="첨부된 문제 이미지", use_container_width=True)
        if message["role"] == "assistant":
            render_assistant_content(message["content"])
            copy_button_widget(message["content"], button_label="📋 답변 전체 복사")
        else:
            st.markdown(message["content"])
            copy_button_widget(message["content"], button_label="📋 내 질문 복사")

# 12. 문제 이미지 첨부 UI 및 멀티모달 질문 처리 (구글 시트 연동)
uploaded_image = st.file_uploader(
    "📷 문제 사진이나 도표/그래프 이미지를 첨부하세요 (선택 사항)", 
    type=["png", "jpg", "jpeg", "webp"],
    help="모의고사 문제, 회로도, 연습장 풀이 사진을 올리면 AI가 함께 분석합니다."
)

if prompt := st.chat_input("첨부한 문제에 대해 궁금한 점이나 물리 질문을 입력하세요..."):
    # 학번/이름 입력 확인
    if not st.session_state.student_name:
        st.warning("👈 좌측 메뉴에서 '학번과 이름'을 먼저 입력해 주세요!")
        st.stop()

    user_msg_record = {"role": "user", "content": prompt}
    if uploaded_image is not None:
        user_msg_record["image"] = uploaded_image.getvalue()
    st.session_state.messages.append(user_msg_record)

    with st.chat_message("user", avatar=AVATAR_USER):
        if uploaded_image is not None:
            st.image(uploaded_image.getvalue(), caption="첨부된 문제 이미지", use_container_width=True)
        st.markdown(prompt)
        copy_button_widget(prompt, button_label="📋 내 질문 복사")

    recent_messages = st.session_state.messages[-4:]
    contents = []
    for msg in recent_messages:
        role = "user" if msg["role"] == "user" else "model"
        parts = []
        if "image" in msg and msg["image"] is not None:
            parts.append(types.Part.from_bytes(data=msg["image"], mime_type="image/jpeg"))
        parts.append(types.Part.from_text(text=msg["content"]))
        contents.append({"role": role, "parts": parts})

    with st.chat_message("assistant", avatar=AVATAR_ASSISTANT):
        response_placeholder = st.empty()
        response_placeholder.markdown("""
        <div class="thinking-box">
            <span class="tutor-active-icon">👨‍🏫</span>
            <span class="tutor-atom-icon">⚛️</span>
            <span class="thinking-text">문제 분석 및 답변 준비중입니다....</span>
        </div>
        """, unsafe_allow_html=True)
        
        if uploaded_image is not None:
            dynamic_instruction = PHYSICS_INSTRUCTION
        else:
            is_casual = len(prompt) < 15 and any(keyword in prompt for keyword in ["안녕", "고마워", "감사", "반가워", "수고", "잘가", "좋은", "그래", "맞아"])
            if is_casual:
                dynamic_instruction = "당신은 'BTMPhysics AI 샘'입니다. 학생의 인사에 '안녕하세요! BTMPhysics AI 샘입니다.'와 같이 1~2문장으로 다정하게 답변하세요. 물리 수식이나 개념 설명은 생략합니다."
            else:
                dynamic_instruction = PHYSICS_INSTRUCTION

        config = types.GenerateContentConfig(
            system_instruction=dynamic_instruction,
            temperature=0.2
        )
        
        full_response = ""
        is_first_chunk = True
        
        candidate_models = ["gemini-2.5-flash", "gemini-3.6-flash"]
        success = False

        for target_model in candidate_models:
            try:
                response_stream = client.models.generate_content_stream(
                    model=target_model,
                    contents=contents,
                    config=config
                )
                for chunk in response_stream:
                    if chunk.text:
                        if is_first_chunk:
                            response_placeholder.empty()
                            is_first_chunk = False
                            
                        full_response += chunk.text
                        response_placeholder.markdown(full_response + "▌")
                        
                response_placeholder.empty()
                render_assistant_content(full_response)
                copy_button_widget(full_response, button_label="📋 답변 전체 복사")
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
                # [구글 시트 연동] 질문 완료 시 실시간 학습 로그 기록
                log_to_google_sheet(
                    student_id=st.session_state.student_name,
                    question=prompt,
                    answer=full_response,
                    engagement=engagement_rate,
                    diligence=diligence_rate,
                    score=learning_score
                )
                
                success = True
                break

            except Exception as e:
                time.sleep(1.0)
                continue

        if not success:
            error_msg = "이미지 분석 또는 응답 처리에 실패했습니다. 잠시 후 다시 질문해 주세요."
            response_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
