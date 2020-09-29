#
# Object for DB tables and columns
#

from collections import OrderedDict
from typing import Sequence, Generator
from nfpy.Tools.Utilities import AttributizedDict


class Column(AttributizedDict):
    """ Class that defines a database column with its properties. """

    def __init__(self, name: str):
        super().__init__()
        self.field = str(name)
        self.type = None
        self.ordinal = None
        self.notnull = False
        self.is_primary = False
        # self.is_rolling = False


class Table(object):
    """ Class to store table information (doesn't contain data). """

    # _STRUCT_F = ['field', 'ordinal', 'type', 'is_primary', 'notnull', 'is_rolling']
    _STRUCT_F = ['field', 'ordinal', 'type', 'is_primary', 'notnull']

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
            m = max(map(len, list(self._fields.keys()))) + 1
            text = '\t'.join([k.rjust(m) for k in self._STRUCT_F]) + '\n'
            for k, c in self._fields.items():
                values = [str(c[f]) for f in self._STRUCT_F]
                text += '\t'.join([k.rjust(m) for k in values]) + '\n'
            return text
        else:
            return self.__class__.__name__ + "()"

    def set_fields(self, v: Sequence):
        """ Create the sequence of column fields in the table. Any previous
            list of columns is overwritten.
        """
        assert isinstance(v, Sequence)
        l = [(k.field, k) for k in v]
        self._fields = OrderedDict(l)

    def add_field(self, v: Column):
        """ Add a column at the end of the table object. """
        self._fields[v.field] = v

    def remove_field(self, field: str):
        """ Remove a field from the table object. """
        del self._fields[field]

    def get_fields(self) -> Generator[str, None, None]:
        """ Return the generator of ordered fields in the table. """
        return self._fields.keys()

    def get_keys(self) -> Generator[str, None, None]:
        """ Return the generator of ordered primary keys in the table. """
        for k, v in self._fields.items():
            if v.is_primary:
                yield k

    """
    def get_rolling(self) -> Generator[str, None, None]:
        " Return the generator of rolling keys in the table. "
        for k, v in self._fields.items():
            if v.is_rolling:
                yield k
    """

    def get_num_cols(self) -> int:
        """ Return the length of the columns dictionary """
        return len(self._fields)

    """
    def set_is_rolling(self, fields, flag: bool = True):
        ''' Set the listed fields as rolling or not based on the flag. All
            listed fields are set to the same truth value.
        '''
        if isinstance(fields, str):
            fields = list(fields)
        for f in fields:
            self._fields[f].is_rolling = flag

    def is_rolling(self, field: str) -> bool:
        " Check whether the given field is a rolling key. "
        return self._fields[field].is_rolling
    """

    def is_primary(self, field: str) -> bool:
        """ Check whether the given field is a primary key. """
        return self._fields[field].is_primary
