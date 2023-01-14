#
# Create Database script
# Creates a new database from scratch
#

import json
import os
import pickle
from pathlib import Path
import sqlite3
from typing import Optional

from nfpy import NFPY_ROOT_DIR
import nfpy.DB as DB
from nfpy.Tools import get_conf_glob

__version__ = '0.9'
_TITLE_ = "<<< Database creation script >>>"

Q_CCY = "insert into Currency (name, symbol, country, pegged, factor) values (?, ?, ?, ?, ?);"
Q_DEC = "insert into DecDatatype (datatype, encoding) values (?, ?);"
Q_FMAP = "insert into MapFinancials (short_name, category, long_name) values (?, ?, ?);"
Q_PROV = "insert into Providers (provider, page, item) values (?, ?, ?);"
Q_SYS = "insert into SystemInfo (field, value, date) values (?, ?, ?);"

PKL_FILE = 'db_static_data.p'
JSN_FILE = 'db_static_data.json'


def get_db_handler(db_path: Optional[str] = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = get_conf_glob().db_dir
        if not os.path.isfile(db_path):
            raise ValueError('Cannot create database.')

    # database creation
    print('Creating the new database...')
    db_conn = DB.get_db_connection(db_path)

    if not db_conn:
        msg = 'I cannot connect to the database... Sorry, I must stop here :('
        raise RuntimeError(msg)
    print(f"New database created in {db_path}")

    return db_conn


def create_schema(conn_: sqlite3.Connection) -> None:
    print('Creating tables...')

    outf = open(
        os.path.join(NFPY_ROOT_DIR, 'schema.sql'),
        mode='r'
    )
    conn_.cursor().executescript(outf.read())
    conn_.commit()
    outf.close()

    print("--- Tables created! ---")


def populate_database(conn_: sqlite3.Connection) -> None:
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

    print("Adding initial data")
    conn_.cursor().executemany(Q_CCY, data_dict['Currency'])
    conn_.cursor().executemany(Q_DEC, data_dict['DecDatatype'])
    conn_.cursor().executemany(Q_FMAP, data_dict['MapFinancials'])
    conn_.cursor().executemany(Q_PROV, data_dict['Providers'])

    # Adding SystemInfo data
    sysinfo_data = [
        ('DBVersion', DB.MIN_DB_VERSION, None),
        ('lastDownload', None, None),
        ('lastImport', None, None)
    ]
    conn_.cursor().executemany(Q_SYS, sysinfo_data)
    conn_.commit()
    print("--- Setup completed! ---")


def new_database(db_path: Optional[str] = None) -> None:
    conn = get_db_handler(db_path)
    create_schema(conn)
    populate_database(conn)


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    new_database(
        input('Give a path and name for the new database: ')
    )

    print('All done!')
