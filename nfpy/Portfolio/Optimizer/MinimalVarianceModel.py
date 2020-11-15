#
# Minimal variance model class
#

import numpy as np
from nfpy.Portfolio.Optimizer.BaseOptimizer import BaseOptimizer, \
    OptimizerConf, OptimizerResult


class MinimalVarianceModel(BaseOptimizer):
    """ Implements the Minimal Variance Portfolio analysis. """

    _LABEL = 'MinVariance'

    def _optimize(self) -> OptimizerResult:
        c = OptimizerConf()
        c.args = (self._cov, self._gamma)
        c.funct = self._calc_var

        opt = self._minimizer(c)

        r = self._create_result_obj()
        if opt.success:
            r.success = True
            r.len = 1
            r.weights = [opt.x]
            # r.const_ret = [self._ret]
            r.ptf_variance = [opt.fun]
            _ptf_ret = np.sum(self._ret * opt.x)
            r.ptf_return = [_ptf_ret]
            r.sharpe = [_ptf_ret / np.sqrt(opt.fun)]
            # r.incl_coupons = self._i0.incl_coupons
            # r.coupons = self._coupons

        # r.model = self._LABEL
        # r.label = self._LABEL
        # r.uids = self._uids
        return r
