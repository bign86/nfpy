#
# Minimal variance model
#

import numpy as np

from .BaseOptimizer import (BaseOptimizer, OptimizerConf, OptimizerResult)

import nfpy.Math as Math


class MinimalVarianceModel(BaseOptimizer):
    """ Implements the Minimal Variance Portfolio analysis. """

    _LABEL = 'MinVariance'

    def _optimize(self) -> OptimizerResult:

        self._mean_ret = Math.compound(
            np.mean(self._ret, axis=1),
            self._scaling
        )
        self._cov = self._calc_cov()

        c = OptimizerConf()
        c.args = (self._cov, self._gamma)
        c.funct = self._var_f
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
            r.ptf_variance = [opt.fun]
            _ptf_ret = np.sum(self._mean_ret * opt.x)
            r.ptf_return = [_ptf_ret]
            r.sharpe = [_ptf_ret / np.sqrt(opt.fun)]

        return r
