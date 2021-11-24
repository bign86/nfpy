#
# Clean Database
# Script to filter data from a table and delete them.
#

from enum import Enum
from tabulate import tabulate

import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.1'
_TITLE_ = "<<< Delete data script >>>"


class States(Enum):
    UNSET = 0
    PRINT = 1
    QUIT = 2


def _get_filters(_c, _d):
    field = inh.input('Column to filter for: ')
    while field not in fields:
        field = inh.input('Field doesn\'t exist. Try again: ')
    _c.append(field)
    search = inh.input('Search for: ')
    _d.append(search)


def _get_results(_c, _d) -> []:
    return db.execute(
        qb.select(table, keys=_c),
        _d
    ).fetchall()


def _do_delete(_r):
    db.executemany(
        qb.delete(table, fields),
        _r,
        commit=True
    )


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    table = inh.input('Give a table to clean: ')
    while not qb.exists_table(table):
        table = inh.input('Table not found. Try again: ')

    keys = tuple(qb.get_keys(table))
    fields = qb.get_fields(table)
    msg = 'The following fields exists (* for keys)\n'
    for f in fields:
        ind = ' * ' if f in keys else '   '
        msg += ind + f + '\n'
    print(msg)

    state = States.UNSET
    columns, data = [], []
    result = None
    in_msg = 'Press "f" to filter, "d" to delete, "q" to quit: '
    while state != States.QUIT:
        if state == States.PRINT:
            print(tabulate(result, headers=fields))
            state = States.UNSET

        do = inh.input(in_msg)
        if do == 'f':
            _get_filters(columns, data)
            result = _get_results(columns, data)
            state = States.PRINT
        elif do == 'q':
            state = States.QUIT
        elif do == 'd':
            if inh.input('Sure (Default False)?: ', idesc='bool', default=False):
                _do_delete(result)
                state = States.QUIT
            else:
                state = States.UNSET

    print('All done!')
