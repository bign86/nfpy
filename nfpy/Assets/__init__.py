from .AssetFactory import get_af_glob
from .Asset import Asset
from .Bond import Bond
from .Company import Company
from .Currency import Currency
from .Curve import Curve
from .Equity import Equity
from .Indices import Indices
from .Portfolio import Portfolio
from .Rate import Rate

from typing import Union

TyAsset = Union[Asset, Bond, Currency, Equity, Indices, Rate]
TyAggregation = Union[Company, Curve, Portfolio]

__all__ = [
    'get_af_glob', 'TyAsset', 'TyAggregation',
    'Asset', 'Bond', 'Company', 'Currency', 'Curve',
    'Equity', 'Indices', 'Portfolio', 'Rate'
]
