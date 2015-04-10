##########################################################################
#
# --> This script performs the IT scan 
# @Tomasz Szumlak
# @Agnieszka Mucha
#
# Based on Paula Collins IT scan procedure
#
# @16/04/2012
#
##########################################################################

from ITScanCore import *
from ROOT import TH1F, TCanvas, kFALSE, TFile, TGraphErrors
from array import array
from threading import Thread, Semaphore
from time import clock

DEB_1 = False
DEB_2 = False

root_sys = os.environ.get('ROOTSYS')
if ( root_sys == None ) or ( root_sys == '' ):
    print ' --> I cannot work here... Set the LHCb environment first!'
    sys.exit(1)

# -> set plotting options
#set_root_env()

FIRST = 0
SECOND = 1
LAST = -1
TIME = 0
TEMP = 1
HIST = 0
FIRST_BIN = 1
I_hv = 1
MAX_THREADS = 100

#simple wrappers
def HVCMTarget(hv_mapper):
	#Works as a target for a thread
	print 'Starting hvcm_thread'
	hv_mapper.append(HVChannelMapper())
	print 'Ending hvcm_thread'

def HVCDTarget(hv_decoder, path):
	#Works as a target for a thread
	print 'Starting hvcd_thread'
	hv_decoder.append(HVCurrentDecoder(path))
	print 'Ending hvcd_thread'
	
def TempDTarget(t_decoder, path):
	#Works as a target for a thread
	print 'Starting tempd_thread'
	t_decoder.append(TemperatureDecoder(path))
	print 'Ending tempd_thread'
	
def hv_plots(hv_decoder, hv_histo_list, hv_mapper, opts, semaph_file):
	if hv_decoder.getStatus() == SUCCESS:
		print ' --> the decoder has been initialised correctly '
		print ' --> plotting HV histograms... '
		hvi_data = hv_decoder.getData()
		hv_channels = hvi_data.keys()
		
		# -> book and fill histos
		for channel in sorted(hv_channels):
			hvi_t_points = hvi_data[channel]
		
			# -> define the range, name and title
			time_start = hvi_t_points[0][TIME].split(':')
			time_stop = hvi_t_points[-1][TIME].split(':')
			first_bin = int(time_start[0])*HOUR + int(time_start[1])*MINUTE + int(time_start[2])
			last_bin = int(time_stop[0])*HOUR + int(time_stop[1])*MINUTE + int(time_stop[2])
			name = 'h_' + hv_mapper.HVChannel2Label(channel)
			title = ' HV currents for sensor ' + hv_mapper.HVChannel2Label(channel)
			bins = (last_bin - first_bin)
			histo = TH1F(name, title, bins, first_bin, last_bin)
			histo.SetStats(kFALSE)
			histo.SetOption("P")
			
			# -> fill histograms
			for point in hvi_t_points:
				time_ = point[TIME].split(':')
				bin = int(time_[0])*HOUR + int(time_[1])*MINUTE + int(time_[2])
				histo.SetBinContent((bin - first_bin), round(float(point[HVI]), 5))
				histo.GetXaxis().SetTitle('time [s]')
				histo.GetXaxis().SetLabelSize(0.03)
				histo.GetYaxis().SetTitle('HV current [mA]')
				histo.GetYaxis().SetLabelSize(0.03)
			
			# -> store the histograms
			hv_histo_list[channel] = [ histo, first_bin ]
	
	else:
		print ' --> problem with initialisation! '
	
	for channel in hv_histo_list:
		hist = hv_histo_list[channel][HIST]
		name = hist.GetName()
		#print ' -> Removing zeros in histogram: ', '\033[91m' + name + '\033[0m'
		nbins = hist.GetNbinsX()
		for bin in range(2, nbins):
			temp = hist.GetBinContent(bin)
			if ( temp < 0.0001 and temp > -0.0001 ):
				temp_prev = hist.GetBinContent(bin -1)
				hist.SetBinContent(bin, temp_prev)
		
	
			

		  
