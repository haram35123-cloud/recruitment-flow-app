import streamlit as st
import pandas as pd
import random
import altair as alt

st.set_page_config(page_title="면접 Low-data 분석 대시보드", layout="wide")

# ==========================================
# [디자인 스타일 설정]
# ==========================================
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 엑셀 템플릿 및 데이터 관리
# ==========================================
st.sidebar.header("📥 엑셀 템플릿 및 데이터 관리")

@st.cache_data
def convert_df_to_excel(df):
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='면접대상자데이터')
    return output.getvalue()

template_data = pd.DataFrame({
    "지원자ID": ["C001", "C002", "C003", "C004"],
    "유입경로": ["잡코리아", "사람인", "잡코리아", "직원추천"],
    "면접참석여부": ["참석", "불참", "참석", "참석"],
    "면접결과": ["합격", "해당없음", "불합격", "합격"],
    "최종입사": ["입사완료", "해당없음", "해당없음", "입사포기"]
})
excel_template = convert_df_to_excel(template_data)

st.sidebar.download_button(
    label="📊 면접 대상자 표준 엑셀 양식 다운로드",
    data=excel_template,
    file_name="면접현황_표준양식.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.sidebar.markdown("---")

# ==========================================
# 2. 로우데이터 업로드 및 실시간 편집기
# ==========================================
st.sidebar.header("📁 면접 Low-data")
uploaded_file = st.sidebar.file_uploader("작성한 엑셀(xlsx) 또는 CSV 파일 첨부", type=["csv", "xlsx"])

@st.cache_data
def get_default_interview_data():
    channels = ["잡코리아", "사람인", "직원추천", "산학협력", "워크넷"]
    data = []
    random.seed(2026)
    for i in range(1, 151):
        ch = random.choice(channels)
        attendance = random.choices(["참석", "불참"], weights=[0.8, 0.2])[0]
        if attendance == "불참":
            result = "해당없음"
            hire = "해당없음"
        else:
            result = random.choices(["합격", "불합격"], weights=[0.6, 0.4])[0]
            if result == "불합격":
                hire = "해당없음"
            else:
                hire = random.choices(["입사완료", "입사포기"], weights=[0.75, 0.25])[0]
        data.append({
            "지원자ID": f"C{i:03d}",
            "유입경로": ch,
            "면접참석여부": attendance,
            "면접결과": result,
            "최종입사": hire
        })
    return pd.DataFrame(data)

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file, engine='openpyxl')
        st.sidebar.success("✨ 면접 Low-data 연동 완료!")
    except Exception as e:
        st.sidebar.error(f"파일 읽기 오류: {e}")
        raw_df = get_default_interview_data()
else:
    raw_df = get_default_interview_data()

st.sidebar.markdown("### 📝 실시간 Low-data")
df = st.sidebar.data_editor(raw_df, num_rows="dynamic", key="interview_data_editor")
filtered_df = df

# ==========================================
# 4. 면접 전형 핵심 지표 (입사/포기 집계 로직 보완)
# ==========================================
total_interview_targets = len(filtered_df)
attended_count = len(filtered_df[filtered_df["면접참석여부"] == "참석"])
no_show_count = len(filtered_df[filtered_df["면접참석여부"] == "불참"])
pass_count = len(filtered_df[filtered_df["면접결과"] == "합격"])

hired_count = len(filtered_df[filtered_df["최종입사"].astype(str).str.contains("입사") & ~filtered_df["최종입사"].astype(str).str.contains("포기")])
giveup_count = len(filtered_df[filtered_df["최종입사"].astype(str).str.contains("포기")])

attendance_rate = (attended_count / total_interview_targets * 100) if total_interview_targets > 0 else 0
no_show_rate = (no_show_count / total_interview_targets * 100) if total_interview_targets > 0 else 0

st.subheader("📊 면접 전형 핵심 지표")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric(label="1. 면접 참석 대상자", value=f"{total_interview_targets}명", delta="지원자ID 수 기준")
with col2:
    st.metric(label="2. 실제 면접 참석", value=f"{attended_count}명", delta=f"참석률 {attendance_rate:.1f}%")
with col3:
    st.metric(label="3. 면접 노쇼(불참)", value=f"{no_show_count}명", delta=f"노쇼율 {no_show_rate:.1f}%", delta_color="inverse")
with col4:
    st.metric(label="4. 면접 합격", value=f"{pass_count}명", delta="편집기 내 합격")
with col5:
    st.metric(label="5. 최종 입사 / 포기", value=f"{hired_count}명", delta=f"포기 {giveup_count}명", delta_color="off")

st.markdown("---")

# ==========================================
# 5. 경로별 면접 참석 유무 현황
# ==========================================
st.subheader("📈 경로별 면접 참석 유무 현황")
if not df.empty and "유입경로" in df.columns and "면접참석여부" in df.columns:
    channel_labels = {}
    for ch in df["유입경로"].unique():
        ch_sub = df[df["유입경로"] == ch]
        tot = len(ch_sub)
        att = len(ch_sub[ch_sub["면접참석여부"] == "참석"])
        rate = (att / tot * 100) if tot > 0 else 0.0
        channel_labels[ch] = f"{ch}\n({rate:.1f}%)"
    
    chart_df = df.copy()
    chart_df["유입경로표시"] = chart_df["유입경로"].map(channel_labels)
    chart_data = chart_df.groupby(["유입경로표시", "면접참석여부"]).size().reset_index(name="인원수")
    
    stacked_bar_chart = alt.Chart(chart_data).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X('유입경로표시:N', title='유입 경로 및 참석률', sort='-y', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('인원수:Q', title='인원 수 (명)'),
        color=alt.Color('면접참석여부:N', title='면접 참석 여부', scale=alt.Scale(domain=['참석', '불참'], range=['#3B82F6', '#EF4444'])),
        tooltip=['유입경로표시', '면접참석여부', '인원수']
    ).properties(height=390)
    
    st.altair_chart(stacked_bar_chart, use_container_width=True)

