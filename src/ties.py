from PyQt5 import QtWidgets, QtSql, QtCore, uic
import logging
import os
import utils


class TieWindow(QtWidgets.QMainWindow):
    def __init__(self, parent, db):
        super(TieWindow, self).__init__(parent=parent)
        uic.loadUi(f"ui{os.sep}display_ties.ui", self)
        self.setWindowTitle("Ties")
        self.logger = logging.getLogger("Main.TieDisplay")
        self.table = self.findChild(QtWidgets.QTableView)
        self.db = db
        self.model = None
        self.local_delegates = None
        self.model_setup()
        self.view_setup()
        self.window().resize(
            self.centralWidget().minimumWidth(), self.centralWidget().height()
        )

    def model_setup(self):
        self.logger.info("Initializing Model")
        tie_model = QtSql.QSqlRelationalTableModel(self)
        tie_model.setTable("ties")
        tie_model.setHeaderData(1, QtCore.Qt.Horizontal, "Team 1")
        tie_model.setHeaderData(2, QtCore.Qt.Horizontal, "Team 2")
        tie_model.setHeaderData(3, QtCore.Qt.Horizontal, "Event")
        tie_model.setHeaderData(4, QtCore.Qt.Horizontal, "Winner")
        tie_model.setRelation(1, QtSql.QSqlRelation("teams", "id", "Name"))
        tie_model.setRelation(2, QtSql.QSqlRelation("teams", "id", "Name"))
        tie_model.setEditStrategy(QtSql.QSqlTableModel.OnFieldChange)
        tie_model.select()
        self.model = tie_model
        self.model.dataChanged.connect(self.update_min_width)

    def view_setup(self):
        self.local_delegates = []
        self.table.setModel(self.model)
        self.table.resizeColumnsToContents()
        self.table.setColumnHidden(0, True)
        self.local_delegates.append(ReadOnlyDelegate(self.table))
        self.table.setItemDelegateForColumn(1, self.local_delegates[-1])
        self.local_delegates.append(ReadOnlyDelegate(self.table))
        self.table.setItemDelegateForColumn(2, self.local_delegates[-1])
        self.local_delegates.append(EventDelegate(self.table))
        self.table.setItemDelegateForColumn(3, self.local_delegates[-1])
        self.local_delegates.append(WinnerDelegate(self.table))
        self.table.setItemDelegateForColumn(4, self.local_delegates[-1])
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )
        self.update_min_width()
        self.table.horizontalHeader().setSectionResizeMode(
            3, QtWidgets.QHeaderView.Fixed
        )
        self.table.setColumnWidth(3, 80)
        self.table.horizontalHeader().setSectionResizeMode(
            4, QtWidgets.QHeaderView.Stretch
        )

    def show(self):
        self.model.select()
        super(TieWindow, self).show()

    def update_min_width(self):
        self.centralWidget().setMinimumWidth(
            self.table.horizontalHeader().length() + self.table.verticalHeader().width()
        )


class ReadOnlyDelegate(QtSql.QSqlRelationalDelegate):
    def __init__(self, parent):
        super(ReadOnlyDelegate, self).__init__(parent=parent)

    def editorEvent(self, event, model, option, index):
        return False

    def createEditor(self, parent, option, index):
        return None


class EventDelegate(QtWidgets.QItemDelegate):
    def __init__(self, parent=None):
        super(EventDelegate, self).__init__(parent=parent)

    def setEditorData(self, editor, index):
        value = index.model().data(index, QtCore.Qt.EditRole)
        if value:
            editor.setCurrentIndex(editor.findText(value))

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        editor.addItems(utils.events)
        return editor

    def setModelData(self, editor, model, index) -> None:
        model.setData(index, editor.currentText(), QtCore.Qt.EditRole)


class WinnerDelegate(QtSql.QSqlRelationalDelegate):
    def __init__(self, parent=None):
        super(WinnerDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        painter.save()

        # Select highlighting
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())

        rect = option.rect
        rect -= QtCore.QMargins(6, 6, 6, 6)
        t_1_name = index.siblingAtColumn(1).data(QtCore.Qt.EditRole)
        t_2_name = index.siblingAtColumn(2).data(QtCore.Qt.EditRole)
        value = [t_1_name, t_2_name][not index.data(QtCore.Qt.EditRole)]
        painter.drawText(rect, (QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter), str(value))

        painter.restore()

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        t_1_name = index.siblingAtColumn(1).data(QtCore.Qt.EditRole)
        t_2_name = index.siblingAtColumn(2).data(QtCore.Qt.EditRole)
        editor.clear()
        editor.addItem(t_1_name, 1)
        editor.addItem(t_2_name, 0)
        editor.setCurrentIndex(not index.data(QtCore.Qt.EditRole))
        return editor

    def setModelData(self, editor, model, index) -> None:
        model.setData(index, editor.currentData(), QtCore.Qt.EditRole)
