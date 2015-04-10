##########################################################################
#
# --> Core functionality of the IT scan for the VELO
# @Tomasz Szumlak
# @Agnieszka Mucha
#
# Based on Paula Collins IT scan procedure
#
# @16/04/2012
#
##########################################################################

import sys, os
import csv
from math import fabs
from ROOT import TH1F, kFALSE, TProfile

# -> definitions -----------------
SUCCESS = 1
FAILURE = 0
#
LABEL = 0
SENSOR = 1
#
HEADER = 2
TEMP_SIGNATURE = 'VEDCSHV'
HVI_SIGNATURE  = 'VEHV'
NULL_ENTRIES = ['', '0', 'nan']
#
HOUR = 3600
MINUTE = 60
#
CANVAS_HISTO = 16
#
TIME = 0
HVI = 1
TEMP = 1
TEMP_PREFIX = 5
HVI_PREFIX = 2
#
TIME_POINT = 0
FIRST_ENTRY = 0
LAST_ENTRY = -1
CONST_TEMP = 0
TIME_INTERVAL = 1
TEMP_BIN_OFFSET = 2 # centigrade
I_HV_MIN = 0.
I_HV_MAX = 0.5
# ---------------------------------

#
class HVCurrentDecoder:
    """ ---------------------------------------------------------------- """
    """  This class acts as a decoder of the HV currents from csv file   """
    """  !! The constructor requires a path to the data files !!         """
    """ ---------------------------------------------------------------- """

    # -> constructor
    # ---------------
    def __init__(self, data_path):
        self.__members__ = {
            'class_id'          : 'HVCurrentDecoder'
           ,'__RAW__'           : []
           ,'__HEADER__'        : { }
           ,'__DECODED__'       : { }
           ,'__path__'          : ''
           ,'__status__'        : None
           ,'__HVI__'           : { }
           ,'__scan_tdate__'    : None
        }
        self.__doc_fields__ = {
            'class_id'          : """ class name """
           ,'__RAW__'           : """ pointers to the body of csv files """
           ,'__HEADER__'        : """ structure containing all header data """
           ,'__DECODED__'       : """ decode data - not separated """
           ,'__DATA__'          : """ structure that holds the decoded data for all sensors """
           ,'__path__'          : """ path to the encoded data files """
           ,'__status__'        : """ processing status """
           ,'__HVI__'           : """ high voltage currents and time """
           ,'__scan_tdate__'    : """ time and date of the current scan """
        }

        # --> check if the given argument is valid
        if data_path != None and data_path != '':
            if os.path.exists(data_path):
                print " --> ", self.__members__['class_id'], "decoder will decode data at: "
                print '     ' + '\033[91m' + data_path + '\033[0m'
                self.__members__['__path__'] = data_path
                self.__members__['__status__'] = SUCCESS
            else:
                print " --> Fatal problem! Given data path: ", self.__members__['__path__']
                print "     is INVALID!!  Processing is terminated! "
                self.__members__['__status__'] = FAILURE
        else:
            print " --> You must provide the path to the data files! "
            print "     Processing is terminated! "
            self.__members__['__status__'] = FAILURE
        self.__check_sources__()
        self.__connect2raw__()
        self.__check_content_and_write_data__()

        # -> sanit check - must have the same number of headers and data blocks
        if len(self.__members__['__DECODED__']) != len(self.__members__['__HEADER__']):
            sefl.__members__['__status__'] = FAILURE
            print ' --> FATAL! The number of headers and data block dont match! '

        # -> and finally create time ordered hvis
        self.__create_time_ordered_hvis__()

        #print len(self.__members__['__HVI__'].keys())

    # -> check the decoder status
    # ---------------------------
    def getStatus(self):
        return ( self.__members__['__status__'] )
    
    # -> class name
    # -------------
    def getName(self):
        return ( self.__members__['class_id'] )

    # -> time and date of the scan
    def getTDate(self):
        tdate = self.__members__['__scan_tdate__']
        tdate = tdate.replace('/', '.')
        tdate = tdate.replace(' ', '_')        
        return ( tdate )

    # -> return the time-ordered currents
    def getData(self):
        return ( self.__members__['__HVI__'] )
    
    # -> check what is inside the folder with data files
    # --------------------------------------------------
    def __check_sources__(self):
        print ' --> I will attempt to decode the following files: '
        print ' ------------------------------------------------- '
        list = os.listdir(self.__members__['__path__'])
        for file in list:
            print file
        print ' ------------------------------------------------- '
        
    # -> connect to file and read data
    # --------------------------------
    def __connect2raw__(self):
        __path__=self.__members__['__path__']
        try:
            list = os.listdir(__path__)
            for file in list:
                raw = csv.reader(open(__path__ + '/' + file, 'rb'))
                self.__members__['__RAW__'].append(raw)
        except IOError:
            print ' --> Problem with reading data files '
            self.__members__['__status__'] = FAILURE
            
    # -> check which files contain HV currents, discard if not currents
    # -----------------------------------------------------------------
    def __check_content_and_write_data__(self):
        raw_data = self.__members__['__RAW__']
        for item, source in enumerate(raw_data):
            header = []
            decoded_data = []
            hvi_file = False
            head_1 = source.next()
            head_2 = source.next()
            for entry in head_1:
                if entry != '':
                    if HVI_SIGNATURE in entry.split(':'):
                        hvi_file = True
                        break
            if hvi_file:
                header.append(head_1)
                for record in source:
                    decoded_data.append(record)
                self.__members__['__DECODED__'][item] = decoded_data
                self.__members__['__HEADER__'][item] = header
                
    # -> grab the data and create time ordered tables for each sensor
    # ---------------------------------------------------------------
    def __create_time_ordered_hvis__(self):
        hvis = self.__members__['__DECODED__']
        headers = self.__members__['__HEADER__']
        first_key = hvis.keys()[0]
        self.__members__['__scan_tdate__'] = hvis[first_key][0][0][:19]
        
        # -> must be the same for both headers and decoded data
        keys = headers.keys()

        # -> now save (time, hvi) pairs for each sensor
        for key in keys:
            data = hvis[key]
            header = headers[key]
            channels = []
            for entry in header:
                for entry_element in entry:
                    if entry_element != '':
                        channels.append(entry_element[23:32])
            for entry in data:
                time = entry[0][11:19]
                e_data = []
                for index in range(1, len(entry) - 1):
                    e_data.append(entry[index])
                for chan, current in enumerate(e_data):
                    if current not in NULL_ENTRIES:
                        if channels[chan] not in self.__members__['__HVI__']:
                            self.__members__['__HVI__'][channels[chan]] = []
                        t_hvi = [time, current[:8]] 
                        self.__members__['__HVI__'][channels[chan]].append(t_hvi)

