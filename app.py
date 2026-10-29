import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
import re

# =====================================
# 1. 앱 기본 설정
# =====================================

st.set_page_config(
    page_title="맘스터치 칼로리 분석기",
    page_icon="🍔",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background-color: #FFF9F0;
}
h1, h2, h3 {
    color: #C62828;
}
div[data-testid="stMetric"] {
    background-color: white;
    padding: 15px;
    border-radius: 15px;
    border: 1px solid #eeeeee;
}
</style>
""", unsafe_allow_html=True)

st.title("🍔 MOM'S NUTRI PRO")
st.subheader("맘스터치 칼로리 분석기")
st.write("맘스터치 메뉴의 칼로리를 검색하고 비교해 보세요!")

OFFICIAL_URL = (
    "https://order.momstouch.co.kr/"
    "momsmall/menu.jsp?menu_cd=001"
)

# =====================================
# 2. CSV 데이터 불러오기
# =====================================

@st.cache_data(ttl=300)
def load_data():
    data = pd.read_csv(
        "menu_data.csv",
        encoding="utf-8-sig"
    )

    # 다른 CSV 열 이름도 지원
    data = data.rename(columns={
        "menu_name": "name",
        "menu": "name",
        "calories": "kcal",
        "calorie": "kcal"
    })

    if "name" not in data.columns:
        raise ValueError("CSV에 name 열이 없습니다.")

    if "kcal" not in data.columns:
        raise ValueError("CSV에 kcal 열이 없습니다.")

    if "category" not in data.columns:
        data["category"] = "기타"

    if "image_url" not in data.columns:
        data["image_url"] = ""

    data["name"] = (
        data["name"].fillna("").astype(str).str.strip()
    )

    data["category"] = (
        data["category"].fillna("기타").astype(str)
    )

    data["image_url"] = (
        data["image_url"].fillna("").astype(str)
    )

    data["kcal"] = pd.to_numeric(
        data["kcal"],
        errors="coerce"
    )

    data = data[data["name"] != ""]
    data = data.drop_duplicates(subset=["name"])

    return data.reset_index(drop=True)


try:
    df = load_data()

except Exception as error:
    st.error(f"메뉴 데이터를 불러오지 못했습니다: {error}")
    st.info(
        "GitHub에 menu_data.csv 파일이 있는지 "
        "확인해 주세요."
    )
    st.stop()


# =====================================
# 3. 공식 메뉴 사진 검색
# =====================================

def clean_name(name):
    """비교를 위해 공백과 일부 기호 제거"""
    return re.sub(
        r"[^가-힣a-zA-Z0-9]",
        "",
        str(name)
    ).lower()


@st.cache_data(ttl=86400, show_spinner=False)
def get_official_images():
    """
    맘스터치 공식 메뉴 페이지에서
    메뉴명과 이미지 주소를 수집합니다.

    사이트 구조나 접근 제한에 따라
    일부 사진은 수집되지 않을 수 있습니다.
    """

    images = {}

    try:
        response = requests.get(
            OFFICIAL_URL,
            timeout=12,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/120.0 Safari/537.36"
                )
            }
        )

        response.raise_for_status()
        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # 메뉴 제목을 기준으로 사진 탐색
        for title in soup.find_all(
            ["h3", "h4", "strong", "dt"]
        ):
            menu_name = title.get_text(
                " ",
                strip=True
            )

            if not menu_name:
                continue

            parent = title.parent

            for _ in range(4):
                if parent is None:
                    break

                img = parent.find("img")

                if img:
                    src = (
                        img.get("data-src")
                        or img.get("data-original")
                        or img.get("src")
                    )

                    if src:
                        full_url = urljoin(
                            OFFICIAL_URL,
                            src
                        )

                        images[
                            clean_name(menu_name)
                        ] = full_url

                        break

                parent = parent.parent

        # 이미지 alt 속성으로 추가 검색
        for img in soup.find_all("img"):
            alt = img.get("alt", "").strip()

            src = (
                img.get("data-src")
                or img.get("src")
            )

            if alt and src:
                key = clean_name(alt)

                if key and key not in images:
                    images[key] = urljoin(
                        OFFICIAL_URL,
                        src
                    )

    except requests.RequestException:
        return {}

    except Exception:
        return {}

    return images


# =====================================
# 4. 사진 표시 함수
# =====================================

def show_menu_image(row):
    name = str(row["name"]).strip()

    # 1순위: images 폴더
    for extension in [
        ".png",
        ".jpg",
        ".jpeg",
        ".webp"
    ]:
        path = Path("images") / f"{name}{extension}"

        if path.is_file():
            st.image(
                str(path),
                use_container_width=True
            )
            return

    # 2순위: CSV 사진 주소
    image_url = str(
        row.get("image_url", "")
    ).strip()

    if image_url.startswith(
        ("https://", "http://")
    ):
        try:
            st.image(
                image_url,
                use_container_width=True
            )
            return
        except Exception:
            pass

    # 3순위: 공식 홈페이지 검색
    images = get_official_images()

    key = clean_name(name)

    if key in images:
        try:
            st.image(
                images[key],
                use_container_width=True
            )
            return
        except Exception:
            pass

    st.info("📷 사진 준비 중")


# =====================================
# 5. 메뉴 카드
# =====================================

def menu_card(row):
    with st.container(border=True):

        show_menu_image(row)

        st.markdown(
            f"### 🍔 {row['name']}"
        )

        if pd.notna(row["kcal"]):
            st.metric(
                "🔥 칼로리",
                f"{row['kcal']:,.0f} kcal"
            )
        else:
            st.warning("칼로리 정보 없음")

        st.caption(
            f"분류: {row['category']}"
        )


# =====================================
# 6. 사이드바
# =====================================

st.sidebar.title("🍔 MOM'S NUTRI")

page = st.sidebar.radio(
    "메뉴 선택",
    [
        "🏠 전체 메뉴",
        "🔍 메뉴 검색",
        "📊 칼로리 비교",
        "🍟 세트 계산기",
        "🎯 칼로리 추천"
    ]
)

st.sidebar.divider()

st.sidebar.write(
    f"📋 등록된 메뉴: {len(df)}개"
)

st.sidebar.caption(
    "칼로리는 참고용이며 "
    "최신 공식 수치와 다를 수 있습니다."
)


# =====================================
# 7. 전체 메뉴
# =====================================

if page == "🏠 전체 메뉴":

    st.header("🍔 전체 메뉴")

    keyword = st.text_input(
        "🔍 메뉴 검색",
        placeholder="메뉴 이름 입력"
    )

    categories = (
        ["전체"] +
        sorted(df["category"].unique().tolist())
    )

    category = st.selectbox(
        "카테고리",
        categories
    )

    filtered = df.copy()

    if category != "전체":
        filtered = filtered[
            filtered["category"] == category
        ]

    if keyword:
        filtered = filtered[
            filtered["name"].str.contains(
                keyword,
                case=False,
                regex=False,
                na=False
            )
        ]

    st.success(
        f"🍔 {len(filtered)}개 메뉴"
    )

    columns = st.columns(3)

    for i, (_, row) in enumerate(
        filtered.iterrows()
    ):
        with columns[i % 3]:
            menu_card(row)


# =====================================
# 8. 메뉴 검색
# =====================================

elif page == "🔍 메뉴 검색":

    st.header("🔍 메뉴 검색")

    keyword = st.text_input(
        "메뉴 이름을 입력하세요",
        placeholder="예: 싸이버거"
    )

    if keyword.strip():

        result = df[
            df["name"].str.contains(
                keyword.strip(),
                case=False,
                regex=False,
                na=False
            )
        ]

        if result.empty:
            st.warning(
                "검색 결과가 없습니다."
            )

        else:
            st.success(
                f"{len(result)}개 메뉴 발견!"
            )

            columns = st.columns(3)

            for i, (_, row) in enumerate(
                result.iterrows()
            ):
                with columns[i % 3]:
                    menu_card(row)

    else:
        st.info(
            "찾고 싶은 메뉴를 입력해 주세요."
        )


# =====================================
# 9. 칼로리 비교
# =====================================

elif page == "📊 칼로리 비교":

    st.header("📊 칼로리 비교")

    selected = st.multiselect(
        "비교할 메뉴를 선택하세요",
        df["name"].tolist()
    )

    if selected:

        result = df[
            df["name"].isin(selected)
        ].dropna(subset=["kcal"])

        if result.empty:
            st.warning(
                "선택한 메뉴의 칼로리 정보가 없습니다."
            )

        else:
            st.bar_chart(
                result.set_index("name")["kcal"]
            )

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

            st.error(
                f"🔥 가장 높은 칼로리: "
                f"{highest['name']} "
                f"({highest['kcal']:.0f} kcal)"
            )

            st.success(
                f"🥗 가장 낮은 칼로리: "
                f"{lowest['name']} "
                f"({lowest['kcal']:.0f} kcal)"
            )

    else:
        st.info(
            "비교할 메뉴를 선택해 주세요."
        )


# =====================================
# 10. 세트 칼로리 계산기
# =====================================

elif page == "🍟 세트 계산기":

    st.header("🍟 나만의 세트 만들기")

    st.write(
        "먹고 싶은 메뉴와 수량을 선택하면 "
        "총칼로리를 계산합니다."
    )

    selected = st.multiselect(
        "메뉴 선택",
        df["name"].tolist()
    )

    total = 0
    missing = []

    for name in selected:

        row = df[
            df["name"] == name
        ].iloc[0]

        quantity = st.number_input(
            f"{name} 수량",
            min_value=1,
            max_value=20,
            value=1,
            step=1,
            key=f"quantity_{name}"
        )

        if pd.notna(row["kcal"]):

            subtotal = (
                float(row["kcal"]) * quantity
            )

            total += subtotal

            st.write(
                f"🍔 {name} × {quantity} = "
                f"{subtotal:,.0f} kcal"
            )

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
            "합계에서 제외되었습니다: "
            + ", ".join(missing)
        )

    if selected and not missing:

        if total <= 500:
            st.success(
                "총칼로리가 500kcal 이하입니다."
            )

        elif total <= 1000:
            st.info(
                "총칼로리가 1,000kcal 이하입니다."
            )

        else:
            st.warning(
                "총칼로리가 1,000kcal를 초과했습니다."
            )

    st.caption(
        "칼로리 합산은 단순 계산이며 "
        "개인별 건강 상태를 평가하지 않습니다."
    )


# =====================================
# 11. 목표 칼로리 추천
# =====================================

elif page == "🎯 칼로리 추천":

    st.header("🎯 목표 칼로리 메뉴 추천")

    target = st.number_input(
        "최대 칼로리를 입력하세요",
        min_value=1,
        max_value=5000,
        value=600,
        step=50
    )

    result = df[
        (df["kcal"].notna()) &
        (df["kcal"] <= target)
    ].sort_values("kcal")

    if result.empty:

        st.warning(
            "조건에 맞는 메뉴가 없습니다."
        )

    else:

        st.success(
            f"🎉 {target}kcal 이하 "
            f"{len(result)}개 메뉴 발견!"
        )

        columns = st.columns(3)

        for i, (_, row) in enumerate(
            result.iterrows()
        ):
            with columns[i % 3]:
                menu_card(row)


# =====================================
# 12. 하단 정보
# =====================================

st.divider()

st.markdown(
    "### 🍔 MOM'S NUTRI PRO"
)

st.caption(
    "Python · Streamlit · Pandas"
)

st.caption(
    "학생 수행평가용 비공식 프로젝트입니다. "
    "맘스터치 공식 서비스가 아닙니다."
)

st.caption(
    "메뉴와 칼로리 정보는 참고용입니다. "
    "실제 영양정보는 공식 자료를 확인하세요."
)

st.link_button(
    "🍔 맘스터치 공식 메뉴 보기",
    OFFICIAL_URL
)
