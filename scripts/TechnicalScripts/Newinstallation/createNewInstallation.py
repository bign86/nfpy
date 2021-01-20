#
# Create Database script
# Creates a new database from scratch
#


from .createNewConfiguration import create_configuration
from .createNewDatabase import new_database

__version__ = '0.2'
_TITLE_ = "<<< New installation script >>>"


def install():
    print('--- Create new configuration ---')
    create_configuration()
    print('--- Create new database ---')
    new_database()


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')
    install()

    print('All done!')
