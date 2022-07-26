#
# Rate factory class
# Class to handle rate and curves
#

from nfpy.Assets import get_af_glob
import nfpy.DB as DB
from nfpy.Tools import (Singleton, Exceptions as Ex)


class RateFactory(metaclass=Singleton):
    """ Factory to handle rates and curves. """

    _CURVE_TABLE = 'Curve'
    _RATE_TABLE = 'Rate'
    _Q_GET_RATES = """
    select currency, uid, NULL, NULL from Rate where is_ccy_rf  = 1
    union select country, min(country_rf), min(gdp), min(inflation) from (
    select country, iif(is_country_rf,uid,NULL) as country_rf,
    iif(is_gdp,uid,NULL) as gdp, iif(is_inflation,uid,NULL) as inflation
    from Rate where is_country_rf or is_gdp or is_inflation) as t
    group by country"""

    def __init__(self):
        self._db = DB.get_db_glob()
        self._qb = DB.get_qb_glob()
        self._af = get_af_glob()
        self._rates = {}

        self._initialize()

    def _initialize(self):
        res = self._db.execute(self._Q_GET_RATES).fetchall()
        if not res:
            raise Ex.MissingData('RateFactory._initialize(): No data found in the database')

        self._rates = {t[0]: t[1:] for t in res}

    def get_gdp(self, country: str):
        try:
            uid = self._rates[country][1]
        except KeyError:
            raise Ex.MissingData(f'No GDP rate set for country {country}')
        else:
            if uid is None:
                raise Ex.MissingData(f'No GDP rate rate set for country {country}')
        return self._af.get(uid)

    def get_inflation(self, country: str):
        try:
            uid = self._rates[country][2]
        except KeyError:
            raise Ex.MissingData(f'No inflation rate set for country {country}')
        else:
            if uid is None:
                raise Ex.MissingData(f'No inflation rate set for country {country}')
        return self._af.get(uid)

    def get_rf(self, label: str):
        try:
            uid = self._rates[label][0]
        except KeyError:
            raise Ex.MissingData(f'No risk free set for ID {label}')
        else:
            if uid is None:
                raise Ex.MissingData(f'No risk free rate set for country {label}')
        return self._af.get(uid)


def get_rf_glob() -> RateFactory:
    """ Returns the pointer to the global RateFactory """
    return RateFactory()
