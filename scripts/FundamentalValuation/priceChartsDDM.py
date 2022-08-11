#
# Price Charts Dividend Discount Model
# Calculate the fair value of company with Dividend Discount Model when
# projection horizon and discount rate are varied.
#

from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from tabulate import tabulate

from nfpy.Calendar import (get_calendar_glob, today)
from nfpy.Financial.EquityValuation import DDM2s
import nfpy.IO as IO

plt.interactive(False)
np.set_printoptions(precision=3, suppress=True)

__version__ = '0.3'
_TITLE_ = "<<< Price equity DDM charts script >>>"

_TCOLS = ('year', 'rate %', 'no_growth', 'growth')


def print_results():
    floatfmt = ('.0f', '.1f', '.2f', '.2f')
    print(
        f'\n--------------------------------------------------------------\n'
        f'\nCurrent price: {res.last_price:.2f}\n'
        f'\nVariable future projection\n'
        f'{tabulate(v1.T, headers=_TCOLS, floatfmt=floatfmt)}\n'
        f'\nVariable discount rate\n'
        f'{tabulate(v2.T, headers=_TCOLS, floatfmt=floatfmt)}',
        end='\n\n'
    )


def print_plots():
    lp = res.last_price
    pl1 = IO.Plotter(xl=('Year',), yl=('Fair value',), x_zero=(lp,))
    pl1.lplot(0, v1[0, :], v1[2, :], linewidth=2., label='w/o growth')
    pl1.lplot(0, v1[0, :], v1[3, :], linewidth=2., label='w/ growth')
    pl1.plot()

    pl2 = IO.Plotter(xl=('Discount rate',), yl=('Fair value',), x_zero=(lp,))
    pl2.lplot(0, v2[1, :], v2[2, :], linewidth=2., label='w/o growth')
    pl2.lplot(0, v2[1, :], v2[3, :], linewidth=2., label='w/ growth')
    pl2.plot()
    pl2.show()


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    inh = IO.InputHandler()

    # Calculate the starting date to ensure enough past data are loaded
    end_date = today(mode='datetime')
    curr_year = end_date.year
    start_date = pd.Timestamp(curr_year - 6, 1, 1)
    get_calendar_glob().initialize(end_date, start_date)

    cmp = inh.input("Give a company uid: ", idesc='uid')
    n = inh.input(f'\nVariable number of projection years\n'
                  f'Number of points (years) (default: 6): ',
                  idesc='int', default=6, optional=True)
    dr = inh.input("Give discount rate (default: None): ",
                   idesc='float', optional=True)
    vr = inh.input(f'\nMax value of discount rate (default: 10%): ',
                   idesc='float', default=0.1, optional=True)
    fp = inh.input("Give number of projection years (default: 5): ",
                   idesc='int', default=5, optional=True)

    # Calculations
    v1 = np.empty((4, n))
    for p in range(1, n + 1):
        ddm = DDM2s(cmp, projection=p)
        res = ddm.result(d_rate=dr)
        v1[0, p - 1] = curr_year + p
        v1[1, p - 1] = res.d_rate * 100.
        v1[2, p - 1] = res.fair_value_no_growth
        v1[3, p - 1] = res.fair_value_with_growth

    ddm = DDM2s(cmp, projection=fp)
    rates_list = list(np.arange(.01, vr + .001, .01))
    v2 = np.empty((4, len(rates_list)))
    for i, r in enumerate(rates_list):
        v2[0, i] = curr_year + fp
        v2[1, i] = r * 100.
        try:
            res = ddm.result(d_rate=r)
            v2[2, i] = res.fair_value_no_growth
            v2[3, i] = res.fair_value_with_growth
        except ValueError:
            v2[2, i] = np.nan
            v2[3, i] = np.nan

    print_results()
    print_plots()

    print('All done!')
