"""Recorder — der Arzt (oder der Agent) nimmt eine SCHRITT-FOLGE auf.

Kein YAML, keine Kommandozeile. Oben: einmal bei Doximity GPT anmelden. Dann
beliebig viele Schritte aufnehmen: Aktion wählen → (falls nötig) mit der Maus auf
das Ziel zeigen (5-Sekunden-Countdown, Element-Aufnahme) → ggf. Text/Optionen.
Speichern schreibt die Schritte ins Rezept.

Für komplexe/variable Abläufe baut der lokale Claude-Code-Agent die Folge
zuverlässiger zusammen (siehe CLAUDE.md) — dieser Recorder ist die einfache
Selbstbedienungs-Variante. Aufnahme funktioniert nur unter Windows.
"""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from . import hand_emr_uia
from .rezept import Rezept

# Aktion -> braucht Ziel?, braucht Text?, Beschreibung
AKTIONEN = {
    "tab_wechseln":     (True,  False, "Auf einen Reiter/Tab klicken"),
    "klicken":          (True,  False, "Auf ein Element klicken (Knopf, Eintrag …)"),
    "tippen":           (True,  True,  "Text in ein Feld schreiben"),
    "scrollen":         (True,  False, "Eine Liste scrollen"),
    "lese_liste":       (True,  False, "Einträge sammeln + feste Regel anwenden"),
    "warte":            (False, False, "Kurze Pause"),
    "an_dox":           (False, False, "Daten an Doximity GPT geben"),
    "report_schreiben": (True,  False, "Antwort ins Zielfeld schreiben"),
}


class _LoginThread(QtCore.QThread):
    fertig = QtCore.Signal()

    def run(self):
        try:
            from .hand_dox import login
            login(headless=False)
        except Exception:                 # noqa: BLE001
            pass
        self.fertig.emit()


