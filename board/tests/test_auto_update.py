"""망고보드 자동 반영(아이콘 실행 시) 테스트 — 네트워크 없이 검증."""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

BOARD_DIR = Path(__file__).resolve().parents[1]
ROOT = BOARD_DIR.parent
sys.path.insert(0, str(BOARD_DIR))

import auto_update as au  # noqa: E402


def test_version_compare():
    assert au.is_newer("1.6.2", "1.6.1") is True
    assert au.is_newer("1.6.1", "1.6.1") is False
    assert au.is_newer("1.10.0", "1.9.9") is True
    assert au.is_newer("", "1.0.0") is False
    assert au.is_newer("1.0.0", "") is True


def test_parse_version_from_version_txt():
    assert au.parse_version("버전 1.6.2 (Python 보드)\n업데이트: …") == "1.6.2"
    assert au.parse_version("version 2.1.56") == "2.1.56"
    assert au.parse_version("설명만 있음") == ""


def test_local_version_reads_own_file():
    assert au.local_version(ROOT) == au.parse_version(
        (ROOT / "VERSION.txt").read_text(encoding="utf-8")
    )


def test_protected_paths_are_not_overwritten():
    assert au.is_protected("run-logs/2026/shot.png") is True
    assert au.is_protected("P2/.chrome-profile/Default/Cookies") is True
    assert au.is_protected("P3_필터단위_수집조건수정/.site_options.json") is True
    assert au.is_protected("입력.xlsx") is True
    assert au.is_protected("망고보드.lnk") is True
    assert au.is_protected("board/app.py") is False


def _make_zip(path: Path, files: dict[str, str], top: str) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, body in files.items():
            zf.writestr(f"{top}/{name}", body)


def test_apply_zip_from_parent_repo_subdir(tmp_path):
    zip_path = tmp_path / "src.zip"
    _make_zip(
        zip_path,
        {
            "Mango_Helper_AI_Board/VERSION.txt": "버전 9.9.9 (Python 보드)\n",
            "Mango_Helper_AI_Board/board/app.py": "print('new')\n",
            "Mango_Helper_AI_Board/run-logs/old.log": "지워지면 안 됨",
            "P2/collect.py": "AI보드 파일 — 복사 대상 아님",
        },
        top="AI_Program_Main_Board-main",
    )
    root = tmp_path / "board_root"
    (root / "run-logs").mkdir(parents=True)
    (root / "run-logs" / "old.log").write_text("기존 로그", encoding="utf-8")

    written = au.apply_zip(zip_path, root, "Mango_Helper_AI_Board")

    assert written == 2  # VERSION.txt + board/app.py (로그는 보호)
    assert au.local_version(root) == "9.9.9"
    assert (root / "board" / "app.py").read_text(encoding="utf-8") == "print('new')\n"
    assert (root / "run-logs" / "old.log").read_text(encoding="utf-8") == "기존 로그"
    assert not (root / "P2" / "collect.py").exists()


def test_apply_zip_from_standalone_repo_root(tmp_path):
    zip_path = tmp_path / "src.zip"
    _make_zip(
        zip_path,
        {"VERSION.txt": "버전 2.0.0 (Python 보드)\n", "run.bat": "@echo off\n"},
        top="Mango_Helper_AI_Board-main",
    )
    root = tmp_path / "root"
    root.mkdir()
    assert au.apply_zip(zip_path, root, "") == 2
    assert au.local_version(root) == "2.0.0"


def test_pick_source_takes_highest_version(monkeypatch):
    texts = {
        au.sources()[0]["version_url"]: "버전 1.0.0 (Python 보드)",
        au.sources()[1]["version_url"]: "버전 1.6.2 (Python 보드)",
    }
    monkeypatch.setattr(au, "fetch_text", lambda url: texts.get(url, ""))
    src, ver = au.pick_source()
    assert ver == "1.6.2"
    assert src["subdir"] == au.PARENT_SUBDIR


def test_update_skips_when_already_latest(monkeypatch, tmp_path):
    (tmp_path / "VERSION.txt").write_text("버전 1.6.2 (Python 보드)\n", encoding="utf-8")
    monkeypatch.setattr(au, "pick_source", lambda: (au.sources()[1], "1.6.2"))
    result = au.update_if_newer(tmp_path)
    assert result["updated"] is False
    assert "최신" in result["message"]


def test_update_offline_keeps_running(monkeypatch, tmp_path):
    (tmp_path / "VERSION.txt").write_text("버전 1.6.2 (Python 보드)\n", encoding="utf-8")
    monkeypatch.setattr(au, "pick_source", lambda: (None, ""))
    result = au.update_if_newer(tmp_path)
    assert result["updated"] is False
    assert "그대로 실행" in result["message"]


def test_update_downloads_and_applies(monkeypatch, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "VERSION.txt").write_text("버전 1.5.1 (Python 보드)\n", encoding="utf-8")

    zip_path = tmp_path / "remote.zip"
    _make_zip(
        zip_path,
        {"Mango_Helper_AI_Board/VERSION.txt": "버전 1.6.2 (Python 보드)\n"},
        top="AI_Program_Main_Board-main",
    )

    monkeypatch.setattr(au, "pick_source", lambda: (au.sources()[1], "1.6.2"))
    monkeypatch.setattr(au, "git_pull", lambda _root: False)
    monkeypatch.setattr(au, "download_zip", lambda _url, _dir: zip_path)

    result = au.update_if_newer(root)
    assert result["updated"] is True
    assert result["before"] == "1.5.1"
    assert result["after"] == "1.6.2"
    assert "자동 반영 완료" in result["message"]


def test_check_only_does_not_write(monkeypatch, tmp_path):
    (tmp_path / "VERSION.txt").write_text("버전 1.5.1 (Python 보드)\n", encoding="utf-8")
    monkeypatch.setattr(au, "pick_source", lambda: (au.sources()[1], "1.6.2"))
    called = []
    monkeypatch.setattr(au, "download_zip", lambda *a: called.append(a))
    result = au.update_if_newer(tmp_path, check_only=True)
    assert result["updated"] is False
    assert called == []
    assert au.local_version(tmp_path) == "1.5.1"


def test_git_repo_dir_finds_parent_repo(tmp_path):
    repo = tmp_path / "AI_Program_Main_Board"
    (repo / ".git").mkdir(parents=True)
    sub = repo / "Mango_Helper_AI_Board"
    sub.mkdir()
    assert au.git_repo_dir(sub) == repo
    assert au.git_repo_dir(tmp_path) is None


def test_run_bat_calls_auto_update():
    text = (ROOT / "run.bat").read_text(encoding="utf-8")
    assert "board\\auto_update.py" in text
    assert "--noupdate" in text  # 생략 옵션
