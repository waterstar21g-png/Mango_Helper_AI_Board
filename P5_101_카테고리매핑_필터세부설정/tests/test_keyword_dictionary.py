"""연관검색어DB(keyword_dictionary) 테스트 — 요건 2026-08-23.

CATEGORY_MASTER(Cat_ID·Cat_Name·Parent_ID·Level·Full_Path) +
KEYWORD_DICTIONARY(Keyword_ID·Search_Keyword·Target_Cat_ID·Mapping_Type·Priority)
논리구조와, 검색어 4단계 폭포수(완전일치→유사어→동일범주→확대범주) 해석을 검증한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import keyword_dictionary as kd  # noqa: E402

PATHS = [
    "패션잡화 > 남성 모자 > 모자기타",
    "패션잡화 > 남성 모자 > 비니/베레모/페도라",
    "패션잡화 > 남성 모자 > 야구모자/뉴에라/스냅백",
    "패션잡화 > 남성 시계 > 디지털시계",
    "패션잡화 > 남성 시계 > 브랜드시계",
    "남성의류 > 캐주얼자켓 > 가죽자켓/무스탕",
    "남성의류 > 캐주얼자켓 > 데님자켓",
    "남성의류 > 캐주얼바지 > 슬랙스",
    "패션의류잡화 > 남성패션 > 남성화 > 로퍼/보트슈즈/웰트화 > 남성로퍼",
    "패션의류잡화 > 남성패션 > 남성화 > 남성슬립온",
    "패션의류잡화 > 남성패션 > 남성화 > 남성부츠",
]


def test_category_master_tree_structure():
    db = kd.build(PATHS)
    root_nodes = [c for c in db.categories.values() if c.parent_id == "ROOT" or c.parent_id is None]
    assert any(n.cat_name == "패션잡화" for n in root_nodes)
    assert any(n.cat_name == "남성의류" for n in root_nodes)

    hat = next(c for c in db.categories.values() if c.cat_name == "야구모자/뉴에라/스냅백")
    assert hat.level == 3
    assert hat.full_path == "패션잡화 > 남성 모자 > 야구모자/뉴에라/스냅백"
    parent = db.categories[hat.parent_id]
    assert parent.cat_name == "남성 모자"


def test_shared_prefix_paths_reuse_same_parent_node():
    """같은 상위 경로를 쓰는 여러 리프는 부모 노드를 하나만 공유한다."""
    db = kd.build(PATHS)
    hat_nodes = [c for c in db.categories.values() if c.cat_name == "남성 모자"]
    assert len(hat_nodes) == 1
    children = db.children_of(hat_nodes[0].cat_id)
    assert len(children) == 3  # 모자기타 · 비니/베레모/페도라 · 야구모자/뉴에라/스냅백


def test_is_leaf_and_leaves():
    db = kd.build(PATHS)
    top = next(c for c in db.categories.values() if c.cat_name == "패션잡화")
    assert db.is_leaf(top.cat_id) is False
    leaf = next(c for c in db.categories.values() if c.cat_name == "디지털시계")
    assert db.is_leaf(leaf.cat_id) is True
    assert len(db.leaves()) == len(PATHS)  # 각 경로의 리프 1개씩, 중복 경로 없음


def test_ancestors_of_returns_near_to_far():
    db = kd.build(PATHS)
    leaf = next(c for c in db.categories.values() if c.cat_name == "디지털시계")
    names = [a.cat_name for a in db.ancestors_of(leaf.cat_id)]
    assert names == ["남성 시계", "패션잡화"]


# ── KEYWORD_DICTIONARY ────────────────────────────────────────────


def test_sy_synonym_from_slash_split_leaf():
    """"비니/베레모/페도라" 처럼 "/" 로 쪼개진 리프는 각 토큰이 동의어(SY)로 등록된다."""
    db = kd.build(PATHS)
    for want in ("비니", "베레모", "페도라"):
        hits = db.lookup(want, mapping_types=("SY",))
        assert hits, f"{want} 동의어 미등록"
        assert db.full_path(hits[0].target_cat_id) == "패션잡화 > 남성 모자 > 비니/베레모/페도라"


def test_mo_attribute_plus_token_combination():
    """★요건(형태소분리): 조상 경로의 "남성" + 리프 토큰 "무스탕" → "남성무스탕"."""
    db = kd.build(PATHS)
    hits = db.lookup("남성무스탕", mapping_types=("MO",))
    assert hits
    assert db.full_path(hits[0].target_cat_id) == "남성의류 > 캐주얼자켓 > 가죽자켓/무스탕"


def test_mo_strips_attribute_prefix_from_leaf_token():
    """리프 토큰에 이미 성별이 붙어 있으면("남성로퍼") 뗀 원형("로퍼")도 등록한다."""
    db = kd.build(PATHS)
    hits = db.lookup("로퍼", mapping_types=("MO",))
    assert hits
    assert "남성로퍼" in db.full_path(hits[0].target_cat_id)


def test_re_sibling_keywords_registered_both_ways():
    """★요건(동일/연관어): 형제 리프("모자기타")의 토큰이 다른 형제("야구모자"
    쪽 리프)의 RE 검색어로도 등록된다."""
    db = kd.build(PATHS)
    hat_leaf = next(c for c in db.categories.values() if c.cat_name == "야구모자/뉴에라/스냅백")
    re_hits = [k for k in db.keywords if k.mapping_type == "RE" and k.target_cat_id == hat_leaf.cat_id]
    re_words = {k.search_keyword for k in re_hits}
    assert "모자기타" in re_words
    assert any(w in re_words for w in ("비니", "베레모", "페도라"))


def test_ex_ancestor_keywords_ranked_near_first():
    """★요건(확대범주): 조상 이름이 EX 로 등록되고, 가까운 조상이 더 높은 우선순위."""
    db = kd.build(PATHS)
    leaf = next(c for c in db.categories.values() if c.cat_name == "디지털시계")
    ex_hits = sorted(
        (k for k in db.keywords if k.mapping_type == "EX" and k.target_cat_id == leaf.cat_id),
        key=lambda k: k.priority,
    )
    assert [k.search_keyword for k in ex_hits] == ["남성 시계", "패션잡화"]


def test_curated_item_synonyms_are_merged_in():
    """★요건(유사검색어): matching.ITEM_SYNONYMS 의 "캡모자"↔"야구모자" 도 SY 로 반영된다."""
    db = kd.build(PATHS)
    hits = db.lookup("캡모자", mapping_types=("SY",))
    assert hits
    assert "야구모자" in db.full_path(hits[0].target_cat_id)


# ── resolve() 4단계 폭포수 ─────────────────────────────────────────


def test_resolve_exact_match_first():
    db = kd.build(PATHS)
    cid, step = db.resolve("디지털시계")
    assert step.startswith("1)")
    assert db.full_path(cid) == "패션잡화 > 남성 시계 > 디지털시계"


def test_resolve_synonym_match_second():
    db = kd.build(PATHS)
    cid, step = db.resolve("뉴에라")
    assert step.startswith("2)")
    assert db.full_path(cid) == "패션잡화 > 남성 모자 > 야구모자/뉴에라/스냅백"


def test_resolve_sibling_match_third():
    """★요건 예시: "정장바지"(어디에도 SY/MO 로 안 걸림) → 연관어(RE)로 수동
    등록해 두면 3) 단계에서 확정된다 (예: 남성의류 > 캐주얼바지 > 슬랙스)."""
    db = kd.build(PATHS)
    slacks = next(c for c in db.categories.values() if c.cat_name == "슬랙스")
    db._add_keyword("정장바지", slacks.cat_id, "RE", 3)
    cid, step = db.resolve("정장바지")
    assert step.startswith("3)")
    assert db.full_path(cid) == "남성의류 > 캐주얼바지 > 슬랙스"


def test_resolve_expanded_category_match_fourth():
    db = kd.build(PATHS)
    cid, step = db.resolve("패션잡화")
    assert step.startswith(("1)", "4)"))  # 상위명 자체가 리프가 아니면 4)


def test_resolve_returns_none_when_unknown():
    db = kd.build(PATHS)
    cid, step = db.resolve("존재하지않는검색어절대")
    assert cid is None
    assert step == "미검출"


def test_resolve_empty_keyword():
    db = kd.build(PATHS)
    cid, step = db.resolve("")
    assert cid is None
    assert step == "검색어 없음"


def test_build_from_empty_paths():
    db = kd.build([])
    assert db.categories == {}
    assert db.keywords == []


def test_add_path_ignores_blank_segments():
    db = kd.KeywordDB()
    leaf_id = db.add_path("A >  > B")
    node = db.categories[leaf_id]
    assert node.cat_name == "B"
    assert node.level == 2


# ── 성능 회귀 방지 (실사례 2026-08-23) ──────────────────────────────
#   `leaves()`/`is_leaf()` 가 카테고리마다 전체를 다시 훑는 O(N²) 로
#   짜여 있어, 실제 6개 마켓 데이터(14,000+ 건)에서 `build_dictionary()`
#   1회에 4초 이상 걸렸다(그 결과 `find_category` 호출마다 마켓당
#   0.5초씩 걸려 전체 실행이 심각하게 느려졌다). 부모→자식 색인으로
#   O(1)/O(N) 이 되도록 고쳤고, 아래 테스트로 회귀를 막는다.


def _synthetic_paths(n_top: int = 20, n_mid: int = 20, n_leaf: int = 5) -> list[str]:
    return [
        f"대분류{t} > 중분류{t}-{m} > 리프{t}-{m}-{leaf}"
        for t in range(n_top)
        for m in range(n_mid)
        for leaf in range(n_leaf)
    ]


def test_build_dictionary_is_fast_for_thousands_of_categories():
    import time

    paths = _synthetic_paths(20, 20, 5)  # 2,000개 카테고리
    t0 = time.time()
    db = kd.build(paths)
    elapsed = time.time() - t0
    assert len(db.categories) > 2000
    assert elapsed < 2.0, f"2,000개 카테고리 구축에 {elapsed:.2f}초 — 너무 느림(O(N^2) 회귀 의심)"


def test_leaves_and_is_leaf_do_not_rescan_everything_per_call():
    import time

    paths = _synthetic_paths(20, 20, 5)
    db = kd.build(paths)
    t0 = time.time()
    for _ in range(50):
        db.leaves()
    elapsed = time.time() - t0
    assert elapsed < 1.0, f"leaves() 50회 호출에 {elapsed:.2f}초 — 너무 느림(O(N^2) 회귀 의심)"


def test_resolve_is_fast_after_build():
    import time

    paths = _synthetic_paths(20, 20, 5)
    db = kd.build(paths)
    t0 = time.time()
    for _ in range(200):
        db.resolve("리프0-0-0")
    elapsed = time.time() - t0
    assert elapsed < 0.5, f"resolve() 200회 호출에 {elapsed:.2f}초 — 너무 느림(O(N^2) 회귀 의심)"


# ── 범위 한정(scoped) 폭포수 — "이 카테고리가 실패했을 때 형제/조상만" ──


def test_siblings_of_excludes_self():
    db = kd.build(PATHS)
    hat_leaf = next(c for c in db.categories.values() if c.cat_name == "야구모자/뉴에라/스냅백")
    sib_names = {s.cat_name for s in db.siblings_of(hat_leaf.cat_id)}
    assert sib_names == {"모자기타", "비니/베레모/페도라"}
    assert hat_leaf.cat_name not in sib_names


def test_substitute_for_picks_sibling_first():
    """★요건 시나리오: M112(야구모자/뉴에라/스냅백) 카테고리가 이 마켓에는
    없다고 가정 — 형제(M111: 비니/베레모/페도라 등)로 대체된다."""
    db = kd.build(PATHS)
    hat_leaf = next(c for c in db.categories.values() if c.cat_name == "야구모자/뉴에라/스냅백")
    sub_id, step = db.substitute_for(hat_leaf.cat_id)
    assert step.startswith("3) 동일범주")
    assert db.categories[sub_id].cat_name in {"모자기타", "비니/베레모/페도라"}


def test_substitute_for_falls_back_to_ancestor_when_no_sibling_available():
    """형제도 전부 이 마켓엔 없다고 가정 — 조상(상위 카테고리)으로 확대."""
    db = kd.build(PATHS)
    hat_leaf = next(c for c in db.categories.values() if c.cat_name == "야구모자/뉴에라/스냅백")
    parent = db.categories[hat_leaf.parent_id]  # "남성 모자"
    sub_id, step = db.substitute_for(hat_leaf.cat_id, available_cat_ids=[parent.cat_id])
    assert step.startswith("4) 확대범주")
    assert sub_id == parent.cat_id


def test_substitute_for_returns_none_only_when_scope_truly_empty():
    """★요건(절대): 범위 자체가 비어 있을 때만(카테고리가 정말 하나도
    없을 때만) None 을 반환한다 — 그것도 "미검출"이 아니라 "카테고리
    자료 없음"으로 구분한다."""
    db = kd.build(PATHS)
    hat_leaf = next(c for c in db.categories.values() if c.cat_name == "야구모자/뉴에라/스냅백")
    sub_id, step = db.substitute_for(hat_leaf.cat_id, available_cat_ids=[])
    assert sub_id is None
    assert step == "카테고리 자료 없음"


