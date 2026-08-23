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


def test_coupang_level5_exact_keyword_match_preferred_over_generic():
    """쿠팡 4단계 일치 시, 5단계에 명백히 검색어가 있는 경우 정확한 카테고리 우선."""
    cats = [
        "패션의류잡화 > 남성패션 > 남성상의 > 티셔츠 > 기타",
        "패션의류잡화 > 남성패션 > 남성상의 > 티셔츠 > 반팔티셔츠",
        "패션의류잡화 > 남성패션 > 남성상의 > 티셔츠 > 긴팔티셔츠",
    ]
    # 필터명이 '반팔티셔츠'를 명시한 경우 -> 5단계 '반팔티셔츠' 우선 매핑
    cat, step = mt.find_category(
        "아름트리-무신사-남성-상의-반팔티셔츠", cats, market="COUP"
    )
    assert cat == "패션의류잡화 > 남성패션 > 남성상의 > 티셔츠 > 반팔티셔츠"


def test_coupang_level5_generic_leaf_chosen_when_no_keyword():
    """쿠팡 4단계 일치 시, 5단계에 검색어가 없으면 '기타/일반' 등 광범위 단어 우선."""
    cats = [
        "패션의류잡화 > 남성패션 > 남성상의 > 셔츠 > 슬림핏셔츠",
        "패션의류잡화 > 남성패션 > 남성상의 > 셔츠 > 오버핏셔츠",
        "패션의류잡화 > 남성패션 > 남성상의 > 셔츠 > 기타",
    ]
    # 필터명에 슬림핏/오버핏 언급이 없는 경우 -> '기타' 우선
    cat, step = mt.find_category(
        "아름트리-무신사-남성-상의-셔츠", cats, market="COUP"
    )
    assert cat == "패션의류잡화 > 남성패션 > 남성상의 > 셔츠 > 기타"


def test_coupang_level5_first_leaf_chosen_when_hard_to_select():
    """쿠팡 4단계 일치 시, 일반적 단어도 없으면 원래 목록 중 첫 번째 선택."""
    cats = [
        "패션의류잡화 > 남성패션 > 남성상의 > 셔츠 > A타입",
        "패션의류잡화 > 남성패션 > 남성상의 > 셔츠 > B타입",
        "패션의류잡화 > 남성패션 > 남성상의 > 셔츠 > C타입",
    ]
    cat, step = mt.find_category(
        "아름트리-무신사-남성-상의-셔츠", cats, market="COUP"
    )
    assert cat == "패션의류잡화 > 남성패션 > 남성상의 > 셔츠 > A타입"


def test_three_stage_verify_and_save_sequence():
    """요건(2026-08-23):
    1차: 최초 등록 -> 저장
    2차: 확인 -> 누락 확인 -> 2차 등록 -> 저장
    3차: 확인 -> 누락 확인 -> 3차 등록 -> 저장
    """
    class VerifyPopup:
        def __init__(self):
            self.saves = 0
            self.round_calls = 0
            self.state = {
                "AUC20": {"code": "", "name": ""},
                "11ST": {"code": "", "name": ""},
                "GMK20": {"code": "", "name": ""},
                "SMART": {"code": "", "name": ""},
                "COUP": {"code": "", "name": ""},
                "LTON": {"code": "", "name": ""},
            }

        def on(self, *a, **k):
            pass

        def evaluate(self, script, *args):
            if "MAPPED_STATE_JS" in script or "openmarket_cm_category_" in script:
                codes = args[0] if args else []
                return {c: self.state.get(c, {"code": "", "name": ""}) for c in codes}
            return {}

        def wait_for_timeout(self, ms):
            pass

        def is_closed(self):
            return False

        def close(self):
            pass

    popup = VerifyPopup()
    # 1차 실행에서는 쿠팡/롯데ON만 성공, 옥션/11번가/G마켓/스마트는 누락되었다고 가정
    # 2차 실행에서 11번가/G마켓 성공, 옥션/스마트 누락
    # 3차 실행에서 옥션/스마트 성공
    attempt = {"n": 0}

    def fake_map_one_market(p, market, *a, **k):
        attempt["n"] += 1
        # 1차
        if attempt["n"] <= 6:
            if market in ("COUP", "LTON"):
                popup.state[market] = {"code": "1", "name": "카테고리"}
                return mc.MappedItem(market, "카테고리", 1.0, True, "성공")
            return mc.MappedItem(market, "", 0.0, False, "1차실패")
        # 2차
        elif attempt["n"] <= 10:
            if market in ("11ST", "GMK20"):
                popup.state[market] = {"code": "1", "name": "카테고리"}
                return mc.MappedItem(market, "카테고리", 1.0, True, "2차성공")
            return mc.MappedItem(market, "", 0.0, False, "2차실패")
        # 3차
        else:
            popup.state[market] = {"code": "1", "name": "카테고리"}
            return mc.MappedItem(market, "카테고리", 1.0, True, "3차성공")

    save_count = {"n": 0}
    def fake_save(p, *a, **k):
        save_count["n"] += 1
        return True

    import sys
    monkeypatch_dict = {
        "open_setting_popup": lambda *a, **k: popup,
        "map_one_market": fake_map_one_market,
        "click_config_save": fake_save,
        "close_popup": lambda *a, **k: None,
    }

    orig_open = mc.open_setting_popup
    orig_map = mc.map_one_market
    orig_save = mc.click_config_save
    orig_close = mc.close_popup

    try:
        mc.open_setting_popup = monkeypatch_dict["open_setting_popup"]
        mc.map_one_market = monkeypatch_dict["map_one_market"]
        mc.click_config_save = monkeypatch_dict["click_config_save"]
        mc.close_popup = monkeypatch_dict["close_popup"]

        row = mc.RowInfo(0, "793", "아름트리-무신사-남성-상의-티셔츠")
        detail = mc.map_one_row(None, row, {m: ["카테고리"] for m in mc.MARKETS}, list_url="url")

        # 1차 저장, 2차 저장, 3차 저장 총 3번 이상 저장 호출 확인
        assert save_count["n"] >= 3
        # 모든 마켓이 3차까지 거쳐 결국 채워졌는지 확인
        assert mc.unmapped_markets(popup, list(mc.MARKETS)) == []
    finally:
        mc.open_setting_popup = orig_open
        mc.map_one_market = orig_map
        mc.click_config_save = orig_save
        mc.close_popup = orig_close


