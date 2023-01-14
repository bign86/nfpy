#
# Dump Table script
# Dump a database table on a csv.
#

import csv
from os.path import join

from nfpy.Calendar import now
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import get_conf_glob

__version__ = '0.2'
_TITLE_ = "<<< Dump Table script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    conf = get_conf_glob()
    inh = IO.InputHandler()

    # get the table to dump
    table = inh.input("Table to dump: ", idesc='str')
    while not qb.exists_table(table):
        msg = "The table does not exists in the database. Please give another: "
        table = inh.input(msg)

    q = f"select * from {table}"
    l = db.execute(q).fetchall()

    fname = f'{table}_{now(mode="str", fmt="%Y%m%d%H%M")}.csv'
    path = join(conf.backup_dir, fname)

    columns = list(qb.get_fields(table))
    with open(path, 'w') as f:
        out = csv.writer(f, lineterminator='\n')
        out.writerow(columns)
        out.writerows(l)

    print("All done!")
