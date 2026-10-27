from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="MOM'S NUTRI | 맘스터치 칼로리", page_icon="🍔", layout="wide")
st.markdown("""<style>.block-container{max-width:1150px;padding-top:2rem}.stMetric{background:#fff4e9;padding:12px;border-radius:12px}</style>""", unsafe_allow_html=True)
st.title("🍔 MOM'S NUTRI")
st.caption("맘스터치 메뉴 칼로리 검색 · 비교 · 세트 계산 | 비공식 교육용 프로젝트")

DATA_FILE = Path(__file__).with_name("menu_data.csv")
@st.cache_data

def load_data():
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    required = {"name", "category", "serving", "kcal", "source_url", "image_url"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError("CSV에 필요한 열이 없습니다: " + ", ".join(sorted(missing)))
    df["kcal"] = pd.to_numeric(df["kcal"], errors="coerce")
    df["name"] = df["name"].fillna("").astype(str)
    df["category"] = df["category"].fillna("기타").astype(str)
    return df

try:
    data = load_data()
except (FileNotFoundError, ValueError, UnicodeError, pd.errors.ParserError) as e:
    st.error(f"메뉴 파일을 불러오지 못했습니다: {e}")
    st.info("app.py와 menu_data.csv가 GitHub 저장소의 같은 위치에 있는지 확인하세요.")
    st.stop()

st.warning("칼로리는 제3자 데이터베이스의 참고값입니다. 최신 공식 수치 및 현재 판매 여부는 확인이 필요합니다. 치킨 100g과 버거 1개의 칼로리를 직접 비교하지 마세요.")
tab1, tab2, tab3, tab4 = st.tabs(["🍔 메뉴 찾기", "⚖️ 칼로리 비교", "🧮 식사 계산기", "🎯 목표 칼로리"])

with tab1:
    search = st.text_input("메뉴 이름 검색", placeholder="예: 싸이버거")
    cats = ["전체"] + sorted(data["category"].unique().tolist())
    cat = st.selectbox("종류", cats)
    found = data[data["name"].str.contains(search, case=False, regex=False, na=False)]
    if cat != "전체":
        found = found[found["category"] == cat]
    st.caption(f"검색 결과: {len(found)}개")
    if found.empty:
        st.info("검색 결과가 없습니다. 다른 이름을 입력해 보세요.")
    for start in range(0, len(found), 3):
        cols = st.columns(3)
        for col, (_, row) in zip(cols, found.iloc[start:start+3].iterrows()):
            with col:
                with st.container(border=True):
                    if pd.notna(row["image_url"]) and str(row["image_url"]).strip():
                        st.image(str(row["image_url"]), use_container_width=True)
                    else:
                        st.markdown("### 🍔 📷 사진 준비 중")
                    st.subheader(row["name"])
                    st.caption(f"{row['category']} · 기준: {row['serving']}")
                    st.metric("칼로리", f"{row['kcal']:,.0f} kcal" if pd.notna(row["kcal"]) else "정보 없음")
                    if pd.notna(row["source_url"]) and str(row["source_url"]).startswith("https://"):
                        st.link_button("칼로리 출처 확인", str(row["source_url"]))

with tab2:
    options = data["name"].tolist()
    selected = st.multiselect("비교할 메뉴 선택 (최대 5개)", options, default=options[:2], max_selections=5)
    comparison = data[data["name"].isin(selected)].dropna(subset=["kcal"])
    if not comparison.empty:
        st.bar_chart(comparison.set_index("name")["kcal"])
        st.dataframe(comparison[["name", "serving", "kcal"]].rename(columns={"name":"메뉴", "serving":"기준량", "kcal":"kcal"}), hide_index=True, use_container_width=True)
        st.caption("제공량이 다른 메뉴의 수치는 동일 조건의 비교가 아닙니다.")
    else:
        st.info("칼로리 정보가 있는 메뉴를 선택하세요.")

with tab3:
    st.write("선택한 메뉴와 수량을 합산합니다. 100g 기준 메뉴는 수량 1이 100g입니다.")
    choices = st.multiselect("먹을 메뉴 선택", options, key="meal")
    total = 0.0
    for name in choices:
        row = data[data["name"] == name].iloc[0]
        qty = st.number_input(f"{name} ({row['serving']}) 수량", min_value=0, max_value=30, value=1, step=1, key=f"qty_{name}")
        if pd.notna(row["kcal"]):
            total += float(row["kcal"]) * qty
        else:
            st.warning(f"{name}: 칼로리 정보가 없어 합산에서 제외됩니다.")
    st.metric("선택한 메뉴 합계", f"{total:,.0f} kcal")

with tab4:
    target = st.number_input("한 끼 목표 칼로리 (kcal)", min_value=100, max_value=3000, value=700, step=50)
    candidates = data[(data["kcal"].notna()) & (data["kcal"] <= target)].sort_values("kcal")
    st.write(f"{target:,} kcal 이하 메뉴: {len(candidates)}개")
    st.dataframe(candidates[["name", "category", "serving", "kcal"]].rename(columns={"name":"메뉴", "category":"분류", "serving":"기준량", "kcal":"칼로리"}), hide_index=True, use_container_width=True)
    st.caption("칼로리 기준 필터이며 건강상 적합성을 판단하는 추천은 아닙니다.")

with st.expander("📚 자료 및 AI 활용 안내"):
    st.write("자료: FatSecret 맘스터치 제품 정보. 제품 변경 및 등록 시점에 따라 실제 값과 다를 수 있습니다.")
    st.write("AI 도움: ChatGPT를 사용하여 Streamlit 구조, 예외 처리, CSV 읽기 예시를 작성함. 제출 전 코드를 이해하고 직접 테스트·수정한 내용을 기록하세요.")
