#
# DCF Report
# Report class for the Discounted Cash Flow Model
#

from copy import deepcopy

import nfpy.Models as Mod

from .BaseReport import BaseReport

# FIXME: terrible hack to be removed as soon as possible
import pandas

if int(pandas.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}
# FIXME: end of the shame


class ReportDCF(BaseReport):
    _M_OBJ = Mod.DiscountedCashFlowModel
    INPUT_QUESTIONS = (
        ('date', 'Insert date of calculation (default None): ',
         {'idesc': 'datetime', 'optional': True}),
        ('past_horizon', 'Insert length of past horizon (default 5): ',
         {'idesc': 'int', 'optional': True}),
        ('future_proj', 'Insert length of future projection (default 3): ',
         {'idesc': 'int', 'optional': True}),
        ('perpetual_rate', 'Insert the perpetual rate of growth (default 0.): ',
         {'idesc': 'float', 'optional': True}),
    )

    def _init_input(self) -> dict:
        """ Prepare the input arguments for the model. """
        p = deepcopy(self._p)
        p.update({'uid': self._uid})
        return p

    def _create_output(self, res):
        """ Create the final output. """
        df = res.df
        df.index = df.index.strftime("%Y-%m-%d")
        df = df.T
        res.df = df.style.format(
            "{:.2f}",
            **PD_STYLE_PROP) \
            .set_table_attributes('class="dataframe"') \
            .render()
        return res
