#
# Base Fundamental Model
# Base class for fundamental models
#

from abc import (ABCMeta, abstractmethod)
from typing import (Any, Optional, TypeVar)

import nfpy.Assets as Ast
from nfpy.Tools import Utilities as Ut


class FundamentalModelResult(Ut.AttributizedDict):
    """ Base object containing the results of the model. """


TyFundamentalModelResult = TypeVar(
    'TyFundamentalModelResult',
    bound=FundamentalModelResult
)


class BaseFundamentalModel(metaclass=ABCMeta):
    """ Base class from which fundamentals models are derived. """

    _RES_OBJ = None

    def __init__(self, uid: str):
        # Handlers
        self._af = Ast.get_af_glob()

        # Input variables
        self._uid = uid
        self._asset = self._af.get(uid)
        self._eq = self._af.get(self._asset.equity)

        # Working data
        self._dt = {}
        self._is_calculated = False
        self._freq = None

    @property
    def frequency(self) -> Any:
        if self._freq is None:
            self._calc_freq()
        return self._freq

    def _res_update(self, **kwargs) -> None:
        self._dt.update(kwargs)

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

        # On-the-fly calculations and outputs
        return self._create_output(
            self._otf_calculate(**kwargs)
        )

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
