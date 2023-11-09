#
# Financials factory
# Class to handle indexes, rates and curves
#

from typing import (Optional, Sequence, Union)

from nfpy.Assets import (get_af_glob, TyAsset)
import nfpy.DB as DB
from nfpy.Tools import (Singleton, Exceptions as Ex)


class FinancialsFactory(metaclass=Singleton):
    """ Factory to handle indexes, rates and curves. """

    _CURVES_TABLE = 'Curve'
    _RATES_TABLE = 'Rate'
    _INDICES_TABLE = 'Index'
    _Q_GET_RATES = """
select currency, uid, NULL, NULL, NULL
from Rate where is_ccy_rf  = 1
union
select country, min(country_rf), min(gdp_real), min(gdp_nominal), min(inflation)
from (select country, iif(is_country_rf, uid, NULL) as country_rf,
iif(is_gdp AND adjustment = 'R', uid, NULL) as gdp_real,
iif(is_gdp AND adjustment = 'N', uid, NULL) as gdp_nominal, 
iif(is_inflation_rate, uid, NULL) as inflation
from Rate where is_country_rf or is_gdp or is_inflation_rate
) as t group by country"""
    _Q_GET_INDICES = """
select country, min(gdp_real), min(gdp_nominal), min(inflation)
from (select country, iif(is_gdp AND adjustment = 'R', uid, NULL) as gdp_real,
iif(is_gdp AND adjustment = 'N', uid, NULL) as gdp_nominal, 
iif(is_inflation, uid, NULL) as inflation
from [Index] where is_gdp or is_inflation ) as t group by country"""

    def __init__(self):
        self._db = DB.get_db_glob()
        self._af = get_af_glob()
        self._rates = {}
        self._indices = {}

        self._initialize()

    def _initialize(self) -> None:
        res = self._db.execute(self._Q_GET_RATES).fetchall()
        if not res:
            raise Ex.MissingData('FinancialsFactory._initialize(): No rates data found in the database')

        self._rates = {t[0]: t[1:] for t in res}

        res = self._db.execute(self._Q_GET_INDICES).fetchall()
        if not res:
            raise Ex.MissingData('FinancialsFactory._initialize(): No indices data found in the database')

        self._indices = {t[0]: t[1:] for t in res}

    def get_gdp(self, country: str, mode: str) -> TyAsset:
        """ Get the GDP given a country. Both real (R) and nominal (N)
            measures are available.
        """
        try:
            mode_code = {'R': 0, 'N': 1}.get(mode)
        except KeyError:
            raise ValueError(f'FinancialsFactory(): mode {mode} not recognized')

        try:
            uid = self._indices[country][mode_code]
        except KeyError:
            raise Ex.MissingData(f'FinancialsFactory(): No GDP [{mode}] set for country {country}')
        else:
            if uid is None:
                raise Ex.MissingData(f'FinancialsFactory(): No GDP [{mode}] set for country {country}')

        return self._af.get(uid)

    def get_gdp_growth(self, country: str, mode: str) -> TyAsset:
        """ Get the GDP growth given a country. Both real (R) and nominal (N)
            measures are available.
        """
        try:
            mode_code = {'R': 1, 'N': 2}.get(mode)
        except KeyError:
            raise ValueError(f'FinancialsFactory(): mode {mode} not recognized')

        try:
            uid = self._rates[country][mode_code]
        except KeyError:
            raise Ex.MissingData(f'FinancialsFactory(): No GDP growth rate [{mode}] set for country {country}')
        else:
            if uid is None:
                raise Ex.MissingData(f'FinancialsFactory(): No GDP growth rate [{mode}] set for country {country}')

        return self._af.get(uid)

    def get_inflation(self, country: str) -> TyAsset:
        """ Get the inflation rate given the country. """
        try:
            uid = self._rates[country][3]
        except KeyError:
            raise Ex.MissingData(f'FinancialsFactory(): No inflation rate set for country {country}')
        else:
            if uid is None:
                raise Ex.MissingData(f'FinancialsFactory(): No inflation rate set for country {country}')
        return self._af.get(uid)

    def get_rf(self, label: str) -> TyAsset:
        """ Get the risk-free rate given the country or the currency label. """
        try:
            uid = self._rates[label][0]
        except KeyError:
            raise Ex.MissingData(f'FinancialsFactory(): No risk free set for ID {label}')
        else:
            if uid is None:
                raise Ex.MissingData(f'FinancialsFactory(): No risk free rate set for country {label}')
        return self._af.get(uid)

    def get_reference_index(self, country: Optional[str] = None,
                            ccy: Optional[str] = None, ac: Optional[str] = None)\
            -> Optional[Union[Sequence[str], str]]:
        """ Get the reference index given a combination of country, currency,
            asset class. None is returned for empty queries or no data found.
            This method calls the DB directly.
        """
        # For empty queries return
        if (not country) & (not ccy) & (not ac):
            return None

        labels = []
        if country is not None:
            labels.append(f'country={country}')
        if ccy is not None:
            labels.append(f'currency={ccy}')
        if ac is not None:
            labels.append(f'ac={ac}')

        where = ' and '.join(labels)
        q = f'select uid from Index where {where}'
        res = self._db.execute(q).fetchall()
        if not res:
            return None

        return res


def get_fin_glob() -> FinancialsFactory:
    """ Returns the pointer to the global FinancialsFactory. """
    return FinancialsFactory()
