#
# Dump report configuration
# Create a JSON configuration file from a database report entry
#

import argparse
import json
from operator import itemgetter
import os
from pandas import DateOffset
from tabulate import tabulate
from typing import Iterable

import nfpy.Calendar as Cal
from nfpy.Tools import get_conf_glob
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

__version__ = '0.2'
_TITLE_ = "<<< Dump report configuration script >>>"

_SELECT_COLS = ('id', 'title', 'description', 'report', 'active')
_TABLE = 'Reports'
_TIME_SPAN_MONTH = 120


def _get_reports_manually(_inh) -> Iterable:
    params = {}

    msg = "Give an id(%) (default None): "
    params['id'] = _inh.input(msg, default=None, optional=True)

    msg = "Give a title(%) (default None): "
    params['title'] = _inh.input(msg, default=None, optional=True)

    msg = "Give a description(%) (default None): "
    params['description'] = _inh.input(msg, default=None, optional=True)

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

    msg = "Choose the indices of the reports to dump. Leave empty to exit (default None): "
    idx = inh.input(msg, idesc='int', is_list=True, default=[], optional=True)

    if not idx:
        return []

    filtered = itemgetter(*idx)(res)
    if len(idx) == 1:
        filtered = (filtered,)

    return tuple(v[0] for v in filtered)


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()

    working_folder = get_conf_glob().working_folder

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i', '--interactive', action='store_true', help='use interactively'
    )
    parser.add_argument(
        '-p', '--path', type=str, dest='path_out', help='Output file path'
    )
    parser.add_argument('ids', nargs="*", help='list of report IDs')
    args = parser.parse_args()

    if args.interactive is True:
        inh = IO.InputHandler()

        path = inh.input(
            f'Give an output folder\n(default {working_folder})\n',
            idesc='str', optional=True, default=working_folder
        )
        while not os.path.isdir(path):
            path = inh.input('Folder not found, retry: ', idesc='str')

        reports = _get_reports_manually(inh)

    else:
        path = args.path_out if args.path_out else working_folder
        reports = tuple(args.ids)

    if not reports:
        print('Nothing to pruduce, exiting...', end='\n\n')
        Ut.print_ok('All done!')
        exit()

    print(f'\nDumping the following reports:\n -> {", ".join(reports)}',
          end='\n\n')

    # Dates are needed in the JSON
    today = Cal.today(mode='timestamp')
    start = (today - DateOffset(months=_TIME_SPAN_MONTH)).strftime('%Y-%m-%d')
    end = today.strftime('%Y-%m-%d')

    # Create select query to get the data
    q = qb.select(_TABLE, keys=('id',))
    cols = qb.get_fields(_TABLE)
    for report_id in reports:
        fp = open(os.path.join(path, report_id + '.json'), 'w')

        db_data = db.execute(q, (report_id,)).fetchone()
        data = dict((k, v) for k, v in zip(cols, db_data))
        data['start'] = start
        data['end'] = end

        json.dump(data, fp)
        fp.close()

    Ut.print_ok('All done!')
