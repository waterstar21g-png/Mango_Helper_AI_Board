"""P3_설정수정_카테고리매핑초기화 단위테스트 — 브라우저 없이 검증."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import reset_category_mapping as rcm  # noqa: E402

LIST_URL = (
    "https://tmg1898.cafe24.com/mall/admin/admin_group.php"
    "?pmode=filter_delete&uids=&site_id=musinsa&ft_num=100"
)


# ── 요건 1: P3_수집조건수정 소스를 활용한다 ────────────────────────


def test_reuses_p3_collect_option_module():
    """접속·사이트선택·검색·팝업닫기는 잘 돌고 있는 P3_수집조건수정 것을 쓴다."""
    for name in (
        "_open_mango",
        "apply_site_filter",
        "pick_list_page",
        "close_popup",
        "contexts",
    ):
        assert hasattr(rcm.p3opt, name), f"P3_수집조건수정 에 {name} 이 없습니다."
    assert rcm.T_CLICK == rcm.p3opt.T_CLICK
    assert rcm.GAP_ROW == rcm.p3opt.GAP_ROW


# ── 선택자 (스크린샷 DOM 그대로) ──────────────────────────────────


def test_setting_edit_matches_screenshot_dom():
    """<a onclick="market_mapping_new('670');"><span>설정수정</span></a>"""
    assert rcm.SETTING_EDIT_JS == "market_mapping_new"
    assert rcm.SETTING_EDIT_LABEL == "설정수정"
    assert "market_mapping_new" in rcm.LIST_ROWS_JS


def test_delete_selectors_match_screenshot_dom():
    """<a onclick="config_remove('','Y')"><span>검색필터 설정삭제</span></a>"""
    joined = " ".join(rcm.DELETE_SELECTORS)
    assert "config_remove" in joined
    assert "검색필터 설정삭제" in joined


# ── 작업 URL ─────────────────────────────────────────────────────


class CountingContext:
    """count() 를 세는 가짜 프레임 — 없는 요소에서 클릭을 시도하는지 검증용."""

    def __init__(self, has_link: bool):
        self.has_link = has_link
        self.count_calls = 0
        self.click_calls = 0

    def locator(self, selector):
        return self

    @property
    def first(self):
        return self

    def count(self):
        self.count_calls += 1
        return 1 if self.has_link else 0

    def click(self, timeout=None):
        self.click_calls += 1
        if not self.has_link:
            raise AssertionError("링크가 없는 프레임에서 click() 을 호출했다")


def test_open_setting_popup_checks_count_before_click(monkeypatch):
    """★관계없는 프레임(광고 iframe 등)에서 헛클릭·헛대기를 하지 않는다.

    count() 로 존재를 먼저 확인하고, 없으면 즉시 다음 프레임으로 넘어가야 한다
    (클릭을 시도하며 없는 요소를 기다리면 프레임마다 수 초씩 낭비된다).
    """
    dead1 = CountingContext(has_link=False)
    dead2 = CountingContext(has_link=False)
    live = CountingContext(has_link=True)
    monkeypatch.setattr(rcm.p3opt, "contexts", lambda page: [dead1, dead2, live])

    class FakePopupInfo:
        value = "POPUP"

    class FakePage:
        def expect_popup(self, timeout=None):
            class Ctx:
                def __enter__(self):
                    return FakePopupInfo()

                def __exit__(self, *a):
                    return False

            return Ctx()

    popup = rcm.open_setting_popup(FakePage(), "670", list_url="https://x/list.php")
    assert popup == "POPUP"
    assert dead1.click_calls == 0     # 없는 프레임에서 클릭 시도 안 함
    assert dead2.click_calls == 0
    assert live.click_calls == 1
    assert dead1.count_calls >= 1     # 존재 확인은 했다 (대기 없이)


def test_build_popup_url_from_list_url():
    url = rcm.build_popup_url(LIST_URL, "670")
    assert url.startswith("https://tmg1898.cafe24.com/mall/admin/admin_category_set.php")
    assert "ps_ftid=670" in url
    assert "tm=F" in url


def test_run_reset_requires_list_url():
    """작업 URL 은 필수 — 되돌릴 수 없는 작업이라 기본값으로 돌리지 않는다."""
    result = rcm.run_reset(list_url="")
    assert result.ok is False
    assert "작업 URL 을 입력하세요" in result.errors[0]
    assert result.rows == 0
    assert result.reset_done == 0


# ── 작업행 범위 ──────────────────────────────────────────────────


def test_row_range_defaults_and_repair():
    assert rcm.row_range(1, 5) == (1, 5)
    assert rcm.row_range(4, 2) == (2, 4)           # 뒤집히면 바로잡는다
    assert rcm.row_range("", "") == (rcm.DEFAULT_ROW_FROM, rcm.DEFAULT_ROW_TO)
    assert rcm.row_range(0, -3) == (rcm.DEFAULT_ROW_FROM, rcm.DEFAULT_ROW_TO)


def test_slice_rows_is_one_based_inclusive():
    rows = [rcm.RowInfo(index=i, ftid=str(700 + i)) for i in range(10)]
    picked = rcm.slice_rows(rows, 2, 4)
    assert [r.ftid for r in picked] == ["701", "702", "703"]


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


class FakePopup:
    def __init__(self, has_button=True):
        self.button = FakeButton(has_button)
        self.evaluated: list[str] = []
        self.closed = False

    def locator(self, selector):
        return self.button

    def evaluate(self, script):
        self.evaluated.append(script)

    def on(self, event, handler):
        pass

    def wait_for_selector(self, selector, timeout=None):
        if not self.button.present:
            raise RuntimeError("없음")

    def is_closed(self):
        return self.closed

    def close(self):
        self.closed = True

    def wait_for_event(self, name, timeout=None):
        self.closed = True


def test_click_delete_setting_clicks_button():
    popup = FakePopup()
    assert rcm.click_delete_setting(popup) is True
    assert popup.button.clicks == 1
    assert popup.evaluated == []


def test_click_delete_setting_falls_back_to_config_remove():
    popup = FakePopup(has_button=False)
    assert rcm.click_delete_setting(popup) is True
    assert any("config_remove" in s for s in popup.evaluated)


# ── 한 행 흐름 ───────────────────────────────────────────────────


def test_reset_one_row_opens_deletes_and_closes(monkeypatch):
    popup = FakePopup()
    closed: list[bool] = []
    monkeypatch.setattr(rcm, "open_setting_popup", lambda *a, **k: popup)
    monkeypatch.setattr(
        rcm.p3opt, "close_popup", lambda p, **k: closed.append(True) or True
    )

    ok = rcm.reset_one_row(None, rcm.RowInfo(index=0, ftid="670", filter_name="f"))
    assert ok is True
    assert popup.button.clicks == 1
    assert closed == [True]


def test_reset_one_row_closes_popup_even_on_failure(monkeypatch):
    popup = FakePopup(has_button=False)
    closed: list[bool] = []
    monkeypatch.setattr(rcm, "open_setting_popup", lambda *a, **k: popup)
    monkeypatch.setattr(rcm, "click_delete_setting", lambda *a, **k: False)
    monkeypatch.setattr(
        rcm.p3opt, "close_popup", lambda p, **k: closed.append(True) or True
    )

    ok = rcm.reset_one_row(None, rcm.RowInfo(index=0, ftid="670"))
    assert ok is False
    assert closed == [True]          # 실패해도 팝업은 닫는다


def test_reset_one_row_reports_when_popup_missing(monkeypatch):
    monkeypatch.setattr(rcm, "open_setting_popup", lambda *a, **k: None)
    assert rcm.reset_one_row(None, rcm.RowInfo(index=0, ftid="670")) is False


# ── 중단 플래그 ──────────────────────────────────────────────────


def test_stop_flag_roundtrip():
    rcm.clear_stop_flag()
    assert rcm.stop_requested() is False
    rcm.STOP_FLAG_PATH.write_text("stop\n", encoding="utf-8")
    assert rcm.stop_requested() is True
    rcm.clear_stop_flag()
    assert rcm.stop_requested() is False


def test_reveal_brings_page_to_front():
    calls = []

    class FakePage:
        def bring_to_front(self):
            calls.append(True)

    rcm.reveal(FakePage())
    assert calls == [True]


def test_reveal_does_not_raise_on_failure():
    class FailingPage:
        def bring_to_front(self):
            raise RuntimeError("창 없음")

    rcm.reveal(FailingPage())  # 예외 없이 넘어가야 한다
