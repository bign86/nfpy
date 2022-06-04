#
# Reporting Engine
# Main engine for reporting
#

from bs4 import BeautifulSoup
from jinja2 import (FileSystemLoader, Environment)
import os
import shutil
from typing import (Generator, Optional, Sequence, Union)

from nfpy import NFPY_ROOT_DIR
import nfpy.Calendar as Cal
import nfpy.DB as DB
from nfpy.Tools import (get_conf_glob, Singleton, Utilities as Ut)

from . import Reports as Rep


class ReportingEngine(metaclass=Singleton):
    """ Main class for reporting. """

    _TBL_REPORTS = 'Reports'
    _DT_FMT = '%Y%m%d'
    _REPORTS = {
        Rep.ReportAlerts,
        Rep.ReportBacktester,
        Rep.ReportCompanies,
        Rep.ReportEquities,
        Rep.ReportMarketShort,
        Rep.ReportPortfolio,
    }
    _TMPL_PATH = os.path.join(NFPY_ROOT_DIR, 'Reporting/Templates')

    def __init__(self):
        self._qb = DB.get_qb_glob()
        self._db = DB.get_db_glob()
        self._conf = get_conf_glob()

        # Work variables
        self._curr_report_dir = ''
        self._rep_path = ''

    def exists(self, report_id: str) -> bool:
        """ Report yes if a report with the input name exists. """
        if len(list(self.list((report_id,)))) > 0:
            return True
        else:
            return False

    @staticmethod
    def get_report_obj(r: str) -> Rep.TyReport:
        """ Return the report object given the report name. """
        return getattr(Rep, r)

    @staticmethod
    def report_obj_exist(r: str) -> bool:
        return hasattr(Rep, r)

    def list(self, ids: Sequence[str] = (), active: Optional[bool] = None) \
            -> Generator[Rep.ReportData, Rep.ReportData, None]:
        """ List reports matching the given input. """
        where = ''
        if ids:
            name_list = "\', \'".join(ids)
            where = f"id in ('{name_list}')"

        keys, data = [], []
        if active is not None:
            keys = ('active',)
            data = (active,)

        return (
            report for report in
            map(
                Rep.ReportData._make,
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

    def run(self, names: Sequence[str] = (), active: Optional[bool] = None) \
            -> None:
        """ Run the report engine. """
        self._run(self.list(names, active))

    def run_custom(self, rep_list: Sequence[Rep.ReportData]) -> None:
        """ Run the report engine. """
        self._run(rep_list)

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

    def _run(self, call_list: Union[Sequence, Generator]) -> None:
        """ Run the report engine. """
        # Create a new report directory
        self._create_new_directory()

        # Calculate model results
        done_reports = []
        for data in call_list:
            print(f'>>> Generating {data.id} [{data.report}]')
            try:
                res = getattr(Rep, data.report)(
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

    def _update_index(self, done: Sequence[Rep.ReportData]) -> None:
        # Extract information
        to_print = [
            (d.id, str(d.description))
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
        index.id = 'index'
        index.template = 'index.html'
        index.title = f"Reports list - {Cal.today(mode='str', fmt='%Y-%m-%d')}"
        index.output = sorted(set(to_print), key=lambda v: v[0])
        self._generate(index)


def get_re_glob() -> ReportingEngine:
    return ReportingEngine()
