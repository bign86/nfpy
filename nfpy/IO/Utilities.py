#
# IO utilities
# Utility functions related to IO
#

from enum import Enum
import re
from typing import (Optional, Sequence)


def to_bool(v: str) -> bool | None:
    """ Transforms a string into a boolean. Return an exception if not possible. """
    vl = v.lower()
    if vl in ('y', 'yes', '1', 'true', 't'):
        return True
    elif vl in ('n', 'no', '0', 'false', 'f'):
        return False
    else:
        return None


def to_string(v: str) -> str:
    return re.sub('[!@#$?*;:+]', '', v)


def to_isin(v: str) -> Optional[str]:
    pattern = re.compile("^([a-zA-Z]{2}[a-zA-Z0-9]{9}[0-9])$")
    return pattern.match(to_string(v))


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


def print_deprecation(msg: str) -> None:
    """ Print a deprecation message. """
    wrn = f'{Col.WARNING.value}Deprecation warning!: {msg}{Col.ENDC.value}'
    print(wrn)
    # warnings.warn(wrn, DeprecationWarning, stacklevel=2)


def print_exc(ex: BaseException) -> None:
    """ Print a raised exception. Gives consistency across the library. """
    print(f'{Col.FAIL.value}ERR {type(ex).__name__}{Col.ENDC.value} - {ex}')


def print_header(msg: str, end: str = '\n') -> None:
    """ Print a message in header style. """
    print(f'{Col.HEADER.value}{Col.BOLD.value}{msg}{Col.ENDC.value}', end=end)


def print_highlight(msg: str, end: str = '\n') -> None:
    """ Print a message in highlighted style. """
    print(f'{Col.OKCYAN.value}{msg}{Col.ENDC.value}', end=end)


def print_ok(msg: str, end: str = '\n') -> None:
    """ Print a *all good* message. """
    print(f'{Col.OKGREEN.value}OK{Col.ENDC.value} - {msg}', end=end)


def print_sequence(seq: Sequence, showindex: bool = False) -> None:
    """ A super simple poor man's tabulate. """
    if showindex:
        print('\n'.join(f'{i}\t{v}' for i, v in enumerate(seq)))
    else:
        print('\n'.join(str(v) for v in seq))


def print_warn(msg: str, end: str = '\n') -> None:
    """ Print a warning message. """
    print(f'{Col.WARNING.value}WARN {Col.ENDC.value} {msg}', end=end)


def print_wrn(wrn: Warning, end: str = '\n') -> None:
    """ Print a raised warning. Gives consistency across the library. """
    print(f'{Col.WARNING.value}WARN {type(wrn).__name__}{Col.ENDC.value} - {wrn}', end=end)


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
