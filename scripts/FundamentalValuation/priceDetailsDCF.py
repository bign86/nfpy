#
# Price Details Discounted Cash Flow
# Calculate the fair value of company with the Discounted Cash Flow
# Model plot details.
#

import argparse
import numpy as np
import pandas as pd

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
from nfpy.Financial import DCF
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

np.set_printoptions(precision=3, suppress=True)

__version__ = '0.4'
_TITLE_ = "<<< Price equity DCF details script >>>"
_DESC_ = """Calculates the fair value of a single company using the DCF methodology."""


def print_results(_r):
    perpetual_growth_str = '-' if _r.perpetual_growth is None else f'{_r.perpetual_growth:>6.1%}'
    premium_str = '-' if _r.premium is None else f'{_r.premium:>6.1%}'

    print(f'\n----------------------------------------\n'
          f'********** {"Input information":^18} **********\n'
          f'Company:\t\t\t{_r.uid:>6}\n'
          f'Last price:\t\t\t{_r.last_price:>6.2f} ({_r.ccy})\n'
          f'History:\t\t\t{_r.history:>6}\n'
          f'Projection:\t\t\t{_r.projection:>6}\n'
          f'Growth:\t\t\t\t{perpetual_growth_str}\n'
          f'Premium:\t\t\t{premium_str}\n\n'
          f'********** {"General results":^18} **********\n'
          f'Fair value:\t\t\t{_r.fair_value:>6.2f} ({_r.ccy})\n'
          f'Return:\t\t\t\t{_r.ret:>6.1%}\n'
          f'Cost equity:\t\t{_r.cost_of_equity:>6.1%}\n'
          f'Cost debt:\t\t\t{_r.cost_of_debt:>6.1%}\n'
          f'WACC:\t\t\t\t{_r.wacc:>6.1%}\n'
          f'LT growth:\t\t\t{_r.lt_growth:>6.1%}\n'
          f'Tot growth:\t\t\t{_r.tot_growth:>6.1%}\n',
          end='\n\n')


def plot_results(_r):
    pl = IO.Plotter(xl=('Date',), yl=(f'Amount ({_r.ccy})',), x_zero=[.0]) \
        .lplot(0, _r.fcff_calc.fcf, color='C0', marker='o', alpha=.5, linewidth=.0, label='FCF') \
        .lplot(0, _r.fcff_calc.calc_fcf, color='C0', marker='X', label='FCF Calculated') \
        .lplot(0, _r.fcff_calc.revenues, color='C1', marker='o', label='Revenues') \
        .lplot(0, _r.fcff_calc.cfo, color='C2', marker='o', label='CFO') \
        .lplot(0, _r.fcff_calc.capex, color='C3', marker='o', label='CAPEX') \
        .plot()

    pl2 = IO.Plotter(xl=('Date',), yl=(f'Return ({_r.ccy})',), x_zero=[.0]) \
        .lplot(0, _r.fcff_calc.revenues_returns, color='C1', marker='o', label='Revenues Ret.') \
        .lplot(0, _r.fcff_calc.cfo_cov, color='C2', marker='o', label='CFO Cov.') \
        .lplot(0, _r.fcff_calc.capex_cov, color='C3', marker='o', label='CAPEX Cov.') \
        .plot()

    pl.show()


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n')
    print(_DESC_, end='\n\n')

    # Handlers
    af = get_af_glob()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i', '--interactive', action='store_true', help='use interactively'
    )
    parser.add_argument(
        '-u', '--uid', type=str, dest='uid', help='UID of the company or the equity'
    )
    parser.add_argument(
        '-g', '--growth', type=float, dest='growth',
        help='Perpetual growth rate, if missing defaults to GDP growth plus inflation'
    )
    parser.add_argument(
        '-F', '--forecast', type=int, dest='forecast_w',
        help='Window length in years of projected cash flow',
        default=5
    )
    parser.add_argument(
        '-H', '--history', type=int, dest='history_w',
        help='Window length in years of the company data history to use',
        default=6
    )
    parser.add_argument(
        '-I', '--inflation-w', type=int, dest='infl_w',
        help='Window length in years for the evaluation of inflation',
        default=20
    )
    parser.add_argument(
        '-G', '--gdp-w', type=int, dest='gdp_w',
        help='Window length in years for the evaluation of GDP',
        default=20
    )
    args = parser.parse_args()

    if args.interactive is True:
        inh = IO.InputHandler()

        uid = inh.input("Give a company uid: ", idesc='uid')
        history_w = inh.input(
            "Give number of years of the company data history to use (default: 6): ",
            idesc='int', default=5, optional=True
        )
        forecast_w = inh.input(
            "Give number of years of projected cash flow (default: 5): ",
            idesc='int', default=3, optional=True
        )
        growth = inh.input(
            "Give perpetual growth rate (default None): ",
            idesc='float', default=None, optional=True
        )
        infl_w = inh.input(
            "Window length in years for the evaluation of inflation (default: 20): ",
            idesc='int', default=20, optional=True
        )
        gdp_w = inh.input(
            "Window length in years for the evaluation of GDP (default: 20): ",
            idesc='int', default=20, optional=True
        )

    else:
        uid = args.uid
        growth = args.growth
        infl_w = args.infl_w
        gdp_w = args.gdp_w
        history_w = args.history_w
        forecast_w = args.forecast_w

    # Calculate the start of the yearly calendar
    yearly_periods = max(infl_w, gdp_w)
    monthly_periods = yearly_periods * 12

    # Calculate the starting date to ensure enough past data are loaded
    end_date = today(mode='datetime')
    curr_year = end_date.year
    start_date = pd.Timestamp(curr_year - history_w, 1, 1)
    get_calendar_glob().initialize(
        end_date, start_date,
        yearly_periods=yearly_periods,
        monthly_periods=monthly_periods
    )

    # Calculate
    res = DCF(uid, growth=growth, history=history_w, future_proj=forecast_w) \
        .result()

    print_results(res)
    plot_results(res)

    Ut.print_ok('All done!')
