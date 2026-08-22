"""P2 입력 엑셀 보관 목록 · 카테고리URL 행 목록 (리스트박스용)"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None  # type: ignore


@dataclass
class ExcelEntry:
    path: str
    name: str
    added_at: str


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def library_path() -> Path:
    return _root() / ".data" / "p2-excel-library.json"


def default_roots() -> list[str]:
    home = Path.home()
    candidates = [
        _root(),
        home / "Downloads",
        home / "다운로드",
        home / "Desktop",
        home / "바탕 화면",
        home / "Documents",
        home / "문서",
    ]
    out: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        p = c.resolve()
        key = str(p).lower()
        if key in seen or not p.is_dir():
            continue
        seen.add(key)
        out.append(str(p))
    return out


def load() -> dict:
    fp = library_path()
    if not fp.exists():
        return {"version": 1, "last_selected": "", "entries": []}
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        if not isinstance(data.get("entries"), list):
            return {"version": 1, "last_selected": "", "entries": []}
        return data
    except Exception:
        return {"version": 1, "last_selected": "", "entries": []}


def save(data: dict) -> None:
    fp = library_path()
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def entries_annotated() -> list[dict]:
    data = load()
    items = []
    for e in data.get("entries") or []:
        path = str(e.get("path") or "").strip()
        if not path:
            continue
        items.append(
            {
                "path": path,
                "name": e.get("name") or Path(path).name,
                "added_at": e.get("added_at") or "",
                "exists": os.path.isfile(path),
            }
        )
    return items


def add_paths(paths: list[str]) -> dict:
    data = load()
    seen = {str(Path(e["path"]).resolve()).lower() for e in data.get("entries") or [] if e.get("path")}
    now = datetime.now(timezone.utc).isoformat()
    for raw in paths:
        p = Path(raw).expanduser().resolve()
        if not p.is_file():
            continue
        key = str(p).lower()
        if key in seen:
            continue
        seen.add(key)
        data.setdefault("entries", []).append(
            {"path": str(p), "name": p.name, "added_at": now}
        )
        data["last_selected"] = str(p)
    save(data)
    return data


def remove_path(path: str) -> dict:
    data = load()
    key = str(Path(path).resolve()).lower()
    data["entries"] = [
        e
        for e in (data.get("entries") or [])
        if str(Path(e.get("path", "")).resolve()).lower() != key
    ]
    if str(Path(data.get("last_selected") or "").resolve()).lower() == key:
        data["last_selected"] = (data["entries"][0]["path"] if data["entries"] else "")
    save(data)
    return data


def set_selected(path: str) -> dict:
    data = load()
    key = str(Path(path).resolve()).lower()
    for e in data.get("entries") or []:
        if str(Path(e.get("path", "")).resolve()).lower() == key:
            data["last_selected"] = e["path"]
            save(data)
            break
    return data


def is_in_library(path: str) -> bool:
    key = str(Path(path).resolve()).lower()
    for e in load().get("entries") or []:
        if str(Path(e.get("path", "")).resolve()).lower() == key:
            return True
    return False


def search_xlsx(dir_path: str, query: str = "", max_depth: int = 3, max_files: int = 200) -> list[dict]:
    root = Path(dir_path).expanduser()
    if not root.is_absolute():
        raise ValueError("절대 경로를 입력하세요.")
    if not root.is_dir():
        raise FileNotFoundError(f"폴더 없음: {root}")

    q = (query or "").strip().lower()
    found: list[dict] = []

    def walk(current: Path, depth: int) -> None:
        if len(found) >= max_files or depth > max_depth:
            return
        try:
            entries = list(current.iterdir())
        except OSError:
            return
        for ent in entries:
            if len(found) >= max_files:
                break
            name = ent.name
            if name.startswith(".") or name in {"node_modules", ".git", ".venv", "venv"}:
                continue
            try:
                if ent.is_dir():
                    walk(ent, depth + 1)
                elif ent.is_file() and name.lower().endswith(".xlsx") and not name.startswith("~$"):
                    if q and q not in name.lower() and q not in str(ent).lower():
                        continue
                    st = ent.stat()
                    found.append({"path": str(ent.resolve()), "name": name, "mtime": st.st_mtime})
            except OSError:
                continue

    walk(root.resolve(), 0)

    def score(n: str) -> int:
        u = n.upper()
        if "카테고리URL" in n or "URL_LIST" in u:
            return 0
        if "카테고리" in n or "CATEGORY" in u:
            return 1
        return 2

    found.sort(key=lambda x: (score(x["name"]), -x["mtime"]))
    return found


def read_category_url_rows(path: str) -> list[dict]:
    """엑셀에서 카테고리URL 행 목록을 읽는다.

    반환: [{"ordinal": 1, "excel_row": 2, "label": "...", "url": "..."}, ...]
    """
    if openpyxl is None:
        raise RuntimeError("openpyxl 이 필요합니다 (pip install openpyxl)")
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"파일 없음: {p}")

    wb = openpyxl.load_workbook(str(p), data_only=True, read_only=True)
    try:
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        try:
            header_cells = next(rows_iter)
        except StopIteration:
            return []
        headers = [str(c or "").strip() for c in header_cells]
        try:
            url_col = headers.index("최종 카테고리 URL주소")
        except ValueError as e:
            raise ValueError(
                "엑셀 1행 헤더에 '최종 카테고리 URL주소' 열이 있어야 합니다."
            ) from e
        # ★요건(2026-08-20): 카테고리URL목록에는 "최종 카테고리명"을 표시한다.
        # 옛 엑셀에는 이 열이 없을 수 있어 "상위 최종 카테고리명"으로 대체한다.
        try:
            label_col = headers.index("최종 카테고리명")
        except ValueError:
            try:
                label_col = headers.index("상위 최종 카테고리명")
            except ValueError as e:
                raise ValueError(
                    "엑셀 1행 헤더에 '최종 카테고리명'"
                    "(또는 '상위 최종 카테고리명') 열이 있어야 합니다."
                ) from e

        out: list[dict] = []
        ordinal = 0
        for excel_row, values in enumerate(rows_iter, start=2):
            vals = list(values or ())
            raw_label = vals[label_col] if label_col < len(vals) else ""
            raw_url = vals[url_col] if url_col < len(vals) else ""
            label = str(raw_label or "").strip()
            url = str(raw_url or "").strip()
            if not url:
                continue
            # ★총건수·목록: 목차 행 제외 (헤더 1행은 위에서 이미 제외)
            if label == "목차" or label.startswith("목차") or label.upper() == "TOC":
                continue
            ordinal += 1
            out.append(
                {
                    "ordinal": ordinal,
                    "excel_row": excel_row,
                    "label": label,
                    "url": url,
                }
            )
        return out
    finally:
        try:
            wb.close()
        except Exception:
            pass
