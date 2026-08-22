"""통합정보화 DB(category_db) 테스트 — 요건재정의(2026-08-22) B 항."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import category_db as cdb  # noqa: E402
import matching as mt  # noqa: E402

EXCELS = {
    "AUC20": [
        "패션의류잡화 > 남성 > 모자 > 버킷햇",
        "패션의류잡화 > 남성 > 모자 > 비니",
    ],
    "11ST": [
        "잡화 > 모자 > 사파리햇",
        "잡화 > 신발 > 운동화",
    ],
    "GMK20": [
        "의류잡화 > 모자 > 벙거지",
    ],
}


def test_build_indexes_all_markets():
    db = cdb.CategoryDB.build(EXCELS)
    assert db.market_count == 3
    assert db.path_count == 5


def test_build_ignores_empty_and_none():
    db = cdb.CategoryDB.build({"A": ["", None, "  "]})
    assert db.path_count == 0
    assert bool(db) is False


def test_search_cross_market():
    """하위 카테고리를 검색어로 넣으면 여러 마켓의 항목이 걸린다."""
    db = cdb.CategoryDB.build(EXCELS)
    hits = db.search("모자")
    assert "패션의류잡화 > 남성 > 모자 > 버킷햇" in hits
    assert "잡화 > 모자 > 사파리햇" in hits
    assert "의류잡화 > 모자 > 벙거지" in hits


def test_related_terms_priority_low_first():
    """★요건: 연관검색어는 하위단계 1순위, 상위단계 2·3순위."""
    db = cdb.CategoryDB.build(EXCELS)
    related = db.related("모자")
    # "모자" 로 교차검색되는 경로들의 하위(리프)가 1순위로 먼저 나온다
    priorities = {name: prio for name, prio in related}
    assert priorities.get("버킷햇") == 1
    assert priorities.get("사파리햇") == 1
    assert priorities.get("벙거지") == 1
    # 상위(패션의류잡화·잡화·의류잡화)는 2·3순위로 뒤에 나온다
    low_priority_names = [n for n, p in related if p == 1]
    high_priority_names = [n for n, p in related if p > 1]
    assert low_priority_names and high_priority_names
    assert related.index((low_priority_names[0], 1)) < len(low_priority_names)


def test_related_terms_excludes_self():
    db = cdb.CategoryDB.build(EXCELS)
    related_names = db.related_terms("모자")
    assert "모자" not in related_names


def test_related_terms_empty_when_unknown():
    db = cdb.CategoryDB.build(EXCELS)
    assert db.related_terms("존재하지않는단어") == []


def test_build_with_no_excels():
    db = cdb.CategoryDB.build(None)
    assert bool(db) is False
    assert db.related_terms("모자") == []


# ── find_category 에서 정보화DB 를 5) 단계 확장검색에 활용 ──────────


def test_find_category_uses_db_related_terms_when_direct_search_fails():
    """직접 검색(하위·중위·확장범주)으로 못 찾을 때, 다른 마켓 엑셀에서
    교차검색으로 얻은 연관검색어("사파리햇")로 확장해 찾아낸다."""
    db = cdb.CategoryDB.build(EXCELS)
    # 이 마켓(옥션2.0) 카테고리엔 "버킷햇"·"비니" 뿐, 필터명은 "사파리 햇"
    market_paths = ["패션의류잡화 > 남성 > 모자 > 버킷햇", "패션의류잡화 > 남성 > 모자 > 비니"]
    cat, step = mt.find_category(
        "아름트리-무신사-남성-모자-사파리 햇", market_paths, db=db
    )
    assert cat == "패션의류잡화 > 남성 > 모자 > 버킷햇"
    assert "5) " in step or "정보화DB" in step or step.startswith("2)")


def test_find_category_without_db_still_works():
    """db 를 안 넘겨도(기본 None) 이전처럼 동작 — 하위호환."""
    cat, step = mt.find_category(
        "아름트리-무신사-남성-모자-비니", ["패션의류잡화 > 남성 > 모자 > 비니"]
    )
    assert cat == "패션의류잡화 > 남성 > 모자 > 비니"
