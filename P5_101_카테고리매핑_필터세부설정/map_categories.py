"""
P5_101_카테고리매핑_필터세부설정 — 필터별 마켓 카테고리 자동 매핑.

초기 1회
  1) 상품수집사이트 선택 (`select[name="site_id"]`)
  2) [선택조건으로 검색하기] (`onclick="search_filter('search')"`)
  3) 마켓별 카테고리 엑셀 읽어 메모리 보관 (P5 추출 결과 양식)

1단계 루프 — 체크된 행마다
  0) 행 정보 읽기 (체크박스 · 필터이름 · ftid)
  1) 필터이름(수정가능) 읽기
  2~3) 필터세부설정 열의 [설정수정] (`onclick="market_mapping_new('<ftid>')"`)
  4) 팝업 `admin_category_set.php?tm=F&ps_ftid=<ftid>`
  5) [AI 자동 매핑 시작하기] (`onclick="search_recommend_category_all(this)"`)
  6) 2단계 루프 — 마켓마다
       필터이름 ↔ 엑셀 카테고리 비교 → 최적 카테고리
       → 검색필드 입력 (`#openmarket_category_search_text_<코드>`)
       → [검색] (`search_category('<코드>','openmarket_category_search_list_<코드>','')`)
       → 결과 목록에서 일치 항목 선택 (`#openmarket_category_search_list_<코드>`)
  7) [검색필터 설정저장 (Alt+S)] (`onclick="config_save()"`)
  8) 모달 닫기 → 9) 다음 행

사용법:
  python map_categories.py --excel-dir D:\\카테고리엑셀
  python map_categories.py --site-id abcmart --excel AUC20=D:\\옥션.xlsx --excel 11ST=D:\\11번가.xlsx
  python map_categories.py --dry-run          # 화면 조작 없이 매칭 결과만 출력
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
P2_DIR = ROOT / "P2"
P5_DIR = ROOT / "P5_카테고리_엑셀추출"
for _p in (P2_DIR, P5_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matching  # noqa: E402

ProgressFn = Callable[[str], None]

HERE = Path(__file__).resolve().parent
STOP_FLAG_PATH = HERE / ".map_stop"

DEFAULT_LIST_URL = (
    "https://tmg1898.cafe24.com/mall/admin/admin_group.php"
    "?pmode=filter_delete&uids=&pg=1&date_type=modify"
    "&start_yy=2026&start_mm=8&start_dd=22&end_yy=2026&end_mm=8&end_dd=22"
    "&site_id=&sales_yn=&ft_group=all&sch_field=title&sch_keyword="
    "&ft_num=10&ft_sort=modify_asc"
)
CATEGORY_PAGE = "admin_category_set.php"

# 매핑 대상 마켓 (P5 추출 대상과 동일)
MARKETS: dict[str, str] = {
    "AUC20": "옥션2.0",
    "11ST": "11번가",
    "GMK20": "G마켓2.0",
    "SMART": "스마트스토어",
    "COUP": "쿠팡",
    "LTON": "롯데ON",
}

# 화면 선택자 (스크린샷 기준)
SEARCH_FILTER_JS = "search_filter('search')"
SETTING_EDIT_JS = "market_mapping_new"
AI_MAPPING_JS = "search_recommend_category_all"
CONFIG_SAVE_JS = "config_save"

T_CLICK = 3_000
T_FIELD = 5_000
T_LIST = 8_000
GAP = 0.15

MIN_SCORE = 0.34  # 이 점수 미만이면 매칭 실패로 본다

# ★요건(2026-08-22): 검증 전까지 무신사에 한해 수행
ALLOWED_SITES = ("musinsa.com",)
DEFAULT_SITE = "MUSINSA.com"

# ★요건: 마켓별 카테고리 구분 라디오 (스크린샷 3·4)
#   <input type="radio" name="openmarket_seller_type2_<코드>"
#     onclick="change_category_list(...,'<코드>', this);"><span>해외직구 카테고리</span>
VARIANT_RADIO_NAME = "openmarket_seller_type2_{market}"
MARKET_VARIANTS: dict[str, tuple[str, ...]] = {
    "11ST": ("해외카테고리", "국내카테고리"),
    "LTON": ("해외직구 카테고리", "일반카테고리"),
}
BOTH = "둘다"  # 두 구분 모두 매핑

# 상품고시정보 팝업 — show_hide('#mapping_notify_<코드>')
NOTIFY_ID = "mapping_notify_{market}"
NOTIFY_RETRIES = 3  # 상품고시정보 팝업이 계속 뜨면 다른 카테고리로 재시도하는 횟수
MAP_RETRIES = 3  # ★요건: 매핑 실패 시 다른 카테고리로 최대 3회 추가 시도
VERIFY_ROUNDS = 3  # ★요건: 저장 후 재검증 — 미매핑 마켓이 있으면 최대 3회 재시도

# ★요건: 작업 행 범위 — <작업 시작 부터> ~ <작업 종료 까지> (1부터, 양끝 포함)
DEFAULT_ROW_FROM = 1
DEFAULT_ROW_TO = 5


@dataclass
class RowInfo:
    index: int
    ftid: str
    filter_name: str
    checked: bool = True


@dataclass
class MappedItem:
    market: str
    category: str
    score: float
    ok: bool = False
    reason: str = ""


@dataclass
class RunResult:
    ok: bool
    rows: int = 0
    mapped: int = 0
    failed: int = 0
    details: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def normalize_site(site: str) -> str:
    return "".join(str(site or "").split()).lower()


def is_allowed_site(site: str) -> bool:
    """무신사만 허용 (다른 사이트는 검증 완료 후 개방)."""
    s = normalize_site(site)
    if not s:
        return False
    return any(allowed in s for allowed in ALLOWED_SITES)


def row_range(row_from: int | str = DEFAULT_ROW_FROM, row_to: int | str = DEFAULT_ROW_TO) -> tuple[int, int]:
    """작업 행 범위 정리 — 1 이상, 시작 ≤ 종료."""

    def _int(value, default: int) -> int:
        try:
            n = int(str(value).strip())
        except (TypeError, ValueError):
            return default
        return n if n > 0 else default

    start = _int(row_from, DEFAULT_ROW_FROM)
    end = _int(row_to, DEFAULT_ROW_TO)
    if end < start:
        start, end = end, start
    return start, end


def slice_rows(rows: Sequence, row_from: int | str, row_to: int | str) -> list:
    """작업 범위에 해당하는 행만 (1부터 세고 양끝 포함)."""
    start, end = row_range(row_from, row_to)
    return list(rows)[start - 1 : end]


def clear_stop_flag() -> None:
    try:
        STOP_FLAG_PATH.unlink(missing_ok=True)  # type: ignore[call-arg]
    except Exception:
        pass


def stop_requested() -> bool:
    return STOP_FLAG_PATH.is_file()


def _log(progress: ProgressFn | None, message: str, *, major: bool = False) -> None:
    line = f"##MAIN##{message}" if major else message
    print(line, flush=True)
    if progress:
        progress(line)


# ── 엑셀 카테고리 자료 (초기 1회 · 메모리 보관) ────────────────────


def market_from_filename(name: str) -> str:
    """파일명에서 마켓 코드 추정 (P5 출력: 카테고리분류표_옥션2.0_....xlsx)."""
    text = str(name)
    for code, label in MARKETS.items():
        if code.lower() in text.lower() or label in text:
            return code
    return ""


def load_categories(path: str | Path) -> list[str]:
    """엑셀에서 카테고리 전체경로 목록을 읽는다.

    P5 추출 양식(마켓·구분·1~6단계·전체경로) 우선, 없으면 단계 열을 이어 붙이거나
    첫 열을 그대로 쓴다.
    """
    from openpyxl import load_workbook  # noqa: WPS433

    wb = load_workbook(str(path), read_only=True, data_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    try:
        header = [str(c or "").strip() for c in next(rows)]
    except StopIteration:
        return []

    full_idx = header.index("전체경로") if "전체경로" in header else -1
    level_idx = [i for i, h in enumerate(header) if re.fullmatch(r"\d단계", h)]

    out: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if row is None:
            continue
        if full_idx >= 0 and full_idx < len(row) and row[full_idx]:
            path_text = str(row[full_idx]).strip()
        elif level_idx:
            parts = [str(row[i]).strip() for i in level_idx if i < len(row) and row[i]]
            path_text = " > ".join(parts)
        else:
            path_text = str(row[0]).strip() if row and row[0] else ""
        if not path_text or path_text in seen:
            continue
        seen.add(path_text)
        out.append(path_text)
    return out


def load_market_excels(
    paths: dict[str, str | Path], *, progress: ProgressFn | None = None
) -> dict[str, list[str]]:
    """마켓 코드 → 카테고리 목록."""
    data: dict[str, list[str]] = {}
    for code, path in paths.items():
        code = code.strip().upper()
        if not path:
            continue
        try:
            cats = load_categories(path)
        except Exception as e:  # noqa: BLE001
            _log(progress, f"엑셀 읽기 실패 · {code} · {e}", major=True)
            continue
        data[code] = cats
        _log(progress, f"  {MARKETS.get(code, code)} 카테고리 {len(cats)}건 로드", major=True)
    return data


def discover_market_excels(folder: str | Path) -> dict[str, str]:
    """폴더에서 마켓별 엑셀을 파일명으로 자동 매칭."""
    found: dict[str, str] = {}
    for p in sorted(Path(folder).glob("*.xlsx")):
        code = market_from_filename(p.name)
        if code and code not in found:
            found[code] = str(p)
    return found


# ── 필터이름 ↔ 카테고리 매칭 (순수 로직) ──────────────────────────

_SPLIT_RE = re.compile(r"[\s_\-/>·,()\[\]]+")


def tokenize(text: str) -> list[str]:
    """비교용 토큰 — 구분자·공백 제거, 소문자화."""
    raw = _SPLIT_RE.split(str(text or "").strip().lower())
    return [t for t in raw if t]


def leaf_of(path: str) -> str:
    parts = [p.strip() for p in str(path or "").split(">") if p.strip()]
    return parts[-1] if parts else ""


def similarity(filter_name: str, category_path: str) -> float:
    """필터이름과 카테고리 경로의 유사도 (0~1).

    마지막 단계(리프)에 가중치를 두고, 경로 전체 토큰 겹침도 함께 본다.
    """
    ftoks = set(tokenize(filter_name))
    if not ftoks:
        return 0.0
    path_toks = set(tokenize(category_path))
    leaf_toks = set(tokenize(leaf_of(category_path)))
    if not path_toks:
        return 0.0

    path_hit = len(ftoks & path_toks) / len(ftoks)
    leaf_hit = len(ftoks & leaf_toks) / len(ftoks) if leaf_toks else 0.0

    # 문자열 포함 보너스 (예: '남성비니' ↔ '비니')
    joined_f = "".join(sorted(ftoks))
    bonus = 0.0
    for tok in leaf_toks:
        if tok and (tok in joined_f or any(tok in f or f in tok for f in ftoks)):
            bonus = max(bonus, 0.25)
    return min(1.0, 0.5 * path_hit + 0.5 * leaf_hit + bonus)


def similarity_best(
    filter_name: str, categories: Sequence[str], *, min_score: float = MIN_SCORE
) -> tuple[str, float]:
    """토큰 유사도만으로 고르는 보조 경로 (결과 목록 선택 등)."""
    best = ""
    best_score = 0.0
    for cat in categories:
        score = similarity(filter_name, cat)
        if score > best_score or (score == best_score and cat and len(cat) < len(best)):
            best, best_score = cat, score
    if best_score < min_score:
        return "", best_score
    return best, best_score


def best_category(
    filter_name: str, categories: Sequence[str], *, min_score: float = MIN_SCORE
) -> tuple[str, float]:
    """★요건 순서(matching.find_category)로 최적 카테고리를 고른다.

    1) 단계 일치 → 2-1) 상위→중위→하위 → 2-2) 중위 전체 → 2-3) 하위 전체
    → 2-4) 품목별 포괄. 못 찾으면 유사도 폴백.
    """
    cat, _step = matching.find_category(filter_name, list(categories))
    if cat:
        return cat, 1.0
    return similarity_best(filter_name, categories, min_score=min_score)


def best_category_with_step(
    filter_name: str, categories: Sequence[str], *, exclude: Sequence[str] = ()
) -> tuple[str, str]:
    """최적 카테고리 + 어느 단계에서 찾았는지 (exclude 는 이미 시도한 것)."""
    cat, step = matching.find_category(filter_name, list(categories), exclude=exclude)
    if cat:
        return cat, step
    skip = {matching.normalize(e) for e in exclude or []}
    rest = [c for c in categories if matching.normalize(c) not in skip]
    cat, score = similarity_best(filter_name, rest)
    return cat, (f"유사도 {score:.2f}" if cat else "미검출")


def search_keyword_for(category_path: str) -> str:
    """카테고리 검색필드에 넣을 검색어 — 마지막 단계."""
    return leaf_of(category_path)


def gender_safe_options(options: Sequence[str], filter_name: str) -> list[str]:
    """★검색 결과에도 성별 규칙을 적용한다.

    검색어는 카테고리의 마지막 단계(예 `로퍼`) 뿐이라, 망고는 `남성신발 > 로퍼` 와
    `여성신발 > 로퍼` 를 함께 돌려준다. 성별을 보지 않으면 목록에 먼저 나온 반대 성별
    항목이 뽑히므로, 여기서 반대 성별을 걷어내고 같은 성별을 우선한다.
    반대 성별만 남으면 빈 목록을 돌려 매핑하지 않게 한다.
    """
    pool = [o for o in options if str(o or "").strip()]
    gender = matching.gender_of(filter_name)
    if not gender:
        return pool
    safe = matching.strip_opposite_gender(pool, gender)
    if not safe:
        return []
    same = [o for o in safe if matching.has_gender(o, gender)]
    return same or safe


def pick_option(
    options: Sequence[str], category_path: str, filter_name: str = ""
) -> str:
    """검색 결과 목록에서 고를 항목 — 완전일치 → 리프일치 → 최고 유사도.

    `filter_name` 을 주면 반대 성별 항목을 먼저 걷어낸 뒤 고른다.
    """
    target = str(category_path or "").strip()
    if not target:
        return ""
    pool = gender_safe_options(options, filter_name) if filter_name else list(options)
    if not pool:
        return ""
    norm = lambda s: "".join(str(s or "").split())  # noqa: E731
    for opt in pool:
        if norm(opt) == norm(target):
            return opt
    leaf = leaf_of(target)
    for opt in pool:
        if leaf and norm(leaf_of(opt)) == norm(leaf):
            return opt
    best, score = similarity_best(target, list(pool), min_score=0.0)
    return best if score > 0 else ""


# ── 화면 조작 ────────────────────────────────────────────────────


def _first(page, selectors: Iterable[str]):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                return loc
        except Exception:
            continue
    return None


SITE_OPTIONS_JS = "(el) => Array.from(el.options).map(o => (o.textContent || '').trim())"


def _norm_site(text: str) -> str:
    """사이트명 비교용 — 공백 제거 + 소문자."""
    return "".join(str(text or "").split()).lower()


def match_site_option(options: Sequence[str], wanted: str) -> str | None:
    """입력한 사이트명을 실제 옵션에 맞춘다.

    정확 일치 → 대소문자·공백 무시 → 부분 포함. `MUSINSA.COM` 처럼 대소문자가
    다르게 입력돼도 `MUSINSA.com` 옵션을 찾아낸다.
    """
    want = str(wanted or "").strip()
    if not want:
        return None
    for opt in options:
        if opt == want:
            return opt
    nw = _norm_site(want)
    for opt in options:
        if _norm_site(opt) == nw:
            return opt
    for opt in options:
        no = _norm_site(opt)
        if nw and no and (nw in no or no in nw):
            return opt
    return None


def read_site_options(page) -> list[str]:
    """상품수집사이트 드롭다운의 옵션 텍스트 목록."""
    loc = _first(page, ('select[name="site_id"]',))
    if loc is None:
        return []
    try:
        raw = loc.evaluate(SITE_OPTIONS_JS) or []
    except Exception:
        return []
    return [str(t).strip() for t in raw if str(t).strip()]


def select_site(page, site_id: str, *, progress: ProgressFn | None = None) -> bool:
    """상품수집사이트 리스트박스 선택 (초기 1회)."""
    if not site_id:
        return True
    loc = _first(page, ('select[name="site_id"]',))
    if loc is None:
        _log(progress, "오류: 상품수집사이트 드롭다운 미검출", major=True)
        return False

    options = read_site_options(page)
    target = match_site_option(options, site_id) if options else site_id
    if target is None:
        _log(
            progress,
            f"오류: 상품수집사이트 미검출 · 입력={site_id} · 화면목록={options}",
            major=True,
        )
        return False

    for how in ("label", "value"):
        try:
            if how == "label":
                loc.select_option(label=target, timeout=T_CLICK)
            else:
                loc.select_option(target, timeout=T_CLICK)
            note = "" if target == site_id else f" (입력 {site_id} → 화면 {target})"
            _log(progress, f"상품수집사이트: {target}{note}", major=True)
            return True
        except Exception:
            continue
    _log(
        progress,
        f"오류: 상품수집사이트 선택 실패 · {target} · 화면목록={options}",
        major=True,
    )
    return False


def click_search_filter(page, *, progress: ProgressFn | None = None) -> bool:
    """[선택조건으로 검색하기]."""
    loc = _first(
        page,
        (
            f'a[onclick*="{SEARCH_FILTER_JS}"]',
            'xpath=//a[.//span[contains(normalize-space(.),"선택조건으로 검색하기")]]',
            'xpath=//*[contains(normalize-space(.),"선택조건으로 검색하기")]',
        ),
    )
    if loc is None:
        _log(progress, "오류: [선택조건으로 검색하기] 미검출", major=True)
        return False
    try:
        loc.click(timeout=T_CLICK)
    except Exception as e:  # noqa: BLE001
        _log(progress, f"오류: 검색 클릭 실패 · {e}", major=True)
        return False
    _log(progress, "[선택조건으로 검색하기] 클릭", major=True)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=T_FIELD)
    except Exception:
        pass
    time.sleep(GAP)
    return True


LIST_ROWS_JS = r"""
() => {
  // 표 구조에 기대지 않고 행을 찾는다.
  // 1순위 [설정수정] 링크 → 2순위 ps_ftid 를 품은 요소 → 3순위 attr-uid / id="td_<ftid>"
  const nameOf = (tr, ftid) => {
    let name = '';
    if (tr) {
      const vals = Array.from(tr.querySelectorAll('input[type="text"], input:not([type])'))
        .map(i => (i.value || i.getAttribute('value') || '').trim())
        .filter(v => v && !/^https?:/i.test(v) && !/^\d+$/.test(v));
      if (vals.length) name = vals[0];
    }
    if (!name && ftid) {
      const byUid = document.querySelector('input[attr-uid="' + ftid + '"]');
      if (byUid) name = (byUid.value || byUid.getAttribute('value') || '').trim();
    }
    if (!name && tr) name = ((tr.innerText || '').trim().split('\n')[0] || '').trim();
    return name;
  };
  const checkedOf = (tr) => {
    if (!tr) return false;
    const cb = tr.querySelector('input[type="checkbox"]');
    return cb ? !!cb.checked : false;
  };

  const collect = (pairs) => {
    // pairs: [ftid, 기준 element]
    const seen = new Set();
    const out = [];
    for (const [ftid, el] of pairs) {
      if (!ftid || seen.has(ftid)) continue;
      seen.add(ftid);
      const tr = el && el.closest ? el.closest('tr') : null;
      out.push({
        index: out.length,
        ftid: ftid,
        filterName: nameOf(tr, ftid),
        checked: checkedOf(tr),
      });
    }
    return out;
  };

  // 1) [설정수정] 링크
  let pairs = [];
  for (const a of Array.from(document.querySelectorAll('a[onclick*="market_mapping_new"]'))) {
    const m = (a.getAttribute('onclick') || '').match(/market_mapping_new\(\s*'?(\d+)'?/);
    if (m) pairs.push([m[1], a]);
  }
  let rows = collect(pairs);
  if (rows.length) return rows;

  // 2) onclick·href 에 ps_ftid 또는 market_mapping 계열이 있는 요소
  pairs = [];
  for (const el of Array.from(document.querySelectorAll('a, button, input, td'))) {
    const src = (el.getAttribute('onclick') || '') + ' '
      + (el.getAttribute('href') || '') + ' ' + (el.href || '');
    if (!src.trim()) continue;
    const m = src.match(/ps_ftid=(\d+)/)
      || src.match(/market_mapping[a-z_]*\(\s*'?(\d+)'?/i);
    if (m) pairs.push([m[1], el]);
  }
  rows = collect(pairs);
  if (rows.length) return rows;

  // 3) 필터명 input 의 attr-uid · td 의 id="td_<ftid>"
  pairs = [];
  for (const inp of Array.from(document.querySelectorAll('input[attr-uid]'))) {
    const uid = (inp.getAttribute('attr-uid') || '').trim();
    if (/^\d+$/.test(uid)) pairs.push([uid, inp]);
  }
  for (const td of Array.from(document.querySelectorAll('td[id^="td_"]'))) {
    const m = (td.getAttribute('id') || '').match(/^td_(\d+)$/);
    if (m) pairs.push([m[1], td]);
  }
  return collect(pairs);
}
"""


LIST_DIAG_JS = r"""
() => {
  const anchors = Array.from(document.querySelectorAll('a[onclick]'));
  const mapping = anchors.filter(a => (a.getAttribute('onclick') || '').includes('market_mapping_new'));
  // 화면이 실제로 쓰는 함수명·행 식별자를 그대로 뽑아낸다 (추측 없이 고치기 위해)
  const fns = new Set();
  for (const el of Array.from(document.querySelectorAll('[onclick]'))) {
    const m = (el.getAttribute('onclick') || '').match(/([A-Za-z_][A-Za-z0-9_]*)\s*\(/g);
    if (m) m.forEach(x => fns.add(x.replace(/\s*\($/, '')));
  }
  const tables = Array.from(document.querySelectorAll('table'))
    .map(t => t.id || '').filter(Boolean);
  return {
    url: location.href,
    table: !!document.querySelector('table#search_category'),
    rows: document.querySelectorAll('tr').length,
    checkboxes: document.querySelectorAll('input[type="checkbox"]').length,
    mappingLinks: mapping.length,
    sample: mapping.slice(0, 3).map(a => (a.getAttribute('onclick') || '').slice(0, 60)),
    attrUid: document.querySelectorAll('input[attr-uid]').length,
    tdIds: document.querySelectorAll('td[id^="td_"]').length,
    ftidLinks: Array.from(document.querySelectorAll('a,button,input,td'))
      .filter(el => /ps_ftid=\d+/.test((el.getAttribute('onclick') || '')
        + (el.getAttribute('href') || ''))).length,
    tableIds: tables.slice(0, 8),
    onclickFns: Array.from(fns).slice(0, 24),
  };
}
"""


def contexts(page) -> list:
    """페이지 + 프레임 (목록이 프레임 안에 있을 수 있다)."""
    out = [page]
    try:
        for f in page.frames:
            if f is not page and f not in out:
                out.append(f)
    except Exception:
        pass
    return out


def diagnose_list(page, *, progress: ProgressFn | None = None) -> None:
    """행을 못 찾을 때 화면 상태를 로그로 남긴다."""
    for i, ctx in enumerate(contexts(page), start=1):
        try:
            info = ctx.evaluate(LIST_DIAG_JS)
        except Exception as e:  # noqa: BLE001
            _log(progress, f"  [진단] 프레임{i}: 읽기 실패 ({e})", major=True)
            continue
        _log(
            progress,
            f"  [진단] 프레임{i} tr={info.get('rows')}"
            f" · 체크박스={info.get('checkboxes')}"
            f" · 설정수정링크={info.get('mappingLinks')}"
            f" · search_category={info.get('table')}"
            f" · 예시={info.get('sample')}",
            major=True,
        )
        # URL 은 잘리면 원인 파악이 안 되므로 통째로 남긴다
        _log(progress, f"  [진단] 프레임{i} url={info.get('url')}", major=True)
        # 행 식별자 후보 — 어느 폴백으로 잡아야 하는지 바로 보이게
        _log(
            progress,
            f"  [진단] 프레임{i} attr-uid={info.get('attrUid')}"
            f" · td_id={info.get('tdIds')}"
            f" · ps_ftid={info.get('ftidLinks')}"
            f" · table id={info.get('tableIds')}",
            major=True,
        )
        _log(progress, f"  [진단] 프레임{i} onclick 함수={info.get('onclickFns')}", major=True)
        if int(info.get("rows") or 0) == 0 and not info.get("table"):
            _log(
                progress,
                "  [진단] 이 화면에는 목록 표가 아예 없습니다 — 「작업 URL」 이"
                " 검색필터 목록 화면이 맞는지 확인하세요."
                " 브라우저 주소창의 목록 화면 URL 을 그대로 붙여넣으면 됩니다.",
                major=True,
            )

    options = read_site_options(page)
    if options:
        _log(progress, f"  [진단] 상품수집사이트 옵션={options}", major=True)


def list_rows(page) -> list[RowInfo]:
    """모든 프레임에서 행을 모으고 ftid 중복은 제거한다."""
    data: list[dict] = []
    seen: set[str] = set()
    for ctx in contexts(page):
        try:
            found = ctx.evaluate(LIST_ROWS_JS) or []
        except Exception:
            found = []
        for item in found:
            ftid = str((item or {}).get("ftid") or "").strip()
            if not ftid or ftid in seen:
                continue
            seen.add(ftid)
            data.append(item)
    rows: list[RowInfo] = []
    for d in data:
        rows.append(
            RowInfo(
                index=int(d.get("index") or 0),
                ftid=str(d.get("ftid") or "").strip(),
                filter_name=str(d.get("filterName") or "").strip(),
                checked=bool(d.get("checked")),
            )
        )
    return rows


def build_mapping_url(ftid: str, *, list_url: str = DEFAULT_LIST_URL) -> str:
    """설정수정 팝업 URL (`admin_category_set.php?tm=F&ps_ftid=<ftid>`)."""
    from urllib.parse import urlencode, urlsplit, urlunsplit

    parts = urlsplit(list_url or DEFAULT_LIST_URL)
    base_dir = parts.path.rsplit("/", 1)[0] if "/" in parts.path else ""
    query = urlencode({"tm": "F", "ps_ftid": str(ftid)})
    return urlunsplit((parts.scheme, parts.netloc, f"{base_dir}/{CATEGORY_PAGE}", query, ""))


def open_setting_popup(page, row: RowInfo, *, list_url: str, progress: ProgressFn | None = None):
    """행의 [설정수정] → 팝업. 실패 시 팝업 URL 직접 오픈."""
    sel = f"a[onclick*=\"{SETTING_EDIT_JS}('{row.ftid}')\"]"
    try:
        with page.expect_popup(timeout=T_FIELD) as info:
            page.locator(sel).first.click(timeout=T_CLICK)
        popup = info.value
        _log(progress, f"  설정수정 팝업 (ftid={row.ftid})")
        return popup
    except Exception:
        pass

    url = build_mapping_url(row.ftid, list_url=list_url)
    try:
        popup = page.context.new_page()
        popup.goto(url, wait_until="domcontentloaded", timeout=30_000)
        _log(progress, f"  설정수정 직접 열기 (ftid={row.ftid})")
        return popup
    except Exception as e:  # noqa: BLE001
        _log(progress, f"오류: 설정수정 팝업 실패 · {e}", major=True)
        return None


def click_ai_mapping(popup, *, progress: ProgressFn | None = None) -> bool:
    """[AI 자동 매핑 시작하기]."""
    loc = _first(
        popup,
        (
            f'a[onclick*="{AI_MAPPING_JS}"]',
            'xpath=//a[.//span[contains(normalize-space(.),"AI 자동 매핑")]]',
        ),
    )
    if loc is None:
        _log(progress, "  경고: [AI 자동 매핑 시작하기] 미검출 — 수동 매핑만 진행")
        return False
    try:
        loc.click(timeout=T_CLICK)
        _log(progress, "  AI 자동 매핑 시작")
        time.sleep(0.5)
        return True
    except Exception:
        return False


def variants_for(market: str, choice: str = "") -> list[str]:
    """이 마켓에서 매핑할 구분 목록 (구분 없는 마켓은 [''])."""
    options = MARKET_VARIANTS.get(market)
    if not options:
        return [""]
    pick = str(choice or "").strip()
    if not pick or pick == BOTH:
        return list(options)
    for opt in options:
        if normalize_site(opt) == normalize_site(pick):
            return [opt]
    return list(options)


def variant_radio_selectors(market: str, variant: str) -> tuple[str, ...]:
    name = VARIANT_RADIO_NAME.format(market=market)
    return (
        f'xpath=//label[.//span[contains(normalize-space(.),"{variant}")]]'
        f'//input[@type="radio" and @name="{name}"]',
        f'xpath=//tr[@id="mapping_category_{market}"]'
        f'//label[.//span[contains(normalize-space(.),"{variant}")]]//input[@type="radio"]',
    )


def select_variant(popup, market: str, variant: str, *, progress: ProgressFn | None = None) -> bool:
    """구분 라디오를 **클릭**해 목록을 바꾼다 (이미 체크돼 있어도 클릭)."""
    if not variant:
        return True
    loc = _first(popup, variant_radio_selectors(market, variant))
    if loc is None:
        _log(progress, f"  경고: 구분 라디오 미검출 · {variant}")
        return False
    try:
        loc.click(timeout=T_CLICK, force=True)
    except Exception:
        try:
            loc.check(timeout=T_CLICK)
        except Exception:
            return False
    _log(progress, f"  구분 선택: {variant}")
    try:
        popup.wait_for_timeout(400)
    except Exception:
        time.sleep(0.4)
    return True


NOTIFY_VISIBLE_JS = """
(id) => {
  const el = document.getElementById(id);
  if (!el) return false;
  const st = window.getComputedStyle(el);
  if (st.display === 'none' || st.visibility === 'hidden') return false;
  return (el.innerText || '').trim().length > 0;
}
"""


def notify_open(popup, market: str) -> bool:
    """상품고시정보 팝업이 떠 있는가."""
    try:
        return bool(popup.evaluate(NOTIFY_VISIBLE_JS, NOTIFY_ID.format(market=market)))
    except Exception:
        return False


def close_notify(popup, market: str, *, progress: ProgressFn | None = None) -> bool:
    """상품고시정보 팝업 닫기 — show_hide 토글 또는 닫기 버튼."""
    notify_id = NOTIFY_ID.format(market=market)
    loc = _first(
        popup,
        (
            f"a[onclick*=\"show_hide('#{notify_id}')\"]",
            f'xpath=//div[@id="{notify_id}"]//*[contains(normalize-space(.),"닫기")]',
        ),
    )
    if loc is not None:
        try:
            loc.click(timeout=T_CLICK)
            _log(progress, "  상품고시정보 팝업 닫기")
            return True
        except Exception:
            pass
    try:
        popup.evaluate(
            "(id) => { const el = document.getElementById(id); if (el) el.style.display = 'none'; }",
            notify_id,
        )
        _log(progress, "  상품고시정보 팝업 닫기(강제)")
        return True
    except Exception:
        return False


def market_search_input(popup, market: str):
    return _first(
        popup,
        (
            f"#openmarket_category_search_text_{market}",
            f'input[id="openmarket_category_search_text_{market}"]',
        ),
    )


def click_market_search(popup, market: str) -> bool:
    loc = _first(
        popup,
        (
            f"a[onclick*=\"search_category('{market}','openmarket_category_search_list_{market}',''\"]",
            f'xpath=//tr[@id="mapping_category_{market}"]'
            '//a[.//span[normalize-space()="검색"]]',
        ),
    )
    if loc is None:
        return False
    try:
        loc.click(timeout=T_CLICK)
        return True
    except Exception:
        return False


# 결과 리스트박스는 마켓에 따라 list_ / list2_ 두 벌이고 보이는 쪽이 다르다
# (11번가·롯데ON). 보이는 select 을 우선 읽고, 선택도 그 id 에 한다.
RESULT_OPTIONS_JS = """
(ids) => {
  const texts = (el) => Array.from(el.options).map(o => (o.textContent || '').trim());
  const isVisible = (el) => {
    const st = window.getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden') return false;
    return el.offsetParent !== null || st.display === 'inline-block';
  };
  const cands = ids.map(id => document.getElementById(id)).filter(Boolean);
  const pick = (list) => {
    let best = {texts: [], id: ''};
    for (const el of list) {
      const t = texts(el);
      if (t.length > best.texts.length) best = {texts: t, id: el.id || ''};
    }
    return best;
  };
  const visible = pick(cands.filter(isVisible));
  return visible.texts.length ? visible : pick(cands);
}
"""


def result_select_ids(market: str) -> list[str]:
    return [
        f"openmarket_category_search_list_{market}",
        f"openmarket_category_search_list2_{market}",
    ]


def read_result_options(
    popup, market: str, *, timeout_ms: int = T_LIST
) -> tuple[list[str], str]:
    """(옵션 목록, 사용한 select id) — 보이는 리스트박스 기준."""
    deadline = time.monotonic() + timeout_ms / 1000
    while True:
        try:
            info = popup.evaluate(RESULT_OPTIONS_JS, result_select_ids(market)) or {}
        except Exception:
            info = {}
        texts = list(info.get("texts") or []) if isinstance(info, dict) else list(info or [])
        sel_id = str(info.get("id") or "") if isinstance(info, dict) else ""
        real = [t for t in texts if t and not t.startswith("-")]
        if real or time.monotonic() >= deadline:
            return real, sel_id or result_select_ids(market)[0]
        try:
            popup.wait_for_timeout(200)
        except Exception:
            time.sleep(0.2)


def choose_option(popup, market: str, label: str, *, select_id: str = "") -> bool:
    ids = [select_id] if select_id else result_select_ids(market)
    for sid in ids:
        loc = _first(popup, (f"#{sid}",))
        if loc is None:
            continue
        try:
            loc.select_option(label=label, timeout=T_CLICK)
            return True
        except Exception:
            continue
    return False


def click_config_save(popup, *, progress: ProgressFn | None = None) -> bool:
    """[검색필터 설정저장 (Alt+S)]."""
    loc = _first(
        popup,
        (
            f'a[onclick*="{CONFIG_SAVE_JS}"]',
            'xpath=//a[.//span[contains(normalize-space(.),"검색필터 설정저장")]]',
        ),
    )
    if loc is None:
        _log(progress, "  오류: [검색필터 설정저장] 미검출", major=True)
        return False
    try:
        loc.click(timeout=T_CLICK)
        _log(progress, "  검색필터 설정저장")
        return True
    except Exception:
        try:
            popup.keyboard.press("Alt+s")
            _log(progress, "  검색필터 설정저장 (Alt+S)")
            return True
        except Exception:
            return False


def close_popup(popup) -> None:
    try:
        if not popup.is_closed():
            popup.close()
    except Exception:
        pass


def map_one_market(
    popup,
    market: str,
    filter_name: str,
    categories: Sequence[str],
    *,
    variant: str = "",
    exclude: Sequence[str] = (),
    retries: int = MAP_RETRIES,
    progress: ProgressFn | None = None,
) -> MappedItem:
    """실패하면 다른 카테고리로 최대 `retries` 회 추가 시도한다."""
    tried = list(exclude or [])
    last = MappedItem(market, "", 0.0, False, "시도 없음")
    for attempt in range(1, max(1, retries) + 1):
        last = _map_once(
            popup,
            market,
            filter_name,
            categories,
            variant=variant,
            exclude=tried,
            progress=progress,
        )
        if last.ok or not last.category:
            return last
        tried.append(last.category)
        _log(
            progress,
            f"  {MARKETS.get(market, market)}: {last.reason} — 다른 카테고리로 재시도"
            f" ({attempt}/{max(1, retries)})",
        )
    return last


def _map_once(
    popup,
    market: str,
    filter_name: str,
    categories: Sequence[str],
    *,
    variant: str = "",
    exclude: Sequence[str] = (),
    progress: ProgressFn | None = None,
) -> MappedItem:
    """한 마켓(+구분) 매핑 — 최적 카테고리 → 검색어 입력 → 검색 → 목록 선택."""
    label = MARKETS.get(market, market) + (f" · {variant}" if variant else "")
    if not categories:
        return MappedItem(market, "", 0.0, False, "엑셀 자료 없음")

    if variant and not select_variant(popup, market, variant, progress=progress):
        return MappedItem(market, "", 0.0, False, f"구분({variant}) 선택 실패")

    category, step = best_category_with_step(filter_name, categories, exclude=exclude)

    # ★절대규칙: 반대 성별 카테고리는 고르지 않는다
    if category and matching.violates_gender(category, filter_name):
        gender = matching.gender_of(filter_name)
        safe = matching.strip_opposite_gender(categories, gender)
        _log(progress, f"  {label}: 반대 성별 카테고리 배제 → 재선정", major=True)
        category, step = best_category_with_step(filter_name, safe, exclude=exclude)

    # ★요건: 최적 카테고리는 **반드시 엑셀 목록 안의 값**이어야 한다
    if category and not matching.is_from(categories, category):
        fixed = matching.ensure_from(categories, category, filter_name)
        _log(progress, f"  {label}: 엑셀 범위 밖 → 목록 내 값으로 교정 ({fixed})")
        category, step = fixed, step + " · 엑셀범위 교정"

    score = 1.0 if category else 0.0
    if not category:
        _log(progress, f"  {label}: 매칭 실패 ({step})")
        return MappedItem(market, "", 0.0, False, "유사 카테고리 없음")
    _log(progress, f"  {label}: 최적 카테고리(엑셀) = {category}  [{step}]")

    keyword = search_keyword_for(category)
    box = market_search_input(popup, market)
    if box is None:
        return MappedItem(market, category, score, False, "검색필드 미검출")
    try:
        box.fill(keyword, timeout=T_CLICK)
    except Exception as e:  # noqa: BLE001
        return MappedItem(market, category, score, False, f"검색어 입력 실패({e})")

    if not click_market_search(popup, market):
        return MappedItem(market, category, score, False, "검색 버튼 미검출")

    options, select_id = read_result_options(popup, market)
    if not options:
        return MappedItem(market, category, score, False, "검색 결과 없음")

    # 결과 목록에서는 **엑셀 카테고리** 를 기준으로 고른다 (필터명은 성별 판정용)
    picked = pick_option(options, category, filter_name)
    if not picked and matching.gender_of(filter_name):
        gender = matching.gender_of(filter_name)
        _log(progress, f"  {label}: 성별({gender}) 조건에 맞는 검색결과 없음", major=True)
        return MappedItem(market, category, score, False, f"성별({gender}) 검색결과 없음")
    if picked and matching.violates_gender(picked, filter_name):
        _log(progress, f"  {label}: 반대 성별 결과 배제 → {picked}", major=True)
        return MappedItem(market, category, score, False, "반대 성별 검색결과만 있음")
    if not picked or not choose_option(popup, market, picked, select_id=select_id):
        return MappedItem(market, category, score, False, "목록 선택 실패")

    _log(progress, f"  {label}: 선택 완료 → {picked}")
    return MappedItem(market, picked, score, True, step)


MAPPED_STATE_JS = """
(codes) => {
  const out = {};
  for (const code of codes) {
    const idEl = document.getElementById('openmarket_cm_category_' + code);
    const nameEl = document.getElementsByName('openmarket_cm_category_name_' + code)[0];
    out[code] = {
      code: idEl ? (idEl.value || '').trim() : '',
      name: nameEl ? (nameEl.value || '').trim() : '',
    };
  }
  return out;
}
"""


def mapped_state(popup, codes: Sequence[str]) -> dict[str, dict]:
    """마켓별 매핑 결과 (hidden 값) — 저장 후 재검증용."""
    try:
        data = popup.evaluate(MAPPED_STATE_JS, list(codes)) or {}
    except Exception:
        return {}
    return {str(k): dict(v or {}) for k, v in data.items()}


def unmapped_markets(popup, codes: Sequence[str]) -> list[str]:
    """카테고리가 비어 있는 마켓 목록."""
    state = mapped_state(popup, codes)
    if not state:
        return []
    out: list[str] = []
    for code in codes:
        info = state.get(code) or {}
        if not (info.get("code") or info.get("name")):
            out.append(code)
    return out


def map_one_row(
    page,
    row: RowInfo,
    excels: dict[str, list[str]],
    *,
    list_url: str,
    markets: Sequence[str] | None = None,
    variant_choice: dict[str, str] | None = None,
    progress: ProgressFn | None = None,
) -> dict:
    """한 행 — 설정수정 팝업 → AI 매핑 → 마켓별 매핑 → 설정저장 → 닫기."""
    codes = list(markets or MARKETS.keys())
    detail: dict = {"ftid": row.ftid, "filter": row.filter_name, "items": []}

    _log(progress, f"필터 [{row.filter_name}] (ftid={row.ftid})", major=True)
    popup = open_setting_popup(page, row, list_url=list_url, progress=progress)
    if popup is None:
        detail["error"] = "팝업 실패"
        return detail

    try:
        popup.on("dialog", lambda d: d.accept())
    except Exception:
        pass

    try:
        click_ai_mapping(popup, progress=progress)
        for market in codes:
            if stop_requested():
                break
            for variant in variants_for(market, (variant_choice or {}).get(market, "")):
                if stop_requested():
                    break
                tried: list[str] = []
                item = map_one_market(
                    popup,
                    market,
                    row.filter_name,
                    excels.get(market, []),
                    variant=variant,
                    progress=progress,
                )
                if item.ok:
                    tried.append(item.category)
                    click_config_save(popup, progress=progress)

                    # 상품고시정보 팝업이 뜨면 닫고 다른 카테고리로 다시 매핑
                    for _ in range(NOTIFY_RETRIES):
                        if not notify_open(popup, market):
                            break
                        _log(
                            progress,
                            f"  {MARKETS.get(market, market)}: 상품고시정보 팝업 —"
                            " 다른 카테고리로 재매핑",
                            major=True,
                        )
                        close_notify(popup, market, progress=progress)
                        item = map_one_market(
                            popup,
                            market,
                            row.filter_name,
                            excels.get(market, []),
                            variant=variant,
                            exclude=tried,
                            progress=progress,
                        )
                        if not item.ok:
                            break
                        tried.append(item.category)
                        click_config_save(popup, progress=progress)

                item.reason = item.reason or ""
                record = dict(item.__dict__)
                record["variant"] = variant
                detail["items"].append(record)
                time.sleep(GAP)

        click_config_save(popup, progress=progress)

        # ★요건: 저장 후 재검증 — 미매핑 마켓이 있으면 최대 3회 다시 매핑
        for round_no in range(1, VERIFY_ROUNDS + 1):
            missing = unmapped_markets(popup, codes)
            if not missing:
                if round_no > 1:
                    _log(progress, "  재검증 — 전 마켓 매핑 확인", major=True)
                break
            names = " · ".join(MARKETS.get(m, m) for m in missing)
            _log(
                progress,
                f"  재검증 {round_no}/{VERIFY_ROUNDS} — 미매핑: {names}",
                major=True,
            )
            for market in missing:
                if stop_requested():
                    break
                variant = variants_for(market, (variant_choice or {}).get(market, ""))[0]
                retry = map_one_market(
                    popup,
                    market,
                    row.filter_name,
                    excels.get(market, []),
                    variant=variant,
                    progress=progress,
                )
                record = dict(retry.__dict__)
                record["variant"] = variant
                record["retry_round"] = round_no
                detail["items"].append(record)
            click_config_save(popup, progress=progress)
            time.sleep(GAP)
        else:
            left = unmapped_markets(popup, codes)
            if left:
                detail["unmapped"] = left
                _log(
                    progress,
                    "  경고: 재검증 3회 후에도 미매핑 — "
                    + " · ".join(MARKETS.get(m, m) for m in left),
                    major=True,
                )
    finally:
        close_popup(popup)
    return detail


def format_row_list(rows: Sequence[RowInfo], *, row_from: int | str = "", row_to: int | str = "") -> list[str]:
    """행 번호 확인용 — 1행부터 순서대로 `번호행: ftid=… · 필터=…`.

    범위를 주면 그 구간에 ★ 표시를 붙여 어디부터 작업되는지 한눈에 보인다.
    """
    start, end = (None, None)
    if str(row_from).strip() or str(row_to).strip():
        start, end = row_range(row_from or DEFAULT_ROW_FROM, row_to or DEFAULT_ROW_TO)
    lines: list[str] = []
    for i, row in enumerate(rows, start=1):
        mark = "★" if (start is not None and start <= i <= end) else "  "
        lines.append(f"{mark}{i:>3}행: ftid={row.ftid or '?'} · 필터={row.filter_name or '(이름 없음)'}")
    return lines


def list_rows_only(
    *,
    site_id: str = DEFAULT_SITE,
    list_url: str = "",
    row_from: int | str = "",
    row_to: int | str = "",
    progress: ProgressFn | None = None,
) -> list[RowInfo]:
    """망고 목록을 열어 행 순서만 확인한다 (매핑 없음) — '몇 번째 행인지' 검증용."""
    try:
        import collect as p2  # noqa: WPS433
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        _log(progress, f"의존성 로드 실패: {e}", major=True)
        return []

    url = (list_url or "").strip() or DEFAULT_LIST_URL
    rows: list[RowInfo] = []
    try:
        with sync_playwright() as pw:
            _browser, page = p2.connect_browser(pw)
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            select_site(page, site_id, progress=progress)
            click_search_filter(page, progress=progress)
            rows = list_rows(page)
    except Exception as e:  # noqa: BLE001
        _log(progress, f"실행 오류: {e}", major=True)
        return rows

    _log(progress, f"검색 결과 {len(rows)}행 (위에서부터 1행)", major=True)
    for line in format_row_list(rows, row_from=row_from, row_to=row_to):
        _log(progress, line)
    return rows


def run_mapping(
    *,
    site_id: str = DEFAULT_SITE,
    excels: dict[str, list[str]] | None = None,
    excel_paths: dict[str, str] | None = None,
    list_url: str = "",
    markets: Sequence[str] | None = None,
    variant_choice: dict[str, str] | None = None,
    row_from: int | str = DEFAULT_ROW_FROM,
    row_to: int | str = DEFAULT_ROW_TO,
    progress: ProgressFn | None = None,
) -> RunResult:
    result = RunResult(ok=False)
    clear_stop_flag()

    site_id = (site_id or DEFAULT_SITE).strip()
    if not is_allowed_site(site_id):
        result.errors.append(
            f"수집사이트 제한: 현재는 {ALLOWED_SITES[0]} 만 수행합니다 (요청={site_id})."
        )
        _log(progress, result.errors[0], major=True)
        return result

    start, end = row_range(row_from, row_to)

    data = dict(excels or {})
    if not data and excel_paths:
        data = load_market_excels(excel_paths, progress=progress)
    if not data:
        result.errors.append("마켓별 카테고리 엑셀이 없습니다.")
        _log(progress, result.errors[0], major=True)
        return result

    try:
        import collect as p2  # noqa: WPS433
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        result.errors.append(f"의존성 로드 실패: {e}")
        _log(progress, result.errors[0], major=True)
        return result

    url = (list_url or "").strip() or DEFAULT_LIST_URL

    try:
        with sync_playwright() as pw:
            _browser, page = p2.connect_browser(pw)
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            _log(progress, "검색필터 목록 화면", major=True)

            if not select_site(page, site_id, progress=progress):
                result.errors.append("상품수집사이트 선택 실패")
            click_search_filter(page, progress=progress)

            # ★검색 결과 목록에 한해 수행 (선택조건으로 검색하기 이후 화면)
            #   체크 여부와 무관하게 **행 범위**로만 대상을 정한다 (요건 2026-08-22 15:03)
            found = [r for r in list_rows(page) if r.ftid]
            if not found:
                result.errors.append("작업 대상 행이 없습니다 (검색 결과 확인).")
                _log(progress, result.errors[0], major=True)
                diagnose_list(page, progress=progress)
                return result

            rows = slice_rows(found, start, end)
            result.rows = len(rows)
            checked = sum(1 for r in found if r.checked)
            _log(
                progress,
                f"검색 결과 {len(found)}행 중 **{start}~{end}행** → {len(rows)}건 수행"
                f" (체크 {checked}건 · 체크 무관 진행)",
                major=True,
            )
            if not rows:
                result.errors.append(
                    f"작업 범위({start}~{end})에 해당하는 행이 없습니다 (체크 {len(found)}건)."
                )
                _log(progress, result.errors[0], major=True)
                return result

            for i, row in enumerate(rows, start=1):
                if stop_requested():
                    _log(progress, "사용자 중단", major=True)
                    break

                _log(progress, f"[{i}/{len(rows)}] (전체 {start + i - 1}행)", major=True)
                detail = map_one_row(
                    page,
                    row,
                    data,
                    list_url=url,
                    markets=markets,
                    variant_choice=variant_choice,
                    progress=progress,
                )
                result.details.append(detail)
                ok_cnt = sum(1 for it in detail.get("items", []) if it.get("ok"))
                result.mapped += ok_cnt
                result.failed += len(detail.get("items", [])) - ok_cnt
                time.sleep(GAP)
    except Exception as e:  # noqa: BLE001
        result.errors.append(str(e))
        _log(progress, f"실행 오류: {e}", major=True)
        return result
    finally:
        clear_stop_flag()

    result.ok = result.mapped > 0
    _log(
        progress,
        f"완료 — 행 {result.rows} · 매핑 성공 {result.mapped} · 실패 {result.failed}",
        major=True,
    )
    return result


def run_dry(
    filter_names: Sequence[str],
    excels: dict[str, list[str]],
    *,
    progress: ProgressFn | None = None,
) -> list[dict]:
    """브라우저 없이 매칭 결과만 확인 (검증용)."""
    out: list[dict] = []
    for name in filter_names:
        row = {"filter": name, "items": []}
        for code, cats in excels.items():
            cat, step = best_category_with_step(name, cats)
            row["items"].append({"market": code, "category": cat, "step": step})
            _log(progress, f"{name} · {MARKETS.get(code, code)} → {cat or '(없음)'} [{step}]")
        out.append(row)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P5_101_카테고리매핑_필터세부설정")
    parser.add_argument(
        "--site-id",
        default=DEFAULT_SITE,
        help=f"상품수집사이트 (현재 {ALLOWED_SITES[0]} 만 허용)",
    )
    parser.add_argument(
        "--row-from",
        type=int,
        default=DEFAULT_ROW_FROM,
        help=f"작업 시작 행 (1부터, 기본 {DEFAULT_ROW_FROM})",
    )
    parser.add_argument(
        "--row-to",
        type=int,
        default=DEFAULT_ROW_TO,
        help=f"작업 종료 행 (포함, 기본 {DEFAULT_ROW_TO})",
    )
    parser.add_argument("--list-url", default="", help=f"목록 URL (기본={DEFAULT_LIST_URL[:60]}…)")
    parser.add_argument("--excel-dir", default="", help="마켓별 엑셀 폴더 (파일명으로 자동 매칭)")
    parser.add_argument(
        "--excel",
        action="append",
        default=[],
        metavar="코드=경로",
        help="마켓별 엑셀 지정 (예: AUC20=D:\\옥션.xlsx)",
    )
    parser.add_argument("--markets", default="", help="대상 마켓 (쉼표, 기본=전체)")
    parser.add_argument(
        "--list-rows",
        action="store_true",
        help="매핑 없이 행 번호·ftid·필터명만 확인 ('몇 번째 행인지' 검증용)",
    )
    parser.add_argument(
        "--variant",
        action="append",
        default=[],
        metavar="코드=구분",
        help="마켓 구분 선택 (예: 11ST=국내카테고리 · LTON=둘다 · 기본=둘다)",
    )
    parser.add_argument("--dry-run", default="", help="매칭만 확인할 필터이름 (쉼표)")
    args = parser.parse_args(argv)

    paths: dict[str, str] = {}
    if args.excel_dir:
        paths.update(discover_market_excels(args.excel_dir))
    for item in args.excel:
        code, _, path = str(item).partition("=")
        if code and path:
            paths[code.strip().upper()] = path.strip()

    excels = load_market_excels(paths) if paths else {}

    if args.dry_run:
        run_dry([n.strip() for n in args.dry_run.split(",") if n.strip()], excels)
        return 0

    markets = [m.strip().upper() for m in args.markets.split(",") if m.strip()] or None
    variant_choice: dict[str, str] = {}
    for item in args.variant:
        code, _, value = str(item).partition("=")
        if code and value:
            variant_choice[code.strip().upper()] = value.strip()
    result = run_mapping(
        site_id=args.site_id,
        excels=excels,
        list_url=args.list_url,
        markets=markets,
        variant_choice=variant_choice,
        row_from=args.row_from,
        row_to=args.row_to,
    )
    for e in result.errors:
        print(f"[오류] {e}", flush=True)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
