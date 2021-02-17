#
# Base Fundamental Model
# Base class for fundamental models
#

from abc import abstractmethod
import pandas as pd
from typing import Union, Any

from nfpy.Tools import Constants as Cn

from .BaseModel import BaseModel


class BaseFundamentalModel(BaseModel):
    """ Base class from which fundamentals models are derived. """

    _RES_OBJ = None

    def __init__(self, uid: str, date: Union[str, pd.Timestamp] = None,
                 past_horizon: int = 5, future_proj: int = 3):
        super().__init__(uid, date)

        # Input variables
        self._eq = self._af.get(self._asset.equity)
        self._idx = self._af.get(self._eq.index)
        self._ph = int(past_horizon)
        self._fp = int(future_proj)
        self._start = self._t0 - pd.Timedelta(days=Cn.DAYS_IN_1Y * self._ph)

        # Working data
        self._freq = None
        self._last_price = None

    @property
    def frequency(self) -> Any:
        if self._freq is None:
            self._calc_freq()
        return self._freq

    def get_last_price(self) -> float:
        if not self._last_price:
            self._calc_last_price()
        return self._last_price

    def _calc_last_price(self):
        """ Returns the last price of the company's equity converted in the
            same currency as the company for consistency with the reported
            financial statements figures.
        """
        v, dt, _ = self._eq.last_price(self._t0)
        cv_obj = self._fx.get(self._eq.currency, self._asset.currency)
        self._last_price = v * cv_obj.get(dt)

    @abstractmethod
    def _calc_freq(self):
        """ Calculates model frequency. """
