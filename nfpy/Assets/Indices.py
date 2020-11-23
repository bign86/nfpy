#
# Index class
# Class for indices
#

from nfpy.Assets.Asset import Asset


class Indices(Asset):
    """ Class for indices """

    _TYPE = 'Indices'
    _BASE_TABLE = 'Indices'
    _TS_TABLE = 'IndexTS'
    _TS_ROLL_KEY_LIST = ['date']
