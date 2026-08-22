"""P1_필터단위_마진정책적용 단위테스트."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apply_policy import (  # noqa: E402
    click_apply_confirm_in_row,
    list_checked_policy_rows,
    select_policy_in_row,
)

POLICY_LIST_HTML = """
<html><body>
<table>
<tr>
  <th><input type="checkbox" id="all"></th>
  <th>사이트</th>
  <th>정책명</th>
  <th>적용</th>
</tr>
<tr>
  <td><input type="checkbox" checked></td>
  <td>Zara</td>
  <td>
    <select id="pol-1">
      <option value="a">기본정책</option>
      <option value="b" selected>할인정책A</option>
    </select>
  </td>
  <td><button type="button" id="apply-1" onclick="document.body.setAttribute('data-applied','1')">적용확인</button></td>
</tr>
<tr>
  <td><input type="checkbox"></td>
  <td>무신사</td>
  <td>
    <select id="pol-2">
      <option>기본정책</option>
      <option>할인정책A</option>
    </select>
  </td>
  <td><button type="button">적용확인</button></td>
</tr>
<tr>
  <td><input type="checkbox" checked></td>
  <td>ABC</td>
  <td>
    <select id="pol-3">
      <option>기본정책</option>
      <option>할인정책A</option>
      <option>프로모션B</option>
    </select>
  </td>
  <td><input type="button" id="apply-3" value="적용확인" onclick="document.body.setAttribute('data-applied','3')"></td>
</tr>
</table>
</body></html>
"""


def test_list_checked_policy_rows_only_checked():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(POLICY_LIST_HTML)
        rows = list_checked_policy_rows(page)
        browser.close()
    assert len(rows) == 2
    assert rows[0].key == 0
    assert rows[1].key == 1
    assert "할인정책A" in [o["text"] for o in rows[0].options]


def test_select_policy_and_apply_confirm():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(POLICY_LIST_HTML)
        sel = select_policy_in_row(page, 1, "할인정책A")
        assert sel["ok"] is True
        assert sel["selected"] == "할인정책A"
        click = click_apply_confirm_in_row(page, 1)
        assert click["ok"] is True
        applied = page.evaluate("() => document.body.getAttribute('data-applied')")
        browser.close()
    assert applied == "3"


def test_select_policy_not_found():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(POLICY_LIST_HTML)
        sel = select_policy_in_row(page, 0, "없는정책")
        browser.close()
    assert sel["ok"] is False
