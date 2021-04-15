#
# Optimize Portfolio Script
# Script to optimize a given portfolio.
#

from tabulate import tabulate

from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.IO as IO
import nfpy.Models as Mod

__version__ = '0.4'
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
}

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    cal = get_calendar_glob()
    db = IO.get_db_glob()
    qb = IO.get_qb_glob()
    inh = IO.InputHandler()

    start = inh.input("Give a start date: ", idesc='timestamp')
    end = inh.input("Give an end date (default today): ",
                    idesc='timestamp', default=today(mode='timestamp'))
    cal.initialize(end, start=start)

    q = "select * from Assets where type = 'Portfolio'"
    f = list(qb.get_fields('Assets'))
    res = db.execute(q).fetchall()

    print('\n\nAvailable portfolios:')
    print(tabulate(res, headers=f, showindex=True))
    idx = inh.input("\nGive a portfolio index: ", idesc='int')
    uid = res[idx][0]

    print('\n\nAvailable optimizers:')
    print(tabulate(_OPTIMIZERS, headers=_OPT_H, showindex=False))
    idx_l = inh.input("\nChoose optimizers indices (comma separated): ",
                      idesc='int', is_list=True)

    algos = {}
    for idx in idx_l:
        algos[_OPTIMIZERS[idx][2]] = {}

    oe = Mod.OptimizationEngine(uid, algorithms=algos)
    res = oe.result

    pl = IO.PtfOptimizationPlot(x_zero=(.0,), y_zero=(.0,))

    for r in res.results:
        if r.success is False:
            continue

        model = r.model
        call, kw = _PLT_STYLE[model]
        pl.add(0, call, r, **kw)

        if model == 'Markowitz':
            continue

    pl.plot()
    pl.show()

    print("All done!")
