"""새로운 요건 검증:
1. 골프, 안전, 구기, 꽃, 생필품, 배달음식, 생활용품, 수입명품, 가구, DIY, PC, 주변기기, 가공식품,
   브랜드, 여행, 티켓, 스포츠, 등산, 낚시, 배낭, 유아, 아동, 운동, 여가, 중성, 혼용, 공용, 유니섹스, 남녀
   단어가 들어간 카테고리는 "망고 필터명"에 있는 단어를 제외하고 완전히 배제.
2. 입력필드 구분 "국내": "해외", "수입명품", "수입" 등 단어가 들어간 카테고리 완전 배제.
3. 입력필드 구분 "해외": "해외", "수입" 단어 카테고리는 가장 낮은 우선순위(최후의 수단).
4. 미매핑 종료 로직 완전 삭제 및 100% 매핑 보장.
"""

import matching as mt
import map_categories as mc


def test_forbidden_words_strictly_excluded_unless_in_filter():
    forbidden_cats = [
        "스포츠 > 골프 > 골프웨어",
        "생활 > 안전용품 > 안전모",
        "스포츠 > 구기 > 축구공",
        "원예 > 꽃 > 장미",
        "마트 > 생필품 > 화장지",
        "외식 > 배달음식 > 피자",
        "가구/인테리어 > DIY > 공구",
        "디지털 > PC > 노트북",
        "디지털 > 주변기기 > 마우스",
        "식품 > 가공식품 > 라면",
        "패션의류 > 브랜드 > 맨투맨",
        "패션잡화 > 여행 > 캐리어",
        "공연 > 티켓 > 뮤지컬",
        "레저 > 낚시 > 낚싯대",
        "가방 > 배낭 > 등산배낭",
        "유아동 > 아동의류 > 원피스",
        "스포츠 > 운동 > 런닝화",
        "문화 > 여가 > 캠핑용품",
        "패션의류 > 남녀공용 > 티셔츠",
        "패션의류 > 중성 > 셔츠",
        "패션의류 > 혼용 > 니트",
        "패션의류 > 유니섹스 > 바지",
    ]
    # 일반 필터 "남성-상의-티셔츠"
    normal_cat = "패션의류 > 남성의류 > 상의 > 티셔츠"
    all_cats = [*forbidden_cats, normal_cat]

    cat, step = mt.find_category("아름트리-무신사-남성-상의-티셔츠", all_cats)
    assert cat == normal_cat
    assert cat not in forbidden_cats


def test_household_goods_not_forbidden():
    """'생활용품'은 배제 단어에서 제외되었으므로 필터링되지 않고 선택 가능해야 함."""
    cats = [
        "마트 > 생활용품 > 세탁세제",
        "디지털 > PC > 노트북",
    ]
    cat, step = mt.find_category("아름트리-무신사-남성-소품-세제", cats)
    assert cat == "마트 > 생활용품 > 세탁세제"


def test_forbidden_word_allowed_if_in_filter_name():
    # 필터명에 '골프'가 있으면 골프 카테고리 매핑 허용
    cats = [
        "패션의류 > 남성골프 > 골프웨어",
        "기타잡화 > 소품 > 파우치",
    ]
    cat, step = mt.find_category("아름트리-무신사-남성-골프-골프웨어", cats)
    assert cat == "패션의류 > 남성골프 > 골프웨어"


def test_domestic_mode_completely_excludes_overseas_and_import():
    cats = [
        "해외직구 > 남성의류 > 티셔츠",
        "수입명품 > 남성패션 > 티셔츠",
        "해외의류 > 남성상의 > 티셔츠",
        "국내패션 > 남성의류 > 티셔츠",
    ]
    cat, step = mt.find_category(
        "아름트리-무신사-남성-상의-티셔츠", cats, region_type="국내"
    )
    assert cat == "국내패션 > 남성의류 > 티셔츠"
    assert "해외" not in cat and "수입" not in cat


def test_overseas_mode_deprioritizes_import_and_overseas():
    cats = [
        "해외직구 > 남성의류 > 티셔츠",
        "수입명품 > 남성패션 > 티셔츠",
        "패션의류 > 남성의류 > 티셔츠",
    ]
    # 해외 모드에서도 국내/일반 카테고리가 있으면 일반 카테고리를 우선 선택
    cat, step = mt.find_category(
        "아름트리-무신사-남성-상의-티셔츠", cats, region_type="해외"
    )
    assert cat == "패션의류 > 남성의류 > 티셔츠"

    # 일반 카테고리가 없고 해외/수입만 있을 때만 최후의 수단으로 선택
    overseas_only = [
        "해외직구 > 남성의류 > 티셔츠",
        "수입명품 > 남성패션 > 티셔츠",
    ]
    cat2, step2 = mt.find_category(
        "아름트리-무신사-남성-상의-티셔츠", overseas_only, region_type="해외"
    )
    assert cat2 in overseas_only


def test_no_unmapped_forced_fallback_ensured():
    # 이상한 더미 카테고리들만 있어도 절대 빈값(미매핑)으로 끝나지 않음
    cats = ["패션잡화 > 소품 > 파우치"]
    cat, step = mt.find_category("아름트리-무신사-남성-신발-스니커즈", cats)
    assert cat == "패션잡화 > 소품 > 파우치"
    assert "근접매핑" in step or "강제지정" in step
