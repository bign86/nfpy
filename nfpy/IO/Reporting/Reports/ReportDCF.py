#
# DCF Report
# Report class for the Discounted Cash Flow Model
#

from copy import deepcopy

import nfpy.Financial.Models as Mod

from .BaseReport import BaseReport


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
        p.update({'company': self._uid})
        return p

    def _create_output(self, res):
        """ Create the final output. """
        res.df.index = res.df.index.strftime("%Y-%m-%d")
        return res