#
class TemperatureDecoder:
    """ ------------------------------------------------------------------ """
    """  This class acts as a decoder of the Temp currents from csv file   """
    """  !! The constructor requires a path to the data files !!           """
    """ ------------------------------------------------------------------ """

    # -> constructor
    # ---------------
    def __init__(self, data_path, deb = False):
        self.__members__ = {
            'class_id'          : 'TemperatureDecoder'
           ,'__RAW__'           : []
           ,'__HEADER__'        : { }
           ,'__DECODED__'       : { }
           ,'__path__'          : ''
           ,'__status__'        : None
           ,'__TEMP__'          : { }
           ,'__scan_tdate__'    : None
           ,'DEBUG'             : False
        }
        self.__doc_fields__ = {
            'class_id'          : """ class name """
           ,'__RAW__'           : """ pointers to the body of csv files """
           ,'__HEADER__'        : """ structure containing all header data """
           ,'__DECODED__'       : """ decode data - not separated """
           ,'__DATA__'          : """ structure that holds the decoded data for all sensors """
           ,'__path__'          : """ path to the encoded data files """
           ,'__status__'        : """ processing status """
           ,'__TEMP__'          : """ temperature and time """
           ,'__scan_tdate__'    : """ time and date of the current scan """
           ,'DEBUG'             : """ debug flag """
        }

        # --> check if the given argument is valid
        if data_path != None and data_path != '':
            if os.path.exists(data_path):
                print " ### The given path looks valid! ### "
                print " -->", self.__members__['class_id'], "decoder will decode data at:"
                print '     ' + '\033[91m' + data_path + '\033[0m'
                print " ################################### "
                self.__members__['__path__'] = data_path
                self.__members__['__status__'] = SUCCESS
            else:
                print " --> Fatal problem! Given data path: ", self.__members__['__path__']
                print "     is INVALID!!  Processing is terminated! "
                self.__members__['__status__'] = FAILURE
        else:
            print " --> You must provide the path to the data files! "
            print "     Processing is terminated! "
            self.__members__['__status__'] = FAILURE
        self.__members__['DEBUG'] = deb
        self.__check_sources__()
        self.__connect2raw__()
        self.__check_content_and_write_data__()

        # -> sanity check - must have the same number of headers and data blocks
        if len(self.__members__['__DECODED__']) != len(self.__members__['__HEADER__']):
            sefl.__members__['__status__'] = FAILURE
            print ' --> FATAL! The number of headers and data block dont match! '
            exit(2)

        # -> and finally create time ordered temperatures
        self.__create_time_ordered_temps__()

    # -> check the decoder status
    # ---------------------------
    def getStatus(self):
        return ( self.__members__['__status__'] )
    
    # -> class name
    # -------------
    def getName(self):
        return ( self.__members__['class_id'] )

    # -> time and date of the scan
    def getTDate(self):
        tdate = self.__members__['__scan_tdate__']
        tdate = tdate.replace('/', '.')
        tdate = tdate.replace(' ', '_')        
        return ( tdate )

    # -> return the time-ordered currents
    def getData(self):
        return ( self.__members__['__TEMP__'] )
    
    # -> check what is inside the folder with data files
    # --------------------------------------------------
    def __check_sources__(self):
        print ' --> I will attempt to decode the following files: '
        print ' ------------------------------------------------- '
        list = os.listdir(self.__members__['__path__'])
        for file in list:
            print file
        print ' ------------------------------------------------- '
        
    # -> connect to file and read data, create a reader object
    # --------------------------------------------------------
    def __connect2raw__(self):
        __path__=self.__members__['__path__']
        try:
            list = os.listdir(__path__)
            for file in list:
                raw = csv.reader(open(__path__ + '/' + file, 'rb'))
                self.__members__['__RAW__'].append(raw)
        except IOError:
            print ' --> Problem with reading data files '
            self.__members__['__status__'] = FAILURE
            
    # -> check which files contain HV currents, discard if not currents
    # -----------------------------------------------------------------
    def __check_content_and_write_data__(self):
        DEBUG = self.__members__['DEBUG']
        raw_data = self.__members__['__RAW__']
        if DEBUG:
            print len(raw_data)
        for item, source in enumerate(raw_data):
            if DEBUG:
                print item
            header = []
            decoded_data = []
            temp_file = False
            head_1 = source.next()
            head_2 = source.next()
            if DEBUG:
                print head_2
            for entry in head_1:
                if entry != '':
                    if TEMP_SIGNATURE in entry.split(':'):
                        temp_file = True
                        break
            if temp_file:
                header.append(head_2)
                for record in source:
                    decoded_data.append(record)
                self.__members__['__DECODED__'][item] = decoded_data
                self.__members__['__HEADER__'][item] = header

    # -> grab the data and create time ordered tables for each sensor
    # ---------------------------------------------------------------
    def __create_time_ordered_temps__(self):
        temps = self.__members__['__DECODED__']
        headers = self.__members__['__HEADER__']
        first_key = temps.keys()[0]
        self.__members__['__scan_tdate__'] = temps[first_key][0][0][:19]
        #print self.__members__['__scan_tdate__'] 
        
        # -> must be the same for both headers and decoded data
        keys = headers.keys()

        # -> now save (time, temp) pairs for each sensor
        for key in keys:
            data = temps[key]
            header = headers[key]
            channels = []
            for entry in header:
                for entry_element in entry:
                    if entry_element != '':
                        channels.append(entry_element[14:21])
                        #print entry_element[14:21]
            for entry in data:
                time = entry[0][11:19]
                e_data = []
                for index in range(1, len(entry) - 1):
                    e_data.append(entry[index])
                for chan, temp in enumerate(e_data):
                    if temp not in NULL_ENTRIES:
                        if channels[chan] not in self.__members__['__TEMP__']:
                            self.__members__['__TEMP__'][channels[chan]] = []
                        t_temp = [time, temp[:7]]
                        #if channels[chan] == 'VL08_CT':
                        #    print t_temp
                        self.__members__['__TEMP__'][channels[chan]].append(t_temp)

