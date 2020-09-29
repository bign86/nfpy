#
# Optimizer metaclass
# Class that implements the basic optimizers routines to be used by other models
#

from abc import ABCMeta, abstractmethod

import numpy as np
import numpy.random as rnd
from scipy.optimize import minimize, OptimizeResult

from nfpy.Assets.Portfolio import Portfolio
from nfpy.Financial.Returns import compound
from nfpy.Tools.Constants import BDAYS_IN_1Y
from nfpy.Tools.Utilities import AttributizedDict


class OptimizerConf(AttributizedDict):
    """ Object containing the parameters for the optimizer. """

    def __init__(self):
        super().__init__()
        self.constraints = ()
        self.tol = 1e-9
        self.method = 'SLSQP'
        self.options = {'disp': False, 'eps': 1e-08, 'maxiter': 80, 'ftol': 1e-09}


class OptimizerResult(AttributizedDict):
    """ Object containing the result of the optimizer. """

    def __init__(self):
        super().__init__()
        self.model = None
        self.success = False
        self.len = 0
        self.label = None
        self.weights = []
        self.ptf_variance = []
        self.ptf_return = []
        self.sharpe = []
        self.uids = []
        self.const_var = []
        self.const_ret = []
        # self.incl_coupons = False


class BaseOptimizer(metaclass=ABCMeta):
    """ Implements the Portfolio Optimizer metaclass. """

    _LABEL = ''

    def __init__(self, ptf: Portfolio, iterations: int = 50,
                 gamma: float = None, **kwargs):
        # Input variables
        self._ptf = ptf
        self._iter = iterations
        self._gamma = gamma
        # self._coupons = coupons

        # Working variables
        self._calc_var = None
        self._len = None
        self._ret = None
        self._var = None
        self._cov = None
        self._uids = None

        # Output variables
        self._res = None

        self._initialize()

    def _initialize(self):
        """ Initialize the input object and set the state for the optimization. """
        self._set_ptf()
        self._calc_var = self._fn_var_l2 if self._gamma else self._fn_var

    def _set_ptf(self):
        """ Set quantities related to portfolios. """
        ptf = self._ptf

        self._uids = ptf.constituents_uids
        self._len = ptf.num_constituents

        ret = ptf.expected_constituents_return()
        vola = ptf.constituents_volatility()
        cov = ptf.covariance.values
        self._ret = compound(ret, BDAYS_IN_1Y)
        self._var = (vola ** 2.) * BDAYS_IN_1Y
        self._cov = cov * BDAYS_IN_1Y

    @property
    def ptf_uid(self) -> str:
        return self._ptf.uid

    @property
    def ptf(self) -> Portfolio:
        return self._ptf

    @property
    def desc(self) -> str:
        return self._LABEL

    @property
    def result(self) -> OptimizerResult:
        if self._res is None:
            self._res = self._optimize()
        return self._res

    @staticmethod
    def _fn_var(*args) -> float:
        """ Calculates the portfolio variance.

            Input:
                wgt [np.array]: portfolio weights vector
                cov [np.array]: portfolio covariance

            Output:
                variance [float]: portfolio variance
        """
        wgt, cov = args[0], args[1]
        return float(np.dot(wgt.T, np.dot(cov, wgt)))  # [0]

    @staticmethod
    def _fn_var_l2(*args) -> float:
        """ Calculates the portfolio variance with L2 regularization.

            Input:
                wgt [np.array]: portfolio weights vector
                cov [np.array]: portfolio covariance
                gamma [float]: regularization parameter

            Output:
                variance [float]: portfolio variance
        """
        wgt, cov, g = args[0], args[1], args[2]
        var = float(np.dot(wgt.T, np.dot(cov, wgt)))
        var += g * np.dot(wgt.T, wgt)
        return var

    def _minimizer(self, conf: OptimizerConf) -> OptimizeResult:
        """ Wrapper to Scipy minimize. """

        def budget(x):
            return np.sum(x) - 1.

        constraints = ({'type': 'eq', 'fun': budget},) + conf.constraints
        bounds = ((0.0, 1.0),) * self._len
        best_conv = 1e6

        result = None
        for _ in range(self._iter):
            _v = rnd.rand(self._len)
            _x0 = _v / np.sum(_v)

            _optimum = minimize(conf.funct, _x0, args=conf.args, tol=conf.tol,
                                method=conf.method, bounds=bounds,
                                constraints=constraints, options=conf.options)

            if _optimum.success and (_optimum.fun < best_conv):
                best_conv = _optimum.fun
                result = _optimum

        return result

    def _create_result_obj(self) -> OptimizerResult:
        obj = OptimizerResult()
        obj.model = self._LABEL
        obj.uids = self._uids
        obj.const_ret = self._ret
        obj.const_var = self._var
        return obj

    @abstractmethod
    def _optimize(self) -> OptimizerResult:
        """ Calls the optimization procedures. """
