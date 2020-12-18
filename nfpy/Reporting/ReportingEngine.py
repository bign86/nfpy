#
# Reporting Engine
# Main engine for reporting
#

import json
import os
from collections import defaultdict
from os.path import join
from jinja2 import FileSystemLoader, Environment

from nfpy import NFPY_ROOT_DIR
from nfpy.Assets import get_af_glob
from nfpy.DB import (get_db_glob, get_qb_glob)
from nfpy.Handlers.Calendar import get_calendar_glob
from nfpy.Handlers.Configuration import get_conf_glob
from nfpy.Reporting.ReportMPDM import ReportMPDM
from nfpy.Reporting.ReportDCF import ReportDCF
from nfpy.Reporting.ReportDDM import ReportDDM
from nfpy.Reporting.ReportMADM import ReportMADM
from nfpy.Reporting.ReportMBDM import ReportMBDM
from nfpy.Reporting.ReportMEDM import ReportMEDM
from nfpy.Reporting.ReportPtfOptimization import ReportPtfOptimization
from nfpy.Tools.Exceptions import MissingData
from nfpy.Tools.Singleton import Singleton


class ReportingEngine(metaclass=Singleton):
    """ Main class for reporting. """

    _TABLE = 'Reports'
    _DT_FMT = '%Y%m%d'
    _IMG_DIR = 'img'
    _REPORTS = {'DDM': ReportDDM, 'DCF': ReportDCF, 'MADM': ReportMADM,
                'MEDM': ReportMEDM, 'MBDM': ReportMBDM, 'MPDM': ReportMPDM,
                'PtfOptimization': ReportPtfOptimization}
    _TMPL_PATH = join(NFPY_ROOT_DIR, 'Reporting/Templates')
    _REP_EXT = '.html'

    def __init__(self):
        self._af = get_af_glob()
        self._qb = get_qb_glob()
        self._db = get_db_glob()
        self._cal = get_calendar_glob()
        self._conf = get_conf_glob()

        # Work variables
        self._p = None
        self._curr_report_dir = None
        self._curr_img_dir = None
        self._rep_path = None

        # Output
        self._res = None
        self._assets = None

        self._initialize()

    def _initialize(self):
        rep_path = self._conf.report_path
        new_folder = 'Report_' + self._cal.end.strftime(self._DT_FMT)
        self._curr_report_dir = join(rep_path, new_folder)
        self._curr_img_dir = join(rep_path, new_folder, self._IMG_DIR)

    def get_report_obj(self, r: str):
        """ Return the report object given the report name. """
        return self._REPORTS[r]

    @property
    def results(self) -> dict:
        return self._res

    def add(self, uid: str, model: str, params: dict, active: bool = False):
        """ Add an item in the reporting table. """
        cols = ('uid', 'model', 'parameters', 'active')
        jp = json.dumps(params)
        p = (uid, model, jp, active)
        q = self._qb.insert(self._TABLE, cols)
        self._db.execute(q, p, commit=True)

    def remove(self, uid: str = None, model: str = None):
        """ Remove an item in the reporting table. """
        q = self._qb.delete(self._TABLE, ('uid', 'model'))
        self._db.executemany(q, (uid, model), commit=True)

    def list(self) -> list:
        """ List reports matching the current setting. """
        if not self._p:
            k = ['active']
            p = [True]
        else:
            k = ['uid', 'model']
            p = [self._p[l] for l in k]
            if not self._p['override_auto']:
                k.append('active')
                p.append(True)
        q = self._qb.select(self._TABLE, keys=k)
        return self._db.execute(q, p).fetchall()

    def set_reports(self, uid: str = None, model: str = None,
                    override_auto: bool = False):
        """ Set the parameters to filter reports.

            Input:
                uid [Iterable]: list of uids to report for
                model [Iterable]: list of modes to report for
                override_auto [bool]: override the auto flag
        """
        self._p = locals()

    def create_new_directory(self):
        """ Create a new directory for the current report. """
        new_path = self._curr_img_dir

        # If directory exists exit
        if os.path.exists(new_path):
            return

        try:
            os.makedirs(new_path)
        except OSError as ex:
            print('Creation of the directory {} failed'.format(new_path))
            raise ex
        else:
            print('Successfully created the directory {}'.format(new_path))

    def _calculate(self, tbg: list):
        """ Calculates results by calling all models. """
        cid = self._curr_img_dir

        ret_dict = defaultdict(dict)
        asset_dict = defaultdict(list)
        for item in tbg:
            u, m, p, _ = item
            print(u, m)
            # print(p)
            pd = json.loads(p)
            report = self._REPORTS[m]

            try:
                r = report(u, pd, img_path=cid).result
            except (ValueError, MissingData, KeyError) as ex:
                print(str(ex))
                continue
            else:
                ret_dict[u][m] = r
                a_type = self._af.get(u).type
                asset_dict[a_type].append(u)

        for k, v in asset_dict.items():
            asset_dict[k] = sorted(set(v))

        self._res = ret_dict
        self._assets = asset_dict

    def _add_asset_info(self):
        """ Add asset infos to the results. """
        for a_type, assets in self._assets.items():
            for uid in assets:
                self._res[uid]['info'] = self._gen_info(a_type, uid)

    def _gen_info(self, a_type: str, uid: str) -> dict:
        asset = self._af.get(uid)
        f = ['uid', 'description']
        if a_type == 'Bond':
            f = f + ['isin', 'issuer', 'currency', 'asset_class',
                     'inception_date', 'maturity', 'coupon', 'c_per_year']
        elif a_type == 'Company':
            f = f + ['name', 'sector', 'industry', 'equity', 'currency', 'country']
        elif a_type == 'Currency':
            f = f + ['base_country', 'tgt_country', 'base_fx', 'tgt_fx']
        elif a_type == 'Equity':
            f = f + ['isin', 'country', 'currency', 'company_uid', 'index']
        elif a_type == 'Indices':
            f = f + ['area', 'currency', 'asset_class']
        elif a_type == 'Portfolio':
            f = f + ['name', 'currency', 'inception_date', 'benchmark',
                     'num_constituents']
        else:
            pass
        return {k: getattr(asset, k) for k in f}

    def _generate(self, name: str, rep_type: str):
        """ Generates the actual report. """
        title = "Report - {}".format(self._cal.t0.strftime('%Y-%m-%d'))
        report = '' .join([rep_type, self._REP_EXT])
        name = '' .join([name, self._REP_EXT])

        j_loader = FileSystemLoader(self._TMPL_PATH)
        j_env = Environment(loader=j_loader)
        main = j_env.get_template(report)
        out = main.render(title=title, all_res=self._res, assets=self._assets)

        out_file = os.path.join(self._curr_report_dir, name)
        outf = open(out_file, 'w')
        outf.write(out)
        outf.close()

    def run(self):
        """ Run the report engine. """
        # Reports to be generated
        tbg = self.list()
        if not tbg:
            print("No reports to generate.")
            return

        # Create a new report directory
        self.create_new_directory()

        # Calculate model results
        self._calculate(tbg)
        self._add_asset_info()

        # Generate reports
        if not self._p:
            name, rep_type = 'main', 'main'
        else:
            name = '_'.join([self._p['uid'], self._p['model']])
            rep_type = self._p['model']
        self._generate(name, rep_type)


def get_re_glob() -> ReportingEngine:
    return ReportingEngine()
