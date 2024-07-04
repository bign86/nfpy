#
# Base Fundamental Model
# Base class for fundamental models
#

from abc import (ABCMeta, abstractmethod)
from copy import deepcopy
import dataclasses
from typing import (Any, TypeVar)

import nfpy.Assets as Ast
import nfpy.Calendar as Cal


@dataclasses.dataclass(init=False)
class FundamentalModelResult:
    """ Base object containing the results of the model. """
    applicable: bool = dataclasses.field(default=False, repr=False)
    last_price: float = dataclasses.field(default=None, repr=False)
    msg: str = dataclasses.field(default='', repr=True)
    outputs: dict = dataclasses.field(default_factory=dict, repr=False)
    success: bool = dataclasses.field(default=False, repr=True)
    uid: str = dataclasses.field(default=None, repr=False)

    def __bool__(self) -> bool:
        return self.success

    def __str__(self) -> str:
        return self.msg

    def set_outputs(self, dic):
        self.outputs.update(dic)


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
        self._cal = Cal.get_calendar_glob()

        # Input variables
        self._uid = uid

        asset = self._af.get(uid)
        if asset.type == 'Equity':
            self._eq = asset
            self._comp = self._af.get(asset.company)
        elif asset.type == 'Company':
            self._comp = asset
            self._eq = self._af.get(asset.equity)
        else:
            raise ValueError(f'BaseFundamentalModel(): something wrong with {uid}')

        # Working data
        self._res = self._RES_OBJ()
        self._is_calculated = False
        self._is_applicable = None
        self._freq = None
        self._last_price = self._eq.last_price()[0]

    @property
    def frequency(self) -> Any:
        if self._freq is None:
            self._calc_freq()
        return self._freq

    def _res_update(self, outputs: dict = None, success: bool = None,
                    applicable: bool = None, msg: str = None,
                    copy: bool = True) -> TyFundamentalModelResult:
        if copy:
            results = deepcopy(self._res)
        else:
            results = self._res

        if applicable:
            results.applicable = applicable
        if success:
            results.success = success
        if msg:
            results.msg = msg
        if outputs:
            results.set_outputs(outputs)

        return results

    def result(self, **kwargs) -> TyFundamentalModelResult:
        if self._is_applicable is None:
            applicable = self._check_applicability()
            self._is_applicable = applicable
            self._res.applicable = applicable
            self._res.uid = self._uid
            self._res.last_price = self._last_price

        if self._is_applicable:
            # Main calculations
            if not self._is_calculated:
                self._calculate()
                self._is_calculated = True

            # On-the-fly calculations and outputs
            self._res = self._res_update(
                **self._otf_calculate(**kwargs)
            )

        return self._res

    @abstractmethod
    def _check_applicability(self) -> bool:
        """ Verify model's applicability conditions. ***MUST*** return the
            value of the _is_applicable flag.
        """

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
