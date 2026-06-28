"""PHI-freies Logging für die Praxis-Hand.

WICHTIG: Es wird NIE der Inhalt von Patienten-Einträgen geloggt — nur
Ablauf-Schritte, Zähler und Fehler. Bei medizinischen Daten ist das Pflicht.
Jeder Lauf bekommt einen Ordner unter runs/<zeitstempel>/ mit log.txt und
optionalen Fehler-Screenshots.
"""
from __future__ import annotations

import datetime
from pathlib import Path


def _basis() -> Path:
    """Schreib-Basis: neben der .exe (PyInstaller) bzw. im Projektordner."""
    import sys
    if getattr(sys, "frozen", False):           # läuft als PyInstaller-.exe
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


RUNS = _basis() / "runs"


class Log:
    def __init__(self, tag: str = "") -> None:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in tag)[:40]
        self.dir = RUNS / (stamp + (f"-{safe}" if safe else ""))
        self.dir.mkdir(parents=True, exist_ok=True)
        self.f = open(self.dir / "log.txt", "a", encoding="utf-8")
        self.line(f"=== Praxis-Hand {stamp} tag={tag!r} ===")

    def line(self, msg: str = "") -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        z = f"[{ts}] {msg}" if msg else ""
        print(z)
        self.f.write(z + "\n")
        self.f.flush()

    def count(self, was: str, n: int) -> None:
        """Nur Zähler loggen (keine Inhalte)."""
        self.line(f"  {was}: {n}")

    def shot(self, name: str, png_bytes: bytes | None = None) -> None:
        """Optionaler Fehler-Screenshot (Bytes aus mss/Playwright)."""
        try:
            if png_bytes:
                (self.dir / f"{name}.png").write_bytes(png_bytes)
                self.line(f"   (Screenshot: {name}.png)")
        except Exception as e:                   # noqa: BLE001
            self.line(f"   (Screenshot {name} fehlgeschlagen: {e})")

    def close(self) -> None:
        self.line("=== Ende ===")
        self.f.close()
