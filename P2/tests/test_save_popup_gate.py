"""저장하기 후 팝업창 모달 필수 대기 — 회귀 테스트.

버그: 상품저장설정 모달만 닫히면 성공 처리 → 팝업 없이 초기화로 진행.
이 테스트가 그 경로를 막는지 검증한다.
"""

from __future__ import annotations

import inspect
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import batch_steps as B  # noqa: E402
import collect as C  # noqa: E402

MODAL_HTML = """
<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>mock mango</title>
<style>
.toolbar button { margin: 4px; padding: 8px 12px; }
#settings { display:none; border:2px solid #333; padding:16px; margin-top:12px; }
#settings.open { display:block; }
.footer a { display:inline-block; padding:10px 18px; margin:4px; color:#fff; text-decoration:underline; }
#saveBtn { background:#1e3a8a; }
#cancelBtn { background:#3b82f6; }
#resultLayer { display:none; position:fixed; inset:20% 25%; background:#fff;
  border:3px solid #111; padding:24px; z-index:99; font-size:18px; }
#resultLayer.show { display:block; }
#initFlag { display:none; color:red; font-weight:bold; }
</style>
</head><body>
  <h2>ABCmart 검색 결과</h2>
  <div class="toolbar">
    <button id="selAll">전체선택</button>
    <button id="selSave">선택상품저장</button>
    <button id="allSave">검색된 상품 모두저장</button>
  </div>
  <div id="products">상품카드들</div>

  <div id="settings">
    <h3>상품저장설정</h3>
    <div>적용정책: 테스트</div>
    <div>검색필터명 <input id="filter" type="text" value=""></div>
    <div>저장상품수 <input id="count" type="text" value=""></div>
    <div class="footer">
      <a href="#" id="saveBtn">저장하기</a>
      <a href="#" id="cancelBtn">취소하기</a>
    </div>
  </div>

  <div id="resultLayer">3건이 수집되었다 <button id="ok">확인</button></div>
  <div id="initFlag">초기화 실행됨</div>

  <script>
    const settings = document.getElementById('settings');
    const result = document.getElementById('resultLayer');
    const initFlag = document.getElementById('initFlag');
    let mode = new URLSearchParams(location.search).get('mode') || 'popup';
    // mode=popup → 저장하기 클릭 시 결과 팝업
    // mode=nopopup → 저장하기 클릭 시 설정모달만 닫힘 (버그 재현)
    document.getElementById('allSave').onclick = () => {
      settings.classList.add('open');
    };
    document.getElementById('cancelBtn').onclick = (e) => {
      e.preventDefault();
      settings.classList.remove('open');
    };
    document.getElementById('saveBtn').onclick = (e) => {
      e.preventDefault();
      settings.classList.remove('open');
      if (mode === 'popup') {
        setTimeout(() => result.classList.add('show'), 200);
      }
      // nopopup: 팝업 안 띄움 — 예전 버그는 여기서 초기화로 넘어감
    };
    document.getElementById('ok').onclick = () => result.classList.remove('show');
    window.__runInit = () => { initFlag.style.display = 'block'; };
  </script>
</body></html>
"""


class FakeCtx:
    def __init__(self):
        self.msgs: list[str] = []
        self.save_popup_seen = False
        self.save_popup_closed = False
        self.search_popup_seen = False
        self.search_popup_closed = False
        self.save_count_logged = False
        self.save_count_snapshot = None
        self.server_save_ok = False
        self.save_awaiting_popup = False
        self.save_popup_kind = ""
        self.save_popup_ui_latched = False
        self.row_deadline = time.time() + 200
        self.save_phase_deadline = time.time() + 200
        self.mango_save_log_lines: list[str] = []
        self.save_count = 3
        self.verify = False

    def info(self, msg: str) -> None:
        self.msgs.append(msg)
        print("[CTX]", msg)

    def step(self, n: int, msg: str) -> None:
        self.msgs.append(f"[STEP {n}] {msg}")
        print(f"[CTX-STEP {n}]", msg)

    def check_budget(self, where: str = "") -> None:
        if (
            self.save_phase_deadline is not None
            and time.time() > self.save_phase_deadline
        ):
            raise C.RowBudgetExceeded("9·10·11 budget")
        if time.time() > self.row_deadline:
            raise C.RowBudgetExceeded("budget")

    def shot(self, page, tag: str, rn: int = 0) -> None:
        self.msgs.append(f"[SHOT] {tag}")


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


