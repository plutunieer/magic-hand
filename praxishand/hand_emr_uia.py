"""PowerChart-Hand — Windows UI Automation (UIA).

Stellt die Aktions-Primitive bereit, die der Orchestrator als Schritt-Folge
abspielt: klicken, tippen, scrollen, tab_wechseln, lese_liste, report_schreiben.
Element-basiert (kein Bild) → deterministisch, kein Modell.

WICHTIG — best-effort: Cerner PowerChart ist eine alte Win32/ActiveX-App. Wie
sauber Elemente im UIA-Baum erscheinen, MUSS am echten Arbeitsplatz geprüft und
in den Ziel-Selektoren des Rezepts hinterlegt werden (Recorder oder Agent, siehe
CLAUDE.md). Die mit  # >>> KALIBRIEREN  markierten Stellen sind die wahrscheinlich
anzupassenden.

Nur Windows. Auf macOS importierbar (zum Entwickeln), Aufrufe werfen sauber.
"""
from __future__ import annotations

import sys
import time

from .log import Log
from .rezept import Rezept, eintrag_passt

try:
    import uiautomation as auto          # type: ignore
    _HAT_UIA = True
except Exception:                        # noqa: BLE001
    auto = None
    _HAT_UIA = False


def verfuegbar() -> bool:
    return _HAT_UIA and sys.platform == "win32"


def capture_unter_cursor() -> dict | None:
    """Element unter dem Mauszeiger erfassen → Selektor-Dict für einen Schritt."""
    if not verfuegbar():
        return None
    try:
        ctrl = auto.ControlFromCursor()
    except Exception:                    # noqa: BLE001
        return None
    if not ctrl:
        return None
    sinnvoll = {"List", "Table", "DataGrid", "Tree",
                "Edit", "Document", "TabItem", "Button", "ListItem", "Pane"}
    cur = ctrl
    for _ in range(6):
        if cur.ControlTypeName.replace("Control", "") in sinnvoll:
            break
        p = cur.GetParentControl()
        if not p:
            break
        cur = p
    typ = cur.ControlTypeName.replace("Control", "")
    name = cur.Name or None
    aid = getattr(cur, "AutomationId", "") or None
    return {"control_type": typ, "name": name, "automation_id": aid,
            "_label": f"{typ} '{(name or '')[:40]}'"}


