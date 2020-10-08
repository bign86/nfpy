#
# Dtatyoe factory class
# Base class to handle datatypes
#

import warnings

from nfpy.Handlers.QueryBuilder import get_qb_glob
from nfpy.Tools.Singleton import Singleton
from nfpy.DB.DB import get_db_glob


class DatatypeFactory(metaclass=Singleton):
    """ Factory to deal with datatypes. """

    _DT_TABLE = 'DecDatatype'

    def __init__(self):
        self._db = get_db_glob()
        self._qb = get_qb_glob()
        self._dec_datatypes = {}
        self._mapping = {}
        self._codes_in_use = []
        self._initializations()

    def _initializations(self):
        """ Get the decodings from the database. """
        q = "select * from " + self._DT_TABLE
        res = self._db.execute(q).fetchall()
        self._dec_datatypes = dict(r for r in res)
        self._codes_in_use = [v for v in self._dec_datatypes.values()]
        self._mapping = {v: k for k, v in self._dec_datatypes.items()}

    def __contains__(self, dtype: str) -> bool:
        """ Check if a datatype is known. """
        return dtype in self._dec_datatypes
    
    def exists(self, dtype: str) -> bool:
        warnings.warn("Deprecated use __contains__ via the 'in' operator", DeprecationWarning)
        return self.__contains__(dtype)

    def is_code_available(self, code: int) -> bool:
        """ Check if a code is un-used in the database. """
        return code not in self._codes_in_use

    def remove(self, dtype: str):
        """ Remove a datatype from the table. """
        if dtype in self._dec_datatypes:
            q_del = self._qb.delete(self._DT_TABLE, ['datatype'])
            self._db.execute(q_del, (dtype,), commit=True)
            code = self._mapping[dtype]
            del self._dec_datatypes[dtype]
            del self._mapping[code]
            self._codes_in_use = [v for v in self._dec_datatypes.values()]
        else:
            raise RuntimeWarning("Datatype {} not found".format(dtype))

    def get(self, dtype: str) -> int:
        """ Return the decoded datatype.
        
            Input:
                dtype [str]: datatype label
            
            Output:
                code [int]: datatype decoded
        """
        try:
            dt = self._dec_datatypes[dtype]
        except KeyError:
            raise KeyError("Datatype {} not known!".format(dtype))
        return dt

    def teg(self, code: int) -> str:
        """ Return the endecoded datatype.

            Input:
                code [int]: datatype decoded

            Output:
                dtype [str]: datatype label
        """
        try:
            dt = self._mapping[code]
        except KeyError:
            raise KeyError("Encoded datatype {} not known!".format(code))
        return dt


def get_dt_glob() -> DatatypeFactory:
    """ Returns the pointer to the global DatatypeFactory """
    return DatatypeFactory()