def _open(browser, mode: str):
    page = browser.new_page()
    page.set_content(MODAL_HTML.replace("mode') || 'popup'", f"mode') || '{mode}'"))
    # ensure mode via evaluate
    page.evaluate(f"() => {{ window.__MODE = '{mode}'; }}")
    # patch save handler mode by re-binding
    page.evaluate(
        """(mode) => {
          const settings = document.getElementById('settings');
          const result = document.getElementById('resultLayer');
          document.getElementById('saveBtn').onclick = (e) => {
            e.preventDefault();
            settings.classList.remove('open');
            if (mode === 'popup') {
              setTimeout(() => result.classList.add('show'), 150);
            }
          };
        }""",
        mode,
    )
    return page


def test_buttons_are_distinct(browser):
    """버튼1 모두저장 vs 버튼2 저장하기 구분."""
    page = _open(browser, "popup")
    page.click("#allSave")
    assert C.save_modal_visible(page)
    btn1 = C.save_all_button(page).first
    assert "모두저장" in (btn1.inner_text() or btn1.get_attribute("value") or "")
    btn2 = C.resolve_save_submit_control(page)
    label = (btn2.get_attribute("value") or btn2.inner_text() or "").strip()
    assert label == "저장하기"
    assert "모두" not in label
    page.close()


def test_find_save_complete_signal_detects_exact_phrase(browser):
    """'신규상품의 저장이 완료되었습니다' 문구를 최우선으로 즉시 감지해야 함."""
    page = _open(browser, "nopopup")
    page.evaluate(
        """() => {
            const d = document.createElement('div');
            d.textContent = '신규상품의 저장이 완료되었습니다';
            document.body.appendChild(d);
        }"""
    )
    found = C.find_save_complete_signal(page, [])
    assert found is not None
    kind, hit, _ = found
    assert kind == "complete_msg"
    assert "신규상품의 저장이 완료되었습니다" in hit
    page.close()


def test_wait_for_save_complete_signal_is_immediate_not_blind(browser):
    """요건: 120초 무행동 대기 없이, 메세지가 뜨면 즉시(짧게) 반환해야 함.

    파이썬 스레드로 페이지를 건드리면 Playwright sync API가 크로스스레드
    호출을 거부하므로(greenlet 오류), 지연 주입은 브라우저 쪽 setTimeout
    으로 한다(같은 스레드에서 안전하게 폴링만 반복).
    """
    page = _open(browser, "nopopup")
    ctx = FakeCtx()
    page.evaluate(
        """() => {
            setTimeout(() => {
                const d = document.createElement('div');
                d.id = 'complete';
                d.textContent = '신규상품의 저장이 완료되었습니다';
                document.body.appendChild(d);
            }, 400);
        }"""
    )
    start = time.time()
    found = C.wait_for_save_complete_signal(
        page, ctx, 1, dialog_msgs=[], timeout_sec=10.0  # type: ignore[arg-type]
    )
    elapsed = time.time() - start
    assert found is not None
    assert elapsed < 5.0, f"120초류 무행동 대기가 남아있음 (elapsed={elapsed:.1f}s)"
    page.close()


def test_run_save_submit_and_verify_full_flow_is_fast_and_shoots_10_11_12(browser):
    """9→10→11→12 전체 흐름이 빠르게 끝나고, 10·11·12 각각 스크린샷을 남겨야 함."""
    page = _open(browser, "popup")
    page.click("#allSave")
    page.fill("#filter", "MEN 라이프스타일")
    page.fill("#count", "3")
    ctx = FakeCtx()
    start = time.time()
    C.run_save_submit_and_verify(page, ctx, 1, 3)  # type: ignore[arg-type]
    elapsed = time.time() - start
    assert ctx.server_save_ok is True
    assert elapsed < 15.0, f"즉시탐지가 아니라 오래 걸림 (elapsed={elapsed:.1f}s)"
    assert any("[SHOT] 10_popup_open" in m for m in ctx.msgs), ctx.msgs
    assert any("[SHOT] 11_popup_closed" in m for m in ctx.msgs), ctx.msgs
    assert any("[SHOT] 12_count_logged" in m for m in ctx.msgs), ctx.msgs
    page.close()


def test_fill_save_modal_fields_are_distinct(browser):
    """회귀: modal_field()가 넓은 #settings div까지 매치해 저장상품수 칸에
    검색필터명 값이 덮어써지던 버그("저장상품수 불일치 — 실제 'xxx'") 방지.
    """
    page = _open(browser, "popup")
    page.click("#allSave")
    assert C.save_modal_visible(page)

    filter_loc = C.modal_field(page, C.FILTER_NAME_LABEL)
    count_loc = C.modal_field(page, C.SAVE_COUNT_LABEL)
    assert filter_loc.count() >= 1
    assert count_loc.count() >= 1
    same = page.evaluate(
        "([a, b]) => a === b",
        [filter_loc.element_handle(), count_loc.element_handle()],
    )
    assert not same, "검색필터명·저장상품수 입력칸이 같은 엘리먼트로 잡힘"
    page.close()


