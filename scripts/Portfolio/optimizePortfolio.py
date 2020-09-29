#
# Optimize Portfolio Script
# Script to optimize a given portfolio.
#

from tabulate import tabulate
from nfpy.DB.DB import get_db_glob
from nfpy.Handlers.AssetFactory import get_af_glob
from nfpy.Handlers.Plotting import PlotOptimizerResult
from nfpy.Handlers.QueryBuilder import get_qb_glob
from nfpy.Handlers.Calendar import get_calendar_glob
from nfpy.Tools.Utilities import import_symbol
from nfpy.Handlers.Inputs import InputHandler

__version__ = '0.1'
_TITLE_ = "<<< Optimize a portfolio script >>>"

_OPT_H = ['Idx', 'Name', 'Module']
_OPTIMIZERS = [(0, 'Efficient Frontier', 'MarkowitzModel'),
               (1, 'Min Variance', 'MinimalVarianceModel'),
               (2, 'Max Sharpe', 'MaxSharpeModel'),
               (3, 'Risk Parity', 'RiskParityModel')]


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = get_db_glob()
    qb = get_qb_glob()
    af = get_af_glob()
    cal = get_calendar_glob()
    inh = InputHandler()

    start = inh.input("Give a start date: ", idesc='str')
    end = inh.input("Give an end date: ", idesc='str')
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
    idx_l = inh.input("\nChoose optimizers indices (comma separated): ", idesc='int', is_list=True)

    pl = PlotOptimizerResult()
    for idx in idx_l:
        module = _OPTIMIZERS[idx][2]
        symbol = '.'.join(['nfpy.Portfolio.Optimizer', module, module])
        model = import_symbol(symbol)
        opt = model(ptf)
        print(opt.result)
        res = opt.result
        pl.add('pl', res)

    pl.plot()
    pl.show()

    print("All done!")
