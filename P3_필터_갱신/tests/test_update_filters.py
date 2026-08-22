"""P3_필터_갱신 단위테스트 — 저장상품수 매핑·URL정규화·엑셀 읽기."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import openpyxl  # noqa: E402
from update_filters import (  # noqa: E402
    DEFAULT_MANGO_URL,
    click_edit_on_row,
    click_modified_confirm,
    click_save_button,
    excel_by_url,
    filter_compare_note,
    find_excel_by_demango_url,
    filters_equal,
    is_modify_page_open,
    list_demango_rows,
    load_mango_url_default,
    map_save_count,
    normalize_url,
    page_shows_not_found,
    read_excel_rows,
    save_mango_url,
    set_save_count,
    screenshot_after_edit_click_series,
    wait_modify_page_closed,
)

DEMANGO_LIST_HTML = """
<html><body>
<table>
<tr>
  <th><input type="checkbox"></th>
  <th>사이트</th>
  <th>필터이름(수정가능)</th>
  <th>검색필터(저장조건)</th>
  <th>저장상품/휴지통</th>
</tr>
<tr>
  <td><input type="checkbox"></td>
  <td>Zara.com/de</td>
  <td><input type="text" value="여성헤어_헤어"></td>
  <td>
    <b>URL 검색:</b>
    <a href="https://www.zara.com/de/en/woman-zara-hair-groom-mkt17602.html?v1=2662755">
      https://www.zara.com/de/en/woman-zara-hair-groom-mkt17602.html?v1=2662755
    </a>
    | <span style="background:#2563eb;color:#fff">수집개수: 3개 | 전체저장</span>
    <button type="button" id="edit-correct-352"
      onclick="document.body.setAttribute('data-clicked','352'); location.href='admin_group_modify.php?ps_mode=modify_filter&amp;ps_fuid=352'">
      수집조건수정
    </button>
  </td>
  <td>0개 / 0개<br>상품확인 (0원)</td>
</tr>
<tr>
  <td><input type="checkbox"></td>
  <td>Zara.com/de</td>
  <td><input type="text" value="여성향수_향수"></td>
  <td>
    URL 검색:
    <a href="https://www.zara.com/de/en/woman-perfumes-l123.html">
      https://www.zara.com/de/en/woman-perfumes-l123.html
    </a>
    | <span>수집개수: 3개 | 전체저장</span>
    <input type="button" id="edit-correct-353" value="수집조건수정" onclick="document.body.setAttribute('data-clicked','353'); go(353)">
  </td>
  <td>2개 / 0개</td>
</tr>
</table>
</body></html>
"""

# 사용자 스크린샷 구조: URL | 수집개수: 3개 | 전체저장 | 수집조건수정
# 행 앞쪽에 엉뚱한 '수집조건수정'/not-found 링크가 있어도 옆 버튼만 눌러야 함
# 옆 버튼은 window.open 으로 수정 팝업을 띄움
DEMANGO_LIST_WITH_DECOY_HTML = """
<html><body>
<table>
<tr>
  <th>필터이름(수정가능)</th>
  <th>검색필터(저장조건)</th>
</tr>
<tr>
  <td><input type="text" value="남성의류_니트"></td>
  <td>
    <a href="admin_group_modify.php?ps_mode=modify_filter&amp;ps_fuid=999"
       id="decoy-wrong">수집조건수정</a>
    URL 검색:
    <a href="https://www.zara.com/de/en/man-knitwear-long-sleeve-l15978.html?v1=2432237">
      https://www.zara.com/de/en/man-knitwear-long-sleeve-l15978.html?v1=2432237
    </a>
    |
    <span style="background:#2b6cb0;color:#fff;padding:2px 6px">수집개수: 3개 | 전체저장</span>
    <input type="button" id="edit-real" value="수집조건수정"
      onclick="document.body.setAttribute('data-clicked','real-777'); window.open('about:blank','mod777');">
  </td>
</tr>
</table>
<script>
// about:blank 팝업에 수정화면 골격 주입 (Playwright expect_popup 검증용)
(function() {
  const _open = window.open;
  window.open = function(url, name) {
    const w = _open.call(window, url, name);
    try {
      w.document.write('<html><body><h1>검색필터 수정</h1>'
        + '<div>저장상품수</div><div>검색결과 상위 <input value="3"> 개</div>'
        + '<input type="button" value="저장하기"></body></html>');
      w.document.close();
    } catch (e) {}
    return w;
  };
})();
</script>
</body></html>
"""

# ★사용자 실사용 데이터: 같은 「URL 검색」 주소가 여러 행에 있고 필터이름만 다르다.
#   URL 만 보고 첫 행을 잡으면 2번째·3번째 행을 갱신할 때 1번째 행이 바뀌어 버린다.
DEMANGO_LIST_DUP_URL_HTML = """
<html><body>
<table>
<tr>
  <th>사이트</th><th>필터이름(수정가능)</th><th>검색필터(저장조건)</th>
</tr>
<tr>
  <td>Zara.com/de</td>
  <td><input type="text" value="남성_니트롱슬리브"></td>
  <td>
    URL 검색:
    <a href="https://www.zara.com/de/en/man-knitwear-long-sleeve-l15978.html?v1=2432237">
      https://www.zara.com/de/en/man-knitwear-long-sleeve-l15978.html?v1=2432237
    </a>
    | <span>수집개수: 76개 | 전체저장</span>
    <input type="button" value="수집조건수정"
      onclick="document.body.setAttribute('data-clicked','row1')">
  </td>
