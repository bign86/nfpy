#
# Portfolio optimization engine
# Engine to perform optimization of portfolios
#

import numpy as np
from typing import (Optional, Sequence, Union)

import nfpy.Assets as Ast
from nfpy.Calendar import get_calendar_glob
import nfpy.Financial as Fin
import nfpy.Math as Math
from nfpy.Tools import (Constants as Cn, Utilities as Ut)


class OptimizationEngineResult(Ut.AttributizedDict):
    """ Report data for Jinja2 generated from single optimization results. """


class OptimizationEngine(object):
    """ Main engine for portfolio optimization """

    def __init__(self, uid: str, algorithms: Union[dict, Sequence[dict]],
                 iterations: Optional[int] = None,
                 start: Optional[np.datetime64] = None,
                 t0: Optional[np.datetime64] = None, **kwargs):
        # Inputs
        self._uid = uid
        self._algo = algorithms
        self._iter = iterations
        self._start = start
        self._t0 = t0

        # Work variables
        self._af = Ast.get_af_glob()
        self._fx = Ast.get_fx_glob()
        self._rf = Fin.get_rf_glob()
        self._cal = get_calendar_glob()
        self._uids = None
        self._ret = None
        self._cov = None
        self._rf_ret = None

        # Outputs
        self._res = None

        self._initialize()

    @property
    def result(self) -> OptimizationEngineResult:
        if self._res is None:
            self.run()
        return self._res

    def _initialize(self) -> None:
        """ Calculates the relevant variables for the optimization routines. """
        # Variables
        ptf = self._af.get(self._uid)
        cal = self._cal.calendar

        # Get number of constituents ex-base cash position
        ccy = ptf.currency
        uids = ptf.constituents_uids.copy()
        uids.remove(ccy)

        # Build the returns matrix
        ret = np.zeros((len(cal), len(uids)))
        for i, uid in enumerate(uids):
            if self._fx.is_ccy(uid):
                r = self._fx.get(uid, ccy) \
                    .returns.values

            else:
                asset = self._af.get(uid)
                r = asset.returns.values
                pos_ccy = asset.currency

                if ccy != pos_ccy:
                    fx_ret = self._fx.get(pos_ccy, ccy) \
                        .returns.values
                    r += fx_ret + r * fx_ret

            ret[:, i] = r

        # Cut the arrays to the right dates and clean
        # ret, dt = Math.trim_ts(ret, cal.values, self._start, self._t0)
        slc = Math.search_trim_pos(cal.values, self._start, self._t0)
        ret, _ = Math.dropna(ret[slc], axis=1)

        self._uids = uids
        self._ret = Math.compound(
            Math.e_ret(ret, is_log=False),
            Cn.BDAYS_IN_1Y
        )
        self._cov = np.cov(ret, rowvar=False) * Cn.BDAYS_IN_1Y
        self._corr = np.corrcoef(ret, rowvar=False)

        if (self._rf_ret is None) and ('CALModel' in self._algo):
            self._rf_ret = Math.compound(
                self._rf.get_rf(ccy).last_price()[0],
                Cn.BDAYS_IN_1Y
            )

    def run(self) -> None:
        res_list = []
        for k, p in self._algo.items():
            symbol = '.'.join(['nfpy.Models.Optimizer', k, k])
            class_ = Ut.import_symbol(symbol)
            obj = class_(self._ret, self._cov, **p)
            result = obj.result
            result.uids = self._uids
            res_list.append(result)

        self._consolidate_results(res_list)

    def _consolidate_results(self, res_list: list) -> None:
        obj = OptimizationEngineResult()
        obj.results = res_list
        obj.uid = self._uid
        obj.uids = self._uids
        obj.start = self._start
        obj.t0 = self._t0
        obj.corr = self._corr
        self._res = obj
