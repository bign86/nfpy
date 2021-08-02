#
# Price Details Discounted Cash Flow
# Calculate the fair value of company with the Discounted Cash Flow
# Model plot details.
#

from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.IO as IO
from nfpy.Models import DiscountedCashFlowModel

plt.interactive(False)
np.set_printoptions(precision=3, suppress=True)

__version__ = '0.3'
_TITLE_ = "<<< Price equity DCF details script >>>"


def print_results(_r):
    floatfmt = (None, '.0f', '.0f', '.0%', '.0f', '.0%', '.0%', '.0f', '.0%',
                '.0%', '.0%', '.0%', '.0%', '.0%')
    print(f'\n--------------------------------------------------------------\n\n'
          f' *** Input information ***\n'
          f'Company:\t\t\t{_r.uid} ({_r.equity})\n'
          f'Past horizon:\t\t{_r.past_horizon:d} years\n'
          f'Future projection:\t{_r.future_proj:d} years\n'
          f'Last price:\t\t\t{_r.last_price:.2f} ({_r.ccy})\n\n'
          # 'Discount factor (WACC):\t{:.1f}%'.format(_r.wacc*100), end='\n\n'
          f'{tabulate(_r.df, headers=_r.df.columns, floatfmt=floatfmt, missingval="-")}\n\n'
          f'Fair value: {_r.fair_value:.2f} ({_r.ccy})',
          end='\n\n')


def plot_results(_r):
    _r.fcf.plot()
    _r.net_income.plot()
    _r.revenues.plot()
    _r.total_debt.plot()
    _r.fcf_coverage.plot()
    _r.revenues_returns.plot()
    _r.net_income_margin.plot()
    _r.tax_rate.plot()
    _r.cost_of_debt.plot()
    _r.beta.plot()
    _r.market_return.plot()
    _r.cost_of_equity.plot()
    _r.wacc.plot()

    plt.legend()
    plt.plot()
    plt.show()


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
    pr = inh.input("Give perpetual growth rate (default: 0.): ",
                   idesc='float', default=0., optional=True)

    # Calculate the starting date to ensure enough past data are loaded
    end_date = today(mode='datetime')
    curr_year = end_date.year
    start_date = pd.Timestamp(curr_year - ph - 1, 1, 1)
    get_calendar_glob().initialize(end_date, start_date)

    # Calculate
    res = DiscountedCashFlowModel(cmp, perpetual_rate=pr,
                                  past_horizon=ph, future_proj=fp) \
        .result()

    print_results(res)
    plot_results(res)

    print('All done!')
