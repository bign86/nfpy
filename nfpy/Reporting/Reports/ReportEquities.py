#
# Report Equities
# Report class for the Equities Data
#

from collections import defaultdict
from datetime import timedelta
import numpy as np
import pandas as pd
from typing import (Any, Optional)

from nfpy.Assets import TyAsset
from nfpy.Calendar import today
from nfpy.Financial import DividendFactory
import nfpy.IO as IO
import nfpy.Math as Math
from nfpy.Tools import (
    Constants as Cn,
    Exceptions as Ex,
    Utilities as Ut
)
import nfpy.Trading as Trd
from nfpy.Trading import (Strategies as Str)

from .BaseReport import (BaseReport, ReportData)

# Remove a style property for Pandas version 0.x
if int(pd.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}


class ReportEquities(BaseReport):
    DEFAULT_P = {
        'years_price_hist': 2.,
        'beta_years_span': 3.,
        'w_alerts_days': 14,
        'alerts': {
            'w_ma_fast': 20,
            'w_ma_slow': 120,
            'w_check': 250
        }
    }

    def __init__(self, data: ReportData, path: Optional[str] = None, **kwargs):
        super().__init__(data, path)
        self._time_spans = (
            Cn.DAYS_IN_1M, 3 * Cn.DAYS_IN_1M, 6 * Cn.DAYS_IN_1M,
            Cn.DAYS_IN_1Y, 2 * Cn.DAYS_IN_1Y, 5 * Cn.DAYS_IN_1Y
        )
        self._hist_slc = None
        self._span_slc = None

    def _init_input(self, type_: Optional[str] = None) -> None:
        """ Prepare and validate the the input parameters for the model. This
            includes verifying the parameters are correct for the models in the
            report. Takes the default parameters if any, applies the values from
            the database and the asset-specific overlays if any.
            The function must ensure the parameters from the database stored in
            the self._p symbol are NOT altered for later usage by making copies
            if required.
        """
        pass

    def _one_off_calculations(self) -> None:
        """ Perform all non-uid dependent calculations for efficiency. """
        # Calculate price history length and save the slice object for later use
        t0 = self._cal.t0
        hist_y = -self._p['years_price_hist'] * Cn.DAYS_IN_1Y
        start = self._cal.shift(t0, hist_y, 'D')
        self._hist_slc = Math.search_trim_pos(
            self._cal.calendar.values,
            start=start.asm8,
            end=t0.asm8
        )

        # Calculate time span length and save the list of slices
        self._span_slc = []
        for i, span in enumerate(self._time_spans):
            start = self._cal.shift(t0, -span, 'D')
            slc_sp = Math.search_trim_pos(
                self._cal.calendar.values,
                start=start.asm8,
                end=t0.asm8
            )
            self._span_slc.append(slc_sp)

    def _calculate(self) -> Any:
        """ Calculate the required models.
            MUST ensure that the model parameters passed in <args> are not
            modified so that the database parameters in self._p are not
            changed from one asset to the next.
        """
        outputs = defaultdict(dict)
        self._one_off_calculations()
        for uid in self.uids:
            print(f'  > {uid}')
            try:
                asset = self._af.get(uid)
                if asset.type != 'Equity':
                    msg = f'{uid} is not an equity'
                    raise Ex.AssetTypeError(msg)

                res = Ut.AttributizedDict()
                self._calc_equity(asset, res)
                self._calc_trading(asset, res)
                outputs[asset.ticker] = res

            except (RuntimeError, Ex.AssetTypeError) as ex:
                Ut.print_exc(ex)

        return outputs

    def _calc_equity(self, asset: TyAsset, res: Ut.AttributizedDict) -> None:
        # General infos
        res.info = {
            k: getattr(asset, k)
            for k in ('uid', 'description', 'ticker', 'isin', 'country',
                      'currency', 'company', 'index')
        }

        # Relative path in results object
        fig_full, fig_rel = self._get_image_paths(
            (
                (asset.uid,), ('ME',), ('p_price', 'beta')
            )
        )
        res.img_prices_long = fig_rel[0]
        res.img_beta = fig_rel[1]

        t0 = self._cal.t0

        # Prices: full history plot
        prices = asset.prices
        v_p = prices.values
        dt_p = prices.index.values

        # Returns
        v_r = asset.returns.values
        bench_r = self._af.get(asset.index) \
            .returns.values

        # Last price
        last_price, idx = Math.last_valid_value(v_p, dt_p, t0.asm8)
        res.last_price = last_price
        res.last_price_date = str(dt_p[idx])[:10]

        # Dividends
        df = DividendFactory(asset)
        res.ttm_div = df.ttm_div()
        res.ttm_yield = df.ttm_yield() * 100.

        # Performance and plot
        # Adjust the slice to account for the fact that the history of the
        # equity may be shorter than the full history span. In such case the
        # oldest equity value would not be applied at the right time on the
        # index. Here we are ensuring a shorter history of the index as well.
        # Is NOT considered the case the index may be shorter than the equity.
        slc = slice(
            Math.next_valid_index(v_p, self._hist_slc.start),
            self._hist_slc.stop
        )
        bench_perf = Math.comp_ret(bench_r[slc], is_log=False) \
                     * Math.next_valid_value(v_p[slc])[0]

        IO.TSPlot() \
            .lplot(0, dt_p[slc], v_p[slc], label=asset.ticker) \
            .lplot(0, dt_p[slc], bench_perf, color='C2',
                   linewidth=1.5, label=asset.index) \
            .plot() \
            .save(fig_full[0]) \
            .close(True)

        # Statistics table and betas
        stats = np.empty((8, len(self._span_slc)))
        betas = []

        for i, slc_sp in enumerate(self._span_slc):
            first_price = Math.next_valid_value(v_p[slc_sp])[0]
            tot_ret = last_price / first_price - 1.

            stats[0, i] = float(np.nanstd(v_r[slc_sp]))
            stats[1, i] = Math.compound(
                tot_ret,
                Cn.BDAYS_IN_1Y / self._time_spans[i]
            )
            stats[2, i] = tot_ret

            beta_results = Math.beta(
                dt_p[slc_sp], v_r[slc_sp], bench_r[slc_sp],
            )
            betas.append(beta_results[1:])
            stats[3:5, i] = beta_results[1:3]
            stats[5, i] = Math.correlation(
                dt_p[slc_sp], v_r[slc_sp], bench_r[slc_sp],
            )[0, 1]

            mean_ret = Math.e_ret(v_r[slc_sp], is_log=False)
            mean_index_ret = Math.e_ret(bench_r[slc_sp], is_log=False)
            rt, delta = Math.sml(
                mean_ret,
                beta_results[1],
                .0,
                mean_index_ret
            )
            stats[6, i] = rt
            stats[7, i] = delta

        # Render dataframes
        df = pd.DataFrame(
            stats.T,
            index=self._time_spans,
            columns=(
                '\u03C3', 'yearly return', 'tot. return', '\u03B2',
                'adj. \u03B2', '\u03C1', 'SML ret', '\u0394 pricing'
            )
        )
        res.stats = df.style.format(
            formatter={
                '\u03C3': '{:,.1%}'.format,
                'yearly return': '{:,.1%}'.format,
                'tot. return': '{:,.1%}'.format,
                '\u03B2': '{:,.2f}'.format,
                'adj. \u03B2': '{:,.2f}'.format,
                '\u03C1': '{:,.2f}'.format,
                'SML ret': '{:,.1%}'.format,
                '\u0394 pricing': '{:,.1%}'.format
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

        # Beta plot
        hist_y = -self._p['beta_years_span'] * Cn.DAYS_IN_1Y
        start = self._cal.shift(t0, hist_y, 'D')
        slc = Math.search_trim_pos(
            dt_p,
            start=start.asm8,
            end=t0.asm8
        )
        ir = bench_r[slc]
        beta = betas[3]
        xg = np.linspace(
            min(float(np.nanmin(ir)), .0),
            float(np.nanmax(ir)),
            2
        )
        yg = beta[0] * xg + beta[2]

        IO.Plotter(x_zero=(.0,), y_zero=(.0,)) \
            .scatter(0, ir, v_r[slc], color='C0', linewidth=.0,
                     marker='o', alpha=.5) \
            .lplot(0, xg, yg, color='C0') \
            .plot() \
            .save(fig_full[1]) \
            .close(True)

    def _calc_trading(self, asset: TyAsset, res: Ut.AttributizedDict) -> None:
        fig_full, fig_rel = self._get_image_paths(
            (
                (asset.uid,), ('TRD',), ('ma_plot',)
            )
        )
        res.img_ma_plot = fig_rel[0]
        t0 = self._cal.t0

        prices = asset.prices
        v_p = prices.values
        dt_p = prices.index.values

        # Manual alerts
        ae = Trd.AlertsEngine()
        alerts = ae.trigger(
            [asset.uid],
            # TODO: this should be run with the number of days since the last
            #       execution. IO a date on the DB?
            date_checked=today(mode='datetime')
                         - timedelta(days=self._p['w_alerts_days'])
        )
        ae.update_db()

        df = pd.DataFrame(alerts, columns=('condition', 'price'))
        res.alerts_table = df.style.format(
            formatter={
                'price': '{:,.2f}'.format,
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

        # Strategy and moving averages
        w_fast = self._p['alerts']['w_ma_fast']
        w_slow = self._p['alerts']['w_ma_slow']
        w_check = self._p['alerts']['w_check']

        total_length = min(w_slow + w_check, dt_p.shape[0])
        fast_dt = dt_p[-total_length:]
        fast_v = v_p[-total_length:]
        strat = Str.TwoEMACross(
            fast_dt, fast_v,
            w_fast, w_slow, True
        )
        signals = strat.bulk_exec()

        IO.TSPlot() \
            .lplot(0, fast_dt[w_slow:], fast_v[w_slow:]) \
            .lplot(0, fast_dt[w_slow:], strat._ma_fast[w_slow:], color='C1',
                   linewidth=1.5, linestyle='--', label=f'MA {w_fast}') \
            .lplot(0, fast_dt[w_slow:], strat._ma_slow[w_slow:], color='C2',
                   linewidth=1.5, linestyle='--', label=f'MA {w_slow}') \
            .plot() \
            .save(fig_full[0]) \
            .clf()

        # Signals table
        if len(signals.signals) > 0:
            sig_price = fast_v[signals.indices]
            trade_ret = np.empty(sig_price.shape)
            trade_ret[:-1] = sig_price[1:] / sig_price[:-1] - 1.
            trade_ret[-1] = res.last_price / sig_price[-1] - 1.

            df = pd.DataFrame(
                index=signals.dates,
                columns=['signal', 'price', 'return', '\u0394 days']
            )
            df['signal'] = signals.signals
            df['price'] = sig_price
            df['return'] = trade_ret
            df['\u0394 days'] = (t0 - df.index).days
            df.replace(
                to_replace={
                    'signal': {1: 'buy', -1: 'sell'}
                },
                inplace=True
            )
            df.index = df.index.strftime("%Y-%m-%d")

        else:
            df = pd.DataFrame(columns=['signal', 'price', 'return', '\u0394 days'])

        res.signals = df.style.format(
            formatter={
                'price': '{:,.2f}'.format,
                'return': '{:,.1%}'.format,
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

        # Support / Resistances
        # be = Trd.BreachesEngine(self._w_sr_slow, self._w_sr_fast, 10)
        # self._res_update(
        #     breaches=be.raise_breaches(self._uid)
        # )
        #
        # res.breaches.plot() \
        #     .plot() \
        #     .save(fig_full[1]) \
        #     .close(True) \
        #     pl.clf()
        #
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
