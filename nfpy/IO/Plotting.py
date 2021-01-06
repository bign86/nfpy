#
# Plotting class
# Class to handle plots in a standardized way across the library
#

from abc import ABCMeta
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import (Union, Sequence)

from nfpy.Financial.Optimizer import OptimizerResult

plt.style.use('seaborn')
# print(plt.style.library['seaborn'])


class Plotting(metaclass=ABCMeta):
    """ Creates a defined environment. """

    _RC = {}
    _RC_TEXT = {}
    _RC_AXIS = {'c': 'k', 'linewidth': .5}

    def __init__(self, ncols: int = 1, nrows: int = 1, xl: str = '',
                 yl: str = '', x_zero: float = None, y_zero: float = None,
                 xlim: Sequence = (), ylim: Sequence = ()):
        # Inputs variables
        self._ncols = int(ncols)
        self._nrows = int(nrows)
        self._xl = str(xl)
        self._yl = str(yl)
        self._x_zero = x_zero
        self._y_zero = y_zero
        self._xlim = xlim
        self._ylim = ylim

        # Working variables
        self._annotations = []
        self._plots = []
        self._lines = []
        self._fig = None
        self._ax = None

        self._initialize()

    def _initialize(self):
        fig, ax = plt.subplots(self._ncols, self._nrows)
        self._fig = fig
        self._ax = ax

    def __del__(self):
        self.close()

    def save(self, f_name: str, fmt: str = 'png'):
        """ Call the savefig() method. """
        self._fig.tight_layout()
        self._fig.savefig(f_name, format=fmt)

    def add(self, x: Union[pd.Series, np.array], y: np.array = None, **kwargs):
        """ Add more plots to be plotted. """
        if isinstance(x, pd.Series):
            _v = x
            x, y = _v.index, _v.values
        self._plots.append((x, y, kwargs))

    def annotate(self, x: Union[pd.Series, np.array], y: np.array = None,
                 labels: Sequence = (), **kwargs):
        if isinstance(x, pd.Series):
            _v = x
            x, y = _v.index, _v.values
        self._annotations.append((x, y, labels, kwargs))

    def line(self, type_: str, v: Union[float, np.array], range_: tuple = (),
             **kwargs):
        self._lines.append((type_, v, range_, kwargs))

    def plot(self):
        """ Creates the figure. """
        ax1, legend = self._ax, False
        ax2, lp = None, []
        for x, y, kw in self._plots:
            try:
                secondary = kw['secondary_y']
                if secondary:
                    if not ax2:
                        ax2 = ax1.twinx()
                    ax2.set_ylabel(kw['label'])
                    ax2.legend(kw['label'])
                    ax = ax2
                else:
                    ax = ax1
                del kw['secondary_y']
            except KeyError:
                ax = ax1

            rc = self._RC.copy()
            rc.update(kw)
            leg = ax.plot(x, y, **rc)

            if 'label' in rc:
                legend = True
                lp.append(leg[0])

        for mode, val, rng, kw in self._lines:
            if mode == 'xh':
                leg = ax1.axhline(val, **kw)
            elif mode == 'xv':
                leg = ax1.axvline(val, **kw)
            elif mode == 'h':
                leg = ax1.hlines(val, *rng, **kw)
            else:
                leg = ax1.vlines(val, *rng, **kw)
            if 'label' in kw:
                legend = True
                lp.append(leg)

        # if self._use_zero:
        if self._x_zero is not None:
            ax1.axvline(self._x_zero, **self._RC_AXIS)
        if self._y_zero is not None:
            ax1.axhline(self._y_zero, **self._RC_AXIS)

        ax1.set_xlabel(self._xl)
        ax1.set_ylabel(self._yl)

        if legend:
            ax1.legend(lp, [l.get_label() for l in lp])

    @staticmethod
    def show():
        """ Show the figure to screen. """
        plt.tight_layout()
        plt.show()

    @staticmethod
    def clf():
        """ Call plt.clf(). """
        plt.clf()

    @staticmethod
    def cla():
        """ Call plt.cla(). """
        plt.cla()

    def close(self, close_all: bool = False):
        """ Call plt.close(). """
        s = 'all' if close_all else self._fig
        plt.close(s)


class PlotLine(Plotting):
    """ Creates a line plot. """

    _RC = {'linestyle': '-', 'marker': ''}


