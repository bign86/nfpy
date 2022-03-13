#
# Activate/Deactivate financial instruments
# Script to change the status in Downloads and/or Imports.
#

from collections import namedtuple
from tabulate import tabulate

import nfpy.DB as DB
import nfpy.Tools.Exceptions as Ex
import nfpy.IO as IO

__version__ = '0.5'
_TITLE_ = "<<< Activate/Deactivate financial instruments >>>"


def _mod_table(items: [], tbl: str) -> []:
    msg = f'The following {tbl} have been found:\n' \
          f'{tabulate(items, qb.get_fields(tbl), showindex=True)}\n\n' \
          f'Give index list of selected {tbl} to change (Default None): '
    idx = inh.input(msg, idesc='int', is_list=True, optional=True)
    if not idx:
        return []

    idx = [
        i for i in set(idx)
        if 0 <= i < len(items)
    ]
    to_change = []
    for i in sorted(idx)[::-1]:
        v = items.pop(i)
        t = v._replace(active=int(not v.active))
        to_change.append(t)
    msg = f'The following will change:\n' \
          f'{tabulate(to_change, qb.get_fields(tbl), showindex=True)}\n\n' \
          f'Continue (Default False)?: '
    if inh.input(msg, idesc='bool', default=False):
        return to_change
    else:
        return []


def _wrt_to_db(wrt: [], tbl: str):
    if wrt:
        keys = set(qb.get_fields(tbl)) - {'active'}

        data = [
            (w.active,) + tuple(getattr(w, f) for f in keys)
            for w in wrt
        ]

        db.executemany(
            qb.update(tbl, fields=('active',), keys=keys),
            data,
            commit=True
        )


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # Give inputs
    # We do not perform sanity checks on the UID. Such check would make it
    # impossible to operate on Downloads/Imports of assets already removed
    # from the elaboration tables.
    uid = inh.input('Give a UID: ', optional=False)
    tblNt = namedtuple('tblNt', qb.get_fields('Imports'))
    imports = list(
        map(
            tblNt._make,
            db.execute(
                qb.select('Imports', keys=('uid',)),
                (uid,)
            ).fetchall()
        )
    )
    if not imports:
        raise Ex.MissingData(f'No Imports found for this UID!')

    if inh.input(f'Modify Imports (Default False)?: ',
                 idesc='bool', default=False):
        _wrt_to_db(
            _mod_table(imports, 'Imports'),
            'Imports'
        )

    where = '\", \"'.join(set(v.ticker for v in imports))
    where = f'ticker in (\"{where}\")'
    tblNt = namedtuple('tblNt', qb.get_fields('Downloads'))
    downloads = list(
        map(
            tblNt._make,
            db.execute(
                qb.select('Downloads', keys=(), where=where),
                ()
            ).fetchall()
        )
    )
    if not downloads:
        print('No downloads on this UID.')
        exit()

    if inh.input(f'Modify Downloads (Default False)?: ',
                 idesc='bool', default=False):
        _wrt_to_db(
            _mod_table(downloads, 'Downloads'),
            'Downloads'
        )

    print('All done!')