st.markdown("---")

# ==========================================
# 6. 경로별 면접 참석 유무 통계
# ==========================================
st.subheader("🚨 경로별 면접 참석 유무 통계")
active_channels = df["유입경로"].unique() if "유입경로" in df.columns else []
analysis_list = []

for ch in active_channels:
    ch_sub = df[df["유입경로"] == ch]
    total_ch = len(ch_sub)
    if total_ch > 0:
        noshow_cnt = len(ch_sub[ch_sub["면접참석여부"] == "불참"])
        noshow_rate = (noshow_cnt / total_ch) * 100
        attend_cnt = len(ch_sub[ch_sub["면접참석여부"] == "참석"])
        attend_rate = (attend_cnt / total_ch) * 100
        p_cnt = len(ch_sub[ch_sub["면접결과"] == "합격"])
        h_cnt = len(ch_sub[ch_sub["최종입사"].astype(str).str.contains("입사") & ~ch_sub["최종입사"].astype(str).str.contains("포기")])
        g_cnt = len(ch_sub[ch_sub["최종입사"].astype(str).str.contains("포기")])
    else:
        noshow_cnt, noshow_rate, attend_cnt, attend_rate, p_cnt, h_cnt, g_cnt = 0, 0.0, 0, 0.0, 0, 0, 0

    analysis_list.append({
        "유입경로": ch,
        "면접대상자": total_ch,
        "면접 참석": f"{attend_cnt}명",
        "면접 참석률": f"{attend_rate:.1f}%",
        "면접 노쇼": f"{noshow_cnt}명",
        "면접 노쇼율": f"{noshow_rate:.1f}%",
        "면접 합격": f"{p_cnt}명",
        "최종 입사완료": f"{h_cnt}명",
        "입사포기": f"{g_cnt}명",
        "_raw_total": total_ch,
        "_raw_attend_rate": attend_rate,
        "_raw_noshow_rate": noshow_rate,
        "_raw_noshow_cnt": noshow_cnt
    })

result_df = pd.DataFrame(analysis_list)
display_table = result_df.drop(columns=["_raw_total", "_raw_attend_rate", "_raw_noshow_rate", "_raw_noshow_cnt"])
st.dataframe(display_table.set_index("유입경로"), use_container_width=True)

st.markdown("---")

# ==========================================
# 7. 경로별 효율성 및 리스크 진단
# ==========================================
st.subheader("🤖 경로별 효율성 및 리스크 진단")
if not result_df.empty:
    best_attend_row = result_df.loc[result_df["_raw_attend_rate"].idxmax()]
    worst_risk_row = result_df.loc[result_df["_raw_noshow_rate"].idxmax()]
else:
    best_attend_row = None
    worst_risk_row = None

col_ai1, col_ai2 = st.columns(2)

with col_ai1:
    if best_attend_row is not None:
        ch_name = best_attend_row["유입경로"]
        ch_tot = best_attend_row["_raw_total"]
        ch_rate = best_attend_row["_raw_attend_rate"]
        sample_eval = f"통계적 유의성 확보 (표본 {ch_tot}명)" if ch_tot >= 10 else f"소표본 주의 (표본 {ch_tot}명)"
        
        st.success(
            f"💡 **[채널 효율성 진단: High-Conversion Sourcing]**\n\n"
            f"• **핵심 지표**: 최고 참석률 채널 **'{ch_name}'** (참석전환율 **{ch_rate:.1f}%** | {sample_eval})\n"
            f"• **HR 솔루션 진단**: 지원 단계에서 직무 Fit이 검증되어 스크리닝 공수가 가장 절감되는 우수 구간\n"
            f"• **실무 액션 플랜**:\n"
            f"  - 해당 채널 유입 풀의 공통 프로필 키워드 및 JD 최적화 연계\n"
            f"  - 채용 예산 및 리소스 우선 배분 검토"
        )
    else:
        st.success("데이터가 부족합니다.")

with col_ai2:
    if worst_risk_row is not None:
        risk_name = worst_risk_row["유입경로"]
        risk_rate = worst_risk_row["_raw_noshow_rate"]
        risk_cnt = worst_risk_row["_raw_noshow_cnt"]
        
        st.warning(
            f"⚠️ **[운영 리스크 진단: Funnel Leakage & No-Show]**\n\n"
            f"• **고위험 지표**: 노쇼 집중 채널 **'{risk_name}'** (노쇼율 **{risk_rate:.1f}%** | 이탈 **{risk_cnt}명**)\n"
            f"• **HR 솔루션 진단**: 대량 지원 성향이 강해 브랜드 로열티가 낮고 이탈 가중\n"
            f"• **실무 액션 플랜**:\n"
            f"  - 면접 일정 확정 주기 단축 (D-3, D-1 자동 알림톡)\n"
            f"  - 후보자 경험 간소화"
        )
    else:
        st.warning("데이터가 부족합니다.")
