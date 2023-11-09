#
# Price Details Dividend Discount Model
# Calculate the fair value of company with the Dividend Discount Model and
# show calculation details.
#

import argparse
import numpy as np
import pandas as pd
from typing import Optional

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
from nfpy.Financial import DDM
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

np.set_printoptions(precision=3, suppress=True)

__version__ = '0.3'
_TITLE_ = "<<< Price equity DDM details script >>>"
_DESC_ = """Calculates the fair value of a single company using the DDM methodology."""

_TCOLS = ['year', 'no_growth', 'growth']

_ARGS_BLOCKS_ = [
    {'interactive': True},
    {
        'uid': None,
        's1': None
    }
]


def build_stage(_input) -> Optional[tuple]:
    n = len(_input)
    if n == 0:
        return None

    _duration = int(_input[0])

    _growth = None
    if (n > 1) and (_input[1].lower() != 'none'):
        _growth = float(_input[1])

    _is_h = False
    if (n > 2) and (_input[2].lower() != 'none'):
        _is_h = Ut.to_bool(_input[2])

    return _duration, _growth, _is_h


def print_results(_r, _in):
    ke_str = '-' if _r.ke is None else f'{_r.ke:>6.1%}'
    premium_str = '-' if _in["premium"] is None else f'{_in["premium"]:>6.1%}'

    print(f'\n----------------------------------------\n'
          f'********** {"Input information":^18} **********\n'
          f'Company:\t\t\t\t\t{_r.uid:>6}\n'
          f'Last price:\t\t\t\t\t{_r.last_price:>6.2f} {_r.ccy}\n'
          f'Stages:\t\t\t\t\t\t{_in["num_stages"]:>6}\n\n'
          f'---------- {"Implied measures":^18} ----------\n'
          f'Impl. cost of equity:\t\t{_r.implied_ke:>6.1%}\n'
          f'Impl. long term premium:\t{_r.implied_lt_premium:>6.1%}\n'
          f'Impl. short term premium:\t{_r.implied_st_premium:>6.1%}\n\n'
          f'********** {"General results":^18} **********\n'
          f'LT growth:\t\t\t\t\t{_r.lt_growth:>6.1%}\n'
          f'Cost of equity:\t\t\t\t{ke_str}\n'
          f'Premium:\t\t\t\t\t{premium_str}\n\n'
          f'********** {"Results":^18} **********\n'
          f'---------- {"No growth":^18} ----------\n'
          f'Fair value:\t\t\t\t\t{_r.no_growth["fv"]:>6.2f}\n'
          f'Return:\t\t\t\t\t\t{_r.no_growth["ret"]:>6.1%}\n')

    if 'manual' in _r:
        print(f'---------- {"Manual":^18} ----------\n'
              f'ST growth:\t\t\t\t\t{_r.manual_growth["st_gwt"]:>6.1%}\n'
              f'Fair value:\t\t\t\t\t{_r.manual_growth["fv"]:>6.2f} {_r.ccy}\n'
              f'Return:\t\t\t\t\t\t{_r.manual_growth["ret"]:>6.1%}\n')

    if 'historical_growth' in _r:
        print(f'---------- {"Historical":^18} ----------\n'
              f'ST growth:\t\t\t\t\t{_r.historical_growth["st_gwt"]:>6.1%}\n'
              f'Fair value:\t\t\t\t\t{_r.historical_growth["fv"]:>6.2f} {_r.ccy}\n'
              f'Return:\t\t\t\t\t\t{_r.historical_growth["ret"]:>6.1%}\n')

    if 'ROE_growth' in _r:
        print(f'---------- {"ROE":^18} ----------\n'
              f'ST growth:\t\t\t\t\t{_r.ROE_growth["st_gwt"]:>6.1%}\n'
              f'Fair value:\t\t\t\t\t{_r.ROE_growth["fv"]:>6.2f} ({_r.ccy})\n'
              f'Return:\t\t\t\t\t\t{_r.ROE_growth["ret"]:>6.1%}\n')


