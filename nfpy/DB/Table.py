#
# Object for DB tables and columns
#

from collections import OrderedDict
from typing import (Any, Generator, KeysView)

from nfpy.Tools import Utilities as Ut


class Column(Ut.AttributizedDict):
    """ Class that defines a database column with its properties. """

    def __init__(self, name: str):
        super().__init__()
        self.field = str(name)
        self.type = None
        self.ordinal = None
        self.notnull = False
        self.is_primary = False


class Table(object):
    """ Class to store table information (doesn't contain data). """

    _STRUCT_F = ('field', 'ordinal', 'type', 'is_primary', 'notnull')

    def __init__(self, name: str):
        self._name = str(name)
        self._fields = OrderedDict()

    @property
    def name(self) -> str:
        return self._name

    @property
    def columns(self) -> OrderedDict:
        return self._fields

    def __len__(self) -> int:
        return len(self._fields)

    @property
    def structure(self) -> str:
        """ Return the table structure as a string. """
        if self._fields.keys():
            m = max(map(len, self._fields.keys())) + 1
            text = '\t'.join([k.rjust(m) for k in self._STRUCT_F]) + '\n'
            text += '-'*80 + '\n'
            for k, c in self._fields.items():
                values = [str(c[f]) for f in self._STRUCT_F]
                text += '\t'.join([k.rjust(m) for k in values]) + '\n'
            return text
        else:
            return self.__class__.__name__ + "()"

    def set_fields(self, v: [Column]) -> None:
        """ Create the sequence of column fields in the table. Any previous
            list of columns is overwritten.
        """
        self._fields = OrderedDict(
            [
                (k.field, k) for k in v
            ]
        )

    def add_field(self, v: Column) -> None:
        """ Add a column at the end of the table object. """
        self._fields[v.field] = v

    def remove_field(self, field: str) -> None:
        """ Remove a field from the table object. """
        del self._fields[field]

    def get_fields(self) -> KeysView:
        """ Return the generator of ordered fields in the table. """
        return self._fields.keys()

    def get_keys(self) -> Generator[Any, Any, None]:
        """ Return the generator of ordered primary keys in the table. """
        # for k, v in self._fields.items():
        #     if v.is_primary:
        #         yield k
        return (
            k
            for k, v in self._fields.items()
            if v.is_primary
        )

    def is_primary(self, field: str) -> bool:
        """ Check whether the given field is a primary key. """
        return self._fields[field].is_primary
