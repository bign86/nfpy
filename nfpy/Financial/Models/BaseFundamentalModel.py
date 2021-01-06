#
# Base Fundamental Model
# Base class for fundamental models
#

from abc import (ABCMeta, abstractmethod)
import pandas as pd
from typing import Union, Any

from nfpy.Assets import get_af_glob
from nfpy.Calendar import get_calendar_glob
import nfpy.Math as Mat
from nfpy.Tools import (Constants as Cn, Utilities as Ut)

from ..CurrencyFactory import get_fx_glob


class BaseFundamentalResult(Ut.AttributizedDict):
    """ Base object containing the results of the model. """


class BaseFundamentalModel(metaclass=ABCMeta):
    """ Base class from which fundamentals models are derived. """

    _RES_OBJ = BaseFundamentalResult

    def __init__(self, company: str, date: Union[str, pd.Timestamp] = None,
                 past_horizon: int = 5, future_proj: int = 3,
                 date_fmt: str = '%Y-%m-%d'):
        # Handlers
        af = get_af_glob()
        self._fx = get_fx_glob()

        # Input data objects
        self._cmp = af.get(company)
        self._eq = af.get(self._cmp.equity)
        self._idx = af.get(self._eq.index)

        # Calculate dates
        self._ph = int(past_horizon)
        self._fp = int(future_proj)
        if date is None:
            self._t0 = get_calendar_glob().t0
        elif isinstance(date, str):
            self._t0 = pd.to_datetime(date, format=date_fmt)
        self._start = self._t0 - pd.Timedelta(days=Cn.DAYS_IN_1Y * self._ph)

        # Working data
        self._dt = {}
        self._freq = None
        self._last_price = None
        self._is_calculated = False

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
        # price = self._eq.prices
        # ts, dt = price.values, price.index.values
        # ts, dt = Mat.trim_ts(ts, dt, self._start.asm8, self._t0.asm8)
        # idx = Mat.last_valid_index(ts)
        # v = ts[idx]
        v, dt, _ = self._eq.last_price(self._t0)
        cv_obj = self._fx.get(self._eq.currency, self._cmp.currency)
        self._last_price = v * cv_obj.get(dt)

    def _res_update(self, **kwargs):
        self._dt.update(kwargs)

    @abstractmethod
    def _check_applicability(self):
        """ Verify model's applicability conditions. """

    @abstractmethod
    def _calc_freq(self):
        """ Calculates model frequency. """

    @abstractmethod
    def _calculate(self):
        """ Perform main calculations. """

    @abstractmethod
    def _otf_calculate(self, **kwargs) -> dict:
        """ Perform on-the-fly calculations. """

    def _create_output(self, outputs: dict):
        res = self._RES_OBJ()
        for k, v in self._dt.items():
            setattr(res, k, v)
        for k, v in outputs.items():
            setattr(res, k, v)
        return res

    def result(self, **kwargs):
        # Main calculations
        if not self._is_calculated:
            self._calculate()
            self._is_calculated = True

        # On-the-fly calculations
        outputs = self._otf_calculate(**kwargs)

        # Output
        return self._create_output(outputs)
