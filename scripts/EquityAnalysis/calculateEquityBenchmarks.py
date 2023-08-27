#
# Calculate Equity benchmarks
# Script to calculate the Beta exposure and correlation of an instrument
# against all known indices.
#

from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import (Exceptions as Ex, Utilities as Ut)

__version__ = '0.9'
_TITLE_ = "<<< Equity benchmark calculation script >>>"
_DESC_ = """Calculates Beta exposure and Correlation of an instrument against all known indices.
The instrument search is treated as partial (similarly to 'like' in databases) and is performed
on the 'uid', 'ticker' and 'description' fields.
To exit type 'quit' in the search field."""


def update_index(_eq) -> None:
    _q = "select * from Assets where type = 'Indices'"
    _idx = db.execute(_q).fetchall()

    _res = []
    for _tup in _idx:
        try:
            _uid = _tup[0]
            _bmk = af.get(_uid)
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
        new_idx = inh.input(
            "Choose a new index: ",
            idesc='index', limits=(0, len(_res) - 1)
        )

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
    eq_idx = inh.input(
        "Give an equity index: ",
        idesc='index', limits=(0, len(list_instr) - 1)
    )

    update_index(
        af.get(list_instr[eq_idx][0])
    )
    print('--------------------------------------', end='\n\n')

    return True


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n')
    print(_DESC_, end='\n\n')

    af = get_af_glob()
    qb = DB.get_qb_glob()
    db = DB.get_db_glob()
    inh = IO.InputHandler()

    start_date = inh.input("Give starting date for time series: ",
                           idesc='timestamp', optional=False)
    end_date = inh.input("Give ending date for time series (default <today>): ",
                         default=today(), idesc='timestamp', optional=True)
    get_calendar_glob().initialize(end_date, start_date)

    while search_equity():
        pass

    Ut.print_ok('All done!')
