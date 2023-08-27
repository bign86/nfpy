#
# Produce a report
# Run the report engine on the selected report
#

import argparse
from pandas import DateOffset
from tabulate import tabulate
from typing import Optional

from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Reporting import get_re_glob
from nfpy.Tools import Utilities as Ut

__version__ = '0.4'
_TITLE_ = "<<< Report generation script >>>"

_SELECT_COLS = ('id', 'title', 'description', 'report', 'active')
_TABLE = 'Reports'
_OFFSET_DAILY_CAL_IN_MONTHS = 120
_OFFSET_YEARLY_CAL_IN_MONTHS = 240


def _get_report_manually() -> Optional[str]:
    _inh = IO.InputHandler()
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
        return None

    print(f'\n-------------------------------------------------------------\n'
          f'{tabulate(res, _SELECT_COLS, showindex=True)}',
          end='\n\n')

    msg = "Choose the index (only one) of the report to generate. Leave empty to exit (default None): "
    idx = _inh.input(
        msg, idesc='index', limits=(0, len(res) - 1),
        default=None, optional=True
    )

    if idx is None:
        return None

    return str(res[idx][0])


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()

    end = today(mode='timestamp')
    start_daily = end - DateOffset(months=_OFFSET_DAILY_CAL_IN_MONTHS)
    start_monthly = end - DateOffset(months=_OFFSET_YEARLY_CAL_IN_MONTHS)
    start_yearly = end - DateOffset(months=_OFFSET_YEARLY_CAL_IN_MONTHS)
    get_calendar_glob().initialize(
        end,
        start=start_daily,
        monthly_start=start_monthly,
        yearly_start=start_yearly
    )

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='use interactively')
    parser.add_argument('id', nargs=1, help='report ID')
    args = parser.parse_args()

    if args.interactive is True:
        report_id = _get_report_manually()

    else:
        report_id = args.id if args.id else None

    if report_id is None:
        print('Nothing to produce, exiting...', end='\n\n')
        Ut.print_ok('All done!')
        exit()

    print(f'\nCreating the following report:\n -> {report_id}', end='\n\n')

    get_re_glob().run(names=report_id)

    Ut.print_ok('All done!')
