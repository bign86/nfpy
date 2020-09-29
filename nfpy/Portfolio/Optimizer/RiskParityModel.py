#
# Risk Parity model class
#

import numpy as np
from typing import Optional

from nfpy.Assets import Portfolio
from nfpy.Portfolio.Optimizer.BaseOptimizer import BaseOptimizer, \
    OptimizerConf, OptimizerResult


class RiskParityModel(BaseOptimizer):
    """ Implements the simple Risk Parity Portfolio analysis. """

    _LABEL = 'RiskParity'

    def __init__(self, ptf: Portfolio, iterations: int = 50, **kwargs):
        super().__init__(ptf=ptf, iterations=iterations)

    def rc(self, wgt: np.array, cov: np.array, var: Optional[np.array] = None) -> np.array:
        """ Calculates the Risk Contribution of each asset in the portfolio.
            
            Input:
                wgt [np.array]: portfolio weights vector
                cov [np.array]: portfolio covariance
                var [Optional[np.array]]: pre-calculated variance, if missing is calculated
                                          on the fly
            
            Output:
                rc [np.array]: risk contribution of each asset
        """
        if var is None:
            var = self._calc_var(wgt, cov)
        mrc = np.dot(cov, wgt) / var
        return np.multiply(wgt, mrc)

    def _optimize(self) -> OptimizerResult:
        risk_tgt = np.ones(self._len) / self._len

        c = OptimizerConf()
        c.args = (self._cov, risk_tgt)
        c.constraints = ({'type': 'ineq', 'fun': lambda x: x},)
        c.funct = self._min_funct

        opt = self._minimizer(c)

        r = self._create_result_obj()
        if opt.success:
            r.success = True
            r.len = 1
            r.weights = [opt.x]
            # r.returns = [pd.Series(data=self._ret, index=self._uids)]
            _var = self._calc_var(opt.x, self._cov, self._gamma)
            r.ptf_variance = [_var]
            _ptf_ret = np.sum(self._ret * opt.x)
            r.ptf_return = [_ptf_ret]
            r.sharpe = [_ptf_ret / np.sqrt(_var)]
            # r.incl_coupons = self._i0.incl_coupons

        # r.model = self._LABEL
        # r.label = self._LABEL
        # r.uids = self._i0.uids
        # r.uids = self._uids
        return r

    def _min_funct(self, wgt: np.array, cov: np.array, risk_tgt: np.array) -> float:
        # FIXME: here the np.dot(cov, wgt) is calculated twice per iteration
        var = self._calc_var(wgt, cov)
        rc = self.rc(wgt, cov, var)
        tgt = np.multiply(var, risk_tgt)
        return sum(np.square(rc - tgt))
