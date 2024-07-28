#
# Report Risk Premium
# Report class for risk premia across equities
#

from collections import defaultdict
from typing import (Any, Optional)

import nfpy.IO.Utilities
from nfpy.Assets import TyAsset
import nfpy.Calendar as Cal
from nfpy.Financial import CAPM
from nfpy.Tools import (
    Exceptions as Ex,
    Utilities as Ut
)

from .BaseReport import (BaseReport, ReportData)


class ReportRiskPremium(BaseReport):

    def __init__(self, data: ReportData, path: Optional[str] = None):
        super().__init__(data, path)
        self._frequency = Cal.Frequency[self._p['frequency']]

    def _one_off_calculations(self) -> None:
        """ Perform all non-uid dependent calculations for efficiency. """
        pass

    def _calculate(self) -> Any:
        """ Calculate the required models.
            MUST ensure that the model parameters passed in <args> are not
            modified so that the database parameters in self._p are not
            changed from one asset to the next.
        """
        outputs = defaultdict(list)
        for uid in self.uids:
            print(f'  > {uid}')
            try:
                asset = self._af.get(uid)
                if asset.type != 'Equity':
                    raise Ex.AssetTypeError(f'{uid} is not an equity')

                self._calc_rp(asset, outputs)
                outputs["indices"] = list(set(outputs["indices"]))

            except (RuntimeError, ValueError, Ex.AssetTypeError) as ex:
                nfpy.IO.Utilities.print_exc(ex)

        return outputs

    def _calc_rp(self, asset: TyAsset, outputs: dict) -> None:
        res = Ut.AttributizedDict()

        # General infos
        res.info = {
            k: getattr(asset, k)
            for k in ('uid', 'ticker', 'isin', 'country', 'currency', 'index')
        }

        res.results = CAPM(asset, self._frequency, self._p['periods']) \
            .results()

        outputs['equities'].append(res)
        outputs['indices'].append(asset.index)
