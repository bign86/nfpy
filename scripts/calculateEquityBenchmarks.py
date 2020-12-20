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
from nfpy.Tools import Exceptions as Ex

__version__ = '0.3'
_TITLE_ = "<<< Equity benchmark calculation script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = get_af_glob()
    qb = DB.get_qb_glob()
    db = DB.get_db_glob()
    inh = IO.InputHandler()

    start_date = inh.input("Give starting date for time series: ", idesc='datetime')
    if not start_date:
        raise ValueError('You must give a starting date.')

    end_date = inh.input("Give ending date for time series (default <today>): ",
                         default=today(), idesc='timestamp')
    get_calendar_glob().initialize(end_date, start_date)

    q = "select * from Assets where type = 'Equity'"
    res = db.execute(q).fetchall()

    f = list(qb.get_fields('Assets'))
    print('\n\nAvailable equities:')
    print(tabulate(res, headers=f, showindex=True))
    uid = inh.input("\nGive an equity index: ", idesc='int')
    eq = af.get(res[uid][0])

    q = "select * from Assets where type = 'Indices'"
    idx = db.execute(q).fetchall()

    default = eq.index
    res = []
    for tup in idx:
        try:
            uid = tup[0]
            bmk = af.get(uid)
            dt, b, adj_b, itc = eq.beta(bmk)
            rho = eq.returns.corr(bmk.returns)
            d = '*' if default == uid else ''
            res.append((d, uid, rho, b, adj_b))
        except Ex.MissingData as ex:
            print(ex)
    res = sorted(res, key=lambda x: x[2], reverse=True)

    f = ['', 'Index', 'Correlation', 'Beta', 'Adj. Beta']
    print('\n--------------------------------------------\nResults:')
    print('--------------------------------------------')
    print(tabulate(res, headers=f, showindex=True, floatfmt=".3f"))

    print('All done!')
