"""Orchestrator — spielt die Schritt-Folge des Rezepts ab.

Bei greif_methode == "uia": kleiner Abspieler (Interpreter) der Schritte. Jeder
Schritt ist eine Aktion auf der EMR-Hand; Sonderschritte sind `an_dox` (Übergabe
an Doximity GPT) und `report_schreiben` (mit Pflicht-Freigabe davor).

Bei greif_methode == "ocr": einfacher 3-Schritt-Pfad (sammeln → dox → schreiben)
über die OCR-Hand (die kennt keine Klick-Aktionen).

Datenfluss über `vars`:  lese_liste -> vars["daten"];  an_dox -> vars["antwort"].
"""
from __future__ import annotations

from typing import Callable

from .hand_dox import DoxHand
from .log import Log
from .rezept import Rezept

# (vorgeschlagener_text) -> (freigegeben, finaler_text)
ReviewCallback = Callable[[str], tuple[bool, str]]


def terminal_review(text: str) -> tuple[bool, str]:
    print("\n----- VORSCHLAG VON DOXIMITY GPT -----\n")
    print(text)
    print("\n--------------------------------------")
    a = input("Übernehmen? [j/N] ").strip().lower()
    return (a in ("j", "y", "ja", "yes"), text)


def _an_dox(rezept: Rezept, daten: str, log: Log, headless: bool) -> str:
    with DoxHand(rezept.dox, log, headless=headless) as dox:
        return dox.frage(rezept.prompt(daten))


def _freigeben(text: str, rezept: Rezept, review: ReviewCallback | None,
               log: Log) -> tuple[bool, str]:
    if not rezept.freigabe_pflicht:
        return True, text
    log.line("  warte auf Freigabe durch den Arzt …")
    ok, final = (review or terminal_review)(text)
    if not ok:
        log.line("  Abgebrochen — keine Freigabe. Nichts ins EMR geschrieben.")
    return ok, final


def _lauf_uia(rezept: Rezept, review, headless_dox, log: Log) -> bool:
    from .hand_emr_uia import EmrHand
    emr = EmrHand(rezept, log)
    emr.verbinden()
    vars: dict[str, str] = {}

    for i, schritt in enumerate(rezept.schritte, 1):
        akt = schritt.get("aktion")
        ziel = schritt.get("ziel", [])
        log.line(f"Schritt {i}: {akt}")
        if akt in ("tab_wechseln", "klicken"):
            emr.klicken(ziel, was=akt)
        elif akt == "tippen":
            emr.tippen(ziel, schritt.get("text", ""))
        elif akt == "scrollen":
            emr.scrollen(ziel, schritt.get("wie", "ende"))
        elif akt == "warte":
            emr.warte(schritt.get("sekunden", 1))
        elif akt == "lese_liste":
            vars["daten"] = emr.lese_liste(ziel)
        elif akt == "an_dox":
            if not vars.get("daten"):
                log.line("  WARNUNG: keine Daten gesammelt vor an_dox.")
            vars["antwort"] = _an_dox(rezept, vars.get("daten", ""), log, headless_dox)
            if not vars["antwort"]:
                log.line("FEHLER: leere Antwort von Doximity GPT.")
                return False
        elif akt == "report_schreiben":
            ok, final = _freigeben(vars.get("antwort", ""), rezept, review, log)
            if not ok:
                return False
            emr.report_schreiben(ziel, final, schritt.get("modus", "anhaengen"))
        else:
            log.line(f"  Unbekannte Aktion '{akt}' — übersprungen.")
    log.line("FERTIG.")
    return True


def _lauf_ocr(rezept: Rezept, review, headless_dox, log: Log) -> bool:
    from .hand_emr_ocr import EmrHandOCR
    emr = EmrHandOCR(rezept, log)
    daten = emr.sammle_relevante_daten()
    antwort = _an_dox(rezept, daten, log, headless_dox)
    if not antwort:
        log.line("FEHLER: leere Antwort von Doximity GPT.")
        return False
    ok, final = _freigeben(antwort, rezept, review, log)
    if not ok:
        return False
    emr.schreibe_report(final)
    log.line("FERTIG.")
    return True


def lauf(rezept: Rezept, review: ReviewCallback | None = None,
         headless_dox: bool = True) -> bool:
    log = Log(rezept.name)
    try:
        methode = rezept.emr.get("greif_methode", "uia").lower()
        if methode == "ocr":
            return _lauf_ocr(rezept, review, headless_dox, log)
        return _lauf_uia(rezept, review, headless_dox, log)
    except Exception as e:                # noqa: BLE001
        log.line(f"FEHLER: {type(e).__name__}: {e}")
        return False
    finally:
        log.close()
