#
# Portfolio Engine
# Engine to work with portfolio
#

import numpy as np

import nfpy.Assets as Ast
import nfpy.Calendar as Cal
from nfpy.Financial import DividendFactory
import nfpy.Math as Math
from nfpy.Tools import Constants as Cn


class PortfolioEngine(object):

    def __init__(self, ptf: Ast.TyAsset):
        self._af = Ast.get_af_glob()
        self._cal = Cal.get_calendar_glob()
        self._fx = Ast.get_fx_glob()

        self._ptf = ptf

    def dividends_paid(self) -> np.ndarray:
        # Create the list of years
        years = np.unique(
            self._cal
                .calendar
                .values
                .astype('datetime64[Y]')
        )
        dividends = np.zeros(years.shape[0])

        for uid in self._ptf.constituents_uids:
            if self._fx.is_ccy(uid):
                continue

            asset = self._af.get(uid)

            if asset.type == 'Equity':
                dt, div = DividendFactory(asset).dividends
                y_dt = dt.astype('datetime64[Y]')

                for n, y in enumerate(years):
                    dividends[n] += np.sum(div[y_dt == y])

        return dividends

    def dividends_ttm(self) -> float:
        start = self._cal.t0.asm8.astype('datetime64[Y]') - \
                np.timedelta64(Cn.DAYS_IN_1Y, 'D')
        dividends = .0

        for uid in self._ptf.constituents_uids:
            if self._fx.is_ccy(uid):
                continue

            asset = self._af.get(uid)

            if asset.type == 'Equity':
                dt, div = DividendFactory(asset).dividends
                slc = Math.search_trim_pos(dt, start=start)
                dividends += np.sum(div[slc])

        return dividends
