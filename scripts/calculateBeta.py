#
# Calculate Beta
# Script to calculate the Beta exposure of an instrument on an index
#

from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.DB import (get_db_glob, get_qb_glob)
from nfpy.Handlers.Calendar import get_calendar_glob, today
from nfpy.Handlers.Inputs import InputHandler
from nfpy.Handlers.Plotting import PlotBeta

__version__ = '0.5'
_TITLE_ = "<<< Beta calculation script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = get_af_glob()
    qb = get_qb_glob()
    db = get_db_glob()
    inh = InputHandler()

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
    f = list(qb.get_fields('Assets'))
    res = db.execute(q).fetchall()

    print('\n\nAvailable indices:')
    print(tabulate(res, headers=f, showindex=True))
    print('Default index: {}'.format(eq.index))
    idx = inh.input("\nGive an index index :) (Default None): ",
                    idesc='int', optional=True)
    bmk = af.get(res[idx][0]) if idx else None

    dt, b, itc = eq.beta(bmk)
    if not idx:
        bmk = af.get(eq.index)
    rho = eq.returns.corr(bmk.returns)

    print('\n----------------------------------\nBeta calculation results')
    print('----------------------------------')
    print('Instrument : {} ({})'.format(eq.uid, eq.type))
    print('             {}'.format(eq.description))
    print('Proxy      : {} ({})'.format(bmk.uid, bmk.type))
    print('             {}'.format(bmk.description))
    print('Beta       : {:2.3f}'.format(b))
    print('Intercept  : {:2.3f}'.format(itc))
    print('Correlation: {:2.3f}\n'.format(rho))

    plt = PlotBeta()
    plt.add(bmk.returns.values, eq.returns.values, (b, itc))
    plt.plot()
    plt.show()

    print('All done!')
