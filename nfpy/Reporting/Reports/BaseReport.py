#
# Base Reporting
# Base class for reporting
#

from abc import (ABCMeta, abstractmethod)
from collections import defaultdict
import itertools
from os.path import (join, basename, normpath)
from typing import (Any, Sequence, Type)

from nfpy.Assets import get_af_glob
from nfpy.Calendar import get_calendar_glob


class BaseReport(metaclass=ABCMeta):
    _M_LABEL = ''
    INPUT_QUESTIONS = (
        # ('parameter', 'question', {'idesc': ?, 'optional': ?, 'default': ?, 'checker': ?})
    )

    def __init__(self, uids: Sequence, p: dict = None, img_path: str = None):
        # Input
        self._uids = uids
        self._img_path = img_path

        # Work & Output variables
        self._af = get_af_glob()
        self._cal = get_calendar_glob()
        self._p = p
        self._jinja_filters = {}
        self._res = defaultdict(dict)

    @property
    def uids(self) -> Sequence:
        return self._uids

    @property
    def filters(self) -> dict:
        return self._jinja_filters

    @property
    def result(self):
        if not self._res:
            self._run()
        return self._res

    def _run(self) -> None:
        # Run uids
        for uid in self.uids:
            print(f'>>> {uid}')
            try:
                type_ = self._af.get_type(uid)
                self._res[type_][uid] = self._calculate(
                    uid,
                    self._init_input(self._p, type_)
                )
            except (RuntimeError, KeyError, ValueError) as ex:
                print(str(ex))

    @abstractmethod
    def _init_input(self, p: dict, uid: str) -> dict:
        """ Prepare and validate the the input parameters for the model. This
            includes verifying the parameters are correct for the models in the
            report.
        """

    @abstractmethod
    def _calculate(self, *args) -> Any:
        """ Calculate the required models. """

    def _get_image_paths(self, labels: tuple) -> tuple[tuple, tuple]:
        img_path = self._img_path

        fig_full_name, fig_rel_name = [], []
        for l in itertools.product(*labels):
            name = f'{"_".join(l)}.png'
            fig_full_name.append(join(img_path, name))
            fig_rel_name.append(join(basename(normpath(img_path)), name))

        return tuple(fig_full_name), tuple(fig_rel_name)


TyReport = Type[BaseReport]
