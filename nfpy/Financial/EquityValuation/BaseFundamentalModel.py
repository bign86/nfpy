#
# Base Fundamental Model
# Base class for fundamental models
#

from abc import (ABCMeta, abstractmethod)
import pandas as pd
from typing import (Any, Optional, TypeVar)

import nfpy.Assets as Ast
import nfpy.Calendar as Cal
from nfpy.Tools import (Constants as Cn, Utilities as Ut)


class FundamentalModelResult(Ut.AttributizedDict):
    """ Base object containing the results of the model. """


TyFundamentalModelResult = TypeVar(
    'TyFundamentalModelResult',
    bound=FundamentalModelResult
)


class BaseFundamentalModel(metaclass=ABCMeta):
    """ Base class from which fundamentals models are derived. """

    _RES_OBJ = None

    def __init__(self, uid: str, date: Optional[Cal.TyDate] = None,
                 past_horizon: int = 5, future_proj: int = 3):
        # Handlers
        self._af = Ast.get_af_glob()
        self._cal = Cal.get_calendar_glob()
        self._fx = Ast.get_fx_glob()

        # Input variables
        self._uid = uid
        self._asset = self._af.get(uid)
        self._eq = self._af.get(self._asset.equity)
        self._idx = self._af.get(self._eq.index)
        self._ph = int(past_horizon)
        self._fp = int(future_proj)

        if date is None:
            self._t0 = self._cal.t0
        elif isinstance(date, str):
            self._t0 = pd.to_datetime(date, format='%Y-%m-%d')
        self._start = self._t0 - pd.Timedelta(days=Cn.DAYS_IN_1Y * self._ph)

        # Working data
        self._dt = {}
        self._is_calculated = False
        self._freq = None
        self._last_price = None

    @property
    # FIXME: not a Timestamp
    def t0(self) -> Cal.TyDate:
        return self._t0

    @property
    def frequency(self) -> Any:
        if self._freq is None:
            self._calc_freq()
        return self._freq

    def get_last_price(self) -> float:
        if not self._last_price:
            self._calc_last_price()
        return self._last_price

    def _res_update(self, **kwargs) -> None:
        self._dt.update(kwargs)

    def _calc_last_price(self) -> None:
        """ Returns the last price of the company's equity converted in the
            same currency as the company for consistency with the reported
            financial statements figures.
        """
        v, dt, _ = self._eq.last_price(self._t0)
        cv_obj = self._fx.get(self._eq.currency, self._asset.currency)
        self._last_price = v * cv_obj.get(dt)

    def _create_output(self, outputs: Optional[dict] = None) \
            -> TyFundamentalModelResult:
        res = self._RES_OBJ()
        for k, v in self._dt.items():
            setattr(res, k, v)
        if outputs:
            for k, v in outputs.items():
                setattr(res, k, v)
        return res

    def result(self, **kwargs) -> TyFundamentalModelResult:
        # Main calculations
        if not self._is_calculated:
            self._calculate()
            self._is_calculated = True

        # On-the-fly calculations
        outputs = self._otf_calculate(**kwargs)

        # Output
        return self._create_output(outputs)

    @abstractmethod
    def _check_applicability(self) -> None:
        """ Verify model's applicability conditions. """

    @abstractmethod
    def _calculate(self) -> None:
        """ Perform main calculations. """

    @abstractmethod
    def _otf_calculate(self, **kwargs) -> dict:
        """ Perform on-the-fly calculations. """

    @abstractmethod
    def _calc_freq(self) -> None:
        """ Calculates model frequency. """


TyFundamentalModel = TypeVar(
    'TyFundamentalModel',
    bound=BaseFundamentalModel
)
