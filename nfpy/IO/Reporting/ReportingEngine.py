#
# Reporting Engine
# Main engine for reporting
#

from collections import defaultdict
from jinja2 import FileSystemLoader, Environment
import json
import os
from os.path import join
import shutil

from nfpy import NFPY_ROOT_DIR
from nfpy.Assets import get_af_glob
from nfpy.Calendar import get_calendar_glob
from nfpy.Configuration import get_conf_glob
import nfpy.DB as DB
from nfpy.Tools import (Singleton, Exceptions as Ex)

from .Reports import *


class ReportingEngine(metaclass=Singleton):
    """ Main class for reporting. """

    _TBL_REPORTS = 'Reports'
    _TBL_ITEMS = 'ReportItems'
    _DT_FMT = '%Y%m%d'
    _IMG_DIR = 'img'
    _MODEL_PER_ASSET_CL = {
        'Bond': ('MBDM', 'TRD'),
        'Company': ('DCF', 'DDM'),
        'Equity': ('MEDM', 'TRD'),
        'Indices': ('MADM', 'TRD'),
        'Portfolio': ('MPDM', 'PtfOptimization'),
        'Rate': ('MADM', 'TRD'),
    }
    _REPORTS = {
        'DDM': ReportDDM, 'DCF': ReportDCF, 'MADM': ReportMADM,
        'MEDM': ReportMEDM, 'MBDM': ReportMBDM, 'MPDM': ReportMPDM,
        'PtfOptimization': ReportPtfOptimization, 'TRD': ReportTrading,
    }
    _TMPL_PATH = join(NFPY_ROOT_DIR, 'IO/Reporting/Templates')
    _REP_EXT = '.html'

    def __init__(self):
        self._af = get_af_glob()
        self._qb = DB.get_qb_glob()
        self._db = DB.get_db_glob()
        self._cal = get_calendar_glob()
        self._conf = get_conf_glob()

        # Work variables
        self._p = {}
        self._curr_report_dir = ''
        self._curr_img_dir = ''
        self._rep_path = ''

        self._initialize()

    def _initialize(self):
        rep_path = self._conf.report_path
        new_folder = 'Report_' + self._cal.end.strftime(self._DT_FMT)
        self._curr_report_dir = join(rep_path, new_folder)
        self._curr_img_dir = join(rep_path, new_folder, self._IMG_DIR)

    def get_report_obj(self, r: str):
        """ Return the report object given the report name. """
        return self._REPORTS[r]

    def get_models_per_asset_type(self, m: str) -> tuple:
        """ Return the models available for the asset class in input. """
        return self._MODEL_PER_ASSET_CL[m]

    def add(self, what: str, **kwargs):
        """ Add an item in the report items table. """
        if what == 'report':
            table = self._TBL_REPORTS
        elif what == 'item':
            table = self._TBL_ITEMS
        else:
            raise ValueError('Mode {} not recognized!'.format(what))

        cols, p = [], []
        for c in self._qb.get_fields(table):
            cols.append(c)
            try:
                if c == 'parameters':
                    p.append(json.dumps(kwargs[c]))
                else:
                    p.append(kwargs[c])
            except KeyError:
                raise KeyError('Missing specification of {}'.format(c))

        q = self._qb.insert(table, cols)
        self._db.execute(q, p, commit=True)

    def remove(self, what: str, **kwargs):
        """ Remove an item in the report items table. """
        if what == 'report':
            table = self._TBL_REPORTS
        elif what == 'item':
            table = self._TBL_ITEMS
        else:
            raise ValueError('Mode {} not recognized!'.format(what))

        cols, p = [], []
        for c in self._qb.get_keys(table):
            cols.append(c)
            try:
                p.append(kwargs[c])
            except KeyError:
                raise KeyError('Missing specification of {}'.format(c))

        q = self._qb.delete(table, cols)
        self._db.executemany(q, p, commit=True)

    def create_new_directory(self):
        """ Create a new directory for the current report. """
        new_path = self._curr_img_dir

        # If directory exists exit
        if os.path.exists(new_path):
            return

        try:
            os.makedirs(new_path)
            src = os.path.join(self._TMPL_PATH, "style.css")
            dst = os.path.join(self._curr_report_dir, "style.css")
            shutil.copyfile(src, dst)
        except OSError as ex:
            print('Creation of the directory {} failed'.format(new_path))
            raise ex
        else:
            print('Successfully created the directory {}'.format(new_path))

    def set_report(self, report: str):
        """ Set the report to be produced. """
        self._p = report

    def list(self) -> list:
        """ List reports matching the current setting. """
        if not self._p:
            k, p = ('active',), (True,)
        else:
            k, p = ('report',), (self._p,)
        q = self._qb.select(self._TBL_REPORTS, keys=k)
        return self._db.execute(q, p).fetchall()

    def _fetch_report_items(self, report: str) -> list:
        """ Fetch the list of item to be calculated for the current report. """
        k, p = ('report', 'active'), (report, True)
        q = self._qb.select(self._TBL_ITEMS, keys=k)
        return self._db.execute(q, p).fetchall()

    def _calculate(self, tbg: list):
        """ Calculates results by calling all models. """
        cid = self._curr_img_dir

        ret_dict = defaultdict(dict)
        asset_dict = defaultdict(list)
        for item in tbg:
            rp, u, m, p, _ = item
            print(rp, u, m)
            pd = json.loads(p)
            report = self._REPORTS[m]

            try:
                r = report(u, pd, img_path=cid).result
            except (ValueError, Ex.MissingData, KeyError) as ex:
                print(str(ex))
                continue
            else:
                ret_dict[u][m] = r
                a_type = self._af.get_type(u)
                asset_dict[a_type].append(u)

        for k, v in asset_dict.items():
            asset_dict[k] = sorted(set(v))

        return ret_dict, asset_dict

    def _add_asset_info(self, res: dict, assets: dict):
        """ Add asset infos to the results. """
        for a_type, asset in assets.items():
            for uid in asset:
                res[uid]['info'] = self._gen_info(a_type, uid)

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

    def _generate(self, name: str, template: str, res: dict, assets: dict):
        """ Generates the actual report. """
        title = "Report - {}".format(self._cal.end.strftime('%Y-%m-%d'))
        report = ''.join([template, self._REP_EXT])
        name = ''.join([name, self._REP_EXT])

        j_loader = FileSystemLoader(self._TMPL_PATH)
        j_env = Environment(loader=j_loader)
        main = j_env.get_template(report)
        out = main.render(title=title, all_res=res, assets=assets)

        out_file = os.path.join(self._curr_report_dir, name)
        outf = open(out_file, 'w')
        outf.write(out)
        outf.close()

    def run(self):
        """ Run the report engine. """
        # Reports to be generated
        reports = self.list()
        if not reports:
            print("No reports to generate.")
            return

        # Create a new report directory
        self.create_new_directory()

        # Calculate model results
        for report in reports:
            tbg = self._fetch_report_items(report[0])
            ret_dict, asset_dict = self._calculate(tbg)
            # TODO: this has to disappear inside something else. I don't want
            #       infos to be hardcoded here in the engine.
            self._add_asset_info(ret_dict, asset_dict)

            # Generate reports
            name, template = report[0:2]
            self._generate(name, template, ret_dict, asset_dict)


def get_re_glob() -> ReportingEngine:
    return ReportingEngine()
