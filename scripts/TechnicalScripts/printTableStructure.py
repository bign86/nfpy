#
# Print table structure script
#

import nfpy.DB as DB
import nfpy.IO as IO
from nfpy.Tools import Utilities as Ut

__version__ = '0.3'
_TITLE_ = "<<< Print table structure script >>>"


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    qb = DB.get_qb_glob()
    inh = IO.InputHandler()

    table = inh.input("Give me a table to dump: ", idesc='table')
    print(qb.get_structure_string(table))

    Ut.print_ok('All done!')
