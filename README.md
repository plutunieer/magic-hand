# Magic Hand — EMR → Doximity GPT → EMR (vollautomatisch)

Eine „Hand", die für einen Arzt den langweiligen Büroteil übernimmt: relevante
Einträge im **Cerner PowerChart** (lokales Windows-Programm) suchen → an
**Doximity GPT** (Browser) übergeben → die Antwort zurück ins Report-Sheet im
PowerChart schreiben. Der Arzt hat nur zwei Fenster offen und drückt einen Knopf.

Abgeleitet vom DOM-Hand-Prinzip der `virtuelle-hand-playwright` (einmal lernen →
deterministisch wiederholen, ~0 Modell-Kosten, Mensch behält die Freigabe).

> **Status:** Vollständiges, lauffähiges Windows-Gerüst. Die Browser-Hand
> (Doximity GPT, Playwright) ist hoch erprobt — gleiches Muster wie
> `notebooklm_pw.py`. Die EMR-Hand (Windows-UIA) ist **best-effort** und muss
> **am echten PowerChart-Arbeitsplatz** mit `--inspect-emr` kalibriert werden
> (Selektoren ins Rezept eintragen). Entwicklung läuft auf macOS, Ziel ist
> Windows — der Windows-Build entsteht automatisch per GitHub Actions.

---

## Die drei Oberflächen

```
┌──────────── PowerChart (Win32, lokal) ───────────┐      ┌─ Doximity GPT (Browser) ─┐
│  Sheet "Daten"  → Befunde/Labor/Verlauf  ──QUELLE─┼─────▶│  Eingabe → Senden        │
│  (andere Ärzte / frühere Tage)                    │      │  Antwort lesen           │
│  Sheet "Report" → wo der Arzt schreibt  ◀──ZIEL───┼──────┤                          │
└───────────────────────────────────────────────────┘      └──────────────────────────┘
```

| Oberfläche | Technik | Modul | Vertrauen |
|---|---|---|---|
| Doximity GPT (Browser) | **Playwright/DOM** | `hand_dox.py` | hoch (erprobtes Muster) |
| PowerChart (Win32) | **Windows UIA** | `hand_emr_uia.py` | best-effort, kalibrieren |
| PowerChart (Notnagel) | **Screenshot + OCR** | `hand_emr_ocr.py` | grob, Fallback |

Ein **Orchestrator** (`orchestrator.py`) koordiniert beide Hände und reicht den
Text per Zwischenablage/Direkt-Text durch.

---

## Der vollständige Ablauf (eine Knopf-Aktion)

```
Auf Sheet "Daten":
 1. Tab "Daten" aktivieren
 2. Liste durchscrollen und ALLE Einträge einsammeln
 3. FESTE REGEL anwenden: datum ∈ {heute, gestern}  UND  typ ∈ {Befund, Labor, Verlauf}
 4. Text der passenden Einträge greifen
Doximity GPT:
 5. Prompt-Vorlage + gesammelte Daten einfügen → senden → Antwort lesen
Zurück ins PowerChart:
 6. Tab "Report" aktivieren
 7. Review-Fenster zeigt die Antwort → Arzt prüft/ergänzt → „Übernehmen"
 8. Text ins Report-Feld schreiben
```

Schritt 3 ist die **feste Regel** (kein Modell nötig). Schritt 7 ist die
**Pflicht-Freigabe** — es wird nie ungeprüft ins EMR geschrieben.

---

## Das „Rezept" (`rezept.example.yaml`)

Der Ablauf ist eine **Schritt-Folge beliebiger Länge** (`schritte:`) — kein
festes Schema. Jeder Schritt = `{aktion, ziel, …}`; Aktionen: `tab_wechseln,
klicken, tippen, scrollen, lese_liste, warte, an_dox, report_schreiben`.
Aufgenommen werden **Elemente** (Windows-Accessibility-Baum), keine Screenshots.
Datenfluss: `lese_liste → daten`, `an_dox → antwort`, `report_schreiben` schreibt
`antwort` (nach Freigabe). Dazu die feste Regel `emr.filter` + die Prompt-Vorlage.
Aufgebaut/repariert wird die Folge vom Recorder (⚙ Einrichten) **oder** vom
lokalen Claude-Code-Agenten. Beim ersten Start kopiert die App
`rezept.example.yaml` → `rezept.yaml`.

---

## Verteilung: GitHub clonen + Terminal-Claude (keine .exe)

Kein Installer, kein Build. Auf dem Arzt-PC: Repo **clonen**, im **Terminal
`claude` starten** — der Agent liest `CLAUDE.md` und macht den Rest (Doximity-
Login, Schritt-Folge bauen, reparieren). Updates per `git pull`, **nie neu
installieren**. Arzt-Anleitung: **[`SETUP-FOR-DOCTOR.md`](SETUP-FOR-DOCTOR.md)**.

---

## Entwicklung (auf macOS, Ziel Windows)

