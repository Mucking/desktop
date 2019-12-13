import logging
import os
import sqlite3
import sys
from datetime import datetime
from PyQt5 import QtCore, QtWidgets, uic, QtSql
import dialogs
import delegates
import utils
import ties
import pathlib

VERSION = "2019.00.90"


class GUI(QtWidgets.QMainWindow):
    # Define Class Signals
    settings_changed = QtCore.pyqtSignal()
    db_changed = QtCore.pyqtSignal()

    def setup_custom_logging(self):
        logging.addLevelName(utils.TXN_LEVEL_NUM, "TXN")
        logging.Logger.txn = utils.txn

        self.logger = logging.getLogger("Main")
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "[%(asctime)-10s][%(levelname)-8s] %(name)-15s - %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Error Checking for log files
        logs_dir = pathlib.Path(f"{self.directory}{os.sep}logs")
        log_file = pathlib.Path(
            f"{logs_dir}{os.sep}mucking_{datetime.now().date()}.log"
        )
        if not logs_dir.is_dir():
            logs_dir.mkdir()
            if not log_file.exists():
                log_file.touch()

        file_handler = logging.FileHandler(
            f"logs{os.sep}mucking_{datetime.now().date()}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.info("Logger Initalized")

    def __init__(self):
        self.directory = QtCore.QDir.currentPath()
        self.data_dir = pathlib.Path(self.directory + os.sep + "data")
        if not self.data_dir.is_dir():
            self.data_dir.mkdir()

        # Logging Setup
        self.logger = None
        self.setup_custom_logging()
        self.logger.info(f"Mucking Score Tracker V{VERSION}")

        # UI Setup
        super(GUI, self).__init__()
        uic.loadUi(f"ui{os.sep}Mucking Score Tracker.ui", self)
        self.logger.info("Setting Up Main UI")

        # Placeholders for active competition variables
        self.settings = None
        self.db = None
        self.data_model = None
        self.rank_model = None
        self.display = self.findChild(QtWidgets.QStackedWidget, "screens")

        # Active Comp Screen
        self.logger.info("Setting Up Comp Screen")
        self.comp_screen = self.findChild(QtWidgets.QWidget, "s_comp")
        self.show()
        self.conn_status = QtWidgets.QLabel()
        self.statusBar().addPermanentWidget(self.conn_status)
        self.c_filter = self.findChild(QtWidgets.QComboBox, "v_div_filter")
        self.c_filter.currentTextChanged.connect(self.model_filter)
        self.rb_imperial = self.findChild(QtWidgets.QRadioButton, "rb_units_imperial")
        self.rb_imperial.toggled.connect(self.units_update)
        self.rb_metric = self.findChild(QtWidgets.QRadioButton, "rb_units_metric")
        self.rb_metric.toggled.connect(self.units_update)
        self.rb_rank = self.findChild(QtWidgets.QRadioButton, "rb_units_rank")
        self.rb_rank.toggled.connect(self.units_update)
        self.team_table = self.findChild(QtWidgets.QTableView, "teams_table")
        self.team_table.installEventFilter(self)
        self.ties_window = None
        b_team_add = self.findChild(QtWidgets.QPushButton, "b_team_add")
        b_team_add.clicked.connect(self.team_create)
        b_comp_score = self.findChild(QtWidgets.QPushButton, "b_comp_score")
        b_comp_score.clicked.connect(self.comp_score)
        self.local_delegates = None

        # Welcome Screen
        self.logger.info("Setting Up Welcome Screen")
        self.welcome_screen = self.findChild(QtWidgets.QWidget, "s_welcome")
        b_load_comp = self.findChild(QtWidgets.QPushButton, "b_load_comp")
        b_load_comp.clicked.connect(self.comp_load)
        b_new_comp = self.findChild(QtWidgets.QPushButton, "b_new_comp")
        b_new_comp.clicked.connect(self.comp_create)

        # Menu Setup
        self.logger.info("Setting Up Dropdown Menus")
        action_new = self.findChild(QtWidgets.QAction, "a_comp_new")
        action_new.triggered.connect(self.comp_create)
        action_open = self.findChild(QtWidgets.QAction, "a_comp_open")
        action_open.triggered.connect(self.comp_load)
        action_close = self.findChild(QtWidgets.QAction, "a_comp_close")
        action_close.triggered.connect(self.restart_app)
        action_save = self.findChild(QtWidgets.QAction, "a_comp_save")
        action_save.triggered.connect(self.comp_save)
        action_save = self.findChild(QtWidgets.QAction, "a_comp_saveAs")
        action_save.triggered.connect(self.comp_save_as)
        action_quit = self.findChild(QtWidgets.QAction, "a_quit")
        action_quit.triggered.connect(self.close)
        action_settings = self.findChild(QtWidgets.QAction, "a_edit_preferences")
        action_settings.triggered.connect(self.settings_modify)
        action_add_team = self.findChild(QtWidgets.QAction, "a_edit_add_team")
        action_add_team.triggered.connect(self.team_create)
        action_add_tie = self.findChild(QtWidgets.QAction, "a_edit_add_tie")
        action_add_tie.triggered.connect(self.tie_add)

        # Context Menu Setup
        self.logger.info("Setting Up Context Menu")
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        context_action_add_team = QtWidgets.QAction("Add Team", self)
        context_action_add_team.triggered.connect(self.team_create)
        self.addAction(context_action_add_team)

        context_action_del_team = QtWidgets.QAction("Delete Team", self)
        context_action_del_team.triggered.connect(self.team_delete)
        self.addAction(context_action_del_team)

        context_action_add_tie = QtWidgets.QAction("Add Tie", self)
        context_action_add_tie.triggered.connect(self.tie_add)
        self.addAction(context_action_add_tie)

        # Default to welcome screen
        self.display.setCurrentWidget(self.welcome_screen)

        # Listen for settings changed signal settings update
        self.db_changed.connect(self.db_update)

    def db_update(self):
        self.logger.info("Database File Changed")
        # TODO: Handle closing of DB
        self.db_setup()
        self.model_setup()
        self.view_setup()

    # Tie functions
    def tie_add(self):
        indexes = self.team_table.selectionModel().selectedRows()
        if len(indexes) == 1:
            diag = dialogs.TieDialog(indexes[0].row())
        elif len(indexes) == 2:
            query = QtSql.QSqlQuery()
            query.exec_(f"SELECT Division from teams where id = {indexes[0].row()+1};")
            query.next()
            t1_div = query.value(0)
            query.exec_(f"SELECT Division from teams where id = {indexes[1].row()+1};")
            query.next()
            t2_div = query.value(0)
            query.clear()
            del query

            if t1_div != t2_div:
                utils.alert("Error", "Ties can only exist within a division ", "crit")
                return
            else:
                diag = dialogs.TieDialog(indexes[0].row(), indexes[1].row())
                pass
        else:
            diag = dialogs.TieDialog()

        if diag.exec_():
            t1_id = diag.team_1.currentData()
            t1_name = diag.team_1.currentText()
            t2_id = diag.team_2.currentData()
            t2_name = diag.team_2.currentText()
            e_name = diag.tie_event.currentText()
            w_id = diag.winner.currentData()
            w_name = diag.winner.currentText()
            query = QtSql.QSqlQuery()
            self.logger.txn(
                f"Add Tie between {t1_name} and {t2_name}, E: {e_name}, W: {w_name}"
            )
            query.exec_(
                f"INSERT INTO ties (team_1_id, team_2_id, event, winner) VALUES ({t1_id}, {t2_id}, '{e_name}', {w_id});"
            )
            query.clear()
            del query

    # Competition Management Functions
    def comp_create(self):
        self.logger.info("Creating New Competition Config File")
        diag = dialogs.NewComp()
        if diag.exec_():
            self.logger.debug("NewComp Dialog Success")
            if self.settings:
                self.settings.sync()
                self.settings = None
            year = diag.year.value()

            # Default Settings to config file
            config_file = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save File",
                str(self.data_dir) + os.sep + f"mucking_{year}.config",
                "Config File (*.config)",
            )[0]
            self.logger.debug(f"Saving Default settings to {config_file}")
            self.settings = QtCore.QSettings(config_file, QtCore.QSettings.IniFormat)
            self.settings.setValue("app/display", "metric")
            self.settings.setValue("comp/host", diag.host.text())
            self.settings.setValue("comp/units", diag.units.currentText())
            self.settings.setValue("comp/year", year)
            self.settings.setValue("units/time", "hh:mm:ss.ss")
            self.settings.setValue("iunits/handsteel", "in")
            self.settings.setValue("iunits/jackleg", "ft")
            self.settings.setValue("iunits/survey", "dynamic")
            self.settings.setValue("munits/handsteel", "mm")
            self.settings.setValue("munits/jackleg", "cm")
            self.settings.setValue("munits/survey", "dynamic")
            self.settings.sync()

            # setup database
            db_filepath = config_file.replace(".config", ".db")
            self.logger.debug(f"Creating New Database {db_filepath}")
            db = sqlite3.connect(db_filepath)
            db.close()
            self.settings.setValue("db/path", db_filepath)

            self.db_changed.emit()

            # Change to Welcome Screen
            self.display.setCurrentWidget(self.comp_screen)

    def comp_load(self):
        # TODO: Detect if comp already loaded and cleanly disconnect (HARD)
        config_file = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load File", str(self.data_dir), "Config File (*.config)"
        )[0]
        if not config_file:
            return
        self.logger.info(f"Loading Competition {config_file}")
        self.settings = QtCore.QSettings(config_file, QtCore.QSettings.IniFormat)
        self.db_changed.emit()
        # match display units to last display mode
        display_button = getattr(
            self, f"rb_{self.settings.value('app/display', 'Imperial')}"
        )
        display_button.toggle()
        self.display.setCurrentWidget(self.comp_screen)

    def comp_save(self):
        self.logger.info(f"Manual Save Initiated")
        self.settings.sync()
        # DB Save scheme means save after every change

    def comp_save_as(self):
        self.logger.info(f"Save As current competition")
        # TODO: Update method to better handle database close/reopen
        #  Ties in with comp_load and comp_close issues
        prev = self.settings
        config_file = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save File", self.settings.fileName(), "Config File (*.config)"
        )[0]

        self.logger.info(f"Copying settings {prev.fileName()} -> {config_file}")
        self.settings = QtCore.QSettings(config_file, QtCore.QSettings.IniFormat)
        for key in prev.allKeys():
            self.settings.setValue(key, prev.value(key))

        # Update DB path
        self.settings.setValue("db/path", config_file.replace(".config", ".db"))

        # Copy DB
        self.logger.info(f"Copying Database to {config_file.replace('.config', '.db')}")
        utils.db_copy(prev.value("db/path"), self.settings.value("db/path"))

        # Close Existing Database
        self.logger.info(f"Closing Existing Database connections")
        self.data_model.clear()
        self.db.removeDatabase(self.db.connectionName())

        # Reinitialize application
        self.settings_changed.emit()

    def comp_close(self):
        self.logger.info(f"Closing Settings and Database Connections")
        print(self.db.connectionNames())
        self.settings.sync()
        self.data_model.close()
        dbname = self.db.connectionName()
        self.settings = None
        self.db = None
        self.data_model = None
        QtSql.QSqlDatabase.removeDatabase(dbname)
        self.team_table.setModel(None)
        self.display.setCurrentWidget(self.welcome_screen)

    def comp_score(self):
        # TODO: Verify no nulls
        # TODO: Improve Scoring Algorithm (Currently does not expect ties)
        #       Current Scoring Improvements
        #         Check if values for a given team are the same in an event
        #         Event Score Check on primary table and then make changes to rank table
        #         2 teams tied for 2nd place both get 2 points and the next team gets 4
        #         This propogates scores cascading down rather than up
        #       Account for ties won in the overall ranking
        #         Needed since event scores will not change

        event_sorting = {
            "Mucking": "ASC",
            "Swede Saw": "ASC",
            "Track Stand": "ASC",
            "Gold Pan": "ASC",
            "Hand Steel": "DESC",
            "Jackleg": "DESC",
            "Survey": "ASC",
        }

        dq_time = {
            "Mucking": utils.DQ_TIME,
            "Swede Saw": utils.DQ_TIME,
            "Track Stand": utils.DQ_TIME,
            "Gold Pan": utils.DQ_TIME,
            "Hand Steel": utils.DQ_MIN_LENGTH,
            "Jackleg": utils.DQ_MIN_LENGTH,
            "Survey": utils.DQ_MAX_LENGTH,
        }
        self.logger.info("Scoring Competition")
        loop_query = QtSql.QSqlQuery(self.db)
        inner_query = QtSql.QSqlQuery(self.db)

        self.logger.debug("Computing Initial Ranks")
        for div in ["A", "C", "M", "W"]:
            for event in event_sorting:
                order = event_sorting[event]
                loop_query.exec(
                    f'SELECT id, School, Name, "{event}" from teams WHERE Division = "{div}" ORDER BY "{event}" {order};'
                )
                i = 1  # Ranking handled at DB level 'i' for placing
                while loop_query.next():
                    t_id = loop_query.value(0)
                    s_name = loop_query.value(1)
                    t_name = loop_query.value(2)
                    e_val = loop_query.value(3)

                    # DQ's Default to 0 for further processing
                    set_val = i if e_val != dq_time[event] else 0
                    inner_query.exec(f"SELECT id FROM ranks WHERE id = {t_id};")

                    # Insert if no existing record else update
                    if not inner_query.next():
                        sql = f'INSERT INTO ranks (id, School, Name, Division, "{event}") VALUES ({t_id}, "{s_name}", "{t_name}", "{div}", {set_val});'
                    else:
                        sql = (
                            f'UPDATE ranks SET "{event}" = {set_val} WHERE id = {t_id};'
                        )
                    temp = inner_query.exec(sql)
                    i += 1

        self.logger.debug("Computing DQ Scores and Updating Ranks")
        for div in ["A", "C", "M", "W"]:
            for event in event_sorting:
                total = 0
                dq = 0
                # How many teams total in the division
                loop_query.exec(
                    f'SELECT COUNT("{event}") FROM ranks where Division="{div}";'
                )
                if loop_query.next():
                    total = loop_query.value(0)
                # How many teams disqualified in the division
                loop_query.exec(
                    f'SELECT COUNT("{event}") FROM ranks WHERE Division="{div}" and "{event}"=0;'
                )
                if loop_query.next():
                    dq = loop_query.value(0)

                # if either of these are empty then there is either no teams or no dq's
                if total and dq:
                    dq_score = total - dq + 1
                    inner_query.exec(
                        f'UPDATE ranks SET "{event}" = {dq_score} where Division="{div}" and "{event}"=0;'
                    )

        # Handle Ties
        # TODO:
        #  Check for ties,
        #  For each tie set both teams to the lowest for each event
        #  Update Ties Won
        #  Update final Scoring to account for ties won

        self.logger.debug("Computing Total Scores")
        loop_query.exec("SELECT * from ranks;")
        while loop_query.next():
            s = 0
            t_id = loop_query.value(0)
            for i in range(4, 11):
                s += loop_query.value(i)
            inner_query.exec(f"UPDATE ranks SET Sum = {s} WHERE id = {t_id};")

        # Cleanup Query Objects just in case
        loop_query.clear()
        inner_query.clear()

        # Change Radio Button to Rank view
        self.rb_rank.setChecked(True)

    # Model/View Functions
    def db_setup(self) -> None:
        self.logger.info("Initializing Database")
        self.db = QtSql.QSqlDatabase.addDatabase("QSQLITE")
        db_filepath = self.settings.value("db/path", "")

        db_file = QtCore.QFileInfo(db_filepath)
        if db_file.exists() and db_file.isFile():
            self.db.setDatabaseName(db_filepath)
            self.db.open()
            # Setup Teams Table
            if "teams" not in self.db.tables():
                query = QtSql.QSqlQuery()
                query.exec_(utils.TEAMS_SQL)
                query.clear()

            # Setup Ranks table if needed
            if "ranks" not in self.db.tables():
                query = QtSql.QSqlQuery()
                query.exec_(utils.RANKS_SQL)
                query.clear()

            # Setup Ties table if needed
            if "ties" not in self.db.tables():
                query = QtSql.QSqlQuery()
                query.exec_(utils.TIES_SQL)
                query.clear()

        else:
            diag = dialogs.RetryDialog(
                "Select Database",
                "Unable to open database\nCheck if file is valid or try a different file",
                "Open",
            )
            diag.retry.connect(self.db_setup)
            diag.accepted.connect(self.db_change)
            diag.rejected.connect(self.close)
            diag.exec_()
            self.conn_status.setText("Connected [local]")

    def db_change(self) -> None:
        self.logger.warning("Unable to locate database, requesting updated location")
        db_filename = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Database File", str(self.data_dir), "Database File (*.db)"
        )[0]
        self.settings.setValue("db/path", db_filename)
        self.db_setup()

    def model_setup(self) -> None:
        self.logger.info("Initializing Models")
        data_model = QtSql.QSqlTableModel(self)
        data_model.setTable("teams")
        data_model.setEditStrategy(QtSql.QSqlTableModel.OnFieldChange)
        data_model.select()
        self.data_model = data_model
        rank_model = QtSql.QSqlTableModel(self)
        rank_model.setTable("ranks")
        rank_model.setEditStrategy(QtSql.QSqlTableModel.OnManualSubmit)
        rank_model.select()
        self.rank_model = rank_model

    def model_filter(self, text):
        self.logger.debug(f"Model Filter Set to {text}")
        if text == "All":
            self.data_model.setFilter("")
            self.rank_model.setFilter("")
        else:
            # Filter based on the first letter of the combobox value, the CHAR in the db
            self.data_model.setFilter(f"division='{text[0]}'")
            self.rank_model.setFilter(f"division='{text[0]}'")

    def model_change(self):
        display_mode = self.settings.value("app/display")
        if display_mode == "rank":
            self.team_table.setModel(self.rank_model)
            self.team_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.rank_model.select()
            self.team_table.resizeColumnsToContents()
        else:
            self.team_table.setModel(self.data_model)
            self.team_table.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
            self.team_table.resizeColumnsToContents()

    def view_setup(self) -> None:
        self.logger.info("Initializing Competition View")
        # Update Title
        title = self.findChild(QtWidgets.QLabel, "l_teams_header")
        title.setText(f"{self.settings.value('comp/year')} Team Scores")

        # Table Options
        # TODO: Setup table based on which model is in use
        self.team_table.setModel(self.data_model)
        self.team_table.setColumnHidden(0, True)
        self.table_min_size()
        self.team_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self.team_table.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeToContents
        )
        self.team_table.horizontalHeader().setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeToContents
        )

        # Column Options
        # Note diff delegate instance for each column as recommended by docs
        # Delegate ref must be kept to prevent GC
        self.logger.info("Initializing Tableview Delegates")
        self.local_delegates = list()

        # Setup Division Delegate
        self.local_delegates.append(delegates.DivisionDelegate(self))
        self.team_table.setItemDelegateForColumn(3, self.local_delegates[-1])

        # Setup Timed Event Delegates
        for col in range(4, 8):
            self.local_delegates.append(delegates.TimeEditDelegate(self))
            self.team_table.setItemDelegateForColumn(col, self.local_delegates[-1])

        # Setup Length Event Delegates
        self.local_delegates.append(delegates.HandsteelDelegate(self))
        self.team_table.setItemDelegateForColumn(8, self.local_delegates[-1])
        self.local_delegates.append(delegates.JacklegDelegate(self))
        self.team_table.setItemDelegateForColumn(9, self.local_delegates[-1])
        self.local_delegates.append(delegates.SurveyDelegate(self))
        self.team_table.setItemDelegateForColumn(10, self.local_delegates[-1])

        self.team_table.resizeColumnsToContents()

        # Needs to be setup here as model is not setup in init
        self.rb_imperial.toggled.connect(self.data_model.select)
        self.rb_metric.toggled.connect(self.data_model.select)
        self.rb_rank.toggled.connect(self.rank_model.select)
        self.rb_imperial.toggled.connect(self.model_change)
        self.rb_metric.toggled.connect(self.model_change)
        self.rb_rank.toggled.connect(self.model_change)
        self.ties_window = ties.TieWindow(self, self.db)
        action_view_ties = self.findChild(QtWidgets.QAction, "a_view_ties")
        action_view_ties.triggered.connect(self.ties_window.show)

    # Team Management Functions
    def team_create(self):
        self.logger.info("Creating New Team")
        diag = dialogs.NewTeam()
        if diag.exec_():
            self.logger.debug("Created New Team, Saving and Refreshing Screen")
            team = self.data_model.record()
            team.setValue("Name", diag.name.text())
            team.setValue("Division", diag.division.currentText()[0])

            # School/Sponsor optional (NULL only in DB not empty strings)
            if diag.school.text():
                team.setValue("School", diag.school.text())

            if self.data_model.insertRecord(-1, team):
                self.logger.debug("Successfully inserted team")
                self.data_model.select()
            else:
                self.logger.debug("Failed to insert team")

    def team_delete(self):
        index = self.team_table.selectedIndexes()

        # Ensure there is a selection
        # Maybe disable in context menu if there is no selection?
        if index:
            index = index[0]
        else:
            utils.alert("No Team Selected", "Please Select a team to delete", "warn")
            return

        backup = []
        for i in range(self.data_model.columnCount()):
            value = self.data_model.data(self.data_model.index(index.row(), i))

            # Replace empty strings with none to better represent the database state
            if value == "":
                value = None
            backup.append(value)

        confirmation = utils.confirm(
            "Delete Team", f"Do you want to delete the following team?\n{backup[2]}"
        )
        if confirmation == QtWidgets.QMessageBox.Yes:
            self.logger.info("Deleting Team")
            self.logger.txn(f"[Deleted] Team Data - {backup}")
            self.data_model.deleteRowFromTable(index.row())
            self.data_model.select()
        else:
            self.logger.debug("Canceled team delete request")

    def settings_modify(self):
        self.logger.info("Open Setting Dialog")
        diag = dialogs.SettingsDialog(self)
        if diag.exec_():
            self.logger.debug("Saving updated settings")
            updates = diag.update_settings()

            for key in updates:
                if key == "units/time":
                    self.settings.setValue(key, updates[key])
                else:
                    self.settings.setValue(key, utils.UNIT_SHORTHAND[updates[key]])

    # Restart program typically to reset DB connections by restarting the application
    def restart_app(self):
        self.logger.warning("Why Though?")
        python = sys.executable
        os.execl(python, python, *sys.argv)

    # keep the main widget from getting smaller than the tableview
    def table_min_size(self):
        self.centralWidget().setMinimumWidth(
            self.team_table.horizontalHeader().length()
            + self.team_table.verticalHeader().width()
            + self.team_table.verticalScrollBar().width()
        )

    def units_update(self):
        # TODO: Handle Dual data model
        caller = self.sender()
        self.settings.setValue("app/display", caller.text().lower())
        for col in range(3, 11):
            self.team_table.horizontalHeader().setSectionResizeMode(
                col, QtWidgets.QHeaderView.ResizeToContents
            )
        self.team_table.resizeColumnsToContents()
        for col in range(3, 11):
            self.team_table.horizontalHeader().setSectionResizeMode(
                col, QtWidgets.QHeaderView.Stretch
            )

    # Application Wide Event Filter
    def eventFilter(self, source: QtWidgets.QWidget, event: QtCore.QEvent):
        if type(source) == QtWidgets.QTableView:
            self.excel_like_enter_filter(source, event)
        return super(GUI, self).eventFilter(source, event)

    # TableView Specific event filtering
    @staticmethod
    def excel_like_enter_filter(source: QtWidgets.QTableView, event: QtCore.QEvent):
        if event.type() == event.KeyPress:
            if event.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
                if int(source.editTriggers()) > int(
                    QtWidgets.QAbstractItemView.NoEditTriggers
                ):
                    next_row = source.currentIndex().row() + 1
                    if next_row + 1 > source.model().rowCount():
                        next_row -= 1
                    if source.state() == source.EditingState:
                        next_index = source.model().index(
                            next_row, source.currentIndex().column()
                        )
                        source.setCurrentIndex(next_index)
                    else:
                        source.edit(source.currentIndex())


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = GUI()
    app.exec_()
