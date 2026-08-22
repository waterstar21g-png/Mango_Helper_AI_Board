"""P5_101 단위테스트 — 매칭 로직·선택자·행 파싱을 브라우저 없이 검증."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import map_categories as mc  # noqa: E402

AUCTION = [
    "패션의류/잡화 > 남성패션 > 남성잡화 > 모자 > 비니",
    "패션의류/잡화 > 여성패션 > 여성잡화 > 모자 > 캡모자",
    "e쿠폰/모바일상품권 > 교육/어학이용권 > 온라인교육/외국어",
    "스포츠/레저 > 등산 > 등산모자",
]


# ── 매칭 로직 ────────────────────────────────────────────────────


def test_tokenize_splits_separators():
    assert mc.tokenize("남성패션 > 남성잡화_모자/비니") == [
        "남성패션",
        "남성잡화",
        "모자",
        "비니",
    ]


def test_leaf_of():
    assert mc.leaf_of("A > B > C") == "C"
    assert mc.leaf_of("단일") == "단일"
    assert mc.leaf_of("") == ""


def test_similarity_prefers_leaf_match():
    high = mc.similarity("남성 비니", "패션의류/잡화 > 남성패션 > 남성잡화 > 모자 > 비니")
    low = mc.similarity("남성 비니", "e쿠폰/모바일상품권 > 교육/어학이용권 > 온라인교육/외국어")
    assert high > low
    assert 0.0 <= low <= high <= 1.0


def test_best_category_picks_expected():
    cat, score = mc.best_category("남성 비니", AUCTION)
    assert cat.endswith("비니")
    assert score >= mc.MIN_SCORE


def test_best_category_always_returns_one():
    """★요건: 무관해 보여도 가장 가까운 카테고리 하나는 반드시 지정한다."""
    cat, score = mc.best_category("자동차 타이어 공기압 센서", AUCTION)
    assert cat in AUCTION
    assert score > 0


def test_search_keyword_is_leaf():
    assert mc.search_keyword_for("A > B > 비니") == "비니"


def test_pick_option_exact_then_leaf():
    options = [
        "패션잡화 > 모자 > 비니",
        "패션의류/잡화 > 남성패션 > 남성잡화 > 모자 > 비니",
    ]
    target = "패션의류/잡화 > 남성패션 > 남성잡화 > 모자 > 비니"
    assert mc.pick_option(options, target) == target          # 완전일치
    assert mc.pick_option(["잡화 > 모자 > 비니"], target).endswith("비니")  # 리프일치
    assert mc.pick_option([], target) == ""


# ── 검색 결과 선택의 성별 구분 ────────────────────────────────────


def test_pick_option_keeps_gender_on_leaf_match():
    """★여성 필터가 `남성신발 > 로퍼` 로 매칭되던 문제.

    검색어는 리프(`로퍼`)뿐이라 망고가 남성·여성을 함께 돌려주는데, 예전에는
    리프만 같으면 목록에 먼저 나온 남성 항목을 골랐다.
    """
    name = "아름트리-무신사-여성-신발-로퍼"
    target = "패션의류잡화 > 여성신발 > 로퍼"
    options = ["패션 > 남성신발 > 로퍼", "패션 > 여성신발 > 로퍼"]

    assert mc.pick_option(options, target, name) == "패션 > 여성신발 > 로퍼"
    # 필터명을 주지 않으면 예전 동작(리프 우선) 그대로 — 하위호환
    assert mc.pick_option(options, target) == "패션 > 남성신발 > 로퍼"


def test_pick_option_no_pick_when_only_opposite_gender():
    """반대 성별만 있으면 고르지 않는다 (오매핑보다 미매핑이 낫다)."""
    name = "아름트리-무신사-여성-신발-로퍼"
    target = "패션의류잡화 > 여성신발 > 로퍼"
    assert mc.pick_option(["패션 > 남성신발 > 로퍼"], target, name) == ""


def test_pick_option_allows_genderless_option():
    """성별 표기가 없는 항목은 남긴다 (마켓 대부분이 성별 없는 경로)."""
    name = "아름트리-무신사-여성-신발-로퍼"
    target = "패션의류잡화 > 여성신발 > 로퍼"
    assert mc.pick_option(["패션 > 신발 > 로퍼"], target, name) == "패션 > 신발 > 로퍼"


def test_gender_safe_options_prefers_same_gender():
    name = "아름트리-무신사-남성-신발-로퍼"
    options = ["여성신발 > 로퍼", "신발 > 로퍼", "남성신발 > 로퍼"]
    assert mc.gender_safe_options(options, name) == ["남성신발 > 로퍼"]
    # 성별을 알 수 없는 필터명이면 그대로 둔다
    assert mc.gender_safe_options(options, "브랜드-사이트-로퍼") == options


# ── 엑셀 로딩 ────────────────────────────────────────────────────


def _write_excel(path: Path, rows: list[list[str]], headers: list[str]) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    wb.save(str(path))


def test_load_categories_from_p5_format(tmp_path):
    path = tmp_path / "카테고리분류표_옥션2.0_20260822.xlsx"
    _write_excel(
        path,
        [
            ["옥션2.0", "", "패션의류/잡화", "남성패션", "", "", "", "", "패션의류/잡화 > 남성패션"],
            ["옥션2.0", "", "스포츠/레저", "등산", "", "", "", "", "스포츠/레저 > 등산"],
        ],
        ["마켓", "구분", "1단계", "2단계", "3단계", "4단계", "5단계", "6단계", "전체경로"],
    )
    cats = mc.load_categories(path)
    assert cats == ["패션의류/잡화 > 남성패션", "스포츠/레저 > 등산"]


def test_load_categories_falls_back_to_levels(tmp_path):
    path = tmp_path / "cat.xlsx"
    _write_excel(
        path,
        [["패션", "모자", "비니"], ["스포츠", "등산", ""]],
        ["1단계", "2단계", "3단계"],
    )
    assert mc.load_categories(path) == ["패션 > 모자 > 비니", "스포츠 > 등산"]


def test_market_from_filename():
    assert mc.market_from_filename("카테고리분류표_옥션2.0_20260822.xlsx") == "AUC20"
    assert mc.market_from_filename("11ST_categories.xlsx") == "11ST"
    assert mc.market_from_filename("무관한파일.xlsx") == ""


def test_discover_market_excels(tmp_path):
    for name in ("카테고리분류표_옥션2.0_1.xlsx", "카테고리분류표_쿠팡_1.xlsx", "기타.xlsx"):
        _write_excel(tmp_path / name, [["A"]], ["1단계"])
    found = mc.discover_market_excels(tmp_path)
    assert set(found) == {"AUC20", "COUP"}


def test_load_market_excels_reports(tmp_path):
    path = tmp_path / "카테고리분류표_쿠팡_1.xlsx"
    _write_excel(path, [["패션", "모자"]], ["1단계", "2단계"])
    logs: list[str] = []
    data = mc.load_market_excels({"COUP": path}, progress=logs.append)
    assert data["COUP"] == ["패션 > 모자"]
    assert any("쿠팡" in l for l in logs)


# ── 화면 선택자 (스크린샷 DOM) ────────────────────────────────────


def test_mapping_url_uses_category_set_page():
    url = mc.build_mapping_url("655")
    assert url.endswith("admin_category_set.php?tm=F&ps_ftid=655")
    assert "/mall/admin/" in url


def test_markets_are_six():
    assert list(mc.MARKETS) == ["AUC20", "11ST", "GMK20", "SMART", "COUP", "LTON"]


def test_screen_hooks_match_screenshots():
    assert mc.SEARCH_FILTER_JS == "search_filter('search')"
    assert mc.SETTING_EDIT_JS == "market_mapping_new"
    assert mc.AI_MAPPING_JS == "search_recommend_category_all"
    assert mc.CONFIG_SAVE_JS == "config_save"


class FakeLoc:
    def __init__(self, page, name, present=True):
        self.page = page
        self.name = name
        self.present = present

    @property
    def first(self):
        return self

    def count(self):
        return 1 if self.present else 0

    def click(self, timeout=None):
        self.page.actions.append(("click", self.name))

    def fill(self, value, timeout=None):
        self.page.actions.append(("fill", self.name, value))

    def select_option(self, value=None, *, label=None, timeout=None):
        self.page.actions.append(("select", self.name, label or value))


class FakePopup:
    def __init__(self, options):
        self.options = list(options)
        self.actions: list[tuple] = []
        self.asked_ids = None

    def locator(self, selector):
        for code in mc.MARKETS:
            if f"search_text_{code}" in selector:
                return FakeLoc(self, f"input_{code}")
            if f"search_list_{code}" in selector and selector.startswith("#"):
                return FakeLoc(self, f"list_{code}")
            if f"search_category('{code}'" in selector:
                return FakeLoc(self, f"searchbtn_{code}")
        if "config_save" in selector:
            return FakeLoc(self, "save")
        if "search_recommend_category_all" in selector:
            return FakeLoc(self, "ai")
        return FakeLoc(self, "none", present=False)

    def evaluate(self, script, *args):
        self.asked_ids = args[0] if args else None
        return {"texts": self.options, "id": "openmarket_category_search_list_AUC20"}

    def wait_for_timeout(self, ms):
        return None


def test_map_one_market_full_sequence():
    target = "패션의류/잡화 > 남성패션 > 남성잡화 > 모자 > 비니"
    popup = FakePopup([target, "패션 > 모자 > 캡모자"])
    logs: list[str] = []

    item = mc.map_one_market(popup, "AUC20", "남성 비니", AUCTION, progress=logs.append)

    assert item.ok is True
    assert item.category == target
    kinds = [a[0] for a in popup.actions]
    assert kinds == ["fill", "click", "select"]      # 입력 → 검색 → 선택
    assert popup.actions[0][2] == "비니"              # 검색어 = 리프
    assert popup.actions[1][1] == "searchbtn_AUC20"
    assert popup.actions[2][2] == target


def test_map_one_market_without_excel_is_skipped():
    item = mc.map_one_market(FakePopup([]), "COUP", "남성 비니", [])
    assert item.ok is False
    assert "엑셀" in item.reason


def test_map_one_market_no_search_result(monkeypatch):
    monkeypatch.setattr(mc, "T_LIST", 200)
    popup = FakePopup([])
    item = mc.map_one_market(popup, "AUC20", "남성 비니", AUCTION, retries=1)
    assert item.ok is False
    assert item.reason == "검색 결과 없음"


def test_map_retries_three_times_with_other_categories(monkeypatch):
    """★요건: 실패하면 다른 카테고리로 최대 3회 추가 시도."""
    monkeypatch.setattr(mc, "T_LIST", 100)
    tried: list[str] = []

    def fake_once(popup, market, name, cats, *, variant="", exclude=(), progress=None):
        cat, _ = mc.best_category_with_step(name, cats, exclude=exclude)
        tried.append(cat)
        return mc.MappedItem(market, cat, 1.0, False, "목록 선택 실패")

    monkeypatch.setattr(mc, "_map_once", fake_once)
    item = mc.map_one_market(FakePopup([]), "AUC20", "남성 비니", AUCTION)
    assert item.ok is False
    assert len(tried) == mc.MAP_RETRIES == 3
    assert len(set(tried)) == 3   # 매번 다른 카테고리


# ── 목록 행 파싱 ─────────────────────────────────────────────────


class RowsPage:
    def __init__(self, rows):
        self.rows = rows
        self.frames = [self]

    def evaluate(self, script, *args):
        if "location.href" in script:
            return {"url": "u", "table": True, "rows": 3, "checkboxes": 0,
                    "mappingLinks": len(self.rows), "sample": []}
        return self.rows


def test_list_rows_parses_checked_and_ftid():
    page = RowsPage(
        [
            {"index": 3, "ftid": "721", "filterName": "남성 비니", "checked": True},
            {"index": 4, "ftid": "722", "filterName": "여성 캡모자", "checked": False},
        ]
    )
    rows = mc.list_rows(page)
    assert [r.ftid for r in rows] == ["721", "722"]
    assert rows[0].checked is True and rows[1].checked is False
    assert rows[0].filter_name == "남성 비니"


def test_list_rows_js_reads_market_mapping_new():
    assert "market_mapping_new" in mc.LIST_ROWS_JS
    assert "checkbox" in mc.LIST_ROWS_JS


def test_list_rows_js_does_not_depend_on_table_id():
    """표 구조가 달라도 [설정수정] 링크로 행을 찾는다 (진단: 링크 15개인데 0행 문제)."""
    assert "table#search_category" not in mc.LIST_ROWS_JS
    assert "closest('tr')" in mc.LIST_ROWS_JS
    assert "attr-uid" in mc.LIST_ROWS_JS   # 이름 폴백


class MultiFramePage:
    """같은 행이 두 프레임에 중복 노출되는 화면."""

    def __init__(self):
        rows = [
            {"index": 0, "ftid": "720", "filterName": "아름트리-무신사-남성-모자-캡", "checked": False},
            {"index": 1, "ftid": "731", "filterName": "아름트리-무신사-남성-모자-비니", "checked": True},
        ]
        self.inner = RowsPage(rows + [{"index": 2, "ftid": "719", "filterName": "f", "checked": False}])
        self.rows = rows
        self.frames = [self, self.inner]

    def evaluate(self, script, *args):
        if "location.href" in script:
            return {"url": "u", "table": True, "rows": 35, "checkboxes": 18,
                    "mappingLinks": 15, "sample": []}
        return self.rows


def test_list_rows_merges_frames_without_duplicates():
    rows = mc.list_rows(MultiFramePage())
    assert [r.ftid for r in rows] == ["720", "731", "719"]   # 중복 제거 + 프레임 병합


# ── 드라이런 ─────────────────────────────────────────────────────


def test_run_dry_reports_per_market():
    logs: list[str] = []
    out = mc.run_dry(["남성 비니"], {"AUC20": AUCTION}, progress=logs.append)
    assert out[0]["filter"] == "남성 비니"
    assert out[0]["items"][0]["market"] == "AUC20"
    assert out[0]["items"][0]["category"].endswith("비니")
    assert any("옥션2.0" in l for l in logs)


def test_market_input_ids_match_screenshots():
    """스크린샷 1~6: 마켓별 카테고리 검색 입력필드 id."""
    expect = {
        "AUC20": "openmarket_category_search_text_AUC20",
        "GMK20": "openmarket_category_search_text_GMK20",
        "SMART": "openmarket_category_search_text_SMART",
        "COUP": "openmarket_category_search_text_COUP",
        "LTON": "openmarket_category_search_text_LTON",
        "11ST": "openmarket_category_search_text_11ST",
    }
    for code, expected_id in expect.items():
        popup = FakePopup([])
        loc = mc.market_search_input(popup, code)
        assert loc is not None and loc.name == f"input_{code}"
        assert expected_id == f"openmarket_category_search_text_{code}"


def test_market_search_button_selector_per_market():
    for code in mc.MARKETS:
        popup = FakePopup([])
        assert mc.click_market_search(popup, code) is True
        assert popup.actions[-1] == ("click", f"searchbtn_{code}")


def test_result_select_ids_cover_both_variants():
    """11번가·롯데ON 은 결과 리스트박스도 list_/list2_ 두 벌 (스크린샷 2·6)."""
    assert mc.result_select_ids("11ST") == [
        "openmarket_category_search_list_11ST",
        "openmarket_category_search_list2_11ST",
    ]
    assert mc.result_select_ids("LTON")[1].endswith("list2_LTON")


def test_read_result_options_asks_both_ids_and_prefers_visible():
    popup = FakePopup(["A > B"])
    options, select_id = mc.read_result_options(popup, "LTON")
    assert options == ["A > B"]
    assert popup.asked_ids == mc.result_select_ids("LTON")
    assert select_id  # 사용한 select id 반환
    js = mc.RESULT_OPTIONS_JS
    assert "getComputedStyle" in js and "offsetParent" in js


# ── 작업 한정·범위 (요건 2026-08-22 14:46) ────────────────────────


def test_only_musinsa_is_allowed():
    assert mc.ALLOWED_SITES == ("musinsa.com",)
    assert mc.DEFAULT_SITE == "MUSINSA.com"
    assert mc.is_allowed_site("MUSINSA.com") is True
    assert mc.is_allowed_site("www.musinsa.com") is True
    assert mc.is_allowed_site("ABCmart.a-rt.com") is False
    assert mc.is_allowed_site("") is False


def test_run_rejects_other_sites():
    logs: list[str] = []
    result = mc.run_mapping(
        site_id="Zara.com/de",
        excels={"AUC20": AUCTION},
        progress=logs.append,
    )
    assert result.ok is False
    assert "musinsa.com" in result.errors[0]
    assert any("제한" in l for l in logs)


def test_row_range_applies(monkeypatch):
    """체크 여부와 무관하게 [부터]~[까지] 범위만 처리한다."""
    seen: list[str] = []
    rows = [
        mc.RowInfo(index=i, ftid=str(700 + i), filter_name=f"f{i}", checked=(i % 2 == 0))
        for i in range(10)
    ]

    monkeypatch.setattr(mc, "list_rows", lambda page: rows)
    monkeypatch.setattr(mc, "select_site", lambda *a, **k: True)
    monkeypatch.setattr(mc, "click_search_filter", lambda *a, **k: True)

    def fake_map_one_row(page, row, excels, **kwargs):
        seen.append(row.ftid)
        return {"ftid": row.ftid, "filter": row.filter_name, "items": [{"ok": True}]}

    monkeypatch.setattr(mc, "map_one_row", fake_map_one_row)

    class FakeP2:
        @staticmethod
        def connect_browser(pw):
            return None, FakeBrowserPage()

    class FakeBrowserPage:
        def goto(self, *a, **k):
            return None

    class FakePW:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setitem(sys.modules, "collect", FakeP2)
    monkeypatch.setitem(
        sys.modules,
        "playwright.sync_api",
        type("M", (), {"sync_playwright": lambda: FakePW()}),
    )

    result = mc.run_mapping(
        site_id="MUSINSA.com", excels={"AUC20": AUCTION}, row_from=2, row_to=4
    )
    assert seen == ["701", "702", "703"]   # 2~4행 (1부터, 양끝 포함)
    assert result.rows == 3


def test_invalid_row_range_falls_back_to_default(monkeypatch):
    monkeypatch.setattr(mc, "list_rows", lambda page: [])
    monkeypatch.setattr(mc, "select_site", lambda *a, **k: True)
    monkeypatch.setattr(mc, "click_search_filter", lambda *a, **k: True)

    class FakeP2:
        @staticmethod
        def connect_browser(pw):
            return None, type("P", (), {"goto": lambda self, *a, **k: None})()

    class FakePW:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setitem(sys.modules, "collect", FakeP2)
    monkeypatch.setitem(
        sys.modules,
        "playwright.sync_api",
        type("M", (), {"sync_playwright": lambda: FakePW()}),
    )

    result = mc.run_mapping(
        site_id="MUSINSA.com", excels={"AUC20": AUCTION}, row_from=0, row_to=-2
    )
    assert "작업 대상 행이 없습니다" in result.errors[0]  # 기본값(1~5)으로 진행하다 행 없음


# ── 작업 범위 · 수집사이트 제한 (요건 2026-08-22 14:46/14:49) ─────


def test_site_restricted_to_musinsa():
    assert mc.ALLOWED_SITES == ("musinsa.com",)
    assert mc.DEFAULT_SITE == "MUSINSA.com"
    assert mc.is_allowed_site("MUSINSA.com") is True
    assert mc.is_allowed_site("musinsa.com") is True
    assert mc.is_allowed_site("ABCmart.a-rt.com") is False
    assert mc.is_allowed_site("") is False


def test_run_mapping_blocks_other_sites():
    result = mc.run_mapping(site_id="ABCmart.a-rt.com", excels={"AUC20": ["A > B"]})
    assert result.ok is False
    assert "musinsa.com" in result.errors[0]


def test_row_range_defaults_and_normalization():
    assert (mc.DEFAULT_ROW_FROM, mc.DEFAULT_ROW_TO) == (1, 5)
    assert mc.row_range() == (1, 5)
    assert mc.row_range("3", "7") == (3, 7)
    assert mc.row_range(9, 2) == (2, 9)      # 뒤집혀 있으면 바로잡는다
    assert mc.row_range("", "") == (1, 5)
    assert mc.row_range(0, -3) == (1, 5)


def test_slice_rows_is_inclusive_and_one_based():
    rows = list("ABCDEFG")
    assert mc.slice_rows(rows, 1, 5) == list("ABCDE")
    assert mc.slice_rows(rows, 2, 4) == list("BCD")
    assert mc.slice_rows(rows, 6, 99) == list("FG")
    assert mc.slice_rows(rows, 10, 12) == []


def test_unchecked_rows_are_processed(monkeypatch):
    """체크가 하나도 없어도 범위 안의 행을 처리한다 (요건 2026-08-22 15:03)."""
    seen: list[str] = []
    rows = [
        mc.RowInfo(index=i, ftid=str(800 + i), filter_name=f"g{i}", checked=False)
        for i in range(4)
    ]
    monkeypatch.setattr(mc, "list_rows", lambda page: rows)
    monkeypatch.setattr(mc, "select_site", lambda *a, **k: True)
    monkeypatch.setattr(mc, "click_search_filter", lambda *a, **k: True)
    monkeypatch.setattr(
        mc,
        "map_one_row",
        lambda page, row, excels, **k: seen.append(row.ftid)
        or {"ftid": row.ftid, "items": [{"ok": True}]},
    )

    class FakeP2:
        @staticmethod
        def connect_browser(pw):
            return None, type("P", (), {"goto": lambda self, *a, **k: None})()

    class FakePW:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setitem(sys.modules, "collect", FakeP2)
    monkeypatch.setitem(
        sys.modules, "playwright.sync_api", type("M", (), {"sync_playwright": lambda: FakePW()})
    )

    result = mc.run_mapping(
        site_id="MUSINSA.com", excels={"AUC20": AUCTION}, row_from=1, row_to=2
    )
    assert seen == ["800", "801"]
    assert result.rows == 2


class FramedRowsPage:
    """목록이 하위 프레임에 있는 화면."""

    def __init__(self, rows):
        self.inner = RowsPage(rows)
        self.frames = [self, self.inner]

    def evaluate(self, script, *args):
        if "location.href" in script:
            return {"url": "outer", "table": False, "rows": 0, "checkboxes": 0,
                    "mappingLinks": 0, "sample": []}
        return []


def test_list_rows_searches_frames():
    page = FramedRowsPage([{"index": 0, "ftid": "900", "filterName": "f", "checked": False}])
    rows = mc.list_rows(page)
    assert [r.ftid for r in rows] == ["900"]


def test_diagnose_list_logs_counts():
    page = RowsPage([{"index": 0, "ftid": "900", "filterName": "f", "checked": False}])
    logs: list[str] = []
    mc.diagnose_list(page, progress=logs.append)
    assert any("설정수정링크" in l for l in logs)


# ── 구분 라디오 · 상품고시정보 팝업 (요건 2026-08-22 15:20) ────────


def test_market_variants_defined():
    assert mc.MARKET_VARIANTS["11ST"] == ("해외카테고리", "국내카테고리")
    assert mc.MARKET_VARIANTS["LTON"] == ("해외직구 카테고리", "일반카테고리")


def test_variants_for_choice():
    assert mc.variants_for("11ST") == ["해외카테고리", "국내카테고리"]        # 기본 둘 다
    assert mc.variants_for("11ST", "국내카테고리") == ["국내카테고리"]
    assert mc.variants_for("LTON", mc.BOTH) == ["해외직구 카테고리", "일반카테고리"]
    assert mc.variants_for("AUC20") == [""]                                   # 구분 없음
    assert mc.variants_for("11ST", "없는값") == ["해외카테고리", "국내카테고리"]


def test_variant_radio_selector_matches_screenshot():
    joined = " ".join(mc.variant_radio_selectors("LTON", "해외직구 카테고리"))
    assert "openmarket_seller_type2_LTON" in joined
    assert "해외직구 카테고리" in joined
    assert "mapping_category_LTON" in joined


class VariantPopup(FakePopup):
    """구분 라디오와 상품고시정보 팝업이 있는 화면."""

    def __init__(self, options, notify_times=0):
        super().__init__(options)
        self.notify_times = notify_times
        self.checked: list[str] = []
        self.closed = 0

    def locator(self, selector):
        for variant in ("해외카테고리", "국내카테고리", "해외직구 카테고리", "일반카테고리"):
            if variant in selector and "radio" in selector:
                return _VariantRadio(self, variant)
        if "mapping_notify" in selector:
            return _NotifyClose(self)
        return super().locator(selector)

    def evaluate(self, script, *args):
        if "innerText" in script:            # notify_open
            if self.notify_times > 0:
                self.notify_times -= 1
                return True
            return False
        if "style.display" in script:        # close_notify 강제 숨김
            return None
        return super().evaluate(script, *args)

    def wait_for_timeout(self, ms):
        return None


class _VariantRadio:
    def __init__(self, popup, variant):
        self.popup = popup
        self.variant = variant

    @property
    def first(self):
        return self

    def count(self):
        return 1

    def click(self, timeout=None, force=False):
        self.popup.checked.append(self.variant)

    def check(self, timeout=None):
        self.popup.checked.append(self.variant)


class _NotifyClose:
    def __init__(self, popup):
        self.popup = popup

    @property
    def first(self):
        return self

    def count(self):
        return 1

    def click(self, timeout=None):
        self.popup.closed += 1


def test_map_one_market_selects_variant_first():
    popup = VariantPopup(["패션의류잡화 > 남성 > 모자 > 버킷햇"])
    item = mc.map_one_market(
        popup,
        "LTON",
        "아름트리-무신사-남성-모자-버킷햇",
        ["패션의류잡화 > 남성 > 모자 > 버킷햇"],
        variant="해외직구 카테고리",
    )
    assert popup.checked == ["해외직구 카테고리"]
    assert item.ok is True


def test_notify_open_and_close():
    popup = VariantPopup([], notify_times=1)
    assert mc.notify_open(popup, "LTON") is True     # 한 번 떠 있음
    assert mc.notify_open(popup, "LTON") is False    # 그 뒤 닫힘
    assert mc.close_notify(popup, "LTON") is True
    assert popup.closed == 1


def test_exclude_picks_next_category():
    """상품고시정보 팝업 후 재매핑 — 직전 카테고리는 제외하고 고른다."""
    cats = [
        "패션의류잡화 > 남성 > 모자 > 버킷햇",
        "패션의류잡화 > 남성 > 모자 > 캡모자",
    ]
    first, _ = mc.best_category_with_step("아름트리-무신사-남성-모자-버킷햇", cats)
    second, _ = mc.best_category_with_step(
        "아름트리-무신사-남성-모자-버킷햇", cats, exclude=[first]
    )
    assert first == "패션의류잡화 > 남성 > 모자 > 버킷햇"
    assert second == "패션의류잡화 > 남성 > 모자 > 캡모자"


# ── 저장 후 재검증 · 미매핑 재시도 (요건 2026-08-22 15:33) ─────────


class StatePopup:
    """마켓별 매핑 상태(hidden 값)를 돌려주는 팝업."""

    def __init__(self, state):
        self.state = dict(state)

    def evaluate(self, script, *args):
        if "openmarket_cm_category_" in script:
            codes = args[0] if args else []
            return {c: self.state.get(c, {"code": "", "name": ""}) for c in codes}
        return None


def test_mapped_state_and_unmapped_detection():
    popup = StatePopup(
        {
            "AUC20": {"code": "123", "name": "패션 > 모자"},
            "COUP": {"code": "", "name": ""},
            "LTON": {"code": "", "name": "롯데 > 모자"},   # 이름만 있어도 매핑으로 본다
        }
    )
    codes = ["AUC20", "COUP", "LTON"]
    assert mc.mapped_state(popup, codes)["AUC20"]["code"] == "123"
    assert mc.unmapped_markets(popup, codes) == ["COUP"]


def test_unmapped_markets_empty_when_state_unavailable():
    class Broken:
        def evaluate(self, *a, **k):
            raise RuntimeError("no")

    assert mc.unmapped_markets(Broken(), ["AUC20"]) == []


def test_verify_rounds_constant():
    assert mc.VERIFY_ROUNDS == 3
    assert mc.MAP_RETRIES == 3


def test_synonym_helps_nearest_pick():
    """AI 보조 — 바라클라바 ↔ 방한모 같은 표현 차이를 메운다."""
    cats = ["패션잡화 > 남성 > 방한모", "생활 > 주방 > 컵"]
    cat, step = mc.best_category_with_step("아름트리-무신사-남성-모자-바라클라바", cats)
    assert cat == "패션잡화 > 남성 > 방한모"   # 바라클라바 ↔ 방한모 동의어
    assert step.startswith(("2-2) 하위", "3) 최근접"))


def test_mapped_category_is_within_excel(monkeypatch):
    """map_one_market 이 고른 최적 카테고리는 엑셀 목록 안의 값이다."""
    target = "패션의류잡화 > 남성 > 남성잡화 > 모자 > 비니"
    excel = [target, "패션의류잡화 > 여성 > 모자 > 캡모자"]
    popup = FakePopup([target, "다른 > 사이트 > 항목"])
    item = mc.map_one_market(popup, "AUC20", "아름트리-무신사-남성-모자-비니", excel)
    assert item.ok is True
    assert item.category in excel or item.category == target


def test_out_of_range_category_is_corrected(monkeypatch):
    """혹시 목록 밖 값이 나오면 엑셀 안 값으로 교정한다."""
    excel = ["패션의류잡화 > 남성 > 모자 > 비니"]
    monkeypatch.setattr(
        mc, "best_category_with_step", lambda *a, **k: ("지어낸 > 카테고리", "테스트")
    )
    logs: list[str] = []
    popup = FakePopup(["패션의류잡화 > 남성 > 모자 > 비니"])
    item = mc._map_once(
        popup, "AUC20", "아름트리-무신사-남성-모자-비니", excel, progress=logs.append
    )
    assert item.category in excel
    assert any("엑셀 범위 밖" in l for l in logs)


def test_map_one_market_blocks_opposite_gender(monkeypatch):
    """최적 선정이 반대 성별을 내놓으면 배제하고 다시 고른다."""
    excel = ["남성패션 > 모자 > 비니", "여성패션 > 모자 > 비니"]
    calls = {"n": 0}

    def fake_best(name, cats, *, exclude=()):
        calls["n"] += 1
        if calls["n"] == 1:
            return "남성패션 > 모자 > 비니", "테스트"      # 규칙 위반 값
        return (list(cats)[0], "재선정")

    monkeypatch.setattr(mc, "best_category_with_step", fake_best)
    logs: list[str] = []
    popup = FakePopup(["여성패션 > 모자 > 비니"])
    item = mc._map_once(
        popup, "AUC20", "아름트리-무신사-여성-모자-비니", excel, progress=logs.append
    )
    assert "남성" not in item.category
    assert any("반대 성별" in l for l in logs)


# ── 몇 번째 행인지 확인 (요건 2026-08-22 16:50) ────────────────────


def test_format_row_list_numbers_from_one():
    rows = [
        mc.RowInfo(index=0, ftid="720", filter_name="아름트리-무신사-남성-모자-캡"),
        mc.RowInfo(index=1, ftid="782", filter_name="아름트리-무신사-여성-신발-샌들/슬리퍼"),
    ]
    lines = mc.format_row_list(rows)
    assert lines[0].startswith("    1행: ftid=720")
    assert "782" in lines[1] and "샌들/슬리퍼" in lines[1]


def test_format_row_list_marks_selected_range():
    rows = [mc.RowInfo(index=i, ftid=str(700 + i), filter_name=f"f{i}") for i in range(15)]
    lines = mc.format_row_list(rows, row_from=11, row_to=11)
    assert lines[10].startswith("★ 11행")
    assert not lines[9].startswith("★")   # 범위 밖은 표시 없음
    assert "10행" in lines[9]


def test_screenshot_row_11_is_ftid_782():
    """스크린샷: attr-uid=782, 필터=아름트리-무신사-여성-신발-샌들/슬리퍼 가 11행."""
    rows = [
        mc.RowInfo(index=i, ftid=str(770 + i), filter_name=f"f{i}") for i in range(10)
    ] + [mc.RowInfo(index=10, ftid="782", filter_name="아름트리-무신사-여성-신발-샌들/슬리퍼")]
    lines = mc.format_row_list(rows, row_from=11, row_to=11)
    assert "★ 11행: ftid=782" in lines[10]


# ── 상품수집사이트 선택 (대소문자·공백 차이 허용) ──────────────────


SITE_OPTIONS = ["-- 수집사이트 --", "4910.kr", "ABCmart.a-rt.com", "MUSINSA.com", "Zara.com/de"]


def test_match_site_option_is_case_insensitive():
    """★`MUSINSA.COM` 입력이 `MUSINSA.com` 옵션을 못 찾아 선택 실패하던 문제."""
    assert mc.match_site_option(SITE_OPTIONS, "MUSINSA.COM") == "MUSINSA.com"
    assert mc.match_site_option(SITE_OPTIONS, "musinsa.com") == "MUSINSA.com"
    assert mc.match_site_option(SITE_OPTIONS, "MUSINSA.com") == "MUSINSA.com"


def test_match_site_option_ignores_spaces_and_allows_partial():
    assert mc.match_site_option(SITE_OPTIONS, " MUSINSA . com ") == "MUSINSA.com"
    assert mc.match_site_option(SITE_OPTIONS, "musinsa") == "MUSINSA.com"
    assert mc.match_site_option(SITE_OPTIONS, "abcmart.A-RT.com") == "ABCmart.a-rt.com"


def test_match_site_option_returns_none_when_absent():
    assert mc.match_site_option(SITE_OPTIONS, "coupang.com") is None
    assert mc.match_site_option(SITE_OPTIONS, "") is None
    assert mc.match_site_option([], "MUSINSA.com") is None


# ── 목록 URL 은 필수 (요건: URL 로 화면을 띄우고 리스트업) ─────────


def test_list_rows_only_requires_url():
    """빈 URL 로 DEFAULT_LIST_URL 에 몰래 떨어지지 않는다 — 명시 실패로 안내."""
    rows = mc.list_rows_only(list_url="")
    assert rows == []


def test_reveal_brings_page_to_front():
    calls = []

    class FakePage:
        def bring_to_front(self):
            calls.append(True)

    mc.reveal(FakePage())
    assert calls == [True]


def test_reveal_does_not_raise_on_failure():
    class FailingPage:
        def bring_to_front(self):
            raise RuntimeError("창 없음")

    mc.reveal(FailingPage())  # 예외 없이 넘어가야 한다
