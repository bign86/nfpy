#
# MBDM Report
# Report class for the Market Bond Data Model
#

from nfpy.Calendar import get_calendar_glob
from nfpy.Financial.Models import MarketBondDataModel
import nfpy.IO as IO

from .ReportMADM import ReportMADM


class ReportMBDM(ReportMADM):
    _M_OBJ = MarketBondDataModel
    _M_LABEL = 'MBDM'
    _IMG_LABELS = ['p_long', 'p_short', 'price_ytm']

    def _create_output(self, res):
        """ Create the final output. """
        # Create the image path
        fig_full_name, fig_rel_name = self._get_image_paths(res.uid)

        # Relative path in results object
        res.prices_long = fig_rel_name[0]
        res.prices_short = fig_rel_name[1]
        res.prices_ytm = fig_rel_name[2]

        # Save out figure
        start = get_calendar_glob().shift(res.date, 120, 'D', fwd=False)
        p = res.prices
        y = res.yields

        div_pl = IO.PlotTS()
        div_pl.add(p, label='Price')
        div_pl.add(y, color='C2', label='Yield', secondary_y=True)
        div_pl.plot()
        div_pl.save(fig_full_name[0])
        div_pl.clf()

        div_pl = IO.PlotTS()
        div_pl.add(p.loc[start:], label='Price')
        div_pl.add(y.loc[start:], color='C2', label='Yield', secondary_y=True)
        div_pl.plot()
        div_pl.save(fig_full_name[1])
        div_pl.clf()

        data = res.yields_array
        bars = res.ytm_bars
        x_zero = res.yields_array[0, 3]
        y_zero = res.yields_array[1, 3]
        div_pl = IO.PlotTS(xl='Price', yl='YTM', y_zero=y_zero, x_zero=x_zero)
        div_pl.add(data[0, :], data[1, :], marker='', linestyle='-',
                   label=r'$YTM(P_0, t_0)$')
        div_pl.line('xh', bars[1, 0], linestyle='--', linewidth='.8',
                    color="C1", label=r'$YTM(P_0\pm\delta^{1M}, t_0)$')
        div_pl.line('xh', bars[1, 1], linestyle='--', linewidth='.8',
                    color="C1")
        div_pl.line('xh', bars[1, 2], linestyle='--', linewidth='.8',
                    color="C2", label=r'$YTM(P_0\pm\delta^{6M}, t_0)$')
        div_pl.line('xh', bars[1, 3], linestyle='--', linewidth='.8',
                    color="C2")
        div_pl.plot()
        div_pl.save(fig_full_name[2])

        div_pl.close(True)

        return res