#
class HVChannelMapper:
    """ ---------------------------------------------------------------- """
    """  The HVIMapper class provides mapping between HV power supply    """
    """  channels and the Velo source id (sensor) numbers                """
    """ ---------------------------------------------------------------- """

    def __init__(self):
        self.__members__ = {
            'class_id'                    : 'HVChannelMapper'
           ,'__HV_Channel2_Label_Sens__'  : { }
        }
        self.__createMap__()

    def __createMap__(self):
        # -> header data have format as follow: maXX/chXX
        #    map will relate hardware channels with labels and sensors
        # ----------------------
        # -> side C, HV_Board00
        self.__members__['__HV_Channel2_Label_Sens__']['ma06/ch00'] = ['PU01_CT', 129]
        self.__members__['__HV_Channel2_Label_Sens__']['ma06/ch01'] = ['PU02_CB', 131]
        self.__members__['__HV_Channel2_Label_Sens__']['ma06/ch02'] = ['VL01_CT', 65]
        self.__members__['__HV_Channel2_Label_Sens__']['ma06/ch03'] = ['VL01_CB', 1]
        self.__members__['__HV_Channel2_Label_Sens__']['ma06/ch04'] = ['VL02_CT', 3]
        self.__members__['__HV_Channel2_Label_Sens__']['ma06/ch05'] = ['VL02_CB', 67]
        self.__members__['__HV_Channel2_Label_Sens__']['ma06/ch06'] = ['VL03_CT', 69]
        self.__members__['__HV_Channel2_Label_Sens__']['ma06/ch07'] = ['VL03_CB', 5]
        # -> side C, HV_Board01
        self.__members__['__HV_Channel2_Label_Sens__']['ma07/ch00'] = ['VL04_CT', 7]
        self.__members__['__HV_Channel2_Label_Sens__']['ma07/ch01'] = ['VL04_CB', 71]
        self.__members__['__HV_Channel2_Label_Sens__']['ma07/ch02'] = ['VL05_CT', 73]
        self.__members__['__HV_Channel2_Label_Sens__']['ma07/ch03'] = ['VL05_CB', 9]
        self.__members__['__HV_Channel2_Label_Sens__']['ma07/ch04'] = ['VL06_CT', 11]
        self.__members__['__HV_Channel2_Label_Sens__']['ma07/ch05'] = ['VL06_CB', 75]
        self.__members__['__HV_Channel2_Label_Sens__']['ma07/ch06'] = ['VL07_CT', 77]
        self.__members__['__HV_Channel2_Label_Sens__']['ma07/ch07'] = ['VL07_CB', 13]
        # -> side C, HV_Board02
        self.__members__['__HV_Channel2_Label_Sens__']['ma08/ch00'] = ['VL08_CT', 15]
        self.__members__['__HV_Channel2_Label_Sens__']['ma08/ch01'] = ['VL08_CB', 79]
        self.__members__['__HV_Channel2_Label_Sens__']['ma08/ch02'] = ['VL09_CT', 81]
        self.__members__['__HV_Channel2_Label_Sens__']['ma08/ch03'] = ['VL09_CB', 17]
        self.__members__['__HV_Channel2_Label_Sens__']['ma08/ch04'] = ['VL10_CT', 19]
        self.__members__['__HV_Channel2_Label_Sens__']['ma08/ch05'] = ['VL10_CB', 83]
        self.__members__['__HV_Channel2_Label_Sens__']['ma08/ch06'] = ['VL11_CT', 85]
        self.__members__['__HV_Channel2_Label_Sens__']['ma08/ch07'] = ['VL11_CB', 21]
        # -> side C, HV_Board03
        self.__members__['__HV_Channel2_Label_Sens__']['ma09/ch00'] = ['VL12_CT', 23]
        self.__members__['__HV_Channel2_Label_Sens__']['ma09/ch01'] = ['VL12_CB', 87]
        self.__members__['__HV_Channel2_Label_Sens__']['ma09/ch02'] = ['VL13_CT', 89]
        self.__members__['__HV_Channel2_Label_Sens__']['ma09/ch03'] = ['VL13_CB', 25]
        self.__members__['__HV_Channel2_Label_Sens__']['ma09/ch04'] = ['VL14_CT', 27]
        self.__members__['__HV_Channel2_Label_Sens__']['ma09/ch05'] = ['VL14_CB', 91]
        self.__members__['__HV_Channel2_Label_Sens__']['ma09/ch06'] = ['VL15_CT', 93]
        self.__members__['__HV_Channel2_Label_Sens__']['ma09/ch07'] = ['VL15_CB', 29]
        # -> side C, HV_Board04
        self.__members__['__HV_Channel2_Label_Sens__']['ma10/ch00'] = ['VL16_CT', 31]
        self.__members__['__HV_Channel2_Label_Sens__']['ma10/ch01'] = ['VL16_CB', 95]
        self.__members__['__HV_Channel2_Label_Sens__']['ma10/ch02'] = ['VL19_CT', 97]
        self.__members__['__HV_Channel2_Label_Sens__']['ma10/ch03'] = ['VL19_CB', 33]
        self.__members__['__HV_Channel2_Label_Sens__']['ma10/ch04'] = ['VL22_CT', 35]
        self.__members__['__HV_Channel2_Label_Sens__']['ma10/ch05'] = ['VL22_CB', 99]
        self.__members__['__HV_Channel2_Label_Sens__']['ma10/ch06'] = ['VL23_CT', 101]
        self.__members__['__HV_Channel2_Label_Sens__']['ma10/ch07'] = ['VL23_CB', 37]
        # -> side C, HV_Board05
        self.__members__['__HV_Channel2_Label_Sens__']['ma11/ch00'] = ['VL24_CT', 39]
        self.__members__['__HV_Channel2_Label_Sens__']['ma11/ch01'] = ['VL24_CB', 103]
        self.__members__['__HV_Channel2_Label_Sens__']['ma11/ch02'] = ['VL25_CT', 105]
        self.__members__['__HV_Channel2_Label_Sens__']['ma11/ch03'] = ['VL25_CB', 41]
        # ----------------------
        # -> side A, HV_Board00
        self.__members__['__HV_Channel2_Label_Sens__']['ma00/ch00'] = ['PU01_AT', 130]
        self.__members__['__HV_Channel2_Label_Sens__']['ma00/ch01'] = ['PU02_AB', 128]
        self.__members__['__HV_Channel2_Label_Sens__']['ma00/ch02'] = ['VL01_AT', 64]
        self.__members__['__HV_Channel2_Label_Sens__']['ma00/ch03'] = ['VL01_AB', 0]
        self.__members__['__HV_Channel2_Label_Sens__']['ma00/ch04'] = ['VL02_AT', 2]
        self.__members__['__HV_Channel2_Label_Sens__']['ma00/ch05'] = ['VL02_AB', 66]
        self.__members__['__HV_Channel2_Label_Sens__']['ma00/ch06'] = ['VL03_AT', 68]
        self.__members__['__HV_Channel2_Label_Sens__']['ma00/ch07'] = ['VL03_AB', 4]
        # -> side A, HV_Board01
        self.__members__['__HV_Channel2_Label_Sens__']['ma01/ch00'] = ['VL04_AT', 6]
        self.__members__['__HV_Channel2_Label_Sens__']['ma01/ch01'] = ['VL04_AB', 70]
        self.__members__['__HV_Channel2_Label_Sens__']['ma01/ch02'] = ['VL05_AT', 72]
        self.__members__['__HV_Channel2_Label_Sens__']['ma01/ch03'] = ['VL05_AB', 8]
        self.__members__['__HV_Channel2_Label_Sens__']['ma01/ch04'] = ['VL06_AT', 10]
        self.__members__['__HV_Channel2_Label_Sens__']['ma01/ch05'] = ['VL06_AB', 74]
        self.__members__['__HV_Channel2_Label_Sens__']['ma01/ch06'] = ['VL07_AT', 76]
        self.__members__['__HV_Channel2_Label_Sens__']['ma01/ch07'] = ['VL07_AB', 12]
        # -> side A, HV_Board02
        self.__members__['__HV_Channel2_Label_Sens__']['ma02/ch00'] = ['VL08_AT', 14]
        self.__members__['__HV_Channel2_Label_Sens__']['ma02/ch01'] = ['VL08_AB', 78]
        self.__members__['__HV_Channel2_Label_Sens__']['ma02/ch02'] = ['VL09_AT', 80]
        self.__members__['__HV_Channel2_Label_Sens__']['ma02/ch03'] = ['VL09_AB', 16]
        self.__members__['__HV_Channel2_Label_Sens__']['ma02/ch04'] = ['VL10_AT', 18]
        self.__members__['__HV_Channel2_Label_Sens__']['ma02/ch05'] = ['VL10_AB', 82]
        self.__members__['__HV_Channel2_Label_Sens__']['ma02/ch06'] = ['VL11_AT', 84]
        self.__members__['__HV_Channel2_Label_Sens__']['ma02/ch07'] = ['VL11_AB', 20]
        # -> side C, HV_Board03
        self.__members__['__HV_Channel2_Label_Sens__']['ma03/ch00'] = ['VL12_AT', 22]
        self.__members__['__HV_Channel2_Label_Sens__']['ma03/ch01'] = ['VL12_AB', 86]
        self.__members__['__HV_Channel2_Label_Sens__']['ma03/ch02'] = ['VL13_AT', 88]
        self.__members__['__HV_Channel2_Label_Sens__']['ma03/ch03'] = ['VL13_AB', 24]
        self.__members__['__HV_Channel2_Label_Sens__']['ma03/ch04'] = ['VL14_AT', 26]
        self.__members__['__HV_Channel2_Label_Sens__']['ma03/ch05'] = ['VL14_AB', 90]
        self.__members__['__HV_Channel2_Label_Sens__']['ma03/ch06'] = ['VL15_AT', 92]
        self.__members__['__HV_Channel2_Label_Sens__']['ma03/ch07'] = ['VL15_AB', 28]
        # -> side A, HV_Board04
        self.__members__['__HV_Channel2_Label_Sens__']['ma04/ch00'] = ['VL16_AT', 30]
        self.__members__['__HV_Channel2_Label_Sens__']['ma04/ch01'] = ['VL16_AB', 94]
        self.__members__['__HV_Channel2_Label_Sens__']['ma04/ch02'] = ['VL19_AT', 96]
        self.__members__['__HV_Channel2_Label_Sens__']['ma04/ch03'] = ['VL19_AB', 32]
        self.__members__['__HV_Channel2_Label_Sens__']['ma04/ch04'] = ['VL22_AT', 34]
        self.__members__['__HV_Channel2_Label_Sens__']['ma04/ch05'] = ['VL22_AB', 98]
        self.__members__['__HV_Channel2_Label_Sens__']['ma04/ch06'] = ['VL23_AT', 100]
        self.__members__['__HV_Channel2_Label_Sens__']['ma04/ch07'] = ['VL23_AB', 36]
        # -> side A, HV_Board05
        self.__members__['__HV_Channel2_Label_Sens__']['ma05/ch00'] = ['VL24_AT', 38]
        self.__members__['__HV_Channel2_Label_Sens__']['ma05/ch01'] = ['VL24_AB', 102]
        self.__members__['__HV_Channel2_Label_Sens__']['ma05/ch02'] = ['VL25_AT', 104]
        self.__members__['__HV_Channel2_Label_Sens__']['ma05/ch03'] = ['VL25_AB', 40]

    def __auto_diagnostic_label__(self):
        map = self.__members__['__HV_Channel2_Label_Sens__']
        for chan in map:
            print ' Hardware HV channel: ', chan, ' mapped to label: ', map[chan][LABEL]
            
    def __auto_diagnostic_sensor__(self):
        map = self.__members__['__HV_Channel2_Label_Sens__']
        for chan in map:
            print ' Hardware HV channel: ', chan, ' mapped to sensor: ', map[chan][SENSOR]

    # -> get label according to the hardware HV channel
    # -------------------------------------------------
    def HVChannel2Label(self, hvChan):
        label = self.__members__['__HV_Channel2_Label_Sens__'][hvChan][LABEL]
        return ( label )

    # -> get sensor number according to the hardware HV channel
    # ---------------------------------------------------------
    def HVChannel2Sensor(self, hvChan):
        sensor = self.__members__['__HV_Channel2_Label_Sens__'][hvChan][SENSOR]
        return ( sensor )
