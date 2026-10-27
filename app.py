import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="MOM'S NUTRI", page_icon="🍔", layout="wide")
st.markdown("""<style>
.stApp {background: #fffaf3;} h1,h2,h3 {color: #773817;}
div[data-testid="stMetric"] {background: white; border-radius: 14px; padding: 15px;}
</style>""", unsafe_allow_html=True)

NUMERIC = {"kcal": "열량(kcal)", "carbs_g": "탄수화물(g)", "protein_g": "단백질(g)",
           "fat_g": "지방(g)", "sugar_g": "당류(g)", "sodium_mg": "나트륨(mg)"}
REQUIRED = ["name", "category", *NUMERIC, "image_url", "source_url", "verified_date"]

@st.cache_data

def load_data():
    df = pd.read_csv("menu_data.csv", dtype={"name": str, "category": str})
    missing = set(REQUIRED) - set(df.columns)
    if missing:
        raise ValueError(f"CSV에 필요한 열이 없습니다: {', '.join(sorted(missing))}")
    df = df.dropna(subset=["name"]).copy()
    df["name"] = df["name"].astype(str).str.strip()
    df = df[df["name"] != ""].drop_duplicates("name")
    df["category"] = df["category"].fillna("기타")
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df.loc[df[col] < 0, col] = float("nan")
    for col in ("image_url", "source_url", "verified_date"):
        df[col] = df[col].fillna("").astype(str).str.strip()
    return df

try:
    df = load_data()
except (FileNotFoundError, ValueError, pd.errors.ParserError) as exc:
    st.error(f"데이터를 불러올 수 없습니다: {exc}")
    st.stop()

st.title("🍔 MOM'S NUTRI")
st.caption("맘스터치 메뉴 탐색 · 영양성분 비교 · 세트 계산")
st.info("학습용 비공식 앱입니다. CSV에 공식 자료를 확인하여 입력한 수치만 표시합니다. 빈칸은 0이 아니라 '정보 없음'입니다.")

page = st.sidebar.radio("기능 선택", ["🍔 전체 메뉴", "📊 메뉴 비교", "🍟 세트 계산", "🎯 목표 칼로리"])

def fmt(value, unit=""):
    return "정보 없음" if pd.isna(value) else f"{value:,.1f}{unit}"

def card(row):
    with st.container(border=True):
        if row["image_url"].startswith("https://"):
            st.image(row["image_url"], use_container_width=True)
        else:
            st.markdown("### 🍽️ 사진 준비 중")
        st.subheader(row["name"])
        st.caption(row["category"])
        st.write("🔥 " + fmt(row["kcal"], " kcal"))
        if row["source_url"].startswith("https://"):
            st.link_button("영양정보 출처", row["source_url"])
        if row["verified_date"]:
            st.caption("확인일: " + row["verified_date"])

def detail(row):
    st.subheader(row["name"] + " 영양정보")
    cols = st.columns(3)
    for i, (key, label) in enumerate(NUMERIC.items()):
        cols[i % 3].metric(label, fmt(row[key]))
    plot = pd.DataFrame([{"성분": label, "함량": row[key]} for key, label in NUMERIC.items() if key not in ("kcal", "sodium_mg") and pd.notna(row[key])])
    if not plot.empty:
        st.plotly_chart(px.bar(plot, x="성분", y="함량", title="영양성분(g)"), use_container_width=True)
    else:
        st.warning("아직 그래프로 표시할 영양정보가 없습니다.")

if page == "🍔 전체 메뉴":
    search = st.text_input("🔍 메뉴 검색", placeholder="예: 싸이버거")
    categories = ["전체"] + sorted(df["category"].unique().tolist())
    category = st.selectbox("카테고리", categories)
    filtered = df[df["name"].str.contains(search, case=False, regex=False, na=False)]
    if category != "전체":
        filtered = filtered[filtered["category"] == category]
    st.write(f"검색 결과: {len(filtered)}개")
    if filtered.empty:
        st.warning("일치하는 메뉴가 없습니다. 다른 검색어를 입력해 보세요.")
    else:
        for start in range(0, len(filtered), 3):
            cols = st.columns(3)
            for col, (_, row) in zip(cols, filtered.iloc[start:start + 3].iterrows()):
                with col:
                    card(row)
        choice = st.selectbox("자세히 볼 메뉴", filtered["name"].tolist())
        detail(filtered.set_index("name").loc[choice])

elif page == "📊 메뉴 비교":
    names = st.multiselect("비교할 메뉴(2개 이상)", df["name"].tolist(), max_selections=5)
    if len(names) < 2:
        st.info("메뉴를 2개 이상 선택하세요.")
    else:
        selected = df.set_index("name").loc[names]
        st.dataframe(selected[list(NUMERIC)].rename(columns=NUMERIC).T, use_container_width=True)
        plot = selected.reset_index().melt(id_vars="name", value_vars=["kcal"], var_name="성분", value_name="열량")
        plot = plot.dropna(subset=["열량"])
        if not plot.empty:
            st.plotly_chart(px.bar(plot, x="name", y="열량", color="name", title="메뉴별 열량(kcal)"), use_container_width=True)
        else:
            st.warning("선택한 메뉴의 열량 정보가 없습니다.")

elif page == "🍟 세트 계산":
    st.write("메뉴별 수량을 선택하면 영양성분을 합산합니다.")
    chosen = st.multiselect("세트에 포함할 메뉴", df["name"].tolist())
    quantities = {name: st.number_input(name + " 수량", min_value=1, max_value=20, value=1, step=1, key="qty_" + name) for name in chosen}
    if chosen:
        selected = df.set_index("name").loc[chosen]
        for key, label in NUMERIC.items():
            values = selected[key]
            if values.isna().any():
                st.write(f"{label}: **계산 불가** (일부 메뉴의 정보 없음)")
            else:
                total = sum(float(selected.loc[name, key]) * quantities[name] for name in chosen)
                st.write(f"{label}: **{total:,.1f}**")

elif page == "🎯 목표 칼로리":
    target = st.number_input("한 메뉴의 최대 열량(kcal)", min_value=1, max_value=5000, value=700, step=50)
    known = df.dropna(subset=["kcal"])
    recommended = known[known["kcal"] <= target].sort_values("kcal")
    st.write(f"기준 이하 메뉴: {len(recommended)}개 (열량 정보가 있는 메뉴만 검색)")
    if recommended.empty:
        st.info("현재 조건에 맞는 검증된 열량 정보가 없습니다. CSV에 영양정보를 추가해 보세요.")
    else:
        st.dataframe(recommended[["name", "category", "kcal"]].rename(columns=NUMERIC), hide_index=True, use_container_width=True)
