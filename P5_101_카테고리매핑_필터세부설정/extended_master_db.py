"""확장형 연관검색어 DB (extended_category_master.csv + extended_keyword_dictionary.csv).

★요건(2026-08-23): "A.마켓별 카테고리 분류엑셀자료, B.카테고리매핑DB, C.카테고리매핑_확장형DB"
- 원본: `data/extended_category_master.csv`(14,207건 표준 카테고리) +
  `data/extended_keyword_dictionary.csv`(29,999건 표준 키워드).
- Word XML 가이드(『공통 확장형 연관검색어 DB 활용 가이드 및 시스템 구축 방안』):
  5단계 폭포수(Waterfall) 매핑 알고리즘:
    1단계: EX (완전 일치) - Priority 1
    2단계: SY (병렬속성/유의어 분리) - Priority 2
    3단계: MO (형태소/단어 분리) - Priority 3
    4단계: IN (문맥추론 - 부모/조부모 결합) - Priority 4~5
    5단계: AB (확대 범주) - Priority 6
- 인메모리 고속 검색을 위해 `data/extended_master_db.json` 단일 캐시로 저장·재사용한다.
- `expand_terms(keyword)`: 주어진 키워드로 표준 카테고리 및 관련 확장 키워드 목록을 추출해
  상위 파이프라인에서 엑셀 검색 범위를 넓히는 데 사용한다.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

try:
    import matching as _matching
except ImportError:  # pragma: no cover
    _matching = None

HERE = Path(__file__).resolve().parent
DEFAULT_EXT_CATEGORY_CSV = HERE / "data" / "extended_category_master.csv"
DEFAULT_EXT_KEYWORD_CSV = HERE / "data" / "extended_keyword_dictionary.csv"
DEFAULT_EXT_JSON_CACHE = HERE / "data" / "extended_master_db.json"


@dataclass
class ExtCategoryNode:
    cat_id: str
    cat_name: str
    parent_id: str  # "ROOT" 면 최상위
    level: int
    full_path: str


@dataclass
class ExtKeywordEntry:
    keyword_id: str
    search_keyword: str
    target_cat_id: str
    mapping_type: str
    priority: int
    mapping_result: str = ""


@dataclass
class ExtendedMasterDB:
    """확장형 표준 카테고리 마스터 + 표준 키워드 사전 DB."""

    categories: dict[str, ExtCategoryNode] = field(default_factory=dict)
    keywords: list[ExtKeywordEntry] = field(default_factory=list)
    _children: dict[str, list[str]] = field(default_factory=dict)
    _keyword_index: dict[str, list[ExtKeywordEntry]] = field(default_factory=dict)  # search_kw_norm -> [Entry]

    # ── 구축 ─────────────────────────────────────────────────────

    @classmethod
    def from_csv(
        cls,
        category_csv: str | Path | None = None,
        keyword_csv: str | Path | None = None,
    ) -> "ExtendedMasterDB":
        category_csv = category_csv if category_csv is not None else DEFAULT_EXT_CATEGORY_CSV
        keyword_csv = keyword_csv if keyword_csv is not None else DEFAULT_EXT_KEYWORD_CSV
        db = cls()
        with open(category_csv, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                cat_id = row.get("Cat_ID", "").strip()
                cat_name = row.get("Cat_Name", "").strip()
                parent_id = row.get("Parent_ID", "").strip()
                level_str = str(row.get("Level", "")).strip()
                full_path = row.get("Full_Path", "").strip()
                if not cat_id:
                    continue
                node = ExtCategoryNode(
                    cat_id=cat_id,
                    cat_name=cat_name,
                    parent_id=parent_id,
                    level=int(level_str) if level_str.isdigit() else 0,
                    full_path=full_path,
                )
                db.categories[cat_id] = node
                db._children.setdefault(parent_id, []).append(cat_id)
                db._children.setdefault(cat_id, [])

        with open(keyword_csv, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                kw_id = row.get("Keyword_ID", "").strip()
                search_kw = row.get("Search_Keyword", "").strip()
                target_cat_id = row.get("Target_Cat_ID", "").strip()
                mapping_type = row.get("Mapping_Type", "").strip()
                priority_raw = str(row.get("Priority", "")).strip()
                mapping_result = row.get("Mapping_Result", "").strip()
                if not search_kw or not target_cat_id:
                    continue
                entry = ExtKeywordEntry(
                    keyword_id=kw_id,
                    search_keyword=search_kw,
                    target_cat_id=target_cat_id,
                    mapping_type=mapping_type,
                    priority=int(priority_raw) if priority_raw.isdigit() else 99,
                    mapping_result=mapping_result,
                )
                db.keywords.append(entry)
                norm_kw = _matching.normalize(search_kw) if _matching is not None else search_kw.strip().lower()
                db._keyword_index.setdefault(norm_kw, []).append(entry)
        return db

    # ── JSON 캐시 ───────────────────────────────────────────────────

    def save_json(self, path: str | Path | None = None) -> Path:
        path = Path(path) if path is not None else DEFAULT_EXT_JSON_CACHE
        path.parent.mkdir(parents=True, exist_ok=True)
        cat_rows = [
            [c.cat_id, c.cat_name, c.parent_id, c.level, c.full_path]
            for c in self.categories.values()
        ]
        kw_rows = [
            [
                k.keyword_id,
                k.search_keyword,
                k.target_cat_id,
                k.mapping_type,
                k.priority,
                k.mapping_result,
            ]
            for k in self.keywords
        ]
        payload = {"categories": cat_rows, "keywords": kw_rows}
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        tmp.replace(path)
        return path

    @classmethod
    def load_json(cls, path: str | Path | None = None) -> "ExtendedMasterDB":
        path = Path(path) if path is not None else DEFAULT_EXT_JSON_CACHE
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        db = cls()
        for row in data.get("categories", []):
            cat_id, cat_name, parent_id, level, full_path = row
            node = ExtCategoryNode(
                cat_id=cat_id,
                cat_name=cat_name,
                parent_id=parent_id,
                level=int(level),
                full_path=full_path,
            )
            db.categories[cat_id] = node
            db._children.setdefault(parent_id, []).append(cat_id)
            db._children.setdefault(cat_id, [])

        for row in data.get("keywords", []):
            kw_id, search_kw, target_cat_id, mapping_type, priority, mapping_result = row
            entry = ExtKeywordEntry(
                keyword_id=kw_id,
                search_keyword=search_kw,
                target_cat_id=target_cat_id,
                mapping_type=mapping_type,
                priority=int(priority),
                mapping_result=mapping_result,
            )
            db.keywords.append(entry)
            norm_kw = _matching.normalize(search_kw) if _matching is not None else search_kw.strip().lower()
            db._keyword_index.setdefault(norm_kw, []).append(entry)
        return db

    @classmethod
    def load(
        cls,
        json_path: str | Path | None = None,
        category_csv: str | Path | None = None,
        keyword_csv: str | Path | None = None,
    ) -> "ExtendedMasterDB":
        json_path = json_path if json_path is not None else DEFAULT_EXT_JSON_CACHE
        if Path(json_path).is_file():
            try:
                return cls.load_json(json_path)
            except Exception:
                pass
        db = cls.from_csv(category_csv=category_csv, keyword_csv=keyword_csv)
        try:
            db.save_json(json_path)
        except Exception:
            pass
        return db

    # ── 조회 및 폭포수 탐색 ──────────────────────────────────────────

    def is_leaf(self, cat_id: str) -> bool:
        return len(self._children.get(cat_id, [])) == 0

    def full_path(self, cat_id: str | None) -> str:
        if not cat_id:
            return ""
        node = self.categories.get(cat_id)
        return node.full_path if node else ""

    def _lookup(self, keyword: str) -> list[ExtKeywordEntry]:
        norm = _matching.normalize(keyword) if _matching is not None else keyword.strip().lower()
        entries = self._keyword_index.get(norm, [])
        return sorted(entries, key=lambda e: e.priority)

    def resolve_ranked(self, keyword: str, *, limit: int = 20) -> list[tuple[str, str, int]]:
        """폭포수 5단계에 따라 (Cat_ID, 단계설명, Priority) 반환."""
        want = str(keyword or "").strip()
        if not want:
            return []
        hits = self._lookup(want)
        out: list[tuple[str, str, int]] = []
        for hit in hits[:limit]:
            step_name = {
                1: "1) EX(완전일치)",
                2: "2) SY(병렬/유의어)",
                3: "3) MO(형태소분리)",
                4: "4) IN(문맥추론-부모결합)",
                5: "4) IN(문맥추론-조부모결합)",
                6: "5) AB(확대범주)",
            }.get(hit.priority, f"{hit.priority}) {hit.mapping_type}")
            out.append((hit.target_cat_id, step_name, hit.priority))
        return out

    def expand_terms(self, keyword: str, *, limit: int = 10) -> list[str]:
        """주어진 키워드로 표준 카테고리 및 관련 키워드/범주 단어들을 추출하여 반환.
        
        2차 및 3차 매핑 파이프라인에서 엑셀 검색 범주/범위를 넓히는 데 사용된다.
        """
        want = str(keyword or "").strip()
        if not want:
            return []
        results: list[str] = []
        seen: set[str] = set()

        def add(term: str):
            t = str(term or "").strip()
            if not t:
                return
            norm = _matching.normalize(t) if _matching is not None else t.lower()
            if norm and norm not in seen:
                seen.add(norm)
                results.append(t)

        # 1. 키워드 사전에서 매핑된 표준 카테고리의 노드명, 리프명, 상위경로 토큰 수집
        hits = self._lookup(want)
        for h in hits[:limit]:
            node = self.categories.get(h.target_cat_id)
            if not node:
                continue
            add(node.cat_name)
            # full_path 상의 레벨 분해
            levels = [lv.strip() for lv in node.full_path.split(">") if lv.strip()]
            for lv in levels:
                add(lv)
                # 복합어 분해 (슬래시 등)
                for part in lv.replace("/", " ").replace(",", " ").split():
                    add(part)

        # 2. 카테고리명 직접 포함 노드 수집
        norm_want = _matching.normalize(want) if _matching is not None else want.lower()
        for node in self.categories.values():
            name_norm = _matching.normalize(node.cat_name) if _matching is not None else node.cat_name.lower()
            if norm_want in name_norm:
                add(node.cat_name)
                for part in node.cat_name.replace("/", " ").replace(",", " ").split():
                    add(part)
            if len(results) >= limit * 3:
                break

        return results
