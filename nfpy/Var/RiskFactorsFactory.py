#
# RiskFactors factory class
# Class to build the risk factors tree
#

from nfpy.Assets.FinancialItem import FinancialItem
from nfpy.DB.DB import get_db_glob
from nfpy.Handlers.QueryBuilder import get_qb_glob
from nfpy.Tools.Exceptions import MissingData
from nfpy.Tools.Singleton import Singleton
from nfpy.Tools.Utilities import import_symbol, AttributizedDict






class RiskFactorsFactory(object):
    """ Factory to create the risk factors tree from the asset objects """

    def __init__(self):
        self._models_map = {}
        self._assets = {}
        self._rf = {}
        self._tree = {}

    def get(self):

    def set(self, assets):
