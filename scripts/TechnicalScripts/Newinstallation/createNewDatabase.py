#
# Create Database script
# Creates a new database from scratch
#

import json
import os
import pickle
from pathlib import Path
from typing import Optional

from nfpy import NFPY_ROOT_DIR
import nfpy.DB as DB
from nfpy.DB.DB import DBHandler
from nfpy.Tools import get_conf_glob

__version__ = '0.7'
_TITLE_ = "<<< Database creation script >>>"

Q_CCY = "insert into Currency (name, symbol, country) values (?, ?, ?);"
Q_DEC = "insert into DecDatatype (datatype, encoding) values (?, ?);"
Q_FMAP = "insert into MapFinancials (short_name, category, long_name) values (?, ?, ?);"
Q_PROV = "insert into Providers (provider, page, item) values (?, ?, ?);"
Q_SYS = "insert into SystemInfo (field, value) values (?, ?);"

PKL_FILE = 'db_static_data.p'
JSN_FILE = 'db_static_data.json'

TABLES_TO_CREATE = [
    (
        'Alerts',
        """create table Alerts (uid TEXT, date DATETIME, cond TEXT, value REAL,
            triggered BOOL, date_triggered DATETIME, date_checked DATETIME,
            primary key (uid, date, cond, value)) without rowid;"""
    ),
    (
        'Bond',
        """create table Bond (uid TEXT, isin TEXT NOT NULL, issuer TEXT NOT NULL,
            currency TEXT NOT NULL, country TEXT, description TEXT,
            asset_class TEXT, inception_date DATETIME, maturity DATETIME NOT NULL,
            rate_type TEXT NOT NULL, coupon REAL, c_per_year INTEGER,
            day_count INTEGER, callable BOOL NOT NULL,
            primary key (uid)) without rowid;"""
    ),
    (
        'BondTS',
        """create table BondTS (uid TEXT, dtype INTEGER NOT NULL,
            date DATETIME NOT NULL, value REAL NOT NULL,
            primary key (uid,dtype,date), foreign key (uid)
            references Bond(uid)) without rowid;"""
    ),
    (
        'Company',
        """create table Company (uid TEXT, description TEXT, name TEXT NOT NULL,
            sector TEXT, industry TEXT, currency TEXT, country TEXT,
            primary key (uid)) without rowid;"""
    ),
    (
        'CompanyFundamentals',
        """create table CompanyFundamentals (uid TEXT, code TEXT, date DATE,
            freq TEXT, value REAL, primary key (uid, code, date, freq),
            foreign key (uid) references Company(uid)) without rowid;"""
    ),
    (
        'Currency',
        """create table Currency (name TEXT, symbol TEXT, country TEXT,
            primary key (symbol)) without rowid;"""

    ),
    (
        'Curve',
        """create table Curve (uid TEXT, description TEXT, currency TEXT,
            primary key (uid)) without rowid;"""
    ),
    (
        'CurveConstituents',
        """create table CurveConstituents (uid TEXT, bucket TEXT NOT NULL,
            primary key (uid, bucket), foreign key (uid) references Rate(uid),
            foreign key (bucket) references Curve(uid)) without rowid;"""
    ),
    (
        'DecDatatype',
        """create table DecDatatype (datatype TEXT, encoding INTEGER NOT NULL,
            primary key (datatype)) without rowid;"""
    ),
    (
        'Downloads',
        """create table Downloads (provider TEXT, page TEXT, ticker TEXT NOT NULL,
            currency TEXT, active BOOL NOT NULL, update_frequency INTEGER NOT NULL,
            last_update DATE, primary key (provider, page, ticker)) without rowid;"""
    ),
    (
        'ECBSeries',
        """create table ECBSeries (ticker TEXT, date DATETIME, value REAL,
            primary key (ticker, date)) without rowid;"""
    ),
    (
        'Equity',
        """create table Equity (uid TEXT, ticker TEXT NOT NULL,
            isin TEXT NOT NULL, description TEXT, country TEXT, market TEXT,
            currency TEXT NOT NULL, company TEXT, preferred BOOL,
            [index] TEXT, primary key (uid), foreign key (company)
            references Company(uid)) without rowid;"""
    ),
    (
        'EquityTS',
        """create table EquityTS (uid TEXT, dtype INTEGER NOT NULL,
            date DATETIME NOT NULL, value REAL NOT NULL,
            primary key (uid, dtype, date),
            foreign key (uid) references Equity(uid)) without rowid;"""
    ),
    (
        'Fx',
        """create table Fx (uid TEXT, description TEXT, price_country TEXT,
            base_country TEXT, price_ccy TEXT NOT NULL, base_ccy TEXT NOT NULL,
            primary key (uid)) without rowid;"""
    ),
    (
        'FxTS',
        """create table FxTS (uid TEXT, dtype INTEGER NOT NULL,
            date DATETIME NOT NULL, value REAL NOT NULL,
            primary key (uid,dtype,date), foreign key (uid)
            references Currency(uid)) without rowid;"""
    ),
    (
        'IBFinancials',
        """create table IBFinancials (ticker TEXT, freq TEXT, date DATE,
            currency TEXT, statement TEXT, code TEXT, value REAL,
            primary key (ticker, freq, date, statement, code)) without rowid;"""
    ),
    (
        'Imports',
        """create table Imports (uid TEXT, ticker TEXT, provider TEXT,
            item TEXT, active BOOL NOT NULL,
            primary key (uid, ticker, provider, item)) without rowid;"""
    ),
    (
        'Indices',
        """create table Indices (uid TEXT, ticker TEXT NOT NULL, area TEXT,
            currency TEXT NOT NULL, description TEXT, ac TEXT,
            primary key (uid)) without rowid;"""
    ),
    (
        'IndexTS',
        """create table IndexTS (uid TEXT, dtype INTEGER NOT NULL,
            date DATETIME NOT NULL, value REAL NOT NULL,
            primary key (uid,dtype,date), foreign key (uid)
            references Indices(uid)) without rowid;"""
    ),
    (
        'InvestingFinancials',
        """create table InvestingFinancials (ticker TEXT, freq TEXT, date DATETIME,
            currency TEXT, statement TEXT, code TEXT, value REAL,
            primary key (ticker, freq, date, statement, code)) without rowid;"""
    ),
    (
        'InvestingPrices',
        """create table InvestingPrices (ticker TEXT, date DATETIME, price REAL,
            open REAL, high REAL, low REAL, volume INTEGER,
            primary key (ticker, date)) without rowid;"""
    ),
    (
        'MapFinancials',
        """create table MapFinancials (short_name TEXT, category TEXT,
            long_name TEXT, primary key (short_name)) without rowid;"""
    ),
    (
        'Portfolio',
        """create table Portfolio (uid TEXT, name TEXT, description TEXT,
            currency TEXT NOT NULL, inception_date DATETIME NOT NULL,
            benchmark TEXT, primary key (uid)) without rowid;"""
    ),
    (
        'PortfolioPositions',
        """create table PortfolioPositions (ptf_uid TEXT, date DATETIME,
            pos_uid TEXT, type TEXT NOT NULL, currency TEXT NOT NULL,
            quantity REAL NOT NULL, alp REAL NOT NULL,
            primary key (ptf_uid, date, pos_uid), foreign key (ptf_uid)
            references Portfolio(uid)) without rowid;"""
    ),
    (
        'Providers',
        """create table Providers (provider TEXT, page TEXT, item TEXT,
            primary key (provider, page, item)) without rowid;"""
    ),
    (
        'Rate',
        """create table Rate (uid TEXT, description TEXT, currency TEXT,
            tenor REAL, is_rf BOOL NOT NULL, primary key (uid)) without rowid;"""
    ),
    (
        'RateTS',
        """create table RateTS (uid TEXT, dtype INTEGER NOT NULL,
            date DATETIME NOT NULL, value REAL NOT NULL,
            primary key (uid, dtype, date), foreign key (uid)
            references Rate(uid)) without rowid;"""
    ),
    (
        'Reports',
        """create table Reports (id TEXT, title TEXT, description TEXT,
            report TEXT, template TEXT, uids PARAMETERS, parameters PARAMETERS,
            active BOOL, primary key (id)) without rowid;"""
    ),
    (
        'SystemInfo',
        """create table SystemInfo (field TEXT, value REAL NOT NULL,
            primary key (field)) without rowid;"""
    ),
    (
        'Trades',
        """create table Trades (ptf_uid TEXT, date DATETIME, pos_uid TEXT,
            buy_sell BOOL NOT NULL, currency TEXT NOT NULL,
            quantity REAL NOT NULL, price REAL NOT NULL, costs REAL, market TEXT,
            primary key (ptf_uid, date, pos_uid), foreign key (ptf_uid)
            references Portfolio(uid)) without rowid;"""
    ),
    (
        'YahooEvents',
        """create table YahooEvents (ticker TEXT, date DATETIME, dtype TEXT,
            value REAL, primary key (ticker, date, dtype)) without rowid;"""
    ),
    (
        'YahooFinancials',
        """create table YahooFinancials (ticker TEXT, freq TEXT, date DATETIME,
            currency TEXT, statement TEXT, code TEXT, value REAL,
            primary key (ticker, freq, date, statement, code)) without rowid;"""
    ),
    (
        'YahooPrices',
        """create table YahooPrices (ticker TEXT, date DATETIME, open REAL,
            high REAL, low REAL, close REAL, adj_close REAL, volume INTEGER,
            primary key (ticker, date)) without rowid;"""
    ),
]

