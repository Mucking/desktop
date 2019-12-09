import logging
from PyQt5 import QtCore, QtWidgets
import utils


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
                    s_time = f"{hours}:" + s_time

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

        if seconds < 0:
            utils.alert("Input Error", "Times less than 0 are not valid", "warn")
        else:
            return seconds


class DistanceEditDelegate(BaseDelegate):
    # ONLY WORKS IN PYTHON 3.6+ due to dict insertion ordering
    # Due to the looping check order of these units is important
    # e.g. km must come before m since 5.0km would match m as 5.0k
    # leading to issues when the program tries to convert to a float

    def display(self, value):
        raise NotImplementedError

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
        units_error_text = "\nPlease make sure the input ends with one of the following\n'km','m','cm','mm', 'mi', 'ft', 'in'"

        # TODO: Implement Fraction Inches input
        for unit in utils.UNIT_FACTORS:
            if string.endswith(unit):
                self.parent().logger.debug(
                    f"Detected units {unit}: {string.replace(unit, '').strip()}"
                )
                try:
                    cms = (
                        float(string.replace(unit, "").strip())
                        / utils.UNIT_FACTORS[unit]
                    )
                    units_detected = True
                except ValueError:
                    self.parent().logger.error(f"Partial Unit match of input: {string}")
                else:
                    if cms < 0:
                        utils.alert(
                            "Input Error", "Distances less than 0 are not valid", "warn"
                        )
                        return
                    return cms

        if not units_detected:
            self.parent().logger.error(f"Unable to detect units of input: {string}")
            utils.alert("Could not detect Units", units_error_text, "warn")
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
