#
# CAPM class
# Solves the CAPM model and calculates the Beta
#

from typing import Union, Iterable

from nfpy.Assets.Asset import Asset
from nfpy.Assets.Portfolio import Portfolio
from nfpy.Tools.Utilities import AttributizedDict


class CAPMResult(AttributizedDict):

    def __init__(self):
        super().__init__()
        self.labels = []
        self.beta = []
        self.var = []
        self.corr = []
        self.mkt = ''
        self.mkt_var = .0


class CAPM(object):
    """ Applies the CAPM model to a portfolio of equities (no bonds supported).
        The beta of each equity vs a market proxy is returned.
    """

    def __init__(self, mkt: Asset, ptf: Union[Portfolio, Iterable]):
        if not isinstance(mkt, Asset):
            raise TypeError('Market proxy (type: {}) is not a valid asset'.format(type(mkt)))
        self._mkt = mkt

        if isinstance(ptf, Portfolio):
            self.ptf = [a for a in ptf.constituents.values() if a.type == 'Equity']
        elif isinstance(ptf, Iterable):
            self.ptf = [a for a in ptf if a.type == 'Equity']
        else:
            raise TypeError('Portfolio type (type: {}) is not a valid'.format(type(ptf)))

        self._resobj = None

    def result(self) -> CAPMResult:
        if not self._resobj:
            self._calculate()
        return self._resobj

    def _calculate(self):
        mr = self._mkt.returns
        mkt_var = mr.var()

        labels = []
        beta = []
        var = []
        corr = []
        for v in self.ptf:
            labels.append(v.uid)
            _var = v.returns.var()
            _corr = v.returns.corr(mr)
            var.append(_var)
            corr.append(_corr)
            beta.append(_var * _corr / mkt_var)

        res = CAPMResult()
        res.labels = labels
        res.beta = beta
        res.var = var
        res.corr = corr
        res.mkt = self._mkt.uid
        res.mkt_var = mkt_var
        self._resobj = res


def CAPModel(mkt: Asset, ptf: Union[Portfolio, Iterable]) -> CAPMResult:
    return CAPM(mkt, ptf).result()
