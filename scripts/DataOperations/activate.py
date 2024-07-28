#
# Activate/Deactivate
# Script to change the activation status in Downloads and Imports.
#

from collections import namedtuple
from tabulate import tabulate

import nfpy.DB as DB
import nfpy.IO as IO
import nfpy.IO.Utilities as Ut
import nfpy.Tools.Exceptions as Ex

__version__ = '0.6'
_TITLE_ = "<<< Activate/Deactivate script >>>"
_DESC_ = """Activate or deactivate downloads and imports."""


def _mod_table(items: [], tbl: str) -> []:
    fields = items[0]._fields

    msg = f'The following {tbl} have been found:\n' \
          f'{tabulate(items, fields, showindex=True)}\n\n' \
          f'Give index list of selected {tbl} to change (default None): '
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
          f'{tabulate(to_change, fields, showindex=True)}\n\n' \
          f'Continue? (default False): '
    if inh.input(msg, idesc='bool', default=False):
        return to_change
    else:
        return []


def _wrt_to_db(wrt: [], tbl: str):
    if wrt:
        print('Updating table...', end='\n\n')
        keys = tuple(set(qb.get_fields(tbl)) - {'active'})

        data = [
            (w.active,) + tuple(getattr(w, f) for f in keys)
            for w in wrt
        ]

        db.executemany(
            qb.update(tbl, fields=('active',), keys=keys),
            data,
            commit=True
        )
    else:
        print('Skipping...', end='\n\n')


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n')
    print(_DESC_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # Give inputs
    # We do not perform a check to confirm the existence of the UID. Such check
    # would make it impossible to operate on Downloads/Imports of assets not
    # present in the elaboration tables.
    uid = inh.input('Give a UID for the Imports table: ', optional=False)
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
        ex = Ex.MissingData(f'No Imports found for this UID!')
        Ut.print_exc(ex)
        raise ex

    # Modify imports
    if inh.input(f'Modify Imports? (default False): ',
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

    if inh.input(f'Modify Downloads? (default False): ',
                 idesc='bool', default=False):
        _wrt_to_db(
            _mod_table(downloads, 'Downloads'),
            'Downloads'
        )

    Ut.print_ok('All done!')