</tr>
<tr>
  <td>Zara.com/de</td>
  <td><input type="text" value="남성의류_니트"></td>
  <td>
    URL 검색:
    <a href="https://www.zara.com/de/en/man-linen-sweaters-l17547.html?v1=2720371">
      https://www.zara.com/de/en/man-linen-sweaters-l17547.html?v1=2720371
    </a>
    | <span>수집개수: 3개 | 전체저장</span>
    <input type="button" value="수집조건수정"
      onclick="document.body.setAttribute('data-clicked','row2')">
  </td>
</tr>
<tr>
  <td>Zara.com/de</td>
  <td><input type="text" value="남성의류_니트2"></td>
  <td>
    URL 검색:
    <a href="https://www.zara.com/de/en/man-knitwear-long-sleeve-l15978.html?v1=2432237">
      https://www.zara.com/de/en/man-knitwear-long-sleeve-l15978.html?v1=2432237
    </a>
    | <span>수집개수: 3개 | 전체저장</span>
    <input type="button" value="수집조건수정"
      onclick="document.body.setAttribute('data-clicked','row3')">
  </td>
</tr>
</table>
</body></html>
"""

MODIFY_HTML = """
<html><body>
<h1>검색필터 수정</h1>
<table>
  <tr><th>검색 URL</th>
      <td><input value="https://www.zara.com/de/en/woman-zara-hair-groom-mkt17602.html?v1=2662755"></td></tr>
  <tr>
    <th>저장상품수</th>
    <td>검색결과 상위 <input type="text" name="ps_save_cnt" value="3"> 개 상품만 저장</td>
  </tr>
</table>
<input type="button" value="저장하기">
<input type="button" value="닫기">
</body></html>
"""


def test_map_save_count_rules():
    assert map_save_count(0) == 0
    assert map_save_count(200) == 200
    assert map_save_count(201) == 300
    assert map_save_count(500) == 300
    assert map_save_count(501) == 400
    assert map_save_count(900) == 400


def test_normalize_url():
    a = normalize_url("https://WWW.Example.com/path/")
    b = normalize_url("https://www.example.com/path")
    assert a == b


def test_filters_equal():
    assert filters_equal("MEN 스니커즈", "MEN 스니커즈")
    assert not filters_equal("A", "B")
    # 불일치 → 엑셀 중간 공백을 _ 로 바꿔 재비교
    assert filters_equal("MEN 스니커즈", "MEN_스니커즈")
    assert filters_equal("A B C", "A_B_C")
    assert not filters_equal("MEN스니커즈", "MEN_스니커즈")  # 엑셀에 공백 없음
    assert filter_compare_note("MEN 스니커즈", "MEN_스니커즈")
    assert filter_compare_note("SAME", "SAME") == ""


def test_mango_url_default_and_save(tmp_path: Path, monkeypatch):
    """망고 URL 고정 초기값 = getGoodsCategory.php(filter_delete·zara_de)."""
    import update_filters as uf

    path = tmp_path / ".last_mango_url"
    monkeypatch.setattr(uf, "LAST_MANGO_URL_PATH", path)
    want = (
        "https://tmg1898.cafe24.com/mall/admin/shop/getGoodsCategory.php"
        "?pmode=filter_delete&uids=&pg=1&date_type=modify"
        "&start_yy=2026&start_mm=8&start_dd=12"
        "&end_yy=2026&end_mm=8&end_dd=12"
        "&site_id=zara_de&sales_yn=&sch_keyword="
        "&ft_num=all&ft_show=&ft_sort=modify_asc"
    )
    assert DEFAULT_MANGO_URL == want
    assert load_mango_url_default() == want
    # .last 에 다른 값이 있어도 초기값은 고정
    path.write_text("https://abcmart.a-rt.com/?track=W0009\n", encoding="utf-8")
    assert load_mango_url_default() == want
    save_mango_url(want)
    assert path.read_text(encoding="utf-8").strip() == want


def test_reveal_browser_page_brings_front():
    """현재 Chrome 탭/팝업을 bring_to_front 로 보여 준다 (화면상세 로그는 억제)."""
    from playwright.sync_api import sync_playwright
    from update_filters import attach_current_mango_page, describe_page_state, reveal_browser_page

    assert callable(attach_current_mango_page)
    fronts: list[str] = []

    class Wrap:
        def __init__(self, page):
            self._p = page

        def __getattr__(self, name):
            return getattr(self._p, name)

        def bring_to_front(self):
            fronts.append("front")
            return self._p.bring_to_front()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(
            "<html><head><title>팝업테스트</title></head>"
            "<body>스토어팝업</body></html>"
        )
        wrapped = Wrap(page)
        reveal_browser_page(
            wrapped, None, step_no="2", action="스토어 팝업 표시", dwell_s=0
        )
        state = describe_page_state(page)
        browser.close()

    assert fronts == ["front"]
    assert "팝업테스트" in state or "url=" in state


def test_attach_mango_browser_uses_p2_connect_browser():
    """P3는 P2 connect_browser 로 망고 Chrome을 연결·표시한다."""
    from update_filters import attach_mango_browser_like_p2

    calls: list[str] = []

    class FakePage:
        url = "https://tmg1898.cafe24.com/mall/admin/admin.php"
        context = None

        def __init__(self):
            self.context = self

        def new_cdp_session(self, _page):
            class S:
                def send(self, *_a, **_k):
                    return {"windowId": 1}

                def detach(self):
                    return None

            return S()

        def set_default_timeout(self, *_a, **_k):
            return None

        def bring_to_front(self):
            calls.append("front")

        def evaluate(self, *_a, **_k):
            return None

        def is_closed(self):
            return False

        def title(self):
            return "mango"

    class FakeP2:
        @staticmethod
        def connect_browser(_pw):
            calls.append("connect")
            return object(), FakePage()

        @staticmethod
        def refresh_if_closed(page):
            return page

    _browser, page = attach_mango_browser_like_p2(FakeP2(), object(), progress=None)
    assert "connect" in calls
    assert "front" in calls
    assert isinstance(page, FakePage)


def test_maximize_mango_chrome_window_logs_and_cdp():
    """목록 복귀 후 행 재탐색 전 — 망고 창 최대화 CDP (화면상세 로그는 억제)."""
    from update_filters import maximize_mango_chrome_window

    cdp_states: list[str] = []

    class FakePage:
        url = "https://tmg1898.cafe24.com/mall/admin/shop/getGoodsCategory.php"
        context = None

        def __init__(self):
            self.context = self

        def new_cdp_session(self, _page):
            class S:
                def send(self, method, params=None):
                    if method == "Browser.getWindowForTarget":
                        return {"windowId": 7}
                    if method == "Browser.setWindowBounds":
                        cdp_states.append(
                            (params or {}).get("bounds", {}).get("windowState")
                        )
                        return {}
                    return {}

                def detach(self):
                    return None

            return S()

        def bring_to_front(self):
            return None

        def evaluate(self, *_a, **_k):
            return None

        def is_closed(self):
            return False

        def title(self):
            return "더망고"

    maximize_mango_chrome_window(FakePage(), None, dwell_s=0)
    assert "maximized" in cdp_states


def test_read_excel_and_lookup(tmp_path: Path):
    fp = tmp_path / "sample.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(
        ["상위 최종 카테고리명", "최종 카테고리 URL주소", "상품수집가능개수"]
    )
    ws.append(["MEN A", "https://shop.example/a", 150])
    ws.append(["MEN B", "https://shop.example/b", 350])
    ws.append(["MEN C", "https://shop.example/c", 600])
    wb.save(fp)

    rows = read_excel_rows(fp)
    assert len(rows) == 3
    by = excel_by_url(rows)
    r = by[normalize_url("https://shop.example/b")]
    assert r.filter_name == "MEN B"
    assert map_save_count(r.collectible) == 300
    assert map_save_count(by[normalize_url("https://shop.example/c")].collectible) == 400
    # 더망고 URL 기준으로 엑셀 검색
    found = find_excel_by_demango_url(by, "https://shop.example/a/")
    assert found is not None
    assert found.filter_name == "MEN A"
    assert find_excel_by_demango_url(by, "https://shop.example/nope") is None


def test_list_demango_rows_filter_input_and_url():
    """스크린샷 구조: 필터이름(수정가능) input · URL 검색 · 수집조건수정."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(DEMANGO_LIST_HTML)
        rows = list_demango_rows(page)
        browser.close()

    assert len(rows) == 2
    assert rows[0]["filterName"] == "여성헤어_헤어"
    assert "woman-zara-hair-groom" in rows[0]["url"]
    assert "ps_fuid=352" in (rows[0].get("editHref") or "")
    assert rows[0]["hasEdit"] is True
    # 사이트열(Zara.com/de)을 필터값으로 오인하지 않음
    assert "Zara" not in rows[0]["filterName"]
    assert rows[1]["filterName"] == "여성향수_향수"
    assert "woman-perfumes" in rows[1]["url"]
    assert "ps_fuid=353" in (rows[1].get("editHref") or "")


