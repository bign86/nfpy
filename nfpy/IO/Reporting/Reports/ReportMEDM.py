#
# MEDM Report
# Report class for the Market Equity Data Model
#

import numpy as np

from nfpy.Calendar import get_calendar_glob
import nfpy.Financial.Models as Mod
import nfpy.IO as IO
from nfpy.Tools import (Constants as Cn)

from .ReportMADM import ReportMADM

# FIXME: terrible hack to be removed as soon as possible
import pandas

if int(pandas.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}


# FIXME: end of the shame


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
        div_pl = IO.TSPlot()
        div_pl.lplot(0, res.prices)
        div_pl.plot()
        div_pl.save(fig_full_name[0])
        div_pl.close(True)

        # Performance plot
        div_pl = IO.TSPlot()
        div_pl.lplot(0, res.perf, color='C0', linewidth=1.5, label=res.uid)
        div_pl.lplot(0, res.perf_idx, color='C2', linewidth=1.5, label='Index')
        div_pl.plot()
        div_pl.save(fig_full_name[1])
        div_pl.close(True)

        # Beta plot
        start = cal.shift(res.date, -Cn.DAYS_IN_1Y, 'D')
        r = res.returns.loc[start:]
        ir = res.index_returns.loc[start:]
        beta = res.beta_params
        xg = np.linspace(min(float(np.nanmin(ir.values)), .0),
                         float(np.nanmax(ir.values)), 2)
        yg = beta[0] * xg + beta[2]

        div_pl = IO.Plotter(x_zero=(.0,), y_zero=(.0,), xlim=((-.15, .15),),
                            ylim=((-.15, .15),))
        div_pl.scatter(0, ir.values, r.values, color='C0', linewidth=.0,
                       marker='o', alpha=.5)
        div_pl.lplot(0, xg, yg, color='C0')
        div_pl.plot()
        div_pl.save(fig_full_name[2])
        div_pl.close(True)

        df = res.stats.T
        res.stats = df.style.format(
            formatter={
                'volatility': '{:,.1%}'.format,
                'mean return': '{:,.1%}'.format,
                'tot. return': '{:,.1%}'.format,
                'beta': '{:,.2f}'.format,
                'adj. beta': '{:,.2f}'.format,
                'correlation': '{:,.2f}'.format,
                'SML ret': '{:,.1%}'.format,
                'delta pricing': '{:,.1%}'.format
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

        return res
