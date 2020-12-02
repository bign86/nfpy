#
# Asset factory class
# Base class for a single asset
#

from nfpy.DB.DB import get_db_glob
from nfpy.Handlers.QueryBuilder import get_qb_glob
from nfpy.Tools.Exceptions import MissingData
from nfpy.Tools.Singleton import Singleton
from nfpy.Tools.Utilities import import_symbol


class AssetFactory(metaclass=Singleton):
    """ Factory to create asset objects from their types """

    _INFO_TABLE = 'Assets'

    def __init__(self):
        self._db = get_db_glob()
        self._qb = get_qb_glob()
        self._known_assets = {}

    def _fetch_asset(self, uid: str):
        """ Given the asset_type creates the correct asset object. """
        q = self._qb.select(self._INFO_TABLE, fields=['uid', 'type'], keys=['uid'])
        res = self._db.execute(q, (uid,)).fetchone()
        if not res:
            raise MissingData('{} not found in the asset types list!'.format(uid))

        atype = res[1]
        symbol = '.'.join(['nfpy.Assets', atype, atype])
        class_ = import_symbol(symbol)
        obj = class_(uid)
        obj.load()
        self._known_assets[uid] = obj
        return obj

    def exists(self, uid: str) -> bool:
        try:
            _ = self.get(uid)
        except MissingData:
            return False
        else:
            return True

    def get(self, uid: str):
        """ Return the correct asset object given the uid. """
        try:
            asset = self._known_assets[uid]
        except KeyError:
            asset = self._fetch_asset(uid)
        return asset

    def add(self, uid: str, asset_type: str):
        """ Add a new uid to the factory table. """
        q = self._qb.select(self._INFO_TABLE, fields=['uid'], keys=['uid'])
        r = self._db.execute(q, (uid,)).fetchall()
        if r:
            raise ValueError("'uid' = {} already present!".format(uid))

        q = self._qb.insert(self._INFO_TABLE)
        self._db.execute(q, (uid, asset_type), commit=True)

    def remove(self, uid: str):
        """ Remove an uid from the factory table. """
        if not isinstance(uid, str):
            raise TypeError("Only string accepted as inputs!")
        q = self._qb.delete(self._INFO_TABLE, fields=['uid'])
        self._db.execute(q, (uid,), commit=True)


def get_af_glob() -> AssetFactory:
    """ Returns the pointer to the global AssetFactory """
    return AssetFactory()
