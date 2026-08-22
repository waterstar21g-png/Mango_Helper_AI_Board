"""P3_설정수정_카테고리매핑초기화 단위테스트 — 브라우저 없이 검증."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import reset_category_mapping as rfs  # noqa: E402
import map_categories as mc  # noqa: E402

LIST_URL = "https://tmg1898.cafe24.com/mall/admin/admin_group.php?pmode=filter"


# ── 선택자 · 상수 ────────────────────────────────────────────────


def test_default_list_url_reused_from_p5_101():
    assert rfs.DEFAULT_LIST_URL == mc.DEFAULT_LIST_URL


def test_delete_selectors_match_screenshot_dom():
    """<a onclick="config_remove('','Y')" ...><span>검색필터 설정삭제</span></a>"""
    joined = " ".join(rfs.DELETE_SELECTORS)
    assert "config_remove" in joined
    assert "검색필터 설정삭제" in joined


def test_row_range_reused_from_p5_101():
    assert rfs.DEFAULT_ROW_FROM == mc.DEFAULT_ROW_FROM == 1
    assert rfs.DEFAULT_ROW_TO == mc.DEFAULT_ROW_TO == 5


# ── 팝업 삭제 클릭 ───────────────────────────────────────────────


class FakeButton:
    def __init__(self, present=True):
        self.present = present
        self.clicks = 0

    @property
    def first(self):
        return self

    def count(self):
        return 1 if self.present else 0

    def click(self, timeout=None):
        if not self.present:
            raise RuntimeError("없음")
        self.clicks += 1


class MissingLocator:
    @property
    def first(self):
        return self

    def count(self):
        return 0


class FakePopup:
    def __init__(self, has_button=True, closes=True):
        self.btn = FakeButton(present=has_button)
        self.closes = closes
        self.closed_flag = False
        self.dialog_handler = None
        self.evaluated: list[str] = []

    def on(self, event, handler):
        if event == "dialog":
            self.dialog_handler = handler

    def locator(self, selector):
        if "config_remove" in selector or "검색필터 설정삭제" in selector:
            return self.btn
        return MissingLocator()

    def evaluate(self, script, *args):
        self.evaluated.append(script)
        return None

    def is_closed(self):
        return self.closed_flag

    def close(self):
        self.closed_flag = True


def test_click_delete_setting_clicks_button():
    popup = FakePopup()
    logs: list[str] = []
    assert rfs.click_delete_setting(popup, progress=logs.append) is True
    assert popup.btn.clicks == 1
    assert any("설정삭제" in l for l in logs)


def test_click_delete_setting_falls_back_to_direct_call():
    popup = FakePopup(has_button=False)
    assert rfs.click_delete_setting(popup) is True
    assert any("config_remove" in s for s in popup.evaluated)


# ── 행 처리 (팝업 열기 → 삭제 → 닫기) ──────────────────────────────


class PopupHost:
    def __init__(self, popup):
        self.popup = popup

    def expect_popup(self, timeout=None):
        host = self

        class Ctx:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            @property
            def value(self):
                return host.popup

        return Ctx()

    def locator(self, selector):
        return FakeButton()


def test_delete_one_row_full_sequence():
    popup = FakePopup()
    row = mc.RowInfo(index=0, ftid="720", filter_name="아름트리-무신사-남성-모자-캡")
    logs: list[str] = []

    ok = rfs.reset_one_row(PopupHost(popup), row, list_url=rfs.DEFAULT_LIST_URL, progress=logs.append)

    assert ok is True
    assert popup.btn.clicks == 1
    assert popup.closed_flag is True
    assert popup.dialog_handler is not None
    assert any("팝업 닫기" in l for l in logs)


def test_delete_one_row_closes_popup_even_on_failure():
    popup = FakePopup(has_button=False)
    popup.evaluate = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no js"))
    row = mc.RowInfo(index=0, ftid="720", filter_name="f")
    ok = rfs.reset_one_row(PopupHost(popup), row, list_url=rfs.DEFAULT_LIST_URL)
    assert ok is False
    assert popup.closed_flag is True   # 실패해도 팝업은 닫는다


# ── 실행 인자 검증 ───────────────────────────────────────────────


def test_run_delete_requires_rows(monkeypatch):
    monkeypatch.setattr(mc, "list_rows", lambda page: [])
    monkeypatch.setattr(mc, "select_site", lambda *a, **k: True)
    monkeypatch.setattr(mc, "click_search_filter", lambda *a, **k: True)
    monkeypatch.setattr(mc, "diagnose_list", lambda *a, **k: None)

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

    result = rfs.run_reset(list_url=LIST_URL)
    assert result.ok is False
    assert "작업 대상 행이 없습니다" in result.errors[0]


def test_run_delete_processes_row_range(monkeypatch):
    seen: list[str] = []
    rows = [mc.RowInfo(index=i, ftid=str(700 + i), filter_name=f"f{i}") for i in range(10)]

    monkeypatch.setattr(mc, "list_rows", lambda page: rows)
    monkeypatch.setattr(mc, "select_site", lambda *a, **k: True)
    monkeypatch.setattr(mc, "click_search_filter", lambda *a, **k: True)
    monkeypatch.setattr(
        rfs,
        "reset_one_row",
        lambda page, row, **k: (seen.append(row.ftid), True)[1],
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

    result = rfs.run_reset(list_url=LIST_URL, row_from=2, row_to=4)
    assert seen == ["701", "702", "703"]
    assert result.rows == 3
    assert result.deleted == 3
    assert result.ok is True


def test_run_reset_requires_list_url():
    """★작업 URL 은 필수 — 기본값으로 엉뚱한 화면에서 초기화하면 되돌릴 수 없다."""
    result = rfs.run_reset(list_url="")
    assert result.ok is False
    assert "작업 URL 을 입력하세요" in result.errors[0]
    assert result.rows == 0
    assert result.deleted == 0
