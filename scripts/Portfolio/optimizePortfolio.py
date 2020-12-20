#
# Optimize Portfolio Script
# Script to optimize a given portfolio.
#

from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

__version__ = '0.3'
_TITLE_ = "<<< Optimize a portfolio script >>>"

_OPT_H = ['Idx', 'Name', 'Module']
_OPTIMIZERS = [(0, 'Efficient Frontier', 'MarkowitzModel'),
               (1, 'Min Variance', 'MinimalVarianceModel'),
               (2, 'Max Sharpe', 'MaxSharpeModel'),
               (3, 'Risk Parity', 'RiskParityModel'),
               (4, 'Capital Asset Line', 'CALModel')]


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    af = get_af_glob()
    cal = get_calendar_glob()
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
    uid = inh.input("\nGive a portfolio index: ", idesc='int')
    ptf = af.get(res[uid][0])

    print('\n\nAvailable optimizers:')
    print(tabulate(_OPTIMIZERS, headers=_OPT_H, showindex=False))
    idx_l = inh.input("\nChoose optimizers indices (comma separated): ",
                      idesc='int', is_list=True)

    pl = IO.PlotPortfolioOptimization()
    for idx in idx_l:
        module = _OPTIMIZERS[idx][2]
        symbol = '.'.join(['nfpy.Portfolio.Optimizer', module, module])
        model = Ut.import_symbol(symbol)
        opt = model(ptf)
        res = opt.result

        if idx == 0:
            label, marker = 'EF ', 'o'
        elif idx == 1:
            label, marker = 'MinVar ', 'd'
        elif idx == 2:
            label, marker = 'Sharpe ', 'x'
        elif idx == 3:
            label, marker = 'RP ', 'x'
        else:
            label, marker = 'CAL ', 'o'
        pl.add(res, label=label + 'no gamma', marker=marker)

    pl.plot()
    pl.show()

    print("All done!")
