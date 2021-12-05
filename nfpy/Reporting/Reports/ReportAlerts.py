#
# Alerts Report
# Report class for the Market Alerts
#

from collections import defaultdict
import pandas as pd
from typing import Any

import nfpy.IO as IO
import nfpy.Models as Mod
from nfpy.Tools import Utilities as Ut

from .BaseReport import BaseReport

# Remove a style property for Pandas version 0.x
if int(pd.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}


class ReportAlerts(BaseReport):
    _M_LABEL = 'Alerts'
    DEFAULT_P = {
        "baseData": {"time_spans": None},
        "alerts": {
            "w_ma_slow": 120,
            "w_ma_fast": 21,
            "w_sr_slow": 120,
            "w_sr_fast": 21,
            "sr_mult": 5.0
        }
    }

    def _init_input(self, type_: str) -> dict:
        """ Prepare and validate the the input parameters for the model. This
            includes verifying the parameters are correct for the models in the
            report. Takes the default parameters if any, applies the values from
            the database and the asset-specific overlays if any.
            The function must ensure the parameters from the database stored in
            the self._p symbol are NOT altered for later usage by making copies
            if required.
        """
        return self._p

    def _calculate(self) -> Any:
        """ Calculate the required models.
            MUST ensure that the model parameters passed in <args> are not
            modified so that the database parameters in self._p are not
            changed from one asset to the next.
        """
        outputs = defaultdict(dict)
        for uid in self.uids:
            print(f'  > {uid}')
            try:
                asset = self._af.get(uid)
                type_ = asset.type
                params = self._init_input(type_)
                if type_ == 'Currency':
                    res1 = self._calc_generic(uid, params)
                    fields = ('uid', 'description', 'price_country', 'base_country',
                              'price_ccy', 'base_ccy')
                    res1.info = {k: getattr(asset, k) for k in fields}
                    res2 = self._calc_trading(uid, params)
                    outputs[type_][uid] = (res1, res2)
                elif type_ == 'Equity':
                    res1 = self._calc_equity(uid, params)
                    fields = ('uid', 'description', 'ticker', 'isin', 'country',
                              'currency', 'company', 'index')
                    res1.info = {k: getattr(asset, k) for k in fields}
                    res2 = self._calc_trading(uid, params)
                    outputs[type_][uid] = (res1, res2)
                else:
                    raise RuntimeError(f'Asset type {type_} not supported by this model')
            except (RuntimeError, KeyError, ValueError) as ex:
                Ut.print_exc(ex)

        return outputs

    def _calc_generic(self, uid: str, p: {}) -> Any:
        mod = Mod.MarketAssetsDataBaseModel(uid, **p['baseData'])
        return self._render_out_generic(mod.result(**p['baseData']))

    def _render_out_generic(self, res: Any) -> Any:
        labels = ((res.uid,), ('MA',), ('p_price',))
        fig_full, fig_rel = self._get_image_paths(labels)
        res.img_prices = fig_rel[0]

        # Full history plot
        IO.TSPlot() \
            .lplot(0, res.prices, label='Price') \
            .plot() \
            .save(fig_full[0]) \
            .close(True) \
            # pl.close(True)

        # Render dataframes
        df = res.stats.T
        res.stats = df.style.format(
            formatter={
                'volatility': '{:,.1%}'.format,
                'mean return': '{:,.1%}'.format,
                'tot. return': '{:,.1%}'.format,
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

        return res

    def _calc_equity(self, uid: str, p: {}) -> Any:
        mod = Mod.MarketEquityDataModel(uid, **p['baseData'])
        return self._render_out_equity(mod.result(**p['baseData']))

    def _render_out_equity(self, res: Any) -> Any:
        labels = ((res.uid,), ('ME',), ('p_price', 'perf', 'beta'))
        fig_full, fig_rel = self._get_image_paths(labels)

        # Relative path in results object
        res.img_prices_long = fig_rel[0]
        res.img_performance = fig_rel[1]
        res.img_beta = fig_rel[2]

        # Full history plot
        IO.TSPlot() \
            .lplot(0, res.prices, label='Price') \
            .plot() \
            .save(fig_full[0]) \
            .close(True)
        # pl.clf()

        # Render dataframes
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

    def _calc_bond(self, uid: str, p: {}) -> Any:
        mod = Mod.MarketBondDataModel(uid, **p['baseData'])
        return self._render_out_bond(mod.result(**p['baseData']))

    def _render_out_bond(self, res: Any) -> Any:
        labels = ((res.uid,), ('ME',), ('p_price', 'price_ytm'))
        fig_full, fig_rel = self._get_image_paths(labels)

        # Relative path in results object
        res.prices_long, res.prices_ytm = fig_rel

        # Full history plot
        IO.TSPlot() \
            .lplot(0, res.prices, label='Price') \
            .lplot(0, res.yields, color='C2', label='Yield', secondary_y=True) \
            .plot() \
            .save(fig_full[0]) \
            .close(True)
        # pl.clf()

        # YTM plot
        data = res.yields_array
        bars = res.ytm_bars

        IO.TSPlot(
            xl=('Price',), yl=('YTM',),
            y_zero=(res.yields_array[1, 3],),
            x_zero=(res.yields_array[0, 3],)
        ) \
            .lplot(0, data[0, :], data[1, :], marker='', linestyle='-',
                   label=r'$YTM(P_0, t_0)$') \
            .line(0, 'xh', bars[1, 0], linestyle='--', linewidth='.8',
                  color="C1", label=r'$YTM(P_0\pm\delta^{1M}, t_0)$') \
            .line(0, 'xh', bars[1, 1], linestyle='--', linewidth='.8',
                  color="C1") \
            .line(0, 'xh', bars[1, 2], linestyle='--', linewidth='.8',
                  color="C2", label=r'$YTM(P_0\pm\delta^{6M}, t_0)$') \
            .line(0, 'xh', bars[1, 3], linestyle='--', linewidth='.8',
                  color="C2") \
            .plot() \
            .save(fig_full[1]) \
            .close(True)
        # pl.clf()

        # Render dataframes
        df = res.stats.T
        res.stats = df.style.format(
            formatter={
                'volatility': '{:,.1%}'.format,
                'mean return': '{:,.1%}'.format,
                'tot. return': '{:,.1%}'.format,
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

        df = res.fair_values
        df.index = df.index.map(lambda x: '{:,.2%}'.format(x))
        res.fair_values = df.style.format("{:,.2f}".format) \
            .format(formatter={'%diff': '{:,.1%}'.format}) \
            .set_table_attributes('class="dataframe"') \
            .render()

        return res

    def _calc_trading(self, uid: str, p: {}) -> Any:
        mod = Mod.TradingModel(uid, **p['alerts'])
        return self._render_out_trd(mod.result(**p['alerts']))

    def _render_out_trd(self, res: Any) -> Any:
        labels = ((res.uid,), ('TRD',), ('p_long', 'p_short'))
        fig_full, fig_rel = self._get_image_paths(labels)
        res.prices_long, res.prices_short = fig_rel
        full_name_long, full_name_short = fig_full

        # Moving averages plot
        start = res.ma_fast.index[0]
        p = res.prices

        IO.TSPlot() \
            .lplot(0, p.loc[start:]) \
            .lplot(0, res.ma_fast, color='C1', linewidth=1.5,
                   linestyle='--', label=f'MA {res.w_fast}') \
            .lplot(0, res.ma_slow.loc[start:], color='C2', linewidth=1.5,
                   linestyle='--', label=f'MA {res.w_slow}') \
            .plot() \
            .save(full_name_long) \
            .clf()

        # Breaches plot
        # res.breaches.plot() \
        #     .plot() \
        #     .save(full_name_short) \
        #     .clf()
        #     .close(True) \

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
        df = pd.DataFrame(res.alerts, columns=('condition', 'price'))
        res.alerts_table = df.style.format(
            formatter={
                'price': '{:,.2f}'.format,
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

        # S/R breach table
        # df_b = pd.DataFrame(res.breaches.breaches, columns=['price'])
        # df_b['signal'] = ['Breach'] * len(res.breaches.breaches)
        # df_t = pd.DataFrame(res.breaches.testing, columns=['price'])
        # df_t['signal'] = ['Testing'] * len(res.breaches.testing)
        # df = pd.concat((df_b, df_t), ignore_index=True)
        # df.sort_values('price', inplace=True)
        # res.breach_table = df.style.format(
        #     formatter={
        #         'price': '{:,.2f}'.format,
        #     },
        #     **PD_STYLE_PROP) \
        #     .set_table_attributes('class="dataframe"') \
        #     .render()

        return res
