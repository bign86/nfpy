#
# Reporting Engine
# Main engine for reporting
#

from jinja2 import FileSystemLoader, Environment
import os
import shutil

from nfpy import NFPY_ROOT_DIR
from nfpy.Assets import get_af_glob
from nfpy.Calendar import get_calendar_glob
import nfpy.DB as DB
from nfpy.Tools import (get_conf_glob, Singleton)

from .Reports import *


class ReportingEngine(metaclass=Singleton):
    """ Main class for reporting. """

    _TBL_REPORTS = 'Reports'
    _DT_FMT = '%Y%m%d'
    _IMG_DIR = 'img'
    _REPORTS = {
        'Market': ReportMarket,
    }
    _TMPL_PATH = os.path.join(NFPY_ROOT_DIR, 'Reporting/Templates')
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

    def _initialize(self) -> None:
        new_folder = f'Report_{self._cal.end.strftime(self._DT_FMT)}'
        self._curr_report_dir = os.path.join(
            self._conf.report_path,
            new_folder
        )
        self._curr_img_dir = os.path.join(
            self._conf.report_path,
            new_folder,
            self._IMG_DIR
        )

    def get_report_obj(self, r: str) -> TyReport:
        """ Return the report object given the report name. """
        return self._REPORTS[r]

    def create_new_directory(self) -> None:
        """ Create a new directory for the current report. """
        new_path = self._curr_img_dir

        # If directory exists exit
        if os.path.exists(new_path):
            return

        try:
            os.makedirs(new_path)
            shutil.copyfile(
                os.path.join(self._TMPL_PATH, "style.css"),
                os.path.join(self._curr_report_dir, "style.css")
            )
        except OSError as ex:
            print(f'Creation of the directory {new_path} failed')
            raise ex
        else:
            print(f'Successfully created the directory {new_path}')

    def set_report(self, report: str) -> None:
        """ Set the report to be produced. """
        self._p = report

    def list(self) -> list:
        """ List reports matching the current setting. """
        return self._db.execute(
            self._qb.select(
                self._TBL_REPORTS,
                keys=('active',)
            ),
            (True,)
        ).fetchall()

    def _calculate(self, data: str) -> tuple:
        """ Calculates results by calling all models. """
        cid = self._curr_img_dir
        report, uids, params = data[1], data[3], data[4]
        print(report, uids, params)

        # pd = json.loads(params)
        # uid_lst = json.loads(uids)
        report_obj = self._REPORTS[report]

        res, filters = None, None
        try:
            report = report_obj(uids, params, img_path=cid)
            res = report.result
            filters = report.filters
        except RuntimeError as ex:
            # traceback.print_exc()
            print(str(ex))

        return res, filters

    def _generate(self, name: str, template: str, res: tuple) -> None:
        """ Generates the actual report. """
        j_env = Environment(loader=FileSystemLoader(self._TMPL_PATH))
        j_env.filters.update(res[1])
        main = j_env.get_template(''.join([template, self._REP_EXT]))
        out = main.render(
            title=f"Report - {self._cal.end.strftime('%Y-%m-%d')}",
            res=res[0]
        )  # , assets=assets)

        outf = open(
            os.path.join(
                self._curr_report_dir,
                ''.join([name, self._REP_EXT])
            ),
            mode='w'
        )
        outf.write(out)
        outf.close()

    def run(self) -> None:
        """ Run the report engine. """
        # Reports to be generated
        report_lst = self.list()
        if not report_lst:
            print("No reports to generate.")
            return

        # Create a new report directory
        self.create_new_directory()

        # Calculate model results
        for data in report_lst:
            out = self._calculate(data)

            # Generate reports
            self._generate(data[0], data[2], out)


def get_re_glob() -> ReportingEngine:
    return ReportingEngine()
