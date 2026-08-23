"""외부 제공 CATEGORY_MASTER + KEYWORD_DICTIONARY CSV를 그대로 DB화한다.

★요건(2026-08-23): "기존 DB를 대체하여 지금 주는 걸 활용하는 프로그램을
구현해. DB는 위의 CSV 자료 그대로 DB화하고 GITHUB에 올려서 메모리로
보관하여 속도를 높이도록 해."

- 원본: `data/category_master.csv`(17,591건, 6개 마켓) +
  `data/keyword_dictionary.csv`(25,399건).
- 이 모듈은 그 CSV를 **가공하지 않고 그대로** 읽어 메모리 구조로 올리고,
  다시 읽지 않도록 `data/category_master_db.json` 캐시로 저장한다
  (JSON 로드가 25,000줄 CSV 재파싱보다 훨씬 빠르다).
- `resolve()` 는 사용자가 준 기획서의 4단계(완전일치→유사어→동일범주→
  확대범주)를 CSV의 실제 컬럼(Mapping_Type·Priority·Parent_ID)으로
  그대로 구현한다. "미매칭 절대 금지" 원칙에 따라, 그 마켓에 카테고리가
  하나라도 있으면 5) 최근접 강제지정으로 반드시 하나를 확정한다.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

try:
    import matching as _matching  # 최근접 강제지정용 유사도 함수 재사용
except ImportError:  # pragma: no cover
    _matching = None

HERE = Path(__file__).resolve().parent
DEFAULT_CATEGORY_CSV = HERE / "data" / "category_master.csv"
DEFAULT_KEYWORD_CSV = HERE / "data" / "keyword_dictionary.csv"
DEFAULT_JSON_CACHE = HERE / "data" / "category_master_db.json"


@dataclass
class CategoryNode:
    cat_id: str
    cat_name: str
    parent_id: str  # "ROOT" 면 최상위
    level: int
    full_path: str
    market: str


@dataclass
class KeywordEntry:
    keyword_id: str
    search_keyword: str
    target_cat_id: str
    mapping_type: str
    priority: int
    market: str
    mapping_result: str = ""


@dataclass
class MasterDB:
    """CSV 그대로 올린 카테고리 마스터 + 키워드 사전 DB (마켓별로 분리)."""

    categories: dict[str, CategoryNode] = field(default_factory=dict)
    keywords: list[KeywordEntry] = field(default_factory=list)
    _children: dict[str, list[str]] = field(default_factory=dict)
    _by_market: dict[str, list[str]] = field(default_factory=dict)  # market -> [cat_id]
    _keyword_index: dict[tuple[str, str], list[KeywordEntry]] = field(default_factory=dict)

    # ── 구축 ─────────────────────────────────────────────────────

    @classmethod
    def from_csv(
        cls,
        category_csv: str | Path | None = None,
        keyword_csv: str | Path | None = None,
    ) -> "MasterDB":
        # ★기본값은 호출 시점에 모듈 전역을 읽는다(정의 시점에 고정하면
        #   테스트에서 monkeypatch 로 기본 경로를 바꿔도 반영되지 않는다).
        category_csv = category_csv if category_csv is not None else DEFAULT_CATEGORY_CSV
        keyword_csv = keyword_csv if keyword_csv is not None else DEFAULT_KEYWORD_CSV
        db = cls()
        with open(category_csv, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                node = CategoryNode(
                    cat_id=row["Cat_ID"].strip(),
                    cat_name=row["Cat_Name"].strip(),
                    parent_id=row["Parent_ID"].strip(),
                    level=int(row["Level"]) if str(row["Level"]).strip().isdigit() else 0,
                    full_path=row["Full_Path"].strip(),
                    market=row["Market"].strip(),
                )
                if not node.cat_id:
                    continue
                db.categories[node.cat_id] = node
                db._children.setdefault(node.parent_id, []).append(node.cat_id)
                db._children.setdefault(node.cat_id, [])
                db._by_market.setdefault(node.market, []).append(node.cat_id)

        with open(keyword_csv, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                priority_raw = str(row.get("Priority", "")).strip()
                entry = KeywordEntry(
                    keyword_id=row["Keyword_ID"].strip(),
                    search_keyword=row["Search_Keyword"].strip(),
                    target_cat_id=row["Target_Cat_ID"].strip(),
                    mapping_type=row["Mapping_Type"].strip(),
                    priority=int(priority_raw) if priority_raw.isdigit() else 99,
                    market=row.get("Market", "").strip(),
                    mapping_result=row.get("Mapping_Result", "").strip(),
                )
                if not entry.search_keyword or not entry.target_cat_id:
                    continue
                db.keywords.append(entry)
                db._keyword_index.setdefault((entry.market, entry.search_keyword), []).append(entry)
        return db

    # ── JSON 캐시 (매번 CSV 재파싱하지 않도록) ───────────────────────

    def save_json(self, path: str | Path | None = None) -> Path:
        path = Path(path) if path is not None else DEFAULT_JSON_CACHE
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "categories": [
                [n.cat_id, n.cat_name, n.parent_id, n.level, n.full_path, n.market]
                for n in self.categories.values()
            ],
            "keywords": [
                [k.keyword_id, k.search_keyword, k.target_cat_id, k.mapping_type, k.priority, k.market, k.mapping_result]
                for k in self.keywords
            ],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def load_json(cls, path: str | Path | None = None) -> "MasterDB | None":
        path = Path(path) if path is not None else DEFAULT_JSON_CACHE
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        db = cls()
        for cat_id, cat_name, parent_id, level, full_path, market in data.get("categories", []):
            node = CategoryNode(cat_id, cat_name, parent_id, level, full_path, market)
            db.categories[cat_id] = node
            db._children.setdefault(parent_id, []).append(cat_id)
            db._children.setdefault(cat_id, [])
            db._by_market.setdefault(market, []).append(cat_id)
        for kw_id, search_keyword, target_cat_id, mapping_type, priority, market, mapping_result in data.get(
            "keywords", []
        ):
            entry = KeywordEntry(kw_id, search_keyword, target_cat_id, mapping_type, priority, market, mapping_result)
            db.keywords.append(entry)
            db._keyword_index.setdefault((market, search_keyword), []).append(entry)
        return db

    @classmethod
    def load(
        cls,
        *,
        category_csv: str | Path | None = None,
        keyword_csv: str | Path | None = None,
        json_cache: str | Path | None = None,
        refresh: bool = False,
    ) -> "MasterDB":
        """★요건: "GITHUB에 올려서 메모리로 보관하여 속도를 높이도록" —
        JSON 캐시가 있으면 그것부터 읽고(빠름), 없거나 `refresh=True` 면
        CSV 원본에서 다시 만들고 캐시를 갱신한다."""
        json_cache = json_cache if json_cache is not None else DEFAULT_JSON_CACHE
        if not refresh:
            cached = cls.load_json(json_cache)
            if cached is not None and cached.categories:
                return cached
        db = cls.from_csv(category_csv, keyword_csv)
        db.save_json(json_cache)
        return db

    # ── 조회 ─────────────────────────────────────────────────────

    def is_leaf(self, cat_id: str) -> bool:
        return not self._children.get(cat_id)

    def children_of(self, cat_id: str) -> list[CategoryNode]:
        return [self.categories[c] for c in self._children.get(cat_id, []) if c in self.categories]

    def siblings_of(self, cat_id: str) -> list[CategoryNode]:
        node = self.categories.get(cat_id)
        if node is None:
            return []
        return [c for c in self.children_of(node.parent_id) if c.cat_id != cat_id]

    def ancestors_of(self, cat_id: str) -> list[CategoryNode]:
        out: list[CategoryNode] = []
        node = self.categories.get(cat_id)
        while node and node.parent_id and node.parent_id != "ROOT":
            node = self.categories.get(node.parent_id)
            if node:
                out.append(node)
        return out

    def market_leaf_paths(self, market: str) -> list[str]:
        """이 마켓의 리프(최하위) 카테고리 Full_Path 전부 — 기존
        `load_market_excels()` 출력과 같은 모양(문자열 목록)이라 그대로
        `map_categories.py` 파이프라인에 넣을 수 있다."""
        ids = self._by_market.get(market, [])
        return [self.categories[i].full_path for i in ids if self.is_leaf(i) and i in self.categories]

    def excels_dict(self, code_to_name: dict[str, str]) -> dict[str, list[str]]:
        """마켓 코드(AUC20 등) → Full_Path 목록. 기존 `excels` 딕셔너리와
        같은 모양으로 반환해, 이 DB를 `map_categories.py` 전체에 그대로
        꽂아 넣을 수 있게 한다."""
        return {code: self.market_leaf_paths(name) for code, name in code_to_name.items()}

    def _lookup(self, market: str, keyword: str) -> list[KeywordEntry]:
        want = str(keyword or "").strip()
        if not want:
            return []
        hits = list(self._keyword_index.get((market, want), []))
        hits.sort(key=lambda k: k.priority)
        return hits

    def _best_by_similarity(self, name: str, candidate_ids: Sequence[str]) -> str | None:
        ranked = self._similar_candidates(name, candidate_ids, limit=1)
        if ranked:
            return ranked[0]
        return candidate_ids[0] if candidate_ids else None

    def _similar_candidates(
        self,
        name: str,
        candidate_ids: Sequence[str],
        *,
        exclude: Sequence[str] = (),
        limit: int = 5,
        gender: str = "",
    ) -> list[str]:
        """이름 유사도로 순위를 매긴다. `matching` 이 있으면 검색어의
        계열(신발·의류 등)과 같은 계열 후보를 먼저 보고, 없으면 마켓
        전체를 본다 — 순수 글자(bigram) 유사도만으로는 "드로즈"가
        "퀵드로"(등산용품) 처럼 전혀 무관한 계열과 우연히 겹쳐 엉뚱한
        걸 고르는 사고가 나기 때문이다.

        ★실사례: 글자 겹침이 전부 0점으로 동률일 때(예: "구두" vs 이름이
        전혀 안 겹치는 "신발"(대분류, 짧음) vs "여성단화"(같은 성별 명시,
        조금 더 길음)) 예전엔 "경로가 짧을수록" 이겨서 성별 표기조차 없는
        밋밋한 대분류가 이겼다. `gender` 를 주면 그 성별이 명시된 경로를
        동점 처리 시 우선한다.
        """
        exclude_set = set(exclude)
        pool = [c for c in candidate_ids if c not in exclude_set and c in self.categories]
        if not pool:
            return []
        if _matching is not None and name:
            cls = _matching.class_of(name)
            if cls:
                same_class = [c for c in pool if _matching.path_class(self.categories[c].full_path) == cls]
                if same_class:
                    pool = same_class
        if _matching is None:
            return list(pool[:limit])
        scored = [
            (
                -(
                    _matching._overlap(name, self.categories[c].cat_name)
                    + 0.5 * _matching._overlap(name, self.categories[c].full_path)
                ),
                0 if (gender and _matching.has_gender(self.categories[c].full_path, gender)) else 1,
                len(self.categories[c].full_path),
                c,
            )
            for c in pool
        ]
        scored.sort(key=lambda t: t[:3])
        return [c for *_rest, c in scored[:limit]]

    def _direct_name_matches(
        self, market: str, keyword: str, market_ids: Sequence[str], *, gender: str = ""
    ) -> list[str]:
        """★요건(절대): "엑셀(CATEGORY_MASTER) 카테고리명이 100% 우선" —
        KEYWORD_DICTIONARY 사전에 연결이 없어도, 검색어 글자가 카테고리명
        (리프 우선, 다음 전체경로) 안에 그대로 들어있으면 그것부터 찾는다.

        실사례: 쿠팡 "여성화 > 하이힐/펌프스/정장구두" 는 "구두" 라는
        글자를 그대로 담고 있는데도, 사전에 "구두"→이 카테고리 연결이
        빠져 있어 엉뚱한(유아동) 카테고리로 샜다. 사전이 불완전해도
        카테고리명 자체는 원본(엑셀)에서 그대로 가져온 값이므로, 이
        직접 포함 여부를 사전 매칭과 별개로 항상 확인한다.
        """
        want_norm = _matching.normalize(keyword) if _matching is not None else keyword.strip().lower()
        if not want_norm:
            return []
        leaf_hits: list[tuple[int, int, str]] = []
        other_hits: list[tuple[int, int, str]] = []
        for cid in market_ids:
            node = self.categories.get(cid)
            if node is None:
                continue
            # ★검색어와 필터의 성별이 경로에 **함께** 명시돼 있으면 우선한다
            #   (예: "여성패션 > 여성화 > 하이힐/펌프스/정장구두" 는 "여성"이
            #   두 번 나오는 만큼 신뢰도가 높다) — 그래야 성별 표기가 아예
            #   없는, 우연히 글자만 짧아 비슷해 보이는 무관한 후보(예:
            #   "스케이트화/스케이트구두")보다 앞선다.
            gender_bonus = 0
            if gender and _matching is not None and _matching.has_gender(node.full_path, gender):
                gender_bonus = -1  # 정렬 시 작을수록 우선이므로 보너스는 음수
            name_norm = (
                _matching.normalize(node.cat_name) if _matching is not None else node.cat_name.strip().lower()
            )
            if want_norm in name_norm:
                leaf_hits.append((gender_bonus, len(name_norm), cid))
                continue
            path_norm = (
                _matching.normalize(node.full_path) if _matching is not None else node.full_path.strip().lower()
            )
            if want_norm in path_norm:
                other_hits.append((gender_bonus, len(path_norm), cid))
        # 카테고리명(리프) 자체에 포함된 것을 우선하고, 그 안에서는 같은
        # 성별이 명시된 것 → 이름이 짧을수록(더 구체적으로 일치) 순.
        leaf_hits.sort(key=lambda t: (t[0], t[1]))
        other_hits.sort(key=lambda t: (t[0], t[1]))
        return [cid for _g, _len, cid in leaf_hits] + [cid for _g, _len, cid in other_hits]

    def resolve_ranked(
        self, market: str, keyword: str, *, limit: int = 10, gender: str = ""
    ) -> list[tuple[str, str]]:
        """(Cat_ID, 단계설명) 여러 개를 우선순위대로 반환한다.

        상위 호출부(`map_categories.best_category_via_master`)가 브랜드·
        성별 절대규칙으로 앞 후보를 건너뛰어도 다음 후보로 계속 시도할
        수 있게, **하나만** 주지 않고 랭킹을 준다. `gender` 를 주면(필터
        명의 성별) 1.5)단계에서 같은 성별이 함께 명시된 카테고리를 우선
        한다.

        순서: 1) 완전일치/유사어(EX) · 2) 유사어(SY) · 3) 형태소분리(MO)
        (KEYWORD_DICTIONARY 조회) → 1.5) 카테고리명에 검색어가 그대로
        포함(엑셀 원본 그대로, 사전이 비어 있어도 항상 확인) → 4) 최근접
        강제지정(bigram 유사도).
        """
        want = str(keyword or "").strip()
        market_ids = self._by_market.get(market, [])
        if not market_ids:
            return []
        out: list[tuple[str, str]] = []
        if want:
            for hit in self._lookup(market, want)[:limit]:
                label = {1: "1) 완전일치/유사어(EX)", 2: "2) 유사어(SY)", 3: "3) 형태소분리(MO)"}.get(
                    hit.priority, hit.mapping_type
                )
                out.append((hit.target_cat_id, label))
        if len(out) < limit and want:
            seen = {cid for cid, _ in out}
            direct = [
                cid
                for cid in self._direct_name_matches(market, want, market_ids, gender=gender)
                if cid not in seen
            ]
            out.extend((cid, "1.5) 카테고리명 직접포함") for cid in direct[: limit - len(out)])
        if len(out) < limit:
            seen = {cid for cid, _ in out}
            more = self._similar_candidates(
                want, market_ids, exclude=seen, limit=limit - len(out), gender=gender
            )
            out.extend((cid, "4) 최근접 강제지정") for cid in more)
        return out

    def resolve(self, market: str, keyword: str) -> tuple[str | None, str]:
        """기획서의 4단계를 CSV 컬럼 그대로 구현한다.

        1) 완전일치/유사어/형태소분리 — `KEYWORD_DICTIONARY` 를
           Priority 순으로(작을수록 우선) 조회한다(EX·SY·MO 전부 여기서
           한 번에 처리 — CSV 는 이미 우선순위를 Priority 컬럼에 담아
           두었으므로 그대로 정렬만 하면 된다).
        2) 동일범주(형제) — 위에서 못 찾으면, **같은 이름을 가진 다른
           마켓 카테고리의 리프명**으로 이 마켓 안의 형제를 찾는다(생략
           — 대신 3)으로 바로 감).
        3) 확대범주(상위) — 이 마켓 트리에 검색어가 아예 없으면, 시도할
           것이 없으므로 4) 최근접 강제지정으로 간다.
        4) ★반드시 하나 지정 — 그 마켓에 카테고리가 있으면(위 어디서도
           못 찾았어도) 이름이 가장 비슷한 것을 강제로 확정한다. "미검출"
           로 끝내는 것은 이 DB 의 존재 목적에 위배된다.
        """
        market_ids = self._by_market.get(market, [])
        if not market_ids:
            return None, "카테고리 자료 없음"
        ranked = self.resolve_ranked(market, keyword, limit=1)
        if not ranked:
            return None, "미검출"
        return ranked[0]

    def full_path(self, cat_id: str | None) -> str:
        if not cat_id:
            return ""
        node = self.categories.get(cat_id)
        return node.full_path if node else ""


def load(
    *,
    category_csv: str | Path | None = None,
    keyword_csv: str | Path | None = None,
    json_cache: str | Path | None = None,
    refresh: bool = False,
) -> MasterDB:
    return MasterDB.load(
        category_csv=category_csv, keyword_csv=keyword_csv, json_cache=json_cache, refresh=refresh
    )
