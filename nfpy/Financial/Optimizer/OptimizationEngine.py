#
# Portfolio optimization engine
# Engine to perform optimization of portfolios
#

import numpy as np
from typing import (Union, Sequence)

from nfpy.Assets import get_af_glob
from nfpy.Calendar import get_calendar_glob
import nfpy.Math as Mat
from nfpy.Tools import (Constants as Cn, Utilities as Ut)

from ..CurrencyFactory import get_fx_glob
from ..RateFactory import get_rf_glob


class ResultOptimization(Ut.AttributizedDict):
    """ Report data for Jinja generated from single optimization results. """


class OptimizationEngine(object):
    """ Main engine for portfolio optimization """

    def __init__(self, uid: str, algorithms: Union[dict, Sequence[dict]],
                 iterations: int = None, start: np.datetime64 = None,
                 t0: np.datetime64 = None, gamma: float = None,
                 **kwargs):
        # Inputs
        self._uid = uid
        self._algo = algorithms
        self._iter = iterations
        self._start = start
        self._t0 = t0
        self._gamma = gamma

        # Work variables
        self._af = get_af_glob()
        self._fx = get_fx_glob()
        self._rf = get_rf_glob()
        self._cal = get_calendar_glob()
        self._uids = None
        self._ret = None
        self._cov = None
        self._rf_ret = None

        # Outputs
        self._res = None

        self._initialize()

    @property
    def result(self):
        if self._res is None:
            self.run()
        return self._res

    def _initialize(self):
        """ Calculates the relevant variables for the optimization routines. """

        # Variables
        ptf = self._af.get(self._uid)
        cal = self._cal.calendar

        # Get number of constituents ex-base cash position
        ccy = ptf.currency
        uids = ptf.constituents_uids.copy()
        uids.remove(ccy)
        length = len(uids)

        # Build the returns matrix
        ret = np.zeros((len(cal), length))
        for i, uid in enumerate(uids):
            if self._fx.is_ccy(uid):
                asset = self._fx.get(uid, ccy)
                r = asset.returns.values

            else:
                asset = self._af.get(uid)
                r = asset.returns.values
                pos_ccy = asset.currency

                if ccy != pos_ccy:
                    fx = self._fx.get(pos_ccy, ccy)
                    fx_ret = fx.returns.values
                    r += fx_ret + r * fx_ret

            ret[:, i] = r

        # Cut the arrays to the right dates and clean
        ret, dt = Mat.trim_ts(ret, cal.values, self._start, self._t0)
        ret, _ = Mat.dropna(ret, axis=1)

        e_ret = Mat.expct_ret(ret, is_log=False)
        cov = np.cov(ret, rowvar=False)
        corr = np.corrcoef(ret, rowvar=False)

        self._uids = uids
        self._ret = Mat.compound(e_ret, Cn.BDAYS_IN_1Y)
        self._cov = cov * Cn.BDAYS_IN_1Y
        self._corr = corr
        
        if (self._rf_ret is None) and ('CALModel' in self._algo):
            rf = self._rf.get_rf(ccy)
            self._rf_ret = Mat.compound(rf.last_price()[0], Cn.BDAYS_IN_1Y)

    def run(self):
        res_list = []
        for k, p in self._algo.items():
            symbol = '.'.join(['nfpy', 'Financial', 'Optimizer', k, k])
            class_ = Ut.import_symbol(symbol)
            obj = class_(self._ret, self._cov, **p)
            result = obj.result
            result.uids = self._uids
            res_list.append(result)

        self._consolidate_results(res_list)

    def _consolidate_results(self, res_list: list):
        obj = ResultOptimization()
        obj.results = res_list
        obj.uid = self._uid
        obj.uids = self._uids
        obj.start = self._start
        obj.t0 = self._t0
        obj.gamma = self._gamma
        obj.corr = self._corr
        self._res = obj
