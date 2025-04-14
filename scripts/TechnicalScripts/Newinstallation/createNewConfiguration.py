#
# Create Configuration file script
# Creates a new configuration file from scratch


from nfpy.IO import Utilities as Ut
from nfpy.Tools.Configuration import create_new

__version__ = '0.4'
_TITLE_ = "<<< Configuration file creation script >>>"


if __name__ == '__main__':
    Ut.print_header(_TITLE_, end='\n\n')

    create_new()

    Ut.print_ok('All done!')