# 
class PatternScanner():
    """ ------------------------------------------------------- """
    """ Scans the Temp data vs. time and performing very simple """
    """ pattern recognition looking for stable temperatures     """
    """ ------------------------------------------------------- """
    
    # -> constructor
    # ---------------
    def __init__(self, temp_histo_list):
        self.__members__ = {
            'class_id'          : 'PatternScanner'
           ,'__T_H__'           : []
           ,'__T_POINTS__'      : {}
           ,'__Status__'        : FAILURE
           ,'__DELTA_T__'       : 0.3
           ,'__DELTA_PAT__'     : 10
           ,'__LEAP__'          : 90
           ,'__PAT_STEP__'      : 5
        }
        self.__doc_fields__ = {
            'class_id'          : """ class name """
           ,'__T_H__'           : """ list of histograms with T(t) """
           ,'__T_POINTS__'      : """ collection of const temps and time intervals """
           ,'__Status__'        : """ initialisation status """
           ,'__DELTA_T__'       : """ max difference of temps allowed in pattern """
           ,'__DELTA_PAT__'     : """ min length of a pattern to be clasified as const temp """
           ,'__LEAP__'          : """ do not waist time looking at transient entries """
           ,'__PAT_STEP__'      : """ how often you sample the pattern """
        }
        
        temp_status = FAILURE
        
        if temp_histo_list != 'None' and len(temp_histo_list) != 0:
            self.__members__['__T_H__'] = temp_histo_list
            temp_status = SUCCESS            

        if temp_status:
            self.__members__['__Status__'] = SUCCESS

    def __compare_temp__(self, delta_T):
        is_const = True if delta_T < self.__members__['__DELTA_T__'] else False
        return ( is_const )

    def __compare_pat_length__(self, delta_pat):
        is_pat = True if delta_pat > self.__members__['__DELTA_PAT__'] else False
        return ( is_pat )

    def GetStatus(self):
        return ( self.__members__['__Status__'] )

    def GetConstTempPoints(self):
        return ( self.__members__['__T_POINTS__'] )

    def PrintConstTempPointsSensor(self, sens_label):
        if sens_label not in self.__members__['__T_POINTS__']:
            print ' -> Check your label! '
        else:
            data = self.__members__['__T_POINTS__'][sens_label]
            for time in sorted(data):
                print ' At time: ', time, ' we observed const temp: ', data[time][0][0], ' for ', data[time][0][1], ' sec ' 

    # -> search for const temperatures, simple patter recognition
    def PatReco(self):
        to_look_at = ['VL02_AT', 'VL04_CB', 'VL19_AB', 'VL09_AB']
        if self.__members__['__Status__']:
            t_banks = self.__members__['__T_H__']
            for data_bank in t_banks:
                bank_label = data_bank.GetName()[TEMP_PREFIX:]
                
                if bank_label not in self.__members__['__T_POINTS__']:
                    self.__members__['__T_POINTS__'][bank_label] = {}

                print ' --> Running Temp Pattern Recognition for sensor: ', bank_label
                nbins = data_bank.GetNbinsX()

                # -> MAIN LOOP
                bin = 0
                while bin < nbins:
                    bin += 1
                    first_in_pattern = data_bank.GetBinContent(bin)
                    next_in_pattern = data_bank.GetBinContent(bin + 1)
                    is_equal = self.__compare_temp__(fabs(first_in_pattern - next_in_pattern))
                    if is_equal:
                        for p_bin in range(bin + 2, nbins):
                            next_in_pattern = data_bank.GetBinContent(p_bin)
                            is_constant = self.__compare_temp__(fabs(first_in_pattern - next_in_pattern))
                            if is_constant:
                                p_bin = p_bin + self.__members__['__PAT_STEP__']
                                continue
                            else:
                                is_pattern = self.__compare_pat_length__(p_bin - bin)
                                if is_pattern:
                                    # -> store const temp, t_i and Delta_t
                                    const_temp = round(first_in_pattern, 2)
                                    time = int(data_bank.GetBinCenter(bin))
                                    t_point_data = [const_temp, (p_bin - bin)]
                                    if time not in self.__members__['__T_POINTS__'][bank_label]:
                                        self.__members__['__T_POINTS__'][bank_label][time] = []
                                    self.__members__['__T_POINTS__'][bank_label][time].append(t_point_data)
                                bin = p_bin + self.__members__['__LEAP__']
                                break

                                                    
