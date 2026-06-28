"""Hilfe & Diagnose — wenn etwas bricht, kann der Arzt mit einem Klick ein
PHI-freies Diagnose-Paket an den Betreuer (support_email) schicken.

Das Paket enthält NUR: das Ablauf-Log des letzten Laufs (ohne Patienteninhalte)
und – unter Windows – einen frischen UIA-Baum-Dump von PowerChart (Struktur,
keine Inhalte). Damit kann der Betreuer das Rezept aus der Ferne korrigieren.
"""
from __future__ import annotations

import sys
import webbrowser
import zipfile
from pathlib import Path

from .log import RUNS, _basis


def _letzter_run() -> Path | None:
    if not RUNS.exists():
        return None
    runs = sorted([p for p in RUNS.iterdir() if p.is_dir()])
    return runs[-1] if runs else None


def paket_schnueren(titel_enthaelt: str = "PowerChart") -> Path:
    """Diagnose-ZIP erstellen und Pfad zurückgeben (PHI-frei)."""
    ziel = _basis() / "diagnose.zip"

    # Frischen UIA-Baum dumpen (nur Struktur), falls Windows
    if sys.platform == "win32":
        try:
            from .inspect_uia import dump
            dump(titel_enthaelt)
        except Exception:                # noqa: BLE001
            pass

    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as z:
        letzter = _letzter_run()
        if letzter:
            for f in letzter.glob("*.txt"):       # nur Logs, keine Screenshots mit PHI
                z.write(f, f"{letzter.name}/{f.name}")
        # zusätzlich die letzten paar inspect-Logs
        if RUNS.exists():
            for d in sorted(RUNS.glob("*inspect*"))[-2:]:
                for f in d.glob("*.txt"):
                    z.write(f, f"{d.name}/{f.name}")
    return ziel


def hilfe_anfordern(support_email: str, titel_enthaelt: str = "PowerChart") -> Path:
    """Paket bauen, Ordner öffnen (zum Anhängen) und Mail-Entwurf öffnen."""
    paket = paket_schnueren(titel_enthaelt)

    # Ordner öffnen, damit der Arzt die Datei anhängen kann
    try:
        if sys.platform == "win32":
            import os
            os.startfile(paket.parent)            # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            import subprocess
            subprocess.run(["open", str(paket.parent)])
    except Exception:                    # noqa: BLE001
        pass

    if support_email:
        betreff = "PraxisHand%20-%20Hilfe%20benoetigt"
        body = ("Es%20gab%20ein%20Problem.%20Bitte%20die%20Datei%20"
                f"{paket.name}%20aus%20dem%20geoeffneten%20Ordner%20anhaengen.")
        webbrowser.open(f"mailto:{support_email}?subject={betreff}&body={body}")
    return paket
