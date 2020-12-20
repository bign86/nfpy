#
# FinancialItem class
# Base class for financial items with biographical data
#

from typing import Union

from nfpy.Tools.DatatypeFactory import get_dt_glob
import nfpy.DB as DB
from nfpy.Tools import Exceptions as Ex


class FinancialItem(object):
    """ Base class for items with only biographical data. """

    _TYPE = ''
    _BASE_TABLE = ''

    def __init__(self, uid: str):
        self._qb = DB.get_qb_glob()
        self._db = DB.get_db_glob()
        self._dt = get_dt_glob()
        self._uid = str(uid)
        self._is_loaded = False

    @property
    def uid(self) -> str:
        return self._uid

    @property
    def asset_type(self) -> str:
        DeprecationWarning('Deprecated! Use type attribute instead!')
        return self.type

    @property
    def type(self) -> str:
        return self._TYPE

    @property
    def base_table(self) -> str:
        return self._BASE_TABLE

    def _get_dati_for_query(self, table: str, rolling: list = ()) -> tuple:
        """ Return a tuple with the data necessary for querying the database
            EXCLUDING the rolling keys
        """
        keys = [k for k in self._qb.get_keys(table) if k not in rolling]
        # the self.datatype is needed for the getattr
        data = tuple(getattr(self, k) for k in keys)
        return data

    def _fill_anag(self, res: Union[list, tuple], table: str, cols: list = None):
        """ Cycle through all fields setting the properties
        
            Input:
                _r [Union[list,tuple]]: results from query
                table [str]: source table
                cols [list]: list of columns used for the select. If None
                             all table columns are assumed

            Exception:
                AttributeError: if the attribute already exists. That may mean that
                        a column name in the table is conflicting with the
                        object attributes.

            The method does not override primary keys for safetyness
        """
        keys = [k for k in self._qb.get_keys(table)]
        if cols is None:
            cols = [c for c in self._qb.get_fields(table)]

        for i, f in enumerate(cols):
            if f in keys:
                continue
            setattr(self, f, res[i])

    def load(self):
        """ Load asset data from base table. Primary keys data must be known. """
        if self._is_loaded:
            return

        q = self._qb.select(self.base_table)
        data = self._get_dati_for_query(self.base_table)

        res = self._db.execute(q, data).fetchall()
        if not res:
            raise Ex.MissingData("{} not found in the database!".format(data))

        self._fill_anag(res[0], self.base_table)
        self._is_loaded = True

    def write(self):
        """ Write asset data to base table. """
        t = self.base_table

        # data for delete are made only by primary keys
        del_data = tuple(getattr(self, k, None) for k in self._qb.get_keys(t))
        if None in del_data:
            raise Ex.IsNoneError("One primary key is None in {}".format(self.uid))
        q = self._qb.delete(t)
        self._db.execute(q, del_data)

        # data for insert are everything. No need to check that primary
        # are filled since it is done in the delete part
        data = tuple(getattr(self, c, None) for c in self._qb.get_fields(t))
        q = self._qb.insert(t)
        self._db.execute(q, data, commit=True)
