#
# MPDM Report
# Report class for the Market Portfolio Data Model
#

import nfpy.Financial.Models as Mod

from .ReportMADM import ReportMADM


class ReportMPDM(ReportMADM):
    _M_OBJ = Mod.MarketPortfolioDataModel
    _M_LABEL = 'MPDM'
