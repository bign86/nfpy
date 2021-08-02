#
# Market Report
# Report class for the Market Data
#

import numpy as np
import pandas as pd
from typing import Any

import nfpy.IO as IO
import nfpy.Models as Mod
from nfpy.Tools import (Constants as Cn, Utilities as Ut)

from .BaseReport import BaseReport

# FIXME: terrible hack to be removed as soon as possible
if int(pd.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}


class ReportMarket(BaseReport):
    # _M_OBJ = Mod.MarketDataModel
    # _IMG_LABELS = ('p_price',)
    _M_LABEL = 'Market'
    _PTF_PLT_STYLE = {
        'Markowitz': (
            'plot',
            {'linestyle': '-', 'linewidth': 2., 'marker': '',
             'color': 'C0', 'label': 'EffFrontier'}
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
    INPUT_QUESTIONS = (
        ('date', 'Insert date of calculation (default None): ',
         {'idesc': 'datetime', 'optional': True}),
    )

    def _init_input(self, p: dict, type_: str) -> dict:
        """ Prepare and validate the the input parameters for the model. This
            includes verifying the parameters are correct for the models in the
            report.
        """
        params = {}
        params.update(p)

        if type_ == 'Portfolio':
            t0 = self._cal.t0
            start = pd.Timestamp(year=(t0.year - 2), month=t0.month, day=t0.day)
            params.update({'iterations': 50, 'start': start.asm8,
                           't0': t0.asm8, 'gamma': None})

        return params

    def _calculate(self, *args: tuple) -> Any:
        """ Calculate the required models. """
        asset = self._af.get(args[0])
        type_ = asset.type
        # results = ()
        if type_ == 'Bond':
            res1 = self._calc_bond(args)
            fields = ('uid', 'description', 'isin', 'issuer', 'currency',
                      'asset_class', 'inception_date', 'maturity', 'coupon',
                      'c_per_year')
            res1.info = {k: getattr(asset, k) for k in fields}
            self._jinja_filters['Bond'] = self.is_mbdm
            res2 = self._calc_trading(args)
            results = (res1, res2)
        elif type_ == 'Company':
            res1 = self._calc_company(args)
            fields = ('uid', 'description', 'name', 'sector', 'industry',
                      'equity', 'currency', 'country')
            res1.info = {k: getattr(asset, k) for k in fields}
            # self._jinja_filters['Company'] = None
            results = (res1,)
        elif type_ == 'Currency':
            res1 = self._calc_generic(args)
            fields = ('uid', 'description', 'price_country', 'base_country',
                      'price_ccy', 'base_ccy')
            res1.info = {k: getattr(asset, k) for k in fields}
            self._jinja_filters['Currency'] = self.is_madm
            results = (res1,)
        elif type_ == 'Equity':
            res1 = self._calc_equity(args)
            fields = ('uid', 'description', 'ticker', 'isin', 'country',
                      'currency', 'company', 'index')
            res1.info = {k: getattr(asset, k) for k in fields}
            self._jinja_filters['Equity'] = self.is_medm
            res2 = self._calc_trading(args)
            results = (res1, res2)
        elif type_ == 'Indices':
            res1 = self._calc_generic(args)
            fields = ('uid', 'description', 'ticker', 'area', 'currency', 'ac')
            res1.info = {k: getattr(asset, k) for k in fields}
            self._jinja_filters['Indices'] = self.is_madm
            results = (res1,)
        elif type_ == 'Portfolio':
            res1 = self._calc_ptf(args)
            fields = ('uid', 'description', 'name', 'currency',
                      'inception_date', 'benchmark', 'num_constituents')
            res1.info = {k: getattr(asset, k) for k in fields}
            # res2 = self._calc_trading(args)
            # results = (res1, res2)
            results = (res1,)
        else:
            raise RuntimeError('Asset type not recognized')

        return results

    def _calc_generic(self, args: tuple) -> Any:
        uid, p = args
        mod = Mod.MarketAssetsDataBaseModel(uid, **p)
        return self._render_out_generic(mod.result(**p), args)

    def _render_out_generic(self, res: Any, args: tuple) -> Any:
        labels = ((res.uid,), ('MA',), ('p_price',))
        fig_full, fig_rel = self._get_image_paths(labels)
        res.img_prices = fig_rel[0]

        # Full history plot
        pl = IO.TSPlot()
        pl.lplot(0, res.prices, label='Price')
        pl.plot()
        pl.save(fig_full[0])
        pl.clf()
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

    def _calc_equity(self, args: tuple) -> Any:
        uid, p = args
        mod = Mod.MarketEquityDataModel(uid, **p)
        return self._render_out_equity(mod.result(**p), args)

    def _render_out_equity(self, res: Any, args: tuple) -> Any:
        labels = ((res.uid,), ('ME',), ('p_price', 'perf', 'beta'))
        fig_full, fig_rel = self._get_image_paths(labels)

        # Relative path in results object
        res.img_prices_long = fig_rel[0]
        res.img_performance = fig_rel[1]
        res.img_beta = fig_rel[2]

        # Full history plot
        pl = IO.TSPlot()
        pl.lplot(0, res.prices, label='Price')
        pl.plot()
        pl.save(fig_full[0])
        # pl.clf()
        pl.close(True)

        # Performance plot
        pl = IO.TSPlot()
        pl.lplot(0, res.perf, color='C0', linewidth=1.5, label=res.uid)
        pl.lplot(0, res.perf_idx, color='C2', linewidth=1.5, label='Index')
        pl.plot()
        pl.save(fig_full[1])
        # pl.clf()
        pl.close(True)

        # Beta plot
        start = self._cal.shift(res.date, -Cn.DAYS_IN_1Y, 'D')
        r = res.returns.loc[start:]
        ir = res.index_returns.loc[start:]
        beta = res.beta_params
        xg = np.linspace(min(float(np.nanmin(ir.values)), .0),
                         float(np.nanmax(ir.values)), 2)
        yg = beta[0] * xg + beta[2]

        pl = IO.Plotter(x_zero=(.0,), y_zero=(.0,))
        pl.scatter(0, ir.values, r.values, color='C0', linewidth=.0,
                   marker='o', alpha=.5)
        pl.lplot(0, xg, yg, color='C0')
        pl.plot()
        pl.save(fig_full[2])
        # pl.clf()
        pl.close(True)

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

    def _calc_bond(self, args: tuple) -> Any:
        uid, p = args
        mod = Mod.MarketBondDataModel(uid, **p)
        return self._render_out_bond(mod.result(**p), args)

    def _render_out_bond(self, res: Any, args: tuple) -> Any:
        labels = ((res.uid,), ('ME',), ('p_price', 'price_ytm'))
        fig_full, fig_rel = self._get_image_paths(labels)

        # Relative path in results object
        res.prices_long, res.prices_ytm = fig_rel

        # Full history plot
        pl = IO.TSPlot()
        pl.lplot(0, res.prices, label='Price')
        pl.lplot(0, res.yields, color='C2', label='Yield', secondary_y=True)
        pl.plot()
        pl.save(fig_full[0])
        # pl.clf()
        pl.close(True)

        # YTM plot
        data = res.yields_array
        bars = res.ytm_bars
        x_zero = res.yields_array[0, 3]
        y_zero = res.yields_array[1, 3]
        pl = IO.TSPlot(xl=('Price',), yl=('YTM',), y_zero=(y_zero,),
                       x_zero=(x_zero,))
        pl.lplot(0, data[0, :], data[1, :], marker='', linestyle='-',
                 label=r'$YTM(P_0, t_0)$')
        pl.line(0, 'xh', bars[1, 0], linestyle='--', linewidth='.8',
                color="C1", label=r'$YTM(P_0\pm\delta^{1M}, t_0)$')
        pl.line(0, 'xh', bars[1, 1], linestyle='--', linewidth='.8',
                color="C1")
        pl.line(0, 'xh', bars[1, 2], linestyle='--', linewidth='.8',
                color="C2", label=r'$YTM(P_0\pm\delta^{6M}, t_0)$')
        pl.line(0, 'xh', bars[1, 3], linestyle='--', linewidth='.8',
                color="C2")
        pl.plot()
        pl.save(fig_full[1])
        # pl.clf()
        pl.close(True)

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

    def _calc_ptf(self, args: tuple) -> Any:
        uid, p = args
        mod = Mod.MarketPortfolioDataModel(uid, **p)
        mkt_res = mod.result(**p)
        oe = Mod.OptimizationEngine(uid, **p)
        # oe_res = oe.result
        # res.update(oe.result)
        return self._render_out_ptf((mkt_res, oe.result), args)

    def _render_out_ptf(self, res: Any, args: tuple) -> Any:
        # Market data
        mkt_res = res[0]
        final_res = self._render_out_generic(mkt_res, args)

        # Render dataframes
        df = mkt_res.cnsts_data
        final_res.cnsts_data = df.style \
            .format('{:,.2f}', subset=['alp', 'cost (FX)',
                                       'value ({})'.format(mkt_res.currency)]) \
            .format('{:,.0f}', subset=['quantity']) \
            .format('{:,.1%}', subset=['weights']) \
            .hide_index() \
            .set_table_attributes('class="dataframe"') \
            .render()

        # Plot portfolio data
        labels = ((mkt_res.uid,), ('PtfOpt',), ('ptf_opt_res',))
        fig_full, fig_rel = self._get_image_paths(labels)

        ptf = self._af.get(mkt_res.uid)
        idx = ptf.constituents_uids.index(ptf.currency)
        wgt = np.delete(ptf.weights.values[-1], idx)
        wgt /= np.sum(wgt)

        # Create result object
        final_res.var_ret_plot = fig_rel[0]

        # Create plot
        pl = IO.PtfOptimizationPlot(x_zero=(.0,), y_zero=(.0,))

        # Process data
        models = ['Actual']
        weights = [wgt]
        for r in res[1].results:
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

        # Save out figure
        pl.plot()
        pl.save(fig_full[0])
        # pl.clf()
        pl.close(True)

        # Create correlation matrix
        corr_df = pd.DataFrame(res[1].corr, index=res[1].uids,
                               columns=res[1].uids)
        final_res.corr = corr_df.style \
            .format('{:,.0%}') \
            .set_table_attributes('class="matrix"') \
            .render()
        # .background_gradient(cmap='RdYlGn', axis=None) \

        # Create results table
        wgt_df = pd.DataFrame(np.vstack(weights).T,
                              index=res[1].uids,
                              columns=models)
        final_res.weights = wgt_df.style \
            .format('{:,.1%}') \
            .set_table_attributes('class="dataframe"') \
            .render()

        return final_res

    def _calc_trading(self, args: tuple) -> Any:
        uid, p = args
        mod = Mod.TradingModel(uid, **p)
        return self._render_out_trd(mod.result(**p), args)

    def _render_out_trd(self, res: Any, args: tuple) -> Any:
        labels = ((res.uid,), ('TRD',), ('p_long', 'p_short'))
        fig_full, fig_rel = self._get_image_paths(labels)
        res.prices_long, res.prices_short = fig_rel
        full_name_long, full_name_short = fig_full

        # Moving averages plot
        start = res.ma_fast.index[0]
        p = res.prices

        pl = IO.TSPlot()
        pl.lplot(0, p.loc[start:])
        pl.lplot(0, res.ma_fast, color='C1', linewidth=1.5,
                 linestyle='--', label='MA {}'.format(res.w_fast))
        pl.lplot(0, res.ma_slow.loc[start:], color='C2', linewidth=1.5,
                 linestyle='--', label='MA {}'.format(res.w_slow))
        pl.plot()
        pl.save(full_name_long)
        pl.clf()

        # Alerts plot
        pl = res.alerts.plot()
        pl.plot()
        pl.save(full_name_short)
        # pl.clf()
        pl.close(True)

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
        df = pd.concat((df_b, df_t), ignore_index=True)
        df.sort_values('price', inplace=True)
        res.breach_table = df.style.format(
            formatter={
                'price': '{:,.2f}'.format,
            },
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()

        return res

    def _calc_company(self, args: tuple) -> Any:
        uid, p = args
        dcf_res = None
        try:
            mod = Mod.DiscountedCashFlowModel(uid, **p)
            dcf_res = mod.result(**p)
        except Exception as ex:
            print('{} - {}'.format(type(ex).__name__, ex))

        ddm_res = None
        try:
            mod = Mod.DividendDiscountModel(uid, **p)
            ddm_res = mod.result(**p)
        except Exception as ex:
            print('{} - {}'.format(type(ex).__name__, ex))

        return self._render_out_company((dcf_res, ddm_res), args)

    def _render_out_company(self, res: Any, args: tuple) -> Any:
        final_res = Ut.AttributizedDict()

        # Render DDM
        ddm_res = res[1]
        if ddm_res is not None:
            final_res.has_ddm = True
            final_res.ccy = ddm_res.ccy
            final_res.last_price = ddm_res.last_price
            final_res.ret_zg = ddm_res.ret_no_growth * 100.
            final_res.ret_wg = ddm_res.ret_with_growth * 100.
            final_res.fair_value_no_growth = ddm_res.fair_value_no_growth
            final_res.fair_value_with_growth = ddm_res.fair_value_with_growth

            fig_full, fig_rel = self._get_image_paths(ddm_res.uid)
            final_res.div_fig = fig_rel[0]

            # Save out figure
            pl = IO.TSPlot(yl=('Dividend',))
            pl.lplot(0, ddm_res.div_ts, marker='o', label='historical')
            pl.lplot(0, ddm_res.div_zg[0, :], ddm_res.div_zg[1, :],
                     marker='o', label='no growth')
            pl.lplot(0, ddm_res.div_gwt[0, :], ddm_res.div_gwt[1, :],
                     marker='o', label='w/ growth')
            pl.plot()
            pl.save(fig_full[0])
            # pl.clf()
            pl.close(True)
        else:
            final_res.has_ddm = False

        # Render DCF
        dcf_res = res[0]
        if dcf_res is not None:
            final_res.has_dcf = True
            final_res.ccy = dcf_res.ccy
            final_res.last_price = dcf_res.last_price
            final_res.fair_value = dcf_res.fair_value

            df = dcf_res.df
            df.index = df.index.strftime("%Y-%m-%d")
            # df = df.T
            final_res.df = df.T.style \
                .format(
                    "{:.2f}",
                    **PD_STYLE_PROP) \
                .set_table_attributes('class="dataframe"') \
                .render()
        else:
            final_res.has_dcf = False

        return final_res

    @staticmethod
    def is_madm(v: Any) -> bool:
        return isinstance(v, Mod.MADMResult)

    @staticmethod
    def is_mbdm(v: Any) -> bool:
        return isinstance(v, Mod.MBDMResult)

    @staticmethod
    def is_medm(v: Any) -> bool:
        return isinstance(v, Mod.MEDMResult)

    @staticmethod
    def is_trd(v: Any) -> bool:
        return isinstance(v, Mod.TradingResult)