#
# Dummy Evolver class
# Fake evolver to be used for testing purposes
#

import numpy as np

from nfpy.Var.EvolutionModels.BaseVarEvolver import BaseVarEvolver
from nfpy.Assets import Asset


class DummyVarEvolver(BaseVarEvolver):
    """ Dummy evolver used for testing purposes. """

    def __init__(self, varobj):
        super().__init__(varobj)

    def _decompose(self, asset: Asset) -> tuple:
        self._rf_uid = asset.uid + '_Dummy'
        return {self._rf_uid: None}, {self._rf_uid: self}

    def _compute_path(self, n: int, draws: np.array):
        self._res[n] = (1. + draws).prod() - 1.

