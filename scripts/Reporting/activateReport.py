#
# Activate/Deactivate reports
# Script to change the activation status in Reports.
#

from operator import itemgetter
from tabulate import tabulate

import nfpy.DB as DB
import nfpy.IO as IO

_TABLE = 'Reports'

__version__ = '0.4'
_TITLE_ = "<<< Activate/Deactivate reports >>>"

_SELECT_COLS = ('id', 'title', 'description', 'report', 'active')


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    params = {}

    msg = "Give a id(%) (default None): "
    params['id'] = inh.input(msg, idesc='str', default=None, optional=True)

    msg = "Give a title(%) (default None): "
    params['title'] = inh.input(msg, idesc='str', default=None, optional=True)

    msg = "Give a description(%) (default None): "
    params['description'] = inh.input(msg, idesc='str', default=None, optional=True)

    select_keys = tuple(k for k, v in params.items() if v is not None)
    select_data = tuple(params[k] for k in select_keys)

    if not select_keys:
        res = db.execute(
            qb.selectall(_TABLE, _SELECT_COLS)
        ).fetchall()
    else:
        q = qb.select(_TABLE, _SELECT_COLS, partial_keys=select_keys)
        res = db.execute(q, select_data).fetchall()

    print(f'\n-------------------------------------------------------------\n'
          f'          {_TABLE}\n\n',
          f'{tabulate(res, _SELECT_COLS, showindex=True)}',
          end='\n\n')

    msg = "Choose the indices to modify (default None): "
    idx = inh.input(msg, idesc='int', is_list=True, default=None, optional=True)

    if not idx:
        print('All done!')
        exit()

    filtered = itemgetter(*idx)(res)
    if len(idx) == 1:
        filtered = (filtered,)

    msg = "Choose activate (1) or deactivate (0): "
    op = inh.input(msg, idesc='bool', optional=False)

    update_keys = tuple(qb.get_keys(_TABLE))
    fields_pos = tuple(_SELECT_COLS.index(f) for f in update_keys)
    update_data = tuple((op, itemgetter(*fields_pos)(v)) for v in filtered)

    q = qb.update(_TABLE, fields=('active',), keys=update_keys)
    db.executemany(q, update_data, commit=True)

    print('All done!')
