##########################################################################
#
# --> Main 'runnable', acts as the application manager, responsible
#     for i/o, module handling, etc.
#
# @Tomasz Szumlak
# @Agnieszka Mucha
#
# Based on the VELO team IT scan procedure
#
# @10/07/2012
#
##########################################################################

import os, sys
from ITScanCore import *
import ITScan

def __help__():
    print ' ------------------------------------------------------------------------------- '
    print ' --> First thing - ENVIRONMENT!                                                '
    print ' Set the environment, e.g. SetupProject LHCb ROOT                              '
    print ' --> Second thing - OPTIONS                                                    '
    print ' In order to run the code properly you need to specify the following:          '
    print ' YOU MUST SPECIFY                                                              '
    print ' -p (--path) - the path to the folder where the data files are stored          '
    print ' YOU CAN SPECIFY                                                               '
    print ' -q (--quiet) - do not plot transient histograms just write them out to a file '
    print ' -t (--time) - time when the scan was initiated (hh:mm:ss)                     '
    print ' -h (--help) - print this help                                                 '
    print ' ################################################################################ '

def __init__():
    print ' --> Initialisation '
    import getopt
    options = []
    # -> check if we have LHCb and ROOT env set properly
    try:
       lhcb_env = os.environ['LHCBSYSROOT']
       root_env = os.environ['ROOTSYS']
    except KeyError:
        print ' --> You need to set the minimal environment! '
        print '     e.g. SetupProject LHCb ROOT              '
        sys.exit(2)

    __path__ = str()
    __time__ = '00:00:00'
    options = { 'path': '', 'plot': True, 'time': '' }
   
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hp:qt:", ["help", "path=", "quiet", "time="])
    except getopt.GetoptError, err:
        print str(err)
        __help__()
        sys.exit(2)

    if len(opts) == 0:
        __help__()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            __help__()
        elif opt in ('-p', '--path'):
            __path__ = arg
            options['path'] = __path__
        elif opt in ('-q', '--quiet'):
            options['plot'] = False
        elif opt in ('-t', '--time'):
            __time__ = arg
            options['time'] = __time__
        else:
            assert False, " --> Unknown option! "
            __help__()
            exit(2)
           
    __except__ = [ None, 'None', '', '0', ' ' ]
    __time_ranges__ = [(0, 23), (0, 59), (0, 59)]
    if __path__ in __except__:
         print " --> You must specify the path to the data files "
         exit(2)
    elif os.path.exists(__path__):
        print ' --> Main data repo at: ', __path__
    else:
        print ' --> You gave wrong path: ', __path__, ' check options and try again! '
        __help__()
        exit(2)
        
    if __time__ in __except__:
         print " --> You must specify time in format hh:mm:ss "
         exit(2)
    else:
        time_fragments = __time__.split(':')
        if ( time_fragments[-1] in __except__ ) or ( len(time_fragments) !=3 ):
            print ' --> Wrong time format! specify hh:mm:ss '
            __help__()
            exit(2)
        else:
            for fragment in time_fragments:
                if not fragment.isdigit():
                    print ' --> Check the time format! Must be hh:mm:ss '
                    __help__()
                    exit(2)
            for index, time_range in enumerate(__time_ranges__):
                if int(time_fragments[index]) not in range(time_range[0], time_range[1]):
                    print ' --> Check the time you give! It looks odd..., terminate! '
                    exit(2)
            
    return ( options )

# ----------
# -- MAIN --
# ----------
if __name__ == '__main__':
    opts = __init__()
    ITScan.__process_and_plot__(opts)
    # -> wait before you exit
    if opts['plot']:
        rep = raw_input( 'press a key to quit ' ) #doesn't do anything because canvas are already deleted at that time
