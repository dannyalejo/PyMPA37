#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# import of useful subroutines and libraries
# Plot template versus continuous data and check differences


import os.path
from math import log10

import matplotlib.pyplot as plt
import numpy as np
from obspy.core import Stream, Trace, read
from obspy.core.event import read_events
from obspy.core.inventory import read_inventory
from obspy.core.utcdatetime import UTCDateTime
from obspy.geodetics import gps2dist_azimuth
from obspy.taup import TauPyModel
from obspy.taup.taup_create import build_taup_model


def kilometer2degrees(kilometer, radius=6371):
    """
    Convenience function to convert kilometers to degrees assuming a perfectly
    spherical Earth.

    :type kilometer: float
    :param kilometer: Distance in kilometers
    :type radius: int, optional
    :param radius: Radius of the Earth used for the calculation.
    :rtype: float
    :return: Distance in degrees as a floating point number.
    """
    pi = 3.14159265359
    return kilometer / (2.0 * radius * pi / 360.0)


def calc_timeshift(eve_lat, eve_lon, eve_dep, sta_lat, sta_lon, tlen_bef):
    epi_dist, az, baz = gps2dist_azimuth(eve_lat, eve_lon, sta_lat, sta_lon)
    epi_dist = epi_dist / 1000
    deg = kilometer2degrees(epi_dist)
    model = TauPyModel(model=taup_model)
    arrivals = model.get_travel_times(
        source_depth_in_km=eve_dep, distance_in_degree=deg,
        phase_list=["s", "S"])
    print(arrivals)
    arrS = arrivals[0]
    # correction to be used to evaluate the start time for the template
    origin_time_shift = arrS.time - tlen_bef
    return origin_time_shift


def mag_detect(magt, amaxt, amaxd):
    """
    mag_detect(mag_temp,amax_temp,amax_detect)
    Returns the magnitude of the new detection by using
    the template/detection amplitude trace ratio
    and the magnitude of the template event
    """
    print("magt == ", magt)
    # print "amaxt == ", amaxt
    # print "amaxd == ", amaxd
    amaxr = amaxt / amaxd
    # print "amaxr == ", amaxr
    magd = magt - log10(amaxr)
    print("magd == ", magd)
    return magd


def read_input_par(vfile):
    with open(vfile) as tf:
        data = tf.read().splitlines()
    stations = data[18].split(" ")
    channels = data[19].split(" ")
    networks = data[20].split(" ")
    lowpassf = float(data[21])
    highpassf = float(data[22])
    tlen_bef = float(data[23])
    tlen_aft = float(data[24])
    UTC_prec = int(data[25])
    cont_dir = "./" + data[26] + "/"
    temp_dir = "./" + data[27] + "/"
    ttimes_dir = "./" + data[28] + "/"
    ev_catalog = str(data[29])
    start_det = int(data[30])
    stop_det = int(data[31])
    det_dur = float(data[32])
    taup_model = str(data[33])
    Flag_Save_Figure = int(data[34])
    Flag_Read_Stats = int(data[35])
    return stations, channels, networks, lowpassf, highpassf, tlen_bef,\
        tlen_aft, UTC_prec, cont_dir, temp_dir, ttimes_dir, ev_catalog,\
        start_det, stop_det, det_dur, taup_model, Flag_Save_Figure,\
        Flag_Read_Stats


def read_sta_inv(invfiles, sta):
    for invv in invfiles:
        inv = read_inventory(invv)
        nt0 = inv[0].select(station=sta)
        if bool(nt0):
            lat = nt0[0].latitude
            lon = nt0[0].longitude
            elev = nt0[0].elevation
            return lat, lon, elev


def read_stats(stats_dir, template_num, yymmdd,
               det_ot, ch_name, ch_cmp):
    filestats = "%s%s.%s.stats" % (stats_dir, str(int(template_num)), yymmdd)
    stat = open(filestats, 'r')

    linestart = 0
    linestop = 0
    istop = 0

    for ist, lstat in enumerate(stat):
        lstat = lstat.strip()
        print("lstat == ", lstat)
        print(str(det_ot), lstat)
        if str(det_ot) not in lstat and istop == 0:
            linestart = ist

        elif str(det_ot) in lstat:
            linestop = ist
        istop = 1
    print("1 linestart, linestop == ", linestart, linestop)
    stat.close()
    stat = open(filestats, 'r')

    for ichan, lstat1 in enumerate(stat):
        lstat1 = lstat1.strip()

        if ichan >= linestart and ichan < linestop:
            # print("lstat1 == ", lstat1)
            ch_string = ch_name + ' ' + ch_cmp

            if ch_string in lstat1:
                cols = lstat1.split()
                channel_name = cols[0]
                channel_cmp = cols[1]
                channel_ccros = cols[3]
                channel_nsample = cols[4]

    return channel_name, channel_cmp, channel_ccros, channel_nsample


