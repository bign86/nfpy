#
# Base Reporting
# Base class for reporting
#

from abc import ABCMeta, abstractmethod
from os.path import join, basename, normpath
from typing import Tuple


class BaseReport(metaclass=ABCMeta):
    _M_OBJ = None
    _M_LABEL = ''
    _IMG_LABELS = []
    INPUT_QUESTIONS = (
        # ('parameter', 'question', {'idesc': ?, 'optional': ?, 'default': ?, 'checker': ?})
    )

    def __init__(self, uid: str, p: dict, img_path: str = None):
        # Input
        self._uid = uid
        self._p = p
        self._img_path = img_path

        # Output
        self._res = None

    @property
    def uid(self) -> str:
        return self._uid

    @property
    def result(self):
        if not self._res:
            self._run()
        return self._res

    def _run(self):
        kwargs = self._init_input()
        results = self._M_OBJ(**kwargs).result(**kwargs)
        self._res = self._create_output(results)

    @abstractmethod
    def _init_input(self) -> dict:
        """ Prepare the input arguments for the model. """

    @abstractmethod
    def _create_output(self, *args):
        """ Create the final output. """

    def _get_image_paths(self, text: str) -> Tuple[Tuple, Tuple]:
        img_path = self._img_path

        fig_full_name, fig_rel_name = [], []
        for l in self._IMG_LABELS:
            name = '_'.join([text, self._M_LABEL, l]) + '.png'
            fig_full_name.append(join(img_path, name))
            fig_rel_name.append(join(basename(normpath(img_path)), name))

        return tuple(fig_full_name), tuple(fig_rel_name)
