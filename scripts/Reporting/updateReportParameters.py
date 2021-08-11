#
# Update report parameters
# Add/remove/update parameters for a report
#

from enum import Enum
from tabulate import tabulate
from typing import Any

import nfpy.Assets as As
import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.1'
_TITLE_ = "<<< Update report parameters script >>>"


class States(Enum):
    NOT_ = 0
    KEY_ = 1
    GUP_ = 2
    MOD_ = 3
    ADD_ = 4
    REM_ = 5
    EXT_ = 6


def is_leaf(_n) -> bool:
    return not isinstance(_n, dict)


def get_node(_p, _b) -> Any:
    leaf = _p
    for el in _b:
        leaf = leaf[el]
    return leaf


def modify_key(_p, _b) -> None:
    _leaf = _b.pop()
    _n = get_node(_p, _b)
    # FIXME: missing error handling on these input commands
    idesc = inh.input('New type for value: ')
    _n[_leaf] = inh.input('New value for key: ', idesc=idesc)


def add_key(_n) -> None:
    _key = inh.input('New key: ')
    idesc = inh.input('New type for value: ')
    _n[_key] = inh.input('New value for key: ', idesc=idesc)


def remove_key(_n) -> None:
    _key = inh.input('Key to delete: ')
    if _key in _n:
        del _n[_key]
    else:
        print(f'  * {_key} not found!')


def get_command(_n) -> tuple:
    if is_leaf(_n):
        if inh.input(f'{_n}\nModify?: ', idesc='bool'):
            return States.MOD_, ''
        else:
            return States.GUP_, ''
    else:
        c = inh.input(f'{", ".join(map(str, _n.keys()))}\nEnter command: ')
        if c == 'q':
            return States.EXT_, ''
        elif c == 'u':
            return States.GUP_, ''
        elif c == 'a':
            return States.ADD_, ''
        elif c == 'r':
            return States.REM_, ''
        else:
            return States.KEY_, c


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    cal = Cal.get_calendar_glob()
    cal.initialize(Cal.today(), Cal.last_business())

    af = As.get_af_glob()
    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # Choose a report to modify
    prk = tuple(qb.get_keys('Reports'))
    reports = db.execute(
        qb.selectall('Reports', fields=prk)
    ).fetchall()

    msg = f'Choose a report to update:\n' \
          f'{tabulate(reports, headers=prk, showindex=True)}\n' \
          f'Give an report index: '
    idx = inh.input(msg, idesc='int')

    # Fetch data
    params = db.execute(
        qb.select(
            'Reports',
            fields=('parameters',),
            keys=prk
        ),
        reports[idx]
    ).fetchall()[0][0]

    # Represent dictionary
    msg = f'Commands:\n  > "key": enter into key\n  > "q": exit\n' \
          f'  > "u": go up one level\n  > "a": add a key\n' \
          f'  > "r": remove a key\nCurrent parameters are:\n'
    print(msg)

    # Poor man's state machine to change parameters
    command = ''
    branch = []
    state = States.NOT_
    while state != States.EXT_:
        if state == States.NOT_:
            state, command = get_command(
                get_node(params, branch)
            )

        elif state == States.MOD_:
            modify_key(params, branch)
            state = States.NOT_

        elif state == States.GUP_:
            try:
                branch.pop()
            except IndexError:
                pass
            state = States.NOT_

        elif state == States.KEY_:
            node = get_node(params, branch)
            if command not in node.keys():
                print('  * Wrong key!')
            else:
                branch.append(command)
            state = States.NOT_

        elif state == States.ADD_:
            add_key(get_node(params, branch))
            state = States.NOT_

        elif state == States.REM_:
            remove_key(get_node(params, branch))
            state = States.NOT_

    # Save changes to database
    if inh.input('Save the new parameters to database (Default False)?: ',
                 idesc='bool', default=False):
        db.execute(
            qb.update(
                'Reports',
                fields=('parameters',),
                keys=prk
            ),
            (params, reports[idx][0])
        )

    print('All done!')
