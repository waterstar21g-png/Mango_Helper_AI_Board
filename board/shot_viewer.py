"""1·2행 전과정 스크린샷 뷰어 (Tkinter)."""

from __future__ import annotations

import json
import os
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


def latest_shot_dir(root: Path) -> Path | None:
    base = root / "P2" / "run-logs"
    if not base.is_dir():
        return None
    dirs = [p for p in base.iterdir() if p.is_dir()]
    if not dirs:
        return None
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs[0]


def latest_p3_shot_dir(root: Path) -> Path | None:
    """P3_필터_갱신/run-logs 최신 폴더."""
    base = root / "P3_필터_갱신" / "run-logs"
    if not base.is_dir():
        return None
    dirs = [p for p in base.iterdir() if p.is_dir()]
    if not dirs:
        return None
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs[0]


def load_shot_items(shot_dir: Path) -> list[dict]:
    idx = shot_dir / "shots.json"
    if idx.is_file():
        try:
            data = json.loads(idx.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except Exception:
            pass
    items: list[dict] = []
    for i, p in enumerate(sorted(shot_dir.glob("*.png")), start=1):
        items.append(
            {
                "step": i,
                "label": p.stem,
                "file": p.name,
                "path": str(p),
            }
        )
    return items


class ShotViewer(tk.Toplevel):
    """좌측 목록 + 우측 이미지 미리보기."""

    def __init__(self, master: tk.Misc, shot_dir: Path, *, title_prefix: str | None = None) -> None:
        super().__init__(master)
        self.shot_dir = Path(shot_dir)
        kind = title_prefix or _viewer_kind(self.shot_dir)
        self.title(f"{kind} — {self.shot_dir.name}")
        self.geometry("1100x720")
        self.minsize(800, 500)
        self._photo: tk.PhotoImage | None = None
        self._items = load_shot_items(self.shot_dir)

        head = tk.Frame(self, bg="#164a59", pady=8)
        head.pack(fill="x")
        tk.Label(
            head,
            text=f"샷 폴더: {self.shot_dir}  ({len(self._items)}장) · {kind}",
            fg="white",
            bg="#164a59",
            font=("Malgun Gothic", 10, "bold"),
            anchor="w",
        ).pack(fill="x", padx=10)
        btns = tk.Frame(head, bg="#164a59")
        btns.pack(fill="x", padx=10, pady=(4, 0))
        tk.Button(btns, text="이전", command=self._prev).pack(side="left")
        tk.Button(btns, text="다음", command=self._next).pack(side="left", padx=6)
        tk.Button(btns, text="HTML 갤러리 열기", command=self._open_html).pack(
            side="left", padx=6
        )
        tk.Button(btns, text="폴더 열기", command=self._open_folder).pack(side="left")

        body = tk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=8)

        left = tk.Frame(body, width=280)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self.listbox = tk.Listbox(left, font=("Malgun Gothic", 10), exportselection=False)
        sb = tk.Scrollbar(left, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        right = tk.Frame(body, bg="#0f172a")
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.caption = tk.Label(
            right, text="", bg="#0f172a", fg="#93c5fd", font=("Malgun Gothic", 11, "bold")
        )
        self.caption.pack(fill="x", pady=(0, 6))
        self.canvas = tk.Label(right, bg="#0f172a")
        self.canvas.pack(fill="both", expand=True)

        for it in self._items:
            step = it.get("step", "")
            label = it.get("label") or it.get("file") or ""
            ord_n = it.get("ordinal") or ""
            cat = it.get("category") or ""
            prefix = f"{step:02d}. " if step != "" else ""
            mid = f"[입력#{ord_n}] " if ord_n else ""
            cat_bit = f" · {cat}" if cat else ""
            self.listbox.insert("end", f"{prefix}{mid}{label}{cat_bit}")

        if self._items:
            self.listbox.selection_set(0)
            self._show_index(0)
        else:
            self.caption.configure(text="(스크린샷 없음)")

    def _on_select(self, _evt=None) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        self._show_index(sel[0])

    def _show_index(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._items):
            return
        it = self._items[idx]
        path = Path(it.get("path") or (self.shot_dir / it["file"]))
        label = it.get("label") or path.name
        cat = it.get("category") or ""
        url = it.get("url") or ""
        cap = f"{it.get('step', idx + 1)}. {label}  —  {path.name}"
        if cat or url:
            cap += f"\n최종 카테고리명={cat}\n최종 카테고리 URL주소={url}"
        self.caption.configure(text=cap, justify="left", anchor="w")
        if not path.is_file():
            self.canvas.configure(image="", text=f"파일 없음:\n{path}", fg="white")
            return
        try:
            img = tk.PhotoImage(file=str(path))
            # 창에 맞게 축소 (정수 배수 subsample)
            max_w, max_h = 820, 520
            factor = max(1, (img.width() + max_w - 1) // max_w, (img.height() + max_h - 1) // max_h)
            if factor > 1:
                img = img.subsample(factor, factor)
            self._photo = img
            self.canvas.configure(image=self._photo, text="")
        except Exception as e:
            self.canvas.configure(image="", text=f"이미지 표시 실패:\n{e}", fg="white")

    def _prev(self) -> None:
        sel = self.listbox.curselection()
        idx = int(sel[0]) if sel else 0
        idx = max(0, idx - 1)
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(idx)
        self.listbox.see(idx)
        self._show_index(idx)

    def _next(self) -> None:
        sel = self.listbox.curselection()
        idx = int(sel[0]) if sel else -1
        idx = min(len(self._items) - 1, idx + 1)
        if idx < 0:
            return
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(idx)
        self.listbox.see(idx)
        self._show_index(idx)

    def _open_html(self) -> None:
        html = self.shot_dir / "index.html"
        if not html.is_file():
            messagebox.showinfo("안내", f"갤러리 없음:\n{html}", parent=self)
            return
        webbrowser.open(html.as_uri())

    def _open_folder(self) -> None:
        path = str(self.shot_dir)
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys_platform_darwin():
                import subprocess

                subprocess.Popen(["open", path])
            else:
                import subprocess

                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("폴더 열기 실패", str(e), parent=self)


def sys_platform_darwin() -> bool:
    return os.name == "posix" and hasattr(os, "uname") and os.uname().sysname == "Darwin"


def _viewer_kind(shot_dir: Path) -> str:
    s = str(shot_dir).replace("\\", "/")
    if "P3_" in s or "필터_갱신" in s:
        return "P3 필터갱신 스크린샷"
    return "1·2행 전과정 스크린샷"


def open_shot_viewer(
    master: tk.Misc,
    shot_dir: Path | None = None,
    root: Path | None = None,
    *,
    prefer_p3: bool = False,
    empty_hint: str | None = None,
) -> None:
    folder = shot_dir
    if folder is None and root is not None:
        folder = latest_p3_shot_dir(root) if prefer_p3 else latest_shot_dir(root)
    if folder is None or not Path(folder).is_dir():
        hint = empty_hint or (
            "P3 스크린샷 폴더가 없습니다.\n작업시작 후 필터 일치 행이 있어야 샷이 생성됩니다."
            if prefer_p3
            else "스크린샷 폴더가 없습니다.\n1행 검증 수집을 먼저 실행하세요."
        )
        messagebox.showinfo("안내", hint, parent=master)
        return
    ShotViewer(master, Path(folder))
