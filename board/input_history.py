"""입력 이력 — 사이트명·목록 URL 을 기억해 리스트박스에서 다시 고를 수 있게.

순수 파이썬 (표준 라이브러리만) — GUI 없이도 테스트 가능하다.
"""

from __future__ import annotations

import json
from pathlib import Path

MAX_HISTORY = 10


def _read(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    values = data.get("values") if isinstance(data, dict) else None
    return [str(v).strip() for v in (values or []) if str(v).strip()]


def load(path: Path) -> list[str]:
    """저장된 값 목록 (가장 최근 입력이 맨 앞)."""
    return _read(path)


def remember(path: Path, value: str, *, limit: int = MAX_HISTORY) -> list[str]:
    """value 를 맨 앞으로 옮기고 중복 제거한 뒤 저장한다.

    빈 값은 무시(현재 목록만 반환)한다. 갱신된 전체 목록을 반환한다.
    """
    value = str(value or "").strip()
    values = _read(path)
    if value:
        values = [value] + [v for v in values if v != value]
        values = values[: max(1, limit)]
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({"values": values}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
    return values
