#
# Optimize Portfolio Script
# Script to optimize a given portfolio.
#

import numpy as np
from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
from nfpy.Financial.Portfolio import PortfolioEngine
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

__version__ = '0.5'
_TITLE_ = "<<< Optimize a portfolio script >>>"

_OPT_H = ['Idx', 'Name', 'Module']
_OPTIMIZERS = [(0, 'Efficient Frontier', 'MarkowitzModel'),
               (1, 'Min Variance', 'MinimalVarianceModel'),
               (2, 'Max Sharpe', 'MaxSharpeModel'),
               (3, 'Risk Parity', 'RiskParityModel'),
               (4, 'Capital Asset Line', 'CALModel')]
_PLT_STYLE = {
    'Markowitz': (
        'plot',
        {'linestyle': '-', 'linewidth': 2., 'marker': '',
         'color': 'C0', 'label': 'EffFrontier'}
    ),
    'MaxSharpe': (
        'scatter',
        {'marker': 'o', 'color': 'C1', 'label': 'MaxSharpe'}
    ),
    'MinVariance': (
        'scatter',
        {'marker': 'o', 'color': 'C2', 'label': 'MinVariance'}
    ),
    'RiskParity': (
        'scatter',
        {'marker': 'o', 'color': 'C4', 'label': 'RiskParity'}
    ),
    'CALModel': (
        'plot',
        {'linestyle': '-', 'linewidth': 2., 'marker': '',
         'color': 'C0', 'label': 'EffFrontier'}
    ),
}

if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    af = get_af_glob()
    cal = get_calendar_glob()
    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    start = inh.input("Give a start date: ", idesc='timestamp')
    end = inh.input("Give an end date (default today): ",
                    idesc='timestamp', default=today(mode='timestamp'))
    cal.initialize(end, start=start)

    q = "select * from Assets where type = 'Portfolio'"
    ptfs = db.execute(q).fetchall()

    f = list(qb.get_fields('Assets'))
    print(
        f'Available portfolios:\n'
        f'{tabulate(ptfs, headers=f, showindex=True)}',
        end='\n\n'
    )
    idx = inh.input("Give a portfolio index: ", idesc='index',
                    limits=(0, len(ptfs) - 1))

    print(
        f'\nAvailable optimizers:\n'
        f'{tabulate(_OPTIMIZERS, headers=_OPT_H, showindex=False)}',
        end='\n\n'
    )
    idx_opt = inh.input("Choose the optimizer index: ", idesc='index',
                        limits=(0, len(_OPTIMIZERS) - 1))

    gamma = inh.input("Enter gamma for L2 regularization (default 0): ",
                      idesc='float', default=.0)
    budget = inh.input("Enter the budget in [-1., 1.] (default 1.): ",
                       idesc='float', default=1.)
    iterations = inh.input("Enter iterations: ", idesc='int', default=50)

    ptf = af.get(ptfs[idx][0])
    pe = PortfolioEngine(ptf)
    res = pe.optimize(
        _OPTIMIZERS[idx_opt][2],
        {
            'gamma': gamma,
            'iterations': iterations,
            'budget': budget,
        }
    )

    # Results
    Ut.print_header(f'\n\nResults', end='\n\n')

    if not res.success:
        Ut.print_wrn(Warning('The optimization did not succeed!'))
        exit()

    if res.len == 1:
        wgts = res.weights[0]
        curr_wgts = pe.weights
        diffs = wgts - curr_wgts[:-1]

        Ut.print_highlight('Optimized weights', end='\n\n')
        print(
            f'{"Instrument":<12} | {"Opt. wgt":^8} | {"wgt":^6} | {"diff":^6}\n'
            f'{"-" * 41}'
        )
        for i in range(wgts.shape[0]):
            print(
                f'{res.labels[i]:<12} | {wgts[i]:>8.1%} | {curr_wgts[i]:>6.1%}'
                f' | {diffs[i]:>6.1%}'
            )
        print(
            f'{"-" * 41}\n'
            f'{"abs(sum(w))":<12} | {np.abs(np.sum(wgts)):>8.2f} | '
            f'{np.abs(np.sum(curr_wgts)):>6.2f} |\n'
            f'{"sum(w)":<12} | {np.sum(wgts):>8.2f} | {np.sum(curr_wgts):>6.2f} |\n',
            end='\n\n'
        )

    pl = IO.PtfOptimizationPlot(x_zero=(.0,), y_zero=(.0,))

    model = res.model
    call, kw = _PLT_STYLE[model]
    pl.add(0, call, res, **kw)

    pl.plot()
    pl.show()

    Ut.print_ok('All done!')
