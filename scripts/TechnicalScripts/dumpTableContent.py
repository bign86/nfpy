#
# Dump Table script
# Dump a database table on a csv.
#

import csv
from os.path import join

from nfpy.DB import (get_db_glob, get_qb_glob)
from nfpy.Handlers.Calendar import now
from nfpy.Handlers.Configuration import get_conf_glob
from nfpy.Handlers.Inputs import InputHandler

__version__ = '0.2'
_TITLE_ = "<<< Dump Table script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = get_db_glob()
    qb = get_qb_glob()
    conf = get_conf_glob()
    inh = InputHandler()

    # get the table to dump
    table = inh.input("Table to dump: ", idesc='str')
    if not qb.exists_table(table):
        raise ValueError("Table {} does not exists in the database".format(table))

    q = "select * from {}".format(table)
    l = db.execute(q).fetchall()

    fname = table + '_' + now(fmt='%Y%m%d%H%M') + '.csv'
    path = join(conf.backup_dir, fname)

    columns = list(qb.get_fields(table))
    with open(path, 'w') as f:
        out = csv.writer(f, lineterminator='\n')
        out.writerow(columns)
        out.writerows(l)

    print("All done!")
