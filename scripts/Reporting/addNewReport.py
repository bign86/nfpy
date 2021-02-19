#
# Add new report
# Add a new report to the database
#

import nfpy.Assets as As
from nfpy.Calendar import (get_calendar_glob, today, last_business)
import nfpy.IO as IO

__version__ = '0.3'
_TITLE_ = "<<< New report add script >>>"


if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    af = As.get_af_glob()
    cal = get_calendar_glob()
    cal.initialize(today(), last_business())

    inh = IO.InputHandler()
    re = IO.get_re_glob()

    # Get a UID and check viable models
    uid = inh.input("Insert UID: ", idesc='str', checker='uid')
    asset_type = af.get_type(uid)
    models = re.get_models_per_asset_type(asset_type)

    # Create model object from input
    models_str = ', '.join(models)
    print("Available models for {} are: {}".format(asset_type, models_str))
    m = inh.input("Insert model: ")
    while m not in models:
        print("*** Model not available for this asset class! ***")
        m = inh.input("Insert model: ")
    m_obj = re.get_report_obj(m)
    
    # Ask user for parameters
    params = {}
    for p, q, kw in m_obj.INPUT_QUESTIONS:
        v = inh.input(q, **kw)
        if v:
            params[p] = v

    # Put in auto?
    active = inh.input("Set 'active' flag? (default False): ",
                       idesc='bool', default=False)

    # Add to table
    re.add(uid, m, params, active)

    print('All done!')
