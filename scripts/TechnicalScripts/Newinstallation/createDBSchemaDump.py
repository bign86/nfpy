#
# Create Database Schema Dump script
# Creates the schema.sql file to recreate the database
#

import os

from nfpy import NFPY_ROOT_DIR
import nfpy.DB as DB

__version__ = '0.1'
_TITLE_ = "<<< Database schema dump creation script >>>"

PKL_FILE = 'db_static_data.p'
JSN_FILE = 'db_static_data.json'

TBL_LIST = ('Currency', 'DecDatatype', 'MapFinancials', 'Providers', 'SystemInfo')


def get_db_data() -> str:
    db = DB.get_db_glob()
    q = 'select sql from sqlite_schema where name not in ("sqlite_stat1");'
    schema = db.execute(q).fetchall()

    result = []
    while schema:
        create = schema.pop(0)[0]
        if create[-1] != ';':
            create += ';'
        result.append(create)
    return '\n'.join(result)


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    outf = open(
        os.path.join(NFPY_ROOT_DIR, 'schema.sql'),
        mode='w'
    )
    outf.write(get_db_data())
    outf.close()

    print("All done!")
