#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2019 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__doc__ = """
Module to process a stack of absorption spectra.
"""
import os
import numpy
import h5py
import posixpath
import logging
from PyMca5.PyMca import XASClass
from PyMca5.PyMcaIO import ConfigDict
import time


_logger = logging.getLogger(__name__)


class XASStackBatch(object):
    def __init__(self, analyzer=None):
        if analyzer is None:
            analyzer = XASClass.XASClass()
        self._analyzer = analyzer

    def setConfiguration(self, configuration):
        if "XASParameters" in configuration:
            self._analyzer.setConfiguration(configuration["XASParameters"])
        else:
            self._analyzer.setConfiguration(configuration)

    def setConfigurationFile(self, ffile):
        if not os.path.exists(ffile):
            raise IOError("File <%s> does not exists" % ffile)
        configuration = ConfigDict.ConfigDict()
        configuration.read(ffile)
        self.setConfiguration(configuration)

    def processMultipleSpectra(self, x, y,
                               xmin=None,
                               xmax=None,
                               configuration=None,
                               ysum=None,
                               weight=None,
                               mask=None,
                               directory=None,
                               name=None,
                               entry=None):
        """
        This method performs the actual work.

        :param x: 1D array containing the x axis (usually the channels) of the spectra.
        :param y: 3D array containing the spectra as [nrows, ncolumns, nchannels]
        :param weight: 0 Means no weight, 1 Use an average weight, 2 Individual weights (slow)
        :return: A dictionary with the results as keys.
        """

        t0 = time.time()
        if configuration is not None:
            self._analyzer.setConfiguration(configuration)

        # read the current configuration
        config = self._analyzer.getConfiguration()

        #
        if weight is None:
            # dictated by the current configuration
            pass
        else:
            _logger.warning("WARNING: weight not handled yet")
        weightPolicy = 0 # no weight
        #weightPolicy = 1 # use average weight from the sum spectrum
        #weightPolicy = 2 # individual pixel weights (slow)
        if hasattr(x, "value"):
            # hdf5 dataset
            x = x.value

        if hasattr(y, "info") and hasattr(y, "data"):
            data = y.data
            mcaIndex = y.info.get("McaIndex", -1)
        else:
            data = y
            mcaIndex = -1

        if len(data.shape) != 3:
            txt = "For the time being only three dimensional arrays supported"
            raise IndexError(txt)
        if mcaIndex not in [-1, 2]:
            txt = "For the time being only mca arrays supported"
            raise IndexError(txt)
        firstSpectrum = None
        if ysum is not None:
            firstSpectrum = ysum
        if weightPolicy:
            # if the cumulated spectrum is present it should be better
            nRows = data.shape[0]
            nColumns = data.shape[1]
            nPixels =  nRows * nColumns
            if ysum is not None:
                firstSpectrum = ysum
            elif weightPolicy == 1:
                # we need to calculate the sum spectrum to derive the uncertainties
                totalSpectra = data.shape[0] * data.shape[1]
                jStep = min(5000, data.shape[1])
                ysum = numpy.zeros((data.shape[mcaIndex],), numpy.float64)
                for i in range(0, data.shape[0]):
                    if i == 0:
                        chunk = numpy.zeros((data.shape[0], jStep), numpy.float64)
                    jStart = 0
                    while jStart < data.shape[1]:
                        jEnd = min(jStart + jStep, data.shape[1])
                        ysum += data[i, jStart:jEnd, :].sum(axis=0, dtype=numpy.float64)
                        jStart = jEnd
                firstSpectrum = ysum
            else:
                firstSpectrum = data[0, :, :].sum(axis=0, dtype=numpy.float64)

        if firstSpectrum is None:
            firstSpectrum = data[0, 0, :]
        # TODO: Check if only one X and it is well behaved in order to
        # avoid unnecessary calculation on each spectrum
        self._analyzer.setSpectrum(x, firstSpectrum)
        # initialize the output arrays
        ddict = self._analyzer.processSpectrum()

        # initialize the arrays from the first results
        entry0 = "PyMcaResults"
        usedEnergy = ddict["Energy"]
        usedMu = ddict["Mu"]
        normalizedIdx = (ddict["NormalizedEnergy"] >= ddict["NormalizedPlotMin"]) & \
              (ddict["NormalizedEnergy"] <= ddict["NormalizedPlotMax"])
        normalizedSpectrumX = ddict["NormalizedEnergy"][normalizedIdx]
        normalizedSpectrumY = ddict["NormalizedMu"][normalizedIdx]
        exafsIdx = (ddict["EXAFSKValues"] >= ddict["KMin"]) & \
                   (ddict["EXAFSKValues"] <= ddict["KMax"])
        exafsSpectrumX = ddict["EXAFSKValues"][exafsIdx]
        exafsSpectrumY = ddict["EXAFSNormalized"][exafsIdx]
        xFT = ddict["FT"]["FTRadius"]
        yFT = ddict["FT"]["FTIntensity"]

        if directory is None:
            directory = os.getcwd()
        if name is None:
            name = "XAS_Result"
        fname = os.path.join(directory, name)
        if entry is None:
            entry = posixpath.join("xas_analysis")
        else:
            entry = posixpath.join(entry, "xas_analysis")
        if not fname.endswith(".h5"):
            fname = fname + ".h5"
        out = h5py.File(fname, "w")
        e0Path = posixpath.join(entry, "edge")
        jumpPath = posixpath.join(entry, "jump")
        spectrumXPath = posixpath.join(entry, "spectrum", "energy")
        spectrumYPath = posixpath.join(entry, "spectrum", "mu")
        normalizedXPath = posixpath.join(entry, "normalized", "energy")
        normalizedYPath = posixpath.join(entry, "normalized", "mu")
        exafsXPath = posixpath.join(entry, "exafs", "k")
        exafsYPath = posixpath.join(entry, "exafs", "signal")
        ftXPath = posixpath.join(entry, "FT", "Radius")
        ftYPath = posixpath.join(entry, "FT", "Intensity")
        ftImaginaryPath = posixpath.join(entry, "FT", "Imaginary")

        iXMin = 0
        iXMax = data.shape[-1] - 1
        e0 = out.require_dataset(e0Path,
                                 shape=data.shape[:-1],
                                 dtype=numpy.float32,
                                 chunks=None,
                                 compression=None)
        jump = out.require_dataset(jumpPath,
                                   shape=data.shape[:-1],
                                   dtype=numpy.float32,
                                   chunks=None,
                                   compression=None)
        shape = list(data.shape[:-1]) + [usedEnergy.size]
        spectrumX = out.require_dataset(spectrumXPath,
                                   shape=[usedEnergy.size],
                                   dtype=numpy.float32,
                                   chunks=None,
                                   compression=None)
        spectrumY = out.require_dataset(spectrumYPath,
                                   shape=shape,
                                   dtype=numpy.float32,
                                   chunks=None,
                                   compression=None)
        shape = list(data.shape[:-1]) + [normalizedSpectrumX.size]
        normalizedX = out.require_dataset(normalizedXPath,
                                   shape=[normalizedSpectrumX.size],
                                   dtype=numpy.float32,
                                   chunks=None,
                                   compression=None)
        normalizedY = out.require_dataset(normalizedYPath,
                                   shape=shape,
                                   dtype=numpy.float32,
                                   chunks=None,
                                   compression=None)
        shape = list(data.shape[:-1]) + [exafsSpectrumX.size]
        exafsX = out.require_dataset(exafsXPath,
                                     shape=[exafsSpectrumX.size],
                                     dtype=numpy.float32,
                                     chunks=None,
                                     compression=None)
        exafsY = out.require_dataset(exafsYPath,
                                     shape=shape,
                                     dtype=numpy.float32,
                                     chunks=None,
                                     compression=None)
        shape = list(data.shape[:-1]) + [xFT.size]
        ftX = out.require_dataset(ftXPath,
                                     shape=[xFT.size],
                                     dtype=numpy.float32,
                                     chunks=None,
                                     compression=None)
        ftY = out.require_dataset(ftYPath,
                                     shape=shape,
                                     dtype=numpy.float32,
                                     chunks=None,
                                     compression=None)
        ftImaginary = out.require_dataset(ftImaginaryPath,
                                     shape=shape,
                                     dtype=numpy.float32,
                                     chunks=None,
                                     compression=None)
        spectrumX[:] = ddict["Energy"]
        normalizedX[:] = ddict["NormalizedEnergy"][normalizedIdx]
        exafsX[:] = ddict["EXAFSKValues"][exafsIdx]
        ftX[:] = ddict["FT"]["FTRadius"]

        t0 = time.time()
        totalSpectra = data.shape[0] * data.shape[1]
        jStep = min(100, data.shape[1])
        if weightPolicy == 2:
            SVD = False
            sigma_b = None
        elif weightPolicy == 1:
            # the +1 is to prevent misbehavior due to weights less than 1.0
            sigma_b = 1 + numpy.sqrt(totalSpectra)/nPixels
            SVD = True
        else:
            SVD = True
            sigma_b = None
        last_svd = None
        #for i in range(10):
        for i in range(0, data.shape[0]):
            #print(i)
            #chunks of nColumns spectra
            if i == 0:
                chunk = numpy.zeros((jStep,
                                     iXMax-iXMin+1),
                                     numpy.float64)
            jStart = 0
            j = 0
            while jStart < data.shape[1]:
                jEnd = min(jStart + jStep, data.shape[1])
                #chunk[:,:(jEnd - jStart)] = data[i, jStart:jEnd, iXMin:iXMax+1].T
                spectra  = data[i, jStart:jEnd, iXMin:iXMax+1]
                nSpectra = spectra.shape[0]
                for spectrumNumber in range(nSpectra):
                    if mask is not None:
                        if mask[i, j] == 0:
                            continue
                    self._analyzer.setSpectrum(x, spectra[spectrumNumber])
                    ddict = self._analyzer.processSpectrum()
                    spectrumY[i, j] = ddict["Mu"]
                    e0[i, j] = ddict["Edge"]
                    jump[i, j] = ddict["Jump"]
                    #normalizedX[i, j] = ddict["NormalizedEnergy"][normalizedIdx]
                    normalizedY[i, j] = ddict["NormalizedMu"][normalizedIdx]
                    #exafsX[i, j] = ddict["EXAFSKValues"][exafsIdx]
                    exafsY[i, j] = ddict["EXAFSNormalized"][exafsIdx]
                    #ftX[i, j] = ddict["FT"]["FTRadius"]
                    ftY[i, j] = ddict["FT"]["FTIntensity"]
                    ftImaginary[i, j] = ddict["FT"]["FTImaginary"]
                    j +=1
                jStart = jEnd
        outputDict = {}
        outputDict["names"] = ["Jump", "Edge"]
        output = numpy.zeros((2, e0.shape[0], e0.shape[1]), dtype = e0.dtype)
        output[0, :] = jump.value
        output[1, :] = e0.value
        outputDict["images"] = output
        out.flush()
        out.close()

        t = time.time() - t0
        _logger.debug("First fit elapsed = %f", t)
        _logger.debug("Spectra per second = %f", data.shape[0]*data.shape[1]/float(t))
        t0 = time.time()
        return outputDict

if __name__ == "__main__":
    _logger.setLevel(logging.DEBUG)
    analyzer = XASClass.XASClass()
    instance = XASStackBatch(analyzer=analyzer)
    configurationFile = "test.ini"
    dataFile = h5py.File("testdata.h5", "r")
    for entry in dataFile:
        data = dataFile[entry]["data"]
        energy = dataFile[entry]["energy"]
        break
    instance.setConfigurationFile(configurationFile)
    instance.processMultipleSpectra(energy, data)
    dataFile.close()
