#
# Profile with Pympler
# Run the report engine on all automatic reports
#

from pympler.classtracker import ClassTracker
from pympler.classtracker_stats import HtmlStats

__version__ = '0.1'
_TITLE_ = "<<< Pympler profiler >>>"

if __name__ == '__main__':
    print(_TITLE_, end='\n\n')

    track = ClassTracker()
    # track.track_class()
    track.start_periodic_snapshots(2)

    # Do something

    track.stop_periodic_snapshots()
    track.stats.print_summary()
    HtmlStats(tracker=track).create_html('profile.html')
    print('All done!')
