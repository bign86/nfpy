#
# MEDM Report
# Report class for the Market Equity Data Model
#

from nfpy.Financial.Models import MarketEquityDataModel
from nfpy.Calendar import get_calendar_glob
import nfpy.IO as IO

from .ReportMADM import ReportMADM


class ReportMEDM(ReportMADM):
    _M_OBJ = MarketEquityDataModel
    _M_LABEL = 'MEDM'
    _IMG_LABELS = ['p_long', 'p_short', 'beta']

    def _create_output(self, res):
        """ Create the final output. """
        # Create the image path
        cal = get_calendar_glob()
        fig_full_name, fig_rel_name = self._get_image_paths(res.uid)

        # Relative path in results object
        res.img_prices_long = fig_rel_name[0]
        res.img_prices_short = fig_rel_name[1]
        res.img_beta = fig_rel_name[2]

        # Save out figure
        start = cal.shift(res.date, 120, 'D', fwd=False)
        p = res.prices

        div_pl = IO.PlotTS()
        div_pl.add(p)
        div_pl.add(res.ma_slow, color='C2', linewidth=1.5,
                   linestyle='--', label='MA slow')
        div_pl.plot()
        div_pl.save(fig_full_name[0])
        div_pl.clf()

        div_pl = IO.PlotTS()
        div_pl.add(p.loc[start:])
        div_pl.add(res.ma_fast[start:], color='C1', linewidth=1.5,
                   linestyle='--', label='MA fast')
        div_pl.add(res.ma_slow[start:], color='C2', linewidth=1.5,
                   linestyle='--', label='MA slow')
        div_pl.plot()
        div_pl.save(fig_full_name[1])

        start = cal.shift(res.date, 365, 'D', fwd=False)
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
