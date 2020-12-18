from .CALModel import CALModel
from .MarkowitzModel import MarkowitzModel
from .MaxSharpeModel import MaxSharpeModel
from .MinimalVarianceModel import MinimalVarianceModel
from .RiskParityModel import RiskParityModel

from typing import Union

TyOptimizer = Union[CALModel, MarkowitzModel, MaxSharpeModel,
                    MinimalVarianceModel, RiskParityModel]

__all__ = [
    'CALModel', 'MarkowitzModel', 'MaxSharpeModel',
    'MinimalVarianceModel', 'RiskParityModel', 'TyOptimizer'
]
