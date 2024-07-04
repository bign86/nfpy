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


class DatatypeError(RuntimeError):
    """ Thrown when a datatype is wrong or un-existent. """


class ShapeError(RuntimeError):
    """ Thrown when an array has the wrong shape. """


class InputHandlingError(RuntimeError):
    """ Thrown when there is an issue with the input handler. """


class UidMalformedError(RuntimeError):
    """ Thrown when a UID contains forbidden characters. """


class LoggerError(RuntimeError):
    """ Thrown on any error in the logger. """

class MissingDataWarn(RuntimeWarning):
    """ Thrown when something non-critical is not found in the database. """


class UnsupportedWarning(RuntimeWarning):
    """ Thrown when an unsupported feature is requested. """


class ToBeImplementedWarning(RuntimeWarning):
    """ Thrown when a feature is planned to be supported in the future. """


class NoNewDataWarning(RuntimeWarning):
    """ Thrown when a no new data are found in a download. """
