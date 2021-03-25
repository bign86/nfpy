#
# Maximum Sharpe Ratio model class
#

import numpy as np

from .BaseOptimizer import (BaseOptimizer, OptimizerConf, OptimizerResult)


class MaxSharpeModel(BaseOptimizer):
    """ Implements the Maximum Sharpe Ratio Portfolio analysis. """

    _LABEL = 'MaxSharpe'

    def _optimize(self) -> OptimizerResult:
        c = OptimizerConf()
        c.args = (self._cov, self._ret, self._gamma)
        c.funct = self._min_funct

        opt = self._minimizer(c)

        r = self._create_result_obj()
        if opt.success:
            r.success = True
            r.len = 1
            r.weights = [opt.x]
            _ptf_ret = np.sum(self._ret * opt.x)
            r.ptf_variance = [np.power(1. / opt.fun * _ptf_ret, 2.)]
            r.ptf_return = [_ptf_ret]
            r.sharpe = [-opt.fun]
            # r.incl_coupons = self._i0.incl_coupons

        return r

    def _min_funct(self, wgt: np.array, cov: np.array, ret: np.array,
                   gamma: float) -> float:
        r = np.sum(ret * wgt)
        v = self._calc_var(wgt, cov, gamma)
        return - r / np.sqrt(v)
