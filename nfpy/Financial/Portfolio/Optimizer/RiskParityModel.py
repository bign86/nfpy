#
# Risk Parity model
#

import numpy as np
from typing import (Optional, Sequence)

from .BaseOptimizer import (BaseOptimizer, OptimizerConf, OptimizerResult)

import nfpy.Math as Math


class RiskParityModel(BaseOptimizer):
    """ Implements the simple Risk Parity Portfolio analysis. """

    _LABEL = 'RiskParity'

    def __init__(self, returns: np.ndarray, freq: str, labels: Sequence[str],
                 iterations: int = 50, budget: float = 1., **kwargs):
        super().__init__(returns=returns, freq=freq, labels=labels,
                         iterations=iterations, budget=budget, **kwargs)

    def rc(self, wgt: np.ndarray, cov: np.ndarray,
           var: Optional[np.ndarray] = None) -> np.ndarray:
        """ Calculates the Risk Contribution of each asset in the portfolio.
            
            Input:
                wgt [np.ndarray]: portfolio weights vector
                cov [np.ndarray]: portfolio covariance
                var [Optional[np.ndarray]]: pre-calculated variance, if missing
                                          is calculated on the fly
            
            Output:
                rc [np.array]: risk contribution of each asset
        """
        if var is None:
            print('DEVO CALCOLARE A PARTE')
            var = self._var_f(wgt, cov, self._gamma)
        mrc = np.dot(cov, wgt) / var
        return np.multiply(wgt, mrc)

    def _optimize(self) -> OptimizerResult:

        self._mean_ret = Math.compound(
            np.mean(self._ret, axis=1),
            self._scaling
        )
        self._cov = self._calc_cov()

        risk_tgt = np.ones(self._num_cnsts) / self._num_cnsts

        c = OptimizerConf()
        c.args = (self._cov, risk_tgt)
        c.constraints = [
            {'type': 'ineq', 'fun': lambda x: x},
            {'type': 'eq', 'fun': self._budget_f},
            {'type': 'eq', 'fun': self._abs_budget_f}
        ]
        c.funct = self._min_funct

        opt = self._minimizer(c)

        r = self._create_result_obj()
        if (opt is not None) and opt.success:
            _var = self._var_f(opt.x, self._cov, self._gamma)
            _ptf_ret = np.sum(self._mean_ret * opt.x)

            r.success = True
            r.len = 1
            r.weights = [opt.x]
            r.ptf_variance = [_var]
            r.ptf_return = [_ptf_ret]
            r.sharpe = [_ptf_ret / np.sqrt(_var)]

        return r

    def _min_funct(self, wgt: np.ndarray, cov: np.ndarray,
                   risk_tgt: np.ndarray) -> float:
        # FIXME: here the np.dot(cov, wgt) is calculated twice per iteration
        var = self._var_f(wgt, cov, self._gamma)
        rc = self.rc(wgt, cov, var)
        tgt = np.multiply(var, risk_tgt)
        return sum(np.square(rc - tgt))