# 
class ITCreator():
    """ ---------------------------------------------------------- """
    """ This class uses information returned by the PatternScanner """
    """ class to select and integrate HV currents                  """
    """ ---------------------------------------------------------- """
    
    # -> constructor
    # ---------------
    def __init__(self, hvi_histo_list, temp_points):
        self.__members__ = {
            'class_id'            : 'ITCreator'
           ,'__HVI_H__'           : []
           ,'__IT_HISTOS__'       : {}
           ,'__T_POINTS__'        : {}
           ,'__Status__'          : FAILURE
        }
        self.__doc_fields__ = {
            'class_id'            : """ class name """
           ,'__HVI_H__'           : """ list of histograms with i_hv(t) """
            ,'_IT_HISTOS__'       : """ a collection of histograms of i_hv(T) """
           ,'__T_POINTS__'        : """ const temperatures found by the scanner class """
           ,'__Status__'          : """ initialisation status """
        }
        
        hvi_status = FAILURE
        temp_status = FAILURE
        
        if hvi_histo_list != 'None' and len(hvi_histo_list) != 0:
            self.__members__['__HVI_H__'] = hvi_histo_list
            hvi_status = SUCCESS            

        if temp_points != 'None' and len(temp_points) != 0:
            self.__members__['__T_POINTS__'] = temp_points
            temp_status = SUCCESS            

        if ( hvi_status and temp_status ):
            self.__members__['__Status__'] = SUCCESS

    def __compare_temp__(self, delta_T):
        is_const = True if delta_T < self.__members__['__DELTA_T__'] else False
        return ( is_const )

    def GetStatus(self):
        return ( self.__members__['__Status__'] )

    def GetITPlots(self):
        return ( self.__members__['__IT_HISTOS__'] )

    def __find_hvi_histo__(self, label):
        hvi_histo = None
        for histo in self.__members__['__HVI_H__']:
            hvi_label = histo.GetName()[HVI_PREFIX:]
            if hvi_label == label:
                hvi_histo = histo.Clone()
                break
        return ( hvi_histo )

    def __const_temp_list__(self, time_data):
        const_temps = []
        for time_point in sorted(time_data):
            temp_data = time_data[time_point]
            const_temps.append(temp_data[TIME_POINT][CONST_TEMP])
        return ( const_temps )


    def FindAndIntegrateHVIs(self):
        T_Points = self.__members__['__T_POINTS__']
        not_valid = ['PU01_AB']
        for sensor_label in T_Points:
            time_data = T_Points[sensor_label]
            if sensor_label not in not_valid:
                # -> create dynamically TProfile object to keep i_hv vs. T curve            
                const_temps = self.__const_temp_list__(time_data)
                if len(const_temps) == 0:
                    continue
                first = min( map(float, const_temps) )
                last = max( map(float, const_temps) )
                bins = int( ((last-first) + TEMP_BIN_OFFSET) )
                #name = 'IT_' + sensor_label
                name = sensor_label
		title = sensor_label
		#title = 'i_hv vs. T for sensor ' + sensor_label
                prof = TProfile(name, title, bins, first - 1.5, last + 1.5, I_HV_MIN, I_HV_MAX)
                if sensor_label not in self.__members__['__IT_HISTOS__']:
                    self.__members__['__IT_HISTOS__'][sensor_label] = None
                self.__members__['__IT_HISTOS__'][sensor_label] = prof

                # -> for each const temp find and integrate hv current
                hvi_bank = self.__find_hvi_histo__(sensor_label)
                if hvi_bank == None:
                    print ' --> Problem, hvi data not found for sensor: ', sensor_label
                    continue

                #######################################################################
                print ' --> Creating IT plot for sensor: ', sensor_label
                #######################################################################

                # -> first get the pair (const_Temp, delta_t)
                bin_pointer = 1
                time_jump = 0
                for time in sorted(time_data):
                    for temp_pair in time_data[time]:
                        const_T = temp_pair[CONST_TEMP]
                        delta_t = temp_pair[TIME_INTERVAL]
                        time_in_bin = hvi_bank.GetBinCenter(bin_pointer)
                        time_jump = time - time_in_bin
                        bin_pointer += int(time_jump)
                        for time_bin in range(bin_pointer, bin_pointer + delta_t):
                            hvi = hvi_bank.GetBinContent(time_bin)
                            if hvi:
                                self.__members__['__IT_HISTOS__'][sensor_label].Fill(const_T, hvi)
                self.__members__['__IT_HISTOS__'][sensor_label].SetStats(kFALSE)
                self.__members__['__IT_HISTOS__'][sensor_label].SetOption("P")
                self.__members__['__IT_HISTOS__'][sensor_label].SetMarkerSize(0.8)
                self.__members__['__IT_HISTOS__'][sensor_label].GetXaxis().SetTitle('Temperature deg')
                self.__members__['__IT_HISTOS__'][sensor_label].GetXaxis().SetLabelSize(0.03)
                self.__members__['__IT_HISTOS__'][sensor_label].GetYaxis().SetTitle('HV current mA')
                self.__members__['__IT_HISTOS__'][sensor_label].GetYaxis().SetLabelSize(0.03)

