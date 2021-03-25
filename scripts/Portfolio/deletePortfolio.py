#
# Delete Portfolio Script
# Script to delete a portfolio.
#

from nfpy.Assets.Portfolio import Portfolio
import nfpy.DB as DB
import nfpy.IO as IO

__version__ = '0.3'
_TITLE_ = "<<< Delete portfolio script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    db = DB.get_db_glob()
    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    # Variable
    base_table = Portfolio._BASE_TABLE
    cnst_table = Portfolio._CONSTITUENTS_TABLE
    # TODO: not used
    # ts_table = Portfolio._TS_TABLE

    # Choose a uid and check for existence
    uid = inh.input("Give a uid for the new portfolio: ", idesc='uid',
                    checker='uid')

    # Are you sure?
    proceed = inh.input("Do you want to proceed? (default No): ", idesc='bool',
                        default=False)

    # Delete
    q_ptf = qb.delete(base_table, fields=('uid',))
    q_pos = qb.delete(cnst_table, fields=('ptf_uid',))
    # TODO: not used
    # q_ts = qb.delete(ts_table, fields=('uid',))

    db.execute(q_ptf, (uid,), commit=True)
    db.execute(q_pos, (uid,), commit=True)
    # TODO: not used
    # db.execute(q_ts, data, commit=True)

    print("All done!")