def test_fill_save_modal_overwrites_mango_default_count(browser):
    """★요건(2026-08-20): 망고 기본값 3 을 그대로 두지 않고 저장상품수로 덮어쓴다."""
    page = _open(browser, "popup")
    page.click("#allSave")
    page.fill("#count", "3")  # 망고 모달 기본값

    ctx = FakeCtx()
    effective = C.fill_save_modal_fields(page, ctx, 1, "MEN 라이프스타일", 50)
    assert page.locator("#filter").input_value() == "MEN 라이프스타일"
    assert page.locator("#count").input_value() == "50"
    assert effective == 50
    page.close()


def test_fill_save_modal_no_redundant_retype_when_already_correct(browser):
    """검색필터명·저장상품수가 이미 맞으면 재입력(덮어쓰기) 로그가 없어야 한다."""
    page = _open(browser, "popup")
    page.click("#allSave")
    page.fill("#filter", "MEN 라이프스타일")
    page.fill("#count", "50")
    ctx = FakeCtx()
    effective = C.fill_save_modal_fields(page, ctx, 1, "MEN 라이프스타일", 50)
    assert page.locator("#filter").input_value() == "MEN 라이프스타일"
    assert page.locator("#count").input_value() == "50"
    assert effective == 50
    assert not any("재입력" in m for m in ctx.msgs), ctx.msgs
    page.close()


def test_fill_save_modal_fills_empty_count_field(browser):
    """저장상품수 칸이 비어 있어도 저장수를 채워 넣는다."""
    page = _open(browser, "popup")
    page.click("#allSave")
    assert page.locator("#count").input_value() == ""
    ctx = FakeCtx()
    effective = C.fill_save_modal_fields(page, ctx, 1, "MEN 라이프스타일", 50)
    assert page.locator("#count").input_value() == "50"
    assert effective == 50
    page.close()


def test_save_modal_visible_survives_icon_wrapped_button(browser):
    """저장하기 버튼에 아이콘/공백이 섞여 정확매치가 깨져도 모달을 인식해야 함.

    회귀: save_modal_visible()의 '^저장하기$' 정확매치가 실패하면
    run_save_submit_and_verify 가 클릭 시도조차 하지 않고 즉시 실패 처리했다.
    """
    ctx = browser.new_context()
    page = ctx.new_page()
    page.set_content(
        """
        <html><body>
        <div class="footer">
          <a href="#" id="saveBtn"><i class="ico"></i>　저장하기　</a>
          <a href="#" id="cancelBtn">취소하기</a>
        </div>
        </body></html>
        """
    )
    # 제목 문구도 없고, 저장하기 텍스트에 전각공백·아이콘이 섞인 최악의 경우
    assert C.save_modal_visible(page) is True
    el = C.resolve_save_submit_control(page)
    tag = el.evaluate("(n) => n.tagName.toLowerCase()")
    assert tag == "a"
    ctx.close()


def test_chrome_launch_disables_popup_blocking():
    """실제 Chrome 실행 인자에 --disable-popup-blocking 이 포함돼야 함.

    저장하기 클릭은 trusted 여도, 사이트가 AJAX 저장 완료 콜백에서
    비동기로 window.open() 하면 Chrome이 '사용자 제스처 없음'으로 보고
    조용히 팝업을 막아버린다 — 그러면 팝업창 자체가 안 생긴다
    (오판이 아니라 실제로 안 열리는 것).
    """
    src = inspect.getsource(C.launch_debug_browser)
    assert "--disable-popup-blocking" in src


def test_no_popup_no_layer_raises_with_popup_block_hint(browser):
    """클릭해도 새 창·레이어가 전혀 안 생기면(진짜 안 열림) 원인 힌트 포함해 실패.

    회귀: 팝업이 '오판'이 아니라 '진짜로 안 열리는' 경우를 재현.
    """
    page = _open(browser, "nopopup")  # saveBtn 클릭해도 결과 레이어 안 뜸
    page.click("#allSave")
    before = {C._popup_id(p) for p in C.save_popups(page)}
    page.click("#saveBtn")
    ctx = FakeCtx()
    old = C.MODAL_WAIT_SEC
    old_g = C.SAVE_POPUP_GRACE_SEC
    C.MODAL_WAIT_SEC = 2
    C.SAVE_POPUP_GRACE_SEC = 1.0
    try:
        with pytest.raises(TimeoutError) as ei:
            C.wait_save_execution_popup(
                page,
                ctx,  # type: ignore[arg-type]
                1,
                dialog_msgs=[],
                before_popup_ids=before,
                timeout_sec=2.0,
                grace_sec=1.0,
            )
    finally:
        C.MODAL_WAIT_SEC = old
        C.SAVE_POPUP_GRACE_SEC = old_g
    msg = str(ei.value)
    assert "팝업" in msg
    assert "새 창이 전혀 안 열림" in msg or "팝업차단" in msg
    page.close()