# 
def time_translator(time):
    ''' Takes time in format HH:MM:SS and translates it to seconds '''
    time_ = time.split(':')
    bin = int(time_[0])*HOUR + int(time_[1])*MINUTE + int(time_[2])

    return ( bin )

#
class VeloDetectorElement():
    """ ------------------------------------------------------------------- """
    """  Can return information regarding sensor number, sensor position    """
    """  and sensor type R = 1, Phi = 0                                     """
    """ ------------------------------------------------------------------- """

    def __init__(self):
        self.__members__ = {
            'class_id'      : 'VeloDetectorElement'
           ,'__Velo_Det__'  : { }
        }
        self.__createMap__()
        self._HV_CHANNEL = 0
        self._SENSOR = 1
        self._Z = 2
        self._SENSOR_TYPE = 3

    def __createMap__(self):
        # -> header data have format as follow: maXX/chXX
        #    map will relate hardware channels with labels and sensors
        # ----------------------
        # -> side C, HV_Board00
        self.__members__['__Velo_Det__']['PU01_CT'] = ['ma06/ch00', 129, -300., 1]
        self.__members__['__Velo_Det__']['PU02_CB'] = ['ma06/ch01', 131, -220., 1]
        self.__members__['__Velo_Det__']['VL01_CT'] = ['ma06/ch02', 65, -160., 0]
        self.__members__['__Velo_Det__']['VL01_CB'] = ['ma06/ch03', 1, -160., 1]
        self.__members__['__Velo_Det__']['VL02_CT'] = ['ma06/ch04', 3, -130., 1]
        self.__members__['__Velo_Det__']['VL02_CB'] = ['ma06/ch05', 67, -130., 0]
        self.__members__['__Velo_Det__']['VL03_CT'] = ['ma06/ch06', 69, -100., 0]
        self.__members__['__Velo_Det__']['VL03_CB'] = ['ma06/ch07', 5, -100., 1]
        # -> side C, HV_Board01
        self.__members__['__Velo_Det__']['VL04_CT'] = ['ma07/ch00', 7, 70., 1]
        self.__members__['__Velo_Det__']['VL04_CB'] = ['ma07/ch01', 71, -70.,0]
        self.__members__['__Velo_Det__']['VL05_CT'] = ['ma07/ch02', 73, -40., 0]
        self.__members__['__Velo_Det__']['VL05_CB'] = ['ma07/ch03', 9, -40., 1]
        self.__members__['__Velo_Det__']['VL06_CT'] = ['ma07/ch04', 11, -10., 1]
        self.__members__['__Velo_Det__']['VL06_CB'] = ['ma07/ch05', 75, -10., 0]
        self.__members__['__Velo_Det__']['VL07_CT'] = ['ma07/ch06', 77, 20., 0]
        self.__members__['__Velo_Det__']['VL07_CB'] = ['ma07/ch07', 13, 20., 1]
        # -> side C, HV_Board02
        self.__members__['__Velo_Det__']['VL08_CT'] = ['ma08/ch00', 15, 50., 1]
        self.__members__['__Velo_Det__']['VL08_CB'] = ['ma08/ch01', 79, 50., 0]
        self.__members__['__Velo_Det__']['VL09_CT'] = ['ma08/ch02', 81, 80., 0]
        self.__members__['__Velo_Det__']['VL09_CB'] = ['ma08/ch03', 17, 80., 1]
        self.__members__['__Velo_Det__']['VL10_CT'] = ['ma08/ch04', 19, 80., 1]
        self.__members__['__Velo_Det__']['VL10_CB'] = ['ma08/ch05', 83, 110., 0]
        self.__members__['__Velo_Det__']['VL11_CT'] = ['ma08/ch06', 85, 140., 0]
        self.__members__['__Velo_Det__']['VL11_CB'] = ['ma08/ch07', 21, 140., 1]
        # -> side C, HV_Board03
        self.__members__['__Velo_Det__']['VL12_CT'] = ['ma09/ch00', 23, 170., 1]
        self.__members__['__Velo_Det__']['VL12_CB'] = ['ma09/ch01', 87, 170., 0]
        self.__members__['__Velo_Det__']['VL13_CT'] = ['ma09/ch02', 89, 200., 0]
        self.__members__['__Velo_Det__']['VL13_CB'] = ['ma09/ch03', 25, 200., 1]
        self.__members__['__Velo_Det__']['VL14_CT'] = ['ma09/ch04', 27, 230., 1]
        self.__members__['__Velo_Det__']['VL14_CB'] = ['ma09/ch05', 91, 230., 0]
        self.__members__['__Velo_Det__']['VL15_CT'] = ['ma09/ch06', 93, 260., 0]
        self.__members__['__Velo_Det__']['VL15_CB'] = ['ma09/ch07', 29, 260., 1]
        # -> side C, HV_Board04
        self.__members__['__Velo_Det__']['VL16_CT'] = ['ma10/ch00', 31, 290., 1]
        self.__members__['__Velo_Det__']['VL16_CB'] = ['ma10/ch01', 95, 290., 0]
        self.__members__['__Velo_Det__']['VL19_CT'] = ['ma10/ch02', 97, 450., 0]
        self.__members__['__Velo_Det__']['VL19_CB'] = ['ma10/ch03', 33, 450., 1]
        self.__members__['__Velo_Det__']['VL22_CT'] = ['ma10/ch04', 35, 600., 1]
        self.__members__['__Velo_Det__']['VL22_CB'] = ['ma10/ch05', 99, 600., 0]
        self.__members__['__Velo_Det__']['VL23_CT'] = ['ma10/ch06', 101, 650., 0]
        self.__members__['__Velo_Det__']['VL23_CB'] = ['ma10/ch07', 37, 650., 1]
        # -> side C, HV_Board05
        self.__members__['__Velo_Det__']['VL24_CT'] = ['ma11/ch00', 39, 700., 1]
        self.__members__['__Velo_Det__']['VL24_CB'] = ['ma11/ch01', 103, 700., 0]
        self.__members__['__Velo_Det__']['VL25_CT'] = ['ma11/ch02', 105, 750., 0]
        self.__members__['__Velo_Det__']['VL25_CB'] = ['ma11/ch03', 41, 750., 1]
        # ----------------------
        # -> side A, HV_Board00
        self.__members__['__Velo_Det__']['PU01_AT'] = ['ma00/ch00', 130, -315., 1]
        self.__members__['__Velo_Det__']['PU02_AB'] = ['ma00/ch01', 128, -235., 1]
        self.__members__['__Velo_Det__']['VL01_AT'] = ['ma00/ch02', 64, -175., 0]
        self.__members__['__Velo_Det__']['VL01_AB'] = ['ma00/ch03', 0, -175., 1]
        self.__members__['__Velo_Det__']['VL02_AT'] = ['ma00/ch04', 2, -145., 1]
        self.__members__['__Velo_Det__']['VL02_AB'] = ['ma00/ch05', 66, -145., 0]
        self.__members__['__Velo_Det__']['VL03_AT'] = ['ma00/ch06', 68, -115., 0]
        self.__members__['__Velo_Det__']['VL03_AB'] = ['ma00/ch07', 4, -115., 1]
        # -> side A, HV_Board01
        self.__members__['__Velo_Det__']['VL04_AT'] = ['ma01/ch00', 6, -85., 1]
        self.__members__['__Velo_Det__']['VL04_AB'] = ['ma01/ch01', 70, -85., 0]
        self.__members__['__Velo_Det__']['VL05_AT'] = ['ma01/ch02', 72, -55., 0]
        self.__members__['__Velo_Det__']['VL05_AB'] = ['ma01/ch03', 8, -55., 1]
        self.__members__['__Velo_Det__']['VL06_AT'] = ['ma01/ch04', 10, -25., 1]
        self.__members__['__Velo_Det__']['VL06_AB'] = ['ma01/ch05', 74, -25., 0]
        self.__members__['__Velo_Det__']['VL07_AT'] = ['ma01/ch06', 76, 5., 0]
        self.__members__['__Velo_Det__']['VL07_AB'] = ['ma01/ch07', 12, 5., 1]
        # -> side A, HV_Board02
        self.__members__['__Velo_Det__']['VL08_AT'] = ['ma02/ch00', 14, 35., 1]
        self.__members__['__Velo_Det__']['VL08_AB'] = ['ma02/ch01', 78, 35., 0]
        self.__members__['__Velo_Det__']['VL09_AT'] = ['ma02/ch02', 80, 65., 0]
        self.__members__['__Velo_Det__']['VL09_AB'] = ['ma02/ch03', 16, 65., 1]
        self.__members__['__Velo_Det__']['VL10_AT'] = ['ma02/ch04', 18, 95., 1]
        self.__members__['__Velo_Det__']['VL10_AB'] = ['ma02/ch05', 82, 95., 0]
        self.__members__['__Velo_Det__']['VL11_AT'] = ['ma02/ch06', 84, 125., 0]
        self.__members__['__Velo_Det__']['VL11_AB'] = ['ma02/ch07', 20, 125., 1]
        # -> side C, HV_Board03
        self.__members__['__Velo_Det__']['VL12_AT'] = ['ma03/ch00', 22, 155., 1]
        self.__members__['__Velo_Det__']['VL12_AB'] = ['ma03/ch01', 86, 155., 0]
        self.__members__['__Velo_Det__']['VL13_AT'] = ['ma03/ch02', 88, 185., 0]
        self.__members__['__Velo_Det__']['VL13_AB'] = ['ma03/ch03', 24, 185., 1]
        self.__members__['__Velo_Det__']['VL14_AT'] = ['ma03/ch04', 26, 215., 1]
        self.__members__['__Velo_Det__']['VL14_AB'] = ['ma03/ch05', 90, 215., 0]
        self.__members__['__Velo_Det__']['VL15_AT'] = ['ma03/ch06', 92, 245., 0]
        self.__members__['__Velo_Det__']['VL15_AB'] = ['ma03/ch07', 28, 245., 1]
        # -> side A, HV_Board04
        self.__members__['__Velo_Det__']['VL16_AT'] = ['ma04/ch00', 30, 275., 1]
        self.__members__['__Velo_Det__']['VL16_AB'] = ['ma04/ch01', 94, 305., 0]
        self.__members__['__Velo_Det__']['VL19_AT'] = ['ma04/ch02', 96, 435., 0]
        self.__members__['__Velo_Det__']['VL19_AB'] = ['ma04/ch03', 32, 435., 1]
        self.__members__['__Velo_Det__']['VL22_AT'] = ['ma04/ch04', 34, 585., 1]
        self.__members__['__Velo_Det__']['VL22_AB'] = ['ma04/ch05', 98, 585., 0]
        self.__members__['__Velo_Det__']['VL23_AT'] = ['ma04/ch06', 100, 635., 0]
        self.__members__['__Velo_Det__']['VL23_AB'] = ['ma04/ch07', 36, 635., 1]
        # -> side A, HV_Board05
        self.__members__['__Velo_Det__']['VL24_AT'] = ['ma05/ch00', 38, 685., 1]
        self.__members__['__Velo_Det__']['VL24_AB'] = ['ma05/ch01', 102, 685., 0]
        self.__members__['__Velo_Det__']['VL25_AT'] = ['ma05/ch02', 104, 735., 0]
        self.__members__['__Velo_Det__']['VL25_AB'] = ['ma05/ch03', 40, 735., 1]

    @property
    def HV_CHANNEL(self):
        return ( self._HV_CHANNEL )

    @property
    def SENSOR(self):
        return ( self._SENSOR )

    @property
    def Z(self):
        return ( self._Z )

    @property
    def SENSOR_TYPE(self):
        return ( self._SENSOR_TYPE )

    # -> translate sensor name to hv module channel
    def sensor_name2hv_channel(self, name):
        return ( self.__members__['__Velo_Det__'][name][self.HV_CHANNEL] )

    # -> get sensor number for a given sensor name
    def sensor_name2sensor_number(self, name):
        return ( self.__members__['__Velo_Det__'][name][self.SENSOR] )

    # -> get z position for a given sensor name
    def sensor_name2sensor_z(self, name):
        return ( self.__members__['__Velo_Det__'][name][self.Z] )

    # -> get sensor type for a given sensor name
    def sensor_name2sensor_type(self, name):
        return ( self.__members__['__Velo_Det__'][name][self.SENSOR_TYPE] )

