"""Oberfläche — schwebende Knopf-Leiste + Pflicht-Review-Fenster (PySide6).

- Pro Rezept ein Knopf. Klick -> Orchestrator läuft in einem Worker-Thread
  (UI friert nicht ein).
- Vor dem Schreiben ins EMR öffnet sich das Review-Fenster: der Arzt sieht den
  Vorschlag, kann ihn editieren und gibt frei oder bricht ab.

Plattformneutral (die EMR-Teile werfen sauber, wenn nicht Windows).
"""
from __future__ import annotations

import threading

from PySide6 import QtCore, QtGui, QtWidgets

from . import orchestrator, support
from .rezept import Rezept, alle_rezepte
from .setup_wizard import assistent_starten


class ReviewDialog(QtWidgets.QDialog):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Freigabe — bitte prüfen und ggf. ergänzen")
        self.resize(720, 560)
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel(
            "Vorschlag von Doximity GPT. Erst nach „Übernehmen“ wird ins "
            "Report-Sheet geschrieben."))
        self.edit = QtWidgets.QPlainTextEdit()
        self.edit.setPlainText(text)
        lay.addWidget(self.edit)
        knoepfe = QtWidgets.QDialogButtonBox()
        self.ok = knoepfe.addButton("Übernehmen", QtWidgets.QDialogButtonBox.AcceptRole)
        knoepfe.addButton("Abbrechen", QtWidgets.QDialogButtonBox.RejectRole)
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)
        lay.addWidget(knoepfe)

    def ergebnis(self) -> tuple[bool, str]:
        return (self.result() == QtWidgets.QDialog.Accepted, self.edit.toPlainText())


class Worker(QtCore.QThread):
    fertig = QtCore.Signal(bool)
    review_anfrage = QtCore.Signal(str, object)   # (text, box-dict)

    def __init__(self, rezept: Rezept):
        super().__init__()
        self.rezept = rezept

    def run(self):
        ok = orchestrator.lauf(self.rezept, review=self._review, headless_dox=True)
        self.fertig.emit(ok)

    def _review(self, text: str) -> tuple[bool, str]:
        """Läuft im Worker-Thread; delegiert ans GUI-Thread und blockiert."""
        box: dict = {}
        evt = threading.Event()
        box["event"] = evt
        self.review_anfrage.emit(text, box)
        evt.wait()
        return box.get("ok", False), box.get("text", text)


class Leiste(QtWidgets.QWidget):
    def __init__(self, rezepte: list[Rezept]):
        super().__init__()
        self.rezepte = rezepte
        self.worker: Worker | None = None
        self.setWindowTitle("Magic Hand")
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)

        for r in rezepte:
            b = QtWidgets.QPushButton(r.name)
            b.setMinimumHeight(34)
            b.clicked.connect(lambda _=False, rez=r: self.starten(rez))
            lay.addWidget(b)

        einrichten = QtWidgets.QPushButton("⚙ Einrichten")
        einrichten.clicked.connect(self.einrichten)
        lay.addWidget(einrichten)

        hilfe = QtWidgets.QPushButton("Hilfe")
        hilfe.clicked.connect(self.hilfe)
        lay.addWidget(hilfe)

        self.status = QtWidgets.QLabel("bereit")
        self.status.setStyleSheet("color:#555; padding:0 8px;")
        lay.addWidget(self.status)

        # Beim ersten Start automatisch den Assistenten öffnen
        QtCore.QTimer.singleShot(300, self._erststart_pruefen)

    def _erststart_pruefen(self):
        if self.rezepte and not self.rezepte[0].kalibriert:
            QtWidgets.QMessageBox.information(
                self, "Magic Hand",
                "Willkommen! Wir richten die App einmal gemeinsam ein.")
            self.einrichten()

    def einrichten(self):
        if not self.rezepte:
            return
        if assistent_starten(self.rezepte[0], self):
            self.status.setText("✓ eingerichtet")

    def hilfe(self):
        r = self.rezepte[0] if self.rezepte else None
        titel = r.emr.get("fenster_titel_enthaelt", "PowerChart") if r else "PowerChart"
        email = r.support_email if r else ""
        paket = support.hilfe_anfordern(email, titel)
        QtWidgets.QMessageBox.information(
            self, "Hilfe",
            f"Ein Diagnose-Paket wurde erstellt:\n{paket}\n\n"
            "Der Ordner wurde geöffnet und ein E-Mail-Entwurf vorbereitet.\n"
            "Bitte die Datei an die E-Mail anhängen und absenden.")

    # --- Ablauf ---
    def starten(self, rezept: Rezept):
        if self.worker and self.worker.isRunning():
            return
        self.status.setText(f"„{rezept.name}“ läuft …")
        self.setEnabled_buttons(False)
        self.worker = Worker(rezept)
        self.worker.review_anfrage.connect(self._zeige_review)
        self.worker.fertig.connect(self._fertig)
        self.worker.start()

    @QtCore.Slot(str, object)
    def _zeige_review(self, text: str, box: dict):
        dlg = ReviewDialog(text, self)
        dlg.exec()
        ok, finaler = dlg.ergebnis()
        box["ok"] = ok
        box["text"] = finaler
        box["event"].set()

    @QtCore.Slot(bool)
    def _fertig(self, ok: bool):
        self.status.setText("✓ fertig" if ok else "✗ abgebrochen/Fehler")
        self.setEnabled_buttons(True)
        if not ok:
            box = QtWidgets.QMessageBox(self)
            box.setWindowTitle("Hat nicht geklappt")
            box.setText("Etwas hat nicht funktioniert. Was möchtest du tun?")
            neu = box.addButton("Einrichtung wiederholen", QtWidgets.QMessageBox.AcceptRole)
            box.addButton("Hilfe anfordern", QtWidgets.QMessageBox.HelpRole)
            box.addButton("Schließen", QtWidgets.QMessageBox.RejectRole)
            box.exec()
            geklickt = box.clickedButton()
            if geklickt is neu:
                self.einrichten()
            elif box.buttonRole(geklickt) == QtWidgets.QMessageBox.HelpRole:
                self.hilfe()

    def setEnabled_buttons(self, an: bool):
        for b in self.findChildren(QtWidgets.QPushButton):
            b.setEnabled(an)


def starten() -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    rezepte = alle_rezepte()
    if not rezepte:
        QtWidgets.QMessageBox.critical(None, "Magic Hand",
                                       "Kein Rezept gefunden (rezept.yaml).")
        return 1
    leiste = Leiste(rezepte)
    leiste.show()
    return app.exec()
