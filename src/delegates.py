import logging
from math import isclose
from PyQt5 import QtCore, QtWidgets, QtGui
import utils


class TimeValidator(QtGui.QValidator):
    def __init__(self, parent):
        super(TimeValidator, self).__init__(parent=parent)
        self.statusBar = self.parent().parent().statusBar()

    def validate(self, value: str, cursor_pos: int):
        state = self.Invalid

        if value.count(":") == 0:
            if value == "":
                state = self.Acceptable
            elif value in ["d", "D"]:
                state = self.Intermediate
            elif value in ["DQ", "dq", "Dq", "dQ"]:
                state = self.Acceptable
            else:
                try:
                    float(value)
                    state = self.Acceptable
                except ValueError:
                    state = self.Invalid
                    self.statusBar.showMessage("Invalid Character", 2500)

        elif value.count(":") == 1:
            if value.endswith(":"):
                state = self.Intermediate
            else:
                m, s = value.split(":")
                try:
                    s = float(s)
                    if int(s) < 60:
                        state = self.Acceptable
                    else:
                        state = self.Invalid
                        self.statusBar.showMessage(
                            "Seconds cannot be > 60 when minutes are specified",
                            2500
                        )
                except ValueError:
                    state = self.Invalid
                    self.statusBar.showMessage("Invalid Character", 2500)

        elif value.count(":") == 2:
            if value.endswith(":"):
                state = self.Intermediate
                if value.endswith("::"):
                    state = self.Invalid
                    self.statusBar.showMessage("Minutes must be at least 0", 2500)
            else:
                h, m, s = value.split(":")
                try:
                    m = float(m)
                    s = float(s)
                    if m < 60 and s < 60:
                        state = self.Acceptable
                    else:
                        state = self.Invalid
                        if m > 60:
                            self.statusBar.showMessage(
                                "Minutes cannot be > 60 when hours are specified",
                                2500
                            )
                        elif s > 60:
                            self.statusBar.showMessage(
                                "Seconds cannot be > 60 when minutes are specified",
                                2500
                            )
                except ValueError:
                    state = self.Invalid
                    self.statusBar.showMessage("Invalid Character", 2500)

        elif value.count(":") > 2:
            state = self.Invalid

        return state, value, cursor_pos


class DistValidator(QtGui.QValidator):
    def __init__(self, parent):
        super(DistValidator, self).__init__(parent=parent)
        self.statusBar = self.parent().parent().statusBar()

    def validate(self, value: str, cursor_pos: int):
        state = self.Invalid
        if len(value) == 0:
            state = self.Acceptable
        elif value in ["d", "D"]:
            state = self.Intermediate
        elif value in ["DQ", "dq", "Dq", "dQ"]:
            state = self.Acceptable
        else:
            value = value.lower()
            if value.isdecimal():
                state = self.Intermediate
            else:
                try:
                    float(value)
                    state = self.Intermediate
                except ValueError:
                    unit_text = "".join([c for c in value if c.isalpha()])
                    if len(unit_text) == 1 and unit_text in "mckif":
                        state = self.Intermediate
                    else:
                        for unit in utils.UNIT_FACTORS:
                            if value.endswith(unit):
                                state = self.Acceptable
                                break
        if "-" in value:
            state = self.Invalid
            self.statusBar.showMessage("Values Less than 0 not allowed", 2500)

        return state, value, cursor_pos


class BaseDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent):
        super(BaseDelegate, self).__init__(parent=parent)
        self.logger = None
        self.h_align = QtCore.Qt.AlignRight
        self.init_logger("Editor")

    def init_logger(self, name):
        if not self.logger:
            self.logger = logging.getLogger(f"Main.{name}")

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def paint(self, painter, option, index):
        # self.initStyleOption(option, index)
        painter.save()

        # Select highlighting
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())

        rect = option.rect
        rect -= QtCore.QMargins(6, 6, 6, 6)
        value = index.model().data(index, QtCore.Qt.DisplayRole)
        painter.drawText(
            rect, (self.h_align | QtCore.Qt.AlignVCenter), self.display(value)
        )

        painter.restore()

    def setModelData(self, editor, model, index):
        value = index.model().data(index, QtCore.Qt.EditRole)
        new_value = self.modelUpdate(editor, model, index)

        # Discard Values that are input within 0.01 cm of each other or None for new
        if value not in [None, '']:
            if new_value not in ["DQ", "dq", "Dq", "dQ", None]:
                if isclose(value, new_value, abs_tol=0.01):
                    return

        model.setData(index, new_value, QtCore.Qt.EditRole)

        # Logging of Transaction
        if value in [utils.DQ_TIME, utils.DQ_MAX_LENGTH, utils.DQ_MIN_LENGTH]:
            value = "DQ"
        if new_value in [utils.DQ_TIME, utils.DQ_MAX_LENGTH, utils.DQ_MIN_LENGTH]:
            new_value = "DQ"

        sname = model.data(index.siblingAtColumn(1), QtCore.Qt.EditRole)
        tname = model.data(index.siblingAtColumn(2), QtCore.Qt.EditRole)
        event = model.headerData(
            index.column(), QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole
        )

        self.logger.txn(f"{sname} - {tname} - {event} {value} -> {new_value}")

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        editor.setFrame(False)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, QtCore.Qt.EditRole)
        editor.setText(self.display(value))

    def sizeHint(self, option, index):
        value = index.model().data(index, QtCore.Qt.DisplayRole)
        rect = option.fontMetrics.boundingRect(self.display(value))
        rect += QtCore.QMargins(8, 0, 8, 0)
        return rect.size()

    def display(self, value) -> str:
        # Must be implemented for each derivative class
        raise NotImplementedError

    def modelUpdate(self, editor, model, index):
        raise NotImplementedError


class DivisionDelegate(BaseDelegate):
    def __init__(self, parent):
        super(DivisionDelegate, self).__init__(parent=parent)
        self.h_align = QtCore.Qt.AlignHCenter

    def display(self, value):
        return utils.DIVISION_LEXICON[value]

    def setEditorData(self, editor, index):
        value = index.model().data(index, QtCore.Qt.EditRole)
        val_index = editor.findText(utils.DIVISION_LEXICON[value])
        if val_index:
            editor.setCurrentIndex(val_index)
        else:
            editor.setCurrentIndex(0)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        editor.setFrame(False)
        editor.addItem("Men's")
        editor.addItem("Women's")
        editor.addItem("Co-Ed")
        editor.addItem("Alumni")
        return editor

    def modelUpdate(self, editor, model, index):
        return utils.DIVISION_LEXICON[editor.currentText()]


