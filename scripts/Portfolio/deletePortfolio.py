#
# Delete Portfolio
# Script to delete a portfolio.
#

from nfpy.Assets.Portfolio import Portfolio
import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

__version__ = '0.4'
_TITLE_ = "<<< Delete portfolio script >>>"


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # Variable
    base_table = Portfolio._BASE_TABLE
    cnst_table = Portfolio._CONSTITUENTS_TABLE

    # Choose an uid and check for existence
    uid = inh.input("Give the portfolio uid to delete: ", idesc='uid')

    # Are you sure?
    proceed = inh.input("Do you want to proceed? (default No): ", idesc='bool',
                        default=False)

    # Delete
    q_ptf = qb.delete(base_table, fields=('uid',))
    db.execute(q_ptf, (uid,), commit=True)

    q_pos = qb.delete(cnst_table, fields=('ptf_uid',))
    db.execute(q_pos, (uid,), commit=True)

    Ut.print_ok('All done!')
