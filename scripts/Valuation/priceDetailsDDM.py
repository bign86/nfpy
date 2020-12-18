#
# Price Details Dividend Discount Model
# Calculate the fair value of company with the Dividend Discount Model and
# plot calculation details.
#

from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Financial.DividendDiscountModel import DividendDiscountModel
from nfpy.Handlers.Calendar import get_calendar_glob, today
from nfpy.Handlers.Inputs import InputHandler

plt.interactive(False)
np.set_printoptions(precision=3, suppress=True)

__version__ = '0.2'
_TITLE_ = "<<< Price equity DDM details script >>>"

_TCOLS = ['year', 'no_growth', 'growth']


def print_results(_r):
    print('\n--------------------------------------------------------------\n')
    print(' *** Input information ***')
    print('Company:\t\t\t{} ({})'.format(_r.company, _r.equity))
    print('Past horizon:\t\t{:d} years\nFuture projection:\t{:d} years'
          .format(_r.past_horizon, _r.future_proj))
    print('Discount factor:\t{:.1f}%'.format(_r.d_rate*100), end='\n\n')

    print(' *** Cash flow projection ***', end='\n')
    v = np.vstack((_r.future_dates + curr_year, _r.div_zg, _r.div_gwt)).T
    print(tabulate(v, headers=_TCOLS, floatfmt=('', '.3f', '.3f')))

    lp = _r.last_price
    fv_ng = _r.fair_value_no_growth
    fv_wg = _r.fair_value_with_growth

    print('\nLast price:\t\t\t\t\t{:.2f} ({})'.format(_r.last_price, _r.ccy))
    print('Fair value\t- no_growth:\t{:.2f} ({:.2f}%)\n\t\t\t- with_growth:\t{:.2f} ({:.2f}%)'
          .format(fv_ng, (lp - fv_ng) / lp * 100., fv_wg, (lp - fv_wg) / lp * 100.), end='\n\n')
    print('Drifts (yearly)\t- price:\t\t{:.1f}%\n\t\t\t\t- dividends:\t{:.1f}%'
          .format(_r.price_drift * 100., _r.div_drift * 100.), end='\n\n')


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    # Handlers
    af = get_af_glob()
    inh = InputHandler()

    # Get inputs
    cmp = inh.input("Give a company uid: ", idesc='uid')
    while not af.exists(cmp):
        print(' * Supplied uid does not exist!')
        cmp = inh.input("Give a company uid: ", idesc='uid')
    ph = inh.input("Give number of years of past horizon (default: 5): ",
                   idesc='int', default=5, optional=True)
    fp = inh.input("Give number of years for projection (default: 3): ",
                   idesc='int', default=3, optional=True)
    dr = inh.input("Give discount rate (default: 7%): ",
                   idesc='float', default=.07, optional=True)

    # Calculate the starting date to ensure enough past data are loaded
    end_date = today(mode='datetime')
    curr_year = end_date.year
    start_date = pd.Timestamp(curr_year - ph - 1, 1, 1)
    get_calendar_glob().initialize(end_date, start_date)

    # Calculate
    ddm = DividendDiscountModel(cmp, past_horizon=ph,
                                future_proj=fp)
    res = ddm.result(d_rate=dr)

    print_results(res)

    print('All done!')
