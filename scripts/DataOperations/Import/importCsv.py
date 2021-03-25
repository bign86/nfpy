#
# Import Csv script
# Insert new data into a table using a csv input file as data source.
# One line header.
#

import csv
import os
from operator import itemgetter

from nfpy.Tools import get_conf_glob
import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.2'
_TITLE_ = "<<< Import Csv script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    conf = get_conf_glob()
    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # get and validate inputs
    dsrc = conf.backup_dir
    msg = "Give me filename to upload (must be present in the data source folder {}): ".format(dsrc)
    name = inh.input(msg, idesc='str')
    src_file = os.path.join(dsrc, name)
    if not os.path.isfile(src_file):
        raise ValueError('Supplied file does not exist! Please give a valid one.')

    table = inh.input("Give me a table to update: ", idesc='str')
    t_exists = qb.exists_table(table)
    if not t_exists:
        raise ValueError('Supplied table name does not exist! Please give a valid one.')

    # read data
    with open(src_file, 'r') as f:
        reader = csv.reader(f, dialect='excel')
        _ = next(reader)
        data = list(reader)
    print("Insert/Update {} records in table {}".format(len(data), table))

    # set up data
    keys = [k for k in qb.get_keys(table)]
    k_pos = [n for n, v in enumerate(keys) if qb.is_primary(table, v)]
    get_keys = itemgetter(*k_pos)
    if len(keys) == 1:
        ddel = [(get_keys(d),) for d in data]
    else:
        ddel = [get_keys(d) for d in data]

    # update database
    q_del = qb.delete(table, fields=keys)
    db.executemany(q_del, ddel)

    q_ins = qb.insert(table)
    db.executemany(q_ins, data, commit=True)

    print("All done!")
