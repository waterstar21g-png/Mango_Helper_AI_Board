"""외부 제공 CATEGORY_MASTER + KEYWORD_DICTIONARY CSV 기반 DB 테스트.

요건(2026-08-23): "기존 DB를 대체하여 지금 주는 걸 활용하는 프로그램을
구현해. DB는 CSV 자료 그대로 DB화하고 GitHub에 올려서 메모리로 보관해
속도를 높이도록 해."
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import category_master_db as cmdb  # noqa: E402


def _write_category_csv(path: Path, rows: list[list[str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Market", "Cat_ID", "Cat_Name", "Parent_ID", "Level", "Full_Path"])
        w.writerows(rows)


def _write_keyword_csv(path: Path, rows: list[list[str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["Keyword_ID", "Search_Keyword", "Target_Cat_ID", "Mapping_Type", "Priority", "Market", "Mapping_Result"]
        )
        w.writerows(rows)


SAMPLE_CATEGORIES = [
    ["쿠팡", "C0001", "패션잡화", "ROOT", "1", "패션잡화"],
    ["쿠팡", "C0002", "남성 모자", "C0001", "2", "패션잡화 > 남성 모자"],
    ["쿠팡", "C0003", "비니", "C0002", "3", "패션잡화 > 남성 모자 > 비니"],
    ["쿠팡", "C0004", "야구모자", "C0002", "3", "패션잡화 > 남성 모자 > 야구모자"],
    ["옥션2.0", "C0005", "잡화", "ROOT", "1", "잡화"],
    ["옥션2.0", "C0006", "모자", "C0005", "2", "잡화 > 모자"],
    ["옥션2.0", "C0007", "비니", "C0006", "3", "잡화 > 모자 > 비니"],
]

SAMPLE_KEYWORDS = [
    ["K0001", "비니", "C0003", "EX(완전일치)", "1", "쿠팡", "패션잡화 > 남성 모자 > 비니"],
    ["K0002", "야구모자", "C0004", "EX(완전일치)", "1", "쿠팡", "패션잡화 > 남성 모자 > 야구모자"],
    ["K0003", "캡모자", "C0004", "SY(유의어분리)", "2", "쿠팡", "패션잡화 > 남성 모자 > 야구모자"],
    ["K0004", "모자", "C0004", "MO(형태소분리)", "3", "쿠팡", "패션잡화 > 남성 모자 > 야구모자"],
    ["K0005", "비니", "C0007", "EX(완전일치)", "1", "옥션2.0", "잡화 > 모자 > 비니"],
]


def _build_sample_db(tmp_path: Path) -> cmdb.MasterDB:
    cat_csv = tmp_path / "category_master.csv"
    kw_csv = tmp_path / "keyword_dictionary.csv"
    _write_category_csv(cat_csv, SAMPLE_CATEGORIES)
    _write_keyword_csv(kw_csv, SAMPLE_KEYWORDS)
    return cmdb.MasterDB.from_csv(cat_csv, kw_csv)


def test_from_csv_loads_categories_and_keywords():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        db = _build_sample_db(Path(d))
    assert len(db.categories) == 7
    assert len(db.keywords) == 5


def test_categories_keep_given_cat_id_and_market():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        db = _build_sample_db(Path(d))
    node = db.categories["C0003"]
    assert node.cat_name == "비니"
    assert node.market == "쿠팡"
    assert node.full_path == "패션잡화 > 남성 모자 > 비니"


def test_is_leaf_and_children_of():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        db = _build_sample_db(Path(d))
    assert db.is_leaf("C0001") is False
    assert db.is_leaf("C0003") is True
    children = db.children_of("C0002")
    assert {c.cat_id for c in children} == {"C0003", "C0004"}


def test_siblings_of_and_ancestors_of():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        db = _build_sample_db(Path(d))
    sibs = db.siblings_of("C0003")
    assert [s.cat_id for s in sibs] == ["C0004"]
    ancestors = [a.cat_id for a in db.ancestors_of("C0003")]
    assert ancestors == ["C0002", "C0001"]


def test_market_leaf_paths_scoped_per_market():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        db = _build_sample_db(Path(d))
    coupang_leaves = db.market_leaf_paths("쿠팡")
    assert set(coupang_leaves) == {"패션잡화 > 남성 모자 > 비니", "패션잡화 > 남성 모자 > 야구모자"}
    auction_leaves = db.market_leaf_paths("옥션2.0")
    assert auction_leaves == ["잡화 > 모자 > 비니"]


def test_excels_dict_matches_map_categories_shape():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        db = _build_sample_db(Path(d))
    excels = db.excels_dict({"COUP": "쿠팡", "AUC20": "옥션2.0"})
    assert set(excels.keys()) == {"COUP", "AUC20"}
    assert "패션잡화 > 남성 모자 > 비니" in excels["COUP"]


# ── resolve() 4단계 ────────────────────────────────────────────────


def test_resolve_exact_match_ex():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        db = _build_sample_db(Path(d))
    cid, step = db.resolve("쿠팡", "비니")
    assert db.full_path(cid) == "패션잡화 > 남성 모자 > 비니"
    assert step.startswith("1)")


def test_resolve_synonym_sy():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        db = _build_sample_db(Path(d))
    cid, step = db.resolve("쿠팡", "캡모자")
    assert db.full_path(cid) == "패션잡화 > 남성 모자 > 야구모자"
    assert step.startswith("2)")


def test_resolve_morpheme_mo():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        db = _build_sample_db(Path(d))
    cid, step = db.resolve("쿠팡", "모자")
    assert db.full_path(cid) == "패션잡화 > 남성 모자 > 야구모자"
    assert step.startswith("3)")


def test_resolve_is_scoped_per_market():
    """같은 검색어라도 마켓이 다르면 그 마켓 카테고리로 확정돼야 한다."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        db = _build_sample_db(Path(d))
    cid_coupang, _ = db.resolve("쿠팡", "비니")
    cid_auction, _ = db.resolve("옥션2.0", "비니")
    assert db.full_path(cid_coupang) == "패션잡화 > 남성 모자 > 비니"
    assert db.full_path(cid_auction) == "잡화 > 모자 > 비니"
    assert cid_coupang != cid_auction


