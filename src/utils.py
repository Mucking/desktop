import fractions
import math
import shutil
import sqlite3
from PyQt5 import QtWidgets, QtCore


TEAMS_SQL = """create table teams (
    id integer 
    constraint teams_pk 
        primary key AUTOINCREMENT, 
    School varchar(120), 
    Name varchar(80)  not null, 
    Division varchar(1) not null, 
    Mucking float,
    "Swede Saw" float,
    "Track Stand" float, 
    "Gold Pan" float, 
    "Hand Steel"  float, 
    Jackleg float, 
    Survey double
    );"""

RANKS_SQL = """create table ranks (
    id INTEGER 
    constraint ranks_pk 
        primary key constraint 
    ranks_teams_id_fk 
        references teams 
        on delete cascade,
    School varchar(120), 
    Name varchar(80) not null,  
    Division varchar(1), 
    Mucking int, 
    "Swede Saw" int, 
    "Track Stand" int, 
    "Gold Pan" int, 
    "Hand Steel" int, 
    Jackleg int, 
    Survey int, 
    Sum int, 
    "Ties Won" int
    );"""

TIES_SQL = """create table ties (
    id integer not null
        constraint ties_pk
            primary key autoincrement,
    team_1_id int not null
        constraint ties_teams_id_fk
            references teams
                on delete cascade,
    team_2_id int not null
        constraint ties_teams_id_fk_2
            references teams
                on delete cascade,
    event text not null,
    winner int not null
        constraint ties_teams_id_fk_3
            references teams
                on delete cascade
);"""

SPACE_INDICATOR = "˽"
DQ_TIME = 180 * 60 * 60
DQ_MIN_LENGTH = 0
DQ_MAX_LENGTH = 99999999.0
TXN_LEVEL_NUM = 25

UNIT_FACTORS = {
    "mm": 10,
    "cm": 1,
    "km": 1 / 100 / 1000,
    "m": 1 / 100,
    "in": 1 / 2.54,
    "ft": 1 / 2.54 / 12,
    "mi": 1 / 2.54 / 12 / 5280,
}

DIVISION_LEXICON = {
    "M": "Men's",
    "W": "Women's",
    "C": "Co-Ed",
    "A": "Alumni",
    "Alumni": "A",
    "Co-Ed": "C",
    "Women's": "W",
    "Men's": "M",
}

UNIT_SHORTHAND = {
    "fractional inches": "fin",
    "inches": "in",
    "feet": "ft",
    "miles": "mi",
    "millimeters": "mm",
    "centimeters": "cm",
    "meters": "m",
    "kilometers": "km",
    "dynamic": "dynamic",
}

events = [
    "",
    "Mucking",
    "Swede Saw",
    "Track Stand",
    "Gold Pan",
    "Hand Steel",
    "Jackleg",
    "Survey",
]


def alert(window_title, text, alert="info"):
    alert_type = {
        "info": QtWidgets.QMessageBox.Information,
        "question": QtWidgets.QMessageBox.Question,
        "warn": QtWidgets.QMessageBox.Warning,
        "crit": QtWidgets.QMessageBox.Critical,
    }

    if alert not in alert_type:
        raise KeyError(f"Invalid alert type. [{'/'.join(alert_type)}]")

    msg = QtWidgets.QMessageBox()
    msg.setIcon(alert_type[alert])
    msg.setText(text)
    msg.setWindowTitle(window_title)
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)

    return msg.exec_()


def confirm(title, text):
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Question)
    msg.setText(text)
    msg.setWindowTitle(title)
    msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

    return msg.exec_()


def db_copy(base, target):
    connection = sqlite3.connect(base)
    cursor = connection.cursor()

    # Lock database before making a backup
    cursor.execute("begin immediate")

    # Make new backup file
    shutil.copyfile(base, target)

    # Unlock database
    connection.rollback()
    cursor.close()
    connection.close()


def get_reasonable_unit(value, is_metric):
    # This is gross
    # TODO FRACTIONAL INCH BS
    power = math.log10(value)
    if is_metric:
        if power <= 0.0:
            units = "mm"
        elif 0.0 < power < 2.0:
            units = "cm"
        elif power >= 5.0:
            units = "km"
        else:
            units = "m"
    else:
        # Convert cm -> in
        value /= 2.54

        # Check if reasonable
        if value < 12:
            units = "in"
        else:
            # Convert in -> ft
            value /= 12
            if value < 5280:
                units = "ft"
            else:
                units = "mi"

    return units


def txn(self, message, *args, **kwargs):
    if self.isEnabledFor(TXN_LEVEL_NUM):
        self._log(TXN_LEVEL_NUM, message, args, **kwargs)
