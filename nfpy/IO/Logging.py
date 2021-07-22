#
# Logging
# Class for logging
#

from enum import Enum
import logging


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


class Logging(object):
    """ Object to handle inputs and wrapping all relevant input and input
        validation methods.
    """

    def __init__(self):
        pass


def print_exc(ex: BaseException) -> None:
    """ Print a raised exception. Gives consistency across the library. """
    print('{}!!!{}{} - {}'.format(Col.FAIL.value, type(ex).__name__,
                                  Col.ENDC.value, ex))


def print_wrn(wrn: Warning) -> None:
    """ Print a raised warning. Gives consistency across the library. """
    print('{}---{}{} - {}'.format(Col.WARNING.value, type(wrn).__name__,
                                  Col.ENDC.value, wrn))
