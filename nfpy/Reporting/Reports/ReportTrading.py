#
# MADM Report
# Report class for the Market Asset Data Model
#

import pandas as pd

import nfpy.IO as IO
import nfpy.Models as Mod

from .BaseReport import BaseReport

# FIXME: terrible hack to be removed as soon as possible
import pandas

if int(pandas.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}
# FIXME: end of the shame


class ReportTrading(BaseReport):
    _M_OBJ = Mod.TradingModel
    _M_LABEL = 'Trading'
    _IMG_LABELS = ['p_long', 'p_short']
    INPUT_QUESTIONS = (
        ('date', 'Insert date of calculation (default None): ',
         {'idesc': 'datetime', 'optional': True}),
        ('w_ma_slow', 'Insert length of the slow MA (default 120): ',
         {'idesc': 'int', 'optional': True}),
        ('w_ma_fast', 'Insert length of the fast MA (default 21): ',
         {'idesc': 'int', 'optional': True}),
        ('sr_mult', 'Insert multiple where to apply the MA (default 5.): ',
         {'idesc': 'float', 'optional': True}),
    )

    def _init_input(self) -> dict:
        """ Prepare the input arguments for the model. """
        d = {'uid': self._uid}
        d.update(self._p)
        return d

    def _create_output(self, res):
        """ Create the final output. """
        # General variables
        fig_full_name, fig_rel_name = self._get_image_paths(res.uid)
        res.prices_long, res.prices_short = fig_rel_name
        full_name_long, full_name_short = fig_full_name

        # Moving averages plot
        start = res.ma_fast.index[0]
        p = res.prices

        div_pl = IO.TSPlot()
        div_pl.lplot(0, p.loc[start:])
        div_pl.lplot(0, res.ma_fast, color='C1', linewidth=1.5,
                     linestyle='--', label='MA {}'.format(res.w_fast))
        div_pl.lplot(0, res.ma_slow.loc[start:], color='C2', linewidth=1.5,
                     linestyle='--', label='MA {}'.format(res.w_slow))
        div_pl.plot()
        div_pl.save(full_name_long)
        div_pl.clf()

        # Alerts plot
        div_pl = res.alerts.plot()
        div_pl.plot()
        div_pl.save(full_name_short)
        div_pl.close(True)

        # Signals table
        df = res.signals
        if not df.empty:
            df.index = df.index.strftime("%Y-%m-%d")
        res.signals = df.style.format(
            formatter={
                'price': '{:,.2f}'.format,
                'return': '{:,.1%}'.format,
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

        # Alerts table
        df = pd.DataFrame(res.alerts.alerts, columns=('condition', 'price'))
        res.alerts_table = df.style.format(
            formatter={
                'price': '{:,.2f}'.format,
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

        # S/R breach table
        df_b = pd.DataFrame(res.alerts.breaches, columns=['price'])
        df_b['signal'] = ['Breach'] * len(res.alerts.breaches)
        df_t = pd.DataFrame(res.alerts.testing, columns=['price'])
        df_t['signal'] = ['Testing'] * len(res.alerts.testing)
        df = pd.concat((df_b, df_t))
        df.sort_values('price', inplace=True)
        res.breach_table = df.style.format(
            formatter={
                'price': '{:,.2f}'.format,
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

        return res
