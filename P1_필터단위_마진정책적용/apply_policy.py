"""
P1_필터단위_마진정책적용 — 더망고 정책적용 목록(체크된 행만) 순차 갱신.

1) 필터단위 마진정책 목록에서 체크된 행만 읽음
2) 각 행의 정책명 리스트박스(select)에서 입력 정책명과 일치하는 항목 선택
3) 해당 행의 「적용확인」 클릭

사용법:
  python apply_policy.py --policy-name "정책이름"
  python apply_policy.py --policy-name "정책이름" --mango-url "https://..."
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
P2_DIR = ROOT / "P2"
if str(P2_DIR) not in sys.path:
    sys.path.insert(0, str(P2_DIR))

STOP_FLAG_PATH = Path(__file__).resolve().parent / ".policy_stop"
RUN_LOG_DIR = Path(__file__).resolve().parent / "run-logs"

ProgressFn = Callable[[str], None]

# 필터단위 마진정책 목록 화면 — 비우면 브라우저 현재 탭 사용
DEFAULT_MANGO_URL = ""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


LIST_CHECKED_POLICY_ROWS_JS = r"""() => {
  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const isApplyBtn = (el) => {
    const t = norm(el.value || el.textContent || el.innerText || '');
    return t === '적용확인' || /^적용\s*확인$/.test(t);
  };
  const out = [];
  let seq = 0;
  const trs = Array.from(document.querySelectorAll('table tr, form tr, tbody tr, tr'));
  for (let i = 0; i < trs.length; i++) {
    const tr = trs[i];
    const cb = tr.querySelector('input[type="checkbox"]');
    if (!cb || !cb.checked) continue;
    const selects = Array.from(tr.querySelectorAll('select'));
    if (!selects.length) continue;
    let policySel = selects.find(s => s.options && s.options.length > 1) || selects[0];
    let applyEl = null;
    for (const el of tr.querySelectorAll(
      'a, button, input[type="button"], input[type="submit"], span, label, div'
    )) {
      if (isApplyBtn(el)) { applyEl = el; break; }
    }
    if (!applyEl) continue;
    const options = Array.from(policySel.options).map((o, idx) => ({
      index: idx,
      value: o.value,
      text: norm(o.text)
    }));
    out.push({
      key: seq++,
      trIndex: i,
      rowLabel: norm(tr.innerText).slice(0, 120),
      options,
      selectId: policySel.id || '',
      selectName: policySel.name || '',
      applyId: applyEl.id || '',
      applyTag: (applyEl.tagName || '').toUpperCase()
    });
  }
  return out;
}"""

SELECT_POLICY_IN_ROW_JS = r"""({ key, policyName }) => {
  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const want = norm(policyName);
  let seq = 0;
  const trs = Array.from(document.querySelectorAll('table tr, form tr, tbody tr, tr'));
  for (let i = 0; i < trs.length; i++) {
    const tr = trs[i];
    const cb = tr.querySelector('input[type="checkbox"]');
    if (!cb || !cb.checked) continue;
    const selects = Array.from(tr.querySelectorAll('select'));
    if (!selects.length) continue;
    let policySel = selects.find(s => s.options && s.options.length > 1) || selects[0];
    let applyEl = null;
    for (const el of tr.querySelectorAll(
      'a, button, input[type="button"], input[type="submit"], span, label, div'
    )) {
      const t = norm(el.value || el.textContent || el.innerText || '');
      if (t === '적용확인' || /^적용\s*확인$/.test(t)) { applyEl = el; break; }
    }
    if (!applyEl) continue;
    if (seq !== key) { seq++; continue; }
    for (const opt of policySel.options) {
      if (norm(opt.text) === want || norm(opt.value) === want) {
        policySel.value = opt.value;
        policySel.dispatchEvent(new Event('change', { bubbles: true }));
        policySel.dispatchEvent(new Event('input', { bubbles: true }));
        return { ok: true, selected: norm(opt.text), key };
      }
    }
    return {
      ok: false,
      key,
      reason: 'policy_not_found',
      available: Array.from(policySel.options).map(o => norm(o.text))
    };
  }
  return { ok: false, reason: 'row_not_found', key };
}"""

CLICK_APPLY_CONFIRM_JS = r"""({ key }) => {
  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
  let seq = 0;
  const trs = Array.from(document.querySelectorAll('table tr, form tr, tbody tr, tr'));
  for (let i = 0; i < trs.length; i++) {
    const tr = trs[i];
    const cb = tr.querySelector('input[type="checkbox"]');
    if (!cb || !cb.checked) continue;
    const selects = Array.from(tr.querySelectorAll('select'));
    if (!selects.length) continue;
    let applyEl = null;
    for (const el of tr.querySelectorAll(
      'a, button, input[type="button"], input[type="submit"], span, label, div'
    )) {
      const t = norm(el.value || el.textContent || el.innerText || '');
      if (t === '적용확인' || /^적용\s*확인$/.test(t)) { applyEl = el; break; }
    }
    if (!applyEl) continue;
    if (seq !== key) { seq++; continue; }
    applyEl.click();
    return { ok: true, key };
  }
  return { ok: false, reason: 'row_not_found', key };
}"""


@dataclass
class PolicyRow:
    key: int
    tr_index: int
    row_label: str
    options: list[dict]


@dataclass
class RunResult:
    ok: bool
    total_checked: int = 0
    updated: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def clear_stop_flag() -> None:
    try:
        STOP_FLAG_PATH.unlink(missing_ok=True)  # type: ignore[call-arg]
    except Exception:
        pass


def stop_requested() -> bool:
    return STOP_FLAG_PATH.is_file()


def _log(progress: ProgressFn | None, message: str, *, major: bool = False) -> None:
    line = message if message else ""
    if major:
        line = f"##MAIN##{line}"
    print(line, flush=True)
    if progress:
        progress(line)


def list_checked_policy_rows(page) -> list[PolicyRow]:
    raw = page.evaluate(LIST_CHECKED_POLICY_ROWS_JS) or []
    rows: list[PolicyRow] = []
    for item in raw:
        rows.append(
            PolicyRow(
                key=int(item.get("key", 0)),
                tr_index=int(item.get("trIndex", 0)),
                row_label=str(item.get("rowLabel") or ""),
                options=list(item.get("options") or []),
            )
        )
    return rows


def select_policy_in_row(page, row_key: int, policy_name: str) -> dict:
    return page.evaluate(SELECT_POLICY_IN_ROW_JS, {"key": row_key, "policyName": policy_name})


def click_apply_confirm_in_row(page, row_key: int) -> dict:
    return page.evaluate(CLICK_APPLY_CONFIRM_JS, {"key": row_key})


def policy_names_available(row: PolicyRow) -> list[str]:
    return [str(o.get("text") or "") for o in row.options if o.get("text")]


def navigate_mango_url(page, mango_url: str, *, p2) -> None:
    url = (mango_url or "").strip()
    if not url:
        return
    if p2 is not None and hasattr(p2, "safe_goto"):
        p2.safe_goto(page, url)
        if hasattr(p2, "refresh_if_closed"):
            page = p2.refresh_if_closed(page)
    else:
        page.goto(url, wait_until="domcontentloaded", timeout=90_000)
    time.sleep(0.3)


def run_apply_policy(
    policy_name: str,
    *,
    mango_url: str = "",
    progress: ProgressFn | None = None,
) -> RunResult:
    policy_name = _norm(policy_name)
    if not policy_name:
        return RunResult(ok=False, errors=["정책명이 비어 있습니다."])

    result = RunResult(ok=False)
    clear_stop_flag()

    try:
        import collect as p2  # noqa: WPS433
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        result.errors.append(f"의존성 로드 실패: {e}")
        _log(progress, result.errors[0], major=True)
        return result

    _log(progress, f"정책명: {policy_name}", major=True)

    try:
        with sync_playwright() as pw:
            _browser, page = p2.connect_browser(pw)
            navigate_mango_url(page, mango_url, p2=p2)
            _log(progress, f"현재 화면: {(page.url or '')[:160]}")

            rows = list_checked_policy_rows(page)
            result.total_checked = len(rows)
            if not rows:
                result.errors.append("체크된 필터단위 마진정책 행이 없습니다.")
                _log(progress, result.errors[0], major=True)
                return result

            _log(progress, f"체크된 행 {len(rows)}건 — 순차 적용 시작", major=True)

            for i, row in enumerate(rows, start=1):
                if stop_requested():
                    _log(progress, "사용자 중단", major=True)
                    break

                _log(
                    progress,
                    f"{i}/{len(rows)} 행 처리 · key={row.key} · {row.row_label[:60]}",
                    major=True,
                )

                sel = select_policy_in_row(page, row.key, policy_name)
                if not sel.get("ok"):
                    result.failed += 1
                    avail = sel.get("available") or policy_names_available(row)
                    msg = (
                        f"정책명 일치 없음 — 입력={policy_name!r} "
                        f"선택지={avail!r}"
                    )
                    result.errors.append(msg)
                    _log(progress, msg, major=True)
                    continue

                _log(progress, f"  정책 선택: {sel.get('selected')}")

                click = click_apply_confirm_in_row(page, row.key)
                if not click.get("ok"):
                    result.failed += 1
                    msg = f"적용확인 클릭 실패 — key={row.key}"
                    result.errors.append(msg)
                    _log(progress, msg, major=True)
                    continue

                result.updated += 1
                _log(progress, f"  적용확인 완료", major=True)
                time.sleep(0.4)

    except Exception as e:  # noqa: BLE001
        result.errors.append(str(e))
        _log(progress, f"실행 오류: {e}", major=True)
        return result

    clear_stop_flag()
    result.ok = result.updated > 0 and result.failed == 0 and not result.errors
    _log(
        progress,
        f"완료 — 성공 {result.updated} · 실패 {result.failed} / 체크 {result.total_checked}",
        major=True,
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P1_필터단위_마진정책적용 — 체크된 행에 정책명 일괄 적용")
    parser.add_argument("--policy-name", required=True, help="적용할 정책명")
    parser.add_argument(
        "--mango-url",
        default=DEFAULT_MANGO_URL,
        help="필터단위 마진정책 목록 URL (비우면 현재 브라우저 화면 사용)",
    )
    args = parser.parse_args(argv)
    result = run_apply_policy(args.policy_name, mango_url=args.mango_url)
    if result.errors:
        for e in result.errors:
            print(f"[오류] {e}", flush=True)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
