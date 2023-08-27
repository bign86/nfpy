#
# List reports
# Script to list available reports and their characteristics
#

import argparse
import json
from tabulate import tabulate
from typing import Optional

import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

__version__ = '0.2'
_TITLE_ = "<<< List reports script >>>"

_SELECT_COLS = ('id', 'title', 'description', 'report', 'active')
_TABLE = 'Reports'


def _get_report_manually() -> Optional[str]:
    _inh = IO.InputHandler()
    params = {}

    _msg = "Give an id(%) (default None): "
    params['id'] = _inh.input(_msg, default=None, optional=True)

    _msg = "Give a title(%) (default None): "
    params['title'] = _inh.input(_msg, default=None, optional=True)

    _msg = "Give a description(%) (default None): "
    params['description'] = _inh.input(_msg, default=None, optional=True)

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
        return None

    print(f'\n-------------------------------------------------------------\n'
          f'{tabulate(res, _SELECT_COLS, showindex=True)}',
          end='\n\n')

    _msg = "Choose the index (only one) of the report to generate. Leave empty to exit (default None): "
    idx = _inh.input(_msg, idesc='int', default=None, optional=True)

    if idx is None:
        return None

    return str(res[idx][0])


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='use interactively')
    parser.add_argument('id', nargs='?', help='report ID')
    args = parser.parse_args()

    if args.interactive is True:
        report_id = _get_report_manually()

    else:
        report_id = str(args.id) if args.id else None

    if report_id is None:
        print('Nothing to show, exiting...', end='\n\n')
        Ut.print_ok('All done!')
        exit()

    # Fetch data
    data = db.execute(
        qb.select(_TABLE, keys=('id',)),
        (report_id,)
    ).fetchone()

    msg = f'\nThe following are the details of the report:\n' \
          f'name:              {data[0]}\n' \
          f'description:       {data[1]}\n' \
          f'report (py):       {data[2]}\n' \
          f'template (html):   {data[3]}.html\n' \
          f'active:            {"Yes" if bool(data[7]) else "No"}\n' \
          f'num. uids:         {len(data[5])}\n\n' \
          f'The following parameters are defined:\n' \
          f'{json.dumps(data[6], indent=4, sort_keys=True)}'
    print(msg, end='\n\n')

    Ut.print_ok('All done!')
