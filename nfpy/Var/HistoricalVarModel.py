#
# Var class
# Class that implements the basic functionalities of historical var models
#

from typing import Union, Iterable
import pandas as pd
import numpy as np

from nfpy.Assets.Portfolio import Portfolio
from nfpy.Handlers.Calendar import get_calendar_glob
from nfpy.Tools.Utilities import AttributizedDict
from nfpy.Var.RandomEngine import RandomEngine
from nfpy.Var.EvolutionModels.BaseVarEvolver import BaseVarEvolver
from nfpy.Var.EvolutionModels.DummyVarEvolver import DummyVarEvolver
from nfpy.Var.EvolutionModels.GBMEvolver import GBMEvolver


# TODO: introduce a memory check on the combination of
#               horizon length * num paths * num risk factors
#       to check we are not overflowing the memory of the system or in any case
#       a reasonable amount of used memory


class VarResult(AttributizedDict):
    """ Object containing the results of the VAR calculation. """

    def __init__(self):
        super().__init__()


class HistoricalVarModel(object):
    _DEFAULT_MODEL_MAP = {'Equity': 'G-BM', 'Indices': 'LN-D', 'Currency': 'G-BM', 'Rate': 'HW-1F'}
    _KNOWN_RF = ['Equity', 'Indices', 'Currency', 'Rate', 'Curve', 'Bond']
    _KNOWN_MODELS = {'Dummy': DummyVarEvolver, 'LN-D': None, 'G-BM': GBMEvolver, 'HW-1F': None}

    def __init__(self, portfolio: Union[Portfolio, Iterable], numpaths: int, horizon: int,
                 observations: int, mapping: dict = None, date: pd.Timestamp = None):
        if mapping is None:
            mapping = {}

        # Inputs
        self._mapping = None
        self._freq = None
        self._horizon = None
        self._input = None
        self._obs = None
        self._t0 = None
        self._n = None

        # Working variables
        self._rf = dict()  # rf name: (rf object)
        self._tree = dict()  # asset uid: (asset object)
        self._num_rf = None

        # Random engine
        self._rnd_engine = RandomEngine()

        # Outputs
        self._res = None

        # perform immediate sanity check
        self._initialize(portfolio, numpaths, horizon, observations, mapping, date)

    @property
    def frequency(self) -> str:
        return self._freq

    @property
    def horizon(self) -> int:
        return self._horizon

    @property
    def t0(self) -> pd.Timestamp:
        return self._t0

    @property
    def observations(self) -> int:
        return self._obs

    @property
    def numpath(self) -> int:
        return self._n

    @property
    def mapping(self) -> str:
        return '\n'.join(map(str, ['{}: {}'.format(k, v) for k, v in self._mapping])) + '\n'

    def __repr__(self) -> str:
        # TODO
        return ''

    def _initialize(self, portfolio: Union[Portfolio, Iterable], numpaths: int, horizon: int,
                    observations: int, mapping: dict, date: pd.Timestamp):
        # setting up calendar
        # TODO: sanity checks on date (type and value)
        cal = get_calendar_glob()
        self._t0 = cal.t0 if not date else date
        self._freq = cal.frequency

        # lengths
        # TODO: sanity checks on the inputs
        self._horizon = int(horizon)
        self._obs = int(observations)
        self._n = int(numpaths)

        # asset class <-> model mapping
        for k in mapping.keys():
            if k not in self._KNOWN_RF:
                raise ValueError('Asset class {} not recognized'.format(k))
        for v in mapping.values():
            if v not in self._KNOWN_MODELS:
                raise ValueError('Model {} not recognized'.format(v))

        # update mapping
        self._mapping = self._DEFAULT_MODEL_MAP
        self._mapping.update(mapping)

        if isinstance(portfolio, Portfolio):
            # self._is_portfolio_obj = True
            self._input = list(portfolio.constituents.values())
        elif isinstance(portfolio, Iterable):
            self._input = set(portfolio)
        else:
            raise TypeError(
                'The given portfolio type ({}) is not supported'.format(type(portfolio)))

    def get_rf(self, l) -> BaseVarEvolver:
        return self._rf[l]

    def get_rnd_draws(self, n: int, rf_uid: str) -> np.array:
        return self._rnd_engine.get(n, rf_uid)

    def calculate(self):
        # fase 0: data cleaning
        self._data_clean()

        # fase 1: assign calculator
        self._build_tree()

        # fase 2: calculate sigma
        self._initialize_random_engine()

        # fase 3: perform simulation
        self._simulate()

        # fase 4: aggregate on the tree
        self._aggregate()

    def _data_clean(self):
        pass

    def _build_tree(self):
        """ create the tree portfolio -> (assets) -> (rf)
            1. map assets <-> calculator
            2. call asset.calculator.build_tree() to yield other rf
            3. merge together all pieces in a unique tree, fill
               also the catalogue of assets, and the one of risk
               factors
        """
        for a in self._input:
            cname = self._mapping[a.type]
            calc = self._KNOWN_MODELS[cname](self)
            tree, rf = calc.build_tree(a)
            self._tree[a.uid] = tree
            self._rf.update(rf)

        # all risk factors have been found, count the size
        self._num_rf = len(self._rf)

    def _initialize_random_engine(self):
        """ calculates the sigma for the risk factors
        """
        self._rnd_engine.initialize_generator(self._rf, self._t0, self._obs,
                                              self._num_rf, self._horizon, self._n)

    def _simulate(self):
        """ for each rf in the dict perform the calculation, to be
            defined how to handle dependencies. The simulation step
            should use the calculator attached to the rf, all having
            a common structure that this function can leverage.
            0. alea jacta est (?)
            1. call rf.calculator.simulate() to yield var for rf
            2. dependencies are called by the calculator itself
            3. do for all the rf
        """
        # size of the draws matrix
        # draws_size = self._num_rf, self._horizon
        self._save_path = np.ones((self._n, self._horizon+1))

        for n in range(self._n):
            # FIXME: can I just run on the values()?
            for rf in self._rf.keys():
                self._rf[rf].simulate(n)

            # all path have been calculated, clean up
            if n % 1000 == 0:
                print('loop {}'.format(n))

    def _aggregate(self):
        """ following the tree of rf aggregate the results for risk
            factors and the final portfolio.
            1. take the var for each asset (not rf) and aggregate
        """
        from nfpy.Handlers.Plotting import PlotTS
        import matplotlib.pylab as plt
        series = []

        pl = PlotTS()
        for k, v in self._rf.items():
            res = np.exp(v._res) - 1.
            x = pd.Series(data=res, name=k)
            pl.add(x)
            series.append(x)
            srt = sorted(res)
            var99 = round(self._n * .01)
            var95 = round(self._n * .05)
            print('{} =>> {:.5f} =>> {:.5f} =>> {:.5f}'
                  .format(k, res.mean(), srt[var95], srt[var99]))
        pl.plot()
        pl.show()

        print('')

        for s in series:
            s.hist(bins=70)
        plt.plot()
        plt.show()

        print('')

    def results(self):
        """ returns the results
            1. portfolio var
            2. portfolio values distribution
            3. single assets var
            4. single values distribution
            5. single rf var
            6. single rf values distribution
        """
        pass