class PlotTS(Plotting):
    """ Creates a time series plot. """

    _RC = {'linestyle': '-', 'marker': ''}

    def __init__(self, ncols: int = 1, nrows: int = 1, xl: str = 'Date',
                 yl: str = 'Price', x_zero: float = None, y_zero: float = None,
                 xlim: Sequence = None, ylim: Sequence = None):
        super().__init__(ncols, nrows, xl, yl, x_zero, y_zero, xlim, ylim)


class PlotBeta(Plotting):
    """ Creates a beta plot. """

    _RC = {'linestyle': '-', 'marker': 'o', 'alpha': .5}
    _RC_BETA = {'linestyle': '-', 'marker': '', 'linewidth': 2.,
                'label': r'$\beta={:.2}$'}

    def __init__(self, ncols: int = 1, nrows: int = 1,
                 xl: str = 'Index returns', yl: str = 'Equity returns',
                 x_zero: float = None, y_zero: float = None,
                 xlim: Sequence = None, ylim: Sequence = None):
        super().__init__(ncols, nrows, xl, yl, x_zero, y_zero, xlim, ylim)

    def add(self, x: Union[pd.Series, np.array], y: np.array = None,
            params: Sequence = (), kw_line: dict = None, **kwargs):
        """ Add more plots to be plotted. """
        if len(self._plots) == 4:
            raise RuntimeError('Already enough regression plot')

        if isinstance(x, pd.Series):
            _v = x
            x, y = _v.index, _v.values
        self._plots.append((x, y, params, kw_line, kwargs))

    def plot(self):
        """ Creates the figure. """
        ax = self._ax
        for x, y, params, kw_line, kw in self._plots:
            rc = self._RC.copy()
            rc.update(kw)
            ax.scatter(x, y, **rc)

            xg = np.linspace(min(float(np.nanmin(x)), .0),
                             float(np.nanmax(x)), 2)
            yg = params[0] * xg + params[1]
            rc_line = self._RC_BETA.copy()
            kw_line = {} if not kw_line else kw_line
            rc_line.update(kw_line)
            try:
                rc_line['label'] = rc_line['label'].format(params[0])
            except KeyError:
                pass
            ax.plot(xg, yg, **rc_line)

        # if self._use_zero
        if self._y_zero is not None:
            ax.axhline(self._y_zero, **self._RC_AXIS)
            ax.axvline(**self._RC_AXIS)

        ax.set_xlabel(self._xl)
        ax.set_ylabel(self._yl)

        if self._xlim:
            ax.set_xlim(self._xlim)
        if self._ylim:
            ax.set_ylim(self._ylim)

        ax.legend()


class PlotVarRet(Plotting):
    """ Creates a variance/return plot. """

    _RC = {'linestyle': '-', 'marker': 'o'}
    _RC_TEXT = {'fontsize': 8, 'fontvariant': 'small-caps'}

    def __init__(self, ncols: int = 1, nrows: int = 1, xl: str = 'Variance',
                 yl: str = 'Return', x_zero: float = None, y_zero: float = None,
                 xlim: Sequence = None, ylim: Sequence = None):
        super().__init__(ncols, nrows, xl, yl, x_zero, y_zero, xlim, ylim)

    def plot(self):
        """ Creates the figure. """
        ax, labels_flag = self._ax, False
        for x, y, kw in self._plots:
            rc = self._RC.copy()
            rc.update(kw)
            ax.plot(x, y, **rc)

        for x, y, l, kw in self._annotations:
            rc = self._RC.copy()
            rc.update(kw)
            ax.scatter(x, y, **rc)
            for i, k in enumerate(l):
                ax.annotate(k, (x[i], y[i]), **self._RC_TEXT)

        if self._y_zero is not None:
            ax.axhline(self._y_zero, **self._RC_AXIS)
            ax.axvline(**self._RC_AXIS)

        ax.set_xlabel(self._xl)
        ax.set_ylabel(self._yl)

        ax.legend(loc=2, fancybox=True, framealpha=0.1)


class PlotPortfolioOptimization(PlotVarRet):
    """ Creates a variance/return plot from a OptimizerResult object. """

    def add(self, res: OptimizerResult, **kwargs):
        """ Add more plots to be plotted. """
        self._plots.append((res, kwargs))

    def plot(self):
        """ Creates the figure. """
        r = self._plots[0][0]
        self._annotations = [(r.const_var, r.const_ret, r.uids, {'marker': 'x'})]

        plots = []
        for r, kw in self._plots:
            x = np.array(r.ptf_variance)
            y = np.array(r.ptf_return)
            plots.append((x, y, kw))
        self._plots = plots

        super().plot()
