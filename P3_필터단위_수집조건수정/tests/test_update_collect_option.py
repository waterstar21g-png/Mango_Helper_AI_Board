"""P3_필터단위_수집조건수정 단위테스트 — 브라우저 없이 로직만 검증."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import update_collect_option as uco  # noqa: E402

# 스크린샷(망고 「번역 후 저장」 드롭다운) 목록 — 순서 그대로
MANGO_OPTIONS = [
    "번역안함",
    "더망고 무료 번역기 사용",
    "구글 번역기 사용",
    "DeepL 번역기 사용",
    "네이버(클라우드) 번역기 사용",
]
MANGO_VALUES = ["0", "1", "2", "3", "4"]


class FakeSelect:
    """select[name=translate_method] 흉내 — 라벨/값 선택과 현재값 읽기."""

    def __init__(self, options, values, selected=0):
        self.options = list(options)
        self.values = list(values)
        self.selected = selected
        self.calls: list[tuple] = []

    @property
    def first(self):  # Playwright Locator.first
        return self

    def count(self) -> int:
        return 1

    def evaluate(self, script, *args):
        if "Array.from(el.options)" in script:
            return [
                {"text": t, "value": v} for t, v in zip(self.options, self.values)
            ]
        if "selectedIndex" in script:
            return self.options[self.selected]
        raise AssertionError(f"예상 못한 스크립트: {script[:40]}")

    def select_option(self, value=None, *, label=None, timeout=None):
        self.calls.append((value, label))
        if label is not None:
            if label not in self.options:
                raise RuntimeError("no such label")
            self.selected = self.options.index(label)
            return
        if value in self.values:
            self.selected = self.values.index(value)
            return
        raise RuntimeError("no such value")


class MissingLocator:
    @property
    def first(self):
        return self

    def nth(self, _idx):
        return self

    def count(self) -> int:
        return 0


class FakeButton:
    def __init__(self, present=True):
        self.present = present
        self.clicks = 0
        self.presses: list[str] = []
        self.selectors: list[str] = []

    @property
    def first(self):
        return self

    def count(self) -> int:
        return 1 if self.present else 0

    def click(self, timeout=None):
        if not self.present:
            raise RuntimeError("없음")
        self.clicks += 1

    def press(self, key, timeout=None):
        self.presses.append(key)


class FakePage:
    def __init__(self, select=None, scan_result=None, site_select=None, search=None):
        self._select = select
        self._scan = scan_result
        self._site = site_select
        self._search = search
        self.locators: list[str] = []
        self.waited = False

    def locator(self, selector):
        self.locators.append(selector)
        if self._select is not None and uco.TRANSLATE_SELECT_NAME in selector:
            return self._select
        if self._site is not None and uco.SITE_SELECT_NAME in selector:
            return self._site
        if self._search is not None and (
            "bt_type" in selector or "검색" in selector or "sch_keyword" in selector
        ):
            self._search.selectors.append(selector)
            return self._search
        return MissingLocator()

    def evaluate(self, script, *args):
        return self._scan

    def wait_for_load_state(self, state, timeout=None):
        self.waited = True

    def wait_for_timeout(self, ms):
        return None

    def evaluate(self, script, *args):
        if "location.href" in script:
            return {
                "url": "about:blank",
                "title": "",
                "selects": [],
                "buttons": [],
                "frames": 0,
            }
        return self._scan


def _select_page(selected=0):
    return FakePage(FakeSelect(MANGO_OPTIONS, MANGO_VALUES, selected))


# ── 리스트박스 기본 목록 (사용자 지정: 스크린샷 그대로) ───────────


def test_default_options_match_mango_screen():
    assert list(uco.DEFAULT_TRANSLATE_OPTIONS) == MANGO_OPTIONS


def test_cached_options_fall_back_to_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(uco, "OPTIONS_CACHE_PATH", tmp_path / "none.json")
    assert uco.load_cached_options() == MANGO_OPTIONS


def test_cached_options_round_trip(monkeypatch, tmp_path):
    monkeypatch.setattr(uco, "OPTIONS_CACHE_PATH", tmp_path / "opts.json")
    uco.save_cached_options(["구글 번역기 사용", "번역안함"])
    assert uco.load_cached_options() == ["구글 번역기 사용", "번역안함"]


# ── 옵션 이름 매칭 ────────────────────────────────────────────────


def test_match_option_exact_and_normalized():
    assert uco.match_option(MANGO_OPTIONS, "구글 번역기 사용") == "구글 번역기 사용"
    assert uco.match_option(MANGO_OPTIONS, " 구글번역기사용 ") == "구글 번역기 사용"


def test_match_option_partial_and_miss():
    assert uco.match_option(MANGO_OPTIONS, "DeepL") == "DeepL 번역기 사용"
    assert uco.match_option(MANGO_OPTIONS, "파파고 번역") is None
    assert uco.match_option(MANGO_OPTIONS, "") is None


# ── 컨트롤 검출 ──────────────────────────────────────────────────


def test_detect_uses_translate_method_select():
    page = _select_page()
    control = uco.detect_translate_control(page)
    assert control is not None
    assert control.kind == "select"
    assert control.options == MANGO_OPTIONS
    assert control.values == MANGO_VALUES
    assert any(uco.TRANSLATE_SELECT_NAME in s for s in page.locators)


def test_detect_returns_none_without_control():
    assert uco.detect_translate_control(FakePage()) is None


def test_detect_radio_fallback():
    scan = {
        "kind": "radio",
        "options": ["번역안함", "구글 번역기 사용"],
        "name": "trans",
        "values": ["0", "2"],
    }
    control = uco.detect_translate_control(FakePage(scan_result=scan))
    assert control is not None and control.kind == "radio"
    assert [label for label, _loc in control.choices] == scan["options"]


def test_detect_checkbox_fallback():
    scan = {"kind": "checkbox", "options": ["사용", "미사용"], "name": "trans", "id": ""}
    control = uco.detect_translate_control(FakePage(scan_result=scan))
    assert control is not None and control.kind == "checkbox"


# ── 적용 ─────────────────────────────────────────────────────────


def test_read_current_option_returns_label_not_value():
    control = uco.detect_translate_control(_select_page(selected=2))
    assert uco.read_current_option(control) == "구글 번역기 사용"


def test_apply_option_selects_by_label():
    page = _select_page(selected=0)
    control = uco.detect_translate_control(page)
    logs: list[str] = []
    assert uco.apply_option(control, "DeepL 번역기 사용", progress=logs.append) is True
    assert control.locator.selected == 3
    assert control.locator.calls[0] == (None, "DeepL 번역기 사용")
    assert any("번역안함" in l and "DeepL 번역기 사용" in l for l in logs)


def test_apply_option_accepts_partial_pick():
    control = uco.detect_translate_control(_select_page())
    assert uco.apply_option(control, "네이버") is True
    assert control.locator.selected == 4


def test_apply_option_unknown_choice_fails():
    control = uco.detect_translate_control(_select_page())
    logs: list[str] = []
    assert uco.apply_option(control, "파파고", progress=logs.append) is False
    assert control.locator.selected == 0
    assert any("미검출" in l for l in logs)


def test_apply_option_falls_back_to_value():
    select = FakeSelect(MANGO_OPTIONS, MANGO_VALUES)

    def label_fails(value=None, *, label=None, timeout=None):
        if label is not None:
            raise RuntimeError("label 선택 불가")
        FakeSelect.select_option(select, value, label=None, timeout=timeout)

    control = uco.detect_translate_control(FakePage(select))
    select.select_option = label_fails  # type: ignore[assignment]
    assert uco.apply_option(control, "구글 번역기 사용") is True
    assert select.selected == 2


def test_checkbox_on_off_words():
    assert uco.wants_on("사용") is True
    assert uco.wants_on("미사용") is False
    assert uco.wants_on("번역안함") is False


# ── 보드 연동 (옵션 목록 주고받기) ────────────────────────────────


def test_option_lines_round_trip():
    text = uco.format_option_lines(MANGO_OPTIONS)
    assert uco.parse_option_lines("잡음\n" + text + "\n기타 로그") == MANGO_OPTIONS


def test_parse_option_lines_ignores_other_output():
    assert uco.parse_option_lines("##MAIN##필터 3행\n[오류] 없음") == []


# ── 수집사이트 리스트박스 (스크린샷: select[name=site_id]) ────────


MANGO_SITES = [
    "-- 수집사이트 --",
    "4910.kr",
    "ABCmart.a-rt.com",
    "HIVER.co.kr",
    "MUSINSA.com",
    "Zara.com/de",
]


def test_default_sites_match_mango_screen():
    assert list(uco.DEFAULT_SITE_OPTIONS) == MANGO_SITES


def test_cached_sites_round_trip(monkeypatch, tmp_path):
    monkeypatch.setattr(uco, "SITES_CACHE_PATH", tmp_path / "sites.json")
    assert uco.load_cached_sites() == MANGO_SITES
    uco.save_cached_sites(["MUSINSA.com"])
    assert uco.load_cached_sites() == ["MUSINSA.com"]


def test_is_all_sites():
    assert uco.is_all_sites("") is True
    assert uco.is_all_sites("-- 수집사이트 --") is True
    assert uco.is_all_sites("MUSINSA.com") is False


def test_read_site_options_from_select():
    page = FakePage(site_select=FakeSelect(MANGO_SITES, ["", "1", "2", "3", "4", "5"]))
    assert uco.read_site_options(page) == MANGO_SITES


def test_apply_site_filter_selects_and_searches():
    site_select = FakeSelect(MANGO_SITES, ["", "1", "2", "3", "4", "5"])
    search = FakeButton()
    page = FakePage(site_select=site_select, search=search)
    logs: list[str] = []
    assert uco.apply_site_filter(page, "MUSINSA.com", progress=logs.append) is True
    assert site_select.selected == 4
    assert search.clicks == 1
    assert page.waited is True


def test_apply_site_filter_all_skips_screen():
    page = FakePage()
    assert uco.apply_site_filter(page, "-- 수집사이트 --") is True
    assert page.locators == []  # 화면을 건드리지 않음


def test_apply_site_filter_missing_select_fails(monkeypatch):
    monkeypatch.setattr(uco, "T_SITE", 300)
    assert uco.apply_site_filter(FakePage(), "MUSINSA.com") is False


def test_click_search_uses_select_condition_button_first():
    search = FakeButton()
    page = FakePage(search=search)
    logs: list[str] = []
    assert uco.click_search(page, progress=logs.append) is True
    assert uco.SEARCH_BUTTON_LABEL in search.selectors[0]
    assert search.clicks == 1
    assert any(uco.SEARCH_BUTTON_LABEL in l for l in logs)


def test_click_search_falls_back_to_enter():
    keyword = FakeButton(present=False)
    page = FakePage(search=keyword)
    assert uco.click_search(page) is True
    assert keyword.presses == ["Enter"]


# ── 수집조건수정 팝업 (열기 → 저장하기 → 닫기) ───────────────────


def test_default_list_url_is_first_screen():
    assert (
        uco.DEFAULT_LIST_URL
        == "https://tmg1898.cafe24.com/mall/admin/shop/getGoodsCategory.php"
    )


def test_build_modify_url_sits_under_admin_not_shop():
    url = uco.build_modify_url(uco.DEFAULT_LIST_URL, "720")
    assert url == (
        "https://tmg1898.cafe24.com/mall/admin/admin_group_modify.php"
        "?ps_mode=modify_filter&ps_fuid=720"
    )


def test_build_modify_url_keeps_query_of_list_out():
    url = uco.build_modify_url(uco.DEFAULT_LIST_URL + "?site_id=zara_de&pg=2", "13")
    assert url.endswith("admin_group_modify.php?ps_mode=modify_filter&ps_fuid=13")


def test_build_modify_url_needs_host():
    assert uco.build_modify_url("", "720") == ""


class FakePopup:
    def __init__(self, options=MANGO_OPTIONS, save=True, closes=True, close_btn=True):
        self.select = FakeSelect(options, MANGO_VALUES)
        self.save_btn = FakeButton(present=save)
        self.close_btn = FakeButton(present=close_btn)
        self.closes = closes
        self.closed = False
        self.dialog_handler = None
        self.waited_selector = ""
        self.order: list[str] = []

    def on(self, event, handler):
        if event == "dialog":
            self.dialog_handler = handler

    def locator(self, selector):
        if uco.TRANSLATE_SELECT_NAME in selector:
            self.order.append("select")
            return self.select
        if "set_save" in selector or "저장하기" in selector:
            self.order.append("save")
            return self.save_btn
        if "window.close" in selector or "닫기" in selector or "dtype6" in selector:
            self.order.append("close")
            return self.close_btn
        return MissingLocator()

    def evaluate(self, script, *args):
        return None

    def wait_for_selector(self, selector, timeout=None):
        self.waited_selector = selector

    def wait_for_event(self, event, timeout=None):
        if not self.closes:
            raise RuntimeError("안 닫힘")
        self.closed = True

    def is_closed(self):
        return self.closed

    def close(self):
        self.closed = True


class PopupHost:
    """팝업을 돌려주는 목록 페이지 대역."""

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


def test_apply_option_in_popup_full_flow():
    popup = FakePopup()
    logs: list[str] = []
    ok = uco.apply_option_in_popup(
        PopupHost(popup), "720", "구글 번역기 사용", progress=logs.append
    )
    assert ok is True
    assert popup.select.selected == 2          # 번역옵션 선택
    assert popup.save_btn.clicks == 1          # 저장하기
    assert popup.closed is True                # 모달 닫기
    assert popup.dialog_handler is not None    # 저장 알림 자동 확인
    assert uco.TRANSLATE_SELECT_NAME in popup.waited_selector


def test_apply_option_in_popup_save_button_missing_uses_set_save():
    popup = FakePopup(save=False)
    calls: list[str] = []
    popup.evaluate = lambda script, *a: calls.append(script)  # type: ignore[assignment]
    assert uco.apply_option_in_popup(PopupHost(popup), "720", "번역안함") is True
    assert any("set_save" in c for c in calls)


def test_apply_option_in_popup_closes_even_if_window_stays():
    popup = FakePopup(closes=False)
    assert uco.apply_option_in_popup(PopupHost(popup), "720", "번역안함") is True
    assert popup.closed is True


def test_close_button_is_clicked_right_after_save():
    """저장하기 → 바로 옆 [닫기] 클릭 (onclick=window.close())."""
    popup = FakePopup()
    logs: list[str] = []
    assert uco.apply_option_in_popup(
        PopupHost(popup), "720", "번역안함", progress=logs.append
    ) is True
    assert popup.close_btn.clicks == 1
    # 순서 보장: 번역옵션 선택 → 저장하기 → 닫기
    first = {name: popup.order.index(name) for name in ("select", "save", "close")}
    assert first["select"] < first["save"] < first["close"]
    assert any("닫기 클릭" in l for l in logs)


def test_close_falls_back_to_window_close_call():
    popup = FakePopup(close_btn=False)
    calls: list[str] = []
    popup.evaluate = lambda script, *a: calls.append(script)  # type: ignore[assignment]
    assert uco.close_popup(popup) is True
    assert any("window.close" in c for c in calls)


def test_close_selectors_match_mango_dom():
    """<a onclick="window.close();" class="defbtn_lar dtype6"><span>닫기</span></a>"""
    joined = " ".join(uco.CLOSE_SELECTORS)
    assert "window.close" in joined
    assert "defbtn_lar" in joined and "dtype6" in joined
    assert "닫기" in joined


def test_step_timeouts_are_fast():
    """단계별 대기를 10배 축소 (컴퓨터 속도)."""
    assert uco.T_CLICK <= 1_500
    assert uco.T_FIELD <= 2_000
    assert uco.T_READ <= 200
    assert uco.T_CLOSE <= 1_500
    assert uco.GAP_ROW <= 0.05
    assert uco.GAP_SEARCH <= 0.2


def test_popup_budget_is_one_second():
    """요건: 팝업·드롭다운 렌더 대기 1초 (0.3초는 목록이 덜 뜬 상태에서 실패)."""
    assert uco.T_POPUP == 1_000


class SlowPopup(FakePopup):
    """첫 1초에 안 뜨는 팝업 — 재시도로 성공."""

    def __init__(self):
        super().__init__()
        self.waits = 0

    def wait_for_selector(self, selector, timeout=None):
        self.waits += 1
        assert timeout == uco.T_POPUP
        if self.waits == 1:
            raise RuntimeError("아직 안 뜸")
        self.waited_selector = selector


def test_slow_popup_retries_once_then_proceeds():
    popup = SlowPopup()
    logs: list[str] = []
    assert uco.wait_translate_select(popup, progress=logs.append) is True
    assert popup.waits == 2
    assert any("재시도" in l for l in logs)


def test_apply_option_in_popup_bad_option_fails_without_save():
    popup = FakePopup()
    assert uco.apply_option_in_popup(PopupHost(popup), "720", "파파고") is False
    assert popup.save_btn.clicks == 0


# ── 실행 인자 검증 ───────────────────────────────────────────────


def test_run_requires_option():
    result = uco.run_update_collect_option("   ")
    assert result.ok is False
    assert "선택" in result.errors[0]


def test_option_lines_include_sites():
    text = uco.format_option_lines(MANGO_OPTIONS, MANGO_SITES)
    assert uco.parse_option_lines(text) == MANGO_OPTIONS
    assert uco.parse_site_lines(text) == MANGO_SITES


# ── 프레임 안 드롭다운 · 대기 · 진단 (수집사이트 미검출 대응) ─────


class FakeFrame:
    def __init__(self, select=None, names=(), url="https://tmg1898.cafe24.com/frame"):
        self._select = select
        self._names = list(names)
        self.url = url

    def locator(self, selector):
        if self._select is not None and uco.SITE_SELECT_NAME in selector:
            return self._select
        return MissingLocator()

    def evaluate(self, script, *args):
        return {
            "url": self.url,
            "title": "frame",
            "selects": self._names,
            "buttons": ["선택조건으로 검색하기"],
            "frames": 0,
        }


class FramedPage:
    """메인 프레임에는 없고 하위 프레임에 수집사이트 select 가 있는 화면."""

    def __init__(self, frame):
        self.frame = frame
        self.frames = [self, frame]
        self.waits = 0

    def locator(self, selector):
        return MissingLocator()

    def evaluate(self, script, *args):
        return {
            "url": "https://tmg1898.cafe24.com/mall/admin/shop/getGoodsCategory.php",
            "title": "The.Mango",
            "selects": ["date_type", "start_yy"],
            "buttons": ["선택조건으로 검색하기"],
            "frames": 1,
        }

    def wait_for_timeout(self, ms):
        self.waits += 1


def test_site_select_found_inside_frame():
    frame = FakeFrame(select=FakeSelect(MANGO_SITES, ["", "1", "2", "3", "4", "5"]))
    page = FramedPage(frame)
    assert uco.find_site_select(page) is not None
    assert uco.read_site_options(page) == MANGO_SITES


def test_wait_site_select_retries_then_gives_up(monkeypatch):
    monkeypatch.setattr(uco, "T_SITE", 500)  # 테스트는 짧게
    page = FramedPage(FakeFrame())  # 어디에도 없음
    logs: list[str] = []
    assert uco.wait_site_select(page, progress=logs.append) is None
    assert page.waits >= 1
    assert any("대기" in l for l in logs)


def test_site_wait_budget_is_five_seconds():
    """시작 시 한 번만 하는 단계라 넉넉히 5초."""
    assert uco.T_SITE == 5_000


def test_pick_list_page_switches_to_tab_with_site_select():
    good = FramedPage(FakeFrame(select=FakeSelect(MANGO_SITES, ["", "1"])))
    blank = FramedPage(FakeFrame())

    class Ctx:
        pages = [blank, good]

    blank.context = Ctx()
    assert uco.pick_list_page(blank) is good


def test_diagnose_reports_url_selects_and_buttons():
    page = FramedPage(FakeFrame(names=["site_id", "sales_yn"]))
    logs: list[str] = []
    names = uco.dump_selects(page, progress=logs.append)
    assert "site_id" in names and "date_type" in names
    joined = " ".join(logs)
    assert "[진단]" in joined and "url=" in joined
    assert "선택조건으로 검색하기" in joined  # 버튼 라벨까지 알려준다
