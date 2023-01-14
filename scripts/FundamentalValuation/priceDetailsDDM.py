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
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.IO as IO
from nfpy.Models import DividendDiscountModel

plt.interactive(False)
np.set_printoptions(precision=3, suppress=True)

__version__ = '0.2'
_TITLE_ = "<<< Price equity DDM details script >>>"

_TCOLS = ['year', 'no_growth', 'growth']


def print_results(_r):
    v = np.vstack((_r.future_dates + curr_year, _r.div_zg, _r.div_gwt)).T
    lp = _r.last_price
    fv_ng = _r.fair_value_no_growth
    fv_wg = _r.fair_value_with_growth
    print(f'\n--------------------------------------------------------------\n'
          f' *** Input information ***\n'
          f'Company:\t\t\t{_r.company} ({_r.equity})\n'
          f'Past horizon:\t\t{_r.past_horizon:d} years\n'
          f'Future projection:\t{_r.future_proj:d} years\n'
          f'Discount factor:\t{_r.d_rate*100:.1f}%\n\n'
          f' *** Cash flow projection ***\n'
          f'{tabulate(v, headers=_TCOLS, floatfmt=("", ".3f", ".3f"))}\n\n'
          f'Last price:\t\t\t\t\t{_r.last_price:.2f} ({_r.ccy})\n'
          f'Fair value\t- no_growth:\t{fv_ng:.2f} ({(lp - fv_ng) / lp * 100.:.2f}%)\n'
          f'\t\t\t- with_growth:\t{fv_wg:.2f} ({(lp - fv_wg) / lp * 100.:.2f}%)\n\n'
          f'Drifts (yearly)\t- price:\t\t{_r.price_drift * 100.:.1f}%\n'
          f'\t\t\t\t- dividends:\t{_r.div_drift * 100.:.1f}%',
          end='\n\n')


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    # Handlers
    af = get_af_glob()
    inh = IO.InputHandler()

    # Get inputs
    cmp = inh.input("Give a company uid: ", idesc='uid')
    while not af.exists(cmp):
        cmp = inh.input(" ! Supplied uid does not exist!\nGive a company uid: ",
                        idesc='uid')
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
    res = DividendDiscountModel(cmp, past_horizon=ph, future_proj=fp)\
        .result(d_rate=dr)

    print_results(res)

    print('All done!')
