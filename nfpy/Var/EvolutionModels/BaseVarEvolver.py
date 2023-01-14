#
# Base Var Evolutor class
# Base class for all Var evolutor
#

from abc import ABCMeta, abstractmethod
import numpy as np
import pandas as pd

from nfpy.Assets import Asset
# from nfpy.Assets.FinancialItem import FinancialItem
# from nfpy.Tools.Exceptions import MissingData


class BaseVarEvolver(metaclass=ABCMeta):
    """ Factory to create the risk factors tree from the asset objects """

    # FIXME: !!!!!cyclic dep!!!!!
    def __init__(self, varobj):
        self._rf = None
        self._rf_uid = None
        self._ret = None
        self._path = None
        self._varobj = varobj

        self._path = None
        self._res = np.empty(varobj.numpath, dtype=float)

    @property
    def returns(self) -> pd.Series:
        if self._ret is None:
            self._get_returns()
        return self._ret

    @property
    def path(self) -> np.array:
        return self._path

    def _get_returns(self):
        """ Get the trimmed series of the risk factor returns."""
        r = self._rf.log_returns
        r = r.loc[:self._varobj.t0]
        self._ret = r[-self._varobj.observations:]

    def build_tree(self, asset: Asset) -> tuple:
        self._rf = asset
        return self._decompose(asset)

    def simulate(self, n: int):
        # get the generated random draws for the path
        draws = self._varobj.get_rnd_draws(n, self._rf_uid)

        # use the draws to regenerate the random path
        self._compute_path(n, draws)

    @abstractmethod
    def _decompose(self, asset: Asset) -> tuple:
        pass

    @abstractmethod
    def _compute_path(self, n: int, draws: np.array):
        pass
