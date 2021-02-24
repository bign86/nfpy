#
# Activate/Deactivate report
# Script to change the status in Reports.
#

from operator import itemgetter
from tabulate import tabulate

import nfpy.DB as DB
import nfpy.IO as IO

_TABLE = 'ReportItems'

__version__ = '0.3'
_TITLE_ = "<<< Activate/Deactivate financial instruments >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    params = {}

    msg = "Give a report name(%) (default None): "
    params['report'] = inh.input(msg, idesc='str', default=None, optional=True)

    msg = "Give a uid(%) (default None): "
    params['uid'] = inh.input(msg, idesc='str', default=None, optional=True)

    msg = "Give a model(%) (default None): "
    params['model'] = inh.input(msg, idesc='str', default=None, optional=True)

    select_keys = tuple(k for k, v in params.items() if v is not None)
    select_data = tuple(params[k] for k in select_keys)

    if not select_keys:
        print('All done!')
        exit()

    print('\n-------------------------------------------------------------')
    print('          {}'.format(_TABLE), end='\n\n')
    q = qb.select(_TABLE, partial_keys=select_keys)
    res = db.execute(q, select_data).fetchall()

    fields = tuple(qb.get_fields(_TABLE))
    print(tabulate(res, fields, showindex=True), end='\n\n')

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
    fields_pos = tuple(fields.index(f) for f in update_keys)
    update_data = tuple((op,) + itemgetter(*fields_pos)(v) for v in filtered)

    q = qb.update(_TABLE, fields=('active',), keys=update_keys)
    db.executemany(q, update_data, commit=True)

    print('All done!')