class TimeEditDelegate(BaseDelegate):
    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        editor.setFrame(False)
        editor.setValidator(TimeValidator(parent=self))
        return editor

    def display(self, value):
        if not value:
            return ""

        display_mode = self.parent().settings.value("app/display")

        if display_mode == "rank":
            return str(value)
        else:
            if value == utils.DQ_TIME:
                return "DQ"
            if self.parent().settings.value("units/time", "ssss.ss") == "ssss.ss":
                s_time = f"{value:7.2f}"
            else:
                hours = int(value // 3600)
                minutes = int((value - hours * 3600) // 60)
                seconds = value - hours * 3600 - minutes * 60

                s_time = f"{minutes}:{seconds:05.2f}"

                if hours:
                    s_time = f"{hours}:{minutes:02}:{seconds:05.2f}"

            return s_time

    def modelUpdate(self, editor, model, index):
        value = editor.text()

        # Set field to None/NULL when left empty
        if value == "":
            return None

        # Check for DQ
        if value in ["DQ", "dq", "Dq", "dQ"]:
            return utils.DQ_TIME

        if value.count(":") == 2:
            h, m, s = value.split(":")
            seconds = int(h) * 3600 + int(m) * 60 + float(s)
        elif value.count(":") == 1:
            m, s = value.split(":")
            seconds = int(m) * 60 + float(s)
        else:
            seconds = float(value)

        return seconds


class DistanceEditDelegate(BaseDelegate):
    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        editor.setFrame(False)
        editor.setValidator(DistValidator(parent=self))
        return editor

    def display(self, value):
        raise NotImplementedError

    # ONLY WORKS IN PYTHON 3.6+ due to dict insertion ordering
    # Due to the looping check order of these units is important
    # e.g. km must come before m since 5.0km would match m as 5.0k
    # leading to issues when the program tries to convert to a float
    def modelUpdate(self, editor, model, index):
        units_detected = False
        # Set field to None/NULL when editor is empty
        if editor.text() == "":
            return None

        string = editor.text()

        # Ensure that there are no trailing spaces
        string = string.lower().strip()

        if string in ["DQ", "dq", "Dq", "dQ"]:
            return self.dq_value

        # TODO: Implement Fraction Inches input
        for unit in utils.UNIT_FACTORS:
            if string.endswith(unit):
                units_detected = True
                self.parent().logger.debug(
                    f"Detected units {unit}: {string.replace(unit, '').strip()}"
                )
                try:
                    cms = (
                        float(string.replace(unit, "").strip())
                        / utils.UNIT_FACTORS[unit]
                    )
                    return cms
                except ValueError:
                    self.parent().logger.error(f"Partial Unit match of input: {string}")

        if not units_detected:
            self.parent().logger.error(f"Unable to detect units of input: {string}")
            return

    @property
    def dq_value(self):
        raise NotImplementedError


class HandsteelDelegate(DistanceEditDelegate):
    def display(self, value):
        # Check for DQ
        if value == utils.DQ_MIN_LENGTH:
            return "DQ"

        # Check for null values
        if not value:
            return ""

        display_mode = self.parent().settings.value("app/display")

        if display_mode == "rank":
            return str(value)
        else:
            # Check display units
            if self.parent().settings.value("app/display", "metric") == "metric":
                units = self.parent().settings.value("munits/handsteel", "mm")
            else:
                units = self.parent().settings.value("iunits/handsteel", "in")

            # Dynamic Unit Selection Support
            if units == "dynamic":
                units = utils.get_reasonable_unit(
                    value,
                    self.parent().settings.value("app/display", "metric") == "metric",
                )

            # Convert and display
            return f"{value * utils.UNIT_FACTORS[units]:.2f} {units}"

    @property
    def dq_value(self):
        return utils.DQ_MIN_LENGTH


class JacklegDelegate(DistanceEditDelegate):
    def display(self, value):
        # Check for DQ
        if value == utils.DQ_MIN_LENGTH:
            return "DQ"

        # Check for null values
        if not value:
            return ""
        display_mode = self.parent().settings.value("app/display")

        if display_mode == "rank":
            return str(value)
        else:
            # Check display units
            if self.parent().settings.value("app/display", "metric") == "metric":
                units = self.parent().settings.value("munits/jackleg", "cm")
            elif self.parent().settings.value("app/display", "imperial") == "imperial":
                units = self.parent().settings.value("iunits/jackleg", "in")

            # Convert and display
            return f"{value * utils.UNIT_FACTORS[units]:.2f} {units}"

    @property
    def dq_value(self):
        return utils.DQ_MIN_LENGTH


class SurveyDelegate(DistanceEditDelegate):
    def display(self, value):
        # Check for null values
        if not value:
            return ""

        # Check for DQ
        if value == utils.DQ_MAX_LENGTH:
            return "DQ"

        display_mode = self.parent().settings.value("app/display")

        if display_mode == "rank":
            return str(value)
        else:
            # Check display units
            if self.parent().settings.value("app/display", "metric") == "metric":
                units = self.parent().settings.value("munits/survey", "dynamic")
            else:
                units = self.parent().settings.value("iunits/survey", "dynamic")

            # Convert and display
            if units == "dynamic":
                units = utils.get_reasonable_unit(
                    value,
                    self.parent().settings.value("app/display", "metric") == "metric",
                )

            return f"{value * utils.UNIT_FACTORS[units]:.3f} {units: >2}"

    @property
    def dq_value(self):
        return utils.DQ_MAX_LENGTH
