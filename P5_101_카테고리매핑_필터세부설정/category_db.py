"""통합정보화 DB — 6개 마켓 엑셀 카테고리를 교차검색해 연관검색어를 관리한다.

요건 (2026-08-22 요건재정의 B):
    1) 사전 6개 마켓 카테고리 엑셀자료를 불러온다
    2) 카테고리 매칭용 통합정보화 DB를 구축한다
    3) 구축 순서
        0) 엑셀자료 상호간 교차검색으로 검색어-연관검색어 매핑 정보를 관리한다
        1) 하위 카테고리를 <검색어>로 6개 엑셀에서 검색항목을 연관검색어로 등록
        2) 연관검색어는 하위단계를 1순위, 상위단계를 2·3순위로 저장
        3) 연관검색어를 향후 매핑검색시 유사정보/확장형 매핑에 활용
        (중위·상위도 동일하게 반복)

이 DB는 사람이 정한 동의어 사전이 아니라, **실제 6개 마켓 엑셀 데이터 자체**에서
"어떤 하위/중위/상위 이름이 같은 카테고리 그룹(상위+중위)에 함께 나오는가"를
교차검색해서 만든다 — 마켓마다 표현이 달라도(예: "버킷햇" ↔ "사파리햇") 같은
그룹에 같이 등장한 이력이 있으면 서로의 연관검색어로 등록된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

import matching


@dataclass
class CategoryDB:
    """마켓 무관 통합 카테고리 색인 — 검색어 → 연관검색어(우선순위별)."""

    # 레벨별 { 정규화된 검색어 : [그 검색어가 나온 전체 경로들] }
    _by_level: dict[str, dict[str, list[str]]] = field(
        default_factory=lambda: {"상위": {}, "중위": {}, "하위": {}}
    )
    market_count: int = 0
    path_count: int = 0

    @classmethod
    def build(cls, excels: Mapping[str, Sequence[str]] | None) -> "CategoryDB":
        db = cls()
        for market, paths in (excels or {}).items():
            db.market_count += 1
            for path in paths or []:
                db._register(path)
        return db

    def _register(self, path: str) -> None:
        levels = matching.split_levels(path)
        if not levels:
            return
        self.path_count += 1
        top = levels[0]
        low = levels[-1]
        # 경로 깊이가 3단계를 넘으면(예: 상위·성별·중위·하위) 첫/끝을 뺀
        # 가운데 전부를 "중위" 후보로 등록한다 — 성별 등 추가 단계가
        # 껴 있어도 실제 중위(모자·소품 등)를 놓치지 않는다.
        mids = levels[1:-1]
        for level_name, terms in (
            ("상위", (top,)),
            ("중위", tuple(mids)),
            ("하위", (low,)),
        ):
            for term in terms:
                if not term:
                    continue
                key = matching.normalize(term)
                if not key:
                    continue
                bucket = self._by_level[level_name].setdefault(key, [])
                if path not in bucket:
                    bucket.append(path)

    def search(self, term: str) -> list[str]:
        """교차검색 — 이 검색어가 상·중·하 어느 레벨이든 걸리는 경로 전부."""
        key = matching.normalize(term)
        if not key:
            return []
        out: list[str] = []
        for level_name in ("하위", "중위", "상위"):
            for existing_key, paths in self._by_level[level_name].items():
                if key in existing_key or existing_key in key:
                    for p in paths:
                        if p not in out:
                            out.append(p)
        return out

    def related(self, term: str, *, limit: int = 20) -> list[tuple[str, int]]:
        """검색어의 연관검색어 — 하위=1순위, 중위=2순위, 상위=3순위.

        교차검색으로 걸린 모든 경로에서 그 경로의 하위·중위·상위 이름을
        뽑아 연관검색어 후보로 등록한다(자기 자신은 제외).
        """
        key = matching.normalize(term)
        if not key:
            return []
        out: list[tuple[str, int]] = []
        seen = {key}

        def add(candidate: str, priority: int) -> None:
            nc = matching.normalize(candidate)
            if not nc or nc in seen:
                return
            seen.add(nc)
            out.append((candidate, priority))

        for path in self.search(term):
            levels = matching.split_levels(path)
            if not levels:
                continue
            top = levels[0]
            low = levels[-1]
            mids = levels[1:-1]
            if low:
                add(low, 1)
            for mid in mids:
                add(mid, 2)
            if top:
                add(top, 3)

        out.sort(key=lambda item: item[1])
        return out[:limit]

    def related_terms(self, term: str, *, limit: int = 20) -> list[str]:
        return [name for name, _priority in self.related(term, limit=limit)]

    def __bool__(self) -> bool:
        return self.path_count > 0


def build(excels: Mapping[str, Sequence[str]] | None) -> CategoryDB:
    return CategoryDB.build(excels)
