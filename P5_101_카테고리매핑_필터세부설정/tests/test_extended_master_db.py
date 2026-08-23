from __future__ import annotations

from pathlib import Path
import pytest

import extended_master_db as emdb
import map_categories as mc
import matching as mt


@pytest.fixture
def sample_ext_db(tmp_path: Path):
    cat_csv = tmp_path / "cats.csv"
    kw_csv = tmp_path / "kws.csv"
    cat_csv.write_text(
        "Cat_ID,Cat_Name,Parent_ID,Level,Full_Path\n"
        "STD_001,패션의류,ROOT,1,패션의류\n"
        "STD_002,여성의류,STD_001,2,패션의류 > 여성의류\n"
        "STD_003,블라우스/셔츠,STD_002,3,패션의류 > 여성의류 > 블라우스/셔츠\n"
        "STD_004,가방/잡화,ROOT,1,가방/잡화\n"
        "STD_005,모자,STD_004,2,가방/잡화 > 모자\n"
        "STD_006,비니/베레모,STD_005,3,가방/잡화 > 모자 > 비니/베레모\n",
        encoding="utf-8",
    )
    kw_csv.write_text(
        "Keyword_ID,Search_Keyword,Target_Cat_ID,Mapping_Type,Priority,Mapping_Result\n"
        "KW_001,비니,STD_006,EX(완전일치),1,가방/잡화 > 모자 > 비니/베레모\n"
        "KW_002,베레모,STD_006,SY(병렬속성분리),2,가방/잡화 > 모자 > 비니/베레모\n"
        "KW_003,셔츠,STD_003,EX(완전일치),1,패션의류 > 여성의류 > 블라우스/셔츠\n"
        "KW_004,블라우스,STD_003,SY(병렬속성분리),2,패션의류 > 여성의류 > 블라우스/셔츠\n"
        "KW_005,모자,STD_006,AB(확대범주),6,가방/잡화 > 모자 > 비니/베레모\n",
        encoding="utf-8",
    )
    return emdb.ExtendedMasterDB.from_csv(cat_csv, kw_csv)


def test_extended_master_db_resolve_waterfall(sample_ext_db):
    # 1단계 EX
    hits = sample_ext_db.resolve_ranked("비니")
    assert len(hits) > 0
    assert hits[0][0] == "STD_006"
    assert "EX" in hits[0][1]

    # 2단계 SY
    hits_sy = sample_ext_db.resolve_ranked("베레모")
    assert len(hits_sy) > 0
    assert hits_sy[0][0] == "STD_006"
    assert "SY" in hits_sy[0][1]


def test_extended_master_db_expand_terms(sample_ext_db):
    terms = sample_ext_db.expand_terms("셔츠")
    assert "블라우스/셔츠" in terms or "블라우스" in terms or "셔츠" in terms
    assert "여성의류" in terms or "패션의류" in terms


def test_find_category_with_extended_db(sample_ext_db):
    paths = [
        "패션의류 > 여성의류 > 블라우스",
        "잡화 > 모자 > 털모자",
    ]
    # "베레모" 필터 -> 엑셀에 베레모는 없지만 ext_db에서 "비니/베레모"->"모자" 범주를 확장하여 매핑
    cat, step = mt.find_category("여성-모자-베레모", paths, ext_db=sample_ext_db)
    assert cat == "잡화 > 모자 > 털모자" or "모자" in cat


def test_real_extended_master_db_json_load():
    db = mc.build_extended_master_db()
    assert len(db.categories) == 14207
    assert len(db.keywords) == 29999
    # check sample queries
    assert len(db.resolve_ranked("비니")) > 0
    assert len(db.resolve_ranked("구두")) > 0
    assert len(db.expand_terms("청바지")) > 0
