#
# Reporting Engine
# Main engine for reporting
#

from bs4 import BeautifulSoup
from jinja2 import FileSystemLoader, Environment
import os
import shutil
from typing import (Generator, Iterable, KeysView, Union)

from nfpy import NFPY_ROOT_DIR
import nfpy.Calendar as Cal
import nfpy.DB as DB
from nfpy.Tools import (get_conf_glob, Singleton, Utilities as Ut)

from .Reports import *


class ReportingEngine(metaclass=Singleton):
    """ Main class for reporting. """

    _TBL_REPORTS = 'Reports'
    _DT_FMT = '%Y%m%d'
    _REPORTS = {
        'Market': ReportMarket,
        'Alerts': ReportAlerts,
        'Backtest': ReportBacktester,
    }
    _TMPL_PATH = os.path.join(NFPY_ROOT_DIR, 'Reporting/Templates')
    _REP_EXT = '.html'

    def __init__(self):
        self._qb = DB.get_qb_glob()
        self._db = DB.get_db_glob()
        self._conf = get_conf_glob()

        # Work variables
        self._curr_report_dir = ''
        self._rep_path = ''

    def get_report_obj(self, r: str) -> TyReport:
        """ Return the report object given the report name. """
        return self._REPORTS[r]

    def get_report_types(self) -> KeysView:
        return self._REPORTS.keys()

    def exists(self, name: str) -> bool:
        """ Report yes if a report with the input name exists. """
        if len(list(self.list((name,)))) > 0:
            return True
        else:
            return False

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

    def list(self, names: [str] = (), active: bool = None) \
            -> Generator[ReportData, ReportData, None]:
        """ List reports matching the given input. """
        where = ''
        if names:
            name_list = "\', \'".join(names)
            where = f"name in ('{name_list}')"

        keys, data = [], []
        if active is not None:
            keys = ('active',)
            data = (active,)

        return (
            report for report in
            map(
                ReportData._make,
                self._db.execute(
                    self._qb.select(
                        self._TBL_REPORTS,
                        keys=keys,
                        where=where
                    ),
                    data
                ).fetchall()
            )
        )

    def _generate(self, res: Union[dict, ReportResult]) -> None:
        """ Generates the actual report. """
        j_env = Environment(loader=FileSystemLoader(self._TMPL_PATH))
        # j_env.filters.update(res[1])
        out = j_env.get_template(''.join([res.template, self._REP_EXT])) \
            .render(
            title=res.title,
            res=res.output
        )

        outf = open(
            os.path.join(
                self._curr_report_dir,
                ''.join([res.name, self._REP_EXT])
            ),
            mode='w'
        )
        outf.write(out)
        outf.close()

    def _run(self, call_list: Union[Iterable, Generator]) -> None:
        """ Run the report engine. """
        # Create a new report directory
        self._create_new_directory()

        # Calculate model results
        done_reports = []
        for data in call_list:
            print(f'>>> Generating {data.name} [{data.report}]')
            try:
                res = self._REPORTS[data.report](
                    data,
                    path=self._curr_report_dir
                ).result
            except RuntimeError as ex:
                Ut.print_exc(ex)
                continue
            self._generate(res)
            done_reports.append(data)

        # Update report index
        self._update_index(done_reports)

    def run(self, names: [str] = (), active: bool = None) -> None:
        """ Run the report engine. """
        self._run(self.list(names, active))

    def run_custom(self, rep_list: [ReportData]) -> None:
        """ Run the report engine. """
        self._run(rep_list)

    def _update_index(self, done: [ReportData]) -> None:
        # Extract information
        to_print = [
            (d.name, str(d.description))
            for d in done
        ]

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
        index.name = 'index'
        index.template = 'index'
        index.title = f"Reports list - {Cal.today(mode='str', fmt='%Y-%m-%d')}"
        index.output = sorted(set(to_print), key=lambda v: v[0])
        self._generate(index)


def get_re_glob() -> ReportingEngine:
    return ReportingEngine()
