"""더망고 로그인 ID/PW 로컬 저장·로드 (P2/.tmg_credentials.json)."""

from __future__ import annotations

import base64
import json
from pathlib import Path

CREDS_PATH = Path(__file__).resolve().parent / ".tmg_credentials.json"


def _obfuscate(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def _deobfuscate(s: str) -> str:
    return base64.b64decode(s.encode("ascii")).decode("utf-8")


def creds_path() -> Path:
    return CREDS_PATH


def has_saved_credentials() -> bool:
    uid, pw = load_credentials()
    return bool(uid and pw)


def load_credentials() -> tuple[str, str]:
    if not CREDS_PATH.is_file():
        return "", ""
    try:
        data = json.loads(CREDS_PATH.read_text(encoding="utf-8"))
        uid = _deobfuscate(str(data.get("id_b64", "")))
        pw = _deobfuscate(str(data.get("pw_b64", "")))
        return uid.strip(), pw
    except Exception:
        return "", ""


def save_credentials(user_id: str, password: str) -> Path:
    uid = (user_id or "").strip()
    pw = password or ""
    if not uid or not pw:
        raise ValueError("아이디와 비밀번호가 모두 필요합니다.")
    payload = {
        "id_b64": _obfuscate(uid),
        "pw_b64": _obfuscate(pw),
        "note": "local only — do not commit",
    }
    CREDS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return CREDS_PATH


def clear_credentials() -> None:
    if CREDS_PATH.is_file():
        CREDS_PATH.unlink()