def t_plots(t_decoder, T_histo_list, TEMP_DATA, STABLE_TEMP_MEAN_RISING, STABLE_TEMP_MEAN_FALLING, STABLE_TEMP_MEAN, BAD_CHANNELS, hv_decoder, opts, semaph_file):
	
	if t_decoder.getStatus() == SUCCESS:
		print ' --> the decoder has been initialised correctly '
		print ' --> plotting Temp histograms... '
		t_data = t_decoder.getData()
		t_channels = t_data.keys()
		
		for channel in sorted(t_channels):
			if DEB_1:
				print ' -------------- DIAGNOSTIC --------------- '
				print channel
			if channel == 'VL01_CB' and DEB_1:
				points = t_data[channel]
				for point in points:
					if point != 0:
						print point
		
		# -> book and fill histos
		for channel in sorted(t_channels):
			t_t_points = t_data[channel]
			# -> define the range, name and title
			# -> find the first measurement not equal zero for a given sensor
			time_start = t_t_points[0][TIME].split(':')
			first_bin = int(time_start[0])*HOUR + int(time_start[1])*MINUTE + int(time_start[2])
			time_stop = t_t_points[-1][TIME].split(':')
			last_bin = int(time_stop[0])*HOUR + int(time_stop[1])*MINUTE + int(time_stop[2])
			name = 'temp_' + channel
			title = ' Temperatures for sensor ' + channel
			bins = (last_bin - first_bin) + 1000
			histo = TH1F(name, title, bins, first_bin - 499.5, last_bin + 500.5)
			histo.SetStats(kFALSE)
			histo.SetOption("P")            
			
			# -> fill histograms
			for point in t_t_points:                
				time_ = point[TIME].split(':')
				bin = int(time_[0])*HOUR + int(time_[1])*MINUTE + int(time_[2])                
				histo.SetBinContent((bin - first_bin + 499), round(float(point[TEMP]), 2))
				if opts['plot'] and DEB_1:
					print bin,  float(point[TEMP])
				histo.GetXaxis().SetTitle('time [s]')
				histo.GetXaxis().SetLabelSize(0.03)
				histo.GetYaxis().SetTitle('Temperature [deg]')
				histo.GetYaxis().SetLabelSize(0.03)
			
			# -> store the histograms    
			T_histo_list.append(histo)
			
			filtered_lists = []
			consecutive_t_list = []
			###########################
			## --> Pattern recognition
			###########################
			
			for index, point in enumerate(t_t_points):
				if channel == 'VL01_CB' and DEB_1:
					print index, point
				if index == ( len(t_t_points) - 1 ):
					if len(consecutive_t_list) == 0:
						consecutive_t_list.append(point)
						filtered_lists.append(consecutive_t_list)
					else:
						last_entry = consecutive_t_list[-1]
						if int(float(last_entry[TEMP])) == int(float(point[TEMP])):
							consecutive_t_list.append(point)
							filtered_lists.append(consecutive_t_list)
							break
						else:
							filtered_lists.append(consecutive_t_list)
							consecutive_t_list = []
							consecutive_t_list.append(point)
							filtered_lists.append(consecutive_t_list)
							break
				if len(consecutive_t_list) == 0:
					consecutive_t_list.append(point)
					if index == ( len(t_t_points) -1 ):
						filtered_lists.append(consecutive_t_list)
						break
				else:
					last_entry = consecutive_t_list[-1]
					if int(float(last_entry[TEMP])) == int(float(point[TEMP])):
						consecutive_t_list.append(point)
						if index == ( len(t_t_points) -1 ):
							filtered_lists.append(consecutive_t_list)
							break
					else:
						filtered_lists.append(consecutive_t_list)
						consecutive_t_list = []
						consecutive_t_list.append(point)
						if index == ( len(t_t_points) -1 ):
							filtered_lists.append(consecutive_t_list)
							break                            
			TEMP_DATA[channel] = filtered_lists
			if channel == 'VL02_AB' and DEB_1:
				print filtered_lists
			
		###############################
		## --> Filter out oscillations
		###############################
		STABLE_TEMP_DATA = {}
		stable_t_lists = []
		for channel in sorted(TEMP_DATA):
			stable_t_lists = []
			lists = TEMP_DATA[channel]
			for list in lists:
				if len(list) == 1:
					continue
				else:
					stable_t_lists.append(list)
			for index, stable_list in enumerate(stable_t_lists):
				if index != ( len(stable_t_lists) - 1 ):
					next_stable_list = stable_t_lists[index + 1]
					first_t = int( float( stable_list[0][TEMP] ) )
					next_t = int( float( next_stable_list[0][TEMP] ) )
					if first_t == next_t:
						if len( stable_list ) >= len( next_stable_list ):
							stable_t_lists.remove( next_stable_list )
						else:
							stable_t_lists.remove( stable_list )
			STABLE_TEMP_DATA[channel] = stable_t_lists
			# -> reset
			stable_t_lists = []
		
		###########################
		## --> Time ordering
		###########################
		for channel in sorted(STABLE_TEMP_DATA):
			if channel not in BAD_CHANNELS:
				stable_lists = STABLE_TEMP_DATA[channel]
				stable_mean_points = []
				stable_mean_values = []
				stable_mean_points_rising = []
				stable_mean_points_falling = []
				for list in stable_lists:
					mean = 0
					time_start = list[FIRST][TIME]
					time_end = list[LAST][TIME]
					for point in list:
						mean += float( point[TEMP] )
					mean /= len(list)
					temp_range = [time_start, time_end]
					mean_point = [temp_range, round(mean,2)]
					stable_mean_points.append( mean_point )
					stable_mean_values.append( round(mean,2) )
				if len(stable_mean_values) == 0:
					print '--> Detected problems with data on', channel
					sys.exit(1)
				max_mean, pos = max((max_mean, pos) for (pos, max_mean) in enumerate(stable_mean_values))
				put_in_front = False
				for index, mean in enumerate(stable_mean_points):
					if index <= pos:
						stable_mean_points_rising.append(mean)
					else:
						if not put_in_front:
							prev_mean = stable_mean_points[index - 1]
							stable_mean_points_falling.append(prev_mean)
							put_in_front = True
						stable_mean_points_falling.append(mean)
				STABLE_TEMP_MEAN[channel] = stable_mean_points
				STABLE_TEMP_MEAN_RISING[channel] = stable_mean_points_rising
				STABLE_TEMP_MEAN_FALLING[channel] = stable_mean_points_falling
		
	else:
		print ' --> problem with initialisation! '
	
	for hist in T_histo_list:
		name = hist.GetName()
		#print ' -> Removing zeros in histogram: ', '\033[91m' + name + '\033[0m'
		nbins = hist.GetNbinsX()
		non_empty = 0
		found_non_empty = False
		for bin in range(1, nbins):
			temp = hist.GetBinContent(bin)
			if ( temp < 0.0001 and temp > -0.0001 ):
				hist.SetBinContent(bin, -199)
		
	