def test_substitute_for_escalates_to_cousin_branch_when_direct_lineage_missing():
    """★요건(절대): 형제·직계 조상이 전부 없어도, 이 마켓(범위) 안에
    카테고리가 하나라도 있으면 절대 빈손으로 끝내지 않는다 — 전혀 다른
    가지(사촌)의 리프라도 반드시 하나 지정한다."""
    db = kd.build(PATHS)
    hat_leaf = next(c for c in db.categories.values() if c.cat_name == "야구모자/뉴에라/스냅백")
    # M112 도, 그 형제(모자기타·비니)도, 조상(남성 모자·패션잡화)도 이
    # 마켓엔 없고, 완전히 다른 가지의 리프("슬랙스")만 있다고 가정.
    far_leaf = next(c for c in db.categories.values() if c.cat_name == "슬랙스")
    sub_id, step = db.substitute_for(hat_leaf.cat_id, available_cat_ids=[far_leaf.cat_id])
    assert sub_id == far_leaf.cat_id
    assert step == "5) 최근접 강제지정(전범위)"


def test_substitute_for_cousin_subtree_before_final_forced_pick():
    """조상 노드 자신은 없어도, 그 조상의 하위트리(사촌 리프)에 available
    한 것이 있으면 5) 최근접 강제지정보다 먼저 그걸 쓴다."""
    db = kd.build(PATHS)
    hat_leaf = next(c for c in db.categories.values() if c.cat_name == "야구모자/뉴에라/스냅백")
    digital_watch = next(c for c in db.categories.values() if c.cat_name == "디지털시계")
    # "남성 모자"(직계 조상)·형제는 없고, "패션잡화"(공통 조상) 아래 다른
    # 가지인 "디지털시계"(사촌 리프, "남성 시계" 하위)만 있다고 가정.
    sub_id, step = db.substitute_for(hat_leaf.cat_id, available_cat_ids=[digital_watch.cat_id])
    assert sub_id == digital_watch.cat_id
    assert "하위트리" in step