def test_batch_step_blocks_init_when_save_awaiting_popup():
    """13항(초기화) 진입 전 save_awaiting_popup=True 면 반드시 거부돼야 함.

    '저장하기 클릭 없이 초기화 실행하면 안 된다'는 요건을 batch_steps
    진입점(run_row_batch) 레벨에서 직접 검증.
    """
    ctx = FakeCtx()
    ctx.save_awaiting_popup = True
    row = {"row": 1, "label": "x", "url": "https://example.com/a"}
    with pytest.raises(RuntimeError) as ei:
        B.run_row_batch(None, row, ctx)  # type: ignore[arg-type]
    assert "초기화" in str(ei.value) or "팝업" in str(ei.value)


def test_save_popup_on_admin_host_is_detected(browser):
    """저장 팝업이 ADMIN_HOST(같은 관리자사이트) 새 창으로 떠도 감지해야 함.

    회귀: popups()는 ADMIN_HOST 새 창을 제외해 저장 팝업을 영원히 못 봤다
    ("저장하기 눌러도 팝업이 전혀 안 뜬다"로 보이던 원인).
    save_popups()/save_result_signal_present 는 ADMIN_HOST 도 잡아야 한다.
    """
    ctx = browser.new_context()
    ctx.route(
        "**/tmg1898.cafe24.com/**",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html; charset=utf-8",
            body="<html><body>3건이 수집되었다</body></html>",
        ),
    )
    page = ctx.new_page()
    page.goto("data:text/html,<h1>main admin page</h1>")
    before = {C._popup_id(p) for p in C.save_popups(page)}

    admin_popup = ctx.new_page()
    admin_popup.goto("https://tmg1898.cafe24.com/mall/admin/save_popup.php")

    # 회귀 확인: 검색전용 popups() 는 ADMIN_HOST 를 제외하므로 못 봄
    assert admin_popup not in C.popups(page), "popups()가 ADMIN_HOST를 잡으면 안 됨(검색전용)"
    # save_popups() 는 ADMIN_HOST 포함해서 잡아야 함
    assert any(
        C._popup_id(p) == C._popup_id(admin_popup) for p in C.save_popups(page)
    ), "save_popups()가 ADMIN_HOST 저장팝업을 못 봄"

    has, detail, hit = C.save_result_signal_present(
        page, [], before_popup_ids=before, baseline=set()
    )
    assert has is True, f"ADMIN_HOST 저장 팝업을 감지 못함: {detail}"
    ctx.close()


def test_diagnose_detects_overlay_interception(browser):
    """오버레이가 저장하기 클릭좌표를 가로채면 진단이 same=False로 잡아야 함."""
    ctx = browser.new_context()
    page = ctx.new_page()
    page.set_content(
        """
        <html><body style="margin:0">
        <a href="#" id="saveBtn" style="position:absolute;left:10px;top:10px;
          width:100px;height:30px;">저장하기</a>
        <div id="overlay" style="position:absolute;left:0;top:0;width:100%;
          height:100%;background:rgba(0,0,0,0.01);z-index:999;"></div>
        </body></html>
        """
    )
    el = page.locator("#saveBtn")
    diag = C.diagnose_save_click_environment(page, el)
    assert diag.get("intercept", {}).get("same") is False, diag
    assert diag["intercept"].get("id") == "overlay"
    ctx.close()


def test_diagnose_detects_unselected_required_radio(browser):
    """정책 선택 등 미선택 라디오그룹을 진단이 잡아야 함."""
    ctx = browser.new_context()
    page = ctx.new_page()
    page.set_content(
        """
        <html><body>
        <div>
          <input type="radio" name="policy" value="a"> A
          <input type="radio" name="policy" value="b"> B
        </div>
        <a href="#" id="saveBtn">저장하기</a>
        </body></html>
        """
    )
    el = page.locator("#saveBtn")
    diag = C.diagnose_save_click_environment(page, el)
    assert any("policy" in x for x in diag.get("unselected_required", [])), diag
    ctx.close()


