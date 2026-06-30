"""Generische Mac-Hand — bedient BELIEBIGE Mac-Apps über "System Events".

System Events ist Apples eingebaute Bedienhilfe-Schnittstelle: damit kann man in
jeder App Knöpfe klicken, in Felder tippen, Texte/Listen lesen und Menüs bedienen
— ohne pro App etwas zu installieren. Reicht das bei einer App nicht (z. B. Word),
nutzt man zusätzlich deren eigenes AppleScript (siehe hand_word_mac.py).

Voraussetzung: Terminal/Python braucht EINMAL die Berechtigung
"Bedienungshilfen" (Systemeinstellungen → Datenschutz → Bedienungshilfen).

Grundbewegungen: apps · inspect · klick · tippe · lese
"""
from __future__ import annotations

import subprocess
import sys


def _osa(script: str) -> str:
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "AppleScript-Fehler")
    return r.stdout.rstrip("\n")


def apps() -> str:
    """Laufende Apps mit Fenster (zum Aussuchen)."""
    return _osa('tell application "System Events" to '
                'return name of (processes whose background only is false)')


def inspect(app: str) -> str:
    """Was im vordersten Fenster der App bedienbar/lesbar ist (Probe fürs Anlernen)."""
    return _osa(f'''
    tell application "System Events" to tell process "{app}"
        set out to "App: {app}" & linefeed
        try
            set out to out & "Fenster: " & (name of windows) & linefeed
        end try
        try
            set out to out & "Knöpfe: " & (name of buttons of window 1) & linefeed
        end try
        try
            set out to out & "Textfelder: " & (count of text fields of window 1) & linefeed
        end try
        try
            set out to out & "Textbereiche: " & (count of text areas of window 1) & linefeed
        end try
        try
            set out to out & "Menüs: " & (name of menu bar items of menu bar 1) & linefeed
        end try
        return out
    end tell''')


def klick(app: str, name: str) -> None:
    """Knopf mit Beschriftung `name` im vordersten Fenster klicken."""
    _osa(f'tell application "System Events" to tell process "{app}" '
         f'to click (first button of window 1 whose name is "{name}")')


def menue(app: str, menu: str, eintrag: str) -> None:
    """Menüpunkt wählen (z. B. menue("TextEdit","Format","Fett"))."""
    _osa(f'''tell application "System Events" to tell process "{app}"
        click menu item "{eintrag}" of menu "{menu}" of menu bar 1
    end tell''')


def tippe(app: str, text: str) -> None:
    """Text in die App tippen (App wird vorher aktiviert)."""
    safe = text.replace('"', '\\"')
    _osa(f'''tell application "{app}" to activate
    delay 0.3
    tell application "System Events" to keystroke "{safe}"''')


def lese(app: str) -> str:
    """Texte aus Feldern/Bereichen des vordersten Fensters lesen."""
    return _osa(f'''
    tell application "System Events" to tell process "{app}"
        set out to ""
        try
            set out to out & (value of text areas of window 1 as string)
        end try
        try
            set out to out & (value of text fields of window 1 as string)
        end try
        return out
    end tell''')


# Mini-CLI:  python -m praxishand.hand_mac inspect "TextEdit"
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "apps"
    arg = sys.argv[2] if len(sys.argv) > 2 else ""
    try:
        if cmd == "apps":
            print(apps())
        elif cmd == "inspect":
            print(inspect(arg))
        elif cmd == "lese":
            print(lese(arg))
        else:
            print("Befehle: apps | inspect <App> | lese <App>")
    except Exception as e:                # noqa: BLE001
        print(f"FEHLER: {e}")
