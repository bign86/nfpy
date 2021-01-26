#
# MBDM Report
# Report class for the Market Bond Data Model
#

import nfpy.Financial.Models as Mod
import nfpy.IO as IO

from .ReportMADM import ReportMADM


class ReportMBDM(ReportMADM):
    _M_OBJ = Mod.MarketBondDataModel
    _M_LABEL = 'MBDM'
    _IMG_LABELS = ['p_price', 'price_ytm']

    def _create_output(self, res):
        """ Create the final output. """
        # Create the image path
        fig_full_name, fig_rel_name = self._get_image_paths(res.uid)

        # Relative path in results object
        res.prices_long, res.prices_ytm = fig_rel_name

        p, y = res.prices, res.yields

        div_pl = IO.PlotTS()
        div_pl.add(p, label='Price')
        div_pl.add(y, color='C2', label='Yield', secondary_y=True)
        div_pl.plot()
        div_pl.save(fig_full_name[0])
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
        div_pl.save(fig_full_name[1])

        div_pl.close(True)

        return res
