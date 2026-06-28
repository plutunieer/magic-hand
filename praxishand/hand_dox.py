"""Doximity-GPT-Hand — DOM-gesteuert mit Playwright.

Gleiches erprobtes Muster wie virtuelle-hand-playwright/notebooklm_pw.py:
Kandidaten-Selektoren (der erste sichtbare gewinnt), persistentes eingeloggtes
Profil, kein LLM für den Ablauf. Aufgabe: Text einfügen -> senden -> Antwort
zurückgeben.

Plattformneutral — läuft auch auf macOS (gut für Entwicklung/Test).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Beim gepackten .exe ist Chromium mit eingebündelt (siehe Magic Hand.spec):
# Playwright muss dorthin zeigen, BEVOR es importiert/gestartet wird.
if getattr(sys, "frozen", False):
    _bundled = os.path.join(getattr(sys, "_MEIPASS", ""), "ms-playwright")
    if os.path.isdir(_bundled):
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", _bundled)

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

from .log import Log, _basis

PROFIL = _basis() / "profile"


def _locator(page, kand):
    typ, wert = kand[0], kand[1]
    extra = kand[2] if len(kand) > 2 else ""
    if typ == "role":
        return page.get_by_role(wert, name=extra, exact=False) if extra \
            else page.get_by_role(wert)
    if typ == "text":
        return page.get_by_text(wert, exact=False)
    if typ == "placeholder":
        return page.get_by_placeholder(wert, exact=False)
    if typ == "css":
        return page.locator(wert)
    raise ValueError(f"Unbekannter Selektortyp: {typ}")


def _erst_sichtbar(page, kandidaten, timeout=15000):
    pro = max(1500, timeout // max(1, len(kandidaten)))
    letzter = None
    for kand in kandidaten:
        try:
            loc = _locator(page, kand).first
            loc.wait_for(state="visible", timeout=pro)
            return loc
        except PWTimeout:
            letzter = kand
    raise RuntimeError(f"Kein sichtbares Element (zuletzt: {letzter})")


def login(headless: bool = False) -> None:
    """EINMAL aufrufen: Browser öffnet, Arzt loggt sich bei Doximity GPT ein.
    Das Profil wird in ./profile gespeichert und danach wiederverwendet."""
    PROFIL.mkdir(exist_ok=True)
    log = Log("dox-login")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFIL), headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.doximity.com/gpt", wait_until="domcontentloaded")
        log.line("Bitte bei Doximity GPT einloggen. Fenster nach dem Login schließen.")
        # Warten bis der Tab geschlossen wird (Arzt ist fertig)
        try:
            while ctx.pages:
                time.sleep(2)
        except Exception:                         # noqa: BLE001
            pass
        log.line("Profil gespeichert.")
        log.close()


def inspect(rezept_dox: dict, headless: bool = False) -> None:
    """Sichtbare Buttons/Textfelder dumpen, um Selektoren zu mappen."""
    log = Log("dox-inspect")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFIL), headless=headless,
            viewport={"width": 1280, "height": 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(rezept_dox.get("url", "https://www.doximity.com/gpt"),
                  wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        for rolle in ("button", "textbox", "link"):
            namen = []
            for e in page.get_by_role(rolle).all()[:40]:
                try:
                    if e.is_visible():
                        t = (e.inner_text(timeout=400)
                             or e.get_attribute("aria-label") or "").strip()
                        if t:
                            namen.append(t.replace("\n", " ")[:40])
                except Exception:                 # noqa: BLE001
                    pass
            log.line(f"  {rolle}: {namen}")
        ctx.close()
        log.close()


class DoxHand:
    """Lebt für die Dauer eines Laufs; öffnet den eingeloggten Browser."""

    def __init__(self, rezept_dox: dict, log: Log, headless: bool = True):
        self.r = rezept_dox
        self.log = log
        self.headless = headless
        self._p = None
        self._ctx = None
        self.page = None

    def __enter__(self):
        if not PROFIL.exists():
            raise RuntimeError("Kein Doximity-Profil. Erst `--login-dox` ausführen.")
        self._p = sync_playwright().start()
        self._ctx = self._p.chromium.launch_persistent_context(
            user_data_dir=str(PROFIL), headless=self.headless,
            accept_downloads=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900})
        self.page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        self.page.goto(self.r.get("url", "https://www.doximity.com/gpt"),
                       wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(2500)
        if "login" in self.page.url or "sign_in" in self.page.url:
            raise RuntimeError("Doximity nicht eingeloggt — `--login-dox` erneut ausführen.")
        return self

    def __exit__(self, *exc):
        try:
            if self._ctx:
                self._ctx.close()
        finally:
            if self._p:
                self._p.stop()

    def frage(self, prompt_text: str) -> str:
        """Prompt einfügen -> senden -> Antwort-Text zurückgeben."""
        page = self.page
        eingabe = _erst_sichtbar(page, self.r["eingabe"], timeout=20000)
        eingabe.click()
        eingabe.fill(prompt_text)               # echte Input-Events
        self.log.line("  Prompt eingefügt.")

        try:
            _erst_sichtbar(page, self.r["senden"], timeout=8000).click()
            self.log.line("  Senden geklickt.")
        except RuntimeError:
            eingabe.press("Enter")
            self.log.line("  (kein Senden-Knopf — Enter gedrückt)")

        timeout = int(self.r.get("timeout_antwort_sek", 180))
        antwort = self._warte_auf_antwort(timeout)
        self.log.count("Antwort-Zeichen", len(antwort))
        return antwort

    def _warte_auf_antwort(self, timeout_sek: int) -> str:
        """Wartet bis die Antwort stabil ist (wächst nicht mehr)."""
        page = self.page
        ende = time.time() + timeout_sek
        letzte = ""
        stabil_seit = 0.0
        while time.time() < ende:
            page.wait_for_timeout(1500)
            try:
                loc = _erst_sichtbar(page, self.r["antwort"], timeout=3000).last
                jetzt = loc.inner_text(timeout=2000) or ""
            except Exception:                     # noqa: BLE001
                jetzt = letzte
            if jetzt and jetzt == letzte:
                stabil_seit += 1.5
                if stabil_seit >= 4.5:            # 3 Runden stabil -> fertig
                    return jetzt.strip()
            else:
                stabil_seit = 0.0
                letzte = jetzt
        return letzte.strip()
