#
# Breaches engine class
# Class to search for trading signals breaches
#

import numpy as np
from typing import (Any, Generator)

from nfpy.Assets import get_af_glob
import nfpy.IO as IO
import nfpy.Financial.Math as Mat
from nfpy.Tools import Utilities as Ut

from . import Trends as Tr


class BreachesResult(Ut.AttributizedDict):
    """ Result object from the BreachesEngine. """

    def __init__(self):
        super().__init__()
        self.uid = ''
        self.ccy = ''
        self.dt = None
        self.p = None
        self.vola = None
        self.w_sr = ()
        self.sr_list = ()
        self.breaches = np.empty(0)
        self.testing = np.empty(0)

    def plot(self) -> IO.TSPlot:
        vola = float(np.nanstd(self.p))
        f_min = np.nanmin(self.p) - 1.65 * vola
        f_max = np.nanmax(self.p) + 1.65 * vola
        dt_min, dt_max = self.dt[-self.w_check], self.dt[-1]

        pl = IO.TSPlot(yl=(f'Price ({self.ccy})',)) \
            .lplot(0, self.dt, self.p) \
            .line(0, 'v', dt_min, (f_min, f_max), colors='C2', linewidth=1.) \
            .set_limits(0, 'y', f_min, f_max)

        # FIXME: generalize to n < 'something reasonable' elements
        for sr, color in zip(self.sr_list, ('dimgray', 'sandybrown')):
            idx = np.where((sr > f_min) & (sr < f_max))
            sr = sr[idx[0]]
            pl.line(
                0, 'h', sr,
                (self.dt[0], self.dt[-1]),
                colors=color, linewidth=1.
            )
            for v in sr:
                corners = (
                    dt_min, v * (1. - self.vola),
                    dt_max, v * (1. + self.vola)
                )
                pl.fill(
                    0, 'r', corners,
                    edgecolor='C2',
                    facecolor='C2', alpha=.2
                )

        return pl


class BreachesEngine(object):
    """ Engine to evaluate breaches of trading signals. """

    def __init__(self, w_sr_slow: int, w_sr_fast: int, w_check: int,
                 sr_mult: float = 5., confidence: float = 1.65) -> None:
        # Handlers
        self._af = get_af_glob()

        # Input parameters
        self._sr_mult = sr_mult
        self._w_check = w_check
        self._confidence = confidence
        self._w_sr = (w_sr_slow, w_sr_fast)

    def _calculate_sr(self, dt: np.ndarray, p: np.ndarray) \
            -> Generator[np.ndarray, Any, None]:
        return (
            Tr.search_sr(
                dt[-int(w * self._sr_mult):],
                p[-int(w * self._sr_mult):],
                w=w, dump=.75
            )
            for w in self._w_sr
        )

    def raise_breaches(self, uid: str) -> BreachesResult:
        # Get asset, prices and volatility of returns
        asset = self._af.get(uid)
        prices = asset.prices
        p = prices.values
        dt = prices.index.values
        vola = float(np.nanstd(
            asset.returns.values[-self._w_check:]
        ))

        # Calculate S/R lines
        sr_groups = Tr.merge_sr(
            vola,
            list(self._calculate_sr(dt, p))
        )
        sr_list = np.sort(
            np.concatenate(
                sr_groups
            )
        )

        # Get the min and max value of the price series over the cross window
        p_c = p[-self._w_check:]
        p_min, p_max = np.nanmin(p_c), np.nanmax(p_c)

        # Run over S/R lines and search for lines in the price range
        vola *= self._confidence
        breach, testing = np.empty(0), np.empty(0)
        idx = np.searchsorted(
            sr_list,
            sorted((
                p_min * (1. - vola),
                p_max * (1. + vola)
            ))
        )
        rng = list(range(*idx))
        if len(rng) > 0:
            sr_list = sr_list[rng]
            final = np.where(
                sr_list <= Mat.next_valid_value(p_c)[0],
                sr_list / p_min - 1.,
                p_max / sr_list - 1.
            )
            breach = sr_list[np.where(final > vola)[0]]
            testing = sr_list[np.where((-vola < final) & (final < vola))[0]]

        # New result object
        w = int(10. * self._w_check)
        out = BreachesResult()
        out.uid = uid
        out.ccy = asset.currency
        out.dt = dt[-w:]
        out.p = p[-w:]
        out.w_sr = self._w_sr
        out.sr_list = sr_groups
        out.breaches = breach
        out.testing = testing
        out.vola = vola
        out.w_check = self._w_check
        return out
