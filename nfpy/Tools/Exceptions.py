#
# Exception
# Custom exceptions
#

# import warnings


class IsNoneError(RuntimeError):
    """ Thrown when something is found to be None and was not supposed to. """


class MissingData(RuntimeError):
    """ Thrown when something is not found in the database. """


class DatabaseError(RuntimeError):
    """ Thrown when something is wrong with the database. """


class CalendarError(RuntimeError):
    """ Thrown when something is wrong with the calendar. """


class ShortSeriesError(RuntimeError):
    """ Thrown when a series is too short. """


class AssetTypeError(RuntimeError):
    """ Thrown when the asset type is wrong. """


class NanPresent(RuntimeError):
    """ Thrown when NaNs are present where there should be none. """


class ConfigurationError(RuntimeError):
    """ Thrown when errors happen with the Configuration module. """


class MissingDataWarn(RuntimeWarning):
    """ Thrown when something non-critical is not found in the database. """


class UnsupportedWarning(Warning):
    """ Thrown when an unsopported feature is requested. """


class ToBeImplementedWarning(Warning):
    """ Thrown when a feature is planned to be supported in the future. """
