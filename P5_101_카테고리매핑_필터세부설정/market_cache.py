"""마켓별 카테고리 캐시 — 엑셀을 다시 읽지 않고 JSON으로 재사용한다.

★요건: "구축된 DB 내용 자체를 파일(JSON)로 저장·GitHub에 커밋 — 매번
엑셀을 다시 읽지 않고 캐시로 재사용 가능하게 할 것."

여기서 캐시하는 건 **원본 카테고리 경로(엑셀을 읽은 결과) 뿐**이다.
`category_db.CategoryDB` 나 `keyword_dictionary.KeywordDB` 처럼 그 위에서
파생(색인·동의어 매핑)한 결과는 캐시하지 않는다 — 파생 결과를 그대로
캐시하면 `matching.py` 의 동의어 사전이 나중에 바뀌어도 캐시가 낡은 값을
계속 돌려주는 사고가 난다. "다시 읽지 않아도 되는" 부분(엑셀 파일 접근·
파싱, openpyxl 의존)만 캐시하고, 색인·사전 생성은 이 캐시를 읽은 뒤
항상 그 자리에서 다시 계산한다(수 초 내로 끝나는 순수 연산).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

HERE = Path(__file__).resolve().parent
DEFAULT_CACHE_PATH = HERE / "data" / "market_categories_cache.json"


def save(
    excels: Mapping[str, Sequence[str]], path: str | Path | None = None
) -> Path:
    """마켓별 카테고리 경로를 JSON 캐시로 저장한다. 저장된 경로를 반환.

    ★`path` 의 기본값은 함수 정의 시점이 아니라 **호출 시점**에
    `DEFAULT_CACHE_PATH` 를 읽는다(모듈 전역을 나중에 바꿔도 반영되도록
    — 예: 테스트에서 `monkeypatch` 로 캐시 경로를 임시로 바꾸는 경우).
    """
    path = Path(path) if path is not None else DEFAULT_CACHE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    markets = {
        str(code).strip().upper(): [str(p) for p in (paths or []) if str(p or "").strip()]
        for code, paths in (excels or {}).items()
    }
    payload = {
        "markets": markets,
        "market_count": len(markets),
        "path_count": sum(len(v) for v in markets.values()),
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
    )
    return path


def load(path: str | Path | None = None) -> dict[str, list[str]]:
    """JSON 캐시를 읽어 마켓별 카테고리 경로로 되돌린다. 없으면 빈 dict."""
    path = Path(path) if path is not None else DEFAULT_CACHE_PATH
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    markets = data.get("markets") or {}
    return {str(code): list(paths or []) for code, paths in markets.items()}


def exists(path: str | Path | None = None) -> bool:
    resolved = Path(path) if path is not None else DEFAULT_CACHE_PATH
    return resolved.exists()


def stats(path: str | Path | None = None) -> dict:
    resolved = Path(path) if path is not None else DEFAULT_CACHE_PATH
    data = load(resolved)
    return {
        "market_count": len(data),
        "path_count": sum(len(v) for v in data.values()),
        "path": str(resolved),
        "exists": exists(resolved),
    }