def test_resolve_forces_a_pick_when_keyword_missing_but_market_has_data():
    """★요건(절대): 미검출로 끝내지 않는다 — 검색어가 전혀 없어도 그
    마켓에 카테고리가 있으면 가장 비슷한 것을 강제 지정한다."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        db = _build_sample_db(Path(d))
    cid, step = db.resolve("쿠팡", "존재하지않는검색어절대")
    assert cid is not None
    assert step.startswith("4)")


def test_resolve_reports_no_data_when_market_unknown():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        db = _build_sample_db(Path(d))
    cid, step = db.resolve("존재하지않는마켓", "비니")
    assert cid is None
    assert step == "카테고리 자료 없음"


def test_resolve_empty_keyword_still_forces_pick_when_market_has_data():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        db = _build_sample_db(Path(d))
    cid, step = db.resolve("쿠팡", "")
    assert cid is not None


# ── JSON 캐시 (요건: GitHub 에 올려서 메모리로 재사용) ───────────────


def test_save_json_and_load_json_roundtrip(tmp_path):
    db = _build_sample_db(tmp_path)
    cache_path = tmp_path / "cache.json"
    db.save_json(cache_path)
    assert cache_path.exists()

    loaded = cmdb.MasterDB.load_json(cache_path)
    assert loaded is not None
    assert len(loaded.categories) == len(db.categories)
    assert len(loaded.keywords) == len(db.keywords)
    cid, step = loaded.resolve("쿠팡", "비니")
    assert loaded.full_path(cid) == "패션잡화 > 남성 모자 > 비니"


def test_load_json_missing_file_returns_none(tmp_path):
    missing = tmp_path / "no_such_file.json"
    assert cmdb.MasterDB.load_json(missing) is None


def test_load_prefers_json_cache_when_present(tmp_path):
    db = _build_sample_db(tmp_path)
    cache_path = tmp_path / "cache.json"
    db.save_json(cache_path)

    # CSV 파일이 없어도(refresh=False) 캐시로 로드되어야 한다
    loaded = cmdb.MasterDB.load(
        category_csv=tmp_path / "no.csv",
        keyword_csv=tmp_path / "no2.csv",
        json_cache=cache_path,
        refresh=False,
    )
    assert len(loaded.categories) == len(db.categories)


def test_load_refresh_rebuilds_from_csv(tmp_path):
    db = _build_sample_db(tmp_path)
    cat_csv = tmp_path / "category_master.csv"
    kw_csv = tmp_path / "keyword_dictionary.csv"
    cache_path = tmp_path / "cache.json"
    db.save_json(cache_path)

    loaded = cmdb.MasterDB.load(
        category_csv=cat_csv, keyword_csv=kw_csv, json_cache=cache_path, refresh=True
    )
    assert len(loaded.categories) == len(db.categories)


# ── 실제 저장소 CSV/캐시 (있을 때만) ─────────────────────────────────


def test_repo_csv_files_are_valid_if_present():
    if not cmdb.DEFAULT_CATEGORY_CSV.exists():
        return
    db = cmdb.MasterDB.from_csv()
    assert len(db.categories) > 0
    assert len(db.keywords) > 0
    for market in ("쿠팡", "옥션2.0", "11번가", "G마켓2.0", "스마트스토어", "롯데ON"):
        assert market in db._by_market, f"{market} 마켓 데이터 없음"
