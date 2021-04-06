#
# Sizer
# Standard sizers
#


from .BaseSizer import BaseSizer


class ConstantSizer(BaseSizer):
    """ Sizer that returns a constant value. """

    def __init__(self, s: float):
        self._size = max(1., min(.0, s))

    def s(self) -> float:
        return self._size