# read input parameters
vfile = 'verify.par'
[stations, channels, networks, lowpassf, highpassf,
    tlen_bef, tlen_aft, UTC_prec, cont_dir, temp_dir,
    ttimes_dir, ev_catalog, start_det, stop_det, det_dur,
    taup_model, Flag_Save_Figure, Flag_Read_Stats] = read_input_par(vfile)

# generate model for travel times
gen_model = taup_model + '.tvel'
build_taup_model(gen_model)

# set inventory files
invfiles = ["inv.ingv.iv", "inv.ingv.mn"]

# read Template Catalog
cat = read_events(ev_catalog, format="ZMAP")
ncat = len(cat)
aa = np.loadtxt(ev_catalog)
aa1 = aa[:, 9]
aa2 = aa1 - np.floor(aa1)
aa3 = aa2 * 1000000
print("aa1, aa2, aa3 == ", aa1, aa2, aa3)

# read Catalog as output from Phase Match Filtering
dc = np.loadtxt("./outcat")
# catalog format
# 2013 9 5 20 4 58.74 1.01 0.506 11.818 32 40.3127 0.6997 5.0 5.0
# 2013 9 5 21 43 47.35 1.29 0.394 9.816 105 40.3744 0.702 2.0 4.0
# 2013 9 5 22 48 29.78 0.53 0.516 12.095 111 40.4103 0.6947 2.0 4.0
# 2013 9 6 4 11 10.6 0.35 0.458 11.586 109 40.3846 0.7071 3.0 4.0
# 2013 9 6 5 20 10.96 0.57 0.432 9.892 75 40.4049 0.6818 1.0 5.0

dcyy = dc[:, 0]
dcmm = dc[:, 1]
dcdd = dc[:, 2]
dchh = dc[:, 3]
dcmin = dc[:, 4]
dcss = dc[:, 5]
dcmag = dc[:, 6]
dcavcc = dc[:, 7]
dcthre = dc[:, 8]
dctmp = dc[:, 9]
dclat = dc[:, 10]
dclon = dc[:, 11]
dcdep = dc[:, 12]
dcchan = dc[:, 13]

ndet = len(dc[:, 0])

