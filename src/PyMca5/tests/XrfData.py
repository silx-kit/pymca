#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2019 European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF by the Software group.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#############################################################################*/
__author__ = "Wout De Nolf"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import numpy
import time
import os
import sys
import numbers


def generateXRFConfig(modfunc=None):
    """
    :param callable modfunc: modify configuration on loading
    :returns: ConfigDict
    """
    from PyMca5.PyMcaDataDir import PYMCA_DATA_DIR as dataDir
    from PyMca5.PyMcaIO import ConfigDict
    configuration = ConfigDict.ConfigDict()
    cfg = os.path.join(dataDir, "Steel.cfg")
    configuration.read(cfg)
    if modfunc is not None:
        modfunc(configuration)
    return configuration


def generateXRFData(nRows=5, nColumns=10, nDet=1, nTimes=3, presetTime=1, same=True):
    """
    :param int nRows:
    :param int nColumns:
    :param int nDet:
    :param int nTimes: number of different live times
    :param int presetTime: exposure time for each spectrum
    :param bool same: same spectrum in all pixels (add pixel index as constant background otherwise)
    :returns: data(nRows, nColumns, nChannels), liveTime(nRows*nColumns)
    """
    from PyMca5.PyMcaDataDir import PYMCA_DATA_DIR as dataDir
    from PyMca5.PyMcaIO import specfilewrapper as specfile
    spe = os.path.join(dataDir, "Steel.spe")
    sf = specfile.Specfile(spe)
    counts = sf[0].mca(1).astype(numpy.int32)
    #counts = numpy.arange(counts.size, dtype=int) # for testing
    data = numpy.zeros((nDet, nRows, nColumns, counts.size), dtype=counts.dtype)
    liveTime = numpy.zeros((nDet, nRows, nColumns), dtype=numpy.float64)
    nTimes *= nDet
    initialTime = presetTime
    mcaIndex = 0
    for i in range(nRows):
        for j in range(nColumns):
            for k in range(nDet):
                if same:
                    data[k, i, j] = counts
                else:
                    data[k, i, j] = counts + mcaIndex*nDet + k
                liveTime[k, i, j] = initialTime * (1 + mcaIndex % nTimes)/float(nTimes)
            mcaIndex += 1
    return data, liveTime


def generate(modfunc=None, **kwargs):
    """
    :param callable modfunc: modify configuration on loading
    :param **kwargs: see `generateXRFData`
    :returns dict: {configuration: ConfigDict,
                    data: ndarray(nDet, nRows, nColumns, nChannels),
                    liveTime: ndarray(nDet, nRows, nColumns),
                    presetTime: number}
    """
    configuration = generateXRFConfig(modfunc=modfunc)
    presetTime = configuration["concentrations"]["time"]
    data, liveTime = generateXRFData(presetTime=presetTime, **kwargs)
    return {'configuration': configuration,
            'data': data,
            'liveTime': liveTime,
            'presetTime': presetTime}


def generateSpecMesh(filename, nmaps=1, **kwargs):
    """
    :param str filename: save data under this name
    :param num nmaps: number of mesh scans
    :param **kwargs: see `generate`
    :returns dict: {filelist: list(str),
                    configuration: ConfigDict,
                    data: ndarray(nDet, nRows, nColumns, nChannels),
                    liveTime: ndarray(nDet, nRows, nColumns),
                    presetTime: number}
    """
    info = generate(**kwargs)
    nDet, nRows, nColumns, nChannels = info['data'].shape
    expoTime = info['presetTime']
    zero = info['configuration']["detector"]["zero"]
    gain = info['configuration']["detector"]["gain"]
    command = 'mesh samy 0 %d %d samz 0 %d %d %g' % \
              (nRows, nRows-1, nColumns, nColumns-1, expoTime)
    if sys.version < "3.0":
        mode = 'wb'
        oparams = {}
    else:
        mode = 'w'
        oparams = {'newline': ''}
    with open(filename, mode, **oparams) as ffile:
        ffile.write("#F %s\n" % filename)
        ffile.write("#D %s\n" % (time.ctime(time.time())))
        ffile.write("\n")
        for scan in range(nmaps):
            ffile.write("#S %d %s\n" % (scan+1, command))
            ffile.write("#D %s\n" % (time.ctime(time.time())))
            ffile.write("#@MCA %16C\n")
            ffile.write("#@CHANN %d %d %d 1\n" % (nChannels, 0, nChannels-1))
            ffile.write("#@CALIB %.7g %.7g %.7g\n" % (zero, gain, 0.0))
            # Live time changes for each spectrum, so this doesn't work:
            #ffile.write("#@CTIME %.7g %.7g %.7g\n" % (preset, live, real))
            ffile.write("#L col row\n")
            for i in range(nRows):
                for j in range(nColumns):
                    ffile.write('%d %d\n' % (j, i))
                    for k in range(nDet):
                        ffile.write(mcaToSpecString(info['data'][k, i, j, :]))
            ffile.write("\n")
    basename = os.path.splitext(os.path.basename(filename))[0]
    path = os.path.dirname(filename)
    cfgname = os.path.join(path, basename+'.cfg')
    info['configuration'].write(cfgname)
    info['filelist'] = [filename]
    return info