def test_save_resolves_clickable_not_wrapper_div(browser):
    """저장하기가 div 래퍼가 아니라 a/button/input 으로 잡혀야 함 (9항 미클릭 원인)."""
    ctx = browser.new_context()
    page = ctx.new_page()
    page.set_content(
        """
        <html><body>
        <div id="settings" class="open">
          <h3>상품저장설정</h3>
          <div>검색필터명 <input id="filter"></div>
          <div>저장상품수 <input id="count"></div>
          <div class="footer">
            <div class="btn-wrap"><a href="#" id="saveBtn">저장하기</a></div>
            <div class="btn-wrap"><a href="#" id="cancelBtn">취소하기</a></div>
          </div>
        </div>
        <div id="resultLayer" style="display:none">3건이 수집되었다
          <button id="ok">확인</button></div>
        <script>
          document.getElementById('saveBtn').onclick = (e) => {
            e.preventDefault();
            window.__SAVE_CLICKED = true;
            document.getElementById('settings').style.display = 'none';
            document.getElementById('resultLayer').style.display = 'block';
          };
        </script>
        </body></html>
        """
    )
    el = C.resolve_save_submit_control(page)
    tag = el.evaluate("(n) => n.tagName.toLowerCase()")
    assert tag in ("a", "button", "input"), f"래퍼가 잡힘: <{tag}>"
    assert C.trusted_click_save_submit(page, el) is True
    assert page.evaluate("() => window.__SAVE_CLICKED === true")
    ctx.close()


def test_modal_close_alone_is_not_reacted(browser):
    """버그 회귀: 설정 모달만 닫히면 save_submit_reacted == False."""
    page = _open(browser, "nopopup")
    page.click("#allSave")
    assert C.save_modal_visible(page)
    before = {C._popup_id(p) for p in C.popups(page)}
    page.click("#saveBtn")
    page.wait_for_timeout(400)
    assert not C.save_modal_visible(page), "설정 모달은 닫혀야 함"
    # 팝업 없음
    assert not C.save_execution_layer_visible(page)
    reacted = C.save_submit_reacted(
        page, [], before_popup_ids=before, timeout_sec=2.0
    )
    assert reacted is False, "모달 닫힘만으로 True면 안 됨"
    page.close()


def test_wait_popup_raises_without_popup_no_init(browser):
    """팝업 없으면 wait_save_execution_popup 이 오류 — 초기화 호출 금지."""
    page = _open(browser, "nopopup")
    page.click("#allSave")
    page.fill("#filter", "테스트필터")
    page.fill("#count", "3")
    before = {C._popup_id(p) for p in C.popups(page)}
    page.click("#saveBtn")
    page.wait_for_timeout(300)

    ctx = FakeCtx()
    # 타임아웃을 짧게
    old = C.MODAL_WAIT_SEC
    C.MODAL_WAIT_SEC = 3
    try:
        with pytest.raises((TimeoutError, RuntimeError)) as ei:
            C.wait_save_execution_popup(
                page,
                ctx,  # type: ignore[arg-type]
                1,
                dialog_msgs=[],
                before_popup_ids=before,
                timeout_sec=3.0,
            )
        assert "팝업" in str(ei.value)
        assert ctx.save_popup_seen is False
        # 초기화 플래그가 켜지지 않았어야 함
        assert page.is_hidden("#initFlag") or page.locator("#initFlag").evaluate(
            "e => getComputedStyle(e).display"
        ) == "none"
    finally:
        C.MODAL_WAIT_SEC = old
    page.close()


def test_wait_popup_ok_when_layer_appears(browser):
    """저장하기 후 결과 팝업(레이어)이 뜨면 통과."""
    page = _open(browser, "popup")
    page.click("#allSave")
    page.fill("#filter", "테스트필터")
    page.fill("#count", "3")
    before = {C._popup_id(p) for p in C.popups(page)}
    page.click("#saveBtn")

    ctx = FakeCtx()
    C.wait_save_execution_popup(
        page,
        ctx,  # type: ignore[arg-type]
        1,
        dialog_msgs=[],
        before_popup_ids=before,
        timeout_sec=10.0,
    )
    assert ctx.save_popup_seen is True
    assert C.save_execution_layer_visible(page) or "수집되었" in C._page_visible_text(
        page
    )
    page.close()


def test_save_result_signal_ignores_settings_modal_close(browser):
    page = _open(browser, "nopopup")
    page.click("#allSave")
    before = set()
    page.click("#saveBtn")
    page.wait_for_timeout(300)
    has, detail, _ = C.save_result_signal_present(page, [], before_popup_ids=before)
    assert has is False, f"모달 닫힘만으로 signal이면 안 됨: {detail}"
    page.close()