def test_click_edit_prefers_button_beside_collect_count(tmp_path: Path):
    """수집개수|전체저장 옆 버튼 클릭 → 수정 팝업 + 클릭후 샷 3장."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_content(DEMANGO_LIST_WITH_DECOY_HTML)
        rows = list_demango_rows(page)
        assert len(rows) == 1
        href = rows[0].get("editHref") or ""
        assert "999" not in href
        shot_dir = tmp_path / "shots"
        ok = click_edit_on_row(
            page,
            int(rows[0]["index"]),
            href,
            row_url=rows[0]["url"],
            progress=None,
            shot_dir=shot_dir,
            row_no=7,
            shot_count=0,
            max_tries=5,
            try_interval_s=0.2,
        )
        assert ok is True
        assert page.locator("body").get_attribute("data-clicked") == "real-777"
        assert len(context.pages) >= 2
        browser.close()


def test_no_coordinate_click_logic_in_source():
    """'전체저장 우측 N글자 이동 클릭' 좌표계산 로직은 완전히 삭제되어야 함."""
    src = (ROOT / "update_filters.py").read_text(encoding="utf-8")
    assert "EDIT_CLICK_FIXED_CHARS" not in src
    assert "EDIT_CLICK_CHAR_PAD_X" not in src
    assert "_edit_click_point_from_allsave" not in src
    assert "_find_allsave_anchor_geometry" not in src
    assert "page.mouse.click(x, y)" not in src


def test_find_edit_button_with_log_marks_real_element():
    """LABEL '수집조건수정'의 실제 버튼요소를 찾아 마킹 — 좌표 없이 요소 자체를 반환."""
    from playwright.sync_api import sync_playwright
    from update_filters import _find_edit_button_with_log

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(DEMANGO_LIST_WITH_DECOY_HTML)
        rows = list_demango_rows(page)
        info = _find_edit_button_with_log(
            page,
            int(rows[0]["index"]),
            rows[0]["url"],
            log_find=False,
        )
        assert info.get("ok") is True
        assert info.get("allsave_found") is True
        assert info.get("matched_label") == "수집조건수정"
        # 실제 DOM 요소가 마킹되어 locator로 곧바로 클릭 가능해야 함
        assert page.locator('[data-p3-edit-target="1"]').count() == 1
        browser.close()


def test_find_edit_button_with_log_logs_text_and_screenshots(tmp_path: Path):
    """전체저장/수집조건수정 찾기 전·후 — 텍스트·버튼명 + 스크린샷 로그."""
    from playwright.sync_api import sync_playwright
    from update_filters import _find_edit_button_with_log, _is_major_log

    logs: list[tuple[str, str]] = []

    def progress(step: str, msg: str) -> None:
        logs.append((step, msg))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(DEMANGO_LIST_WITH_DECOY_HTML)
        rows = list_demango_rows(page)
        shot_dir = tmp_path / "shots"
        info = _find_edit_button_with_log(
            page,
            int(rows[0]["index"]),
            rows[0]["url"],
            progress=progress,
            shot_dir=shot_dir,
            row_no=1,
            log_find=True,
        )
        assert info.get("ok") is True
        browser.close()

    texts = [m for s, m in logs]
    assert any("텍스트 찾기 전" in m and "전체저장" in m for m in texts)
    assert any("텍스트 찾기 후" in m and "전체저장" in m for m in texts)
    assert any("버튼명 찾기 전" in m and "수집조건수정" in m for m in texts)
    assert any("버튼명 찾기 후" in m and "수집조건수정" in m for m in texts)
    shots = list(shot_dir.glob("*.png"))
    assert len(shots) >= 4
    # 버튼 찾기 과정은 5) 수집조건수정 단계의 세부내용(SUB) — MAIN엔 7단계만
    assert all("5) " in m for m in texts if "찾기" in m)
    assert not _is_major_log("주요", "5) 텍스트 찾기 전 · 텍스트=전체저장")
    assert not _is_major_log("화면", "망고 Chrome 창 표시")


def test_click_edit_on_row_uses_real_locator_click_not_coordinates(tmp_path: Path):
    """click_edit_on_row 는 마킹된 실제 버튼 요소를 locator.click() 으로 클릭한다."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_content(DEMANGO_LIST_WITH_DECOY_HTML)
        rows = list_demango_rows(page)
        ok = click_edit_on_row(
            page,
            int(rows[0]["index"]),
            row_url=rows[0]["url"],
            progress=None,
            shot_dir=tmp_path / "shots",
            row_no=1,
            max_tries=2,
            try_interval_s=0.2,
        )
        assert ok is True
        # onclick 핸들러가 실행되어 실제 클릭이 일어났음을 증명
        assert page.locator("body").get_attribute("data-clicked") == "real-777"
        browser.close()


