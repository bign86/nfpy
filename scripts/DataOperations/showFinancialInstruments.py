#
# Show financial instruments
# Script to show all financial instruments known by the system
#

from itertools import groupby
from tabulate import tabulate

import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools.Utilities import Col

__version__ = '0.5'
_TITLE_ = "<<< Show financial instruments script >>>"


def search_instrument() -> bool:
    search_str = inh.input('Search: ', idesc='str')
    if search_str == 'quit':
        return False

    search = '%' + search_str + '%'
    data = (search, search)
    where = 't.[uid] like ? or t.[description] like ?'
    q_ac = qb.select(
        'Assets',
        fields=('type', 'uid'),
        where=where
    )

    list_instr = db.execute(q_ac, data).fetchall()
    if not list_instr:
        print(f'{Col.WARNING.value}Nothing found.{Col.ENDC.value}', end='\n\n')
        return True

    q_asset = 'select * from {} where uid in {}'
    list_instr = sorted(list_instr, key=lambda v: v[0])
    for k, g in groupby(list_instr, lambda v: v[0]):
        uids = [v[1] for v in g]
        where = "('" + "', '".join(uids) + "')"
        assets = db.execute(q_asset.format(k, where)).fetchall()
        f = list(qb.get_fields(k))
        print(
            f'{Col.OKGREEN.value}Found {len(uids)} {k}{Col.ENDC.value}\n'
            f'{tabulate(assets, headers=f)}',
            end='\n\n'
        )

    return True


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    print("The search input is always treated as partial. Type 'quit' to exit.")
    while search_instrument():
        pass

    print('All done!')
