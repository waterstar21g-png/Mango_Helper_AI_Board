"""필터명 해석·카테고리 탐색 순서 테스트 (요건 예시 그대로)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matching as mt  # noqa: E402

EXCEL = [
    "패션의류잡화 > 남성 > 모자 > 버킷햇",
    "패션의류잡화 > 남성 > 모자 > 비니",
    "패션의류잡화 > 남성 > 모자 > 캡모자",
    "패션의류잡화 > 남성 > 소품 > 선글라스",
    "패션의류잡화 > 여성 > 모자 > 버킷햇",
    "의류잡화 > 잡화 > 안경테",
    "스포츠 > 등산 > 등산모자",
]


# ── 필터명 해석 ──────────────────────────────────────────────────


def test_parse_ignores_brand_and_site():
    p = mt.parse_filter_name("아름트리-무신사-남성-모자-버킷/사파리 햇")
    assert p.ignored == ["아름트리", "무신사"]
    assert p.top == "남성"
    assert p.mid == "모자"


def test_low_variants_example1():
    """버킷/사파리 햇 → 버킷햇 · 버킷 · 햇 · 사파리"""
    p = mt.parse_filter_name("아름트리-무신사-남성-모자-버킷/사파리 햇")
    for want in ("버킷햇", "버킷", "햇", "사파리"):
        assert want in p.lows, f"{want} 누락: {p.lows}"


def test_low_variants_example2():
    """바라클라바 → 바라클라바 · 바라 · 클라바"""
    p = mt.parse_filter_name("아름트리-무신사-남성-모자-바라클라바")
    for want in ("바라클라바", "바라", "클라바"):
        assert want in p.lows, f"{want} 누락: {p.lows}"


def test_low_variants_example3():
    """선글라스/안경테 → 선글라스 · 안경테"""
    p = mt.parse_filter_name("아름트리-무신사-남성-소품-선글라스/안경테")
    assert p.top == "남성" and p.mid == "소품"
    assert "선글라스" in p.lows and "안경테" in p.lows


def test_top_and_mid_fallbacks():
    p = mt.parse_filter_name("아름트리-무신사-남성-소품-선글라스/안경테")
    assert p.tops[0] == "남성"
    for extra in ("패션잡화", "의류잡화", "패션의류잡화"):
        assert extra in p.tops
    assert "잡화" in p.mids  # 소품 ↔ 잡화


def test_parse_without_prefix_keeps_all():
    p = mt.parse_filter_name("남성-모자")
    assert p.top == "남성" and p.mid == "모자"


# ── 탐색 순서 ────────────────────────────────────────────────────


def test_example1_picks_bucket_hat():
    cat, step = mt.find_category("아름트리-무신사-남성-모자-버킷/사파리 햇", EXCEL)
    assert cat == "패션의류잡화 > 남성 > 모자 > 버킷햇"
    assert step.startswith(("1)", "2-1)"))


def test_example3_picks_sunglasses():
    cat, _ = mt.find_category("아름트리-무신사-남성-소품-선글라스/안경테", EXCEL)
    assert cat == "패션의류잡화 > 남성 > 소품 > 선글라스"


def test_women_filter_does_not_take_men_path():
    cat, _ = mt.find_category("아름트리-무신사-여성-모자-버킷햇", EXCEL)
    assert cat == "패션의류잡화 > 여성 > 모자 > 버킷햇"


def test_step_2_2_mid_only_when_top_missing():
    """상위(남성)가 없는 자료 → 중위(모자)로 전체 재검색."""
    cats = ["스포츠 > 등산 > 등산모자", "생활 > 주방 > 컵"]
    cat, step = mt.find_category("아름트리-무신사-남성-모자-비니", cats)
    assert cat == "스포츠 > 등산 > 등산모자"
    assert "중위" in step


def test_step_2_3_low_only():
    """상위·중위 모두 없고 하위(안경테)만 있는 자료."""
    cats = ["잡화모음 > 안경테"]
    cat, step = mt.find_category("아름트리-무신사-남성-소품-선글라스/안경테", cats)
    assert cat == "잡화모음 > 안경테"
    assert "하위" in step


def test_step_2_4_generic_for_accessory():
    """어디에도 없으면 품목별 포괄 카테고리 (모자 → 의류잡화·패션의류잡화)."""
    cats = ["패션의류잡화 > 기타", "식품 > 과일"]
    cat, step = mt.find_category("아름트리-무신사-남성-모자-바라클라바", cats)
    assert cat == "패션의류잡화 > 기타"
    assert step.startswith("2-4)")


def test_step_2_4_generic_for_shoes():
    """중위(슈즈)·하위(스니커즈) 어디에도 없으면 신발 포괄 카테고리."""
    cats = ["신발잡화 > 기타", "식품 > 과일"]
    cat, step = mt.find_category("아름트리-무신사-남성-슈즈-스니커즈", cats)
    assert cat == "신발잡화 > 기타"
    assert step.startswith("2-4) 포괄(신발)")   # 뒤에 적용 규칙 태그가 붙을 수 있다


def test_mid_name_matching_precedes_generic():
    """중위(신발)가 '신발잡화' 에 걸리면 2-2 에서 끝난다 (2-4 로 가지 않음)."""
    cats = ["신발잡화 > 기타", "식품 > 과일"]
    cat, step = mt.find_category("아름트리-무신사-남성-신발-스니커즈", cats)
    assert cat == "신발잡화 > 기타"
    assert step.startswith("2-3)")   # 하위(스니커즈) 없음 → 중위(신발)


def test_always_picks_one_when_rules_fail():
    """★요건: 규칙으로 못 찾아도 가장 가까운 하나를 반드시 지정한다."""
    cat, step = mt.find_category("아름트리-무신사-남성-모자-버킷햇", ["식품 > 과일 > 사과"])
    assert cat == "식품 > 과일 > 사과"
    assert step.startswith("3) 최근접")


def test_force_off_returns_empty():
    cat, step = mt.find_category(
        "아름트리-무신사-남성-모자-버킷햇", ["식품 > 과일 > 사과"], force=False
    )
    assert cat == "" and step == "미검출"


def test_nearest_prefers_same_gender():
    cats = ["잡화 > 여성 > 기타소품", "잡화 > 남성 > 기타소품"]
    cat, _ = mt.find_category("아름트리-무신사-남성-소품-핸드워머", cats)
    assert cat == "잡화 > 남성 > 기타소품"


def test_nearest_uses_material_and_purpose():
    cats = ["아웃도어 > 등산 > 등산용품", "생활 > 주방 > 컵"]
    cat, step = mt.find_category("아름트리-무신사-남성-용품-등산스틱", cats)
    assert cat == "아웃도어 > 등산 > 등산용품"


def test_leaf_of_helper():
    assert mt.leaf_of("A > B > C") == "C"
    assert mt.leaf_of("") == ""


def test_empty_excel():
    assert mt.find_category("아름트리-무신사-남성-모자-버킷햇", []) == ("", "자료 없음")


# ── 보조 ─────────────────────────────────────────────────────────


def test_level_hit_is_partial_and_space_insensitive():
    assert mt.level_hit("남성 잡화", "남성잡화") is True
    assert mt.level_hit("모자", "버킷햇") is False
    assert mt.level_hit("버킷햇", "버킷") is True


def test_kind_detection():
    assert mt.kind_of(mt.parse_filter_name("a-b-남성-모자-비니")) == "잡화"
    assert mt.kind_of(mt.parse_filter_name("a-b-남성-신발-운동화")) == "신발"
    assert mt.kind_of(mt.parse_filter_name("a-b-남성-의류-티셔츠")) == "의류"


def test_pick_best_prefers_more_specific():
    paths = ["패션의류잡화 > 남성", "패션의류잡화 > 남성 > 모자 > 버킷햇"]
    parsed = mt.parse_filter_name("아름트리-무신사-남성-모자-버킷햇")
    assert mt.pick_best(paths, parsed) == "패션의류잡화 > 남성 > 모자 > 버킷햇"


# ── 엑셀 범위 보장 (요건 2026-08-22 15:45) ────────────────────────


def test_result_is_always_from_excel_list():
    """어떤 필터명이 와도 결과는 엑셀 목록 안의 값이어야 한다."""
    names = [
        "아름트리-무신사-남성-모자-버킷/사파리 햇",
        "아름트리-무신사-여성-소품-선글라스/안경테",
        "아름트리-무신사-남성-신발-스니커즈",
        "자동차 타이어 공기압 센서",
        "",
    ]
    for name in names:
        cat, _step = mt.find_category(name, EXCEL)
        assert cat == "" or cat in EXCEL, f"{name} → {cat}"


def test_is_from_and_ensure_from():
    assert mt.is_from(EXCEL, EXCEL[0]) is True
    assert mt.is_from(EXCEL, "패션의류잡화 > 남성 > 모자 > 없는것") is False
    assert mt.is_from(EXCEL, "") is False

    fixed = mt.ensure_from(EXCEL, "지어낸 > 카테고리", "아름트리-무신사-남성-모자-비니")
    assert fixed in EXCEL


def test_ensure_from_keeps_valid_value():
    assert mt.ensure_from(EXCEL, EXCEL[1], "무엇이든") == EXCEL[1]


# ── 선택 규칙 2·3·4 (요건 2026-08-22 15:53) ───────────────────────

RULE_EXCEL = [
    "패션의류 > 남성 > 하의 > 팬츠",
    "패션의류 > 여성 > 하의 > 팬츠",
    "스포츠/레저 > 등산 > 등산바지",
    "패션의류잡화 > 남성 > 모자 > 비니",
    "패션의류잡화 > 여성 > 모자 > 비니",
    "패션의류잡화 > 남성 > 신발 > 스니커즈",
    "생활 > 주방 > 컵",
]


def test_rule2_gender_is_enforced():
    """남성 필터는 여성 카테고리를 고르지 않는다."""
    cat, step = mt.find_category("아름트리-무신사-남성-모자-비니", RULE_EXCEL)
    assert cat == "패션의류잡화 > 남성 > 모자 > 비니"
    assert "성별=남성" in step

    cat, _ = mt.find_category("아름트리-무신사-여성-모자-비니", RULE_EXCEL)
    assert cat == "패션의류잡화 > 여성 > 모자 > 비니"


def test_rule2_falls_back_to_genderless_when_no_same_gender():
    cats = ["잡화 > 모자 > 비니", "패션의류잡화 > 여성 > 모자 > 비니"]
    cat, _ = mt.find_category("아름트리-무신사-남성-모자-비니", cats)
    assert cat == "잡화 > 모자 > 비니"   # 다른 성별 대신 무성별 경로


def test_rule3_item_name_must_match():
    """필터명이 '신발' 이면 신발이 들어간 카테고리에서 고른다."""
    cat, step = mt.find_category("아름트리-무신사-남성-신발-스니커즈", RULE_EXCEL)
    assert cat == "패션의류잡화 > 남성 > 신발 > 스니커즈"
    assert "품목=신발" in step


def test_rule3_priority_is_top_then_mid_then_low():
    """같은 품목명이 여러 단계에 있으면 상위 단계 우선."""
    cats = [
        "패션의류 > 남성 > 하의 > 의류기타",   # '의류' 가 상위(0단계)
        "생활 > 남성 > 의류 > 기타",           # '의류' 가 2단계
    ]
    ranked = mt.item_paths(cats, ["의류"])
    assert ranked[0] == "패션의류 > 남성 > 하의 > 의류기타"
    assert mt.item_level("생활 > 남성 > 의류 > 기타", "의류") == 2


def test_rule4_clothing_prefers_fashion_categories():
    """남성-팬츠: 스포츠/레저보다 패션의류를 우선."""
    cat, step = mt.find_category("아름트리-무신사-남성-의류-팬츠", RULE_EXCEL)
    assert cat == "패션의류 > 남성 > 하의 > 팬츠"
    assert "품목=의류" in step


def test_rule4_preference_order():
    cats = ["남성의류 > 하의 > 팬츠", "패션의류잡화 > 남성 > 하의 > 팬츠"]
    assert mt.clothing_priority(cats)[0] == "패션의류잡화 > 남성 > 하의 > 팬츠"


def test_rules_never_leave_excel_range():
    for name in (
        "아름트리-무신사-남성-의류-팬츠",
        "아름트리-무신사-여성-액세서리-귀걸이",
        "아름트리-무신사-남성-선글라스-보잉",
    ):
        cat, _ = mt.find_category(name, RULE_EXCEL)
        assert cat in RULE_EXCEL


def test_constrain_reports_applied_rules():
    parsed = mt.parse_filter_name("아름트리-무신사-남성-의류-팬츠")
    pool, notes = mt.constrain(RULE_EXCEL, parsed)
    assert all("여성" not in p for p in pool)
    assert "성별=남성" in notes and "품목=의류" in notes


# ── 반대 성별 절대 배제 (요건 2026-08-22 16:25) ───────────────────


def test_female_filter_never_picks_male_category():
    cats = [
        "남성패션 > 모자 > 비니",
        "남성신발 > 스니커즈",
        "패션의류잡화 > 공용 > 모자 > 비니",
    ]
    cat, _ = mt.find_category("아름트리-무신사-여성-모자-비니", cats)
    assert "남성" not in cat
    assert cat == "패션의류잡화 > 공용 > 모자 > 비니"


def test_male_filter_never_picks_female_category():
    cats = ["여성패션 > 모자 > 비니", "잡화 > 모자 > 비니"]
    cat, _ = mt.find_category("아름트리-무신사-남성-모자-비니", cats)
    assert "여성" not in cat
    assert cat == "잡화 > 모자 > 비니"


def test_returns_none_rather_than_opposite_gender():
    """반대 성별만 있으면 고르지 않는다 (절대 배제 우선)."""
    cats = ["남성패션 > 모자 > 비니", "남성신발 > 스니커즈"]
    cat, step = mt.find_category("아름트리-무신사-여성-모자-비니", cats)
    assert cat == ""
    assert "성별(여성)" in step


def test_strip_opposite_gender_helper():
    cats = ["남성패션 > 상의", "여성패션 > 상의", "공용 > 상의"]
    assert mt.strip_opposite_gender(cats, "여성") == ["여성패션 > 상의", "공용 > 상의"]
    assert mt.strip_opposite_gender(cats, "남성") == ["남성패션 > 상의", "공용 > 상의"]
    assert mt.strip_opposite_gender(cats, "") == cats


def test_violates_gender_helper():
    assert mt.violates_gender("남성패션 > 모자", "아름트리-무신사-여성-모자-비니") is True
    assert mt.violates_gender("공용 > 모자", "아름트리-무신사-여성-모자-비니") is False
    assert mt.violates_gender("남성패션 > 모자", "아름트리-무신사-남성-모자-비니") is False


def test_gender_of_english_women_is_not_men():
    """★`women` 안의 `men` 때문에 여성 카테고리를 남성으로 읽던 문제."""
    assert mt.gender_of("Womens Shoes") == "여성"
    assert mt.gender_of("Woman Loafer") == "여성"
    assert mt.gender_of("Men Shoes") == "남성"
    assert mt.gender_of("Loafer") == ""


def test_has_gender_english_notation():
    assert mt.has_gender("Womens Shoes > Loafer", "여성") is True
    assert mt.has_gender("Womens Shoes > Loafer", "남성") is False
    assert mt.has_gender("Men Shoes > Loafer", "남성") is True


def test_strip_opposite_gender_covers_english():
    """영문 표기도 반대 성별이면 배제한다."""
    cats = ["Men Shoes > Loafer", "Womens Shoes > Loafer", "Shoes > Loafer"]
    assert mt.strip_opposite_gender(cats, "여성") == [
        "Womens Shoes > Loafer",
        "Shoes > Loafer",
    ]


def test_nearest_fallback_also_respects_gender():
    """최근접 지정 단계에서도 반대 성별은 나오지 않는다."""
    cats = ["남성패션 > 기타", "생활 > 주방 > 컵"]
    cat, step = mt.find_category("아름트리-무신사-여성-소품-핸드워머", cats)
    assert cat == "생활 > 주방 > 컵"      # 남성 경로는 제외
    assert step.startswith("3) 최근접")


# ── 품목 계열 배타 · 검색 순서 (요건 2026-08-22 16:31) ────────────

CLASS_EXCEL = [
    "패션의류 > 남성 > 하의 > 팬츠",
    "패션잡화 > 남성 > 신발 > 스니커즈",
    "패션잡화 > 남성 > 시계",
    "패션잡화 > 남성 > 선글라스",
    "패션잡화 > 남성 > 기타소품",
]


def test_clothing_filter_never_picks_shoes():
    cat, step = mt.find_category("아름트리-무신사-남성-의류-팬츠", CLASS_EXCEL)
    assert "신발" not in cat
    assert cat == "패션의류 > 남성 > 하의 > 팬츠"
    assert "계열=의류" in step


def test_shoes_filter_never_picks_clothing():
    cat, _ = mt.find_category("아름트리-무신사-남성-신발-스니커즈", CLASS_EXCEL)
    assert cat == "패션잡화 > 남성 > 신발 > 스니커즈"


def test_sunglasses_never_picks_watch():
    cat, _ = mt.find_category("아름트리-무신사-남성-소품-선글라스", CLASS_EXCEL)
    assert "시계" not in cat
    assert cat == "패션잡화 > 남성 > 선글라스"


def test_class_falls_back_to_generic_when_missing():
    """의류·신발 계열이 없으면 잡화 계열에서 고른다."""
    cats = ["패션잡화 > 남성 > 기타소품", "생활 > 주방 > 컵"]
    cat, step = mt.find_category("아름트리-무신사-남성-신발-스니커즈", cats)
    assert cat == "패션잡화 > 남성 > 기타소품"


def test_class_helpers():
    assert mt.class_of("아름트리-무신사-남성-신발-스니커즈") == "신발"
    assert mt.class_of("아름트리-무신사-남성-소품-선글라스") == "선글라스"
    assert mt.class_of("아름트리-무신사-남성-소품-핸드워머") == ""
    assert mt.path_class("패션잡화 > 남성 > 시계") == "시계"
    assert mt.is_generic_path("패션잡화 > 남성 > 기타") is True


def test_strip_other_classes_keeps_generic_and_unknown():
    cats = ["A > 신발 > 스니커즈", "B > 의류 > 팬츠", "패션잡화 > 기타", "C > 알수없음"]
    kept = mt.strip_other_classes(cats, "의류")
    assert "A > 신발 > 스니커즈" not in kept
    assert "B > 의류 > 팬츠" in kept
    assert "패션잡화 > 기타" in kept          # 잡화는 폴백용으로 남긴다
    assert "C > 알수없음" in kept             # 계열 불명도 남긴다


def test_search_order_low_first_then_mid():
    """★규칙4: 전체 재검색 단계에서 하위(1차) → 중위(2차) 순서."""
    # 상위·중위로는 못 좁히는 자료 — 하위(비니)만 걸린다
    cats = ["아웃도어 > 등산 > 비니", "생활 > 주방 > 컵"]
    cat, step = mt.find_category("아름트리-무신사-남성-모자-비니", cats)
    assert cat == "아웃도어 > 등산 > 비니"
    assert step.startswith("2-2) 하위 전체")


def test_mid_used_when_low_absent():
    cats = ["패션 > 모자 > 기타", "생활 > 주방 > 컵"]
    cat, step = mt.find_category("아름트리-무신사-남성-모자-비니", cats)
    assert cat == "패션 > 모자 > 기타"
    assert "중위" in step or "2-1" in step


def test_maternity_category_counts_as_female_even_without_the_word():
    """★'임부복' 처럼 '여성' 글자가 없어도 여성 전용 카테고리다.

    남성 필터에 마땅한 남성 카테고리가 없을 때, 이런 카테고리를 '성별 무관'
    으로 보고 최근접 후보로 골라버리면 오매칭이 된다.
    """
    assert mt.gender_of("임부복") == "여성"
    assert mt.gender_of("임산부 원피스") == "여성"
    assert mt.has_gender("임부복", "여성") is True

    cats = ["임부복", "생활용품"]
    cat, step = mt.find_category("아름트리-무신사-남성-상의-니트", cats)
    assert cat != "임부복"          # 남성 필터가 임부복을 고르면 안 된다
    assert cat == "생활용품"


def test_gender_leakage_reported_examples():
    """사용자가 지적한 실제 사례 — 남성 필터에 임부복·여성패션·여성브이넥 배제,
    여성 필터에 남성복·남성패션·남성니트 배제."""
    cats = ["임부복", "여성패션", "여성 브이넥", "남성복", "남성패션", "남성 니트"]

    male_cat, _ = mt.find_category("아름트리-무신사-남성-상의-니트", cats)
    assert male_cat not in ("임부복", "여성패션", "여성 브이넥")

    female_cat, _ = mt.find_category("아름트리-무신사-여성-상의-니트", cats)
    assert female_cat not in ("남성복", "남성패션", "남성 니트")


def test_gender_of_recognizes_implicit_female_words():
    """★'임부복' 처럼 '여성' 글자가 없어도 여성 전용 카테고리로 인식한다.

    없으면 남성 필터에서 마땅한 남성 카테고리가 없을 때 최근접 단계가
    성별무관으로 보고 임부복 을 그냥 골라버린다 (실제 오매칭 사례).
    """
    assert mt.gender_of("임부복") == "여성"
    assert mt.gender_of("임산부 원피스") == "여성"
    assert mt.gender_of("마터니티 룩") == "여성"


def test_male_filter_never_falls_back_to_maternity_category():
    cats = ["임부복", "생활용품"]
    cat, step = mt.find_category("아름트리-무신사-남성-상의-니트", cats)
    assert cat != "임부복"
    assert cat == "생활용품"
    assert step.startswith("3) 최근접")


# ── 짧은 필터명(브랜드-사이트 없이 성별-상위-하위 3조각) 파싱 ──────


def test_parse_filter_name_without_brand_site_prefix():
    """★'여성-신발-구두' 처럼 3조각뿐이면 앞 2개를 브랜드-사이트로 오인해
    성별·상위 정보를 통째로 날리면 안 된다.
    """
    p = mt.parse_filter_name("여성-신발-구두")
    assert p.ignored == []
    assert p.top == "여성"
    assert p.mid == "신발"
    assert p.lows == ["구두"]


def test_parse_filter_name_still_ignores_brand_site_when_enough_segments():
    """5조각 이상인 정상 필터명은 기존처럼 앞 2조각(브랜드-사이트)을 무시한다."""
    p = mt.parse_filter_name("아름트리-무신사-남성-모자-비니")
    assert p.ignored == ["아름트리", "무신사"]
    assert p.top == "남성"
    assert p.mid == "모자"


def test_parse_filter_name_two_segments_gender_and_item():
    p = mt.parse_filter_name("남성-신발")
    assert p.ignored == []
    assert p.top == "남성"
    assert p.mid == "신발"


def test_find_category_for_short_gender_item_item_filter():
    """★요건: 필터명 '남성-잡화-신발' — 성별·상위·하위가 살아있어야 올바르게 고른다."""
    name = "남성-잡화-신발"
    cats = [
        "잡화 > 남성신발",
        "여성패션 > 신발 > 구두",       # 반대 성별 — 배제
        "남성패션 > 상의 > 니트",       # 다른 품목(의류) — 배제
    ]
    cat, step = mt.find_category(name, cats)
    assert cat == "잡화 > 남성신발"


def test_find_category_falls_back_within_generic_when_no_shoe_class():
    """신발 계열이 전혀 없으면 잡화 안에서 성별이 맞는 것을 고른다."""
    name = "남성-잡화-신발"
    cats = ["잡화 > 남성용품 > 지갑", "잡화 > 여성용품 > 파우치", "패션의류 > 남성 > 니트"]
    cat, step = mt.find_category(name, cats)
    assert cat == "잡화 > 남성용품 > 지갑"


def test_find_category_picks_nearest_generic_when_nothing_matches_well():
    """예) 잡화기타·구두기타 처럼 애매한 후보뿐이면 그중 가장 가까운 걸 고른다."""
    name = "남성-잡화-신발"
    cat, step = mt.find_category(name, ["잡화기타", "구두기타", "문구"])
    assert cat == "구두기타"
    assert step.startswith("3) 최근접")


def test_shoe_synonyms_include_active_and_sports_shoes():
    """★요건 예시 — '활동화'·'스포츠화' 도 신발 동의어로 인식한다."""
    assert mt.class_of("잡화 > 남성 > 활동화") == "신발"
    assert mt.class_of("잡화 > 남성 > 스포츠화") == "신발"
    cat, step = mt.find_category(
        "남성-잡화-신발", ["잡화 > 남성 > 활동화", "여성패션 > 상의"]
    )
    assert cat == "잡화 > 남성 > 활동화"


# ── 뷰티 계열 (스크린샷 하위 카테고리 = 뷰티의 다른 이름) ──────────


def test_class_of_recognizes_beauty_subcategories():
    """★뷰티 화면 하위 카테고리명 자체를 '뷰티' 계열로 인식한다."""
    for word in (
        "스킨케어", "마스크팩", "베이스메이크업", "립메이크업", "아이메이크업",
        "네일", "프레그런스", "선케어", "클렌징", "필링", "헤어케어", "바디케어",
        "쉐이빙", "제모", "뷰티디바이스", "미용소품", "헬스", "푸드",
    ):
        assert mt.class_of(word) == "뷰티", f"{word} 가 뷰티 계열로 인식되지 않음"


def test_beauty_filter_excludes_clothing_and_shoes():
    """뷰티 필터는 의류·신발 카테고리와 섞이지 않는다."""
    cats = ["뷰티 > 스킨케어 > 토너", "남성패션 > 상의 > 니트", "신발 > 운동화"]
    cat, step = mt.find_category("여성-뷰티-스킨케어", cats)
    assert cat == "뷰티 > 스킨케어 > 토너"


def test_beauty_class_isolated_from_other_classes():
    """의류·신발 필터도 뷰티 카테고리를 잘못 고르지 않는다."""
    cats = ["뷰티 > 헤어케어 > 샴푸", "남성패션 > 상의 > 니트"]
    cat, step = mt.find_category("남성-상의-니트", cats)
    assert cat == "남성패션 > 상의 > 니트"


# ── 아우터 하위 카테고리 (다른 이름 -> 의류 계열) ──────────────────


def test_class_of_recognizes_outer_subcategories():
    """★아우터 화면 하위 카테고리명을 '의류' 계열로 인식한다."""
    for word in (
        "후드집업", "블루종", "라이더스 재킷", "슈트/블레이저 재킷", "카디건",
        "경량 패딩", "패딩 베스트", "사파리/헌팅 재킷", "트러커 재킷",
        "스타디움 재킷", "나일론/코치 재킷", "트레이닝 재킷", "아노락 재킷",
        "플리스/뽀글이", "환절기 코트", "베스트", "무스탕/퍼",
        "겨울 싱글 코트", "겨울 더블 코트", "겨울 기타 코트", "숏패딩",
        "롱패딩/헤비 아우터", "기타 아우터",
    ):
        assert mt.class_of(word) == "의류", f"{word} 가 의류 계열로 인식되지 않음"


def test_outer_filter_excludes_shoes_and_beauty():
    """아우터(패딩 등) 필터는 신발·뷰티 카테고리와 섞이지 않는다."""
    cats = ["아우터 > 패딩 > 롱패딩", "신발 > 운동화", "뷰티 > 스킨케어"]
    cat, step = mt.find_category("남성-아우터-패딩", cats)
    assert cat == "아우터 > 패딩 > 롱패딩"


# ── 바지 하위 카테고리 · 속옷/홈웨어 계열 ───────────────────────────


def test_class_of_recognizes_pants_subcategories():
    for word in (
        "데님 팬츠", "트레이닝/조거 팬츠", "코튼 팬츠", "슈트 팬츠/슬랙스",
        "숏 팬츠", "레깅스", "점프 슈트/오버올", "기타 하의",
    ):
        assert mt.class_of(word) == "의류", f"{word} 가 의류 계열로 인식되지 않음"


def test_class_of_recognizes_underwear_subcategories():
    for word in ("홈웨어", "여성 속옷 상의", "여성 속옷 하의", "여성 속옷 세트"):
        assert mt.class_of(word) == "속옷", f"{word} 가 속옷 계열로 인식되지 않음"


def test_underwear_filter_excludes_other_classes():
    cats = ["속옷/홈웨어 > 여성 속옷 상의", "아우터 > 패딩", "신발 > 운동화"]
    cat, step = mt.find_category("여성-속옷-상의", cats)
    assert cat == "속옷/홈웨어 > 여성 속옷 상의"


# ── 바지 하위 카테고리 · 속옷/홈웨어 · 신발 품목별 (다른 이름) ─────


def test_class_of_recognizes_pants_subcategories():
    for word in (
        "데님 팬츠", "트레이닝/조거 팬츠", "코튼 팬츠", "슈트 팬츠/슬랙스",
        "숏 팬츠", "레깅스", "점프 슈트/오버올", "기타 하의",
    ):
        assert mt.class_of(word) == "의류", f"{word} 가 의류 계열로 인식되지 않음"


def test_class_of_recognizes_underwear_subcategories():
    for word in ("홈웨어", "여성 속옷 상의", "여성 속옷 하의", "여성 속옷 세트"):
        assert mt.class_of(word) == "속옷", f"{word} 가 속옷 계열로 인식되지 않음"


def test_class_of_recognizes_shoe_item_subcategories():
    for word in (
        "스니커즈", "스포츠화", "구두", "부츠/워커", "샌들/슬리퍼",
        "패딩/퍼 신발", "신발용품",
    ):
        assert mt.class_of(word) == "신발", f"{word} 가 신발 계열로 인식되지 않음"


def test_class_of_prefers_longer_match_at_same_position():
    """★'패딩/퍼 신발' 처럼 앞머리가 다른 계열 단어(패딩)와 겹치면,
    더 길게(구체적으로) 일치하는 쪽(신발 전체 문구)을 우선한다.
    """
    assert mt.class_of("패딩/퍼 신발") == "신발"     # "패딩"(의류) 보다 길게 일치
    assert mt.class_of("패딩 베스트") == "의류"       # 신발 관련 없음 — 그대로 의류


def test_underwear_filter_excludes_outer_and_shoes():
    cats = ["속옷 > 여성속옷상의", "아우터 > 패딩", "신발 > 운동화"]
    cat, step = mt.find_category("여성-속옷-상의", cats)
    assert cat == "속옷 > 여성속옷상의"


def test_class_of_recognizes_hat_subcategories():
    """★모자 화면 하위 카테고리명을 '모자' 계열로 인식한다."""
    for word in (
        "캡/야구모자", "헌팅캡/베레모", "페도라", "버킷/사파리햇",
        "비니", "트루퍼", "바라클라바", "기타 모자",
    ):
        assert mt.class_of(word) == "모자", f"{word} 가 모자 계열로 인식되지 않음"


def test_hat_filter_excludes_other_classes():
    cats = ["모자 > 페도라", "의류 > 니트", "신발 > 운동화"]
    cat, step = mt.find_category("남성-모자-페도라", cats)
    assert cat == "모자 > 페도라"


# ── DB화 — 동떨어진 형제 품목 금지, 일반화(상위) 폴백만 허용 ──────


def test_shoe_filter_never_falls_back_to_sibling_shoe_type():
    """★신발 -> 구두 는 NOT-OK. 구두만 있으면 매핑하지 않는다."""
    cat, step = mt.find_category("남성-신발", ["구두 전용관"])
    assert cat == ""
    assert "형제 품목" in step or step == "미검출"


def test_shoe_filter_falls_back_to_generic_bucket():
    """신발 -> 잡화 는 OK."""
    cat, step = mt.find_category("남성-신발", ["구두 전용관", "남성 잡화"])
    assert cat == "남성 잡화"


def test_socks_filter_never_falls_back_to_tshirt():
    """★양말 -> 티셔츠 는 NOT-OK. 티셔츠만 있으면 매핑하지 않는다."""
    cat, step = mt.find_category("남성-양말", ["남성 티셔츠 전문관"])
    assert cat == ""


def test_socks_filter_falls_back_to_other_clothing_bucket():
    """양말 -> 기타의류 는 OK."""
    cat, step = mt.find_category("남성-양말", ["남성 티셔츠 전문관", "남성 기타의류"])
    assert cat == "남성 기타의류"


def test_sneakers_filter_never_falls_back_to_opposite_gender_sneakers():
    """★남성스니커즈 -> 여성스니커즈 는 NOT-OK (성별 규칙으로도 이미 배제됨)."""
    cat, step = mt.find_category("남성-신발-스니커즈", ["여성스니커즈"])
    assert cat == ""


def test_sneakers_filter_falls_back_to_same_gender_shoe_bucket():
    """남성스니커즈 -> 남성신발 은 OK (같은 성별의 더 넓은 신발 카테고리)."""
    cat, step = mt.find_category("남성-신발-스니커즈", ["여성스니커즈", "남성신발"])
    assert cat == "남성신발"


def test_specific_item_conflict_ignores_safe_fallback_words():
    """안전한 일반화 단어(잡화 등)가 함께 있으면 형제 품목이라도 막지 않는다."""
    parsed = mt.parse_filter_name("남성-신발")
    assert mt._specific_item_conflict("잡화기타 (구두 포함)", parsed) is False


def test_specific_item_conflict_allows_same_target_item():
    """찾는 것과 같은 품목이면 형제 충돌로 보지 않는다."""
    parsed = mt.parse_filter_name("남성-신발-구두")
    assert mt._specific_item_conflict("남성 구두", parsed) is False


def test_sibling_exclusion_applies_to_all_stages_not_just_nearest():
    """★실사례: '맨투맨/후드' 필터가 다른 마켓에서 '패딩'으로 새던 문제.

    형제 품목 배제는 3) 최근접 단계뿐 아니라 앞선 단계(2-1 등)에도 똑같이
    적용돼야 한다. 패딩만 있으면 매핑하지 않고, 맨투맨/후드가 있으면
    그것을 고른다.
    """
    with_target = ["여성의류 > 아우터 > 패딩", "여성의류 > 상의 > 맨투맨/후드"]
    cat, step = mt.find_category("여성-아우터-맨투맨/후드", with_target)
    assert cat == "여성의류 > 상의 > 맨투맨/후드"

    only_padding = ["여성의류 > 아우터 > 패딩"]
    cat2, step2 = mt.find_category("여성-아우터-맨투맨/후드", only_padding)
    assert cat2 == ""


def test_underwear_related_compound_word_not_treated_as_sibling_conflict():
    """★'여성속옷상의' 처럼 찾는 말(속옷·상의)을 담은 긴 합성어는 형제가 아니다."""
    cats = ["속옷/홈웨어 > 여성 속옷 상의", "아우터 > 패딩", "신발 > 운동화"]
    cat, step = mt.find_category("여성-속옷-상의", cats)
    assert cat == "속옷/홈웨어 > 여성 속옷 상의"


# ── "브랜드" 카테고리는 엑셀에 있어도 절대 확정하지 않는다 ─────────


def test_find_category_never_confirms_brand_only_category():
    """★실사례: 옥션2.0/11번가/G마켓2.0 엑셀에 정식 카테고리 없이 '브랜드 …'
    카테고리만 있는 경우 — 매핑하지 않는다(엑셀에 있어도 확정하지 않음).
    """
    cats = ["브랜드 여성의류 > 야상/점퍼/패딩 > 바람막이"]
    cat, step = mt.find_category("여성-아우터-바람막이", cats)
    assert cat == ""
    assert "브랜드" in step


def test_find_category_prefers_non_brand_when_both_exist():
    """정식(비브랜드) 카테고리가 있으면 그것을 쓴다."""
    cats = [
        "브랜드 여성의류 > 야상/점퍼/패딩 > 바람막이",
        "패션의류 > 여성의류 > 아우터 > 바람막이",
    ]
    cat, step = mt.find_category("여성-아우터-바람막이", cats)
    assert cat == "패션의류 > 여성의류 > 아우터 > 바람막이"


def test_find_category_brand_exclusion_applies_regardless_of_gender():
    """성별이 없는 필터에도 브랜드 배제가 동일하게 적용된다."""
    cats = ["브랜드 캐쥬얼의류 > 티셔츠/셔츠 > 맨투맨/후드"]
    cat, step = mt.find_category("아우터-맨투맨", cats)
    assert cat == ""
