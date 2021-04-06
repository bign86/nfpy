#
# Plotting class
# Class to handle plots in a standardized way across the library
#

from abc import ABCMeta
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import (Union, Sequence)

plt.style.use('seaborn')


class Plotter(metaclass=ABCMeta):
    """ New plotting class. """

    _RC = {'linestyle': '-', 'marker': ''}
    _RC_AXIS = {'c': 'k', 'linewidth': .5}
    _RC_TEXT = {'fontsize': 8, 'fontvariant': 'small-caps'}

    def __init__(self, ncols: int = 1, nrows: int = 1, xl: Sequence = (),
                 yl: Sequence = (), x_zero: Sequence = (), y_zero: Sequence = (),
                 xlim: Sequence = (), ylim: Sequence = ()):
        # Inputs variables
        self._ncols = int(ncols)
        self._nrows = int(nrows)
        self._xl = tuple(xl)
        self._yl = tuple(yl)
        self._x_zero = x_zero
        self._y_zero = y_zero
        self._xlim = xlim
        self._ylim = ylim

        # Working variables
        self._length = ncols * nrows
        self._annotations = []
        self._plots = []
        self._lines = []
        self._fig = None
        self._ax = None
        self._ax2 = None

        self._initialize()

    def _initialize(self):
        fig, ax = plt.subplots(self._ncols, self._nrows)
        self._fig = fig
        if self._length == 1:
            self._ax = [ax]
        else:
            self._ax = ax
        self._ax2 = [None] * self._length

        if not self._xl:
            self._xl = (None,) * self._length
        if not self._yl:
            self._yl = (None,) * self._length
        if not self._xlim:
            self._xlim = (None,) * self._length
        if not self._ylim:
            self._ylim = (None,) * self._length

    def __del__(self):
        self.close()

    def save(self, f_name: str, fmt: str = 'png'):
        """ Call the savefig() method. """
        self._fig.tight_layout()
        self._fig.savefig(f_name, format=fmt)

    def _get_axes(self, axid: int, secondary: bool):
        if secondary:
            ax = self._ax2[axid]
            if ax is None:
                ax = self._ax[axid].twinx()
                self._ax2[axid] = ax
        else:
            ax = self._ax[axid]
        return ax

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

    def lplot(self, axid: int, x: Union[pd.Series, np.array],
              y: np.array = None, **kwargs):
        if isinstance(x, pd.Series):
            _v = x
            x, y = _v.index, _v.values
        self._plots.append((axid, 'plot', x, y, kwargs))

    def scatter(self, axid: int, x: Union[pd.Series, np.array],
                y: np.array = None, **kwargs):
        """ Add more plots to be plotted. """
        if isinstance(x, pd.Series):
            _v = x
            x, y = _v.index, _v.values
        self._plots.append((axid, 'scatter', x, y, kwargs))

    def hist(self, axid: int, x: Union[pd.Series, np.array],
             y: np.array = None, **kwargs):
        if isinstance(x, pd.Series):
            _v = x
            x, y = _v.index, _v.values
        self._plots.append((axid, 'hist', x, y, kwargs))

    def annotate(self, axid: int, x: Union[pd.Series, np.array],
                 y: np.array = None, labels: Sequence = (), **kwargs):
        if isinstance(x, pd.Series):
            _v = x
            x, y = _v.index, _v.values
        self._annotations.append((axid, x, y, labels, kwargs))

    def line(self, axid: int, type_: str, v: Union[float, np.array],
             range_: tuple = (), **kwargs):
        self._lines.append((axid, type_, v, range_, kwargs))

    def plot(self):
        """ Creates the figure. """
        add_legend = [False] * self._length
        label_legend = [[]] * self._length

        # Run over plots
        for plot in self._plots:
            axid, call, x, y, kw = plot
            secondary = kw.pop('secondary_y', False)
            ax = self._get_axes(axid, secondary)

            rc = self._RC.copy()
            rc.update(kw)
            leg = getattr(ax, call)(x, y, **rc)

            if 'x_label' in rc:
                ax.set_xlabel(rc['x_label'])
            else:
                ax.set_xlabel(self._xl[axid])
            if 'y_label' in rc:
                ax.set_ylabel(rc['y_label'])
            else:
                ax.set_ylabel(self._yl[axid])

            if 'label' in rc:
                if isinstance(leg, list):
                    leg = leg[0]
                add_legend[axid] = True
                label_legend[axid].append(leg)

        # Run over additional lines
        for axid, mode, val, rng, kw in self._lines:
            ax = self._get_axes(axid, False)
            if mode == 'xh':
                leg = ax.axhline(val, **kw)
            elif mode == 'xv':
                leg = ax.axvline(val, **kw)
            elif mode == 'h':
                leg = ax.hlines(val, *rng, **kw)
            else:
                leg = ax.vlines(val, *rng, **kw)
            if 'label' in kw:
                add_legend[axid] = True
                label_legend[axid].append(leg)

        # Run over axis lines
        for ax, xz in zip(self._ax, self._x_zero):
            ax.axvline(xz, **self._RC_AXIS)
        for ax, yz in zip(self._ax, self._y_zero):
            ax.axhline(yz, **self._RC_AXIS)

        for axid, x, y, l, kw in self._annotations:
            ax = self._get_axes(axid, False)
            rc = self._RC.copy()
            rc.update(kw)
            ax.scatter(x, y, **rc)
            for i, k in enumerate(l):
                ax.annotate(k, (x[i], y[i]), **self._RC_TEXT)

        # Create legend
        for n, v in enumerate(zip(add_legend, label_legend)):
            flag, leg = v
            if flag:
                self._ax[n].legend(leg, (l.get_label() for l in leg))