def test_full_gate_blocks_server_save_ok_without_popup(browser):
    """run_save 경로 핵심: 팝업 없으면 save_popup_seen/server_save_ok False."""
    page = _open(browser, "nopopup")
    page.click("#allSave")
    page.fill("#filter", "필터A")
    page.fill("#count", "3")
    ctx = FakeCtx()
    before = {C._popup_id(p) for p in C.popups(page)}
    base = C.collect_alert_baseline(page)
    page.click("#saveBtn")
    page.wait_for_timeout(200)
    old = C.MODAL_WAIT_SEC
    old_g = C.SAVE_POPUP_GRACE_SEC
    C.MODAL_WAIT_SEC = 3
    C.SAVE_POPUP_GRACE_SEC = 1.0
    try:
        with pytest.raises((TimeoutError, RuntimeError)):
            C.wait_save_overlays_settle(
                page,
                ctx,  # type: ignore[arg-type]
                1,
                dialog_msgs=[],
                before_popup_ids=before,
                baseline=base,
            )
    finally:
        C.MODAL_WAIT_SEC = old
        C.SAVE_POPUP_GRACE_SEC = old_g
    assert ctx.save_popup_seen is False
    assert ctx.server_save_ok is False
    page.close()


def test_stale_00_collect_text_is_not_save_popup(browser):
    """검색단계 잔여 '00건이 수집되었다' 로는 저장 팝업 통과·초기화 금지."""
    page = _open(browser, "nopopup")
    # 검색 단계에서 이미 화면에 있던 잔여 문구 시뮬레이션
    page.evaluate(
        """() => {
          const d = document.createElement('div');
          d.id = 'stale';
          d.textContent = '00건이 수집되었다';
          document.body.appendChild(d);
        }"""
    )
    page.click("#allSave")
    page.fill("#filter", "필터")
    page.fill("#count", "3")
    base = C.collect_alert_baseline(page)
    assert any("00건" in x or ":0:" in x for x in base), base
    before = {C._popup_id(p) for p in C.popups(page)}
    page.click("#saveBtn")
    page.wait_for_timeout(300)

    # 잔여 00건만으로는 signal 없어야 함
    has, detail, _ = C.save_result_signal_present(
        page, [], before_popup_ids=before, baseline=base
    )
    assert has is False, f"잔여 00건을 팝업으로 봄: {detail}"

    ctx = FakeCtx()
    old = C.MODAL_WAIT_SEC
    old_g = C.SAVE_POPUP_GRACE_SEC
    C.MODAL_WAIT_SEC = 3
    C.SAVE_POPUP_GRACE_SEC = 1.0
    try:
        with pytest.raises((TimeoutError, RuntimeError)) as ei:
            C.wait_save_execution_popup(
                page,
                ctx,  # type: ignore[arg-type]
                1,
                dialog_msgs=[],
                before_popup_ids=before,
                baseline=base,
                timeout_sec=3.0,
                grace_sec=1.0,
            )
        assert "팝업" in str(ei.value)
    finally:
        C.MODAL_WAIT_SEC = old
        C.SAVE_POPUP_GRACE_SEC = old_g
    assert ctx.save_popup_seen is False
    page.close()


def test_new_alert_after_click_accepted_despite_stale_00(browser):
    """잔여 00건이 있어도, 클릭 후 새 '3건이 수집' 레이어면 통과."""
    page = _open(browser, "popup")
    page.evaluate(
        """() => {
          const d = document.createElement('div');
          d.id = 'stale';
          d.textContent = '00건이 수집되었다';
          document.body.appendChild(d);
        }"""
    )
    page.click("#allSave")
    base = C.collect_alert_baseline(page)
    before = {C._popup_id(p) for p in C.popups(page)}
    page.click("#saveBtn")
    ctx = FakeCtx()
    C.wait_save_execution_popup(
        page,
        ctx,  # type: ignore[arg-type]
        1,
        dialog_msgs=[],
        before_popup_ids=before,
        baseline=base,
        timeout_sec=10.0,
        grace_sec=1.0,
    )
    assert ctx.save_popup_seen is True
    page.close()


