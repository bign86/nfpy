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
import nfpy.IO as IO
import nfpy.Math as Math
from nfpy.Tools import (
    Constants as Cn,
    Exceptions as Ex,
    Utilities as Ut
)
import nfpy.Trading as Trd
from nfpy.Trading import (Indicators as Ind, Strategies as Str)

from .BaseReport import (BaseReport, ReportData)

# Remove a style property for Pandas version 0.x
if int(pd.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}


class ReportEquities(BaseReport):

    def __init__(self, data: ReportData, path: Optional[str] = None, **kwargs):
        super().__init__(data, path)
        self._time_spans = (
            Cn.DAYS_IN_1M, 3 * Cn.DAYS_IN_1M, 6 * Cn.DAYS_IN_1M,
            Cn.DAYS_IN_1Y, 2 * Cn.DAYS_IN_1Y, 5 * Cn.DAYS_IN_1Y
        )

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
                (asset.uid,), ('ME',), ('p_price', 'perf', 'beta')
            )
        )
        res.img_prices_long = fig_rel[0]
        res.img_performance = fig_rel[1]
        res.img_beta = fig_rel[2]

        t0 = self._cal.t0

        # Prices: full history plot
        prices = asset.prices
        v_p = prices.values
        dt_p = prices.index.values

        IO.TSPlot() \
            .lplot(0, prices, label='Price') \
            .plot() \
            .save(fig_full[0]) \
            .close(True)

        # Returns
        v_r = asset.returns.values
        bench_r = self._af.get(asset.index) \
            .returns.values

        # Last price
        last_price, idx = Math.last_valid_value(v_p, dt_p, t0.asm8)
        res.last_price = last_price
        res.last_price_date = str(dt_p[idx])[:10]

        # Performance and plot
        start = self._cal.shift(t0, -2. * Cn.DAYS_IN_1Y, 'D')
        slc = Math.search_trim_pos(
            dt_p,
            start=start.asm8,
            end=t0.asm8
        )
        perf = Math.comp_ret(v_r[slc], is_log=False)
        bench_perf = Math.comp_ret(bench_r[slc], is_log=False)

        IO.TSPlot() \
            .lplot(0, dt_p[slc], perf, color='C0', linewidth=1.5, label=asset.uid) \
            .lplot(0, dt_p[slc], bench_perf, color='C2',
                   linewidth=1.5, label='Index') \
            .plot() \
            .save(fig_full[1]) \
            .close(True)

        # Statistics table and betas
        stats = np.empty((8, len(self._time_spans)))
        betas = []

        for i, span in enumerate(self._time_spans):
            start = self._cal.shift(t0, -span, 'D')
            slc_sp = Math.search_trim_pos(
                dt_p,
                start=start.asm8,
                end=t0.asm8
            )

            stats[0, i] = float(np.nanstd(v_r[slc_sp]))
            mean_ret = Math.e_ret(v_r[slc_sp], is_log=False)
            stats[1, i] = mean_ret

            first_price = Math.next_valid_value(v_p[slc_sp])[0]
            stats[2, i] = last_price / first_price - 1.

            beta_results = Math.beta(
                dt_p[slc_sp], v_r[slc_sp], bench_r[slc_sp],
            )
            betas.append(beta_results[1:])
            stats[3:5, i] = beta_results[1:3]
            stats[5, i] = Math.correlation(
                dt_p[slc_sp], v_r[slc_sp], bench_r[slc_sp],
            )[0, 1]

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
                '\u03C3', 'mean return', 'tot. return', '\u03B2',
                'adj. \u03B2', 'correlation', 'SML ret', '\u0394 pricing'
            )
        )
        res.stats = df.style.format(
            formatter={
                '\u03C3': '{:,.1%}'.format,
                'mean return': '{:,.1%}'.format,
                'tot. return': '{:,.1%}'.format,
                '\u03B2': '{:,.2f}'.format,
                'adj. \u03B2': '{:,.2f}'.format,
                'correlation': '{:,.2f}'.format,
                'SML ret': '{:,.1%}'.format,
                '\u0394 pricing': '{:,.1%}'.format
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

        # Beta plot
        ir = bench_r[slc]
        beta = betas[3]
        xg = np.linspace(
            min(
                float(np.nanmin(ir)),
                .0
            ),
            float(np.nanmax(ir)),
            2
        )
        yg = beta[0] * xg + beta[2]

        IO.Plotter(x_zero=(.0,), y_zero=(.0,)) \
            .scatter(0, ir, v_r[slc], color='C0', linewidth=.0,
                     marker='o', alpha=.5) \
            .lplot(0, xg, yg, color='C0') \
            .plot() \
            .save(fig_full[2]) \
            .close(True)

    def _calc_trading(self, asset: TyAsset, res: Ut.AttributizedDict) -> None:
        fig_full, fig_rel = self._get_image_paths(
            (
                (asset.uid,), ('TRD',), ('p_long', 'p_short')
            )
        )
        res.prices_long, res.prices_short = fig_rel
        full_name_long, full_name_short = fig_full
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
            date_checked=today(mode='datetime') - timedelta(days=10)
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
        w_slow = self._p['alerts']['w_sr_slow']
        sr_mult = self._p['alerts']['sr_mult']

        fast_length = int(w_fast * (sr_mult + 1))
        fast_dt = dt_p[-fast_length:]
        fast_v = v_p[-fast_length:]
        strat = Str.TwoEMACross(
            fast_dt, fast_v,
            w_fast, w_slow, True
        )
        signals = strat.bulk_exec()

        ma_slow = Ind.ewma(
            v_p[-int(w_slow * (sr_mult + 1)):],
            w=w_slow
        )[-fast_length:]

        IO.TSPlot() \
            .lplot(0, fast_dt, fast_v) \
            .lplot(0, fast_dt, strat._ma_fast, color='C1', linewidth=1.5,
                   linestyle='--', label=f'MA {w_fast}') \
            .lplot(0, fast_dt, ma_slow, color='C2', linewidth=1.5,
                   linestyle='--', label=f'MA {w_slow}') \
            .plot() \
            .save(full_name_long) \
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
        #     .save(full_name_short) \
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
