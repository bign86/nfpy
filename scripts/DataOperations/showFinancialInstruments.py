#
# Show financial instruments
# Script to show all financial instruments known by the system
#

from itertools import groupby
from tabulate import tabulate

import nfpy.DB as DB
import nfpy.IO as IO
import nfpy.IO.Utilities as Ut

__version__ = '0.6'
_TITLE_ = "<<< Show financial instruments script >>>"
_DESC_ = """Make a partial string search (like a 'like' statement in the DB) in the uid and
description fields across all elaboration tables. To quit type 'quit' in the search field."""


def search_instrument() -> bool:
    search_str = inh.input('Search: ', idesc='str')
    if search_str == 'quit':
        return False

    search = '%' + search_str + '%'
    list_instr = db.execute(
        qb.select(
            'Assets',
            fields=('type', 'uid'),
            where='t.[uid] LIKE ? OR t.[description] LIKE ?'
        ),
        (search, search)
    ).fetchall()
    if not list_instr:
        Ut.print_wrn(Warning('Nothing found'), end='\n\n')
        return True

    q_asset = 'SELECT * from [{}] WHERE uid IN {}'
    list_instr = sorted(list_instr, key=lambda v: v[0])
    for k, g in groupby(list_instr, lambda v: v[0]):
        uids = [v[1] for v in g]
        where = "('" + "', '".join(uids) + "')"
        assets = db.execute(
            q_asset.format(k, where)
        ).fetchall()
        f = list(qb.get_fields(k))
        print(f'Found {len(uids)} {k}\n{tabulate(assets, headers=f)}', end='\n\n')

    return True


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n')
    print(_DESC_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    while search_instrument():
        pass

    Ut.print_ok('All done!')
