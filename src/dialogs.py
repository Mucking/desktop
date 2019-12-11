import datetime
import logging
import os
from PyQt5 import QtWidgets, uic, QtSql
from PyQt5.QtCore import pyqtSignal
import utils


class NewComp(QtWidgets.QDialog):
    def __init__(self):
        super(NewComp, self).__init__()
        uic.loadUi(f"ui{os.sep}new_comp.ui", self)
        self.logger = logging.getLogger("Main.NewComp")
        self.logger.info("Generating New Competition from Dialog")
        self.setWindowTitle("New...")
        self.host = self.findChild(QtWidgets.QLineEdit, "hostname_value")
        self.units = self.findChild(QtWidgets.QComboBox, "units_value")
        self.year = self.findChild(QtWidgets.QSpinBox, "year_value")
        self.year.setValue(datetime.datetime.now().year)
        self.bb = self.findChild(QtWidgets.QDialogButtonBox)
        self.ok = self.bb.button(self.bb.Save)
        self.ok.setEnabled(False)
        self.host.textChanged.connect(self.verify)

    def verify(self):
        self.logger.debug("Checking host.text != None")
        if not self.host.text():
            self.ok.setEnabled(False)
        else:
            self.ok.setEnabled(True)


class NewTeam(QtWidgets.QDialog):
    def __init__(self):
        super(NewTeam, self).__init__()
        uic.loadUi(f"ui{os.sep}new_team.ui", self)
        self.logger = logging.getLogger("Main.NewTeam")
        self.logger.info("Generating New Team from Dialog")
        self.setWindowTitle("New Team")
        self.school = self.findChild(QtWidgets.QLineEdit, "v_school")
        self.name = self.findChild(QtWidgets.QLineEdit, "v_team_name")
        self.division = self.findChild(QtWidgets.QComboBox, "v_division")
        self.bb = self.findChild(QtWidgets.QDialogButtonBox)
        self.ok = self.bb.button(self.bb.Save)
        self.ok.setEnabled(False)
        self.name.textChanged.connect(self.verify)

    def verify(self):
        self.logger.debug("Checking name.text != None")
        if not self.name.text():
            self.ok.setEnabled(False)
        else:
            self.ok.setEnabled(True)


class TieDialog(QtWidgets.QDialog):
    team_changed = pyqtSignal()

    def __init__(self, team_1_id=None, team_2_id=None):
        super(TieDialog, self).__init__()
        uic.loadUi(f"ui{os.sep}new_tie.ui", self)
        self.logger = logging.getLogger("Main.NewTie")
        self.bb = self.findChild(QtWidgets.QDialogButtonBox)
        self.ok = self.bb.button(self.bb.Ok)
        self.ok.setEnabled(False)
        self.setWindowTitle("New Tie")
        self.team_1 = self.findChild(QtWidgets.QComboBox, "cb_team_1")
        self.team_2 = self.findChild(QtWidgets.QComboBox, "cb_team_2")
        self.tie_event = self.findChild(QtWidgets.QComboBox, "cb_event")
        self.winner = self.findChild(QtWidgets.QComboBox, "cb_winner")
        self.setup_combos(team_1_id, team_2_id)
        self.team_1.currentIndexChanged.connect(self.update_winner_box)
        self.team_1.currentIndexChanged.connect(self.update_combo_2)
        self.team_2.currentIndexChanged.connect(self.update_winner_box)
        self.update_winner_box()
        self.tie_event.currentIndexChanged.connect(self.verify)
        self.winner.currentIndexChanged.connect(self.verify)

    def verify(self):
        if not self.winner.currentText() or not self.tie_event.currentText():
            self.ok.setEnabled(False)
        else:
            self.ok.setEnabled(True)

    def setup_combos(self, team_1_id, team_2_id):
        for event in utils.events:
            self.tie_event.addItem(event)

        query = QtSql.QSqlQuery()
        query.exec_("SELECT id, Name FROM teams;")
        while query.next():
            self.team_1.addItem(query.value(1), query.value(0))
        query.clear()
        del query

        if team_1_id:
            self.team_1.setCurrentIndex(self.team_1.findData(team_1_id) + 1)

        self.update_combo_2()

        if team_2_id:
            self.team_2.setCurrentIndex(self.team_2.findData(team_2_id) + 1)


    def update_combo_2(self):
        team_1_id = self.team_1.currentData()
        query = QtSql.QSqlQuery()
        query.exec_(f"SELECT Division from teams WHERE id = {team_1_id}")
        query.next()
        div = query.value(0)
        query.exec_(f"SELECT id, Name FROM teams WHERE Division = '{div}';")
        self.team_2.clear()
        while query.next():
            if query.value(0) != team_1_id:
                self.team_2.addItem(query.value(1), query.value(0))
        query.clear()
        del query

    def update_winner_box(self):
        self.winner.clear()
        self.winner.addItem("", -1)
        self.winner.addItem(self.team_1.currentText(), self.team_1.currentData())
        self.winner.addItem(self.team_2.currentText(), self.team_2.currentData())


