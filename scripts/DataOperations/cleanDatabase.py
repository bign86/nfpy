#
# Clean Database
# Script to filter and delete data from a database table.
# Allows to choose a table and filter the data contained on the existing
# columns to select the data to be deleted.
#

from enum import Enum
from tabulate import tabulate

import nfpy.DB as DB
import nfpy.IO as IO
import nfpy.IO.Utilities as Ut

__version__ = '0.2'
_TITLE_ = "<<< Delete data script >>>"

_ITEM_SHOWED = 10


class States(Enum):
    UNSET = 0
    PRINT = 1
    QUIT = 2
    SHOWF = 3
    GETF = 4
    DELRC = 5
    EXIT = 6
    FETCH = 7
    DELFT = 8


class StateMachine(object):
    _ACTION_MSG = f'\n\t{Ut.Col.OKCYAN.value}a{Ut.Col.ENDC.value}: add a filter\n' \
                  f'\t{Ut.Col.OKCYAN.value}f{Ut.Col.ENDC.value}: show current filters\n' \
                  f'\t{Ut.Col.OKCYAN.value}p{Ut.Col.ENDC.value}: print found records\n' \
                  f'\t{Ut.Col.OKCYAN.value}d{Ut.Col.ENDC.value}: delete a filter\n' \
                  f'\t{Ut.Col.OKCYAN.value}e{Ut.Col.ENDC.value}: erase records found\n' \
                  f'\t{Ut.Col.OKCYAN.value}q{Ut.Col.ENDC.value}: quit\n' \
                  f'Command: '

    def __init__(self, table: str):
        self.table = table
        self.keys = tuple(qb.get_keys(table))
        self.fields = tuple(qb.get_fields(table))

        self.STATE = States.UNSET
        self.records_found = []
        self.conditions = []

    def run(self) -> None:
        while self.STATE != States.EXIT:

            if self.STATE == States.UNSET:
                self._get_state()
            elif self.STATE == States.PRINT:
                self.print_results()
                self.STATE = States.UNSET
            elif self.STATE == States.QUIT:
                self._quit()
                self.STATE = States.EXIT
            elif self.STATE == States.SHOWF:
                self.print_filters()
                self.STATE = States.UNSET
            elif self.STATE == States.GETF:
                self._get_filter()
                self.STATE = States.FETCH
            elif self.STATE == States.DELRC:
                self._delete_records()
                self.STATE = States.UNSET
            elif self.STATE == States.FETCH:
                self._fetch()
                self.STATE = States.UNSET
            elif self.STATE == States.DELFT:
                self._delete_filter()
                self.STATE = States.FETCH

    def _delete_filter(self):
        self.print_filters()
        delete = inh.input(
            'Choose which to delete: ', idesc='index',
            limits=(0, len(self.conditions)-1)
        )
        self.conditions.pop(delete)

    def _delete_records(self) -> None:
        if inh.input(f'About to delete {len(self.records_found)} records!\n'
                     f'SURE??? (default False): ', idesc='bool', default=False):
            print('Ok...', end='')
            db.executemany(
                qb.delete(self.table, self.fields),
                self.records_found,
                commit=True
            )
            print(' Done!')
            self.records_found = []
        else:
            print('Aborted!')

        self.STATE = States.UNSET

    def _fetch(self) -> None:
        where = ' and '.join(self.conditions)
        self.records_found = db.execute(
            qb.select(self.table, keys=(), where=where),
        ).fetchall()
        print(f'Found {Ut.Col.WARNING.value}{len(self.records_found)}{Ut.Col.ENDC.value} records.')

    def _get_filter(self):
        self.print_fields()
        condition = inh.input('Insert a condition like <field> <=> <value>: ')
        elements = condition.split(' ')
        while (len(elements) < 3) or \
                (elements[0] not in self.fields) or \
                (elements[1] not in ('=', '<', '>', '<=', '>=', '!=')):
            condition = inh.input('Condition malformed. Try again: ')
            elements = condition.split(' ')
        condition_string = f"[{elements[0]}] {elements[1]} '{elements[2]}'"
        self.conditions.append(condition_string)

    def _get_state(self) -> None:
        todo = inh.input(self._ACTION_MSG)
        print()
        while todo not in ('a', 'q', 'f', 'p', 'd', 'e'):
            todo = inh.input(f'{todo} not recognized! Again, please: ')

        if todo == 'a':
            self.STATE = States.GETF
        elif todo == 'q':
            self.STATE = States.QUIT
        elif todo == 'f':
            self.STATE = States.SHOWF
        elif todo == 'p':
            self.STATE = States.PRINT
        elif todo == 'd':
            self.STATE = States.DELFT
        elif todo == 'e':
            self.STATE = States.DELRC

    def _quit(self) -> None:
        print('So long... quitting!')

    def print_fields(self) -> None:
        _msg = f'The following fields exists (* for keys)\n'
        for _field in self.fields:
            _ind = ' * ' if _field in self.keys else '   '
            _msg += _ind + _field + '\n'
        print(_msg)

    def print_filters(self) -> None:
        _msg = f'The following conditions exists:\n'
        for i, condition in enumerate(self.conditions):
            _msg += f'{i} | {condition}\n'
        print(_msg)

    def print_results(self) -> None:
        n = len(self.records_found)
        if n > _ITEM_SHOWED:
            print(
                f'Only the first {_ITEM_SHOWED} of {Ut.Col.WARNING.value}{n}{Ut.Col.ENDC.value} showed.',
                end='\n\n'
            )
        print(tabulate(self.records_found[-_ITEM_SHOWED:], headers=self.fields))


def _print_fields(_f, _k):
    _msg = 'The following fields exists (* for keys)\n'
    for _field in _f:
        _ind = ' * ' if _field in _k else '   '
        _msg += _ind + _field + '\n'
    print(_msg)


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    tbl = inh.input('Give a table to clean: ')
    while not qb.exists_table(tbl):
        tbl = inh.input(f'Table {tbl} not found. Try again: ')

    sm = StateMachine(tbl)
    sm.run()

    Ut.print_ok('All done!')
