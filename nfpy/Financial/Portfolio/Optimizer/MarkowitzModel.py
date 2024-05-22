#
# Markowitz model
# Class that implements the Markowitz portfolio optimization on the
# given portfolio to obtain the efficient frontier
#

import numpy as np
from typing import (Optional, Sequence)

from .BaseOptimizer import (BaseOptimizer, OptimizerConf)

import nfpy.Math as Math


class MarkowitzModel(BaseOptimizer):
    """ Implements the Markowitz Portfolio analysis. """

    _LABEL = 'Markowitz'

    def __init__(self, returns: np.ndarray, freq: str, labels: Sequence[str],
                 max_ret: float = 1., min_ret: float = .0,
                 iterations: int = 50, points: int = 20,
                 ret_grid: Sequence[float] = None,
                 gamma: Optional[float] = None, **kwargs):
        super().__init__(returns=returns, freq=freq, labels=labels,
                         iterations=iterations, gamma=gamma, **kwargs)

        # Input variables
        self._grid_size = points
        self._max_r = max_ret
        self._min_r = min_ret
        self._ret_grid = ret_grid

        if ret_grid is not None:
            if len(ret_grid) > 0:
                self._grid_size = len(self._ret_grid)
                self._max_r = max(self._ret_grid)
                self._min_r = min(self._ret_grid)

    def returns_grid(self):
        """ Calculates the grid of returns for the efficient frontier. """
        grid = self._ret_grid
        if not grid:
            _rmax = np.minimum(np.max(self._mean_ret), self._max_r)
            _rmin = np.maximum(np.min(self._mean_ret), self._min_r)
            # print('max {:.5f} min {:.5f}'.format(_rmax, _rmin))
            _h = (_rmax - _rmin) / self._grid_size
            grid = np.arange(_rmin, _rmax + _h, _h)
        for r in grid:
            yield r

    def _optimize(self):
        """ Optimize following the Markowitz procedure """

        def constrain_ret(wgt, sret, tret):
            return np.dot(wgt, sret) - tret

        def budget(x):
            return np.sum(x) - 1.

        self._mean_ret = Math.compound(
            np.mean(self._ret, axis=1),
            self._scaling
        )
        self._cov = self._calc_cov()

        r = self._create_result_obj()
        for i, fix_ret in enumerate(self.returns_grid()):
            print(f'{i:>3}:{self._grid_size:>3} | {fix_ret:.2f}')

            c = OptimizerConf()
            c.args = (self._cov, self._gamma)
            c.funct = self._var_f
            c.constraints = [
                {'type': 'eq', 'fun': constrain_ret, 'args': (self._mean_ret, fix_ret)},
                {'type': 'eq', 'fun': budget},
            ]

            opt = self._minimizer(c)

            if (opt is not None) and opt.success:
                r.success = True
                r.len = r.len + 1
                r.weights.append(opt.x)
                r.ptf_variance.append(opt.fun)
                _ptf_ret = np.sum(self._mean_ret * opt.x)
                r.ptf_return.append(_ptf_ret)
                r.sharpe.append(_ptf_ret / np.sqrt(opt.fun))

        return r
