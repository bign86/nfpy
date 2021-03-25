#
# MPDM Report
# Report class for the Market Portfolio Data Model
#

import nfpy.Models as Mod

from .ReportMADM import ReportMADM


class ReportMPDM(ReportMADM):
    _M_OBJ = Mod.MarketPortfolioDataModel
    _M_LABEL = 'MPDM'

    def _create_output(self, res):
        """ Create the final output. """
        res = super()._create_output(res)

        # Render dataframes
        df = res.cnsts_data
        res.cnsts_data = df.style \
            .format('{:,.2f}', subset=['alp', 'cost (FX)',
                                       'value ({})'.format(res.currency)]) \
            .format('{:,.0f}', subset=['quantity']) \
            .format('{:,.1%}', subset=['weights']) \
            .hide_index() \
            .set_table_attributes('class="dataframe"') \
            .render()
        return res
