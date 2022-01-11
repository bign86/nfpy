#
# GBM Evolver class
# Gaussian Brownian Motion evolver
#

import numpy as np

from nfpy.Assets import Asset
from nfpy.Var.EvolutionModels.BaseVarEvolver import BaseVarEvolver


class GBMEvolver(BaseVarEvolver):
    """ Gaussian Brownian Motion evolver used for testing purposes. """

    def __init__(self, varobj):
        super().__init__(varobj)
        self._mu = None
        self._var = None

    @property
    def mu(self):
        if self._mu is None:
            self._mu = self._ret.mean()
        return self._mu

    @property
    def var(self):
        if self._var is None:
            self._var = self._ret.var()
        return self._var

    def _decompose(self, asset: Asset) -> tuple:
        self._rf_uid = asset.uid + '_Eq'
        return {self._rf_uid: None}, {self._rf_uid: self}

    def _compute_path(self, n: int, draws: np.array):
        # d\ln{S} = (\mu − .5 \sigma^2) dt + \sigma dz
        self._path = self.mu - .5*self.var + draws
        self._res[n] = self._path.sum()
        # self._data[n] = (1. + self._path).prod() - 1.
