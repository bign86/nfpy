#
# Random Engine class
# Class that implements the basic random generator engine for Var
#

import numpy as np
import pandas as pd
import numpy.random as rnd
from numpy.linalg import cholesky

from nfpy.Tools.TSUtils import dropna, trim_ts


class RandomEngine(object):

    def __init__(self, rf_dict: dict, obs: int, dim: int, length: int, it: int,
                 start: pd.Timestamp = None, end: pd.Timestamp = None):
        # Sigma related
        self._dim = None
        self._obs = None
        self._index = None
        self._start = None
        self._end = None

        # Random draws related
        self._length = None
        self._iter = None
        self._seed = None

        # Matrices
        self._sigma = None
        self._choly = None
        self._draws = None

        self._initialize(rf_dict, obs, dim, length, it, start, end)

    @property
    def seed(self) -> int:
        return self._seed

    @seed.setter
    def seed(self, v: int):
        self._seed = v

    @property
    def sigma(self) -> np.array:
        return self._sigma

    @property
    def cholesky(self) -> np.array:
        return self._choly

    @property
    def size(self) -> tuple:
        return self._iter, self._dim, self._length

    def _initialize(self, rf_dict: dict, obs: int, dim: int, length: int,
                    it: int, start: pd.Timestamp, end: pd.Timestamp):
        # Consistency check
        if not rf_dict:
            raise ValueError('Risk Factors not present!')
        if int(dim) <= 0:
            raise ValueError('Number of paths inconsistent!')
        if int(length) <= 0:
            raise ValueError('Length of the future projection inconsistent!')

        # Calculate correlation matrix and cholesky
        nrf = len(rf_dict)
        mat = np.empty((nrf, obs))

        index, i = [], 0
        for k, rf in rf_dict.items():
            index.append(k)
            r = rf.returns
            v, _ = trim_ts(r.values, r.index.values, start, end)
            mat[i, :] = r[-obs:]
            i = i + 1

        # calculate covariance matrix
        mat, _ = dropna(mat)
        sigma = np.cov(mat)
        choly = cholesky(sigma)

        # draw normal random numbers
        size = (it, dim, length)
        draws = rnd.normal(size=size)

        # apply cholesky
        for i in range(size[0]):
            mat = draws[i, :, :]
            draws[i, :, :] = np.dot(choly, mat)

        self._dim = dim
        self._length = length
        self._iter = it
        self._draws = draws
        self._dim = nrf
        self._obs = obs
        self._index = index
        self._sigma = sigma
        self._choly = choly
        self._start = end
        self._end = start

    def get(self, it: int, rf: str) -> np.array:
        i = self._index.index(rf)
        return self._draws[it, i, :]
