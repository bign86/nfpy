#
# Activate/Deactivate reports
# Script to change the activation status in Reports.
#

import argparse
from operator import itemgetter
from tabulate import tabulate
from typing import Iterable

import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

_TABLE = 'Reports'

__version__ = '0.5'
_TITLE_ = "<<< Activate/Deactivate reports >>>"
_DESC_ = """In terminal mode, pass a list of report IDs for which to toggle the 'active'
flag. In interactive mode (-i argument), you can give some manual information to search
the reports to toggle."""

_SELECT_COLS = ('id', 'title', 'description', 'report', 'active')


def _get_reports_manually() -> Iterable:
    inh = IO.InputHandler()
    params = {}

    msg = "Give an id(%) (default None): "
    params['id'] = inh.input(msg, default=None, optional=True)

    msg = "Give a title(%) (default None): "
    params['title'] = inh.input(msg, default=None, optional=True)

    msg = "Give a description(%) (default None): "
    params['description'] = inh.input(msg, default=None, optional=True)

    select_keys = tuple(k for k, v in params.items() if v is not None)
    select_data = tuple(f'%{params[k]}%' for k in select_keys)

    if not select_keys:
        res = db.execute(
            qb.selectall(_TABLE, _SELECT_COLS)
        ).fetchall()
    else:
        q_sel = qb.select(_TABLE, _SELECT_COLS, partial_keys=select_keys)
        res = db.execute(q_sel, select_data).fetchall()

    if not res:
        print('No results found for this search, exiting...')
        return []

    print(f'\n-------------------------------------------------------------\n'
          f'{tabulate(res, _SELECT_COLS, showindex=True)}',
          end='\n\n')

    msg = "Choose the indices of the reports to modify. Leave empty to exit (default None): "
    idx = inh.input(msg, idesc='int', is_list=True, default=[], optional=True)

    if not idx:
        return []

    filtered = itemgetter(*idx)(res)
    if len(idx) == 1:
        filtered = (filtered,)

    return tuple((v[-1], v[0]) for v in filtered)


def _get_reports(_args) -> Iterable:
    list_ids = "','".join(_args.ids)
    where = f"[id] in (\'{list_ids}\')"
    return db.execute(
        qb.select(_TABLE, ('active', 'id'), keys=(), where=where),
        ()
    ).fetchall()


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n')
    print(_DESC_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='use interactively')
    parser.add_argument('ids', nargs="*", help='list of report IDs')
    args = parser.parse_args()

    if args.interactive is True:
        reports = _get_reports_manually()

    else:
        reports = _get_reports(args)

    if not reports:
        print('Nothing to change, exiting...', end='\n\n')
        Ut.print_ok('All done!')
        exit()

    print(f'\nToggling the following reports:\n'
          f' -> {", ".join(v[1] for v in reports)}',
          end='\n\n')

    update_data = (
        (int(not bool(v[0])), v[1])
        for v in reports
    )

    q = qb.update(_TABLE, fields=('active',), keys=('id',))
    db.executemany(q, update_data, commit=True)

    Ut.print_ok('All done!')
