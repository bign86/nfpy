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
from nfpy.Tools import (get_dt_glob, Exceptions as Ex, Utilities as Ut)


class BasePage(metaclass=ABCMeta):
    """ Base metaclass for pages downloading. Every downloadable page should be
        derived from this class defining class attributes and writing the proper
        parsing and saving methods.
    """

    _PARAMS = {}
    _MANDATORY = []
    _PROVIDER = ''
    _PAGE = ''
    _TABLE = ''
    _COLUMNS = {}
    _BASE_URL = ''
    _ENCODING = ''
    _REQ_METHOD = ''
    _USE_UPSERT = False
    _HEADER = {}

    def __init__(self, p: Dict = None):
        self._db = IO.get_db_glob()
        self._qb = IO.get_qb_glob()
        self._dt = get_dt_glob()
        self._p = self._PARAMS
        self._ticker = None
        self._robj = None
        self._res = None
        self._jar = None
        self._curr = None
        self._fname = None
        self._is_initialized = False

        if p:
            self.params = p

    @property
    def ticker(self) -> str:
        if self._ticker is None:
            raise Ex.IsNoneError("The ticker must be given!")
        return self._ticker

    @property
    def params(self) -> Dict[str, Union[str, int]]:
        return self._p

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

    @params.setter
    def params(self, v: Dict[str, Union[str, int]]):
        """ Filter out unwanted parameters, update the dictionary, downloaded
            page is deleted to allow for a new download.
        """
        to_delete_ = set(v.keys()) - set(self._p.keys())
        for k in to_delete_:
            v.pop(k, None)
        self._p.update(v)
        self._robj = None

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

    def _check_params(self):
        _l = []
        for p in self._MANDATORY:
            if (p not in self._p) or (self._p[p] is None):
                _l.append(p)

        if _l:
            raise Ex.IsNoneError("The following parameters are required: {}".format(', '.join(_l)))

    def save(self, backup: bool = False, fname: str = None):
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

    def initialize(self, asset: dict, fname: Union[str, Path] = None,
                   params: dict = None):
        """ Parameters are checked before download, encoding is set, parsed
            object is deleted if present.

            Input:
                asset [dict]: asset data
                fname [Union[str, Path]]: file name to load
                params [dict]: dictionary of parameters to update

            Errors:
                MissingData: if data are not found in the database
        """
        if self._is_initialized is True:
            return

        if params:
            self.params = params
        self._ticker = asset['ticker']
        self._curr = asset['currency']
        if fname is not None:
            self._fname = fname
        else:
            self._local_initializations()
        self._is_initialized = True

    def fetch(self):
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

    def _load_file(self):
        """ Load a file to be parsed. """
        if self._fname is None:
            raise ValueError("File to load not specified!")

        r = Ut.FileObject(self._fname)
        r.encoding = self._ENCODING
        self._robj = r

    def _download(self):
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

        print("{}\n{}".format(r.request.url, r.status_code))
        if r.status_code == 200:
            r.encoding = self._ENCODING
            self._jar = r.cookies
            self._robj = r
        else:
            raise RuntimeWarning("Error {} in downloading the page {} because of\n{}"
                                 .format(r.status_code, self.__class__.__name__,
                                         r.reason))

    def _write_to_file(self, fname: str = None):
        """ Write to a text file. """
        if not fname:
            now_ = now(string=True, fmt='%Y%m%d_%H%M')
            t = self._ticker.replace(':', '.')
            fname = self._PROVIDER + '_' + t + '_' + now_

        bak_dir = get_conf_glob().backup_dir
        fd = Path(os.path.join(bak_dir, fname))
        with fd.open(mode='w') as f:
            f.write(self._robj.text)

    def _write_to_db(self):
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

    def printout(self):
        """ Print out the results of the fetched object. """
        if not self.is_downloaded:
            raise RuntimeError("Nothing to save")
        if not self.is_parsed:
            self._parse()
        with pd.option_context('display.max_rows', None,
                               'display.max_columns', None,
                               'display.width', 10000):
            print(repr(self._res))

    @property
    @abstractmethod
    def baseurl(self) -> str:
        """ Return the base url for the page. """

    @abstractmethod
    def _local_initializations(self):
        """ Local initializations for the single page. """

    @abstractmethod
    def _parse(self):
        """ Parse the fetched object. """
