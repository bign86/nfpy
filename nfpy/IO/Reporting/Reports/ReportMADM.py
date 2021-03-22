#
# MADM Report
# Report class for the Market Asset Data Model
#

import nfpy.Financial.Models as Mod
import nfpy.IO as IO

from .BaseReport import BaseReport

# FIXME: terrible hack to be removed as soon as possible
import pandas

if int(pandas.__version__.split('.')[0]) < 1:
    PD_STYLE_PROP = {}
else:
    PD_STYLE_PROP = {'na_rep': "-"}


# FIXME: end of the shame


class ReportMADM(BaseReport):
    _M_OBJ = Mod.MarketAssetsDataBaseModel
    _M_LABEL = 'MADM'
    _IMG_LABELS = ['p_price']
    INPUT_QUESTIONS = (
        ('date', 'Insert date of calculation (default None): ',
         {'idesc': 'datetime', 'optional': True}),
    )

    def _init_input(self) -> dict:
        """ Prepare the input arguments for the model. """
        d = {'uid': self._uid}
        d.update(self._p)
        return d

    def _create_output(self, res):
        """ Create the final output. """
        # Create the image path
        fig_full_name, fig_rel_name = self._get_image_paths(res.uid)

        # Relative path in results object
        res.prices_long = fig_rel_name[0]
        full_name_long = fig_full_name[0]

        # Slow plot
        div_pl = IO.TSPlot()
        div_pl.lplot(0, res.prices)
        div_pl.plot()
        div_pl.save(full_name_long)
        div_pl.clf()

        div_pl.close(True)

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