VIEWS_TO_CREATE = [
    (
        'Assets',
        """CREATE VIEW Assets AS SELECT uid, type, description, currency FROM
            (
                SELECT uid, 'Bond' as type, description, currency FROM Bond union
                SELECT uid, 'Company' as type, description, currency FROM Company union
                SELECT uid, 'Curve' as type, description, currency FROM Curve union
                SELECT uid, 'Equity' as type, description, currency FROM Equity union
                SELECT uid, 'Fx' as type, description, NULL FROM Fx union
                SELECT uid, 'Indices' as type, description, currency FROM Indices union
                SELECT uid, 'Portfolio' as type, description, NULL FROM Portfolio union
                SELECT uid, 'Rate' as type, description, NULL FROM Rate
            ) AS src;"""
    ),
]


def get_db_handler(db_path: Optional[str] = None) -> DBHandler:
    if db_path is None:
        db_path = get_conf_glob().db_dir
        if not os.path.isfile(db_path):
            raise ValueError('Cannot create database.')

    # database creation
    print('Creating the new database...')
    db_ = DB.get_db_glob(db_path)

    if not db_:
        msg = 'I cannot connect to the database... Sorry, I must stop here :('
        raise RuntimeError(msg)
    print(f"New database created in {db_.db_path}")

    return db_


