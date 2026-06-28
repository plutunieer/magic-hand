"""macOS-Hand für Microsoft Word — über AppleScript.

Test-Pendant zur Windows-EMR-Hand: liest Text aus dem GEÖFFNETEN Word-Dokument
und schreibt Text zurück. Steuert die laufende Word-App (nicht die Datei) über
die offizielle AppleScript-Schnittstelle von Word — robust, kein UIA nötig.

Nur macOS. Word muss laufen mit einem offenen Dokument.
"""
from __future__ import annotations

import os
import subprocess
import tempfile


def _osa(script: str) -> str:
    r = subprocess.run(["osascript", "-e", script],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "AppleScript-Fehler")
    return r.stdout.rstrip("\n")


def lese_dokument() -> str:
    """Gesamten Text des aktiven Word-Dokuments lesen."""
    return _osa(
        'tell application "Microsoft Word" to '
        'return content of text object of active document'
    )


def schreibe_ende(text: str) -> None:
    """Text ans Ende des aktiven Dokuments anhängen (über temp. Datei, damit
    Sonderzeichen/Zeilenumbrüche sicher übergeben werden)."""
    tmp = tempfile.NamedTemporaryFile("w", suffix=".txt",
                                      delete=False, encoding="utf-8")
    tmp.write(text)
    tmp.close()
    try:
        _osa(f'''
        set neu to (read POSIX file "{tmp.name}" as «class utf8»)
        tell application "Microsoft Word"
            set t to content of text object of active document
            set content of text object of active document to t & return & return & neu
        end tell
        ''')
    finally:
        os.unlink(tmp.name)
