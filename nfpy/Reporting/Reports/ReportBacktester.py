#
# Backtester Report
# Report class for the Backtester
#

import numpy as np
import pandas as pd
from typing import (Any, Sequence)

import nfpy.IO as IO
import nfpy.Tools.Utilities as Ut
import nfpy.Trading as Trd

from .BaseReport import BaseReport

# Remove a style property for Pandas version 0.x
if int(pd.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}


class ReportBacktester(BaseReport):
    DEFAULT_P = {
        "start_amount": 10000.,
        "strategy": "MACDHistReversalStrategy",
        "strategy_params": {
            'w_fast': 100,
            'w_slow': 200,
            'w_macd': 50
        },
        "sizer": "ConstantSplitSizer",
        "sizer_params": {'buy': .2, 'sell': .3}
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
        bk = Trd.Backtester(self.uids, self._p['start_amount'], False)
        symbol = '.'.join(['nfpy.Trading.Strategies', self._p['strategy']])
        bk.strategy = Ut.import_symbol(symbol)
        bk.parameters = self._p['strategy_params']

        symbol = '.'.join(['nfpy.Trading.Sizers', self._p['sizer']])
        class_ = Ut.import_symbol(symbol)
        bk.sizer = class_(**self._p['sizer_params'])
        try:
            bk.run()
        except (RuntimeError, IndexError) as ex:
            print(ex)

        return self._render_results(
            bk.results,
            bk.strategy,
            bk.parameters,
            self._p['sizer_params']
        )

    def _render_results(self, res_dict: Any, strategy: Trd.TyStrategy,
                        strategy_p: dict, sizer_p: Sequence) -> Any:
        outputs = {}

        # Aggregated measures
        avg_return = .0
        avg_buy = 0
        avg_sell = 0

        for uid, bt_res in res_dict.items():
            asset = self._af.get(uid)
            labels = ((uid,), ('BT',), ('results',))
            fig_full, fig_rel = self._get_image_paths(labels)
            res = Ut.AttributizedDict()

            # Relative path in results object
            res.img_results = fig_rel[0]

            # General results
            res.initial_value = bt_res.initial
            res.final_value = bt_res.final_value
            res.buy = bt_res.num_buy
            res.sell = bt_res.num_sell
            res.tot_return = bt_res.total_return * 100.

            # Aggregated results
            avg_return += bt_res.total_return
            avg_buy += bt_res.num_buy
            avg_sell += bt_res.num_sell

            # Prepare data for plotting
            dates = asset.prices.index.values
            prices = asset.prices.values
            sig_dates = np.array([v[0] for v in bt_res.trades])
            signals = np.array([v[1] for v in bt_res.trades])
            sell_dates = np.array(
                [
                    v[0]
                    for v in bt_res.trades
                    if v[1] == -1
                ]
            )
            returns = np.array(
                [
                    v[7]
                    for v in bt_res.trades
                    if v[1] == -1
                ]
            )

            _idx = np.searchsorted(dates, sig_dates)
            _shares = np.zeros(dates.shape[0], dtype=int)
            np.put(
                _shares, _idx,
                [v[1] * v[3] for v in bt_res.trades]
            )

            _cash = np.zeros(dates.shape[0])
            _cash[0] = bt_res.initial
            np.put(
                _cash, _idx,
                [-v[1] * v[4] for v in bt_res.trades]
            )
            _cash = _cash.cumsum()
            _shares = _shares.cumsum()

            _shares_val = prices * _shares
            _total_val = _shares_val + _cash
            _perf = asset.performance()

            # Plotting
            pl = IO.Plotter(4, 1, figsize=(15, 12.8)) \
                .lplot(0, dates, _total_val, label='tot. value', color='C0') \
                .lplot(0, dates, _shares_val / _total_val, label='eq%',
                       color='C1', linewidth=.75, secondary_y=True) \
                .lplot(0, dates, _cash / _total_val, label='cash%',
                       color='C2', linewidth=.75, secondary_y=True) \
                .lplot(1, dates, _total_val, label='total value') \
                .lplot(1, dates, _shares_val, label='equity value') \
                .lplot(1, dates, _cash, label='cash value') \
                .lplot(3, dates, _perf, label='price perf.', color='C5') \
                .lplot(3, dates, _total_val / bt_res.initial, label='ptf perf.', color='C0') \
                .scatter(2, sell_dates, returns, label='returns') \
                .line(2, 'xh', .0)

            for i in range(sig_dates.shape[0]):
                color = 'C2' if signals[i] == -1 else 'C1'
                pl.line(0, 'xv', sig_dates[i], color=color, linewidth=.6)
                pl.line(1, 'xv', sig_dates[i], color=color, linewidth=.6)
                pl.line(3, 'xv', sig_dates[i], color=color, linewidth=.6)

            pl.plot() \
                .save(fig_full[0]) \
                .close(True)

            # Render dataframes
            df = pd.DataFrame(
                bt_res.trades,
                columns=('date', 'signal', 'price', 'shares',
                         'd_cash', 'base cost', 'P&L', 'R')
            )
            res.trades_table = df.style.format(
                formatter={
                    'price': '{:,.2f}'.format,
                    'shares': '{:,.0f}'.format,
                    'd_cash': '{:,.2f}'.format,
                    'base cost': '{:,.2f}'.format,
                    'P&L': '{:,.2f}'.format,
                    'R': '{:,.1%}'.format
                },
                **PD_STYLE_PROP) \
                .set_table_attributes('class="dataframe"') \
                .render()

            outputs[uid] = res

        # Add aggregated results to outputs
        tests_performed = len(res_dict)
        aggregated_res = Ut.AttributizedDict()

        aggregated_res.name = strategy.NAME
        aggregated_res.description = strategy.DESCRIPTION
        aggregated_res.parameters = strategy_p
        aggregated_res.sizer = sizer_p

        aggregated_res.tests_performed = tests_performed
        aggregated_res.avg_return = avg_return / tests_performed * 100.
        aggregated_res.avg_buy = avg_buy / tests_performed
        aggregated_res.avg_sell = avg_sell / tests_performed
        outputs['__aggregated_results__'] = aggregated_res

        return outputs
