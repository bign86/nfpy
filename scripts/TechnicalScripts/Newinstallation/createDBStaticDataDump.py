#
# Create Database Static Data Dump script
# Creates the files with the database static data
#

import json
import os
from pathlib import Path
import pickle

from nfpy import NFPY_ROOT_DIR
import nfpy.DB as DB

__version__ = '0.2'
_TITLE_ = "<<< Database static data dump creation script >>>"

PKL_FILE = 'db_static_data.p'
JSN_FILE = 'db_static_data.json'

TBL_LIST = ['DecDatatype', 'SystemInfo', 'MapFinancials']


def get_db_data():
    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    return {
        t: db.execute(qb.selectall(t)).fetchall()
        for t in TBL_LIST
    }


def to_pickle(dt):
    try:
        data_file = Path(os.path.join(NFPY_ROOT_DIR, PKL_FILE))
        pickle.dump(dt, data_file.open('wb'))
    except Exception as ex:
        raise ex


def to_json(dt):
    try:
        data_file = Path(os.path.join(NFPY_ROOT_DIR, JSN_FILE))
        json.dump(dt, data_file.open('w'))
    except Exception as ex:
        raise ex


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    data = get_db_data()
    # print(data)
    to_pickle(data)
    to_json(data)

    print("All done!")