def test_must_wait_until_final_popup_closes(browser):
    """최종 팝업이 열린 뒤 닫힐 때까지 대기 — 열린 채 통과 금지."""
    page = _open(browser, "popup")
    page.click("#allSave")
    base = C.collect_alert_baseline(page)
    before = {C._popup_id(p) for p in C.popups(page)}
    page.click("#saveBtn")
    ctx = FakeCtx()
    C.wait_save_execution_popup(
        page,
        ctx,  # type: ignore[arg-type]
        1,
        dialog_msgs=[],
        before_popup_ids=before,
        baseline=base,
        timeout_sec=10.0,
        grace_sec=1.0,
    )
    assert ctx.save_popup_seen is True
    assert C.final_save_popup_still_open(
        page, before_popup_ids=before, baseline=base
    )

    # 열림 상태에서 닫힘 대기를 백그라운드로 — 잠시 후 확인 클릭
    import threading

    def _close_later():
        page.wait_for_timeout(800)
        page.click("#ok")

    threading.Thread(target=_close_later, daemon=True).start()
    C.wait_save_popup_closed(
        page,
        ctx,  # type: ignore[arg-type]
        1,
        before_popup_ids=before,
        baseline=base,
        timeout_sec=10.0,
    )
    assert ctx.save_popup_closed is True
    assert not C.final_save_popup_still_open(
        page, before_popup_ids=before, baseline=base
    )
    page.close()


def test_open_plus_close_gate(browser):
    """wait_save_overlays_settle = 열림 + 닫힘 둘 다."""
    page = _open(browser, "popup")
    page.click("#allSave")
    base = C.collect_alert_baseline(page)
    before = {C._popup_id(p) for p in C.popups(page)}
    page.click("#saveBtn")
    ctx = FakeCtx()

    import threading

    def _close_later():
        page.wait_for_timeout(1200)
        try:
            page.click("#ok")
        except Exception:
            pass

    threading.Thread(target=_close_later, daemon=True).start()
    old_g = C.SAVE_POPUP_GRACE_SEC
    C.SAVE_POPUP_GRACE_SEC = 1.0
    try:
        C.wait_save_overlays_settle(
            page,
            ctx,  # type: ignore[arg-type]
            1,
            dialog_msgs=[],
            before_popup_ids=before,
            baseline=base,
        )
    finally:
        C.SAVE_POPUP_GRACE_SEC = old_g
    assert ctx.save_popup_seen is True
    assert ctx.save_popup_closed is True
    page.close()


def test_bare_page_text_is_not_popup_modal(browser):
    """본문 '3건이 수집' 텍스트만으로는 팝업모달로 인정·초기화 금지."""
    page = _open(browser, "nopopup")
    page.evaluate(
        """() => {
          const d = document.createElement('div');
          d.id = 'orphanText';
          d.textContent = '3건이 수집되었다';
          document.body.appendChild(d);
        }"""
    )
    page.click("#allSave")
    base = set()  # 의도적으로 baseline 비움 — 그래도 UI 없으면 안 됨
    before = {C._popup_id(p) for p in C.popups(page)}
    page.click("#saveBtn")
    page.wait_for_timeout(300)
    has, detail, _ = C.save_result_signal_present(
        page, [], before_popup_ids=before, baseline=base
    )
    assert has is False, f"본문 텍스트만으로 signal: {detail}"
    assert C.save_execution_layer_visible(page, baseline=base) is False
    page.close()


def test_awaiting_popup_blocks_init_log_path(browser):
    """save_awaiting_popup=True 이면 초기화(_process_row_once 진입) 거부."""
    page = _open(browser, "nopopup")
    ctx = FakeCtx()
    ctx.save_awaiting_popup = True
    row = {"row": 1, "label": "테스트", "url": "https://example.com/x"}
    with pytest.raises(RuntimeError) as ei:
        C._process_row_once(page, row, ctx)  # type: ignore[arg-type]
    assert "팝업모달" in str(ei.value) or "초기화" in str(ei.value)
    # 초기화 로그가 찍히면 안 됨
    assert not any("0. 초기화" in m for m in ctx.msgs)
    page.close()


def test_search_popup_close_timeout_raises_no_force_continue(browser):
    """6항: 검색 팝업이 안 닫히면 TimeoutError — 강제닫고 다음단계 금지."""
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto("data:text/html,<h1>main</h1>")
    popup = ctx.new_page()
    # about:blank 는 popups() 필터에서 제외되므로 http(s)/data URL 사용
    popup.goto("data:text/html,<h1>search popup stuck</h1>")
    assert C.popups(page), "테스트용 검색 팝업이 열려 있어야 함"
    with pytest.raises(TimeoutError) as ei:
        C.wait_popups_close(page, timeout_sec=2)
    assert "6항" in str(ei.value) or "닫히지" in str(ei.value)
    # 강제 닫지 않았으므로 팝업이 남아 있어야 함
    assert not popup.is_closed()
    ctx.close()


