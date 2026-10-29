import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin

# ==============================
# 기본 설정
# ==============================

st.set_page_config(
    page_title="맘스터치 칼로리 분석기",
    page_icon="🍔",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background-color: #fffaf2;
}
h1, h2, h3 {
    color: #d62828;
}
div[data-testid="stMetric"] {
    background: white;
    padding: 15px;
    border-radius: 15px;
    border: 1px solid #eeeeee;
}
</style>
""", unsafe_allow_html=True)

st.title("🍔 MOM'S NUTRI")
st.subheader("맘스터치 칼로리 분석기 PRO")

st.caption("맘스터치 메뉴의 칼로리를 검색하고 비교해 보세요!")

# ==============================
# 메뉴 데이터 불러오기
# ==============================

@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv("menu_data.csv", encoding="utf-8-sig")

        # 기존 CSV와 새 CSV 모두 지원
        if "menu_name" in df.columns and "name" not in df.columns:
            df = df.rename(columns={"menu_name": "name"})

        if "calories" in df.columns and "kcal" not in df.columns:
            df = df.rename(columns={"calories": "kcal"})

        if "name" not in df.columns:
            st.error("CSV에 name 열이 없습니다.")
            st.stop()

        if "kcal" not in df.columns:
            st.error("CSV에 kcal 열이 없습니다.")
            st.stop()

        if "category" not in df.columns:
            df["category"] = "기타"

        if "image_url" not in df.columns:
            df["image_url"] = ""

        df["name"] = df["name"].fillna("").astype(str)
        df["category"] = df["category"].fillna("기타")
        df["kcal"] = pd.to_numeric(df["kcal"], errors="coerce")
        df["image_url"] = df["image_url"].fillna("")

        return df

    except FileNotFoundError:
        st.error("menu_data.csv 파일이 없습니다!")
        st.stop()

    except Exception as e:
        st.error(f"데이터 오류: {e}")
        st.stop()


df = load_data()

# ==============================
# 공식 메뉴 사진 찾기
# ==============================

OFFICIAL_URL = (
    "https://order.momstouch.co.kr/"
    "momsmall/menu.jsp?menu_cd=001"
)

@st.cache_data(ttl=86400, show_spinner=False)
def find_official_image(menu_name):
    """
    공식 메뉴 페이지에서 메뉴 이름과
    일치하는 이미지가 있는지 확인합니다.

    사이트 구조에 따라 실패할 수 있습니다.
    """

    try:
        response = requests.get(
            OFFICIAL_URL,
            timeout=8,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # 이미지의 alt 속성 확인
        for img in soup.find_all("img"):
            alt = img.get("alt", "").strip()
            src = img.get("src", "")

            if menu_name in alt and src:
                return urljoin(OFFICIAL_URL, src)

        # 메뉴 이름이 포함된 요소 주변 이미지 확인
        for element in soup.find_all(
            string=lambda text:
            text is not None and menu_name in text
        ):
            parent = element.parent

            for _ in range(3):
                if parent is None:
                    break

                img = parent.find("img")

                if img and img.get("src"):
                    return urljoin(
                        OFFICIAL_URL,
                        img["src"]
                    )

                parent = parent.parent

    except requests.RequestException:
        pass

    except Exception:
        pass

    return None


def show_image(row):
    name = row["name"]
    image_url = str(row.get("image_url", "")).strip()

    # 1. CSV에 등록된 사진
    if image_url.startswith(("https://", "http://")):
        try:
            st.image(image_url, use_container_width=True)
            return
        except Exception:
            pass

    # 2. GitHub images 폴더에 등록된 사진
    for ext in [".png", ".jpg", ".jpeg", ".webp"]:
        path = Path("images") / (name + ext)

        if path.is_file():
            st.image(str(path), use_container_width=True)
            return

    # 3. 공식 사이트에서 사진 검색
    found_image = find_official_image(name)

    if found_image:
        try:
            st.image(
                found_image,
                use_container_width=True
            )
            return
        except Exception:
            pass

    # 4. 사진이 없을 때
    st.info("📷 메뉴 사진을 찾지 못했습니다.")


# ==============================
# 사이드바
# ==============================

st.sidebar.title("🍔 메뉴")

page = st.sidebar.radio(
    "기능 선택",
    [
        "🏠 전체 메뉴",
        "🔍 메뉴 검색",
        "📊 칼로리 비교",
        "🍟 세트 계산기",
        "🎯 칼로리 추천"
    ]
)

st.sidebar.divider()

st.sidebar.info(
    "칼로리는 참고용입니다. "
    "제품의 실제 영양정보와 다를 수 있습니다."
)

# ==============================
# 메뉴 카드
# ==============================

def menu_card(row):
    with st.container(border=True):
        show_image(row)

        st.markdown(f"### 🍔 {row['name']}")

        if pd.notna(row["kcal"]):
            st.metric(
                "🔥 칼로리",
                f"{row['kcal']:,.0f} kcal"
            )
        else:
            st.warning("칼로리 정보 없음")

        st.caption(f"카테고리: {row['category']}")


# ==============================
# 1. 전체 메뉴
# ==============================

if page == "🏠 전체 메뉴":

    st.header("🍔 맘스터치 전체 메뉴")

    categories = ["전체"] + sorted(
        df["category"].unique().tolist()
    )

    selected_category = st.selectbox(
        "카테고리 선택",
        categories
    )

    if selected_category == "전체":
        filtered = df
    else:
        filtered = df[
            df["category"] == selected_category
        ]

    st.success(f"총 {len(filtered)}개 메뉴")

    columns = st.columns(3)

    for i, (_, row) in enumerate(filtered.iterrows()):
        with columns[i % 3]:
            menu_card(row)


# ==============================
# 2. 메뉴 검색
# ==============================

elif page == "🔍 메뉴 검색":

    st.header("🔍 메뉴 검색")

    keyword = st.text_input(
        "찾고 싶은 메뉴를 입력하세요",
        placeholder="예: 싸이버거"
    )

    if keyword:
        result = df[
            df["name"].str.contains(
                keyword,
                case=False,
                na=False,
                regex=False
            )
        ]

        if result.empty:
            st.warning("검색 결과가 없습니다.")
        else:
            st.success(f"{len(result)}개 메뉴 발견!")

            columns = st.columns(3)

            for i, (_, row) in enumerate(result.iterrows()):
                with columns[i % 3]:
                    menu_card(row)

    else:
        st.info("메뉴 이름을 입력해 주세요.")


# ==============================
# 3. 칼로리 비교
# ==============================

elif page == "📊 칼로리 비교":

    st.header("📊 메뉴별 칼로리 비교")

    selected = st.multiselect(
        "비교할 메뉴 선택",
        df["name"].tolist()
    )

    if selected:
        result = df[
            df["name"].isin(selected)
        ].dropna(subset=["kcal"])

        if result.empty:
            st.warning("칼로리 정보가 없습니다.")

        else:
            chart = result.set_index("name")["kcal"]

            st.bar_chart(chart)

            st.dataframe(
                result[["name", "kcal"]],
                hide_index=True,
                use_container_width=True
            )

            highest = result.loc[
                result["kcal"].idxmax()
            ]

            lowest = result.loc[
                result["kcal"].idxmin()
            ]

            st.success(
                f"🔥 가장 높은 칼로리: "
                f"{highest['name']} "
                f"({highest['kcal']:.0f} kcal)"
            )

            st.info(
                f"🥗 가장 낮은 칼로리: "
                f"{lowest['name']} "
                f"({lowest['kcal']:.0f} kcal)"
            )

    else:
        st.info("비교할 메뉴를 선택하세요.")


# ==============================
# 4. 세트 칼로리 계산기
# ==============================

elif page == "🍟 세트 계산기":

    st.header("🍟 나만의 세트 계산기")

    st.write(
        "버거, 치킨, 사이드, 음료를 선택해 "
        "총칼로리를 계산해 보세요."
    )

    selected = st.multiselect(
        "먹을 메뉴 선택",
        df["name"].tolist()
    )

    total = 0
    missing = []

    for name in selected:
        row = df[df["name"] == name].iloc[0]

        if pd.notna(row["kcal"]):
            total += row["kcal"]
        else:
            missing.append(name)

    st.divider()

    st.metric(
        "🔥 총칼로리",
        f"{total:,.0f} kcal"
    )

    if missing:
        st.warning(
            "다음 메뉴는 칼로리 정보가 없어 "
            "합계에서 제외했습니다: "
            + ", ".join(missing)
        )

    if selected and not missing:
        if total <= 500:
            st.success("🥗 500kcal 이하입니다!")

        elif total <= 1000:
            st.info("🍔 총칼로리가 1,000kcal 이하입니다.")

        else:
            st.warning(
                "🔥 총칼로리가 1,000kcal를 초과했습니다."
            )

    st.caption(
        "이 기준은 단순한 열량 안내이며 "
        "개인별 건강 상태를 평가하지 않습니다."
    )


# ==============================
# 5. 목표 칼로리 추천
# ==============================

elif page == "🎯 칼로리 추천":

    st.header("🎯 목표 칼로리 메뉴 찾기")

    target = st.number_input(
        "최대 칼로리 설정",
        min_value=1,
        max_value=5000,
        value=600,
        step=50
    )

    result = df[
        (df["kcal"] <= target) &
        (df["kcal"].notna())
    ].sort_values("kcal")

    if result.empty:
        st.warning(
            "설정한 칼로리 이하의 메뉴가 없습니다."
        )

    else:
        st.success(
            f"🔥 {target}kcal 이하 메뉴 "
            f"{len(result)}개 발견!"
        )

        columns = st.columns(3)

        for i, (_, row) in enumerate(result.iterrows()):
            with columns[i % 3]:
                menu_card(row)


# ==============================
# 하단 정보
# ==============================

st.divider()

st.caption(
    "MOM'S NUTRI | Python + Streamlit"
)

st.caption(
    "비공식 학생 프로젝트입니다. "
    "맘스터치 공식 서비스가 아닙니다."
)

st.link_button(
    "🍔 맘스터치 공식 메뉴 확인",
    OFFICIAL_URL
)
