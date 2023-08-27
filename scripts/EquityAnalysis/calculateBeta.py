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
from nfpy.Tools import Utilities as Ut

__version__ = '0.8'
_TITLE_ = "<<< Beta calculation script >>>"

if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    af = get_af_glob()
    qb = DB.get_qb_glob()
    db = DB.get_db_glob()
    inh = IO.InputHandler()

    start_date = inh.input("Give starting date for time series: ",
                           idesc='datetime', optional=False)

    end_date = inh.input("Give ending date for time series (default <today>): ",
                         default=today(), idesc='timestamp')
    get_calendar_glob().initialize(end_date, start_date)

    f = list(qb.get_fields('Assets'))

    # Get equity
    eq_uid = inh.input("Give an equity uid (press Enter for a list): ",
                       idesc='uid', optional=True)
    if not eq_uid:
        q = "select * from Assets where type = 'Equity'"
        res = db.execute(q).fetchall()

        msg = f'\n\nAvailable equities:\n' \
              f'{tabulate(res, headers=f, showindex=True)}\n' \
              f'Give an equity index: '
        idx = inh.input(msg, idesc='index', limits=(0, len(res) - 1))
        eq_uid = res[idx][0]
    eq = af.get(eq_uid)

    # Get index
    bmk_uid = eq.index
    if not inh.input(f"Use default benchmark index ({bmk_uid})? (default True): ",
                     idesc='bool', default=True):
        bmk_uid = inh.input("Give an index uid (press Enter for a list): ",
                            idesc='uid', optional=True)
        if not bmk_uid:
            q = "select * from Assets where type = 'Indices'"
            res = db.execute(q).fetchall()

            print(f'\n\nAvailable indices:\n'
                  f'{tabulate(res, headers=f, showindex=True)}'
                  f'Default index: {eq.index}',
                  end='\n\n')
            idx = inh.input("Give one index's index :): ",
                            idesc='index', limits=(0, len(res) - 1))
            bmk_uid = res[idx][0]
    bmk = af.get(bmk_uid)

    beta, adj_beta, itc = eq.beta(bmk)
    rho = eq.returns.corr(bmk.returns)

    print(f'\n----------------------------------\n'
          f'    Beta calculation results\n'
          f'----------------------------------\n'
          f'Instrument : {eq.uid} ({eq.type})\n'
          f'             {eq.description}\n'
          f'Proxy      : {bmk.uid} ({bmk.type})\n'
          f'             {bmk.description}\n'
          f'Beta       : {beta[0]:2.3f}\n'
          f'Adj. Beta  : {adj_beta[0]:2.3f}\n'
          f'Intercept  : {itc[0]:2.3f}\n'
          f'Correlation: {rho:2.3f}',
          end='\n\n')

    br = bmk.returns.to_numpy()
    er = eq.returns.to_numpy()
    xg = np.linspace(
        min(float(np.nanmin(br)), .0),
        float(np.nanmax(br)),
        2
    )
    yg = beta[0] * xg + itc[0]

    IO.Plotter(x_zero=(.0,), y_zero=(.0,)) \
        .scatter(0, br, er, color='C0', linewidth=.0, marker='o', alpha=.5) \
        .lplot(0, xg, yg, color='C0', label=f'{eq.uid}/{bmk.uid}') \
        .plot() \
        .show()

    Ut.print_ok('All done!')