def create_database(db_: DBHandler) -> None:
    # create tables
    print('Creating tables...')
    for t, q in TABLES_TO_CREATE:
        print(f"Create table {t}... ", end="")
        db_.execute(q)
        print("done!")

    print("--- Tables created! ---")

    # create views
    print('Creating views...')
    for t, q in VIEWS_TO_CREATE:
        print(f"Create view {t}... ", end="")
        db_.execute(q)
        print("done!")

    print("--- Views created! ---")


def populate_database(db_: DBHandler) -> None:
    """ Populate database """

    try:
        data_file = Path(os.path.join(NFPY_ROOT_DIR, PKL_FILE))
        data_dict = pickle.load(data_file.open('rb'))
    except RuntimeError:
        try:
            data_file = Path(os.path.join(NFPY_ROOT_DIR, JSN_FILE))
            data_dict = json.load(data_file.open('rb'))
        except RuntimeError as ex2:
            raise ex2

    # data_file.close()

    print("Adding initial data")
    db_.executemany(Q_SYS, data_dict['DATA_SYS'])
    db_.executemany(Q_FMAP, data_dict['DATA_FINMAP'])
    db_.executemany(Q_DEC, data_dict['DATA_DEC'], commit=True)
    print("--- Setup completed! ---")


def new_database(db_path: Optional[str] = None) -> None:
    db = get_db_handler(db_path)
    create_database(db)
    populate_database(db)


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    new_database(
        input('Give a path and name for the new database: ')
    )

    print('All done!')