def plot_results(_r, _df):
    yearly_div_dt, yearly_div = _df.annual_dividends
    yearly_ret_div = yearly_div[1:] / yearly_div[:-1] - 1.
    yearly_div_dt = yearly_div_dt + np.timedelta64(6, 'M')
    all_div_dt, all_div = _df.all_dividends
    ret_div = all_div[1:] / all_div[:-1] - 1.

    pl = IO.Plotter(xl=('Date',), yl=(f'Price ({_r.ccy})',), x_zero=[.0]) \
        .lplot(0, yearly_div_dt, yearly_div, color='k',
               marker='o', label='yearly paid divs.') \
        .lplot(0, _r.div_ts, color='gray',
               marker='X', linestyle='--', label='paid divs.') \
        .lplot(0, _r.dates, y=_r.no_growth['cf'][1],
               color='C0', label='no growth')

    if 'manual_growth' in _r:
        pl.lplot(0, _r.dates, y=_r.manual_growth['cf'][1],
                 color='C1', label='manual')

    if 'historical_growth' in _r:
        pl.lplot(0, _r.dates, y=_r.historical_growth['cf'][1],
                 color='C2', label='historical')

    if 'ROE_growth' in _r:
        pl.lplot(0, _r.dates, y=_r.ROE_growth['cf'][1],
                 color='C3', label='ROE')

    pl.plot()

    pl2 = IO.Plotter(xl=('Date',), yl=(f'Rate',), x_zero=[.0]) \
        .lplot(0, yearly_div_dt[1:], yearly_ret_div,
               color='k', marker='o', label='yearly divs. growth') \
        .lplot(0, all_div_dt[1:], ret_div, color='gray',
               marker='X', linestyle='--', label='divs. growth')

    if 'manual_growth' in _r:
        pl2.lplot(0, _r.dates, y=_r.manual_growth['rates'],
                  color='C1', label='manual')

    if 'historical_growth' in _r:
        pl2.lplot(0, _r.dates, y=_r.historical_growth['rates'],
                  color='C2', label='historical')

    if 'ROE_growth' in _r:
        pl2.lplot(0, _r.dates, y=_r.ROE_growth['rates'],
                  color='C3', label='ROE')

    pl2.plot()
    pl.show()
    pl2.show()


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
        '-H', '--history-w', type=int, dest='history',
        help='Window length in years for the dividends', default=10
    )
    parser.add_argument(
        '-k', '--ke', type=float, dest='ke', help='Cost of equity'
    )
    parser.add_argument(
        '-p', '--premium', type=float, dest='premium',
        help='Premium required by the investor above the current inflation or cost of equity'
    )
    parser.add_argument(
        '-d', '--ddm-stage1', nargs='+', type=str, dest='s1',
        help='DDM stage 1 as <duration> <dividend growth> <is_H-model>'
    )
    parser.add_argument(
        '-D', '--ddm-stage2', nargs='+', type=str, dest='s2',
        help='DDM stage 2 as <duration> <dividend growth> <is_H-model>'
    )
    parser.add_argument(
        '--use-roe', action='store_true', dest='use_roe',
        help='Employ the ROE methodology to calculate growth',
    )
    parser.add_argument(
        '--use-historical', action='store_true', dest='use_hist',
        help='Employ the Historical methodology to calculate growth',
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

    Ut.check_mandatory_args(_ARGS_BLOCKS_, args)

    if args.interactive is True:
        inh = IO.InputHandler()

        uid = inh.input('Insert:\n > UID: ', idesc='uid')
        history = inh.input(' > length of historical data in years: ', idesc='int')
        ke = inh.input(' > cost of equity (default None): ', idesc='float',
                       default=None, optional=True)
        premium = inh.input(' > premium (default None): ', idesc='float',
                            default=None, optional=True)
        infl_w = inh.input(' > years of inflation history (default 20): ',
                           idesc='int', default=20, optional=True)
        gdp_w = inh.input(' > years of GDP history (default 20): ',
                          idesc='int', default=20, optional=True)
        use_hist = inh.input(' > use Historical model of growth? (default False): ',
                             idesc='bool', default=False, optional=True)
        use_roe = inh.input(' > use ROE model of growth? (default False): ',
                            idesc='bool', default=False, optional=True)
        msg = f'\nDDM Stages:\n > fist stage as a list of:\n\tstage duration [mandatory]\n' \
              f'\tdividend growth [optional]\n\tis H-model [optional]\n' \
              f'   input must be given as a list, leave blank for no stage: '
        s1 = inh.input(msg, idesc='str', is_list=True, default=[], optional=True)
        msg = f' > second stage if needed, defined as above: '
        s2 = inh.input(msg, idesc='str', is_list=True, default=[], optional=True)

    else:
        uid = args.uid
        history = args.history
        ke = args.ke
        premium = args.premium
        infl_w = args.infl_w
        gdp_w = args.gdp_w
        use_hist = args.use_hist
        use_roe = args.use_roe
        s1 = args.s1
        s2 = args.s2

    # Create the tuples for the stages with the right variable type
    s1 = build_stage(s1) if s1 else None
    s2 = build_stage(s2) if s2 else None

    # Handle growth modes
    gwt_mode = []
    if use_hist:
        gwt_mode.append('historical')
    if use_roe:
        gwt_mode.append('ROE')

    # Calculate how far back we need to go with the daily calendar
    min_history = 0
    if s1 is not None:
        min_history += s1[0]
    if s2 is not None:
        min_history += s2[0]

    if history < min_history:
        msg = f'History length too short ({history} < {min_history}).' \
              f' Length increased to {min_history}.'
        Ut.print_wrn(Warning(msg))
        history = min_history

    # Calculate the start of the yearly calendar
    yearly_periods = max(infl_w, gdp_w)
    monthly_periods = yearly_periods * 12

    # Calculate the starting date to ensure enough past data are loaded
    end_date = today(mode='datetime')
    curr_year = end_date.year
    start_date = pd.Timestamp(curr_year - history, 1, 1)
    get_calendar_glob().initialize(
        end_date, start_date,
        yearly_periods=yearly_periods,
        monthly_periods=monthly_periods
    )

    # Calculate
    ddm_obj = DDM(uid, s1, s2, gwt_mode=gwt_mode)
    res = ddm_obj.result(cost_equity=ke, premium=premium)

    print_results(res, ddm_obj.inputs)
    plot_results(res, ddm_obj._df)

    Ut.print_ok('All done!')
