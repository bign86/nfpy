#
# Utilities
# Various utilities
#

import importlib

from enum import Enum
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
        """ Tranform the path in to a pathlib object id not already done and
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


def print_sequence(seq: Sequence, showindex: bool = False) -> None:
    """ A super simple poor man's tabulate. """
    if showindex:
        print('\n'.join(f'{i}\t{v}' for i, v in enumerate(seq)))
    else:
        print('\n'.join(str(v) for v in seq))


class Col(Enum):
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_exc(ex: BaseException) -> None:
    """ Print a raised exception. Gives consistency across the library. """
    print(f'{Col.FAIL.value}!!!{type(ex).__name__}{Col.ENDC.value} - {ex}')


def print_header(msg: str, end: str = '\n') -> None:
    """ Print a message in header style. """
    print(f'{Col.HEADER.value}{Col.BOLD.value}{msg}{Col.ENDC.value}', end=end)


def print_highlight(msg: str, end: str = '\n') -> None:
    """ Print a message in highlighted style. """
    print(f'{Col.OKCYAN.value}{msg}{Col.ENDC.value}', end=end)


def print_ok(msg: str, end: str = '\n') -> None:
    """ Print a *all good* message. """
    print(f'{Col.OKGREEN.value}OK{Col.ENDC.value} - {msg}', end=end)


def print_warn(msg: str, end: str = '\n') -> None:
    """ Print a warning message. """
    print(f'{Col.WARNING.value}--- {msg}', end=end)


def print_wrn(wrn: Warning, end: str = '\n') -> None:
    """ Print a raised warning. Gives consistency across the library. """
    print(f'{Col.WARNING.value}---{type(wrn).__name__}{Col.ENDC.value} - {wrn}', end=end)


def print_deprecation(msg: str) -> None:
    """ Print a deprecation message. """
    wrn = f'{Col.WARNING.value}Deprecation warning!: {msg}{Col.ENDC.value}'
    print(wrn)
    # warnings.warn(wrn, DeprecationWarning, stacklevel=2)


def ordered_unique(v: Sequence) -> Sequence:
    """ Create an ordered list of unique elements. """
    seen = set()
    seen_add = seen.add
    return [x for x in v if not (x in seen or seen_add(x))]


def to_bool(v: str) -> bool:
    """ Transform a string into a boolean. Return an exception if not possible. """
    vl = v.lower()
    if vl in ('y', 'yes', '1', 'true', 't'):
        return True
    elif vl in ('n', 'no', '0', 'false', 'f'):
        return False
    else:
        raise ValueError(f'InputHandler(): {v} not recognized as boolean')


def check_mandatory_args(blocks: Sequence[dict], args) -> bool:
    """ Check if arguments are consistent. The non-none arguments are compared
        groups of arguments that constitute a complete set to identify whether
        there is at least one complete configuration.
        For example, it is usually the case that -i, --interactive constitutes
        one block by itself, another block may be constituted by the minimal
        configuration to provide if interactive is disabled.
    """
    good_block_found = False

    for block in blocks:
        block_valid = True

        for key, val in block.items():
            if key not in args:
                block_valid = False
                break
            else:
                if (val is not None) & (getattr(args, key) != val):
                    block_valid = False
                    break
                elif (val is None) & (getattr(args, key) is None):
                    block_valid = False
                    break

        if block_valid:
            good_block_found = True
            break

    return good_block_found
