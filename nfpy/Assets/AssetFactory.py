#
# Asset factory class
# Base class for a single asset
#

from nfpy.Calendar import Frequency
import nfpy.DB as DB
from nfpy.Tools import (Singleton, Exceptions as Ex, Utilities as Ut)

from .Asset import TyAsset
from .FinancialItem import TyFI


class AssetFactory(metaclass=Singleton):
    """ Factory to create asset objects from their types """

    _ASSETS_VIEW = 'Assets'
    _ASSET_TYPES = {'Bond', 'Company', 'Curve', 'Etf', 'Equity', 'Fx',
                    'Index', 'Portfolio', 'Rate'}

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
        self._qb = DB.get_qb_glob()

        self._known_assets = {}
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

    @property
    def asset_types(self) -> set:
        return self._ASSET_TYPES

    def _fetch_type(self, uid: str) -> str:
        """ Fetch the correct asset type. """
        res = self._db.execute(
            self._qb.select(
                self._ASSETS_VIEW,
                fields=('uid', 'type'),
                keys=('uid',)
            ),
            (uid,)
        ).fetchone()
        if not res:
            raise Ex.MissingData(f'{uid} not found in the asset types list!')
        return res[1]

    def _create_obj(self, uid: str) -> TyFI:
        """ Given the asset_type creates the correct asset object. """
        a_type = self._fetch_type(uid)

        symbol = '.'.join(['nfpy.Assets', a_type, a_type])
        class_ = Ut.import_symbol(symbol)
        obj = class_(uid)
        obj.load()

        self._known_assets[uid] = obj
        return obj

    def exists(self, uid: str) -> bool:
        try:
            _ = self.get_asset_type(uid)
        except Ex.MissingData:
            return False
        else:
            return True

    def get(self, uid: str) -> TyFI:
        """ Return the correct asset object given the uid. """
        try:
            asset = self._known_assets[uid]
        except KeyError:
            asset = self._create_obj(uid)
        return asset

    def get_asset_type(self, uid: str) -> str:
        """ Return the asset type for the given uid. """
        try:
            a_type = self._known_assets[uid].type
        except KeyError:
            a_type = self._fetch_type(uid)
        return a_type

    def get_assets_in_class(self, asset_type: str) -> list:
        """ Return the list of all assets for a given asset type. """
        if asset_type not in self._ASSET_TYPES:
            raise ValueError(f'AssetFactory(): asset class {asset_type} not recognized')

        return self._db.execute(
            self._qb.select(
                self._ASSETS_VIEW,
                fields=('uid', 'type'),
                keys=('type',)
            ),
            (asset_type,)
        ).fetchall()

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
            return self.get(uid)

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
            tuple(data)
        ).fetchall()

        if len(res) == 1:
            return self.get(res[0][0])
        elif len(res) > 1:
            return tuple(v[0] for v in res)
        else:
            raise Ex.MissingData(f'FinancialsFactory(): No derived series found with given filters')

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

        return self.get(uid)

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

        return self.get(uid)

    def get_inflation(self, country: str) -> TyAsset:
        """ Get the inflation rate given the country. """
        try:
            uid = self._rates[country][3]
        except KeyError:
            raise Ex.MissingData(f'FinancialsFactory(): No inflation rate set for country {country}')
        else:
            if uid is None:
                raise Ex.MissingData(f'FinancialsFactory(): No inflation rate set for country {country}')
        return self.get(uid)

    def get_rf(self, label: str) -> TyAsset:
        """ Get the risk-free rate given the country or the currency label. """
        try:
            uid = self._rates[label][0]
        except KeyError:
            raise Ex.MissingData(f'FinancialsFactory(): No risk free set for ID {label}')
        else:
            if uid is None:
                raise Ex.MissingData(f'FinancialsFactory(): No risk free rate set for country {label}')
        return self.get(uid)

    def add(self, uid: str, asset_type: str) -> None:
        """ Add a new uid to the factory table. """
        r = self._db.execute(
            self._qb.select(
                self._ASSETS_VIEW,
                fields=('uid',),
                keys=('uid',)
            ),
            (uid,)
        ).fetchall()
        if r:
            raise ValueError(f"\'uid\' = {uid} already present!")

        self._db.execute(
            self._qb.insert(self._ASSETS_VIEW),
            (uid, asset_type),
            commit=True
        )

    def remove(self, uid: str) -> None:
        """ Remove an uid from the factory table. """
        self._db.execute(
            self._qb.delete(
                self._ASSETS_VIEW,
                fields=('uid',)
            ),
            (uid,),
            commit=True
        )


def get_af_glob() -> AssetFactory:
    """ Returns the pointer to the global AssetFactory """
    return AssetFactory()
