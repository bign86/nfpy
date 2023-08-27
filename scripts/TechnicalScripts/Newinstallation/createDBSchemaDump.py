#
# Create Database Schema Dump script
# Creates the schema.sql file to recreate the database
#

import os

from nfpy import NFPY_ROOT_DIR
import nfpy.DB as DB
from nfpy.Tools import Utilities as Ut

__version__ = '0.2'
_TITLE_ = "<<< Database schema dump creation script >>>"


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
    Ut.print_header(_TITLE_, end='\n\n')

    outf = open(
        os.path.join(NFPY_ROOT_DIR, 'schema.sql'),
        mode='w'
    )
    outf.write(get_db_data())
    outf.close()

    Ut.print_ok('All done!')