def test_run_update_uses_canonical_7step_log_messages():
    """run_update 본문이 사용자 지정 1)~7) 단계 문구·중요정보를 사용해야 함."""
    src = (ROOT / "update_filters.py").read_text(encoding="utf-8")
    assert "1) 망고 수집 URL 링크로 진입" in src
    assert "2) 망고행 · 필터=" in src  # 2단계 = 망고행 요약(URL 1회)
    assert "2) 망고행 원문: " in src  # 원문은 SUB
    assert "4) 상품수 {ex.collectible} (엑셀값 사용 · URL 화면 안 열음)" in src
    assert "5) 수집조건수정 → 저장하기 → 확인 OK · 상품수 " in src
    assert "7) 갱신 완료 (저장상품수 " in src
    # 매칭되지 않는 행 정보는 로그에 남기지 않음 (KEY/필터 불일치 시 조용히 skip)
    assert "매칭되지 않는 정보는 로그에 남기지 않는다" in src
    # 옛 Logger 세부로그 클래스·미사용 비교로그는 완전히 제거됨
    assert "class Logger" not in src
    assert "DETAIL_EXCEL_ROWS" not in src
    assert "log_first10_compare" not in src
    # '저장'이 아닌 '저장하기' 라벨을 찾아 클릭 (요건 정정 반영)
    assert 'value="저장하기"' in src
    assert "click_save_button" in src


def test_major_log_filter_keeps_steps_drops_noise():
    """자동판정은 오류/중단/완료 요약만 MAIN — 1)~7) 단계는 호출부 major=True.

    ★메시지 첫머리의 "N)" 로 자동판정하면 스크린샷 라벨
    ("6)확인 클릭 실패 -> ....png")까지 MAIN 에 섞인다(요건: MAIN은 7단계만).
    """
    from update_filters import _is_major_log

    assert _is_major_log("오류", "행1 실패")
    assert _is_major_log("중단", "사용자 중단 요청")
    assert _is_major_log("완료", "갱신 1 · 실패 0")
    assert not _is_major_log("준비", "스크린샷 폴더: /tmp/x")
    assert not _is_major_log("화면", "필터일치 목록행 표시 · filter=x")
    # 스크린샷 세부로그는 단계번호로 시작해도 MAIN 이 아니다
    assert not _is_major_log("샷", "6)확인 클릭 실패 -> /tmp/x/r106_06_confirm_fail.png")
    assert not _is_major_log("로직", "5) LABEL '수집조건수정' 버튼 찾아 실제 클릭")


