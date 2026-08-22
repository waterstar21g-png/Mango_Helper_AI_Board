"""망고보드 바탕화면 아이콘 생성 테스트."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

BOARD_DIR = Path(__file__).resolve().parents[1]
ROOT = BOARD_DIR.parent
sys.path.insert(0, str(BOARD_DIR))
sys.path.insert(0, str(ROOT / "scripts"))

import desktop_icon  # noqa: E402
import launch  # noqa: E402


def _fake_desktops(tmp_path: Path) -> dict[str, str]:
    home = tmp_path / "user"
    (home / "Desktop").mkdir(parents=True)
    (home / "OneDrive" / "바탕 화면").mkdir(parents=True)
    return {"USERPROFILE": str(home), "OneDrive": str(home / "OneDrive")}


def test_desktop_dirs_collects_existing_only(tmp_path):
    env = _fake_desktops(tmp_path)
    dirs = desktop_icon.desktop_dirs(env)
    names = [d.name for d in dirs]
    assert "Desktop" in names
    assert "바탕 화면" in names
    assert len(dirs) == len(set(dirs))  # 중복 없음
    assert all(d.is_dir() for d in dirs)


def test_desktop_dirs_empty_env_is_safe():
    assert desktop_icon.desktop_dirs({}) == []


def test_shortcut_paths_default_is_single_executable_icon(monkeypatch, tmp_path):
    env = _fake_desktops(tmp_path)
    monkeypatch.setattr(desktop_icon, "registry_desktop", lambda runner=None: None)
    paths = desktop_icon.shortcut_paths(ROOT, env)
    assert len(paths) == 1
    assert paths[0].name == "망고보드.lnk"
    assert paths[0].parent == desktop_icon.desktop_dirs(env)[0]


def test_shortcut_paths_all_targets_includes_project_copy(monkeypatch, tmp_path):
    env = _fake_desktops(tmp_path)
    paths = desktop_icon.shortcut_paths(ROOT, env, all_targets=True)
    assert all(p.name == "망고보드.lnk" for p in paths)
    assert paths[-1] == ROOT / "망고보드.lnk"  # 드래그용 사본
    assert len(paths) == len(desktop_icon.desktop_dirs(env)) + 1


def test_primary_desktop_prefers_registry_value(tmp_path):
    real = tmp_path / "OneDriveDesktop"
    real.mkdir()

    class Proc:
        stdout = f"\r\n    Desktop    REG_SZ    {real}\r\n".encode("cp949")

    picked = desktop_icon.primary_desktop({}, runner=lambda _args: Proc())
    assert picked == real


def test_parse_reg_desktop_handles_spaces_in_path():
    line = "    Desktop    REG_SZ    C:\\Users\\me\\OneDrive\\바탕 화면\r\n"
    assert desktop_icon.parse_reg_desktop(line) == "C:\\Users\\me\\OneDrive\\바탕 화면"
    assert desktop_icon.parse_reg_desktop("Personal REG_SZ C:\\docs") == ""


def test_create_reports_when_no_desktop_found(monkeypatch, tmp_path):
    (tmp_path / "run.bat").write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr(desktop_icon, "is_windows", lambda: True)
    monkeypatch.setattr(desktop_icon, "shortcut_paths", lambda *a, **k: [])
    result = desktop_icon.create(tmp_path)
    assert result["ok"] is False
    assert "바탕화면" in result["message"]


def test_build_powershell_points_at_run_bat(tmp_path):
    targets = [tmp_path / "a" / "망고보드.lnk", tmp_path / "b" / "망고보드.lnk"]
    script = desktop_icon.build_powershell(ROOT, targets)
    assert str(ROOT / "run.bat") in script
    assert script.count("CreateShortcut") == len(targets)
    assert script.count("$sc.Save()") == len(targets)
    assert "imageres.dll,171" in script
    assert "shell32.dll,44" in script  # 폴백
    for t in targets:
        assert str(t) in script


def test_build_powershell_pins_first_target(tmp_path):
    lnk = tmp_path / "망고보드.lnk"
    script = desktop_icon.build_powershell(ROOT, [lnk])
    assert "User Pinned\\TaskBar" in script
    assert "Shell.Application" in script
    assert "$verb.DoIt()" in script
    assert "GetFolderPath('Programs')" in script  # 시작메뉴 등록
    assert desktop_icon.PIN_VERB_PATTERN in script


def test_build_powershell_can_skip_pinning(tmp_path):
    script = desktop_icon.build_powershell(ROOT, [tmp_path / "망고보드.lnk"], pin=False)
    assert "Shell.Application" not in script
    assert "CreateShortcut" in script


def test_pin_verb_pattern_covers_korean_and_english():
    import re

    pat = re.compile(desktop_icon.PIN_VERB_PATTERN)
    assert pat.search("작업 표시줄에 고정")
    assert pat.search("작업표시줄에 고정")
    assert pat.search("Pin to taskbar")


def test_create_reports_pinned(monkeypatch, tmp_path):
    (tmp_path / "run.bat").write_text("@echo off\n", encoding="utf-8")
    lnk = tmp_path / "망고보드.lnk"
    monkeypatch.setattr(desktop_icon, "is_windows", lambda: True)
    monkeypatch.setattr(desktop_icon, "shortcut_paths", lambda *a, **k: [lnk])

    class Proc:
        stdout = f"OK {lnk}\nPIN {lnk}\n".encode("utf-8")
        stderr = b""

    monkeypatch.setattr(desktop_icon.subprocess, "run", lambda *a, **k: Proc())
    result = desktop_icon.create(tmp_path)
    assert result["ok"] is True
    assert result["pinned"] == [str(lnk)]
    assert "작업표시줄에 고정했습니다" in result["message"]


def test_create_explains_when_pin_blocked(monkeypatch, tmp_path):
    (tmp_path / "run.bat").write_text("@echo off\n", encoding="utf-8")
    lnk = tmp_path / "망고보드.lnk"
    monkeypatch.setattr(desktop_icon, "is_windows", lambda: True)
    monkeypatch.setattr(desktop_icon, "shortcut_paths", lambda *a, **k: [lnk])

    class Proc:
        stdout = f"OK {lnk}\nPINVERB none\n".encode("utf-8")
        stderr = b""

    monkeypatch.setattr(desktop_icon.subprocess, "run", lambda *a, **k: Proc())
    result = desktop_icon.create(tmp_path)
    assert result["ok"] is True
    assert result["pinned"] == []
    assert "우클릭" in result["message"]


def test_build_powershell_escapes_single_quote(tmp_path):
    odd = tmp_path / "it's" / "망고보드.lnk"
    script = desktop_icon.build_powershell(ROOT, [odd])
    assert "it''s" in script


def test_powershell_command_is_utf16_encoded(tmp_path):
    script = desktop_icon.build_powershell(ROOT, [tmp_path / "망고보드.lnk"])
    cmd = desktop_icon.powershell_command(script)
    assert cmd[0] == "powershell"
    assert "-EncodedCommand" in cmd
    decoded = base64.b64decode(cmd[-1]).decode("utf-16-le")
    assert decoded == script


def test_create_without_run_bat_reports_folder(tmp_path):
    result = desktop_icon.create(tmp_path)
    assert result["ok"] is False
    assert "run.bat" in result["message"]
    assert result["created"] == []


def test_create_on_non_windows_is_reported_not_raised(monkeypatch, tmp_path):
    (tmp_path / "run.bat").write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr(desktop_icon, "is_windows", lambda: False)
    result = desktop_icon.create(tmp_path)
    assert result["ok"] is False
    assert "Windows" in result["message"]


def test_icon_module_uses_own_root_only():
    assert desktop_icon.board_root() == ROOT
    assert (desktop_icon.board_root() / "board" / "desktop_icon.py").is_file()


def test_launch_build_command_by_suffix(tmp_path):
    assert launch.build_command(tmp_path / "a.py", ["x"])[0] == sys.executable
    assert launch.build_command(tmp_path / "a.ps1", [])[0] == "powershell"
    assert "-File" in launch.build_command(tmp_path / "a.ps1", [])
    assert launch.build_command(tmp_path / "a.bat", [])[:2] == ["cmd", "/c"]


def test_installers_delegate_icon_creation():
    """바로가기 생성 구현이 갈라지지 않도록 — 설치 스크립트는 desktop_icon.py 만 호출."""
    for name in ("scripts/install-all.ps1", "scripts/setup-pc.ps1"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "desktop_icon.py" in text, f"{name} 이 아이콘 생성을 위임하지 않음"
        assert "CreateShortcut" not in text, f"{name} 에 별도 바로가기 생성 구현 남음"


def test_registry_has_desktop_icon_entry():
    data = launch.load_registry()
    entry = next(p for p in data["programs"] if p["id"] == "desktop_icon")
    assert (ROOT / entry["script"]).is_file()
    assert (ROOT / entry["launcher"]).is_file()
