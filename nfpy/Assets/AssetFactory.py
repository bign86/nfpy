#
# Asset factory class
# Base class for a single asset
#

import nfpy.IO.DB as DB
from nfpy.Tools import (Singleton, Exceptions as Ex, Utilities as Ut)

from .FinancialItem import TyFI


class AssetFactory(metaclass=Singleton):
    """ Factory to create asset objects from their types """

    _INFO_TABLE = 'Assets'

    def __init__(self):
        self._db = DB.get_db_glob()
        self._qb = DB.get_qb_glob()
        self._known_assets = {}

    def _fetch_type(self, uid: str) -> str:
        """ Fetch the correct asset type. """
        q = self._qb.select(self._INFO_TABLE, fields=['uid', 'type'], keys=['uid'])
        res = self._db.execute(q, (uid,)).fetchone()
        if not res:
            raise Ex.MissingData('{} not found in the asset types list!'
                                 .format(uid))
        return res[1]

    def _create_obj(self, uid: str) -> TyFI:
        """ Given the asset_type creates the correct asset object. """
        a_type = self._fetch_type(uid)

        # atype = res[1]
        symbol = '.'.join(['nfpy.Assets', a_type, a_type])
        class_ = Ut.import_symbol(symbol)
        obj = class_(uid)
        obj.load()
        self._known_assets[uid] = obj
        return obj

    def exists(self, uid: str) -> bool:
        try:
            _ = self.get_type(uid)
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

    def get_type(self, uid: str) -> str:
        """ Return the asset type for the given uid. """
        try:
            a_type = self._known_assets[uid].type
        except KeyError:
            a_type = self._fetch_type(uid)
        return a_type

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