class TSPlot(Plotter):
    """ Creates a time series plot. """

    def __init__(self, ncols: int = 1, nrows: int = 1, xl: Sequence = ('Date',),
                 yl: Sequence = ('Price',), x_zero: Sequence = (),
                 y_zero: Sequence = (), xlim: Sequence = (),
                 ylim: Sequence = ()):
        super().__init__(ncols, nrows, xl, yl, x_zero, y_zero, xlim, ylim)


class PtfOptimizationPlot(Plotter):
    """ Creates a variance/return plot from a OptimizerResult object. """

    # def add(self, axid: int, call: str, res: OptimizerResult, **kwargs):
    def add(self, axid: int, call: str, res, **kwargs):
        """ Add more plots to be plotted. """
        x = np.array(res.ptf_variance)
        y = np.array(res.ptf_return)
        self._plots.append((axid, call, x, y, kwargs))

        if not self._annotations:
            xc = np.array(res.const_var)
            yc = np.array(res.const_ret)
            labels = res.uids
            self._annotations.append((axid, xc, yc, labels, {'marker': 'x'}))


def shiftedColorMap(cmap, start=0, midpoint=0.5, stop=1.0, name='shiftedcmap'):
    """ Function to offset the "center" of a colormap. Useful for data with a
        negative min and positive max and you want the middle of the colormap's
        dynamic range to be at zero.

        Input
        -----
          cmap : The matplotlib colormap to be altered
          start : Offset from lowest point in the colormap's range.
              Defaults to 0.0 (no lower offset). Should be between
              0.0 and `midpoint`.
          midpoint : The new center of the colormap. Defaults to
              0.5 (no shift). Should be between 0.0 and 1.0. In
              general, this should be  1 - vmax / (vmax + abs(vmin))
              For example if your data range from -15.0 to +5.0 and
              you want the center of the colormap at 0.0, `midpoint`
              should be set to  1 - 5/(5 + 15)) or 0.75
          stop : Offset from highest point in the colormap's range.
              Defaults to 1.0 (no upper offset). Should be between
              `midpoint` and 1.0.
    """
    cdict = {
        'red': [],
        'green': [],
        'blue': [],
        'alpha': []
    }

    cmap_obj = getattr(mpl.cm, cmap)

    # regular index to compute the colors
    reg_index = np.linspace(start, stop, 257)
    print(reg_index[0], reg_index[128], reg_index[-1])

    # shifted index to match the data
    shift_index = np.hstack([
        np.linspace(0.0, midpoint, 128, endpoint=False),
        np.linspace(midpoint, 1.0, 129, endpoint=True)
    ])

    for ri, si in zip(reg_index, shift_index):
        r, g, b, a = cmap_obj(ri)

        cdict['red'].append((si, r, r))
        cdict['green'].append((si, g, g))
        cdict['blue'].append((si, b, b))
        cdict['alpha'].append((si, a, a))

    newcmap = mpl.colors.LinearSegmentedColormap(name, cdict)
    plt.register_cmap(cmap=newcmap)

    return newcmap
