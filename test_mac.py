"""TEST-SZENARIO (macOS): Word  ->  ChatGPT  ->  Word.

Liest den Text aus dem geöffneten Word-Dokument, schickt ihn an ChatGPT, zeigt
die Antwort zur Freigabe und hängt sie ans Word-Dokument an. Beweist den ganzen
Roundtrip lokal auf dem Mac (ohne Windows/PowerChart).

EINMAL anmelden:
    python test_mac.py --login         # Browser öffnet -> bei ChatGPT einloggen, Fenster schließen

DANN testen (Word offen mit einem Dokument):
    python test_mac.py
"""
from __future__ import annotations

import sys

from praxishand.hand_dox import DoxHand, login
from praxishand.hand_word_mac import lese_dokument, schreibe_ende
from praxishand.log import Log

CHATGPT = {
    "url": "https://chatgpt.com",
    "eingabe": [
        ["css", "#prompt-textarea"],
        ["role", "textbox", ""],
        ["css", "textarea"],
    ],
    "senden": [
        ["css", "[data-testid='send-button']"],
        ["role", "button", "Send"],
    ],
    "antwort": [
        ["css", "[data-message-author-role='assistant']"],
        ["css", ".markdown"],
    ],
    "timeout_antwort_sek": 180,
    "prompt_vorlage": (
        "Hier ist der Inhalt eines Word-Dokuments. Fasse die wichtigsten Punkte "
        "in kurzen Stichpunkten zusammen.\n\n--- DOKUMENT ---\n{daten}\n--- ENDE ---"
    ),
}


def main() -> int:
    if "--login" in sys.argv:
        login(headless=False, url=CHATGPT["url"])
        return 0

    log = Log("test-mac")
    try:
        log.line("Lese Word-Dokument …")
        daten = lese_dokument()
        log.count("Dokument-Zeichen", len(daten))
        if not daten.strip():
            log.line("Word-Dokument ist leer / nicht gefunden.")
            return 1

        prompt = CHATGPT["prompt_vorlage"].replace("{daten}", daten)
        log.line("Frage ChatGPT …")
        with DoxHand(CHATGPT, log, headless=False) as dox:
            antwort = dox.frage(prompt)
        if not antwort.strip():
            log.line("Leere Antwort von ChatGPT.")
            return 1

        print("\n----- ANTWORT VON CHATGPT -----\n")
        print(antwort)
        print("\n-------------------------------")
        if input("Ins Word-Dokument übernehmen? [j/N] ").strip().lower() not in ("j", "y", "ja", "yes"):
            log.line("Abgebrochen — nichts geschrieben.")
            return 0

        schreibe_ende(antwort)
        log.line("FERTIG — Antwort ins Word-Dokument geschrieben.")
        return 0
    except Exception as e:                # noqa: BLE001
        log.line(f"FEHLER: {type(e).__name__}: {e}")
        return 1
    finally:
        log.close()


if __name__ == "__main__":
    sys.exit(main())
