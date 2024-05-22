#
# Utilities
# Various utilities
#

import importlib

from pathlib import Path
from typing import Union, Sequence


class AttributizedDict(dict):
    """ Redefinition of dict to support attributes. Taken from Scipy. """

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __repr__(self):
        if self.keys():
            m = max(map(len, list(self.keys()))) + 1
            return '\n'.join(f"{k.rjust(m)}: {repr(v)}" for k, v in self.items())
        else:
            return f"{self.__class__.__name__}()"


class FileObject(AttributizedDict):
    """ Simple redefinition of an AttributizedDict to read a file descriptor
        and store the read data into the 'text' attribute.
    """

    def __init__(self, fname: Union[str, Path]):
        super().__init__()
        self._text = None
        self.status_code = None
        self.path = self._validate_path(fname)

    @property
    def text(self) -> str:
        """ Return the content of the file as a string. """
        if self._text is None:
            self._text = self._read()
        return self._text

    def _validate_path(self, fname: Union[str, Path]) -> Path:
        """ Transforms the path in to a pathlib object id not already done and
            validates the file.
        """
        if isinstance(fname, str):
            fname = Path(fname)
        self.status_code = 200 if fname.is_file() else 500
        return fname

    def _read(self) -> str:
        """ Read the entire file from disk into memory. Batch mode NOT supported. """
        if self.status_code != 200:
            msg = f'Cannot open file {self.path} with status code {self.status_code}'
            raise RuntimeError(msg)
        with self.path.open(mode='r') as fd:
            text = ''.join(fd.readlines())
        return text


def import_symbol(name: str, pkg: str = None):
    """ Function to dynamically load a symbol inside a module. """
    mod, _, symbol = name.rpartition('.')
    _mod = importlib.import_module(mod, package=pkg)
    return getattr(_mod, symbol)


def list_to_dict(v: Sequence) -> dict:
    """ Transforms a sequence into a dictionary. Passing either a flat sequence
        structured as [key1, value1, key2, value2, ...], or a nested sequence
        structured as [(key1, x1, y1, z1), (key2, x2, y2, z2), ...].
        In the first case the flat sequence must have an even length.
    """
    if not v:
        return {}

    elif isinstance(v[0], (set, list, tuple)):
        return {key: (*d,) for key, *d in v}

    else:
        if len(v) % 2 != 0:
            raise ValueError("Cannot make an odd flat list into a dictionary.")
        return dict(zip(v[::2], v[1::2]))


def ordered_unique(v: Sequence) -> Sequence:
    """ Create an ordered list of unique elements. """
    seen = set()
    seen_add = seen.add
    return [x for x in v if not (x in seen or seen_add(x))]
