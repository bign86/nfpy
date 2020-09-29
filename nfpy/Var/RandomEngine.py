#
# Random Engine class
# Class that implements the basic random generator engine for Var
#

import numpy as np
import pandas as pd
import numpy.random as rnd
from numpy.linalg import cholesky


class RandomEngine(object):

    def __init__(self):
        # Sigma related
        self._dim = None
        self._obs = None
        self._index = None

        # Random draws related
        self._length = None
        self._iter = None
        self._seed = None

        # Matrices
        self._sigma = None
        self._choly = None
        self._draws = None

        self._is_initialized = False

    @property
    def seed(self) -> int:
        return self._seed

    @seed.setter
    def seed(self, v: int):
        self._seed = v

    @property
    def sigma(self) -> pd.DataFrame:
        return self._sigma

    @property
    def cholesky(self) -> pd.DataFrame:
        return self._choly

    @property
    def size(self) -> tuple:
        return self._iter, self._dim, self._length

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    def calc_sigma(self, rf_dict: dict, date: pd.Timestamp, obs: int) -> pd.DataFrame:
        nrf = len(rf_dict)
        mat = np.empty((nrf, obs))

        index = []
        i = 0
        for k, rf in rf_dict.items():
            index.append(k)
            r = rf.returns.loc[:date]
            mat[i, :] = r[-obs:].values
            i = i + 1

        # calculate covariance matrix
        sigma = np.cov(mat)
        choly = cholesky(sigma)
        choly = pd.DataFrame(data=choly, index=index)

        # with pd.option_context('display.max_rows', None, 'display.max_columns', None):
        #   print(sigma)

        self._dim = nrf
        self._obs = obs
        self._index = index
        self._sigma = pd.DataFrame(data=sigma, index=index)
        self._choly = choly

        return choly

    def initialize_generator(self, rf_dict: dict, date: pd.Timestamp,
                             obs: int, dim: int, length: int, it: int):
        # draw normal random numbers
        size = (it, dim, length)
        draws = rnd.normal(size=size)

        # calculate correlation matrix and cholesky
        choly = self.calc_sigma(rf_dict, date, obs)

        # apply cholesky
        for i in range(size[0]):
            mat = draws[i, :, :]
            draws[i, :, :] = np.dot(choly, mat)

        self._dim = dim
        self._length = length
        self._iter = it
        self._draws = draws
        self._is_initialized = True

    def get(self, it: int, rf: str) -> np.array:
        i = self._index.index(rf)
        return self._draws[it, i, :]