def test_step_logs_go_to_main_and_details_group_by_step(capsys):
    """MAIN=1~7단계만 · 단계 진행 중 세부내용은 그 단계 SUB로 묶인다."""
    import update_filters as uf

    uf._SEQ_STATE.update({"seq": 0, "cur_seq": 0, "cur_n": 0})
    uf._PENDING_SUB.clear()

    uf._log(None, "준비", "엑셀 x.xlsx · URL 12건")
    uf._log(None, "로직", "1) 망고 수집 URL 링크로 진입: https://tmg", major=True)
    uf._log(None, "로직", "2) KEY확인 · 필터=니트", major=True)
    # 5단계 동작 중 세부내용 — 5단계 MAIN 이 아직 안 나왔다
    uf._log(None, "화면", "5) 검색필터 수정 팝업 표시 · url=https://tmg/modify", major=False)
    uf._log(None, "샷", "5)검색필터 수정 화면 -> /tmp/s/r1_05.png", major=False)
    uf._log(None, "로직", "5) 저장상품수=73 입력 → 저장하기 클릭 완료", major=True)
    uf._log(None, "오류", "행106 · 6) '확인' 버튼 클릭 실패 · KEY=https://zara")
    uf._log(None, "완료", "갱신 0 · 건너뜀 0 · 실패 1 / 더망고 12행")

    lines = [ln for ln in capsys.readouterr().out.splitlines() if "##" in ln]
    mains = [ln.split("##") for ln in lines if "##MAIN##" in ln]
    steps = [int(p[3]) for p in mains]
    # MAIN 은 7단계 범위만 (실패한 6단계도 그 단계 행으로 남는다)
    assert [s for s in steps if 1 <= s <= 7] == [1, 2, 5, 6]
    # 단계를 특정할 수 없는 완료 요약은 90/91/92 코드 (보드가 SUB로 표시)
    assert 91 in steps

    def subs_of(seq: int) -> list[str]:
        out = []
        for ln in lines:
            if f"##SUB##{seq}##" in ln:
                out.append(ln.split(f"##SUB##{seq}##", 1)[1])
        return out

    seq_by_step = {int(p[3]): int(p[2]) for p in mains}
    # 준비 로그는 첫 단계(1)의 세부내용으로 들어간다
    assert any("엑셀 x.xlsx" in m for m in subs_of(seq_by_step[1]))
    # 5단계 진행 중 세부내용·스크린샷은 5단계에 묶인다 (앞 단계 2에 섞이지 않음)
    five = subs_of(seq_by_step[5])
    assert any("검색필터 수정 팝업 표시" in m for m in five)
    assert any("r1_05.png" in m for m in five)
    assert subs_of(seq_by_step[2]) == []


def test_store_count_call_commented_out_never_opens_row_url():
    """★요건: 망고 행 「URL 검색」 주소로 상품수 읽기·화면열기 전부 주석처리."""
    import update_filters as uf

    assert uf.ENABLE_STORE_COUNT_CALL is False
    # 함수 자체는 추후 완성본을 위해 남겨 두지만 호출부는 없어야 한다
    assert callable(uf.browse_store_count_cards)
    assert callable(uf.click_demango_row_url)
    src = (ROOT / "update_filters.py").read_text(encoding="utf-8")
    assert "def browse_store_count_cards" in src
    assert "if ENABLE_STORE_COUNT_CALL:" not in src
    live = [
        ln
        for ln in src.splitlines()
        if not ln.lstrip().startswith("#")
        and ("click_demango_row_url(" in ln or "browse_store_count_cards(" in ln)
    ]
    # 남아 있는 것은 def 정의 줄뿐 — 실제 호출은 모두 주석
    assert all(ln.lstrip().startswith("def ") for ln in live), live


def test_no_delay_runs_at_machine_speed():
    """★요건: 순서만 지키고 중간 대기 없이 컴퓨터 속도로 진행 (지연 0)."""
    import update_filters as uf

    assert uf.SLOW_DEMO_ROWS == 0
    assert uf.SLOW_DEMO_DELAY_SEC == 0.0
    assert uf.STEP_VIEW_DWELL_SEC == 0.0
    for n in (1, 5, 6, 99):
        assert uf.step_delay_sec(n) == 0.0
    src = (ROOT / "update_filters.py").read_text(encoding="utf-8")
    assert "_demo_pause" not in src  # 대기 로직 자체가 없음

def test_find_edit_marks_right_of_url():
    """수집조건수정이 URL 오른쪽에 있으면 rightOfUrl=Y."""
    from playwright.sync_api import sync_playwright
    from update_filters import _find_and_mark_edit_button

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(DEMANGO_LIST_WITH_DECOY_HTML)
        rows = list_demango_rows(page)
        info = _find_and_mark_edit_button(page, int(rows[0]["index"]), rows[0]["url"])
        assert info.get("ok") is True
        assert info.get("rightOfUrl") is True
        assert page.locator('[data-p3-edit-target="1"]').count() == 1
        browser.close()


def test_screenshot_after_edit_click_series(tmp_path: Path):
    """클릭 후 샷 시리즈가 로그용 PNG 3장을 만든다."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content("<html><body><h1>검색필터 수정</h1><div>저장상품수</div></body></html>")
        shot_dir = tmp_path / "s"
        paths = screenshot_after_edit_click_series(
            page,
            shot_dir,
            row_no=1,
            progress=None,
            count=3,
            interval_s=0,
        )
        assert len(paths) == 3
        for pth in paths:
            assert pth.is_file() and pth.stat().st_size > 0
        browser.close()


def test_click_edit_fails_when_popup_does_not_open():
    """클릭은 되나 팝업이 없으면 False — href 대체 없이 실패."""
    from playwright.sync_api import sync_playwright

    html = """
    <html><body>
    <table><tr>
      <td><input type="text" value="테스트_필터"></td>
      <td>
        URL 검색: <a href="https://www.zara.com/de/en/x.html">https://www.zara.com/de/en/x.html</a>
        | <span>수집개수: 3개 | 전체저장</span>
        <input type="button" value="수집조건수정" onclick="document.body.setAttribute('data-clicked','1')">
      </td>
    </tr></table>
    </body></html>
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html)
        rows = list_demango_rows(page)
        # editHref 가 있어도 사용하지 않고 실패해야 함
        fake_href = "admin_group_modify.php?ps_mode=modify_filter&ps_fuid=999"
        ok = click_edit_on_row(
            page,
            int(rows[0]["index"]),
            fake_href,
            row_url=rows[0]["url"],
            progress=None,
            max_tries=3,
            try_interval_s=0.1,
        )
        assert ok is False
        # 같은 탭이 href 로 이동하지 않았는지
        assert "admin_group_modify" not in (page.url or "")
        browser.close()


