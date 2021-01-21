#
# Base class for Pages
#

from abc import (ABCMeta, abstractmethod)
import os
from pathlib import Path
from typing import (Dict, Union)

import pandas as pd
import requests

import nfpy.DB as IO
from nfpy.Calendar import now
from nfpy.Configuration import get_conf_glob
from nfpy.DatatypeFactory import get_dt_glob
from nfpy.Tools import (Exceptions as Ex, Utilities as Ut)


class BasePage(metaclass=ABCMeta):
    """ Base metaclass for pages downloading. Every downloadable page should be
        derived from this class defining class attributes and writing the proper
        parsing and saving methods.
    """

    _PARAMS = {}
    _MANDATORY = ()
    _PROVIDER = ''
    _PAGE = ''
    _TABLE = ''
    _COLUMNS = {}
    _BASE_URL = ''
    _ENCODING = ''
    _REQ_METHOD = ''
    _USE_UPSERT = False
    _HEADER = {}
    _Q_MAX_DATE = "select max(date) from {} where ticker = ?"

    def __init__(self, ticker: str):
        self._db = IO.get_db_glob()
        self._qb = IO.get_qb_glob()
        self._dt = get_dt_glob()
        self._ticker = ticker

        self._p = None
        self._robj = None
        self._res = None
        self._jar = None
        self._curr = None
        self._fname = None
        self._is_initialized = False

        self._set_default_params()

    @property
    def ticker(self) -> str:
        if self._ticker is None:
            raise Ex.IsNoneError("The ticker must be given!")
        return self._ticker

    @property
    def params(self) -> Dict[str, Union[str, int]]:
        return self._p

    @params.setter
    def params(self, v: Dict[str, Union[str, int]]) -> None:
        """ Filter out unwanted parameters, update the dictionary, downloaded
            page is deleted to allow for a new download.
        """
        to_delete_ = set(v.keys()) - set(self._p.keys())
        for k in to_delete_:
            v.pop(k, None)
        self._p.update(v)
        self._robj = None

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
        return 'Mozilla/5.0 (X11; Linux x86_64; rv:67.0) Gecko/20100101 Firefox/67.0'

    @property
    def req_method(self) -> str:
        return self._REQ_METHOD

    @property
    def is_downloaded(self) -> bool:
        return False if self._robj is None else True

    @property
    def is_parsed(self) -> bool:
        return False if self._res is None else True

    @property
    def is_inizialized(self) -> bool:
        return self._is_initialized

    @property
    def use_upsert(self) -> bool:
        return self._USE_UPSERT

    def _check_params(self) -> None:
        _l = []
        for p in self._MANDATORY:
            if (p not in self._p) or (self._p[p] is None):
                _l.append(p)

        if _l:
            raise Ex.IsNoneError("The following parameters are required: {}".format(', '.join(_l)))

    def save(self, backup: bool = False, fname: str = None) -> None:
        """ Save the downloaded page in the DB and on a file.

            Input:
                fname [str]: backup file name, overrides default
        """
        if not self.is_downloaded:
            raise RuntimeError("Nothing to save")
        if not self.is_parsed:
            self._parse()
        if backup:
            self._write_to_file(fname)
        self._write_to_db()

    def initialize(self, currency: str = None, fname: Union[str, Path] = None,
                   params: dict = {}) -> None:
        """ Parameters are checked before download, encoding is set, parsed
            object is deleted if present.

            Input:
                currency [str]: currency of the download
                fname [Union[str, Path]]: file name to load
                params [dict]: dictionary of parameters to update

            Errors:
                MissingData: if data are not found in the database
        """
        if self._is_initialized is True:
            return

        self._curr = currency
        if fname is not None:
            self._fname = fname
        else:
            self._local_initializations(params)
        
        self._is_initialized = True

    def fetch(self) -> None:
        """ Either download from internet or from a local file the data.

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

    def _load_file(self) -> None:
        """ Load a file to be parsed. """
        if self._fname is None:
            raise ValueError("File to load not specified!")

        r = Ut.FileObject(self._fname)
        r.encoding = self._ENCODING
        self._robj = r

    def _download(self) -> None:
        """ Fetch from the remote url the page data. The object must be initialized
            first. If not initialized a RuntimeError exception is thrown.

            Errors:
                RuntimeError: uninitialized object
                RequestException: for any error in requests library
                RuntimeWarning: if page downloaded with negative status_code
        """
        if not self._is_initialized:
            raise RuntimeError("The object must be initialized first")

        req = requests.Session()

        if self._jar:
            req.cookies = self._jar

        headers = self._HEADER
        headers['User-Agent'] = self.user_agent

        if self.req_method == 'get':
            r = req.get(self.baseurl, params=self._p, headers=headers)
        elif self.req_method == 'post':
            r = req.post(self.baseurl, data=self._p, headers=headers)
        else:
            raise ValueError('Request method {} not recognized'
                             .format(self.req_method))

        if r.status_code == 200:
            r.encoding = self._ENCODING
            self._jar = r.cookies
            self._robj = r
        else:
            raise RuntimeWarning("Error in downloading the page {}: {} @ {}"
                                 .format(self.__class__.__name__,
                                         r.status_code, r.reason))

    def _write_to_file(self, fname: str = None) -> None:
        """ Write to a text file. """
        if not fname:
            now_ = now(string=True, fmt='%Y%m%d_%H%M')
            t = self._ticker.replace(':', '.')
            fname = self._PROVIDER + '_' + t + '_' + now_

        bak_dir = get_conf_glob().backup_dir
        fd = Path(os.path.join(bak_dir, fname))
        with fd.open(mode='w') as f:
            f.write(self._robj.text)

    def _write_to_db(self) -> None:
        """ Write to the database table. """
        # Get all fields and data
        fields_all = self._res.columns.values.tolist()
        data_all = self._res.values.tolist()

        # We make the use of UPSERT optional field
        if self.use_upsert:
            # Update/Insert new data
            q_ups = self._qb.upsert(self._TABLE, fields=fields_all)
            self._db.executemany(q_ups, data_all, commit=True)
        else:
            # Delete old data
            keys = [k for k in self._qb.get_keys(self._TABLE)]
            data_del = self._res[keys].values.tolist()
            q_del = self._qb.delete(self._TABLE, fields=keys)
            self._db.executemany(q_del, data_del, commit=False)

            # Insert new data
            q_ins = self._qb.merge(self._TABLE, ins_fields=fields_all)
            self._db.executemany(q_ins, data_all, commit=True)

    def printout(self) -> None:
        """ Print out the results of the fetched object. """
        if not self.is_downloaded:
            raise RuntimeError("Nothing to save")
        if not self.is_parsed:
            self._parse()
        with pd.option_context('display.max_rows', None,
                               'display.max_columns', None,
                               'display.width', 10000):
            print(repr(self._res))

    def _fetch_last_data_point(self) -> dict:
        """ Calculates the last available data point in the database for
            incremental downloads.
        """
        q = self._Q_MAX_DATE.format(self._TABLE)
        last_date = self._db.execute(q, (self.ticker,)).fetchone()
        return last_date[0] if last_date[0] else '1990-01-01'

    @abstractmethod
    def _set_default_params(self) -> None:
        """ Set the starting default of the parameters for the page. """

    @property
    @abstractmethod
    def baseurl(self) -> str:
        """ Return the base url for the page. """

    @abstractmethod
    def _local_initializations(self, params: Dict) -> None:
        """ Page-dependent initializations of parameters. """

    @abstractmethod
    def _parse(self) -> None:
        """ Parse the fetched object. """
