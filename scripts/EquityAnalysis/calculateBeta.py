#
# Calculate Beta
# Script to calculate the Beta exposure of an instrument on an index
#

import numpy as np
from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.7'
_TITLE_ = "<<< Beta calculation script >>>"

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
    print(f'\n\nAvailable equities:\n'
          f'{tabulate(res, headers=f, showindex=True)}',
          end='\n\n')
    uid = inh.input("Give an equity index: ", idesc='int')
    eq = af.get(res[uid][0])

    q = "select * from Assets where type = 'Indices'"
    res = db.execute(q).fetchall()

    print(f'\n\nAvailable indices:\n'
          f'{tabulate(res, headers=f, showindex=True)}'
          f'Default index: {eq.index}',
          end='\n\n')
    idx = inh.input("Give one index index :) (Default None): ",
                    idesc='int', optional=True)
    bmk = af.get(res[idx][0]) if idx else None

    dt, b, adj_b, itc = eq.beta(bmk)
    if not idx:
        bmk = af.get(eq.index)
    rho = eq.returns.corr(bmk.returns)

    print(f'\n----------------------------------\n'
          f'    Beta calculation results'
          f'----------------------------------\n'
          f'Instrument : {eq.uid} ({eq.type})\n'
          f'             {eq.description}\n'
          f'Proxy      : {bmk.uid} ({bmk.type})\n'
          f'             {bmk.description}\n'
          f'Beta       : {b:2.3f}\n'
          f'Adj. Beta  : {adj_b:2.3f}\n'
          f'Intercept  : {itc:2.3f}\n'
          f'Correlation: {rho:2.3f}',
          end='\n\n')

    br = bmk.returns.values
    er = eq.returns.values
    xg = np.linspace(min(float(np.nanmin(br)), .0),
                     float(np.nanmax(br)), 2)
    yg = b * xg + itc

    plt = IO.Plotter()
    plt.scatter(0, br, er, color='C0', linewidth=.0, marker='o', alpha=.5)
    plt.lplot(0, xg, yg, color='C0')
    plt.plot()
    plt.show()

    print('All done!')
