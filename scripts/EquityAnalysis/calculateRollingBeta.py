#
# Calculate Rolling Beta
# Script to calculate the rolling Beta exposure of an instrument on an index
#

from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.3'
_TITLE_ = "<<< Rolling Beta calculation script >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = get_af_glob()
    qb = DB.get_qb_glob()
    db = DB.get_db_glob()
    inh = IO.InputHandler()

    start_date = inh.input("Give starting date for time series: ",
                           idesc='datetime', optional=False)
    end_date = inh.input("Give ending date for time series (default <today>): ",
                         default=today(), idesc='timestamp')
    get_calendar_glob().initialize(end_date, start_date)

    q = "select * from Assets where type = 'Equity'"
    res = db.execute(q).fetchall()

    f = list(qb.get_fields('Assets'))
    print(f'\n\nAvailable equities:'
          f'{tabulate(res, headers=f, showindex=True)}')
    uid = inh.input("\nGive an equity index: ", idesc='int')
    eq = af.get(res[uid][0])

    q = "select * from Assets where type = 'Indices'"
    res = db.execute(q).fetchall()

    print(f'\n\nAvailable indices:'
          f'{tabulate(res, headers=f, showindex=True)}'
          f'Default index: {eq.index}')
    idx = inh.input("\nGive indices comma separated (Default None): ",
                    idesc='int', optional=True, is_list=True)
    w = inh.input("\nChoose window size (Default 120 (~6m)): ", default=120,
                  idesc='int', optional=True, is_list=True)

    plt = IO.Plotter()

    if idx is None:
        dt, b, adj_b, itc = eq.beta(w=w)
        plt.lplot(0, dt, b, label=eq.index)
    else:
        for i in idx:
            bmk = af.get(res[i][0])
            dt, b, adj_b, itc = eq.beta(bmk, w=w)
            plt.lplot(0, dt, b, label=bmk.uid)

    plt.plot()
    plt.show()

    print('All done!')
