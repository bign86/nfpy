#
# MPDM Report
# Report class for the Market Portfolio Data Model
#

from nfpy.Financial.Models import MarketPortfolioDataModel

from .ReportMADM import ReportMADM


class ReportMPDM(ReportMADM):
    _M_OBJ = MarketPortfolioDataModel
    _M_LABEL = 'MPDM'
