#
# Calculate Equity benchmarks
# Script to calculate the Beta exposure and correlation of an instrument
# against a number of different indices
#

from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import (Exceptions as Ex, Utilities as Ut)

__version__ = '0.8'
_TITLE_ = "<<< Equity benchmark calculation script >>>"


def update_index(_eq) -> None:
    _q = "select * from Assets where type = 'Indices'"
    _idx = db.execute(_q).fetchall()

    _res = []
    for _tup in _idx:
        try:
            _uid = _tup[0]
            _bmk = af.get(_uid)
            # d = '*' if _eq.index == _uid else ''
            _res.append(
                (
                    '*' if _eq.index == _uid else '',
                    _uid,
                    _eq.returns.corr(_bmk.returns),
                    *(_eq.beta(_bmk)[:2])
                )
            )
        except Ex.MissingData as ex:
            Ut.print_exc(ex)
    _res = sorted(_res, key=lambda x: x[2], reverse=True)

    _f = ['', 'Index', 'Correlation', 'Beta', 'Adj. Beta']
    print(
        f'\n--------------------------------------------\nResults:\n'
        f'--------------------------------------------\n'
        f'{tabulate(_res, headers=_f, showindex=True, floatfmt=".3f")}',
        end='\n\n'
    )
    update = inh.input(
        "Update default index (default No)? ",
        idesc='bool', default=False, optional=True
    )
    if update:
        new_idx = 9999
        while (new_idx < 0) or (new_idx >= len(_res)):
            new_idx = inh.input("Choose a new index: ", idesc='int')

        _q_upd = qb.update('Equity', fields=('index',))
        db.execute(_q_upd, (_res[new_idx][1], _eq.uid), commit=True)
        print('...saved...')


def search_equity() -> bool:
    search_str = inh.input('Search: ', idesc='str')
    if search_str == 'quit':
        return False

    search = '%' + search_str + '%'
    data = (search, search, search)
    q_ac = f'select [uid], [ticker], [description] from [Equity] ' \
           f'where [uid] like ? or [ticker] like ? or [description] like ?'

    list_instr = db.execute(q_ac, data).fetchall()
    if not list_instr:
        print(f'{Ut.Col.WARNING.value}Nothing found.{Ut.Col.ENDC.value}', end='\n\n')
        return True

    header = ('uid', 'ticker', 'description')
    print(
        f'{Ut.Col.OKGREEN.value}Found {len(list_instr)}{Ut.Col.ENDC.value}\n'
        f'{tabulate(list_instr, headers=header, showindex=True)}',
        end='\n\n'
    )

    eq_idx = inh.input("Give an equity index: ", idesc='int')
    while (eq_idx < 0) or (eq_idx >= len(list_instr)):
        msg = f'{Ut.Col.WARNING.value} ! Wrong index !{Ut.Col.ENDC.value}\n' \
              f'Give an equity index: '
        eq_idx = inh.input(msg, idesc='int')

    update_index(
        af.get(list_instr[eq_idx][0])
    )
    print('--------------------------------------', end='\n\n')

    return True


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = get_af_glob()
    qb = DB.get_qb_glob()
    db = DB.get_db_glob()
    inh = IO.InputHandler()

    start_date = inh.input("Give starting date for time series: ",
                           idesc='timestamp', optional=False)
    end_date = inh.input("Give ending date for time series (default <today>): ",
                         default=today(), idesc='timestamp', optional=True)
    get_calendar_glob().initialize(end_date, start_date)

    print("The search input is always treated as partial. Type 'quit' to exit.")
    while search_equity():
        pass

    print('All done!')
