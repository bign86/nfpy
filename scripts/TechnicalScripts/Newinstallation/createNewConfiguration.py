#
# Create Configuration file script
# Creates a new configuration file from scratch
#


from nfpy.Handlers.Configuration import PARAMS_DICT__, create_new
from nfpy.Handlers.Inputs import InputHandler

__version__ = '0.1'
_TITLE_ = "<<< Configuration file creation script >>>"


def create_configuration():
    inh = InputHandler()

    print('Insert the following parameters:')
    parameters = {}
    for k, v in PARAMS_DICT__.items():
        p = inh.input(v + ': ', idesc='str')
        parameters[k] = p if p else ''

    print('Creating new file...')
    create_new(parameters)
    print("--- File Created! ---")


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')
    create_configuration()