def test_order_is_open_close_then_count(browser):
    """10 열림 → 11 닫힘 → 12 건수 순서 (닫힘 전 dismiss로 건수 소실 방지)."""
    page = _open(browser, "popup")
    page.click("#allSave")
    base = C.collect_alert_baseline(page)
    before = {C._popup_id(p) for p in C.popups(page)}
    page.click("#saveBtn")
    ctx = FakeCtx()
    import threading

    def _close_later():
        page.wait_for_timeout(900)
        try:
            page.click("#ok")
        except Exception:
            pass

    threading.Thread(target=_close_later, daemon=True).start()
    C.wait_save_execution_popup(
        page,
        ctx,  # type: ignore[arg-type]
        1,
        dialog_msgs=[],
        before_popup_ids=before,
        baseline=base,
        timeout_sec=10.0,
        grace_sec=1.0,
    )
    assert ctx.save_popup_seen is True
    # 열린 중 스냅샷
    sn, _, _, _ = C.find_mango_collect_alert(page, [], baseline=base)
    if sn is not None:
        ctx.save_count_snapshot = sn
    C.wait_save_popup_closed(
        page,
        ctx,  # type: ignore[arg-type]
        1,
        before_popup_ids=before,
        baseline=base,
        timeout_sec=10.0,
    )
    assert ctx.save_popup_closed is True
    n = C.verify_mango_collect_alert(
        page,
        ctx,  # type: ignore[arg-type]
        1,
        3,
        baseline=base,
        dismiss=False,
    )
    assert n == 3
    ctx.save_count_logged = True
    page.close()


if __name__ == "__main__":
    # pytest 없이도 직접 실행 가능
    failed = 0
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        for name, fn in [
            ("distinct", test_buttons_are_distinct),
            ("popup_blocking_flag", lambda _b: test_chrome_launch_disables_popup_blocking()),
            ("no_popup_block_hint", test_no_popup_no_layer_raises_with_popup_block_hint),
            ("batch_blocks_init", lambda _b: test_batch_step_blocks_init_when_save_awaiting_popup()),
            ("fill_modal_fields_distinct", test_fill_save_modal_fields_are_distinct),
            ("fill_modal_overwrites_default_count", test_fill_save_modal_overwrites_mango_default_count),
            ("fill_modal_no_redundant_retype", test_fill_save_modal_no_redundant_retype_when_already_correct),
            ("fill_modal_fills_empty_count", test_fill_save_modal_fills_empty_count_field),
            ("complete_signal_exact_phrase", test_find_save_complete_signal_detects_exact_phrase),
            ("complete_signal_immediate", test_wait_for_save_complete_signal_is_immediate_not_blind),
            ("full_flow_fast_shots_10_11_12", test_run_save_submit_and_verify_full_flow_is_fast_and_shoots_10_11_12),
            ("modal_visible_icon_wrapped", test_save_modal_visible_survives_icon_wrapped_button),
            ("admin_host_popup_detected", test_save_popup_on_admin_host_is_detected),
            ("diag_overlay", test_diagnose_detects_overlay_interception),
            ("diag_required_radio", test_diagnose_detects_unselected_required_radio),
            ("clickable_not_wrapper", test_save_resolves_clickable_not_wrapper_div),
            ("modal_close_not_reacted", test_modal_close_alone_is_not_reacted),
            ("raise_no_popup", test_wait_popup_raises_without_popup_no_init),
            ("popup_ok", test_wait_popup_ok_when_layer_appears),
            ("signal_ignore_close", test_save_result_signal_ignores_settings_modal_close),
            ("full_gate", test_full_gate_blocks_server_save_ok_without_popup),
            ("stale_00", test_stale_00_collect_text_is_not_save_popup),
            ("stale_00_then_new", test_new_alert_after_click_accepted_despite_stale_00),
            ("wait_until_closed", test_must_wait_until_final_popup_closes),
            ("open_plus_close", test_open_plus_close_gate),
            ("bare_text_not_modal", test_bare_page_text_is_not_popup_modal),
            ("awaiting_blocks_init", test_awaiting_popup_blocks_init_log_path),
            ("step6_no_force", test_search_popup_close_timeout_raises_no_force_continue),
            ("order_10_11_12", test_order_is_open_close_then_count),
        ]:
            try:
                fn(b)
                print(f"PASS {name}")
            except Exception as e:
                failed += 1
                print(f"FAIL {name}: {type(e).__name__}: {e}")
        b.close()
    raise SystemExit(failed)