def generateEdfMap(filename, fastpulsefraction=0.01, **kwargs):
    """
    Result of a digital pulse processor with fast and slow channel
    for pile-up rejection and paralyzable deadtime.

    :param str filename: save data under this name
    :param num fastpulsefraction: ratio of fast pulse width (in time) over slow pulse width
    :param **kwargs: see `generate`
    :returns dict: {filelist: list(str),
                    configuration: ConfigDict,
                    data: ndarray(nDet, nRows, nColumns, nChannels),
                    liveTime: ndarray(nDet, nRows, nColumns),
                    presetTime: number}
    """
    from PyMca5.PyMcaIO.EdfFile import EdfFile
    info = generate(**kwargs)
    nDet, nRows, nColumns, nChannels = info['data'].shape
    Treal = float(info['configuration']["concentrations"]["time"])
    nstats = 6
    stats = numpy.empty((nRows, nColumns, nDet*nstats),
                        dtype=info['data'].dtype)

    for k in range(nDet):
        # Slow channel  events
        Nslow = info['data'][k, ...].sum(axis=-1)
        LTslow = info['liveTime'][k, ...]
        Rslow = Nslow/Treal
        DTslow = 1-LTslow/Treal
        Rreal = Rslow/LTslow*Treal
        tauslow = -numpy.log(1-DTslow)/Rreal
        # Fast channel events
        taufast = tauslow*fastpulsefraction
        factor = numpy.exp(-Rreal*taufast)
        LTfast = Treal*factor
        #Rfast = Rreal*factor
        #DTfast = 1-Rfast/Rreal
        stats[..., k*nstats+0] = k   # detector index
        stats[..., k*nstats+1] = Nslow  # slow channel events
        stats[..., k*nstats+2] = Rreal  # real count rate (Hz)
        stats[..., k*nstats+3] = Rslow  # slow channel count rate (Hz)
        stats[..., k*nstats+4] = LTfast*1000  # fast channel live time (msec)
        stats[..., k*nstats+5] = DTslow*100  # dead time %

    basename = os.path.splitext(os.path.basename(filename))[0]
    path = os.path.dirname(filename)
    cfgname = os.path.join(path, basename+'.cfg')
    filelist = []
    for i in range(nRows):
        for k in range(nDet):
            filename = os.path.join(path, '{}_xia{:02d}_0001_0000_{:04d}.edf'
                                    .format(basename, k, i))
            edf = EdfFile(filename, 'wb+')
            edf.WriteImage({'time': Treal}, info['data'][k, i, ...])
            edf = None
            filelist.append(filename)
        filename = os.path.join(path, '{}_xiast_0001_0000_{:04d}.edf'.format(basename, i))
        edf = EdfFile(filename, 'wb+')
        edf.WriteImage({'time': Treal}, stats[i, ...])
        edf = None
    info['configuration'].write(cfgname)
    info['filelist'] = sorted(filelist)
    return info


def generateHdf5Map(filename, **kwargs):
    """
    :param str filename: save data under this name
    :param **kwargs: see `generate`
    :returns dict: {filelist: list(str),
                    configuration: ConfigDict,
                    data: ndarray(nDet, nRows, nColumns, nChannels),
                    liveTime: ndarray(nDet, nRows, nColumns),
                    presetTime: number}
    """
    from PyMca5.PyMcaIO import NexusUtils
    info = generate(**kwargs)
    preset_time = info['configuration']["concentrations"]["time"]
    basename = os.path.splitext(os.path.basename(filename))[0]
    path = os.path.dirname(filename)
    cfgname = os.path.join(path, basename+'.cfg')

    with NexusUtils.nxRoot(filename, mode='w') as f:
        entry = NexusUtils.nxEntry(f, basename)
        instrument = NexusUtils.nxInstrument(entry)
        xrf = NexusUtils.nxSubEntry(entry, 'xrf')
        for iDet, (detData, detLT) in enumerate(zip(info['data'], info['liveTime'])):
            name = 'mca{:02}'.format(iDet)
            detector = NexusUtils.nxDetector(instrument, name)
            detector['data'] = detData
            detector['data'].attrs['interpretation'] = 'spectrum'
            xdetector = NexusUtils.nxCollection(xrf, name)
            xdetector['data'] = NexusUtils.h5py.SoftLink(detector['data'].name)
            xdetector['preset_time'] = preset_time
            xdetector['live_time'] = detLT
            xdetector['live_time'].attrs['interpretation'] = 'image'
            xdetector['live_time'].attrs['units'] = 's'
        #nxprocess = NexusUtils.nxProcess(entry, 'fit')
        #NexusUtils.nxProcessConfigurationInit(nxprocess, configdict=info['configuration'])
    info['configuration'].write(cfgname)
    info['filelist'] = [filename]
    return info


def mcaToSpecString(mca):
    """
    :param mca: vector(list or ndarray)
    :returns str: formatted for spec file
    """
    tmpstr = "@A"
    length = len(mca)
    nChanPerLine = 16
    if isinstance(mca[0], numbers.Integral):
        fmt = " %d"
    else:
        fmt = " %.4f"
    for idx in range(0, length, nChanPerLine):
        if idx+nChanPerLine-1 < length:
            for i in range(0, nChanPerLine):
                tmpstr += fmt % mca[idx+i]
            if idx+nChanPerLine != length:
                tmpstr += "\\"
        else:
            for i in range(idx, length):
                tmpstr += fmt % mca[i]
        tmpstr += "\n"
    return tmpstr