def test_no_href_fallback_in_click_edit_source():
    """수집조건수정 클릭 경로에 href 재시도 코드가 없어야 함."""
    src = (ROOT / "update_filters.py").read_text(encoding="utf-8")
    assert "_open_modify_via_href" not in src
    assert "href로 재시도" not in src
    assert "href 폴백" not in src
    # click_edit_on_row 본문에 금지 문구 명시
    assert "href 재시도 금지" in src or "href 대체 없음" in src


def test_find_alive_mango_and_dismiss_keeps_other_tab():
    """스토어 레이어 닫기가 더망고 탭을 닫지 않고, 재연결이 된다."""
    from playwright.sync_api import sync_playwright
    from update_filters import (
        dismiss_store_layers_only,
        find_alive_mango_page,
        page_is_usable,
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        mango = context.new_page()
        mango.goto("https://example.com/demango/admin_group_list.php?x=1")
        store = context.new_page()
        store.set_content(
            "<html><body>"
            "<button aria-label='Close'>X</button>"
            "<div>zara store</div></body></html>"
        )
        n_before = len(context.pages)
        closed = dismiss_store_layers_only(store)
        assert closed >= 1
        assert len(context.pages) == n_before
        assert not mango.is_closed()
        found = find_alive_mango_page(
            context,
            "https://example.com/demango/admin_group_list.php?x=1",
            prefer=mango,
        )
        assert found is mango
        assert page_is_usable(found) is True
        # 스토어만 닫은 뒤에도 더망고 재연결
        store.close()
        found2 = find_alive_mango_page(
            context,
            "https://example.com/demango/admin_group_list.php?x=1",
            prefer=mango,
        )
        assert found2 is mango
        assert page_is_usable(found2) is True
        browser.close()


def test_resolve_demango_row_index_by_url():
    """복귀 후 URL로 행 index를 다시 찾는다."""
    from playwright.sync_api import sync_playwright
    from update_filters import resolve_demango_row_index_by_url

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(DEMANGO_LIST_HTML)
        rows = list_demango_rows(page)
        assert len(rows) >= 2
        want = rows[1]["url"]
        idx = resolve_demango_row_index_by_url(
            page, want, fallback_index=999, progress=None
        )
        assert idx == int(rows[1]["index"])
        browser.close()


def test_page_shows_not_found():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(
            "<html><body><h1>Not Found</h1><p>페이지를 찾을 수 없습니다</p></body></html>"
        )
        assert page_shows_not_found(page) is True
        page.set_content(
            "<html><body><h1>검색필터 수정</h1><div>저장상품수</div>"
            "<div>검색결과 상위 3 개</div><button>저장하기</button></body></html>"
        )
        assert page_shows_not_found(page) is False
        browser.close()


def test_modify_popup_save_count_and_save_button():
    """저장상품수: 값 '3' 칸을 찾아 상품수값으로 대체."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(MODIFY_HTML)
        before = page.locator("td:has-text('검색결과 상위') input").input_value()
        assert before == "3"
        assert set_save_count(page, 44)
        val = page.locator("td:has-text('검색결과 상위') input").input_value()
        assert val == "44"
        url_val = page.locator("tr:has-text('검색 URL') input").input_value()
        assert "zara.com" in url_val
        assert click_save_button(page)
        assert is_modify_page_open(page) is True
        browser.close()


def test_screenshot_step_and_save_count_grid(tmp_path: Path):
    """필터일치 단계 샷 + 저장상품수 입력그리드 근접 샷."""
    from playwright.sync_api import sync_playwright
    from update_filters import screenshot_save_count_grid, screenshot_step

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(MODIFY_HTML)
        shot_dir = tmp_path / "shots"
        p1 = screenshot_step(
            page,
            shot_dir,
            step_tag="02_modify_opened",
            label="2)검색필터 수정 화면",
            row_no=1,
            progress=None,
        )
        assert p1 is not None and p1.is_file()
        loc = page.locator("td:has-text('검색결과 상위') input").first
        p2 = screenshot_save_count_grid(
            page,
            loc,
            shot_dir,
            tag="before",
            row_no=1,
            note="현재값=3",
            progress=None,
        )
        assert p2 is not None and p2.is_file()
        browser.close()


def test_set_save_count_always_before_after_shots(tmp_path: Path):
    """5)저장상품수 갱신 전·후 스크린샷이 항상 생성된다."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(MODIFY_HTML)
        shot_dir = tmp_path / "shots"
        assert set_save_count(page, 63, shot_dir=shot_dir, row_no=10)
        before = shot_dir / "r010_05_save_count_before.png"
        after = shot_dir / "r010_05_save_count_after.png"
        assert before.is_file() and before.stat().st_size > 0
        assert after.is_file() and after.stat().st_size > 0
        assert page.locator("td:has-text('검색결과 상위') input").input_value() == "63"
        browser.close()


