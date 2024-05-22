#
# Base class for Pages
#

from abc import (ABCMeta, abstractmethod)
from collections import namedtuple
import os
import pandas as pd
from pathlib import Path
import requests
from requests import adapters
import ssl
from typing import (Sequence, TypeVar)
from urllib3 import poolmanager

from nfpy.Calendar import now
import nfpy.DB as DB
from nfpy.DatatypeFactory import get_dt_glob
from nfpy.Tools import (Exceptions as Ex, get_conf_glob, Utilities as Ut)


# Tuple to define parameters
DwnParameter = namedtuple('DwnParameter', ['code', 'mandatory', 'default'])


class TLSAdapter(adapters.HTTPAdapter):

    def init_poolmanager(self, connections, maxsize, block=False):
        """Create and initialize the urllib3 PoolManager."""
        # ctx = ssl.create_default_context()
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.options |= 0x4
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        self.poolmanager = poolmanager.PoolManager(
                num_pools=connections,
                maxsize=maxsize,
                block=block,
                ssl_version=ssl.PROTOCOL_TLS,
                ssl_context=ctx
        )


# Base class for every download
class BasePage(metaclass=ABCMeta):
    """ Base metaclass for pages downloading. Every downloadable page should be
        derived from this class defining class attributes and writing the proper
        parsing and saving methods.
    """

    _PARAMS = {}
    _PROVIDER = ''
    _PAGE = ''
    _TABLE = ''
    _COLUMNS = {}
    _BASE_URL = ''
    _ENCODING = ''
    _REQ_METHOD = ''
    _USE_UPSERT = False
    _Q_MAX_DATE = ''
    _Q_SELECT = ''
    _DATE0 = '1950-01-01'
    _HEADER = {
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }

    def __init__(self, ticker: str, currency: str):
        self._db = DB.get_db_glob()
        self._qb = DB.get_qb_glob()
        self._dt = get_dt_glob()
        self._ticker = ticker
        self._currency = currency

        self._p = []
        self._robj = []
        self._res = None
        self._jar = None
        self._fname = None

        self._is_initialized = False
        self._is_saved = False

        self._set_default_params()

    @property
    def ticker(self) -> str:
        if self._ticker is None:
            raise Ex.IsNoneError("BaseDownloader(): The ticker must be given!")
        return self._ticker

    @property
    def provider(self) -> str:
        return self._PROVIDER

    @property
    def page(self) -> str:
        return self._PAGE

    @property
    def table(self) -> str:
        return self._TABLE

    @property
    def user_agent(self) -> str:
        # return 'Mozilla/5.0 (X11; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0'
        # return 'Mozilla/5.0 (X11; Linux x86_64; rv:67.0) Gecko/20100101 Firefox/67.0'
        # return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15'
        return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Safari/605.1.15'

    @property
    def req_method(self) -> str:
        return self._REQ_METHOD

    @property
    def is_downloaded(self) -> bool:
        return False if len(self._robj) == 0 else True

    @property
    def is_parsed(self) -> bool:
        return False if self._res is None else True

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    @property
    def is_saved(self) -> bool:
        return self._is_saved

    @property
    def use_upsert(self) -> bool:
        return self._USE_UPSERT

    @property
    def select(self) -> str:
        return self._Q_SELECT

    @property
    def data(self) -> pd.DataFrame:
        if not self.is_downloaded:
            msg = f"{' | '.join((self.provider, self.page, self.ticker))} - Nothing to save"
            raise RuntimeError(msg)
        if not self.is_parsed:
            self._parse()
        return self._res

    def _check_params(self) -> None:
        _missing = set()
        for p in self._PARAMS.values():
            if p.mandatory:
                code = p.code
                for param_set in self._p:
                    if (code not in param_set) or (param_set[code] is None):
                        _missing.add(code)

        if _missing:
            msg = f"BaseDownloader(): The following required parameters are missing: {', '.join(_missing)}"
            raise Ex.IsNoneError(msg)

    def save(self) -> None:
        """ Save the downloaded page in the DB. """
        if not self.is_parsed:
            self._parse()
        self._write_to_db()

    def dump(self, fname: str | None = None) -> None:
        """ Dump the downloaded page on a file.

            Input:
                fname [str | None]: backup file name, overrides default
        """
        if not self.is_parsed:
            self._parse()
        self._write_to_file(fname)

    def initialize(
        self,
        fname: str | Path | None = None,
        params: dict | None = None
    ):
        """ Parameters are checked before download, encoding is set, parsed
            object is deleted if present.

            Input:
                fname [str | Path | None]: file name to load
                params [dict | None]: dictionary of parameters to update.
                    Supported:
                        'currency': currency of the download (mandatory)
                        'start': starting date
                        'end': ending date

            Output:
                self: returns self on completion

            Errors:
                MissingData: if data are not found in the database
        """
        if self._is_initialized is True:
            return self

        if fname is not None:
            self._fname = fname
        else:
            p = {'currency': self._currency}
            p.update(params)
            self._local_initializations(p)

        self._is_initialized = True
        return self

    def fetch(self):
        """ Either download from internet or from a local file the data.

            Output:
                self: returns self on completion

            Errors:
                IsNoneError: if one mandatory parameter is absent
                RuntimeError: uninitialized object
                RequestException: for any error in requests library
                RuntimeWarning: if page downloaded with negative status_code
        """
        if self._fname is not None:
            self._load_file()
        else:
            self._check_params()
            self._download()
        self._res = None
        return self

    def _load_file(self) -> None:
        """ Load a file to be parsed. """
        if self._fname is None:
            raise ValueError("BaseDownloader(): File to load not specified!")

        r = Ut.FileObject(self._fname)
        r.encoding = self._ENCODING
        self._robj = [r]

    def _download(self) -> None:
        """ Fetch from the remote url the page data. The object must be initialized
            first. If not initialized a RuntimeError exception is thrown.

            Errors:
                RuntimeError: uninitialized object
                RequestException: for any error in requests library
                RuntimeWarning: if page downloaded with negative status_code
        """
        if not self._is_initialized:
            raise RuntimeError("BaseDownloader(): The object must be initialized first")

        session = requests.Session()
        self._mount(session)

        if self._jar:
            session.cookies = self._jar

        headers = self._HEADER
        headers['User-Agent'] = self.user_agent

        # Run through the list of parameters for each call
        for param_set in self._p:

            # Make the call
            if self.req_method == 'get':
                r = session.get(self.baseurl, params=param_set, headers=headers, timeout=10)
            elif self.req_method == 'post':
                r = session.post(self.baseurl, data=param_set, headers=headers)
            else:
                raise ValueError(f'BaseDownloader(): Request method {self.req_method} not recognized')

            if r.status_code == 200:
                r.encoding = self._ENCODING
                self._jar = r.cookies
                self._robj.append(r)
            else:
                msg = f"BaseDownloader(): Error in downloading {self.__class__.__name__}|{self.ticker}: " \
                      f"[{r.status_code}] {r.reason}"
                raise requests.HTTPError(msg)

    def _mount(self, session) -> None:
        """ To apply a custom SSL context to the call. """
        pass

    def _write_to_file(self, fname: str | None = None) -> None:
        """ Write to a text file. """
        if not fname:
            now_ = now(mode='str', fmt='%Y%m%d_%H%M')
            t = self._ticker.replace(':', '.')
            fname = f"{self._PROVIDER}_{self.page}_{t}_{now_}"

        bak_dir = get_conf_glob().backup_folder
        fd = Path(os.path.join(bak_dir, fname))
        with fd.open(mode='w') as f:
            for result in self._robj:
                f.write(result.text)

    def _write_to_db(self) -> None:
        """ Write to the database table. """
        # Get all fields and data
        fields_all = self._res.columns.values.tolist()
        data_all = self._res.values.tolist()

        # We make the use of UPSERT optional field
        if self.use_upsert:
            # Update/Insert new data
            self._db.executemany(
                self._qb.upsert(
                    self._TABLE,
                    fields=fields_all
                ),
                data_all,
                commit=True
            )
        else:
            # Delete old data
            keys = [k for k in self._qb.get_keys(self._TABLE)]
            self._db.executemany(
                self._qb.delete(
                    self._TABLE,
                    fields=keys
                ),
                self._res[keys].values.tolist(),
                commit=False
            )

            # Insert new data
            self._db.executemany(
                self._qb.merge(
                    self._TABLE,
                    ins_fields=fields_all
                ),
                data_all,
                commit=True
            )

        self._is_saved = True

    def printout(self) -> None:
        """ Print out the results of the fetched object. """
        with pd.option_context('display.max_rows', None,
                               'display.max_columns', None,
                               'display.width', 10000):
            print(repr(self.data))

    # FIXME: shouldn't this one return a parsed date (datetime or Timestamp)?
    def _fetch_last_data_point(self, data: Sequence) -> str:
        """ Calculates the last available data point in the database for
            incremental downloads.
        """
        date = self._DATE0
        last_date = self._db.execute(
            self._Q_MAX_DATE,
            data
        ).fetchone()
        if last_date:
            if last_date[0] is not None:
                date = last_date[0]
        return date

    @abstractmethod
    def _set_default_params(self) -> None:
        """ Set the starting default of the parameters for the page. """

    @property
    @abstractmethod
    def baseurl(self) -> str:
        """ Return the base url for the page. """

    @abstractmethod
    def _local_initializations(self, ext_p: dict) -> None:
        """ Page-dependent initializations of parameters. """

    @abstractmethod
    def _parse(self) -> None:
        """ Parse the fetched object. """


# Download page type for export
TyDownloadPage = TypeVar('TyDownloadPage', bound=BasePage)
