#
# Report Market Short
# Report class for the short report on market data
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
from nfpy.Trading import (Indicators as Ind)

from .BaseReport import (BaseReport, ReportData)

# Remove a style property for Pandas version 0.x
if int(pd.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}


class ReportMarketShort(BaseReport):
    DEFAULT_P = {
        'years_price_hist': 2.,
        'w_alerts_days': 14,
        'ma': {
            'w_ma_fast': 20,
            'w_ma_slow': 120,
            'w_plot': 250
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
                (asset.uid,), ('ME',), ('p_price',)
            )
        )
        res.img_prices_long = fig_rel[0]

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
        stats = np.empty((5, len(self._span_slc)))
        betas = []
        ann_vola = np.sqrt(250)
        for i, slc_sp in enumerate(self._span_slc):
            stats[0, i] = float(np.nanstd(v_r[slc_sp])) * ann_vola

            first_price = Math.next_valid_value(v_p[slc_sp])[0]
            stats[1, i] = last_price / first_price - 1.

            beta_results = Math.beta(
                dt_p[slc_sp], v_r[slc_sp], bench_r[slc_sp],
            )
            betas.append(beta_results[1:])
            stats[2:4, i] = beta_results[1:3]
            stats[4, i] = Math.correlation(
                dt_p[slc_sp], v_r[slc_sp], bench_r[slc_sp],
            )[0, 1]

        # Render dataframes
        df = pd.DataFrame(
            stats.T,
            index=self._time_spans,
            columns=(
                '\u03C3 (Y)', 'return', '\u03B2', 'adj. \u03B2', '\u03C1'
            )
        )
        res.stats = df.style.format(
            formatter={
                '\u03C3 (Y)': '{:,.1%}'.format,
                'return': '{:,.1%}'.format,
                '\u03B2': '{:,.2f}'.format,
                'adj. \u03B2': '{:,.2f}'.format,
                '\u03C1': '{:,.2f}'.format,
                'SML ret': '{:,.1%}'.format,
                '\u0394 pricing': '{:,.1%}'.format
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

    def _calc_trading(self, asset: TyAsset, res: Ut.AttributizedDict) -> None:
        fig_full, fig_rel = self._get_image_paths(
            (
                (asset.uid,), ('TRD',), ('ma_plot',)
            )
        )
        res.img_ma_plot = fig_rel[0]

        prices = asset.prices
        v_p = prices.values
        dt_p = prices.index.values

        # Manual alerts
        ae = Trd.AlertsEngine()
        _ = ae.trigger([asset.uid])
        ae.update_db()

        dt_today = today(mode='datetime')
        check_start = dt_today - timedelta(days=self._p['w_alerts_days'])
        alerts = ae.fetch(
            [asset.uid],
            triggered=None,
            date_checked=check_start
        )
        alerts.sort(key=lambda x: x.value)

        alerts_data = []
        for a in alerts:
            is_today = 'NEW' if a.date_triggered == dt_today else ''
            dt_trigger = a.date_triggered.strftime('%Y-%m-%d') \
                if a.date_triggered else ''
            alerts_data.append((a.cond, a.value, is_today, dt_trigger))

        if len(alerts_data) > 0:
            df = pd.DataFrame(
                alerts_data,
                columns=('condition', 'price', 'new', 'date trigger')
            )
            res.alerts_table = df.style.format(
                formatter={
                    'price': '{:,.2f}'.format,
                },
                **PD_STYLE_PROP) \
                .set_table_attributes('class="dataframe"') \
                .render()
        else:
            res.alerts_table = f'No manual alerts'

        # Strategy and moving averages
        w_fast = self._p['ma']['w_ma_fast']
        w_slow = self._p['ma']['w_ma_slow']
        w_check = self._p['ma']['w_plot']

        total_length = min(w_slow + w_check, v_p.shape[0])
        shortened_v = v_p[-total_length:]
        shortened_dt = dt_p[-total_length:]
        ma_fast = Ind.ewma(shortened_v, w_fast)
        ma_slow = Ind.ewma(shortened_v, w_slow)

        pl = IO.TSPlot() \
            .lplot(0, shortened_dt[w_slow:], shortened_v[w_slow:]) \
            .lplot(0, shortened_dt[w_slow:], ma_fast[w_slow:], color='C1',
                   linewidth=1.5, linestyle='--', label=f'MA {w_fast}') \
            .lplot(0, shortened_dt[w_slow:], ma_slow[w_slow:], color='C2',
                   linewidth=1.5, linestyle='--', label=f'MA {w_slow}')

        for a in alerts:
            color = 'C4' if a.date_triggered is None else 'C3'
            pl.line(0, 'xh', a.value, color=color, linestyle='--', linewidth=1)

        pl.plot() \
            .save(fig_full[0]) \
            .clf()
