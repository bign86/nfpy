#
# Financials factory
# Class to handle indexes, rates and curves
#


from nfpy.Assets import (get_af_glob, TyAsset)
from nfpy.Calendar import Frequency
import nfpy.DB as DB
import nfpy.IO.Utilities as Ut
from nfpy.Tools import (Singleton, Exceptions as Ex)


class FinancialsFactory(metaclass=Singleton):
    """ Factory to handle indexes, rates and curves. """

    _Q_GET_RATES = """
SELECT c.symbol, r.uid, NULL, NULL, NULL
FROM Currency AS c
JOIN Rate AS r ON r.currency = COALESCE(c.pegged, c.symbol)
WHERE r.is_ccy_rf  = 1
UNION
SELECT country, MIN(country_rf), MIN(gdp_real),
    MIN(gdp_nominal), MIN(inflation)
    FROM (
        SELECT country, IIF(is_country_rf, uid, NULL) AS country_rf,
            IIF(is_gdp AND adjustment = 'R', uid, NULL) AS gdp_real,
            IIF(is_gdp AND adjustment = 'N', uid, NULL) AS gdp_nominal, 
            IIF(is_inflation_rate, uid, NULL) AS inflation
        FROM [Rate]
        WHERE is_country_rf  OR is_gdp  OR is_inflation_rate
    ) AS t
GROUP BY country;
"""
    _Q_GET_INDICES = """
SELECT country, MIN(gdp_real), MIN(gdp_nominal), MIN(inflation)
FROM (
    SELECT country,
        IIF(is_gdp AND adjustment = 'R', uid, NULL) AS gdp_real,
        IIF(is_gdp AND adjustment = 'N', uid, NULL) AS gdp_nominal, 
        IIF(is_inflation, uid, NULL) AS inflation
    FROM [Index]
    WHERE is_gdp OR is_inflation
) AS t
GROUP BY country;
"""

    def __init__(self):
        self._db = DB.get_db_glob()
        self._af = get_af_glob()
        self._qb = DB.get_qb_glob()
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

    # def get_reference_index(
    #         self,
    #         country: str | None = None,
    #         ccy: str | None = None,
    #         ac: str | None = None
    # ) -> Sequence[str] | str | None:
    #     """ Get the reference index given a combination of country, currency,
    #         asset class. None is returned for empty queries or no data found.
    #         This method calls the DB directly.
    #     """
    #     # For empty queries return
    #     if (not country) & (not ccy) & (not ac):
    #         return None
    #
    #     labels = []
    #     if country is not None:
    #         labels.append(f'[country]={country}')
    #     if ccy is not None:
    #         labels.append(f'[currency]={ccy}')
    #     if ac is not None:
    #         labels.append(f'[ac]={ac}')
    #
    #     where = ' AND '.join(labels)
    #     q = f'SELECT [uid] FROM [Index] WHERE {where}'
    #     res = self._db.execute(q).fetchall()
    #     if not res:
    #         return None
    #
    #     return res

    def get_derived_series(
            self,
            uid: str | None = None,
            asset1: str | None = None,
            asset2: str | None = None,
            frequency: Frequency | None = None,
            horizon: str | None = None,
    ) -> TyAsset | tuple[str, ...]:
        # If uid is given, fetch that
        if uid:
            return self._af.get(uid)

        # If some other filter is given try to get one single series
        keys, data = [], []
        if asset1:
            keys.append('asset1')
            data.append(asset1)
        if asset2:
            keys.append('asset2')
            data.append(asset2)
        if frequency:
            keys.append('frequency')
            data.append(frequency.value)
        if horizon:
            keys.append('horizon')
            data.append(horizon)

        res = self._db.execute(
            self._qb.select(
                'DerivedSeries',
                fields=('uid',),
                keys=keys
            ),
            data
        ).fetchall()

        if len(res) == 1:
            return self._af.get(res[0])
        elif len(res) > 1:
            return tuple(v[0] for v in res)
        else:
            raise Ex.MissingData(f'FinancialsFactory(): No derived series found with given filters')


def get_fin_glob() -> FinancialsFactory:
    """ Returns the pointer to the global FinancialsFactory. """
    Ut.print_deprecation('FinancialsFactory() -> AssetFactory()')
    return FinancialsFactory()