def test_substitute_for_unknown_category():
    db = kd.build(PATHS)
    sub_id, step = db.substitute_for("C9999")
    assert sub_id is None
    assert step == "대상 카테고리 없음"


def test_resolve_with_fallback_reproduces_screenshot_scenario():
    """★요건 원문 그대로 재현: '남자 캡모자' 검색 → 2)유사어매칭으로
    "야구모자/뉴에라/스냅백"(M112) 확정 → 그 마켓엔 M112 재고가 0(=목록에
    없음) → 3)동일범주로 형제("비니/베레모/페도라" 등)로 대체."""
    db = kd.build(PATHS)
    hat_leaf = next(c for c in db.categories.values() if c.cat_name == "야구모자/뉴에라/스냅백")
    beanie = next(c for c in db.categories.values() if c.cat_name == "비니/베레모/페도라")
    misc = next(c for c in db.categories.values() if c.cat_name == "모자기타")

    # 이 마켓엔 M112(야구모자/뉴에라/스냅백)가 없고, 형제만 있다고 가정
    available = [c.cat_id for c in db.categories.values() if c.cat_id != hat_leaf.cat_id]
    cid, step = db.resolve_with_fallback("캡모자", available_cat_ids=available)
    assert step.startswith("2) 유사어매칭(SY) 대상 없음 → 3) 동일범주")
    assert cid in {beanie.cat_id, misc.cat_id}


