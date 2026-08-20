import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(
    page_title="BTMPHYSICS 관리자 대시보드",
    page_icon="📊",
    layout="wide"
)

st.title("👨‍🏫 BTMPHYSICS AI Tutor 학생 학습 관리 대시보드")
st.caption("학생들의 실시간 질문 기록과 성실도/참여도 통계를 분석합니다.")

# 관리자 비밀번호 보호
ADMIN_PW = st.secrets.get("ADMIN_PASSWORD", "1234")
pw_input = st.sidebar.text_input("관리자 비밀번호", type="password")

if pw_input != ADMIN_PW:
    st.info("좌측 사이드바에 관리자 비밀번호를 입력해 주세요.")
    st.stop()

# 구글 시트 연결 및 데이터 로드
GSHEET_URL = st.secrets.get("GSHEET_URL", "복사한_구글시트_공유링크")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=GSHEET_URL, ttl=5)
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

if df.empty or "학번이름" not in df.columns:
    st.info("아직 기록된 학생 학습 데이터가 없습니다.")
    st.stop()

# 상단 핵심 메트릭
col1, col2, col3, col4 = st.columns(4)
total_logs = len(df)
unique_students = df["학번이름"].nunique()
avg_score = int(df["점수"].mean()) if "점수" in df.columns else 0

with col1:
    st.metric("총 누적 질문 수", f"{total_logs}건")
with col2:
    st.metric("참여 학생 수", f"{unique_students}명")
with col3:
    st.metric("평균 학습 점수", f"{avg_score}점")
with col4:
    if st.button("🔄 최신 데이터 새로고침"):
        st.rerun()

st.markdown("---")

# 탭 구성: 1) 학생별 요약 2) 전체 질문 로그 3) 개별 학생 정밀 조회
tab1, tab2, tab3 = st.tabs(["👥 학생별 활동 요약", "📋 실시간 전체 로그", "🔍 개별 학생 상세 탐구"])

with tab1:
    st.subheader("학생별 학습 통계 및 랭킹")
    summary = df.groupby("학번이름").agg(
        총질문수=("질문내용", "count"),
        최종점수=("점수", "max"),
        최근접속=("일시", "max")
    ).reset_index().sort_values(by="총질문수", ascending=False)
    
    st.dataframe(summary, use_container_width=True)

with tab2:
    st.subheader("실시간 질문 및 답변 로그")
    st.dataframe(df.sort_values(by="일시", ascending=False), use_container_width=True)
    
    # 엑셀/CSV 다운로드 버튼
    csv_data = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 전체 로그 CSV 다운로드",
        data=csv_data,
        file_name="BTMPHYSICS_학생학습기록.csv",
        mime="text/csv"
    )

with tab3:
    st.subheader("특정 학생 대화 내역 정밀 분석")
    student_list = sorted(df["학번이름"].unique())
    selected_student = st.selectbox("조회할 학생을 선택하세요", student_list)
    
    student_df = df[df["학번이름"] == selected_student].sort_values(by="일시")
    st.write(f"**{selected_student}** 학생의 누적 질문 수: {len(student_df)}회")
    
    for _, row in student_df.iterrows():
        with st.expander(f"[{row['일시']}] 질문: {row['질문내용'][:30]}..."):
            st.write(f"**질문 원문:** {row['질문내용']}")
            st.write(f"**AI 피드백 요약:** {row['AI답변요약']}")
            st.caption(f"점수: {row.get('점수', '-')}점 | 참여도: {row.get('참여도', '-')} | 성실도: {row.get('성실도', '-')}")
