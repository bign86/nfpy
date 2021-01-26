#
# MEDM Report
# Report class for the Market Equity Data Model
#

from nfpy.Calendar import get_calendar_glob
import nfpy.Financial.Models as Mod
import nfpy.IO as IO
from nfpy.Tools import (Constants as Cn)

from .ReportMADM import ReportMADM


class ReportMEDM(ReportMADM):
    _M_OBJ = Mod.MarketEquityDataModel
    _M_LABEL = 'MEDM'
    _IMG_LABELS = ['p_price', 'perf', 'beta']

    def _create_output(self, res):
        """ Create the final output. """
        # Create the image path
        cal = get_calendar_glob()
        fig_full_name, fig_rel_name = self._get_image_paths(res.uid)

        # Relative path in results object
        res.img_prices_long = fig_rel_name[0]
        res.img_performance = fig_rel_name[1]
        res.img_beta = fig_rel_name[2]

        # Slow plot
        div_pl = IO.PlotTS()
        div_pl.add(res.prices)
        div_pl.plot()
        div_pl.save(fig_full_name[0])
        div_pl.clf()

        # Performance plot
        div_pl = IO.PlotTS()
        div_pl.add(res.perf, color='C0', linewidth=1.5, label=res.uid)
        div_pl.add(res.perf_idx, color='C2', linewidth=1.5, label='Index')

        div_pl.plot()
        div_pl.save(fig_full_name[1])

        # Beta plot
        start = cal.shift(res.date, -Cn.DAYS_IN_1Y, 'D')
        r = res.returns.loc[start:]
        ir = res.index_returns.loc[start:]
        beta = res.beta_params

        div_pl = IO.PlotBeta(x_zero=.0, y_zero=.0, xlim=(-.15, .15),
                             ylim=(-.15, .15))
        div_pl.add(ir.values, r.values, (beta[0], beta[2]))
        div_pl.plot()
        div_pl.save(fig_full_name[2])

        div_pl.close(True)

        return res
