#
# Singleton Metaclass
# Base class for anything that must be a singleton
#


from abc import ABCMeta


class Singleton(type):
    """ Metaclass to define singletons. """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class SingletonMetaMixin(ABCMeta, Singleton):
    """ Metaclass to define abstract singletons. """
    pass