```bash
cd ~/Documents/Startup/magic-hand
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

Was wo getestet werden kann:

| Teil | macOS | Windows |
|---|---|---|
| Browser-Hand (Doximity GPT) | ✅ teils testbar | ✅ |
| Orchestrator / Rezept / UI | ✅ | ✅ |
| EMR-UIA-Hand | ❌ (Windows-only) | ✅ — hier kalibrieren |
| OCR-Fallback | ⚠️ Screenshot ok, Klicks Windows-spezifisch | ✅ |

### Befehle

```bash
python -m praxishand.main --login-dox      # EINMAL: bei Doximity GPT einloggen (Profil speichern)
python -m praxishand.main --inspect-dox    # Browser-Selektoren prüfen/mappen
python -m praxishand.main --inspect-emr    # (Windows) UIA-Baum von PowerChart dumpen → Selektoren finden
python -m praxishand.main                  # App starten (schwebende Knopf-Leiste)
python -m praxishand.main --run            # einen Durchlauf headless/CLI starten (Debug)
```

---

## Wartung vor Ort: lokaler Claude-Code-Agent

Der Arzt ist Laie und es ist kein Techniker vor Ort. Der **Betreuer** ist
deshalb ein **lokaler Claude-Code-Agent** auf demselben Windows-PC:

- **Daily Use:** der Arzt nutzt `Magic Hand.exe` (ein Knopf, Pflicht-Freigabe).
- **Einrichten (Normalfall):** grafischer Assistent (⚙ Einrichten) — Arzt zeigt
  mit der Maus, kein YAML.
- **Reparieren / harter Fall:** der Arzt startet **`Fix-mit-KI.bat`** und sagt in
  Worten, was klemmt („die Liste wird nicht gefunden"). Der Agent liest
  `CLAUDE.md`, lässt `--inspect-emr` laufen, korrigiert `rezept.yaml`, testet —
  vor Ort, ohne Wartezeit auf einen Menschen.

Voraussetzungen auf dem PC (einmalig per `install-windows.ps1`): Python + venv,
Playwright-Chromium, Node.js, **Claude Code** + Anthropic-Login. Daily-Use über
die `.exe` bleibt davon unberührt.

**Grenzen (ehrlich):** Ein Agent mit Shell-Zugriff + Internet auf einem
Klinik-PC ist eine **IT-/Compliance-Entscheidung** der Einrichtung. `CLAUDE.md`
verbietet dem Agenten PHI zu lesen/senden und in echte Akten zu schreiben;
Inspektion nur mit Test-/Leerpatient. Gibt PowerChart seinen Inhalt gar nicht
preis, eskaliert der Agent an die Klinik-IT (FHIR-Schnittstelle).

## Datenschutz / Compliance (WICHTIG)

- **Patientendaten (PHI).** Doximity GPT ist für US-Ärzte HIPAA-konform — die
  KI-Verarbeitung läuft dort. Die App **bewegt** PHI nur zwischen zwei Fenstern;
  sie sendet **nichts** an Dritte und ruft selbst kein externes Modell.
- **Keine PHI in Logs.** Logs enthalten nur Ablauf-Schritte und Fehler, nie den
  Inhalt der Einträge (`log.py`).
- **Pflicht-Freigabe** vor jedem Schreibvorgang ins EMR.
- **Institutionelle Freigabe.** Automatisierung eines klinischen EHR berührt
  IT-/Sicherheitsrichtlinien der Einrichtung. Vor Produktiveinsatz mit der
  Klinik-IT klären (der robuste Langfristweg wäre eine FHIR-Schnittstelle).

---

## Dateien

```
magic-hand/
├─ README.md                  # diese Datei (Entwickler)
├─ CLAUDE.md                  # Drehbuch für den Vor-Ort-Claude-Code-Agenten
├─ SETUP-FOR-DOCTOR.md        # kinderleichte Anleitung (Englisch, für den US-Arzt)
├─ install-windows.ps1        # optionaler Helfer: Python/Node/Claude-Code installieren
├─ requirements.txt
├─ rezept.example.yaml        # das Rezept (Schritt-Folge + feste Regel + Prompt)
└─ praxishand/
   ├─ main.py                 # Einstieg + CLI
   ├─ orchestrator.py         # der vollständige Ablauf
   ├─ hand_dox.py             # Doximity-GPT-Hand (Playwright)
   ├─ hand_emr_uia.py         # PowerChart-Hand (Windows UIA)
   ├─ hand_emr_ocr.py         # PowerChart-Fallback (Screenshot/OCR)
   ├─ inspect_uia.py          # UIA-Baum dumpen (Techniker-Kalibrierung)
   ├─ setup_wizard.py         # Einrichtungs-Assistent für den Arzt (Anklicken statt YAML)
   ├─ support.py              # "Hilfe"-Knopf: PHI-freies Diagnose-Paket an den Betreuer
   ├─ rezept.py               # Rezept laden/speichern + feste Regel
   ├─ ui.py                   # schwebende Leiste + Review + Einrichten/Hilfe (PySide6)
   └─ log.py                  # PHI-freies Logging
```
