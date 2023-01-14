#
# Companies Report
# Class for the Companies Data
#

from collections import defaultdict
import pandas as pd
from typing import (Any, Optional)

from nfpy.Assets import TyAsset
import nfpy.IO as IO
from nfpy.Financial.EquityValuation import (
    DCF, DDM
)
import nfpy.Math as Math
from nfpy.Tools import (
    Constants as Cn,
    Exceptions as Ex,
    Utilities as Ut
)

from .BaseReport import (BaseReport, ReportData)

# Remove a style property for Pandas version 0.x
if int(pd.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}


class ReportCompanies(BaseReport):
    DEFAULT_P = {'years_price_hist': 2.}

    def __init__(self, data: ReportData, path: Optional[str] = None, **kwargs):
        super().__init__(data, path)
        self._time_spans = (
            Cn.DAYS_IN_1M, 6 * Cn.DAYS_IN_1M, Cn.DAYS_IN_1Y,
            2 * Cn.DAYS_IN_1Y, 3 * Cn.DAYS_IN_1Y, 5 * Cn.DAYS_IN_1Y
        )
        self._hist_slc = None

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
        hist_y = -self._p['years_price_hist'] * Cn.DAYS_IN_1Y
        start = self._cal.shift(t0, hist_y, 'B')
        self._hist_slc = Math.search_trim_pos(
            self._cal.calendar.values,
            start=start.asm8,
            end=t0.asm8
        )

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
                if asset.type != 'Company':
                    msg = f'{uid} is not a company'
                    raise Ex.AssetTypeError(msg)

                res = Ut.AttributizedDict()
                self._calc_equity(asset, res)
                self._calc_company(asset, res)
                outputs[uid] = res

            except (ValueError, KeyError, Ex.AssetTypeError) as ex:
                Ut.print_exc(ex)

        return outputs

    def _calc_equity(self, asset: TyAsset, res: Ut.AttributizedDict) -> None:
        # Relative path in results object
        fig_full, fig_rel = self._get_image_paths(
            (
                (asset.uid,), ('ME',), ('p_price',)
            )
        )
        res.img_prices = fig_rel[0]

        t0 = self._cal.t0

        # Prices: full history plot
        equity = self._af.get(asset.equity)
        prices = equity.prices
        v_p = prices.values
        dt_p = prices.index.values

        IO.TSPlot() \
            .lplot(0, prices[self._hist_slc], label=asset.uid) \
            .plot() \
            .save(fig_full[0]) \
            .close(True)

        # Last price
        last_price, idx = Math.last_valid_value(v_p, dt_p, t0.asm8)
        res.last_price = last_price
        res.last_price_date = str(dt_p[idx])[:10]

    def _calc_company(self, asset: TyAsset, res: Ut.AttributizedDict) -> None:
        # General infos
        res.info = {
            k: getattr(asset, k)
            for k in ('uid', 'description', 'name', 'sector', 'industry',
                      'equity', 'currency', 'country')
        }

        # Render DCF
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

        # Render DDM
        try:
            p = self._p.get('DDM', {})
            ddm_res = DDM(asset.uid, **p).result(**p)
        except Exception as ex:
            res.has_ddm = False
            Ut.print_exc(ex)
        else:
            res.has_ddm = True
            res.ret_no_growth = ddm_res.ret_no_growth * 100.
            res.ret_growth = ddm_res.ret_growth * 100.
            res.fv_no_growth = ddm_res.fv_no_growth
            res.fv_growth = ddm_res.fv_growth

            labels = ((ddm_res.uid,), ('DDM',), ('div',))
            fig_full, fig_rel = self._get_image_paths(labels)
            res.div_fig = fig_rel[0]

            # Save out figure
            IO.TSPlot(yl=('Dividend',)) \
                .lplot(0, ddm_res.div_ts, marker='o', label='historical') \
                .lplot(0, ddm_res.dates, ddm_res.div_no_growth,
                       marker='o', label='no growth') \
                .lplot(0, ddm_res.dates, ddm_res.div_growth,
                       marker='o', label='w/ growth') \
                .plot() \
                .save(fig_full[0]) \
                .close(True)
