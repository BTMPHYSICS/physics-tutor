import streamlit as st
import pandas as pd
import re

# 1. 페이지 설정
st.set_page_config(
    page_title="BTMPHYSICSAITUTOR",
    page_icon="⚛️",
    layout="wide"
)

# 모바일 홈 화면 설치 시 기본 앱 이름 강제 지정
st.markdown("""
<head>
    <meta name="apple-mobile-web-app-title" content="BTMPHYSICSAITUTOR">
    <meta name="application-name" content="BTMPHYSICSAITUTOR">
</head>
""", unsafe_allow_html=True)

# 기존의 큰 st.title(...) 대신 아래 코드로 교체
st.markdown("<h2 style='font-size: 24px; font-weight: bold; margin-bottom: 2px;'>BTMPHYSICS 학생 학습 관리 대시보드</h2>", unsafe_allow_html=True)
st.caption("구글 스프레드시트와 실시간 연동되어 학생들의 질문 기록 및 참여도 통계를 분석합니다.")

# 2. 관리자 비밀번호 보호
ADMIN_PW = st.secrets.get("ADMIN_PASSWORD", "1234")
pw_input = st.sidebar.text_input("🔒 관리자 비밀번호", type="password")

if pw_input != ADMIN_PW:
    st.info("좌측 사이드바에 관리자 비밀번호를 입력해 주세요.")
    st.stop()

# 3. 구글 스프레드시트 URL 로드
GSHEET_URL = st.secrets.get("GSHEET_URL", "https://docs.google.com/spreadsheets/d/1r4arjnZr3ypEQl6bGeIdcygTjnlIpxQa1OWOaK4eWwA/edit?gid=0#gid=0")

# 4. 시트 고유 ID 및 GID 안전 파싱 함수
def extract_sheet_id(url):
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    return match.group(1) if match else url.strip()

# 5. UTF-8 기반 실시간 구글 시트 데이터 로드 함수
@st.cache_data(ttl=3)
def load_data(url):
    sheet_id = extract_sheet_id(url)
    gid_match = re.search(r"[#&]gid=([0-9]+)", url)
    gid = gid_match.group(1) if gid_match else "0"
    
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"
    return pd.read_csv(csv_url, encoding="utf-8")

# 6. 데이터 가져오기 실행
try:
    df = load_data(GSHEET_URL)
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.info("스프레드시트의 공유 설정이 '링크가 있는 모든 사용자 - 뷰어(또는 편집자)'로 되어 있는지 확인해 주세요.")
    st.stop()

# 7. 컬럼 헤더 공백 정리 및 검증
df.columns = [str(col).strip() for col in df.columns]

if "학번이름" not in df.columns:
    st.error("구글 스프레드시트 1행에 '학번이름' 열이 없습니다. 시트의 헤더명을 확인해 주세요.")
    st.write("현재 시트에서 읽어온 열 목록:", list(df.columns))
    st.stop()

if len(df) == 0:
    st.info("💡 스프레드시트 연결이 정상 완료되었습니다. 학생이 첫 질문을 전송하면 실시간으로 통계가 집계됩니다.")
    st.stop()

# 8. 상단 핵심 통계 지표
col1, col2, col3, col4 = st.columns(4)
total_logs = len(df)
unique_students = df["학번이름"].nunique()
avg_score = int(pd.to_numeric(df["점수"], errors="coerce").fillna(0).mean()) if "점수" in df.columns else 0

with col1:
    st.metric("총 누적 질문 수", f"{total_logs}건")
with col2:
    st.metric("참여 학생 수", f"{unique_students}명")
with col3:
    st.metric("평균 학습 점수", f"{avg_score}점")
with col4:
    if st.button("🔄 최신 데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# 9. 탭별 상세 분석
tab1, tab2, tab3 = st.tabs(["👥 학생별 활동 요약", "📋 실시간 전체 로그", "🔍 개별 학생 상세 탐구"])

with tab1:
    st.subheader("학생별 학습 통계 및 랭킹")
    summary = df.groupby("학번이름").agg(
        총질문수=("질문내용", "count"),
        최종점수=("점수", "max") if "점수" in df.columns else ("학번이름", "count"),
        최근접속=("일시", "max") if "일시" in df.columns else ("학번이름", "count")
    ).reset_index().sort_values(by="총질문수", ascending=False)
    
    st.dataframe(summary, use_container_width=True)

with tab2:
    st.subheader("실시간 질문 및 답변 로그")
    sort_col = "일시" if "일시" in df.columns else df.columns[0]
    st.dataframe(df.sort_values(by=sort_col, ascending=False), use_container_width=True)
    
    # 엑셀 한글 깨짐 방지 utf-8-sig 인코딩
    csv_data = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 전체 학습 기록 CSV 다운로드",
        data=csv_data,
        file_name="BTMPHYSICS_학생학습기록.csv",
        mime="text/csv",
        use_container_width=True
    )

with tab3:
    st.subheader("특정 학생 대화 내역 정밀 분석")
    student_list = sorted(df["학번이름"].dropna().unique())
    selected_student = st.selectbox("조회할 학생을 선택하세요", student_list)
    
    student_df = df[df["학번이름"] == selected_student]
    if "일시" in student_df.columns:
        student_df = student_df.sort_values(by="일시")
        
    st.write(f"**{selected_student}** 학생의 누적 질문 수: {len(student_df)}회")
    
    for _, row in student_df.iterrows():
        question_text = str(row.get('질문내용', ''))
        question_preview = question_text[:35] if question_text else "질문 없음"
        time_label = row.get('일시', '')
        
        with st.expander(f"[{time_label}] 질문: {question_preview}..."):
            st.write("질문 원문:")
            st.write(row.get('질문내용', '-'))
            st.write("AI 피드백 요약:")
            st.write(row.get('AI답변요약', '-'))
            st.caption(f"점수: {row.get('점수', '-')}점 | 참여도: {row.get('참여도', '-')} | 성실도: {row.get('성실도', '-')}")
