#
# Base Reporting
# Base class for reporting
#

from abc import (ABCMeta, abstractmethod)
from collections import namedtuple
import itertools
import os.path
from typing import (Any, Optional, Sequence, Type)

import nfpy.Assets as Ast
import nfpy.Calendar as Cal
from nfpy.Tools import Utilities as Ut

ReportData = namedtuple('ReportData', (
    'id', 'title', 'description', 'report', 'template',
    'uids', 'calendar_setting', 'parameters', 'active'
))


class ReportResult(Ut.AttributizedDict):
    """ Main report results object. """


class BaseReport(metaclass=ABCMeta):
    _DIR_IMG = 'img'

    def __init__(self, data: ReportData, path: Optional[str] = None):
        # Factories
        self._af = Ast.get_af_glob()
        self._cal = Cal.get_calendar_glob()
        self._fx = Ast.get_fx_glob()

        # Inputs
        self._id = data.id
        self._uids = data.uids
        self._p = data.parameters

        # Paths
        self._base_path = path
        self._report_path = None
        self._img_path = None
        self._img_rel_path = None

        # Work & Output variables
        self._is_calculated = False
        self._res = ReportResult()
        self._res.id = data.id
        self._res.template = data.template
        self._res.title = f"{data.title} - {Cal.today(mode='str')}"

    @property
    def uids(self) -> Sequence[str]:
        return self._uids

    @property
    def result(self) -> ReportResult:
        if not self._is_calculated:
            self._run()
        return self._res

    def _create_new_directory(self) -> None:
        """ Create a new directory for the current report. """
        self._img_rel_path = os.path.join(
            self._id,
            self._DIR_IMG
        )
        self._report_path = os.path.join(
            self._base_path,
            self._id
        )
        img_path = os.path.join(
            self._base_path,
            self._img_rel_path
        )
        self._img_path = img_path

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

        # Run
        self._res.output = self._calculate()
        self._is_calculated = True

    @abstractmethod
    def _one_off_calculations(self) -> None:
        """ Perform all non-uid dependent calculations for efficiency. """

    @abstractmethod
    def _calculate(self) -> Any:
        """ Calculate the required models.
            MUST ensure that the model parameters passed in <args> are not
            modified so that the database parameters in self._p are not
            changed from one asset to the next.
        """

    def _get_image_paths(self, labels: Sequence[Sequence]) \
            -> tuple[tuple, tuple]:
        fig_full_name, fig_rel_name = [], []
        for label in itertools.product(*labels):
            name = f'{"_".join(label)}.png'
            fig_full_name.append(os.path.join(self._img_path, name))
            fig_rel_name.append(os.path.join(self._img_rel_path, name))

        return tuple(fig_full_name), tuple(fig_rel_name)


TyReport = Type[BaseReport]