def test_resolve_with_fallback_expands_to_ancestor_when_siblings_also_missing():
    db = kd.build(PATHS)
    hat_leaf = next(c for c in db.categories.values() if c.cat_name == "야구모자/뉴에라/스냅백")
    parent = db.categories[hat_leaf.parent_id]  # "남성 모자"

    # M112 도, 그 형제들도 이 마켓엔 없고 상위("남성 모자")만 있다고 가정
    cid, step = db.resolve_with_fallback("캡모자", available_cat_ids=[parent.cat_id])
    assert "4) 확대범주" in step
    assert cid == parent.cat_id


def test_resolve_with_fallback_uses_direct_hit_when_available():
    """대상이 그 범위 안에 있으면 대체를 찾지 않고 그대로 확정한다."""
    db = kd.build(PATHS)
    hat_leaf = next(c for c in db.categories.values() if c.cat_name == "야구모자/뉴에라/스냅백")
    cid, step = db.resolve_with_fallback("캡모자", available_cat_ids=[hat_leaf.cat_id])
    assert cid == hat_leaf.cat_id
    assert step == "2) 유사어매칭(SY)"


def test_resolve_with_fallback_exact_match_also_respects_availability():
    db = kd.build(PATHS)
    leaf = next(c for c in db.categories.values() if c.cat_name == "디지털시계")
    sibling = next(c for c in db.categories.values() if c.cat_name == "브랜드시계")
    cid, step = db.resolve_with_fallback("디지털시계", available_cat_ids=[sibling.cat_id])
    assert cid == sibling.cat_id
    assert step.startswith("3) 동일범주")


def test_resolve_with_fallback_no_availability_constraint_behaves_like_resolve():
    db = kd.build(PATHS)
    cid, step = db.resolve_with_fallback("디지털시계")
    assert step == "1) 완전일치"
    assert db.full_path(cid) == "패션잡화 > 남성 시계 > 디지털시계"


def test_resolve_with_fallback_unknown_keyword_still_forces_a_pick():
    """★요건(절대): 이 DB의 존재 목적은 미검출을 없애는 것 — SY/MO 로 전혀
    못 찾아도 카테고리 자료가 있으면 가장 비슷한 것 하나를 강제 지정한다."""
    db = kd.build(PATHS)
    cid, step = db.resolve_with_fallback("존재하지않는검색어절대로없음")
    assert cid is not None
    assert step.startswith("5) 최근접 강제지정")


def test_resolve_with_fallback_reports_no_data_only_when_scope_empty():
    db = kd.build(PATHS)
    cid, step = db.resolve_with_fallback("존재하지않는검색어", available_cat_ids=[])
    assert cid is None
    assert step == "카테고리 자료 없음"
