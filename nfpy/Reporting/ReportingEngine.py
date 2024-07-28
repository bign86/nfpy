#
# Reporting Engine
# Main engine for reporting
#
import pandas as pd
from bs4 import BeautifulSoup
from jinja2 import (FileSystemLoader, Environment)
import os
import shutil
from typing import (Optional, Union)

from nfpy import NFPY_ROOT_DIR
import nfpy.Calendar as Cal
import nfpy.DB as DB
import nfpy.IO.Utilities as UtI
from nfpy.Tools import (get_conf_glob, Utilities as Ut)

from . import Reports as Rep


class ReportingEngine(object):
    """ Main class for reporting. """

    _TBL_REPORTS = 'Reports'
    _DT_FMT = '%Y%m%d'
    _REPORTS = {
        Rep.ReportAlerts,
        Rep.ReportBacktester,
        Rep.ReportEquityFull,
        Rep.ReportMarketShort,
        Rep.ReportPortfolio,
        Rep.ReportRiskPremium,
    }
    _TMPL_PATH = os.path.join(NFPY_ROOT_DIR, 'Reporting/Templates')

    def __init__(self, end: Optional[Cal.TyDate] = None):
        self._qb = DB.get_qb_glob()
        self._db = DB.get_db_glob()
        self._conf = get_conf_glob()

        # Work variables
        self._end = pd.Timestamp(end) if end else Cal.today(mode='timestamp')
        self._curr_report_dir = ''
        self._rep_path = ''

    def exists(self, report_id: str) -> bool:
        """ Report yes if a report with the input name exists. """
        return True if self.search(report_id) is not None else False

    @staticmethod
    def get_report_obj(r: str) -> Rep.TyReport:
        """ Return the report object given the report name. """
        return getattr(Rep, r)

    @staticmethod
    def report_obj_exist(r: str) -> bool:
        return hasattr(Rep, r)

    def search(self, report_id: str, active: Optional[bool] = None) -> Optional[Rep.ReportData]:
        """ Search a report matching the given input. """
        keys, data = ('id',), (report_id,)
        if active is not None:
            keys += ('active',)
            data += (active,)

        return list(
            map(
                Rep.ReportData._make,
                self._db.execute(
                    self._qb.select(
                        self._TBL_REPORTS,
                        keys=keys,
                    ),
                    data
                ).fetchall()
            )
        )[0]

    def run(self, report_id: str, active: Optional[bool] = None) -> None:
        """ Run the report engine. """
        self._run(self.search(report_id, active))

    def run_custom(self, report: Rep.ReportData) -> None:
        """ Run the report engine. """
        self._run(report)

    def _create_new_directory(self) -> None:
        """ Create a new directory for the today's reports. """
        new_folder = f'Reports_{Cal.today(mode="str", fmt=self._DT_FMT)}'
        new_path = os.path.join(
            self._conf.report_path,
            new_folder
        )
        self._curr_report_dir = new_path

        # If directory exists exit
        if os.path.exists(new_path):
            return

        try:
            os.makedirs(new_path)
            shutil.copyfile(
                os.path.join(self._TMPL_PATH, "style.css"),
                os.path.join(new_path, "style.css")
            )
        except OSError as ex:
            print(f'Creation of the directory {new_path} failed')
            raise ex
        else:
            print(f'Successfully created the directory {new_path}')

    def _generate(self, res: Union[dict, Rep.ReportResult]) -> None:
        """ Generates the actual report. """
        j_env = Environment(loader=FileSystemLoader(self._TMPL_PATH))
        # j_env.filters.update(res[1])
        out = j_env.get_template(res.template) \
            .render(
                title=res.title,
                res=res.output
            )

        outf = open(
            os.path.join(
                self._curr_report_dir,
                ''.join([res.id, os.path.splitext(res.template)[1]])
            ),
            mode='w'
        )
        outf.write(out)
        outf.close()

    def _run(self, report_data: Optional[Rep.ReportData]) -> None:
        """ Run the report engine. """
        # Quick exit
        if not report_data:
            return

        # Create a new report directory and set calendar
        self._set_calendar(report_data)
        self._create_new_directory()

        # Calculate model results
        print(f'>>> Generating {report_data.id} [{report_data.report}]')
        try:
            res = getattr(Rep, report_data.report)(
                report_data,
                path=self._curr_report_dir
            ).result
        except RuntimeError as ex:
            UtI.print_exc(ex)
            UtI.print_warn(f'Report failed!')
            UtI.print_exc(ex)
        else:
            # Generate the report and update the index
            self._generate(res)
            self._update_index(report_data)
            UtI.print_ok(f'Report completed!')

    def _set_calendar(self, report_data: Rep.ReportData) -> None:
        """ Set the global calendar. """
        # start_daily = self._end - DateOffset(years=report_data.calendar_setting['D'])
        start_daily = pd.Timestamp(
            self._end.year - report_data.calendar_setting['D'],
            1, 1
        )
        start_monthly = pd.Timestamp(
            self._end.year - report_data.calendar_setting['M'],
            1, 1
        )
        start_yearly = pd.Timestamp(
            self._end.year - report_data.calendar_setting['Y'],
            1, 1
        )
        Cal.get_calendar_glob().initialize(
            self._end,
            start=start_daily,
            monthly_start=start_monthly,
            yearly_start=start_yearly
        )

    def _update_index(self, done: Rep.ReportData) -> None:
        # Extract information
        to_print = [(done.id, str(done.description))]

        # Parse existing index file
        try:
            index_file = os.path.join(self._curr_report_dir, "index.html")
            with open(index_file) as f:
                soup = BeautifulSoup(f, "html.parser")
                ul = soup.find('ul', {'class': "reports_list"})

                to_print.extend([
                    tuple(li.text.split(' - ', maxsplit=1))
                    for li in ul.select('li')
                ])
        except FileNotFoundError:
            pass

        index = Ut.AttributizedDict()
        index.id = 'index'
        index.template = 'index.html'
        index.title = f"Reports list - {Cal.today(mode='str', fmt='%Y-%m-%d')}"
        index.output = sorted(set(to_print), key=lambda v: v[0])
        self._generate(index)