# start loop on detections
for jf, detection_num in enumerate(range(start_det, stop_det)):
    # for jf, detection_num in enumerate(range(85,86)):
    st_temp = Stream()
    st_cont = Stream()
    st1_cont = Stream()

    # read date and time from the detection catalog
    yy = int(dcyy[detection_num])
    mm = int(dcmm[detection_num])
    dd = int(dcdd[detection_num])
    hh = int(dchh[detection_num])
    mmn = int(dcmin[detection_num])
    ss = dcss[detection_num]
    print("ss ==", ss)

    # read UTCDateTime and other detection parameters
    detection_otime = UTCDateTime(yy, mm, dd, hh, mmn, ss)
    detection_daily_otime = detection_otime.timestamp -\
        UTCDateTime(yy, mm, dd, 0, 0, 0, 0).timestamp
    magd = dcmag[detection_num]
    avcc = dcavcc[detection_num]
    thre = dcthre[detection_num]
    template_num = int(dctmp[detection_num])
    chan_num = int(dcchan[detection_num])
    print("template  number == ", template_num)

    # read latitude longitude and depth from the template catalog
    eve_lat = cat[template_num].origins[0].latitude
    eve_lon = cat[template_num].origins[0].longitude
    eve_dep = cat[template_num].origins[0].depth / 1000
    print("eve_lat, eve_lon == ", eve_lat, eve_lon)

    # read time and parameters of template event
    ot = cat[template_num].origins[0].time.datetime
    ot1 = UTCDateTime(ot)
    yyt = ot1.year
    mmt = ot1.month
    ddt = ot1.day
    hht = ot1.hour
    mint = ot1.minute
    sst = ot1.second
    msect = aa3[template_num]
    microsect = int(msect)
    print("aa3[template_num], microsect", aa3[template_num], microsect)
    magt = cat[template_num].magnitudes[0].mag

    template_otime = UTCDateTime(yyt, mmt, ddt, hht, mint, sst, microsect)
    template_daily_otime = template_otime.timestamp -\
        UTCDateTime(yyt, mmt, ddt, 0, 0, 0, 0).timestamp
    print("yyt, mmt, ddt, hht, mint, sst, microsect == ", yyt, mmt,
          ddt, hht, mint, sst, microsect)
    print("detection_daily_otime, template_daily_otime == ",
          detection_daily_otime, template_daily_otime)

    # define useful parameters for the stream of continuous data
    # string name
    sday = str(yy)[2:4] + str(mm).zfill(2) + str(dd).zfill(2)
    # filtering range
    bandpass = [lowpassf, highpassf]

    # load template related waveforms
    stemp_num = str(template_num)
    print("template_num == ", stemp_num)

    # load ttimes
    travel_file = "%s%s.ttimes" % (ttimes_dir, template_num)

    # store ttimes info in a dictionary
    with open(travel_file, "r") as ttim:
        d = dict(x.rstrip().split(None, 1) for x in ttim)
    ttmin = [float(str(x)) for x in d.values()]
    min_time = min(ttmin[:])

    for network in networks:

        for station in stations:

            for channel in channels:
                file = temp_dir + stemp_num + '.' + network + '.' + station +\
                    '..' + channel + '.mseed'
                print('file :' + file)

                if os.path.isfile(file):
                    st_temp += read(file)

    # load 24h continuous waveforms only if template exists
    for tt in st_temp:
        station = tt.stats.station
        channel = tt.stats.channel
        file1 = cont_dir + sday + '.' + station + '.' + channel
        print(" file1 ===", file1)

        if os.path.isfile(file1):
            st_cont += read(file1)
        else:
            # remove from the template stream if continuous not exists
            st_temp.remove(tt)

    st_cont.filter('bandpass', freqmin=bandpass[0], freqmax=bandpass[1],
                   zerophase=True)

    # define variables
    # st1_temp = st_temp.select(channel=channel[0])
    tt = Trace()
    tc = Trace()
    count = 0
    nmin = 0

    npanels = len(st_temp)
    nfile = len(st_temp)
    Tstart = np.empty(nfile)
    Tend = np.empty(nfile)
    tdif = np.empty(nfile)

    plt.rcParams["figure.figsize"] = [16, 9]
    jf, axarray = plt.subplots(npanels, sharex=True)

    count = 0

    for it, tt in enumerate(st_temp):
        count = count + 1
        sstat = tt.stats.station
        print("station == ", sstat)

        # get coordinates from the inventory
        slat, slon, selev = read_sta_inv(invfiles, sstat)
        print("sta_lat, sta_lon === ", eve_lat, eve_lon, eve_dep, slat, slon)


        if Flag_Read_Stats == 1:
            # compute shift from the origin time
            stats_dir = './'
            ch_name = tt.stats.network + '.' + sstat
            ch_cmp = tt.stats.channel
            [ch_id, ch_cmp, ch_ccros, ch_nsamp] = read_stats(
                stats_dir, str(template_num), sday, detection_otime,
                ch_name, ch_cmp)
            # print("ch_ccros, ch_nsamp == ", ch_ccros, ch_nsamp)
            # print("tt.stats.delta = ", tt.stats.delta)
            time_shift = float(ch_nsamp) * tt.stats.delta
        ori = calc_timeshift(eve_lat, eve_lon, eve_dep, slat, slon, tlen_bef)
        # print("ori == ", ori)

        if Flag_Read_Stats == 1:
            ori = ori - time_shift

        # get channel id
        chan = tt.stats.channel
        netwk = tt.stats.network
        idchan = netwk + "." + sstat + ".." + chan
        idchan_dic = netwk + "." + sstat + "." + chan
        print("idchan_dic == ", idchan_dic)

        if st_cont.select(id=idchan).__nonzero__():
            st1_cont = st_cont.select(id=idchan)
            st1_cont.merge()
            print(st1_cont.__str__(extended=True))
            tc = st1_cont[0]
            print("Trace Id.i= ", st1_cont[0])
            tc.trim(starttime=UTCDateTime(detection_otime),
                    endtime=UTCDateTime(detection_otime) + 2 * det_dur,
                    pad=True, nearest_sample=True, fill_value=0)
            print("tc.stats.starttime == ", tc.stats.starttime)
            print("detection_otime == ", UTCDateTime(detection_otime))

            # compute maximum amplitude in the continuous waveforms
            # for magnitude estimation
            ind_tmin = int((ori) / tc.stats.delta) + 1
            ind_tmax = int((ori + 5.0) / tc.stats.delta) + 1

            # set magg to be used as maximum amplitude level in plotting
            # 40s window
            magg = max(tc.data)

            # max of windowed template amplitude
            amaxat = max(abs(tt.data))

            # max of windowed continuous data in the template window
            if tc.data[ind_tmin:ind_tmax].size:
                amaxad = max(abs(tc.data[ind_tmin:ind_tmax]))
            else:
                amaxad = amaxat

            # compute magnitude
            print("amaxat, amaxad == ", amaxat, amaxad)
            amaxmul = amaxad / amaxat
            print("amaxmul == ", amaxmul)
            magd = mag_detect(magt, amaxat, amaxad)
            smagd = str("%4.2f" % magd)
            smagd = "Md=" + smagd + " Mt=" + str(magt)
            mag = amaxad
            tlen = UTCDateTime(detection_otime).timestamp

            # plot tc and tt data
            tad = np.arange(0, (tt.stats.npts / tt.stats.sampling_rate),
                            tt.stats.delta)
            print(tad, tad + ori)
            t = np.arange(0, tc.stats.npts / tc.stats.sampling_rate,
                          tc.stats.delta)
            axarray[count - 1].plot(t, tc.data, 'k', lw=1.0)
            axarray[count - 1].plot(tad + ori, amaxmul * tt.data, 'r', lw=1.5)
            # axarray[count - 1].plot(t, tc.data, 'k', lw=1.0)
            axarray[count - 1].text(det_dur * 1.45, 0.45 * magg,
                                    smagd, fontsize=12)
            if Flag_Read_Stats == 1:
                axarray[count - 1].text(det_dur * 1.85, 0.45 * magg,
                                        'ch_cc = ' + ch_ccros[0:5],
                                        fontsize=12)
            elif Flag_Read_Stats == 0:
                axarray[count - 1].text(det_dur * 1.85, 0.45 * magg,
                                        'avcc = ' + str(avcc)[0:5],
                                        fontsize=12)
            # axarray[count - 1].text(det_dur * 1.45, 0.55 * magg,
            #                         'av_ch_cc/MAD= ' + str(thre)[0:4],
            #                         fontsize=10)
            # axarray[count - 1].text(det_dur, 0.65 * magg, 'template_num=' +
            #                         str(template_num), fontsize=10)
            axarray[count - 1].text(det_dur * 0.05, 0.45 * magg,
                                    tc.stats.station + '.' +
                                    tc.stats.channel, fontsize=12)
            print("det_dur, magg == ", det_dur, magg)

            # uncomment 2 lines below to display template and detection time
            # axarray[count-1].text(det_dur, -0.9*magg, 'template_time=' +
            # str(tt.stats.starttime-ori), fontsize=11)
            # axarray[count-1].text(det_dur*0.05, -0.9*magg,
            #    'detection_time=' + str(detection_otime), fontsize=11)

            on_of = ori + tlen_bef
            axarray[count - 1].axvline(on_of, color='b',
                linewidth=1.8, linestyle='--')
            if count == 1:
                axarray[count - 1].text(det_dur * 0.10, 1.4 * magg,
                                        'Detection = ' + str(detection_num) +
                                        ', ' + 'Template = ' + str(
                                            template_num) + ', DateTime = ' +
                                        str(detection_otime) +
                                        ' av_ch_cc/MAD = ' + str(thre)[0:4],
                                        fontsize=14)
                print("det_dur, magg == ", det_dur, magg)

            plt.xlabel('Time [s]')

            on_of = ori + tlen_bef
            axarray[count - 1].axvline(on_of, color='b',
                linewidth=1.8, linestyle='--')

    if Flag_Save_Figure == 0:
        plt.show()

    if Flag_Save_Figure == 1:
        fig = plt.gcf()
        fig.set_size_inches(15.98, 11.93)
        # print "sfig===", sfig
        outfile = sday + sstat + "." + str(detection_num) +\
            "." + str(template_num).zfill(3) + ".png"
        fig.savefig(outfile, dpi=300)
        fig.clf()
