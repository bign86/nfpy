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
from nfpy.Models import DividendDiscountModel
import nfpy.IO as IO

plt.interactive(False)
np.set_printoptions(precision=3, suppress=True)

__version__ = '0.2'
_TITLE_ = "<<< Price equity DDM charts script >>>"

_TCOLS = ['year', 'rate %', 'no_growth', 'growth']


def print_results():
    floatfmt = ('.0f', '.1f', '.2f', '.2f')
    print('\n--------------------------------------------------------------')
    print('\nVariable future projection')
    print(tabulate(v1, headers=_TCOLS, floatfmt=floatfmt))
    print('\nVariable discount rate')
    print(tabulate(v2, headers=_TCOLS, floatfmt=floatfmt), end='\n\n')


def print_plots():
    lp = ddm.get_last_price()
    pl1 = IO.Plotter(xl=('Year',), yl=('Fair value',), x_zero=(lp,))
    pl1.lplot(0, v1[:, 0], v1[:, 2], color='k', linewidth=2., label='no_growth')
    pl1.lplot(0, v1[:, 0], v1[:, 3], color='b', linewidth=2., label='growth')
    pl1.plot()

    pl2 = IO.Plotter(xl=('Discount rate',), yl=('Fair value',), x_zero=(lp,))
    pl2.lplot(0, v2[:, 1], v2[:, 2], color='k', linewidth=2., label='no_growth')
    pl2.lplot(0, v2[:, 1], v2[:, 3], color='b', linewidth=2., label='growth')
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
    print('\nVariable number of projection years')
    n = inh.input("Number of points (years) (default: 6): ", idesc='int',
                  default=6, optional=True)
    dr = inh.input("Give discount rate (default: 7%): ",
                   idesc='float', default=.07, optional=True)
    print('\nVariable value of discount rate')
    r = inh.input("Number of points (discount rate) (default: 10): ", idesc='int',
                  default=10, optional=True)
    fp = inh.input("Give number of projection years (default: 5): ",
                   idesc='int', default=5, optional=True)

    # Calculations
    v1 = np.zeros((n, 4))
    for p in range(1, n + 1):
        ddm = DividendDiscountModel(cmp, future_proj=p)
        res = ddm.result(d_rate=dr)
        v1[p - 1, 0] = curr_year + p
        v1[p - 1, 1] = dr * 100.
        v1[p - 1, 2] = res.fair_value_no_growth
        v1[p - 1, 3] = res.fair_value_with_growth

    ddm = DividendDiscountModel(cmp, future_proj=fp)
    v2 = np.zeros((r, 4))
    for p in range(1, r + 1):
        res = ddm.result(d_rate=p / 100.)
        v2[p - 1, 0] = curr_year + fp
        v2[p - 1, 1] = p
        v2[p - 1, 2] = res.fair_value_no_growth
        v2[p - 1, 3] = res.fair_value_with_growth

    print_results()
    print_plots()

    print('All done!')
