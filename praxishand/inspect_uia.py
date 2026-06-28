"""UIA-Baum von PowerChart dumpen — der Kalibrier-Schritt vor dem Bauen.

Gegenstück zu `notebooklm_pw.py --inspect`. Zeigt, welche Elemente PowerChart an
die Windows-Accessibility-Schnittstelle gibt — damit man control_type /
automation_id / Spaltennamen ins Rezept eintragen kann.

Auswertung:
  - Erscheinen Liste/Einträge/Felder als echte Elemente?  -> UIA baubar
  - Nur ein großer Block ohne Kinder?                       -> OCR-Fallback nötig

Nur Windows:  python -m praxishand.main --inspect-emr
"""
from __future__ import annotations

import sys

from .log import Log


def dump(titel_enthaelt: str = "PowerChart", max_tiefe: int = 6) -> None:
    if sys.platform != "win32":
        print("inspect-emr läuft nur unter Windows.")
        return
    try:
        import uiautomation as auto       # type: ignore
    except Exception as e:                # noqa: BLE001
        print(f"uiautomation fehlt: {e}")
        return

    log = Log("emr-inspect")
    win = auto.WindowControl(searchDepth=2, SubName=titel_enthaelt)
    if not win.Exists(maxSearchSeconds=5):
        log.line(f"PowerChart-Fenster ('{titel_enthaelt}') nicht gefunden.")
        log.close()
        return

    log.line(f"Fenster: {win.Name!r}")
    log.line("Baum (Typ | Name | AutomationId):")

    def rein(ctrl, tiefe=0):
        if tiefe > max_tiefe:
            return
        try:
            kinder = ctrl.GetChildren()
        except Exception:                 # noqa: BLE001
            kinder = []
        for k in kinder:
            try:
                typ = k.ControlTypeName
                name = (k.Name or "")[:50].replace("\n", " ")
                aid = getattr(k, "AutomationId", "") or ""
                log.line("  " * tiefe + f"- {typ} | {name!r} | id={aid!r}")
            except Exception:             # noqa: BLE001
                continue
            rein(k, tiefe + 1)

    rein(win)
    log.line("--- Ende Baum ---")
    log.line("Wenn Liste/Einträge oben als List/ListItem/Table mit lesbaren "
             "Namen auftauchen: UIA baubar. Wenn nur ein Pane/Custom-Block ohne "
             "Kinder: OCR-Fallback (emr.greif_methode: ocr).")
    log.close()
