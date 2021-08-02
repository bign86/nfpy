#
# Base Model
# Base class for all models
#

from abc import (ABCMeta, abstractmethod)
import pandas as pd
from typing import (Union, TypeVar)

from nfpy.Assets import get_af_glob
import nfpy.Calendar as Cal
from nfpy.Tools import Utilities as Ut

import nfpy.Financial as Fin


class BaseModelResult(Ut.AttributizedDict):
    """ Base object containing the results of the model. """


class BaseModel(metaclass=ABCMeta):
    """ Base class from which all models are derived. """

    _RES_OBJ = None

    def __init__(self, uid: str, date: Union[str, pd.Timestamp] = None,
                 **kwargs):
        # Handlers
        self._af = get_af_glob()
        self._fx = Fin.get_fx_glob()

        # Input data objects
        self._uid = uid
        self._asset = self._af.get(uid)

        # FIXME: should be a Timestamp or a datetime64.
        #       if True: is a Timestamp
        #       if False: is a datetime
        if date is None:
            self._t0 = Cal.get_calendar_glob().t0
        elif isinstance(date, str):
            self._t0 = pd.to_datetime(date, format='%Y-%m-%d')

        # Working data
        self._dt = {}
        self._is_calculated = False

    @property
    # FIXME: not a Timestamp
    def t0(self) -> Cal.TyDate:
        return self._t0

    def _res_update(self, **kwargs):
        self._dt.update(kwargs)

    @abstractmethod
    def _check_applicability(self):
        """ Verify model's applicability conditions. """

    @abstractmethod
    def _calculate(self):
        """ Perform main calculations. """

    @abstractmethod
    def _otf_calculate(self, **kwargs) -> dict:
        """ Perform on-the-fly calculations. """

    def _create_output(self, outputs: dict = None):
        res = self._RES_OBJ()
        for k, v in self._dt.items():
            setattr(res, k, v)
        if outputs:
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


TyModelResult = TypeVar('TyModelResult', bound=BaseModelResult)
TyModel = TypeVar('TyModel', bound=BaseModel)
