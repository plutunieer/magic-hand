"""Magic Hand — Einstieg + CLI.

  python -m praxishand.main                # App starten (schwebende Knopf-Leiste)
  python -m praxishand.main --login-dox    # EINMAL: bei Doximity GPT einloggen
  python -m praxishand.main --inspect-dox  # Browser-Selektoren prüfen
  python -m praxishand.main --inspect-emr  # (Windows) PowerChart-UIA-Baum dumpen
  python -m praxishand.main --run          # einen Durchlauf im Terminal (Debug)
"""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="Magic Hand: EMR -> Doximity GPT -> EMR")
    ap.add_argument("--login-dox", action="store_true",
                    help="Einmaliger Login bei Doximity GPT (Profil speichern)")
    ap.add_argument("--inspect-dox", action="store_true",
                    help="Sichtbare Doximity-Elemente dumpen")
    ap.add_argument("--inspect-emr", action="store_true",
                    help="(Windows) UIA-Baum von PowerChart dumpen")
    ap.add_argument("--run", action="store_true",
                    help="Einen Durchlauf im Terminal ausführen (Debug)")
    ap.add_argument("--rezept", help="Pfad zu einem bestimmten Rezept (.yaml)")
    a = ap.parse_args()

    from . import rezept as rez_mod

    if a.login_dox:
        from .hand_dox import login
        login(headless=False)
        return 0

    if a.inspect_dox:
        from .hand_dox import inspect
        r = rez_mod.Rezept.laden(a.rezept) if a.rezept \
            else rez_mod.alle_rezepte()[0]
        inspect(r.dox, headless=False)
        return 0

    if a.inspect_emr:
        from .inspect_uia import dump
        r = rez_mod.Rezept.laden(a.rezept) if a.rezept \
            else rez_mod.alle_rezepte()[0]
        dump(r.emr.get("fenster_titel_enthaelt", "PowerChart"))
        return 0

    if a.run:
        from . import orchestrator
        r = rez_mod.Rezept.laden(a.rezept) if a.rezept \
            else rez_mod.alle_rezepte()[0]
        ok = orchestrator.lauf(r, review=orchestrator.terminal_review,
                               headless_dox=False)
        return 0 if ok else 1

    # Standard: grafische Knopf-Leiste
    from .ui import starten
    return starten()


if __name__ == "__main__":
    sys.exit(main())
