#
# Exception
# Custom exceptions
#

# import warnings


class IsNoneError(RuntimeError):
    """ This exception should be thrown when something is found to be None and
        was not supposed to.
    """


class MissingData(RuntimeError):
    """ This exception should be thrown when something is not found. """


class DatabaseError(RuntimeError):
    """ This exception should be thrown when something is wrong with the database. """


class CalendarError(RuntimeError):
    """ This exception should be thrown when something is wrong with the calendar. """


class ShortSeriesError(RuntimeError):
    """ This exception should be thrown when a series is too short. """


class AssetTypeError(RuntimeError):
    """ This exception should be thrown when the asset type is wrong. """


class MissingDataWarn(RuntimeWarning):
    """ This warning should be used when something non-critical is not found. """


class UnsupportedWarning(Warning):
    """ This warning should be thrown when an unsopported feature is requested. """


class ToBeImplementedWarning(Warning):
    """ This warning should be thrown when a feature is planned to be
        supported in the future.
    """