class RetryDialog(QtWidgets.QDialog):
    retry = pyqtSignal()

    def __init__(self, title, text, acc_text):
        super(RetryDialog, self).__init__()
        uic.loadUi(f"ui{os.sep}diag_retry_accept_reject.ui", self)
        self.logger = logging.getLogger("Main.NewComp")
        self.logger.warning(f"{title} Error Occurred, Attempting to Recover")
        self.setWindowTitle(title)
        self.details = self.findChild(QtWidgets.QLabel, "l_dialog_info")
        self.details.setText(text)
        self.b_action = self.findChild(QtWidgets.QPushButton, "b_accept")
        self.b_action.setText(acc_text)
        self.b_retry = self.findChild(QtWidgets.QPushButton, "b_retry")
        self.b_retry.clicked.connect(self.emit_retry)

    def emit_retry(self):
        self.done(-1)
        self.retry.emit()


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super(SettingsDialog, self).__init__(parent=parent)
        uic.loadUi(f"ui{os.sep}settings_menu.ui", self)
        # TODO: Load from settings file for default checked boxes
        self.settings = self.parent().settings
        self.host = self.findChild(QtWidgets.QLineEdit, "v_settings_host")
        self.host.setText(self.parent().settings.value("comp/host"))
        self.year = self.findChild(QtWidgets.QSpinBox, "v_settings_year")
        self.year.setValue(int(self.parent().settings.value("comp/year")))
        self.units = self.findChild(QtWidgets.QComboBox, "v_settings_units")
        self.units.setCurrentIndex(
            self.units.findText(self.settings.value("comp/units"))
        )
        self.bg_time = self.findChild(QtWidgets.QButtonGroup, "bg_time")
        self.bg_i_jackleg = self.findChild(QtWidgets.QButtonGroup, "bg_i_jackleg")
        self.bg_i_handsteel = self.findChild(QtWidgets.QButtonGroup, "bg_i_handsteel")
        self.bg_i_survey = self.findChild(QtWidgets.QButtonGroup, "bg_i_survey")
        self.bg_m_jackleg = self.findChild(QtWidgets.QButtonGroup, "bg_m_jackleg")
        self.bg_m_handsteel = self.findChild(QtWidgets.QButtonGroup, "bg_m_handsteel")
        self.bg_m_survey = self.findChild(QtWidgets.QButtonGroup, "bg_m_survey")

    def update_settings(self):
        values = {
            "units/time": self.bg_time.checkedButton().text().lower(),
            "iunits/handsteel": self.bg_i_handsteel.checkedButton().text().lower(),
            "iunits/jackleg": self.bg_i_jackleg.checkedButton().text().lower(),
            "iunits/survey": self.bg_i_survey.checkedButton().text().lower(),
            "munits/handsteel": self.bg_m_handsteel.checkedButton().text().lower(),
            "munits/jackleg": self.bg_m_jackleg.checkedButton().text().lower(),
            "munits/survey": self.bg_m_survey.checkedButton().text().lower(),
        }

        return values
