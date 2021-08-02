#
# Equity returns analysis
# Tool to analyse equity returns
#

import numpy as np
from matplotlib import pyplot as plt
from scipy.stats import norm, probplot, cauchy
from tabulate import tabulate

from nfpy.Assets import get_af_glob
from nfpy.Calendar import (get_calendar_glob, today)
import nfpy.DB as DB
import nfpy.IO as IO

plt.interactive(False)
plt.style.use('seaborn')

__version__ = '0.2'
_TITLE_ = "<<< Equity returns analysis script >>>"


def _gen_sample():
    for r in eq_list:
        yield af.get(r)


def analyze():
    ret = np.zeros(0)
    for eq in _gen_sample():
        ret = np.concatenate((ret, eq.returns.dropna().values))

    edges = np.histogram_bin_edges(ret, bins=bins)
    mids = edges[:-1] + .5 * np.diff(edges)
    b, edge = np.histogram(ret, bins=bins, density=True)

    n_p = norm.fit(ret)
    c_p = cauchy.fit(ret)

    print(f'Gaussian  loc= {n_p[0]:.2%}\tscale= {n_p[1]:.2%}\n'
          f'Lorentian loc= {c_p[0]:.2%}\tscale= {c_p[1]:.2%}')

    y_n = norm.pdf(mids, *n_p)
    y_c = cauchy.pdf(mids, *c_p)
    diff_n = (y_n - b)
    diff_c = (y_c - b)

    pt, line = probplot(ret, dist=norm, fit=True)
    lx = np.array([np.min(pt[0]), np.max(pt[0])])
    ly = line[0] * lx + line[1]

    return ret, b, y_n, y_c, diff_n, diff_c, pt, lx, ly, mids


def plot():
    ret, b, y_n, y_c, diff_n, diff_c, pt, lx, ly, mids = analysis

    fig = plt.figure(constrained_layout=True)
    gs = fig.add_gridspec(2, 2)
    ax1 = fig.add_subplot(gs[0, 0])
    _ = ax1.hist(ret, bins=bins, density=True)
    _ = ax1.plot(mids, y_n, linewidth=2.)
    _ = ax1.plot(mids, y_c, linewidth=2.)

    ax2 = fig.add_subplot(gs[1, 0])
    _ = ax2.plot(mids, diff_n, color='C1')
    _ = ax2.plot(mids, diff_c, color='C2')

    ax3 = fig.add_subplot(gs[:, 1])
    _ = ax3.scatter(pt[0], pt[1], color='C0', alpha=.5)
    _ = ax3.plot(lx, ly, color='C2')

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = get_af_glob()
    qb = DB.get_qb_glob()
    db = DB.get_db_glob()
    inh = IO.InputHandler()

    start_date = inh.input("Give starting date for time series: ", idesc='datetime')
    if not start_date:
        raise ValueError('You must give a starting date.')

    end_date = inh.input("Give ending date for time series (default <today>): ",
                         default=today(), idesc='timestamp')
    get_calendar_glob().initialize(end_date, start_date)

    msg = "Give a list of equities (press Enter for a list): "
    eq_list = inh.input(msg, optional=True, is_list=True)
    if not eq_list:
        q = "select * from Assets where type = 'Equity'"
        res = db.execute(q).fetchall()

        f = list(qb.get_fields('Assets'))
        print(f'\n\nAvailable equities:\n'
              f'{tabulate(res, headers=f, showindex=True)}',
              end='\n\n')
        idx_list = inh.input("Give a list of  equity indices: ",
                             idesc='int', is_list=True, optional=False)
        eq_list = tuple(res[i][0] for i in idx_list)

    bins = inh.input("Give number of bins (default 10): ",
                     default=10, idesc='int')

    analysis = analyze()
    plot()

    print('All done!')