class EmrHand:
    def __init__(self, rezept: Rezept, log: Log):
        if not verfuegbar():
            raise RuntimeError("UIA nur unter Windows verfügbar (uiautomation fehlt).")
        self.r = rezept
        self.emr = rezept.emr
        self.log = log
        self.win = None

    def verbinden(self) -> None:
        titel = self.emr.get("fenster_titel_enthaelt", "PowerChart")
        self.win = auto.WindowControl(searchDepth=2, SubName=titel)
        if not self.win.Exists(maxSearchSeconds=5):
            raise RuntimeError(f"PowerChart-Fenster ('{titel}') nicht gefunden.")
        self.win.SetActive()
        self.log.line("PowerChart-Fenster verbunden.")

    # ----- Element-Finder (mehrere Kandidaten, erster Treffer gewinnt) -----
    def _finde(self, ziel: list[dict], was: str = "Element"):
        for sel in ziel or []:
            ct = sel.get("control_type", "Pane")
            kwargs = {}
            if sel.get("name"):
                kwargs["Name"] = sel["name"]
            if sel.get("automation_id"):
                kwargs["AutomationId"] = sel["automation_id"]
            try:
                getter = getattr(self.win, f"{ct}Control")
                ctrl = getter(**kwargs)
                if ctrl.Exists(maxSearchSeconds=2):
                    return ctrl
            except Exception:            # noqa: BLE001
                continue
        raise RuntimeError(f"{was} nicht gefunden — Ziel-Selektor kalibrieren.")

    # ----- Aktionen --------------------------------------------------------
    def klicken(self, ziel: list[dict], was: str = "Element") -> None:
        ctrl = self._finde(ziel, was)
        ctrl.Click(simulateMove=False)   # >>> KALIBRIEREN (ggf. GetInvokePattern().Invoke())
        time.sleep(0.8)
        self.log.line(f"  geklickt: {was}")

    def tab_wechseln(self, ziel: list[dict]) -> None:
        self.klicken(ziel, was="Tab")

    def tippen(self, ziel: list[dict], text: str) -> None:
        ctrl = self._finde(ziel, "Eingabefeld")
        ctrl.SetFocus()
        try:
            ctrl.GetValuePattern().SetValue(text)
        except Exception:                # noqa: BLE001
            import pyperclip
            pyperclip.copy(text)
            ctrl.SendKeys("{Ctrl}a{Delete}")
            ctrl.SendKeys("{Ctrl}v")
        self.log.count("getippt Zeichen", len(text))

    def scrollen(self, ziel: list[dict], wie="ende") -> None:
        ctrl = self._finde(ziel, "Liste")
        runden = 30 if wie == "ende" else int(wie)
        for _ in range(runden):
            try:
                sp = ctrl.GetScrollPattern()
                if sp and sp.VerticallyScrollable:
                    sp.Scroll(auto.ScrollAmount.NoAmount, auto.ScrollAmount.LargeIncrement)
                else:
                    ctrl.SetFocus(); ctrl.SendKeys("{PageDown}")
            except Exception:            # noqa: BLE001
                ctrl.SetFocus(); ctrl.SendKeys("{PageDown}")
            time.sleep(0.3)

    def warte(self, sekunden: float) -> None:
        time.sleep(float(sekunden))

    # ----- lese_liste: Einträge sammeln + feste Regel ---------------------
    def lese_liste(self, ziel: list[dict]) -> str:
        liste = self._finde(ziel, "Einträge-Liste")
        feld = self.emr.get("eintrag", {})
        filter_regel = self.emr.get("filter", {})
        max_n = int(filter_regel.get("max_eintraege", 40))

        gesehen: set[str] = set()
        treffer: list[str] = []
        gesamt = 0
        leerlauf = 0
        while leerlauf < 2 and len(treffer) < max_n:
            neue = 0
            for item in liste.GetChildren():        # >>> KALIBRIEREN (ggf. ListItem-Filter)
                roh = self._eintrag_lesen(item, feld)
                key = f"{roh.get('datum')}|{roh.get('typ')}|{roh.get('text','')[:30]}"
                if key in gesehen:
                    continue
                gesehen.add(key); gesamt += 1; neue += 1
                if eintrag_passt(roh, filter_regel):
                    treffer.append(self._formatieren(roh))
            leerlauf = leerlauf + 1 if neue == 0 else 0
            self.scrollen(ziel, "1")
        self.log.count("Einträge gesehen", gesamt)
        self.log.count("Einträge nach Regel", len(treffer))
        if not treffer:
            raise RuntimeError("Keine passenden Einträge (Regel/Selektoren prüfen).")
        return "\n\n".join(treffer[:max_n])

    def _eintrag_lesen(self, item, feld: dict) -> dict:
        out = {"datum": "", "typ": "", "text": ""}
        try:
            for k, spalte in (("datum", feld.get("feld_datum")),
                              ("typ", feld.get("feld_typ")),
                              ("text", feld.get("feld_text"))):
                if not spalte:
                    continue
                zelle = item.TextControl(Name=spalte)
                if zelle.Exists(maxSearchSeconds=0):
                    out[k] = zelle.Name or ""
        except Exception:                # noqa: BLE001
            pass
        if not any(out.values()):        # Fallback: ganze Zeile als ein String
            zeile = getattr(item, "Name", "") or ""
            out = {"datum": zeile, "typ": zeile, "text": zeile}
        return out

    def _formatieren(self, roh: dict) -> str:
        d, t = roh.get("datum", "").strip(), roh.get("typ", "").strip()
        txt = roh.get("text", "").strip()
        kopf = " | ".join(x for x in (d, t) if x)
        return f"[{kopf}]\n{txt}" if kopf else txt

    # ----- report_schreiben -----------------------------------------------
    def report_schreiben(self, ziel: list[dict], text: str, modus="anhaengen") -> None:
        feld = self._finde(ziel, "Report-Textfeld")
        feld.SetFocus()
        try:
            vp = feld.GetValuePattern()
            if modus == "ersetzen":
                vp.SetValue(text)
            else:
                vp.SetValue(((vp.Value or "") + "\n\n" + text).strip())
        except Exception:                # noqa: BLE001
            import pyperclip
            pyperclip.copy(text)
            if modus == "ersetzen":
                feld.SendKeys("{Ctrl}a{Delete}")
            else:
                feld.SendKeys("{End}{Enter}{Enter}")
            feld.SendKeys("{Ctrl}v")
        self.log.line("  Report geschrieben.")
