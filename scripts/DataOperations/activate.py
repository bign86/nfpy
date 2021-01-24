#
# Activate/Deactivate financial instruments
# Script to change the status in Downloads and/or Imports.
#

from operator import itemgetter
from tabulate import tabulate

import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.1'
_TITLE_ = "<<< Activate/Deactivate financial instruments >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    params = {}

    msg = "Give a uid (default None): "
    params['uid'] = inh.input(msg, idesc='str', default=None, optional=True)

    msg = "Give a ticker (default None): "
    params['ticker'] = inh.input(msg, idesc='str', default=None, optional=True)

    msg = "Give a provider (default None): "
    params['provider'] = inh.input(msg, idesc='str', default=None, optional=True)

    msg = "Give a page (default None): "
    params['page'] = inh.input(msg, idesc='str', default=None, optional=True)

    select_keys = tuple(k for k, v in params.items() if v is not None)
    select_data = tuple(params[k] for k in select_keys)

    if not select_keys:
        print('All done!')
        exit()

    for table in ['Downloads', 'Imports']:
        print('\n-------------------------------------------------------------')
        print('          {}'.format(table), end='\n\n')
        q = qb.select(table, keys=select_keys)
        res = db.execute(q, select_data).fetchall()

        fields = tuple(qb.get_fields(table))
        print(tabulate(res, fields, showindex=True), end='\n\n')

        msg = "Choose the indices to modify (default None): "
        idx = inh.input(msg, idesc='int', is_list=True,
                        default=None, optional=True)

        if not idx:
            continue
        filtered = itemgetter(*idx)(res)
        if len(idx) == 1:
            filtered = (filtered,)

        msg = "Choose activate (1) or deactivate (0): "
        op = inh.input(msg, idesc='bool', optional=False)

        update_keys = tuple(qb.get_keys(table))
        fields_pos = tuple(fields.index(f) for f in update_keys)
        update_data = tuple((op,) + itemgetter(*fields_pos)(v) for v in filtered)

        q = qb.update(table, fields=('active',), keys=update_keys)
        db.executemany(q, update_data, commit=True)

    print('All done!')