def test_set_save_count_reports_before_after_counts():
    """★요건: 상품수 갱신 전·후 값을 5단계 로그에 표출하도록 out 으로 돌려준다."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(MODIFY_HTML)
        io: dict = {}
        assert set_save_count(page, 73, out=io)
        assert io["before"] == "3"  # 화면 기본값
        assert io["after"] == "73"
        browser.close()


def test_dup_url_rows_click_their_own_edit_button():
    """★버그: 같은 URL이 여러 행에 있으면 2·3번째 행이 1번째 행 '수집조건수정'을 눌렀다.

    필터이름으로 그 행을 정확히 골라, 각 행이 자기 버튼을 누르는지 확인한다.
    """
    from playwright.sync_api import sync_playwright
    from update_filters import _find_and_mark_edit_button

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(DEMANGO_LIST_DUP_URL_HTML)
        rows = list_demango_rows(page)
        assert [r["filterName"] for r in rows] == [
            "남성_니트롱슬리브",
            "남성의류_니트",
            "남성의류_니트2",
        ]
        for expect, row in zip(("row1", "row2", "row3"), rows):
            page.evaluate("() => document.body.removeAttribute('data-clicked')")
            info = _find_and_mark_edit_button(
                page,
                int(row["index"]),
                row["url"],
                row["filterName"],
            )
            assert info.get("ok") is True, info
            page.locator('[data-p3-edit-target="1"]').first.click()
            assert page.locator("body").get_attribute("data-clicked") == expect, (
                f"{row['filterName']} 행이 {expect} 이 아닌 다른 행을 클릭"
            )
        browser.close()


def test_click_edit_on_row_refuses_other_row():
    """지정 필터이름과 다른 행이 잡히면 클릭하지 않고 False (다른 행 갱신 방지)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(DEMANGO_LIST_DUP_URL_HTML)
        rows = list_demango_rows(page)
        logs: list[tuple[str, str]] = []
        ok = click_edit_on_row(
            page,
            int(rows[0]["index"]),
            "",
            row_url=rows[0]["url"],
            filter_hint="엑셀에만_있는_필터",
            progress=lambda s, m: logs.append((s, m)),
            row_no=1,
            max_tries=1,
            try_interval_s=0.2,
        )
        assert ok is False
        assert page.locator("body").get_attribute("data-clicked") is None
        browser.close()


def test_find_demango_row_for_excel_prefers_matching_filter():
    """★요건2: 엑셀 URL KEY → 망고 행 찾기 (같은 URL이면 필터이름으로 구분)."""
    from playwright.sync_api import sync_playwright
    from update_filters import ExcelRow, find_demango_row_for_excel, row_done_key

    url = "https://www.zara.com/de/en/man-knitwear-long-sleeve-l15978.html?v1=2432237"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(DEMANGO_LIST_DUP_URL_HTML)

        first = find_demango_row_for_excel(
            page, ExcelRow(excel_row=2, url=url, filter_name="남성의류_니트2", collectible=3)
        )
        assert first is not None
        assert first["filterName"] == "남성의류_니트2"

        # 같은 URL 두 번째 엑셀행 — 이미 처리한 행은 건너뛰고 남은 행을 잡는다
        done = {row_done_key(url, "남성의류_니트2")}
        second = find_demango_row_for_excel(
            page,
            ExcelRow(excel_row=3, url=url, filter_name="", collectible=3),
            done_keys=done,
        )
        assert second is not None
        assert second["filterName"] == "남성_니트롱슬리브"

        # 망고에 없는 URL → None (조용히 skip)
        assert (
            find_demango_row_for_excel(
                page,
                ExcelRow(excel_row=9, url="https://example.com/none", filter_name="", collectible=1),
            )
            is None
        )
        browser.close()


def test_find_demango_rows_for_excel_returns_all_same_url_rows():
    """★요건: 같은 URL 행이 여러 개면 전체를 갱신 대상으로 돌려준다."""
    from playwright.sync_api import sync_playwright
    from update_filters import ExcelRow, find_demango_rows_for_excel

    url = "https://www.zara.com/de/en/man-knitwear-long-sleeve-l15978.html?v1=2432237"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(DEMANGO_LIST_DUP_URL_HTML)
        found = find_demango_rows_for_excel(
            page, ExcelRow(excel_row=2, url=url, filter_name="남성의류_니트2", collectible=3)
        )
        # 같은 URL 2개 행 전체 · 엑셀 필터이름 일치 행이 앞
        assert [r["filterName"] for r in found] == ["남성의류_니트2", "남성_니트롱슬리브"]
        browser.close()


def test_dup_url_count_and_url_marked_red():
    """★요건: 동일 URL 행 2개 이상이면 개수·URL 을 적색으로 구분 표시."""
    src = (ROOT / "update_filters.py").read_text(encoding="utf-8")
    assert "if len(matches) >= 2:" in src
    assert "동일 URL 망고행 {len(matches)}개 — 전체 갱신" in src
    assert "_red(" in src
    # 보드는 ##RED## 표식이 붙은 줄을 적색 행으로 표시한다
    assert 'RED_PREFIX = "##RED##"' in src


def test_run_update_is_excel_driven_in_order():
    """★요건: 1) 엑셀 첫행부터 순차 → 2) 그 URL KEY로 망고 행 찾기 (방향 반대 아님)."""
    src = (ROOT / "update_filters.py").read_text(encoding="utf-8")
    assert "for i, ex in enumerate(rows, start=1):" in src
    assert "find_demango_row_for_excel(" in src
    # 망고 목록을 훑는 방향(옛 로직)은 없어야 한다
    assert "for i, drow in enumerate(demango_rows" not in src


def test_save_count_single_write_only():
    """★요건: 저장상품수는 처음 한 번만 입력 (재입력 방식 없음)."""
    src = (ROOT / "update_filters.py").read_text(encoding="utf-8")
    assert "def verify_save_count" not in src
    assert "→ 재입력" not in src
    assert "★단발 입력" in src


def test_step2_shows_url_once_and_row_text_in_sub():
    """★요건: URL 은 2단계 MAIN 에서 한 번만 · 망고행 원문은 SUB 로."""
    src = (ROOT / "update_filters.py").read_text(encoding="utf-8")
    assert 'f"URL={d_url}"' in src
    assert '2) 망고행 원문: {d_row_text' in src
    assert 'd_row_text = " ".join((drow.get("text") or "").split())' in src
    # 다른 단계 메시지에는 URL(KEY) 을 넣지 않는다
    assert "KEY={key_short}" not in src
    assert "KEY={row_url[:100]}" not in src


