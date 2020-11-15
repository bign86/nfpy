#
# Capital Asset Line model class
# Class that implements the Capital Asset Line portfolio optimization on the
# given portfolio
#

import numpy as np

from nfpy.Assets.Portfolio import Portfolio
from nfpy.Financial.Returns import compound
from nfpy.Handlers.RateFactory import get_rf_glob
from nfpy.Portfolio.Optimizer.BaseOptimizer import BaseOptimizer
from nfpy.Portfolio.Optimizer.MarkowitzModel import MarkowitzModel
from nfpy.Portfolio.Optimizer.MaxSharpeModel import MaxSharpeModel
from nfpy.Tools.Constants import BDAYS_IN_1Y


class CALModel(BaseOptimizer):
    """ Implements the Markowitz Portfolio analysis. """

    _LABEL = 'CALModel'

    def __init__(self, ptf: Portfolio, iterations: int = 50,
                 points: int = 20, rf_ret: float = None, **kwargs):
        self._num = points
        self._rf_ret = rf_ret
        super().__init__(ptf=ptf, iterations=iterations)

    def _initialize(self):
        super()._initialize()

        if self._rf_ret is None:
            rf = get_rf_glob().get_rf(self._ptf.currency)
            self._rf_ret = compound(rf.last_price(), BDAYS_IN_1Y)

    def _optimize(self):
        """ Optimize following the Markowitz procedure """

        # Search for the max sharpe portfolio
        msh = MaxSharpeModel(ptf=self._ptf, iterations=self._iter)
        msh_res = msh.result
        msh_ret = msh_res.ptf_return
        msh_var = msh_res.ptf_variance
        msh_wgt = msh_res.weights

        # Calculate how many points to be calculated above and below the sharpe
        # optimum to preserve the total
        down_pts, up_pts = self._calc_pts_separation(msh_ret[0])

        # Calculate the CAL below the sharpe optimum
        cal_res = self._calc_lending_line(msh_ret[0], msh_var[0],
                                          msh_wgt[0], down_pts)
        cal_ret, cal_var, cal_wgt = cal_res

        # Calculate the EF above the sharpe optimum
        mkw = MarkowitzModel(ptf=self._ptf, iterations=self._iter,
                             points=up_pts, min_ret=msh_ret[0])
        mkw_res = mkw.result
        mkw_ret = mkw_res.ptf_return
        mkw_var = mkw_res.ptf_variance
        mkw_wgt = mkw_res.weights

        # Build up the final portfolio
        r = self._create_result_obj()
        r.success = True
        r.len = self._num
        r.weights = cal_wgt + msh_wgt + mkw_wgt
        r.ptf_variance = cal_var + msh_var + mkw_var
        r.ptf_return = cal_ret + msh_ret + mkw_ret

        return r

    def _calc_pts_separation(self, sharpe_ret: float) -> tuple:
        """ Calculates how many points we must have above and below sharpe. """
        _rmax = np.max(self._ret)
        _rmin = np.maximum(np.min(self._ret), .0)
        ms_res_share = (sharpe_ret - _rmin) / (_rmax - _rmin)

        down_pts = int(round((self._num - 1) * ms_res_share))
        up_pts = int(self._num - 1 - down_pts)
        # assert self._num == 1 + up_pts + down_pts

        return down_pts, up_pts

    def _calc_lending_line(self, msh_ret: float, msh_var: float,
                           msh_wgt: np.array, num_pts: int) -> tuple:
        """ Calculates the lending portfolios below sharpe.

            Input:
                msh_ret [float]: max sharpe portfolio's return
                msh_var [float]: max sharpe portfolio's variance
                msh_wgt [np.array]: max sharpe portfolio's weights
                num_pts [int]: grid size to calculate

            Output:
               cal_ret [list]: calculated list of returns
               cal_var [list]: calculated list of variances
               cal_wgt [list]: calculated list of weights
        """
        rf = self._rf_ret
        _h = (msh_ret - rf) / num_pts
        const = msh_var / (msh_ret - rf)
        wgt_decay = 1. / num_pts

        cal_ret, cal_var, cal_wgt = [], [], []
        tot_decay = 0.
        for r in np.arange(rf, msh_ret, _h):
            cal_ret.append(r)
            cal_var.append((r - rf) * const)
            cal_wgt.append(msh_wgt * tot_decay)
            tot_decay += wgt_decay

        return cal_ret, cal_var, cal_wgt
