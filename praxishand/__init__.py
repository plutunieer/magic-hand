"""Magic Hand — automatisiert den Büro-Roundtrip EMR -> Doximity GPT -> EMR.

Module:
  rezept         Rezept (YAML) laden/speichern
  log            PHI-freies Logging + Fehler-Screenshots
  hand_dox       Doximity-GPT-Hand (Playwright/DOM)
  hand_emr_uia   PowerChart-Hand (Windows UI Automation)
  hand_emr_ocr   PowerChart-Fallback (Screenshot/OCR)
  orchestrator   verbindet beide Hände zum vollständigen Ablauf
  ui             schwebende Knopf-Leiste + Review-Fenster (PySide6)
  main           Einstieg + CLI
"""
__version__ = "1.0.0"
