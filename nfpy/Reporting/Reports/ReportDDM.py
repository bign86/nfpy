#
# Report Market Short
# Report class for the short report on market data
#

from collections import defaultdict
import numpy as np
import pandas as pd
from typing import Any

import nfpy.IO.Utilities
from nfpy.Assets import TyAsset
from nfpy.Financial import DividendFactory
from nfpy.Financial.EquityValuation import DDM
import nfpy.IO as IO
from nfpy.Tools import (
    Exceptions as Ex,
    Utilities as Ut
)

from .BaseReport import BaseReport

# Remove a style property for Pandas version 0.x
if int(pd.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}


class ReportDDM(BaseReport):

    def _one_off_calculations(self) -> None:
        """ Perform all non-uid dependent calculations for efficiency. """
        pass

    def _calculate(self) -> Any:
        """ Calculate the required models.
            MUST ensure that the model parameters passed in <args> are not
            modified so that the database parameters in self._p are not
            changed from one asset to the next.
        """
        outputs = defaultdict(dict)
        uid = self.uids[0]
        print(f'  > {uid}')
        try:
            asset = self._af.get(uid)
            if asset.type != 'Equity':
                raise Ex.AssetTypeError(f'ReportDDM(): {uid} is not an equity')

            res = Ut.AttributizedDict()
            self._calc_ddm(asset, res)
            outputs[asset.ticker] = res

        except (RuntimeError, ValueError, Ex.AssetTypeError) as ex:
            nfpy.IO.Utilities.print_exc(ex)

        return outputs

    def _calc_ddm(self, asset: TyAsset, res: Ut.AttributizedDict) -> None:
        # Build dividends structure and quick exit if not a dividend payer
        df = DividendFactory(asset)
        if not df.is_dividend_payer:
            raise Ex.AssetTypeError(f'ReportDDM(): {asset.uid} not a dividend payer!')

        # General infos
        res.info = {
            k: getattr(asset, k)
            for k in ('uid', 'description', 'ticker', 'isin', 'country',
                      'currency', 'company', 'index')
        }

        # Relative path in results object
        fig_full, fig_rel = self._get_image_paths(
            (
                (asset.uid,), ('DDM',),
                (
                    'p_price',
                    'divs',
                    'growth_rates',
                )
            )
        )
        res.img_prices_long = fig_rel[0]
        res.img_divs = fig_rel[1]
        res.img_growth_rates = fig_rel[2]

        # Dividends
        res.is_dividend_suspended = df.is_dividend_suspended
        res.freq_div = df.frequency
        res.ytd_yrl_div = df.ytd_div()
        res.ytd_yrl_yield = df.ytd_yield() * 100.
        yearly_div_dt, yearly_div = df.annual_dividends
        yearly_ret_div = yearly_div[1:] / yearly_div[:-1] - 1.
        yearly_div_dt = yearly_div_dt + np.timedelta64(6, 'M')
        all_div_dt, all_div = df.dividends
        ret_div = all_div[1:] / all_div[:-1] - 1.

        _, yrl_yield = df.annual_yields()
        if len(yrl_yield) >= 1:
            res.last_yrl_div = yearly_div[-1]
            res.last_yrl_yield = yrl_yield[-1] * 100.
        else:
            res.last_yrl_div = 0.
            res.last_yrl_yield = 0.

        # Last price
        last_price, last_price_dt, _ = asset.last_price()
        res.last_price = last_price
        res.last_price_date = str(last_price_dt)[:10]

        # Prices: full history plot
        prices = asset.prices
        ath_idx = np.argmax(prices)
        atl_idx = np.argmin(prices)
        ath_ret = prices[ath_idx] / last_price - 1.
        atl_ret = prices[atl_idx] / last_price - 1.

        pl3 = IO.TSPlot(x_zero=[.0]) \
            .lplot(0, prices, color='k', linewidth=.75) \
            .annotate(0, f' {last_price:.2f}', (last_price_dt, last_price), fontsize=12) \
            .annotate(0, f'{ath_ret:.1%}', (prices.index[ath_idx], prices[ath_idx]),
                      fontsize=12, color='forestgreen', ha='right', va='bottom') \
            .annotate(0, f'{atl_ret:.1%}', (prices.index[atl_idx], prices[atl_idx]),
                      fontsize=12, color='firebrick', ha='right', va='top') \

        # Dividends Discount Model Calculation
        try:
            ddm_res = DDM(asset.uid, **self._p) \
                .result(**self._p)
        except (Ex.MissingData, ValueError) as ex:
            res.has_ddm = False

            # Save the prices plot regardless of whether the model completed
            pl3.plot() \
                .save(fig_full[0]) \
                .clf()

            nfpy.IO.Utilities.print_exc(ex)
            return

        res.has_ddm = True
        res.ddm_success = ddm_res.success
        res.ddm_msg = ddm_res.msg

        if ddm_res.applicable:
            res.ddm_im_ke = ddm_res.outputs['implied_ke'] * 100.
            res.ddm_ke = ddm_res.outputs['ke'] * 100.
            res.ddm_lt_g = ddm_res.outputs['lt_growth'] * 100.
            res.ddm_capm = ddm_res.outputs.get('capm', None)

            res.ddm_res_no_gwt = ddm_res.outputs['no_growth']
            res.ddm_res_manual = ddm_res.outputs.get('manual_growth', None)
            res.ddm_res_hist = ddm_res.outputs.get('historical_growth', None)
            res.ddm_res_roe = ddm_res.outputs.get('ROE_growth', None)

            res.ddm_inputs = self._p

            # Plotting
            dates = ddm_res.outputs['dates']
            pl = IO.Plotter(
                xl=('Date',),
                yl=(f'Price ({ddm_res.outputs["ccy"]})',),
                x_zero=[.0]
            ) \
                .lplot(0, yearly_div_dt, yearly_div, color='k',
                       marker='o', label='yearly paid divs.') \
                .lplot(0, ddm_res.outputs['div_ts'], color='gray',
                       marker='X', linestyle='--', label='paid divs.') \
                .lplot(0, dates, y=ddm_res.outputs['no_growth']['cf'][1],
                       color='C0', label='no growth')

            manual_data = ddm_res.outputs.get('manual_growth', None)
            if manual_data is not None:
                pl.lplot(0, dates, y=manual_data['cf'][1],
                         marker='o', color='C1', label='manual')

            hist_data = ddm_res.outputs.get('historical_growth', None)
            if hist_data is not None:
                pl.lplot(0, dates, y=hist_data['cf'][1],
                         marker='o', color='C2', label='historical')

            roe_data = ddm_res.outputs.get('ROE_growth', None)
            if roe_data is not None:
                pl.lplot(0, dates, y=roe_data['cf'][1],
                         marker='o', color='C3', label='ROE')

            pl.plot() \
                .save(fig_full[1]) \
                .clf()

            lt_growth_date = dates[-1] + \
                             np.timedelta64(1, 'Y').astype('timedelta64[D]')

            pl2 = IO.Plotter(xl=('Date',), yl=(f'Rate',), x_zero=[.0])

            lt_growth = ddm_res.outputs['lt_growth']
            if manual_data is not None:
                pl2.lplot(
                    0,
                    np.r_[yearly_div_dt[-1], dates, lt_growth_date],
                    y=np.r_[yearly_ret_div[-1], manual_data['rates'], lt_growth],
                    marker='o', color='C1', label='manual'
                )

            if hist_data is not None:
                pl2.lplot(
                    0,
                    np.r_[yearly_div_dt[-1], dates, lt_growth_date],
                    y=np.r_[yearly_ret_div[-1], hist_data['rates'], lt_growth],
                    marker='o', color='C2', label='historical'
                )

            if roe_data is not None:
                pl2.lplot(
                    0,
                    np.r_[yearly_div_dt[-1], dates, lt_growth_date],
                    y=np.r_[yearly_ret_div[-1], roe_data['rates'], lt_growth],
                    marker='o', color='C3', label='ROE'
                )

            pl2.lplot(0, yearly_div_dt[1:], yearly_ret_div,
                      color='k', marker='o', label='yearly divs. growth') \
                .lplot(0, all_div_dt[1:], ret_div, color='gray',
                       marker='X', linestyle='--', label='divs. growth') \
                .scatter(0, lt_growth_date, lt_growth, s=120,
                         color='k', marker='x', label='perpetual growth', zorder=1000) \
                .plot() \
                .save(fig_full[2]) \
                .clf()

            # Add fair values to prices plot
            pl3.line(0, 'xh', ddm_res.outputs['no_growth']["fv"],
                     color='C0', label='no growth')

            if manual_data is not None:
                pl3.line(0, 'xh', manual_data["fv"], color='C1', label='manual')

            if hist_data is not None:
                pl3.line(0, 'xh', hist_data["fv"], color='C2', label='historical')

            if roe_data is not None:
                pl3.line(0, 'xh', roe_data["fv"], color='C3', label='ROE')

        # Save the prices plot regardless of whether the model completed
        pl3.plot() \
            .save(fig_full[0]) \
            .clf()
