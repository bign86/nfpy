#
# Maximum Sharpe Ratio model
#

import numpy as np

from .BaseOptimizer import (BaseOptimizer, OptimizerConf, OptimizerResult)

import nfpy.Math as Math


class MaxSharpeModel(BaseOptimizer):
    """ Implements the Maximum Sharpe Ratio Portfolio analysis.
        The budget is always 1.
    """

    _LABEL = 'MaxSharpe'

    def _optimize(self) -> OptimizerResult:

        self._mean_ret = Math.compound(
            np.mean(self._ret, axis=1),
            self._scaling
        )
        self._cov = self._calc_cov()

        c = OptimizerConf()
        c.args = (self._cov, self._mean_ret, self._gamma)
        c.funct = self._min_funct
        c.constraints = [
                {'type': 'eq', 'fun': self._budget_f},
                {'type': 'eq', 'fun': self._abs_budget_f}
        ]
        opt = self._minimizer(c)

        r = self._create_result_obj()
        if (opt is not None) and opt.success:
            r.success = True
            r.len = 1
            r.weights = [opt.x]
            _ptf_ret = np.sum(self._mean_ret * opt.x)
            r.ptf_variance = [np.power(1. / opt.fun * _ptf_ret, 2.)]
            r.ptf_return = [_ptf_ret]
            r.sharpe = [-opt.fun]

        return r

    def _min_funct(self, wgt: np.array, cov: np.array, ret: np.array,
                   gamma: float) -> float:
        r = np.sum(ret * wgt)
        v = self._var_f(wgt, cov, gamma)
        return - r / np.sqrt(v)