class AufnahmeDialog(QtWidgets.QDialog):
    """Einen Schritt zusammenstellen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schritt aufnehmen")
        self.resize(440, 320)
        self.ziel: dict | None = None
        lay = QtWidgets.QVBoxLayout(self)

        lay.addWidget(QtWidgets.QLabel("Aktion wählen:"))
        self.combo = QtWidgets.QComboBox()
        for a, (_, _, beschr) in AKTIONEN.items():
            self.combo.addItem(f"{a} — {beschr}", a)
        self.combo.currentIndexChanged.connect(self._aktualisieren)
        lay.addWidget(self.combo)

        # Ziel-Aufnahme
        self.ziel_box = QtWidgets.QGroupBox("Ziel (mit der Maus zeigen)")
        zl = QtWidgets.QVBoxLayout(self.ziel_box)
        self.btn_auf = QtWidgets.QPushButton("Ziel aufnehmen (5 Sekunden)")
        self.btn_auf.clicked.connect(self._aufnehmen)
        zl.addWidget(self.btn_auf)
        self.ziel_status = QtWidgets.QLabel("— noch nichts aufgenommen —")
        zl.addWidget(self.ziel_status)
        lay.addWidget(self.ziel_box)

        # Text (für tippen)
        self.text_box = QtWidgets.QGroupBox("Text (was getippt wird)")
        tl = QtWidgets.QVBoxLayout(self.text_box)
        self.text_edit = QtWidgets.QLineEdit()
        tl.addWidget(self.text_edit)
        lay.addWidget(self.text_box)

        knoepfe = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)
        lay.addWidget(knoepfe)

        self._rest = 0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._aktualisieren()

    def _aktualisieren(self):
        akt = self.combo.currentData()
        braucht_ziel, braucht_text, _ = AKTIONEN[akt]
        self.ziel_box.setVisible(braucht_ziel)
        self.text_box.setVisible(braucht_text)

    def _aufnehmen(self):
        if not hand_emr_uia.verfuegbar():
            self.ziel_status.setText("Aufnahme nur unter Windows möglich.")
            return
        self._rest = 5
        self.ziel_status.setText("Maus über die Stelle bewegen … 5")
        self._timer.start(1000)

    def _tick(self):
        self._rest -= 1
        if self._rest > 0:
            self.ziel_status.setText(f"Maus über die Stelle bewegen … {self._rest}")
            return
        self._timer.stop()
        cap = hand_emr_uia.capture_unter_cursor()
        if cap:
            self.ziel = cap
            self.ziel_status.setText(f"✓ {cap['_label']}")
        else:
            self.ziel_status.setText("✗ nichts erkannt — bitte erneut aufnehmen")

    def schritt(self) -> dict | None:
        akt = self.combo.currentData()
        braucht_ziel, braucht_text, _ = AKTIONEN[akt]
        s: dict = {"aktion": akt}
        if braucht_ziel:
            if not self.ziel:
                return None
            sel = {k: v for k, v in self.ziel.items()
                   if not k.startswith("_") and v}
            s["ziel"] = [sel]
        if braucht_text:
            s["text"] = self.text_edit.text()
        if akt == "warte":
            s["sekunden"] = 1
        return s


class Recorder(QtWidgets.QDialog):
    def __init__(self, rezept: Rezept, parent=None):
        super().__init__(parent)
        self.rezept = rezept
        self.setWindowTitle("PraxisHand — Ablauf aufnehmen")
        self.resize(560, 480)
        lay = QtWidgets.QVBoxLayout(self)

        lay.addWidget(QtWidgets.QLabel(
            "1) Bei Doximity GPT anmelden.  2) Den Ablauf Schritt für Schritt "
            "aufnehmen (beliebig viele).  3) Speichern."))

        self.btn_login = QtWidgets.QPushButton("1) Bei Doximity GPT anmelden")
        self.btn_login.clicked.connect(self._login)
        lay.addWidget(self.btn_login)

        self.liste = QtWidgets.QListWidget()
        # vorhandene Schritte laden
        for s in rezept.schritte:
            self.liste.addItem(self._beschriften(s))
        self._schritte: list[dict] = list(rezept.schritte)
        lay.addWidget(self.liste, 1)

        zeile = QtWidgets.QHBoxLayout()
        b_add = QtWidgets.QPushButton("Schritt hinzufügen")
        b_add.clicked.connect(self._hinzufuegen)
        b_del = QtWidgets.QPushButton("Markierten löschen")
        b_del.clicked.connect(self._loeschen)
        b_up = QtWidgets.QPushButton("▲")
        b_up.clicked.connect(lambda: self._verschieben(-1))
        b_down = QtWidgets.QPushButton("▼")
        b_down.clicked.connect(lambda: self._verschieben(1))
        for b in (b_add, b_del, b_up, b_down):
            zeile.addWidget(b)
        lay.addLayout(zeile)

        knoepfe = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        knoepfe.accepted.connect(self._speichern)
        knoepfe.rejected.connect(self.reject)
        lay.addWidget(knoepfe)

    def _beschriften(self, s: dict) -> str:
        akt = s.get("aktion", "?")
        ziel = ""
        if s.get("ziel"):
            z = s["ziel"][0]
            ziel = f" → {z.get('control_type','')} '{(z.get('name') or '')[:30]}'"
        if s.get("text"):
            ziel += f"  text='{s['text'][:20]}'"
        return f"{akt}{ziel}"

    def _login(self):
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Browser geöffnet — bitte anmelden …")
        self._t = _LoginThread()
        self._t.fertig.connect(lambda: self.btn_login.setText("✓ angemeldet"))
        self._t.start()

    def _hinzufuegen(self):
        dlg = AufnahmeDialog(self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            s = dlg.schritt()
            if s is None:
                QtWidgets.QMessageBox.warning(self, "Fehlt", "Kein Ziel aufgenommen.")
                return
            self._schritte.append(s)
            self.liste.addItem(self._beschriften(s))

    def _loeschen(self):
        i = self.liste.currentRow()
        if i >= 0:
            self.liste.takeItem(i)
            del self._schritte[i]

    def _verschieben(self, richtung: int):
        i = self.liste.currentRow()
        j = i + richtung
        if i < 0 or j < 0 or j >= len(self._schritte):
            return
        self._schritte[i], self._schritte[j] = self._schritte[j], self._schritte[i]
        self.liste.insertItem(j, self.liste.takeItem(i))
        self.liste.setCurrentRow(j)

    def _speichern(self):
        self.rezept.setze_schritte(self._schritte)
        self.rezept.daten["kalibriert"] = True
        self.rezept.speichern()
        self.accept()


def assistent_starten(rezept: Rezept, parent=None) -> bool:
    return Recorder(rezept, parent).exec() == QtWidgets.QDialog.Accepted
