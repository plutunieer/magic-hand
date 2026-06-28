"""Rezept laden/speichern + Filterregel zur Laufzeit auflösen.

Ein Rezept ist eine YAML-Datei (siehe rezept.example.yaml). Beim ersten Start
wird das Beispiel nach rezept.yaml kopiert. Mehrere Rezepte (mehrere Aufgaben/
Knöpfe) werden im Ordner rezepte/ abgelegt.
"""
from __future__ import annotations

import datetime
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dateutil import parser as dateparser

from .log import _basis


def _projekt() -> Path:
    return _basis()


def standard_rezept_pfad() -> Path:
    return _projekt() / "rezept.yaml"


def beispiel_pfad() -> Path:
    return _projekt() / "rezept.example.yaml"


def sicherstellen_vorhanden() -> Path:
    """Kopiert beim ersten Start rezept.example.yaml -> rezept.yaml."""
    ziel = standard_rezept_pfad()
    if not ziel.exists() and beispiel_pfad().exists():
        shutil.copy(beispiel_pfad(), ziel)
    return ziel


def alle_rezepte() -> list["Rezept"]:
    """rezept.yaml + alles unter rezepte/*.yaml."""
    pfade: list[Path] = []
    haupt = sicherstellen_vorhanden()
    if haupt.exists():
        pfade.append(haupt)
    ordner = _projekt() / "rezepte"
    if ordner.exists():
        pfade.extend(sorted(ordner.glob("*.yaml")))
    return [Rezept.laden(p) for p in pfade]


@dataclass
class Rezept:
    pfad: Path
    daten: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def laden(cls, pfad: Path) -> "Rezept":
        with open(pfad, "r", encoding="utf-8") as f:
            return cls(pfad=pfad, daten=yaml.safe_load(f) or {})

    def speichern(self) -> None:
        with open(self.pfad, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.daten, f, allow_unicode=True, sort_keys=False)

    # --- bequeme Zugriffe ---
    @property
    def name(self) -> str:
        return self.daten.get("name", self.pfad.stem)

    @property
    def hotkey(self) -> str | None:
        return self.daten.get("hotkey")

    @property
    def emr(self) -> dict[str, Any]:
        return self.daten.get("emr", {})

    @property
    def schritte(self) -> list[dict[str, Any]]:
        return self.daten.get("schritte", [])

    def setze_schritte(self, schritte: list[dict[str, Any]]) -> None:
        self.daten["schritte"] = schritte

    @property
    def dox(self) -> dict[str, Any]:
        return self.daten.get("dox", {})

    @property
    def freigabe_pflicht(self) -> bool:
        return str(self.daten.get("freigabe", "pflicht")).lower() == "pflicht"

    @property
    def kalibriert(self) -> bool:
        return bool(self.daten.get("kalibriert", False))

    @property
    def support_email(self) -> str:
        return self.daten.get("support_email", "")

    def setze_anker(self, pfad: list[str], selektor: dict) -> None:
        """Vom Assistenten erfassten Selektor ins Rezept schreiben.
        pfad z.B. ["emr","sheet_daten","liste"]; gespeichert als 1-Element-Liste."""
        knoten = self.daten
        for teil in pfad[:-1]:
            knoten = knoten.setdefault(teil, {})
        sel = {k: v for k, v in selektor.items() if not k.startswith("_") and v}
        knoten[pfad[-1]] = [sel]

    def prompt(self, daten_text: str) -> str:
        vorlage = self.dox.get("prompt_vorlage", "{daten}")
        return vorlage.replace("{daten}", daten_text)


# ---------- feste Filterregel ----------
def _aufgeloeste_daten(regel: list[str]) -> set[datetime.date]:
    """Wandelt ["heute","gestern"] in konkrete Datumswerte um."""
    heute = datetime.date.today()
    out: set[datetime.date] = set()
    for r in regel:
        rl = str(r).lower()
        if rl in ("heute", "today"):
            out.add(heute)
        elif rl in ("gestern", "yesterday"):
            out.add(heute - datetime.timedelta(days=1))
        else:
            try:
                out.add(dateparser.parse(r).date())
            except Exception:                    # noqa: BLE001
                pass
    return out


def eintrag_passt(eintrag: dict[str, str], filter_regel: dict[str, Any]) -> bool:
    """Feste Regel — deterministisch, kein Modell.

    eintrag: {"datum": "<roh>", "typ": "<roh>", "text": "..."}
    """
    erlaubte_daten = _aufgeloeste_daten(filter_regel.get("datum", []))
    erlaubte_typen = [t.lower() for t in filter_regel.get("typ", [])]

    # Datum prüfen
    if erlaubte_daten:
        roh = (eintrag.get("datum") or "").strip()
        try:
            d = dateparser.parse(roh, fuzzy=True).date()
        except Exception:                        # noqa: BLE001
            return False
        if d not in erlaubte_daten:
            return False

    # Typ prüfen (Substring-Treffer gegen erlaubte Typen)
    if erlaubte_typen:
        typ = (eintrag.get("typ") or "").lower()
        if not any(t in typ for t in erlaubte_typen):
            return False

    return True
