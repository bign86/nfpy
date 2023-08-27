#
# Add Trade
# Script to add or remove trades from portfolios.
#

from tabulate import tabulate

import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

__version__ = '0.4'
_TITLE_ = "<<< Add trade script >>>"

_COLS_ORDER = ['date', 'pos_uid', 'buy_sell', 'currency',
               'quantity', 'price', 'costs', 'market']
_COLS_QUESTIONS = {
    'date': ('Insert date and time (%Y-%m-%d %H:%M:%S): ', 'datetime'),
    'pos_uid': ('Insert position uid: ', 'str'),
    'buy_sell': ('Is it a buy position?: ', 'bool'),
    'currency': ('Insert currency uid: ', 'str'),
    'quantity': ('Insert quantity: ', 'float'),
    'price': ('Insert unitary price: ', 'float'),
    'costs': ('Insert trade costs (optional): ', 'float'),
    'market': ('Insert market of execution (optional): ', 'str')
}


def insert_trade_data():
    print('\n--- Insert trade data ---')
    columns = qb.get_columns('Trades')

    data = [ptf]
    for col in _COLS_ORDER:
        col_obj = columns[col]
        q, idesc = _COLS_QUESTIONS[col]

        in_data = inh.input(q, idesc=idesc, optional=not col_obj.notnull,
                            fmt='%Y-%m-%d %H:%M:%S')

        if col == 'buy_sell':
            in_data = 1 if in_data else 2

        data.append(in_data)

    # Insert trade
    q = qb.insert('Trades')
    db.execute(q, data, commit=True)


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # List available portfolios
    q_ptf = "select * from Assets where type = 'Portfolio'"
    res = db.execute(q_ptf).fetchall()

    fa = list(qb.get_fields('Assets'))
    print(
        f'\n\nAvailable portfolios:\n{tabulate(res, headers=fa, showindex=True)}',
        end='\n\n'
    )
    idx = inh.input(
        "Give a portfolio index: ",
        idesc='index', limits=(0, len(res) - 1)
    )
    ptf = res[idx][0]

    # User provides data
    v = True
    while v:
        insert_trade_data()
        v = inh.input('\n -> Insert another trade?: ', idesc='bool',
                      default=False)

    Ut.print_ok('All done!')
