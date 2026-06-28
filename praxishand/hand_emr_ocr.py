"""PowerChart-Fallback — Screenshot + OCR (Stufe 3).

NUR Notnagel: wenn UIA die Liste nicht als Elemente preisgibt (selbst-gezeichnet).
Liest definierte Bildschirm-Regionen per OCR, wendet die feste Regel zeilenweise
an und schreibt die Antwort per Zwischenablage ins Report-Feld.

Grob und layout-abhängig — die Regionen [x,y,w,h] und ein paar Klick-Punkte
müssen im Rezept (emr.ocr) hinterlegt werden. Nur Windows.
"""
from __future__ import annotations

import sys

from .log import Log
from .rezept import Rezept, eintrag_passt

try:
    import mss                            # type: ignore
    import pytesseract                    # type: ignore
    import pyautogui                      # type: ignore
    import pyperclip                      # type: ignore
    from PIL import Image                 # type: ignore
    _HAT_OCR = True
except Exception:                         # noqa: BLE001
    _HAT_OCR = False


def verfuegbar() -> bool:
    return _HAT_OCR and sys.platform == "win32"


def _grab(region: list[int]):
    x, y, w, h = region
    with mss.mss() as sct:
        raw = sct.grab({"left": x, "top": y, "width": w, "height": h})
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


def _zeile_zu_eintrag(zeile: str) -> dict:
    """Sehr grobe Heuristik: Datum/Typ aus einer OCR-Zeile raten.
    Die feste Regel filtert anschließend per eintrag_passt()."""
    return {"datum": zeile, "typ": zeile, "text": zeile}


class EmrHandOCR:
    def __init__(self, rezept: Rezept, log: Log):
        if not verfuegbar():
            raise RuntimeError("OCR-Fallback nur unter Windows (mss/pytesseract/pyautogui).")
        self.r = rezept
        self.emr = rezept.emr
        self.ocr = self.emr.get("ocr", {})
        self.log = log

    def sammle_relevante_daten(self) -> str:
        region = self.ocr.get("region_liste")
        if not region or region == [0, 0, 0, 0]:
            raise RuntimeError("emr.ocr.region_liste im Rezept nicht gesetzt.")
        bild = _grab(region)
        text = pytesseract.image_to_string(bild)
        filter_regel = self.emr.get("filter", {})
        treffer = [z.strip() for z in text.splitlines()
                   if z.strip() and eintrag_passt(_zeile_zu_eintrag(z), filter_regel)]
        self.log.count("OCR-Zeilen passend", len(treffer))
        if not treffer:
            raise RuntimeError("OCR: keine passenden Zeilen (Region/Regel prüfen).")
        return "\n".join(treffer)

    def schreibe_report(self, text: str) -> None:
        region = self.ocr.get("region_report")
        if not region or region == [0, 0, 0, 0]:
            raise RuntimeError("emr.ocr.region_report im Rezept nicht gesetzt.")
        x, y, w, h = region
        pyautogui.click(x + w // 2, y + h // 2)    # ins Report-Feld klicken
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        self.log.line("  Report per OCR-Fallback eingefügt (zur Freigabe).")