def __process_and_plot__(opts):
    # -> get mapper object
    czas = clock()
    path = opts['path']
    hv_mapperTemp = []
    hv_decoderTemp = []
    t_decoderTemp = []
    
    semaph_main = Semaphore(MAX_THREADS) #main semaphore
    semphr_syncText = Semaphore(1) #sempahore for synchronizing text output
    semaph_file = Semaphore(1) #sempahore for synchronizing file access
    hvcm_thread = Thread(target=HVCMTarget, args=(hv_mapperTemp,))
    hvcd_thread = Thread(target=HVCDTarget, args=(hv_decoderTemp, path))
    tempd_thread = Thread(target=TempDTarget, args=(t_decoderTemp, path))
    
    hvcm_thread.start()
    hvcd_thread.start()
    tempd_thread.start()
    
    hvcm_thread.join()
    hvcd_thread.join()
    tempd_thread.join()
    
    hv_mapper = hv_mapperTemp[0]
    hv_decoder = hv_decoderTemp[0]
    t_decoder = t_decoderTemp[0]

    hv_histo_list = {}
    #Start hv plots thread 
    hv_plotThread = Thread(target=hv_plots, args=(hv_decoder, hv_histo_list, hv_mapper, opts, semaph_file))
    hv_plotThread.start()

    T_histo_list = []
    TEMP_DATA = {}
    STABLE_TEMP_MEAN_RISING = {}
    STABLE_TEMP_MEAN_FALLING = {}
    STABLE_TEMP_MEAN = {}
    
    BAD_CHANNELS = ['PU02_AT']
    
    t_plotThread = Thread(target=t_plots, args=(t_decoder, T_histo_list, TEMP_DATA, STABLE_TEMP_MEAN_RISING, STABLE_TEMP_MEAN_FALLING, STABLE_TEMP_MEAN, BAD_CHANNELS, hv_decoder, opts, semaph_file))
    t_plotThread.start()
            
    #better to join those threads
    hv_plotThread.join()
    t_plotThread.join()
    
    #write plots to file
    date = hv_decoder.getTDate()
    
    if opts['plot']:
		canvas_list = []
		for canvas in range(6):
			canvas_list.append(TCanvas('hvi_' + str(canvas), ' HV currents vs. time'))
			canvas_list[canvas].Divide(4, 4)
	
		keys = hv_histo_list.keys()
		for cnt, key in enumerate( sorted( keys ) ):
			canvas_list[cnt/CANVAS_HISTO].cd(cnt%CANVAS_HISTO+1)
			histo = hv_histo_list[key][HIST]
			histo.GetYaxis().SetRangeUser(0., 0.25)
			histo.Draw()
		t_canvas_list = []
		for canvas in range(6):
			t_canvas_list.append(TCanvas('t_' + str(canvas), ' Temperatures vs. time'))
			t_canvas_list[canvas].Divide(4, 4)
		
		for cnt, histo in enumerate(T_histo_list):
			t_canvas_list[cnt/CANVAS_HISTO].cd(cnt%CANVAS_HISTO+1)
			histo.GetYaxis().SetRangeUser(-40., 0.)
			histo.Draw()

    f = TFile('hvi_temp_histos_' + date + '.root', 'recreate')
    for key in sorted( hv_histo_list.keys() ):
	histo = hv_histo_list[key][HIST]
	histo.GetYaxis().SetRangeUser(0., 0.25)
	histo.Write()
	
    #date = hv_decoder.getTDate() #dunno if second date is required but it was here before, check if works without this
    for histo in T_histo_list:
        histo.GetYaxis().SetRangeUser(-40., 0.)
        histo.Write()
    f.Close

    if DEB_2:
        for channel in sorted(STABLE_TEMP_MEAN_RISING):
            if channel == 'VL12_CT':
                stable_means_r = STABLE_TEMP_MEAN_RISING[channel]
                for point in stable_means_r:
                    print point
	
    ###########################################
    # --> plot our golden histos i_hv vs. T
    ###########################################
    # -> for given time ranges calculate hv current means
    # -> do it only for the rising edge of each scan
    HV_CURRENTS = {}
    hv_stable_points = []
    mapper = HVChannelMapper()
    for hv_channel in sorted(hv_histo_list):
        hv_data_repo = hv_histo_list[hv_channel][HIST]
        first_bin = hv_histo_list[hv_channel][FIRST_BIN]
        temp_channel = mapper.HVChannel2Label(hv_channel)
        if DEB_2:
            if temp_channel == 'VL12_CT':
                hv_data_repo.Draw()
        if temp_channel not in BAD_CHANNELS:
            if temp_channel in STABLE_TEMP_MEAN_RISING:
                stable_temp_points = STABLE_TEMP_MEAN_RISING[temp_channel]
                for stable_point in stable_temp_points:
                    hv_currents_in_temp_range = []
                    if int(stable_point[TEMP]) >= -30:
                        time_range = stable_point[TIME]
                        time_start = time_translator( time_range[FIRST] )
                        time_end = time_translator( time_range[SECOND] )
                        for bin in range(time_start, time_end):
                            hv_current = hv_data_repo.GetBinContent( bin - first_bin )
                            hv_currents_in_temp_range.append(hv_current)
                        if len(hv_currents_in_temp_range):
                            mean_current = 0
                            for current in hv_currents_in_temp_range:
                                mean_current += current
                            mean_current /= len(hv_currents_in_temp_range)
                        hv_stable_point = [time_range, round(mean_current, 5)]
                        hv_stable_points.append(hv_stable_point)
                HV_CURRENTS[temp_channel] = hv_stable_points
                hv_stable_points = []

    if DEB_2:
        for channel in sorted(HV_CURRENTS):
            if channel == 'VL12_CT':
                hv_points = HV_CURRENTS[channel]
                for hv_point in hv_points:
                    print hv_point

    IT_GRAPH_TEMP_RISING_DATA = {}
    f_it = TFile('IT_histos_' + date + '.root', 'recreate')
    for channel in sorted(HV_CURRENTS):
        filtered_hv_values = []
        filtered_t_values = []
        IT_Graph_data = []
        hv_points = HV_CURRENTS[channel]
        stable_rising_temp_points = STABLE_TEMP_MEAN_RISING[channel]
        for index, point in enumerate(hv_points):
            if point[I_hv] not in filtered_hv_values:
                filtered_hv_values.append( point[I_hv] )
                corresponding_t = [ pt for pt in stable_rising_temp_points if pt[TIME] == point[TIME] ]
                filtered_t_values.append( corresponding_t[FIRST][TEMP] )
        IT_Graph_data.append( filtered_hv_values )
        IT_Graph_data.append( filtered_t_values )
        IT_GRAPH_TEMP_RISING_DATA[channel] = IT_Graph_data
        title = 'IT histo for channel: ' + channel
        last_bin = filtered_t_values[FIRST] - 0.5
        first_bin = filtered_t_values[LAST] + 0.5
        n = len( filtered_t_values )
        if DEB_2:
            print 'last temp. bin: ', last_bin, ', first temp. bin: ', first_bin 
        it_hist = TH1F(channel, title, (n + 1), last_bin,  first_bin)
        for index, hv_value in enumerate(filtered_hv_values):
            it_hist.SetBinContent(index + 2, hv_value)
        it_hist.Write()        
        if DEB_2:
            if channel == 'VL12_CT':
                it_hist.Draw()

    f_it.Close()

    if DEB_2:
        for channel in IT_GRAPHS_TEMP_RISING:
            if channel == 'VL12_CT':
                IT_points = IT_GRAPHS_TEMP_RISING[channel]
                hv_points = IT_points[FIRST]
                t_points = IT_points[SECOND]
                for index, temp in enumerate(t_points):
                    print 'point: ', index, 'temp: ', temp, 'i_hv: ', hv_points[index]

    IT_GRAPHS = {}
    data_2_plot = 0
    IT_GRAPHS = {}
    for channel in sorted(IT_GRAPH_TEMP_RISING_DATA):
        ############################################################
        # -> first level of filtering to create IT graphs
        #    if the next i_hv is lower than the current i_hv value
        #    discard it and the rest of the data
        ############################################################
        raw_hv = IT_GRAPH_TEMP_RISING_DATA[channel][FIRST]
        raw_t = IT_GRAPH_TEMP_RISING_DATA[channel][SECOND]
        # -> filtered arrays
        f_hv = []
        f_t = []
        # -> remove very small leakage currents
        for index, hv in enumerate( raw_hv ):
            if abs( hv ) < 0.01:
                continue
            else:
                f_hv.append( raw_hv[index] )
                f_t.append( raw_t[index] )
        for index, hv in enumerate( sorted( f_hv ) ):
            if index < ( len( f_hv ) - 1 ):
                if f_hv[index + 1] - f_hv[index] < 0:
                    delta_percent = 100* abs( ( f_hv[index + 1] - f_hv[index] )/f_hv[index] )
                    if delta_percent > 7.:
                        data_2_plot = index
                        break
                    else:
                        continue
            else:
                data_2_plot = index
        # -> for the moment only placeholders are present...
        err_t = array( 'f', [ err_x * 0. for err_x in range( data_2_plot )] )
        err_i_hv = array( 'f', [ err_x * 0. for err_x in range( data_2_plot )] )
        if DEB_2:
           print 'filered points: ', data_2_plot, ', channel: ', channel, ', data size: ', len(f_hv)
        if data_2_plot == len( f_hv ):
            # -> no problem detected, plot all points
            t = array( 'f', f_t )
            i_hv = array( 'f', f_hv )
            gr = TGraphErrors( data_2_plot, t, i_hv, err_t, err_i_hv )
            gr.SetTitle( 'IT graph for sensor: ' + channel )
            gr_name = 'IT_' + channel
            gr.SetName( gr_name )
            gr.SetMarkerColor( 1 )
            gr.SetMarkerStyle( 21 )
            IT_GRAPHS[channel] = gr
        else:
            if data_2_plot:
                # -> some of the points were removed
                t = array( 'f', [ t for index, t in enumerate( f_t ) if index < data_2_plot ] )
                i_hv = array( 'f', [ i_hv for index, i_hv in enumerate( f_hv ) if index < data_2_plot ] )
                gr = TGraphErrors( data_2_plot, t, i_hv, err_t, err_i_hv )
                gr.SetTitle( 'IT graph for sensor: ' + channel )
                gr_name = 'IT_' + channel
                gr.SetName( gr_name )
                gr.SetMarkerColor( 1 )
                gr.SetMarkerStyle( 21 )
                IT_GRAPHS[channel] = gr
        data_2_plot = 0
    
    czas2 = clock()
    totaltime = czas2 - czas
    print totaltime
    # -> FIT
    from ROOT import Double
    FIT_LIBRARY = {}
    fit_engine = FitModel()
    TMIN = Double(0.0)
    TMAX = Double(0.0)
    I_hv_MIN = Double(0.0)
    I_hv_MAX = Double(0.0)
    for channel in IT_GRAPHS:
        IT_GRAPHS[channel].ComputeRange(TMIN, TMAX, I_hv_MIN, I_hv_MAX)
        fit_engine.TMIN = TMIN
        fit_engine.TMAX = TMAX
        FIT_LIBRARY[channel] = fit_engine.prepare_fit('fit_' + channel)
        IT_GRAPHS[channel].Fit(FIT_LIBRARY[channel], 'rmq')
        if channel == 'VL05_CT':
            IT_GRAPHS[channel].Draw('AZP')
            FIT_LIBRARY[channel].Draw('SAME')

    
    # --> keep the interpreter on...
    rep = raw_input( 'Press ENTER to finish ' )

    # -> order them - first A type then C ones, this creates a root file
    #    that contains filtered graphs with measured leakage current vs. temp
    g_it = TFile('IT_graphs_' + date + '.root', 'recreate')
    for channel in sorted( IT_GRAPHS ):
        if 'A' in channel:
            name = IT_GRAPHS[channel].GetName()
            IT_GRAPHS[channel].Write(name)
        else:
            continue
            
    for channel in sorted( IT_GRAPHS ):
        if 'C' in channel:
            name = IT_GRAPHS[channel].GetName()
            IT_GRAPHS[channel].Write(name)
        else:
            continue
    g_it.Close()            
