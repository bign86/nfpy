#
# Portfolio Report
# Report class for the Portfolio Data
#

from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import (Any, Optional)

from nfpy.Assets import TyAsset
import nfpy.Financial.Portfolio as Ptf
import nfpy.IO as IO
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


class ReportPortfolio(BaseReport):
    DEFAULT_P = {
        "d_rate": 0.00,
        "baseData": {"time_spans": None},
        "portfolioOptimization": {
            "algorithms": {
                "MarkowitzModel": {"gamma": .0},
                "MinimalVarianceModel": {"gamma": .0},
                "MaxSharpeModel": {"gamma": .0},
                "RiskParityModel": {}
            },
            "iterations": 30,
            "start": None,
            "t0": None
        },
        "alerts": {
            "w_ma_slow": 120,
            "w_ma_fast": 21,
            "w_sr_slow": 120,
            "w_sr_fast": 21,
            "sr_mult": 5.0
        }
    }
    _PTF_PLT_STYLE = {
        'Markowitz': (
            'plot',
            {
                'linestyle': '-', 'linewidth': 2., 'marker': '',
                'color': 'C0', 'label': 'EffFrontier'
            }
        ),
        'MaxSharpe': (
            'scatter',
            {'marker': 'o', 'color': 'C1', 'label': 'MaxSharpe'}
        ),
        'MinVariance': (
            'scatter',
            {'marker': 'o', 'color': 'C2', 'label': 'MinVariance'}
        ),
        'RiskParity': (
            'scatter',
            {'marker': 'o', 'color': 'C4', 'label': 'RiskParity'}
        ),
    }

    def __init__(self, data: ReportData, path: Optional[str] = None):
        super().__init__(data, path)
        self._time_spans = (
            Cn.DAYS_IN_1M, 3 * Cn.DAYS_IN_1M, 6 * Cn.DAYS_IN_1M, Cn.DAYS_IN_1Y
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
        t0 = self._cal.t0
        start = pd.Timestamp(year=(t0.year - 2), month=t0.month, day=t0.day)

        opt_p = self._p.get('portfolioOptimization', {})
        opt_p.update({'start': start.asm8, 't0': t0.asm8})

        self._p['portfolioOptimization'] = opt_p

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
        for uid in self.uids:
            print(f'  > {uid}')
            try:
                asset = self._af.get(uid)
                if asset.type != 'Portfolio':
                    msg = f'{uid} is not a portfolio'
                    raise Ex.AssetTypeError(msg)
                self._init_input()

                res = Ut.AttributizedDict()
                pe = Ptf.PortfolioEngine(asset)
                self._calc_ptf(asset, res, pe)
                self._calc_optimization(asset, res, pe)
                outputs[uid] = res

            except (RuntimeError, Ex.AssetTypeError) as ex:
                Ut.print_exc(ex)

        return outputs

    def _calc_ptf(self, asset: TyAsset, res: Ut.AttributizedDict,
                  pe: Ptf.PortfolioEngine) -> None:
        # General infos
        res.info = {
            k: getattr(asset, k)
            for k in ('uid', 'description', 'name', 'currency',
                      'inception_date', 'benchmark', 'num_constituents')
        }

        # Relative path in results object
        fig_full, fig_rel = self._get_image_paths(
            (
                (asset.uid,), ('Ptf',), ('p_price', 'divs', 'pies')
            )
        )
        res.img_value_hist = fig_rel[0]
        res.img_divs_hist = fig_rel[1]
        res.img_conc_pies = fig_rel[2]

        t0 = self._cal.t0

        # Prices: full performance
        dt_p, v_p, v_no_divs = pe.performance()
        _, v_r = pe.returns

        last_price = Math.last_valid_value(v_p, dt_p, t0.asm8)[0]

        IO.TSPlot(yl=(f'Performance ({asset.currency})',)) \
            .lplot(0, dt_p, v_p, label='Capital + Divs.') \
            .lplot(0, dt_p, v_no_divs, color='C2', label='Capital only') \
            .plot() \
            .save(fig_full[0]) \
            .close(True)

        # Last total value
        last_tot_value, idx = Math.last_valid_value(
            pe.total_value[1],
            dt_p, t0.asm8
        )
        res.last_tot_value = last_tot_value
        res.last_tot_date = str(dt_p[idx])[:10]

        # Statistics table and betas
        stats = np.empty((2, len(self._time_spans)))
        ann_vola = np.sqrt(250)
        for i, span in enumerate(self._time_spans):
            start = self._cal.shift(t0, -span, 'D')
            slc_sp = Math.search_trim_pos(
                dt_p,
                start=start.asm8,
                end=t0.asm8
            )

            stats[0, i] = float(np.nanstd(v_r[slc_sp])) * ann_vola
            first_price = Math.next_valid_value(v_p[slc_sp])[0]
            stats[1, i] = last_price / first_price - 1.

        # Render dataframes
        res.stats = pd.DataFrame(
            stats.T,
            index=self._time_spans,
            columns=('\u03C3 (Y)', 'tot. return')
        ).to_html(
            index=True,
            formatters={
                '\u03C3 (Y)': '{:,.1%}'.format,
                'tot. return': '{:,.1%}'.format,
            },
            border=None,
            **PD_STYLE_PROP
        )

        # Portfolio summary
        summary = pe.summary()
        res.tot_value = summary['tot_value'],
        res.tot_deposits = summary['tot_deposits']
        res.tot_withdrawals = summary['tot_withdrawals']

        merged = pd.merge(
            summary['constituents_data'],
            pd.DataFrame(
                pe.weights[-1],
                index=asset.constituents_uids,
                columns=['weights']
            ),
            left_on='uid',
            right_index=True
        )
        res.cnsts_data = merged.to_html(
            index=False,
            formatters={
                'alp': '{:,.2f}'.format,
                'cost (FX)': '{:,.2f}'.format,
                f'value ({asset.currency})': '{:,.2f}'.format,
                'quantity': '{:,.0f}'.format,
                'weights': '{:,.1%}'.format,
            },
            **PD_STYLE_PROP
        )

        # Dividends received
        res.div_ttm = pe.dividends_received_ttm()
        res.div_history = pe.dividends_received_yearly()

        IO.TSPlot(yl=(f'Dividends ({asset.currency})',)) \
            .lplot(0, *pe.dividends_received_history()) \
            .plot() \
            .save(fig_full[1]) \
            .close(True)

        # Concentration measures
        plt.style.use('seaborn')
        props_plot = {
            'wedgeprops': dict(width=0.4),
            'startangle': -40,
            'textprops': dict(color='w', weight='bold'),
            'autopct': lambda pct: f'{pct / 100.:.1%}',
            'pctdistance': .8,
        }
        props_leg = {
            'loc': "center left",
            'bbox_to_anchor': (1, 0, 0.5, 1)
        }
        fig, ax = plt.subplots(nrows=1, ncols=3, figsize=(20, 5),
                               subplot_kw=dict(aspect="equal"))

        labels, data = pe.currency_concentration()
        wedges, texts, autotext = ax[0].pie(data, **props_plot)
        ax[0].legend(wedges, labels, **props_leg)

        labels, data = pe.country_concentration()
        wedges, texts, autotext = ax[1].pie(data, **props_plot)
        ax[1].legend(wedges, labels, **props_leg)

        labels, data = pe.sector_concentration()
        wedges, texts, autotext = ax[2].pie(data, **props_plot)
        ax[2].legend(wedges, labels, **props_leg)

        fig.tight_layout()
        fig.savefig(fig_full[2], format='png')

    def _calc_optimization(self, asset: TyAsset, res: Ut.AttributizedDict,
                           pe: Ptf.PortfolioEngine) -> None:
        # Plot portfolio data
        fig_full, fig_rel = self._get_image_paths(
            ((asset.uid,), ('PtfOpt',), ('ptf_opt_res',))
        )
        res.var_ret_plot = fig_rel[0]

        idx = asset.constituents_uids.index(asset.currency)
        wgt = np.delete(pe.weights[-1], idx)
        wgt /= np.sum(wgt)

        # Portfolio optimization
        oe = Ptf.OptimizationEngine(
            asset.uid,
            **self._p['portfolioOptimization']
        ).result

        # Create plot
        pl = IO.PtfOptimizationPlot(x_zero=(.0,), y_zero=(.0,))

        # Process data
        models = ['Actual']
        weights = [wgt]
        for r in oe.results:
            if r.success is False:
                continue

            model = r.model
            call, kw = self._PTF_PLT_STYLE[model]
            pl.add(0, call, r, **kw)

            if model == 'Markowitz':
                continue

            models.extend([model, model + '_delta'])
            model_wgt = r.weights[0]
            weights.extend([model_wgt, model_wgt / wgt - 1.])

        # TODO: Current state of portfolio. Insert a marker on the plot for the
        #       current portfolio to compare with the optimizations.

        # Save out figure
        pl.plot() \
            .save(fig_full[0]) \
            .close(True)

        # Create correlation matrix
        res.corr = pd.DataFrame(oe.corr, index=oe.uids, columns=oe.uids) \
            .to_html(
            float_format='{:,.0%}'.format,
            classes='matrix'
        )

        # Create results table
        res.weights = pd.DataFrame(
            np.vstack(weights).T,
            index=oe.uids,
            columns=models
        ).to_html(
            float_format='{:,.1%}'.format,
        )
