#
# Optimizer metaclass
# Class that implements the basic optimizers routines to be used by other models
#

from abc import (ABCMeta, abstractmethod)
import numpy as np
import numpy.random as rnd
from scipy.optimize import (minimize, OptimizeResult)
from typing import (Sequence, Type)

from nfpy.Tools import (Constants as Cn, Utilities as Ut)


class OptimizerConf(Ut.AttributizedDict):
    """ Object containing the parameters for the optimizer. """

    def __init__(self):
        super().__init__()
        self.constraints = []
        self.tol = 1e-9
        self.method = 'SLSQP'
        self.options = {'disp': False, 'eps': 1e-08,
                        'maxiter': 80, 'ftol': 1e-09}


class OptimizerResult(Ut.AttributizedDict):
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
        self.const_var = []
        self.const_ret = []


class BaseOptimizer(metaclass=ABCMeta):
    """ Implements the Portfolio Optimizer metaclass. Optimizer algorithms
        should derive from this class.
    """

    _LABEL = ''

    def __init__(self, returns: np.ndarray, freq: str, labels: Sequence[str],
                 iterations: int = 50, gamma: float = .0,
                 budget: float = 1., **kwargs):
        # Input variables
        self._ret = returns
        self._freq = freq
        self._iter = iterations
        self._cnsts_labels = labels

        self._gamma = abs(gamma)

        # Working variables
        assert returns.shape[0] == len(labels)
        self._num_cnsts = returns.shape[0]
        self._var_f = self._fn_var_l2 if gamma != 0 else self._fn_var
        self._budget_constraint = self._set_budget(budget)
        self._scaling = Cn.FREQ_2_D[freq]['Y']
        self._mean_ret = None
        self._cov = None

        # Output variables
        self._res = None

    @property
    def desc(self) -> str:
        """ Returns the identifier of the optimization model. """
        return self._LABEL

    @property
    def result(self) -> OptimizerResult:
        if self._res is None:
            self._res = self._optimize()
        return self._res

    @property
    def covariance(self) -> np.ndarray:
        return self._cov

    @covariance.setter
    def covariance(self, v: np.ndarray) -> None:
        if v.ndim != 2:
            raise ValueError('BaseOptimizer(): covariance matrix not 2D')
        if v.shape[0] != v.shape[1]:
            raise ValueError('BaseOptimizer(): covariance matrix not squared')
        if v.shape[0] != self._num_cnsts:
            raise ValueError(f'BaseOptimizer(): covariance matrix not of size {self._num_cnsts}')
        self._cov = v

    @property
    def mean_returns(self) -> np.ndarray:
        return self._mean_ret

    @mean_returns.setter
    def mean_returns(self, v: np.ndarray) -> None:
        if v.ndim != 1:
            raise ValueError('BaseOptimizer(): mean returns vector not 1D')
        if v.shape[0] != self._num_cnsts:
            raise ValueError(f'BaseOptimizer(): mean returns vector not of size {self._num_cnsts}')
        self._mean_ret = v

    def _abs_budget_f(self, v: np.ndarray) -> float:
        return np.sum(np.abs(v)) - self._budget_constraint[1]

    def _budget_f(self, v: np.ndarray) -> float:
        return np.sum(v) - self._budget_constraint[0]

    @staticmethod
    def _set_budget(budget: float) -> tuple[float, float]:
        budget = max(-1., min(1., budget))
        return budget, 2.-abs(budget)

    @staticmethod
    def _fn_var(*args) -> float:
        """ Calculates the portfolio variance.

            Input:
                wgt [np.ndarray]: portfolio weights vector
                cov [np.ndarray]: portfolio covariance

            Output:
                variance [float]: portfolio variance
        """
        wgt, cov = args[0], args[1]
        return float(np.dot(wgt.T, np.dot(cov, wgt)))

    @staticmethod
    def _fn_var_l2(*args) -> float:
        """ Calculates the portfolio variance with L2 regularization.

            Input:
                wgt [np.ndarray]: portfolio weights vector
                cov [np.ndarray]: portfolio covariance
                gamma [float]: regularization parameter

            Output:
                variance [float]: portfolio variance
        """
        wgt, cov, g = args[0], args[1], args[2]
        var = float(np.dot(wgt.T, np.dot(cov, wgt))) \
              + g * np.dot(wgt.T, wgt)
        return var

    def _minimizer(self, conf: OptimizerConf) -> OptimizeResult:
        """ Wrapper to Scipy minimize. Defines the budget rule, runs the
            minimization and collects the results.

            Input:
                conf [OptimizerConf]: configuration of the optimization
        """
        bounds = ((-1.0, 1.0),) * self._num_cnsts
        best_conv = 1e6

        result = None
        for _ in range(self._iter):
            _v = rnd.rand(self._num_cnsts)
            _x0 = _v / np.sum(_v)

            _optimum = minimize(
                conf.funct, _x0, args=conf.args, tol=conf.tol,
                method=conf.method, bounds=bounds,
                constraints=conf.constraints, options=conf.options
            )

            if _optimum.success and (_optimum.fun < best_conv):
                best_conv = _optimum.fun
                result = _optimum

        return result

    def _create_result_obj(self) -> OptimizerResult:
        obj = OptimizerResult()
        obj.model = self._LABEL
        obj.labels = self._cnsts_labels
        obj.const_ret = self._mean_ret
        obj.const_var = self._cov.diagonal()
        return obj

    @abstractmethod
    def _optimize(self) -> OptimizerResult:
        """ Abstract method. Must create the configuration of the minimization
            and call the minimization routine. Inputs to the minimization must
            be created here. In particular,
                * mean returns if not set before
                * covariance matrix if not set before (_calc_cov() is available,
                    override if not appropriate for the method)
                * define all constraint functions including the budget()
        """

    def _calc_cov(self) -> np.ndarray:
        """ Calculate the covariance. Must be called by _optimize() and may be
            overridden in child classes.
        """
        return np.cov(self._ret.T, rowvar=False) * self._scaling


TyOptimizer = Type[BaseOptimizer]
