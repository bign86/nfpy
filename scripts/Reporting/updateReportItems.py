#
# Update report target items
# Add/remove uids to the report
#

from tabulate import tabulate
from typing import (Iterable, Optional)

import nfpy.Assets as As
import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

__version__ = '0.2'
_TITLE_ = "<<< Update report target items script >>>"

_SELECT_COLS = ('id', 'title', 'description', 'report', 'active')
_TABLE = 'Reports'


def _get_report_manually() -> Optional[Iterable]:
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
    idx = _inh.input(
        _msg, idesc='index', limits=(0, len(res) - 1),
        default=None, optional=True
    )

    if idx is None:
        return None

    _report_id = str(res[idx][0])
    q_sel = qb.select(_TABLE, fields=('uids',), keys=('id',))
    _uids = db.execute(q_sel, (_report_id,)).fetchone()[0]
    return _report_id, _uids


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    cal = Cal.get_calendar_glob()
    cal.initialize(Cal.today(), Cal.last_business())

    af = As.get_af_glob()
    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # Choose a report to modify and return the UIDs
    report_search_data = _get_report_manually()
    if report_search_data is None:
        print('Aborting...', end='\n\n')
        Ut.print_ok('All done!')
        exit()

    report_id, uids = report_search_data
    msg = f'\nCurrent uids are {len(uids)}:\n'
    for u in uids:
        msg += f'  > {u:>6} ({af.get_type(u):>9})\n'
    print(msg)

    # Add uids
    manual_add = inh.input('List the UIDs to add, comma separated: ',
                           is_list=True, default=[])

    # Check for associated equity/companies
    to_add = []
    while manual_add:
        u = manual_add.pop()
        v = af.get(u)
        if (v.type == 'Equity') \
                and (v.company not in to_add) \
                and (v.company not in uids):
            msg = f'You added {u} (Equity). Do you also want to add the ' \
                  f'company {v.company}? (default No): '
            if inh.input(msg, idesc='bool', default=False):
                to_add.append(v.company)
        elif (v.type == 'Company') \
                and (v.equity not in to_add) \
                and (v.equity not in uids):
            msg = f'You added {u} (Company). Do you also want to add the ' \
                  f'equity {v.equity}? (default No): '
            if inh.input(msg, idesc='bool', default=False):
                to_add.append(v.equity)
        to_add.append(u)

    # Remove uids
    manual_rem = inh.input('List uids to remove, comma separated: ',
                           is_list=True, default=[])

    # Check for associated equity/companies
    to_rem = []
    while manual_rem:
        u = manual_rem.pop()
        v = af.get(u)
        if (v.type == 'Equity') \
                and ((v.company in to_add) or (v.company in uids)):
            msg = f'You removed {u} (Equity). Do you also want to remove ' \
                  f'the company {v.company}? (default No): '
            if inh.input(msg, idesc='bool', default=False):
                to_rem.append(v.company)
        elif (v.type == 'Company') \
                and ((v.equity in to_add) or (v.equity in uids)):
            msg = f'You removed {u} (Company). Do you also want to remove ' \
                  f'the equity {v.equity}? (default No): '
            if inh.input(msg, idesc='bool', default=False):
                to_rem.append(v.equity)
        to_rem.append(u)

    # Update list
    uids = list((set(uids) - set(to_rem)) | set(to_add))

    if inh.input('Proceed with the changes (default No)?: ',
                 idesc='bool', default=False):
        db.execute(
            qb.update(
                _TABLE,
                fields=('uids',),
                keys=('id',)
            ),
            (uids, report_id)
        )
    else:
        print('Aborting...', end='\n\n')

    Ut.print_ok('All done!')
