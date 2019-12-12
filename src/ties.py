from PyQt5 import QtWidgets, QtSql, QtCore, uic
import logging
import os


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

    def model_setup(self):
        self.logger.info("Initializing Model")
        tie_model = QtSql.QSqlRelationalTableModel(self)
        tie_model.setTable("ties")
        tie_model.setRelation(0, QtSql.QSqlRelation("teams", "id", "Name"))
        tie_model.setRelation(1, QtSql.QSqlRelation("teams", "id", "Name"))
        tie_model.setRelation(3, QtSql.QSqlRelation("teams", "id", "Name"))
        tie_model.setEditStrategy(QtSql.QSqlTableModel.OnFieldChange)
        tie_model.select()
        self.model = tie_model

    def view_setup(self):
        self.local_delegates = []
        self.table.setModel(self.model)
        self.local_delegates.append(ReadOnlyDelegate(self.table))
        self.table.setItemDelegateForColumn(0, self.local_delegates[-1])
        self.local_delegates.append(ReadOnlyDelegate(self.table))
        self.table.setItemDelegateForColumn(1, self.local_delegates[-1])
        self.local_delegates.append(QtSql.QSqlRelationalDelegate(self.table))
        self.table.setItemDelegateForColumn(3, self.local_delegates[-1])

    def show(self):
        self.model.select()
        super(TieWindow, self).show()


class ReadOnlyDelegate(QtSql.QSqlRelationalDelegate):
    def __init__(self, parent):
        super(ReadOnlyDelegate, self).__init__(parent=parent)

    def editorEvent(self, event, model, option, index):
        return False

    def createEditor(self, parent, option, index):
        return None

# TODO:
#   New Delegate for event column
#   New Delegate for winner column
#   Header Data




