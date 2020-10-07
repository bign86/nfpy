#
# Calculate Beta
# Script to calculate the Beta exposure of an instrument on an index
#

from tabulate import tabulate

from nfpy.DB.DB import get_db_glob
from nfpy.Handlers.AssetFactory import get_af_glob
from nfpy.Handlers.Calendar import get_calendar_glob, today
from nfpy.Handlers.Plotting import PlotBeta
from nfpy.Handlers.QueryBuilder import get_qb_glob
from nfpy.Handlers.Inputs import InputHandler

__version__ = '0.2'
_TITLE_ = "<<< Beta calculation script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = get_af_glob()
    qb = get_qb_glob()
    db = get_db_glob()
    inh = InputHandler()

    start_date = inh.input("Give starting date for time series: ", idesc='str')
    if not start_date:
        raise ValueError('You must give a starting date.')

    end_date = inh.input("Give ending date for time series (default <today>): ",
                         default=today(), idesc='timestamp', optional=True)
    print('\n * Calendar dates: {} - {}'.format(start_date, end_date))
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
    print('Beta       : {:2.4f}'.format(b))
    print('Intercept  : {:2.4f}'.format(itc))
    print('Correlation: {:2.4f}\n'.format(rho))

    plt = PlotBeta(use_zero=True)
    plt.add(bmk.returns, eq.returns, (b, itc), label=eq.uid)
    plt.plot()
    plt.show()

    print('All done!')
