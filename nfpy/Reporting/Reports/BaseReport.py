#
# Base Reporting
# Base class for reporting
#

from abc import (ABCMeta, abstractmethod)
from collections import defaultdict
import itertools
import os.path
from typing import (Any, Type)

from nfpy.Assets import get_af_glob
from nfpy.Calendar import get_calendar_glob
from nfpy.Tools import Utilities as Ut


class ReportResult(Ut.AttributizedDict):
    """ Main report results object. """


class BaseReport(metaclass=ABCMeta):
    _M_LABEL = ''
    _DIR_IMG = 'img'
    DEFAULT_P = {}

    def __init__(self, name: str, template: str, uids: [str],
                 p: dict = None, path: str = None):
        # Inputs
        self._name = name
        self._uids = uids
        self._p = p

        # Paths
        self._base_path = path
        self._report_path = None
        self._img_path = None
        self._img_rel_path = None

        # Work & Output variables
        self._af = get_af_glob()
        self._cal = get_calendar_glob()
        self._is_calculated = False
        # self._jinja_filters = {}

        self._res = ReportResult()
        self._res.name = name
        self._res.template = template
        self._res.title = f"Report - {self._cal.end.strftime('%Y-%m-%d')}"

    @property
    def uids(self) -> [str]:
        return self._uids

    # @property
    # def filters(self) -> dict:
    #     return self._jinja_filters

    @property
    def result(self):
        if not self._is_calculated:
            self._run()
        return self._res

    def _create_new_directory(self) -> None:
        """ Create a new directory for the current report. """
        img_rel_path = os.path.join(
            self._name,
            self._DIR_IMG
        )
        rep_path = os.path.join(
            self._base_path,
            self._name
        )
        img_path = os.path.join(
            self._base_path,
            img_rel_path
        )
        self._report_path = rep_path
        self._img_path = img_path
        self._img_rel_path = img_rel_path

        # If directory exists exit
        if os.path.exists(img_path):
            return

        try:
            os.makedirs(img_path)
        except OSError as ex:
            print(f'Creation of the directory {img_path} failed')
            raise ex
        else:
            print(f'Successfully created the directory {img_path}')

    def _run(self) -> None:
        # Create the report folder
        self._create_new_directory()

        # Run uids
        outputs = defaultdict(dict)
        for uid in self.uids:
            print(f'  > {uid}')
            try:
                type_ = self._af.get_type(uid)
                outputs[type_][uid] = self._calculate(
                    uid,
                    self._init_input(type_)
                )
            except (RuntimeError, KeyError, ValueError) as ex:
                Ut.print_exc(ex)
        self._res.output = outputs
        self._is_calculated = True

    @abstractmethod
    def _init_input(self, uid: str) -> dict:
        """ Prepare and validate the the input parameters for the model. This
            includes verifying the parameters are correct for the models in the
            report. Takes the default parameters if any, applies the values from
            the database and the asset-specific overlays if any.
            The function must ensure the parameters from the database stored in
            the self._p symbol are NOT altered for later usage by making copies
            if required.
        """

    @abstractmethod
    def _calculate(self, *args) -> Any:
        """ Calculate the required models.
            MUST ensure that the model parameters passed in <args> are not
            modified so that the database parameters in self._p are not
            changed from one asset to the next.
        """

    def _get_image_paths(self, labels: tuple) -> tuple[tuple, tuple]:
        fig_full_name, fig_rel_name = [], []
        for l in itertools.product(*labels):
            name = f'{"_".join(l)}.png'
            fig_full_name.append(os.path.join(self._img_path, name))
            fig_rel_name.append(os.path.join(self._img_rel_path, name))

        return tuple(fig_full_name), tuple(fig_rel_name)


TyReport = Type[BaseReport]
