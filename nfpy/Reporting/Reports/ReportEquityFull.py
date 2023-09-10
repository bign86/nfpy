#
# Report Market Short
# Report class for the short report on market data
#

from collections import defaultdict
import cutils
from datetime import timedelta
import numpy as np
import pandas as pd
from typing import (Any, Optional)

from nfpy.Assets import TyAsset
from nfpy.Calendar import today
from nfpy.Financial import DividendFactory
from nfpy.Financial.EquityValuation import (DCF, DDM)
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


class ReportEquityFull(BaseReport):
    DEFAULT_P = {
        'history': 5,
        'w_alerts_days': 14,
        'DCF': {
            'past_horizon': 8,
            'future_proj': 5,
            'perpetual_rate': .0,
        },
        'DDM': {
            'ke': None,
            'history': 5,
            'premium': 0.02,
            'stage1': (5, None, True),
            'stage2': None,
            'gwt_mode': ['historical', 'ROE', 'booth'],
        },
        'ewma': {
            'w_ma_fast': 20,
            'w_ma_slow': 120,
            'w_plot': 250
        },
        'sr': {
            'w_sr': [120, 20],
            'w_check': 10,
            'tolerance': 1.5,
            'w_multi': 2.,
        },
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
        """ Prepare and validate the input parameters for the model. This
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
        hist_y = -self._p['history'] * Cn.DAYS_IN_1Y
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
        try:
            asset = self._af.get(self.uids[0])
            if asset.type == 'Company':
                asset = self._af.get(asset.equity)
            else:
                msg = f'{self.uids[0]} is not an equity or a company'
                raise Ex.AssetTypeError(msg)

            res = Ut.AttributizedDict()
            self._calc_equity(asset, res)
            self._calc_ddm(asset, res)
            self._calc_trading(asset, res)
            outputs[asset.ticker] = res

        except (RuntimeError, Ex.AssetTypeError) as ex:
            Ut.print_exc(ex)

        return outputs

    def _calc_dcf(self, asset: TyAsset, res: Ut.AttributizedDict) -> None:
        # Discounted Cash Flow calculation
        try:
            p = self._p.get('DCF', {})
            dcf_res = DCF(asset.uid, **p) \
                .result(**p)
        except Exception as ex:
            res.has_dcf = False
            Ut.print_exc(ex)
        else:
            res.has_dcf = True
            res.dcf_ret = (dcf_res.fair_value / res.last_price - 1.) * 100.
            res.dcf_fair_value = dcf_res.fair_value
            res.dcf_wacc = dcf_res.wacc
            res.dcf_coe = dcf_res.cost_of_equity
            res.dcf_cod = dcf_res.cost_of_debt
            res.dcf_history = dcf_res.history
            res.dcf_project = dcf_res.projection

            df = dcf_res.df
            df.index = df.index.strftime("%Y-%m-%d")
            res.df = df.T.to_html(
                index=True,
                na_rep='-',
                float_format='{:,.2f}'.format,
                border=None,
            )

    def _calc_ddm(self, asset: TyAsset, res: Ut.AttributizedDict) -> None:
        # Dividends Discount Model Calculation
        try:
            p = self._p.get('DDM', {})
            ddm_res = DDM(asset.uid, **p).result(**p)
        except Ex.MissingData as ex:
            res.has_ddm = False
            Ut.print_exc(ex)
        else:
            res.has_ddm = True
            res.ddm_im_ke = ddm_res.implied_ke * 100.
            res.ddm_im_lt_prm = ddm_res.implied_lt_premium * 100.
            res.ddm_im_st_prm = ddm_res.implied_st_premium * 100.

            res.ddm_ke = ddm_res.ke * 100.
            res.ddm_premium = ddm_res.premium * 100.
            res.ddm_lt_g = ddm_res.lt_growth * 100.

            res.ddm_res_no_gwt = ddm_res.no_growth

            labels = ((ddm_res.uid,), ('DDM',), ('div', 'rates'))
            fig_full, fig_rel = self._get_image_paths(labels)
            res.div_fig = fig_rel[0]
            res.div_rates_fig = fig_rel[1]

            # Save out dividend figure
            pl_d = IO.TSPlot(yl=('Dividend',)) \
                .lplot(0, ddm_res.div_ts, marker='o', label='Historical', color='dimgrey')

            if ddm_res.stages > 0:
                pl_d.lplot(
                    0, ddm_res.dates, ddm_res.no_growth['cf'][1, :],
                    marker='o', label='No growth', color='C0'
                )

                pl_r = IO.TSPlot(yl=('Dividend growth',)) \
                    .line(0, 'xh', res.ddm_lt_g, label='Long-Term growth rate',
                          linestyle='--', color='dimgrey')
                # .lplot(0, ddm_res.macro_growth, label='Macro growth') \

                if hasattr(ddm_res, 'manual_growth'):
                    res.ddm_res_manual = ddm_res.manual_growth
                    pl_d.lplot(
                        0, ddm_res.dates, ddm_res.manual_growth['cf'][1, :],
                        label='Manual growth', color='C1'
                    )
                    pl_r.lplot(
                        0, ddm_res.dates, ddm_res.manual_growth['rates'] * 100.,
                        label='Manual rates', color='C1'
                    )

                if hasattr(ddm_res, 'historical_growth'):
                    res.ddm_res_hist = ddm_res.historical_growth
                    pl_d.lplot(
                        0, ddm_res.dates, ddm_res.historical_growth['cf'][1, :],
                        label='Hist growth', color='C2'
                    )
                    pl_r.lplot(
                        0, ddm_res.dates, ddm_res.historical_growth['rates'] * 100.,
                        label='Hist rates', color='C2'
                    )

                if hasattr(ddm_res, 'ROE_growth'):
                    res.ddm_res_roe = ddm_res.ROE_growth
                    pl_d.lplot(
                        0, ddm_res.dates, ddm_res.ROE_growth['cf'][1, :],
                        label='ROE growth', color='C3'
                    )
                    pl_r.lplot(
                        0, ddm_res.dates, ddm_res.ROE_growth['rates'] * 100.,
                        label='ROE rates', color='C3'
                    )

                if hasattr(ddm_res, 'booth_growth'):
                    res.ddm_res_booth = ddm_res.booth_growth
                    pl_d.lplot(
                        0, ddm_res.dates, ddm_res.booth_growth['cf'][1, :],
                        label='Booth growth', color='C4'
                    )
                    pl_r.lplot(
                        0, ddm_res.dates, ddm_res.booth_growth['rates'] * 100.,
                        label='Booth rates', color='C4'
                    )

                # Save out dividend growth figure
                pl_r.plot() \
                    .save(fig_full[1]) \
                    .close(True)

            pl_d.plot() \
                .save(fig_full[0]) \
                .close(True)

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

        # Last price
        last_price, idx = Math.last_valid_value(v_p, dt_p, t0.asm8)
        res.last_price = last_price
        res.last_price_date = str(dt_p[idx])[:10]

        # Dividends
        df = DividendFactory(asset)
        res.freq_div = df.frequency
        _, yrl_div = df.annual_dividends
        _, yrl_yield = df.annual_yields()
        if len(yrl_yield) > 0:
            res.ytd_yrl_div = yrl_div[-1]
            res.ytd_yrl_yield = yrl_yield[-1] * 100.
        else:
            res.ytd_yrl_div = 0.
            res.ytd_yrl_yield = 0.
        if len(yrl_yield) > 1:
            res.last_yrl_div = yrl_div[-2]
            res.last_yrl_yield = yrl_yield[-2] * 100.
        else:
            res.last_yrl_div = 0.
            res.last_yrl_yield = 0.

        # Performance and plot
        # Adjust the slice to account for the fact that the history of the
        # equity may be shorter than the full history span. In such case the
        # oldest equity value would not be applied at the right time on the
        # index. Here we are ensuring a shorter history of the index as well.
        # Is NOT considered the case the index may be shorter than the equity.
        slc = slice(
            cutils.next_valid_index(v_p, self._hist_slc.start),
            self._hist_slc.stop
        )

        pl = IO.TSPlot(figsize=(10, 4)) \
            .lplot(0, dt_p[slc], v_p[slc], label=asset.ticker)

        bench_uid = asset.index
        if bench_uid is not None:
            bench_r = self._af.get(bench_uid).returns.values
            bench_perf = Math.comp_ret(bench_r[slc], is_log=False) \
                         * Math.next_valid_value(v_p[slc])[0]

            pl.lplot(0, dt_p[slc], bench_perf, color='C2',
                     linewidth=1.5, label=bench_uid)

        pl.plot() \
            .save(fig_full[0]) \
            .close(True)

        # Statistics table and betas
        stats = np.empty((5, len(self._span_slc)))
        betas = []
        ann_vola = np.sqrt(Cn.BDAYS_IN_1Y)
        for i, slc_sp in enumerate(self._span_slc):
            stats[0, i] = float(np.nanstd(v_r[slc_sp])) * ann_vola

            first_price = Math.next_valid_value(v_p[slc_sp])[0]
            stats[1, i] = last_price / first_price - 1.

            if bench_uid is not None:
                beta_results = Math.beta(
                    dt_p[slc_sp], v_r[slc_sp], bench_r[slc_sp],
                )
                betas.append(beta_results[1:])
                stats[2:4, i] = beta_results[1:3]
                stats[4, i] = Math.correlation(
                    dt_p[slc_sp], v_r[slc_sp], bench_r[slc_sp],
                )[0, 1]
            else:
                betas.append(np.nan)
                stats[2:5, i] = [np.nan, np.nan, np.nan]

        # Render dataframes
        df = pd.DataFrame(
            stats.T,
            index=self._time_spans,
            columns=[
                '\u03C3 (Y)', 'return', '\u03B2', 'adj. \u03B2', '\u03C1'
            ]
        )
        res.stats = df.to_html(
            index=True,
            na_rep='-',
            border=None,
            formatters={
                '\u03C3 (Y)': '{:,.1%}'.format,
                'return': '{:,.1%}'.format,
                '\u03B2': '{:,.2f}'.format,
                'adj. \u03B2': '{:,.2f}'.format,
                '\u03C1': '{:,.2f}'.format,
                'SML ret': '{:,.1%}'.format,
                '\u0394 pricing': '{:,.1%}'.format
            },
        )

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
        last_price, _ = Math.last_valid_value(v_p, dt_p, self._cal.t0.asm8)

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

        # Create a common list of alerts
        alerts_data = []
        for a in alerts:
            if a.date_triggered is not None:
                is_today = 'NEW' if a.date_triggered == dt_today else ''
                dt_trigger = a.date_triggered.strftime('%Y-%m-%d')
                status = 'breach'
            else:
                is_today = ''
                dt_trigger = ''
                status = ''
            alerts_data.append((a.cond, status, a.value, is_today, dt_trigger))

        # # S/R lines alerts & add to the common list
        # w_sr = self._p['sr']['w_sr']
        # sr_check = self._p['sr']['w_check']
        # sr_tol = self._p['sr']['tolerance']
        # sr_multi = self._p['sr']['w_multi']

        # smooth_w = int(round(max(w_sr) * sr_multi))
        # sr_checker = Trd.SRBreach(
        #     v_p[-smooth_w:],
        #     sr_check, sr_tol, 'smooth', w_sr
        # )
        # for b in sr_checker.get():
        #     alerts_data.append((b[0], b[2], b[1], '', ''))

        # Strategy and moving averages
        w_fast = self._p['ewma']['w_ma_fast']
        w_slow = self._p['ewma']['w_ma_slow']
        w_check = self._p['ewma']['w_plot']

        total_length = min(w_slow + w_check, v_p.shape[0])
        shortened_v = cutils.ffill(v_p[-total_length:].copy())
        shortened_dt = dt_p[-total_length:]
        ema_f = Ind.Ewma(shortened_v, True, w_fast)
        ema_s = Ind.Ewma(shortened_v, True, w_slow)
        ema_f.start(w_slow)
        ema_s.start(w_slow)
        ma_fast = ema_f.get_indicator()['ewma']
        ma_slow = ema_s.get_indicator()['ewma']

        # Pivots
        # The pivots are calculated on the same length of series of the MAs
        #
        # if self._p['pivots']['type'] == 'volatility':
        #     ret = asset.returns.values[w_slow:]
        #     threshold = np.std(ret) * self._p['pivots']['threshold']
        # else:  # 'return'
        #     threshold = self._p['pivots']['threshold']
        # pivot_dt, pivot_p = Trd.get_pivot(
        #     valid_dt, valid_p,
        #     threshold
        # )

        # Absolute max and min
        valid_dt = shortened_dt[w_slow:]
        valid_p = shortened_v[w_slow:]
        ath_idx = np.argmax(valid_p)
        atl_idx = np.argmin(valid_p)
        ath_ret = valid_p[ath_idx] / last_price - 1.
        atl_ret = valid_p[atl_idx] / last_price - 1.

        # Create plot with alerts and S/Rs
        pl = IO.TSPlot(figsize=(10, 8)) \
            .lplot(0, valid_dt, valid_p) \
            .lplot(0, valid_dt, ma_fast[w_slow:], color='C1',
                   linewidth=1.5, linestyle='--', label=f'MA {w_fast}') \
            .lplot(0, valid_dt, ma_slow[w_slow:], color='C2',
                   linewidth=1.5, linestyle='--', label=f'MA {w_slow}') \
            .scatter(0, valid_dt[atl_idx], valid_p[atl_idx], s=40, marker='v',
                     color='firebrick') \
            .scatter(0, valid_dt[ath_idx], valid_p[ath_idx], s=40, marker='^',
                     color='forestgreen') \
            .annotate(0, f'{last_price:.2f}', (dt_p[-1], last_price), fontsize=12) \
            .annotate(0, f'{ath_ret:.1%}', (valid_dt[ath_idx], valid_p[ath_idx]),
                      fontsize=12, color='forestgreen', ha='right', va='bottom') \
            .annotate(0, f'{atl_ret:.1%}', (valid_dt[atl_idx], valid_p[atl_idx]),
                      fontsize=12, color='firebrick', ha='right', va='top')

        alerts_to_plot = []
        while alerts_data:
            a = alerts_data.pop()
            color = 'C4' if a[0] in 'SR' else 'C3'
            style = '-' if a[1] == '' else '--'
            pl.line(0, 'xh', a[2], color=color, linestyle=style, linewidth=1)
            if a[1] != '':
                alerts_to_plot.append(a)

        pl.plot() \
            .save(fig_full[0]) \
            .clf()

        # Create a DataFrame for alerts
        if len(alerts_to_plot) > 0:
            alerts_to_plot.sort(key=lambda x: x[2])
            df = pd.DataFrame(
                alerts_to_plot,
                columns=['condition', 'status', 'price', 'new', 'date trigger']
            )
            res.alerts_table = df.to_html(
                index=False,
                na_rep='-',
                formatters={'price': '{:,.2f}'.format, },
            )
        else:
            res.alerts_table = f'No alerts triggered'
