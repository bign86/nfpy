#
# Markowitz model class
# Class that implements the Markowitz portfolio optimization on the
# given portfolio
#

from typing import Sequence
import numpy as np

from nfpy.Portfolio.Optimizer.BaseOptimizer import BaseOptimizer, \
    OptimizerConf


class MarkowitzModel(BaseOptimizer):
    """ Implements the Markowitz Portfolio analysis. """

    _LABEL = 'Markowitz'

    def __init__(self, mean_returns: np.ndarray, covariance: np.ndarray,
                 max_ret: float = 1e6, min_ret: float = .0,
                 iterations: int = 50, points: int = 20,
                 ret_grid: Sequence = None, gamma: float = None, **kwargs):
        super().__init__(mean_returns=mean_returns, covariance=covariance,
                         iterations=iterations, gamma=gamma, **kwargs)

        # Input variables
        self._num = points
        self._max_r = max_ret
        self._min_r = min_ret
        self._ret_grid = ret_grid

        self._initialize()

    def _initialize(self):
        if self._ret_grid is not None:
            self._num = len(self._ret_grid)
            self._max_r = max(self._ret_grid)
            self._min_r = min(self._ret_grid)

    def returns_grid(self):
        """ Calculates the grid of returns for the efficient frontier. """
        grid = self._ret_grid
        if not grid:
            _rmax = np.minimum(np.max(self._ret), self._max_r)
            _rmin = np.maximum(np.min(self._ret), self._min_r)
            # print('max {:.5f} min {:.5f}'.format(_rmax, _rmin))
            _h = (_rmax - _rmin) / self._num
            grid = np.arange(_rmin, _rmax + _h, _h)
        for r in grid:
            yield r

    def _optimize(self):
        """ Optimize following the Markowitz procedure """

        def constrain_ret(wgt, sret, tret):
            return np.dot(wgt, sret) - tret

        r = self._create_result_obj()
        for fix_ret in self.returns_grid():

            c = OptimizerConf()
            c.args = (self._cov, self._gamma)
            c.funct = self._calc_var
            c.constraints = ({'type': 'eq', 'fun': constrain_ret,
                              'args': (self._ret, fix_ret)},)

            opt = self._minimizer(c)

            if opt.success:
                r.success = True
                r.len = r.len + 1
                r.weights.append(opt.x)
                r.ptf_variance.append(opt.fun)
                _ptf_ret = np.sum(self._ret * opt.x)
                r.ptf_return.append(_ptf_ret)
                r.sharpe.append(_ptf_ret / np.sqrt(opt.fun))

        return r
