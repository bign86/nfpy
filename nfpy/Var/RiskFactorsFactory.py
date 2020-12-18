#
# RiskFactors factory class
# Class to build the risk factors tree
#


class RiskFactorsFactory(object):
    """ Factory to create the risk factors tree from the asset objects """

    def __init__(self):
        self._models_map = {}
        self._assets = {}
        self._rf = {}
        self._tree = {}

    def get(self):
        pass

    def set(self, assets):
        pass
