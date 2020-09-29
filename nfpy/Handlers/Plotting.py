#
# Plotting class
# Class to handle plots in a standardized way across the library
#

from abc import ABCMeta, abstractmethod
from math import inf
from typing import Union, Sized
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from nfpy.Portfolio.Optimizer.BaseOptimizer import OptimizerResult

# plt.ioff()


class Plotting(metaclass=ABCMeta):
    """ Creates a defined environment. """

    def __init__(self, xl: str = '', yl: str = '', zero: float = None):
        # Inputs variables
        self._xlim = [inf, -inf]
        self._ylim = [inf, -inf]
        self._xl = xl
        self._yl = yl
        self._zero = zero
        self._use_zero = False

        # Working variables
        self._plots = []
        self._fig = None
        self._ax = None

        self._init()

    def _init(self):
        fig, ax = plt.subplots()
        self._fig = fig
        self._ax = ax

        if self._zero is not None:
            self._use_zero = True

    def save(self, f_name: str):
        """ Call the savefig() method. """
        self._fig.savefig(f_name)

    @abstractmethod
    def add(self, *args, **kwargs):
        """ Add more plots to be plotted. """

    @abstractmethod
    def plot(self):
        """ Creates the figure. """

    @staticmethod
    def show():
        """ Show the figure to screen. """
        plt.show()

    @staticmethod
    def clf():
        """ Call plt.clf(). """
        plt.clf()


class PlotVarRet(Plotting):
    """ Creates a variance/return plot. """

    def add(self, x: Union[float, Sized], y: Union[float, Sized], label: str = None, **kwargs):
        """ Add more plots to be plotted. """
        pl = (x, y, label, kwargs)
        self._plots.append(pl)

    def plot(self):
        """ Creates the figure. """
        ax = self._ax
        for x, y, l, kw in self._plots:
            if isinstance(x, Sized):
                if len(x) != len(y):
                    raise RuntimeError('Size of x and y mismatch in {}'.format(self.__name__))

                ax.scatter(x, y, **kw)
                if l:
                    ax.text(x, y, s=l, fontsize=6, fontvariant='small-caps', **kw)
            elif isinstance(x, float):
                ax.scatter(x, y, **kw)
                if l:
                    ax.text(x, y, s=l, fontsize=6, fontvariant='small-caps', **kw)
            else:
                raise TypeError('Data type not recognized in {} class'.format(self.__name__))

        if self._use_zero:
            plt.axvline(c='k', linewidth=.5)
            plt.axhline(self._zero, c='k', linewidth=.5)
        plt.xlabel('Variance')
        plt.ylabel('Return')


class PlotLine(Plotting):
    """ Creates a line plot. """

    def add(self, x: Union[pd.Series, np.array], y: np.array = None, **kwargs):
        """ Add more plots to be plotted. """
        if isinstance(x, pd.Series):
            x = x.values
            y = x.index
        pl = (x, y, kwargs)
        self._plots.append(pl)

    def plot(self):
        """ Creates the figure. """
        ax = self._ax
        for x, y, kw in self._plots:
            ax.plot(x, y, **kw)

        if self._use_zero:
            plt.axhline(self._zero, c='k', linewidth=.5)
        plt.xlabel(self._xl)
        plt.ylabel(self._yl)
        plt.legend()


class PlotTS(Plotting):
    """ Creates a time series plot. """

    def add(self, x: Union[pd.Series, np.array], y: np.array = None, **kwargs):
        """ Add more plots to be plotted. """
        # if not isinstance(data, pd.Series):
        #     raise TypeError('Plotting class expects Series for plotting time series')
        if isinstance(x, pd.Series):
            _v = x
            x = _v.index
            y = _v.values
        # pl = (data, kwargs)
        pl = (x, y, kwargs)
        self._plots.append(pl)

    def plot(self):
        """ Creates the figure. """
        ax = self._ax
        for x, y, kw in self._plots:
            ax.plot(x, y, **kw)
        # for data, kw in self._plots:
        #     data.plot(ax=ax, **kw)

        if self._use_zero:
            plt.axhline(self._zero, c='k', linewidth=.5)
        plt.xlabel('Date')
        plt.ylabel('Price')


class PlotBeta(Plotting):
    """ Creates a beta plot. """

    _COLORS = (('cornflowerblue', 'blue'), ('salmon', 'red'), ('lime', 'green'), ('silver', 'grey'))

    def add(self, index: pd.Series, instrument: pd.Series, params: tuple, **kwargs):
        """ Add more plots to be plotted. """
        if len(self._plots) == 4:
            raise RuntimeError('Already enough regression plot')
        if not isinstance(index, pd.Series) or not isinstance(instrument, pd.Series):
            raise TypeError('Plotting class expects Series for plotting time series')
        pl = (index, instrument, params, kwargs)
        self._plots.append(pl)

    def plot(self):
        """ Creates the figure. """
        # ax = self._ax
        for n, data in enumerate(self._plots):
            idx, instr, params, kw = data
            sc, rc = self._COLORS[n]
            x = np.linspace(min(np.min(idx), .0), np.max(idx), 2)
            y = params[0] * x + params[1]
            plt.scatter(idx, instr, color=sc, **kw)
            if 'label' in kw:
                del kw['label']
            plt.plot(x, y, color=rc, linewidth=2., **kw)

        if self._use_zero:
            plt.axhline(self._zero, c='k', linewidth=.5)
            plt.axvline(c='k', linewidth=.5)
        plt.xlabel('Index returns')
        plt.ylabel('Equity returns')
        plt.legend()


class PlotOptimizerResult(Plotting):
    """ Creates a variance/return plot from a OptimizerResult object. """

    def add(self, res: OptimizerResult, **kwargs):
        """ Add more plots to be plotted. """
        pl = (res, kwargs)
        self._plots.append(pl)

    def plot(self):
        """ Creates the figure. """
        ax = self._ax
        for r, kw in self._plots:
            ax.scatter(r.ptf_variance, r.ptf_return, **kw)
            ax.scatter(r.const_var, r.const_ret, **kw)
            # ax.text(var, ret, s=uids, fontsize=6, fontvariant='small-caps')

        if self._use_zero:
            plt.axvline(c='k', linewidth=.5)
            plt.axhline(self._zero, c='k', linewidth=.5)
        plt.xlabel('Variance')
        plt.ylabel('Return')
        plt.legend()