def test_step5_shows_save_count_before_after():
    """★요건: 상품수 갱신전·갱신후는 5단계 '저장하기' 로그에 표출."""
    src = (ROOT / "update_filters.py").read_text(encoding="utf-8")
    assert "5) 수집조건수정 → 저장하기 → 확인 OK · 상품수 {before_cnt} → " in src


def test_step5_one_line_summary_marks_failing_part():
    """★요건: 5단계는 한 줄 요약 — 실패 시 그 부분에 '오류' 표시."""
    src = (ROOT / "update_filters.py").read_text(encoding="utf-8")
    assert "5) 수집조건수정 → 저장하기 → 확인 OK · 상품수 " in src
    assert "5) 수집조건수정 오류 · " in src
    assert "5) 수집조건수정 OK → 상품수입력 오류 · " in src
    assert "5) 수집조건수정 OK → 저장하기 오류 · " in src
    assert "5) 수집조건수정 OK → 저장하기 OK → 확인 오류 · " in src
    # 개별 완료 줄은 MAIN 에 남기지 않는다
    assert '"6) 확인 완료"' not in src
    assert "5) 저장하기 완료 · 상품수" not in src


def test_sub_lines_have_no_step_number_prefix():
    """★요건: MAIN 과 SUB 를 섞지 않는다 — 단계번호는 MAIN 에만."""
    import update_filters as uf

    assert uf._strip_step_no("5) 검색필터 수정 팝업 표시 · url=x") == (
        "검색필터 수정 팝업 표시 · url=x"
    )
    assert uf._strip_step_no("팝업닫기 후") == "팝업닫기 후"
    src = (ROOT / "update_filters.py").read_text(encoding="utf-8")
    assert "##SUB##{cur_seq}##{_strip_step_no(m)}" in src


def test_confirm_click_finds_button_in_different_browser_context():
    """'수정되었습니다' + '확인' 페이지가 원래 page 와 다른 BrowserContext(별도
    팝업/창)에 열려도 찾아서 클릭해야 한다 (admin_etc_ok.php 류 확인창)."""
    from playwright.sync_api import sync_playwright
    from update_filters import _all_pages_and_frames

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx1 = browser.new_context()
        page = ctx1.new_page()
        page.set_content("<html><body><div>검색필터 수정 화면</div></body></html>")

        ctx2 = browser.new_context()
        confirm_page = ctx2.new_page()
        confirm_page.set_content(
            "<html><body>수정되었습니다."
            "<button id='ok'>확인</button>"
            "<script>document.getElementById('ok').onclick="
            "function(){document.body.setAttribute('data-ok','1');};</script>"
            "</body></html>"
        )

        found = [kind for kind, _p in _all_pages_and_frames(page)]
        assert found.count("page") >= 2

        assert click_modified_confirm(page, timeout_ms=3000) is True
        assert confirm_page.locator("body").get_attribute("data-ok") == "1"
        browser.close()


def test_any_dialog_after_save_counts_as_confirmed():
    """★요건: '저장하기' 다음에 팝업이 뜨면 조건 없이 확인 처리 (메시지 안 따짐).

    네이티브 다이얼로그는 핸들러가 이미 수락하므로 그것으로 완료로 본다 —
    질문형('저장하시겠습니까?')이어도 실패로 만들지 않는다.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content("<html><body><div>대기중</div></body></html>")
        for msg in ("저장하시겠습니까?", "수정되었습니다", ""):
            state = {"seen": True, "message": msg, "accepted": True}
            assert (
                click_modified_confirm(page, timeout_ms=600, dialog_state=state) is True
            ), msg
        # 팝업도 없고 '확인' 요소도 없으면 실패
        assert click_modified_confirm(page, timeout_ms=400) is False
        browser.close()


def test_real_completion_dialog_message_still_short_circuits():
    """실제 완료 안내('수정되었습니다')는 그대로 완료로 인정한다."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content("<html><body><div>대기중</div></body></html>")
        dialog_state = {"seen": True, "message": "수정되었습니다", "accepted": True}
        assert click_modified_confirm(page, timeout_ms=600, dialog_state=dialog_state) is True
        browser.close()


def test_modified_confirm_click_after_popup_close():
    """저장 후 '수정되었습니다' 팝업의 확인 버튼 클릭."""
    from playwright.sync_api import sync_playwright

    html = """
    <html><body>
      <div class="ui-dialog" role="dialog">
        <div>수정되었습니다</div>
        <input type="button" id="okbtn" value="확인">
      </div>
      <script>
        document.getElementById('okbtn').onclick = function() {
          document.body.setAttribute('data-confirmed', '1');
          this.closest('.ui-dialog').remove();
        };
      </script>
    </body></html>
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html)
        assert wait_modify_page_closed(page, timeout_ms=2000) is True
        assert click_modified_confirm(page, timeout_ms=5000) is True
        assert page.locator("body").get_attribute("data-confirmed") == "1"
        assert page.locator("text=수정되었습니다").count() == 0
        browser.close()


if __name__ == "__main__":
    import tempfile

    test_map_save_count_rules()
    test_normalize_url()
    test_filters_equal()
    with tempfile.TemporaryDirectory() as d:
        test_read_excel_and_lookup(Path(d))
    test_list_demango_rows_filter_input_and_url()
    test_modify_popup_save_count_and_save_button()
    with tempfile.TemporaryDirectory() as d2:
        test_screenshot_step_and_save_count_grid(Path(d2))
    test_modified_confirm_click_after_popup_close()
    print("PASS P3_필터_갱신 tests")