#
def set_root_env():
    from ROOT import gStyle, gROOT
    gROOT.Reset()
    gROOT.SetStyle('Plain')
    gStyle.SetCanvasColor(10)
    gStyle.SetStatBorderSize(1)
    gStyle.SetFillColor(10)
    gStyle.SetOptStat(1)
    gStyle.SetStatX(0.46)
    gStyle.SetStatY(0.9)
    gStyle.SetTitleYOffset(1.4)
    gStyle.SetPalette(45)
    gStyle.SetMarkerSize(0.8)
    gStyle.SetLineColor(1)
    gStyle.SetLineWidth(1)

#
class FitModel():
    """ ------------------------------------------------------------------- """
    """   Contains:                                                         """
    """             fitting engine for IT scans                             """
    """             ploter (points + fit results                            """
    """             current finder                                          """
    """ ------------------------------------------------------------------- """
    
    def __init__(self):
        self._TMIN = -30.
        self._TMAX = 0.
        self._PARAMS = 3

    @property
    def TMIN(self):
        return ( self._TMIN )

    @TMIN.setter
    def TMIN(self, value):
        self._TMIN = value
        
    @property
    def TMAX(self):
        return ( self._TMAX )

    @TMAX.setter
    def TMAX(self, value):
        self._TMAX = value

    @property
    def PARAMS(self):
        return ( self._PARAMS )

    @PARAMS.setter
    def PARAMS(self, value):
        self._PARAMS = value

    def py_model(self, x, par):
        import math
        # -> model used to fit the data
        factor = ( 1./( 2.*8.6e-5 ) )
        zero_celsius = 273.15
        T = x[0] + zero_celsius
        A = par[0]
        B = par[1]
        E_g = par[2]
        model = A * ( 1 + B * T * T * math.exp(-factor * ( E_g/T ) ) )
        return ( model )

    def prepare_fit(self, fit_name):
        from ROOT import TF1
        fit_model = TF1( fit_name, self.py_model, self.TMIN, self.TMAX, self.PARAMS )
        fit_model.SetParNames('A','B','E_{g}')
        return ( fit_model )
