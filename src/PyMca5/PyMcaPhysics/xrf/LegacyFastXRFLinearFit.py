#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF.
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
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__doc__ = """
Module to perform a fast linear fit on a stack of fluorescence spectra.
"""
import os
import numpy
import logging
from PyMca5.PyMcaMath.linalg import lstsq
from . import ClassMcaTheory
from PyMca5.PyMcaMath.fitting import Gefit
from . import ConcentrationsTool
from PyMca5.PyMcaMath.fitting import SpecfitFuns
from PyMca5.PyMcaIO import ConfigDict
import time

_logger = logging.getLogger(__name__)


class FastXRFLinearFit(object):
    def __init__(self, mcafit=None):
        self._config = None
        if mcafit is None:
            self._mcaTheory = ClassMcaTheory.McaTheory()
        else:
            self._mcaTheory = mcafit

    def setFitConfiguration(self, configuration):
        self._mcaTheory.setConfiguration(configuration)
        self._config = self._mcaTheory.getConfiguration()

    def setFitConfigurationFile(self, ffile):
        if not os.path.exists(ffile):
            raise IOError("File <%s> does not exists" % ffile)
        configuration = ConfigDict.ConfigDict()
        configuration.read(ffile)
        self.setFitConfiguration(configuration)

    def fitMultipleSpectra(self, x=None, y=None, xmin=None, xmax=None,
                           configuration=None, concentrations=False,
                           ysum=None, weight=None, refit=True,
                           livetime=None):
        """
        This method performs the actual fit. The y keyword is the only mandatory input argument.

        :param x: 1D array containing the x axis (usually the channels) of the spectra.
        :param y: 3D array containing the spectra as [nrows, ncolumns, nchannels]
        :param xmin: lower limit of the fitting region
        :param xmax: upper limit of the fitting region
        :param weight: 0 Means no weight, 1 Use an average weight, 2 Individual weights (slow)
        :param concentrations: 0 Means no calculation, 1 Calculate them
        :param refit: if False, no check for negative results. Default is True.
        :livetime: It will be used if not different from None and concentrations
                   are to be calculated by using fundamental parameters with
                   automatic time. The default is None.
        :return: A dictionary with the parameters, uncertainties, concentrations and names as keys.
        """
        if y is None:
            raise RuntimeError("y keyword argument is mandatory!")

        if hasattr(y, "info") and hasattr(y, "data"):
            data = y.data
            mcaIndex = y.info.get("McaIndex", -1)
        else:
            data = y
            mcaIndex = -1

        if x is None:
            if hasattr(y, "info") and hasattr(y, "x"):
                x = y.x[0]

        if livetime is None:
            if hasattr(y, "info"):
                if "McaLiveTime" in y.info:
                    livetime = y.info["McaLiveTime"]
        t0 = time.time()
        if configuration is not None:
            self._mcaTheory.setConfiguration(configuration)
        elif self._config is None:
            raise ValueError("Fit configuration missing")
        else:
            _logger.debug("Setting default configuration")
            self._mcaTheory.setConfiguration(self._config)
        # read the current configuration
        # it is a copy, we can modify it at will
        config = self._mcaTheory.getConfiguration()
        if xmin is None:
            xmin = config['fit']['xmin']
        if xmax is None:
            xmax = config['fit']['xmax']
        toReconfigure = False

        # if concentrations and use times, it needs to be reconfigured
        # without using times and correct later on. If the concentrations
        # are to be calculated from internal standard there is no need to
        # raise an exception either.
        autotime = 0
        liveTimeFactor = 1.0
        if not concentrations:
            # ignore any time information to prevent unnecessary errors when
            # setting the fitting data whithout the time information
            if config['concentrations'].get("useautotime", 0):
                config['concentrations']["useautotime"] = 0
                toReconfigure = True
        elif config["concentrations"]["usematrix"]:
            if config['concentrations'].get("useautotime", 0):
                config['concentrations']["useautotime"] = 0
                toReconfigure = True
        else:
            # we are calculating concentrations from fundamental parameters
            autotime = config['concentrations'].get("useautotime", 0)
            nSpectra = data.size // data.shape[mcaIndex]
            if autotime:
                if livetime is None:
                    txt = "Automatic time requested but no time information provided"
                    raise RuntimeError(txt)
                elif numpy.isscalar(livetime):
                    liveTimeFactor = \
                        float(config['concentrations']["time"]) / livetime
                elif livetime.size == nSpectra:
                    liveTimeFactor = \
                        float(config['concentrations']["time"]) / livetime
                else:
                    raise RuntimeError( \
                        "Number of live times not equal number of spectra")
                config['concentrations']["useautotime"] = 0
                toReconfigure = True

        # use of strategies is not supported for the time being
        strategy = config['fit'].get('strategyflag', 0)
        if strategy:
            raise RuntimeError("Strategies are incompatible with fast fit")

        # background
        if config['fit']['stripflag']:
            if config['fit']['stripalgorithm'] == 1:
                _logger.debug("SNIP")
            else:
                raise RuntimeError("Please use the faster SNIP background")

        if weight is None:
            # dictated by the file
            weight = config['fit']['fitweight']
            if weight:
                # individual pixel weights (slow)
                weightPolicy = 2
            else:
                # No weight
                weightPolicy = 0
        elif weight == 1:
            # use average weight from the sum spectrum
            weightPolicy = 1
            if not config['fit']['fitweight']:
                 config['fit']['fitweight'] = 1
                 toReconfigure = True
        elif weight == 2:
           # individual pixel weights (slow)
            weightPolicy = 2
            if not config['fit']['fitweight']:
                 config['fit']['fitweight'] = 1
                 toReconfigure = True
            weight = 1
        else:
            # No weight
            weightPolicy = 0
            if config['fit']['fitweight']:
                 config['fit']['fitweight'] = 0
                 toReconfigure = True
            weight = 0

        if not config['fit']['linearfitflag']:
            #make sure we force a linear fit
            config['fit']['linearfitflag'] = 1
            toReconfigure = True

        if toReconfigure:
            # we must configure again the fit
            self._mcaTheory.setConfiguration(config)

        if len(data.shape) != 3:
            txt = "For the time being only three dimensional arrays supported"
            raise IndexError(txt)
        elif mcaIndex not in [-1, 2]:
            txt = "For the time being only mca arrays supported"
            raise IndexError(txt)
        else:
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
            elif not concentrations:
                # just one spectrum is enough for the setup
                firstSpectrum = data[0, 0, :]
            else:
                firstSpectrum = data[0, :, :].sum(axis=0, dtype=numpy.float64)

        # make sure we calculate the matrix of the contributions
        self._mcaTheory.enableOptimizedLinearFit()

        # initialize the fit
        # print("xmin = ", xmin)
        # print("xmax = ", xmax)
        # print("firstShape = ", firstSpectrum.shape)
        self._mcaTheory.setData(x=x, y=firstSpectrum, xmin=xmin, xmax=xmax)

        # and initialize the derivatives
        self._mcaTheory.estimate()

        # now we can get the derivatives respect to the free parameters
        # These are the "derivatives" respect to the peaks
        # linearMatrix = self._mcaTheory.linearMatrix

        # but we are still missing the derivatives from the background
        nFree = 0
        freeNames = []
        nFreeBackgroundParameters = 0
        for i, param in enumerate(self._mcaTheory.PARAMETERS):
            if self._mcaTheory.codes[0][i] != ClassMcaTheory.Gefit.CFIXED:
                nFree += 1
                freeNames.append(param)
                if i < self._mcaTheory.NGLOBAL:
                    nFreeBackgroundParameters += 1
        if nFree == 0:
            txt = "No free parameters to be fitted!\n"
            txt += "No peaks inside fitting region?"
            raise ValueError(txt)

        #build the matrix of derivatives
        derivatives = None
        idx = 0
        for i, param in enumerate(self._mcaTheory.PARAMETERS):
            if self._mcaTheory.codes[0][i] == ClassMcaTheory.Gefit.CFIXED:
                continue
            deriv= self._mcaTheory.linearMcaTheoryDerivative(self._mcaTheory.parameters,
                                                             i,
                                                             self._mcaTheory.xdata)
            deriv = numpy.ravel(deriv)
            if derivatives is None:
                derivatives = numpy.zeros((deriv.shape[0], nFree), numpy.float64)
            derivatives[:, idx] = deriv
            idx += 1


        #loop for anchors
        xdata = self._mcaTheory.xdata

        if config['fit']['stripflag']:
            anchorslist = []
            if config['fit']['stripanchorsflag']:
                if config['fit']['stripanchorslist'] is not None:
                    ravelled = numpy.ravel(xdata)
                    for channel in config['fit']['stripanchorslist']:
                        if channel <= ravelled[0]:continue
                        index = numpy.nonzero(ravelled >= channel)[0]
                        if len(index):
                            index = min(index)
                            if index > 0:
                                anchorslist.append(index)
            if len(anchorslist) == 0:
                anchorlist = [0, self._mcaTheory.ydata.size - 1]
            anchorslist.sort()

        # find the indices to be used for selecting the appropriate data
        # if the original x data were not ordered we have a problem
        # TODO: check for original ordering.
        if x is None:
            # we have an enumerated channels axis
            iXMin = xdata[0]
            iXMax = xdata[-1]
        else:
            iXMin = numpy.nonzero(x <= xdata[0])[0][-1]
            iXMax = numpy.nonzero(x >= xdata[-1])[0][0]
        # numpy 1.11.0 returns an array on previous expression
        # and then complains about a future deprecation warning
        # because of using an array and not an scalar in the selection
        if hasattr(iXMin, "shape"):
            if len(iXMin.shape):
                iXMin = iXMin[0]
        if hasattr(iXMax, "shape"):
            if len(iXMax.shape):
                iXMax = iXMax[0]

        dummySpectrum = firstSpectrum[iXMin:iXMax+1].reshape(-1, 1)
        # print("dummy = ", dummySpectrum.shape)

        # allocate the output buffer
        results = numpy.zeros((nFree, nRows, nColumns), numpy.float32)
        uncertainties = numpy.zeros((nFree, nRows, nColumns), numpy.float32)

        #perform the initial fit
        _logger.debug("Configuration elapsed = %f", time.time() - t0)
        t0 = time.time()
        totalSpectra = data.shape[0] * data.shape[1]
        jStep = min(100, data.shape[1])
        if weightPolicy == 2:
            SVD = False
            sigma_b = None
        elif weightPolicy == 1:
            # the +1 is to prevent misbehavior due to weights less than 1.0
            sigma_b = 1 + numpy.sqrt(dummySpectrum)/nPixels
            SVD = True
        else:
            SVD = True
            sigma_b = None
        last_svd = None
        for i in range(0, data.shape[0]):
            #print(i)
            #chunks of nColumns spectra
            if i == 0:
                chunk = numpy.zeros((dummySpectrum.shape[0],
                                     jStep),
                                     numpy.float64)
            jStart = 0
            while jStart < data.shape[1]:
                jEnd = min(jStart + jStep, data.shape[1])
                chunk[:,:(jEnd - jStart)] = data[i, jStart:jEnd, iXMin:iXMax+1].T
                if config['fit']['stripflag']:
                    for k in range(jStep):
                        # obtain the smoothed spectrum
                        background=SpecfitFuns.SavitskyGolay(chunk[:, k],
                                                config['fit']['stripfilterwidth'])
                        lastAnchor = 0
                        for anchor in anchorslist:
                            if (anchor > lastAnchor) and (anchor < background.size):
                                background[lastAnchor:anchor] =\
                                        SpecfitFuns.snip1d(background[lastAnchor:anchor],
                                                           config['fit']['snipwidth'],
                                                           0)
                                lastAnchor = anchor
                        if lastAnchor < background.size:
                            background[lastAnchor:] =\
                                    SpecfitFuns.snip1d(background[lastAnchor:],
                                                       config['fit']['snipwidth'],
                                                       0)
                        chunk[:, k] -= background

                # perform the multiple fit to all the spectra in the chunk
                #print("SHAPES")
                #print(derivatives.shape)
                #print(chunk[:,:(jEnd - jStart)].shape)
                ddict=lstsq(derivatives, chunk[:,:(jEnd - jStart)],
                            sigma_b=sigma_b,
                            weight=weight,
                            digested_output=True,
                            svd=SVD,
                            last_svd=last_svd)
                last_svd = ddict.get('svd', None)
                parameters = ddict['parameters']
                results[:, i, jStart:jEnd] = parameters
                uncertainties[:, i, jStart:jEnd] = ddict['uncertainties']
                jStart = jEnd
        t = time.time() - t0
        _logger.debug("First fit elapsed = %f", t)
        if t > 0.:
            _logger.debug("Spectra per second = %f",
                          data.shape[0]*data.shape[1]/float(t))
        t0 = time.time()

        # cleanup zeros
        # start with the parameter with the largest amount of negative values
        if refit:
            negativePresent = True
        else:
            negativePresent = False
        nFits = 0
        while negativePresent:
            zeroList = []
            #totalNegative = 0
            for i in range(nFree):
                #we have to skip the background parameters
                if i >= nFreeBackgroundParameters:
                    t = results[i] < 0
                    tsum = t.sum()
                    if tsum > 0:
                        zeroList.append((tsum, i, t))
                    #totalNegative += tsum
            #print("totalNegative = ", totalNegative)

            if len(zeroList) == 0:
                negativePresent = False
                continue

            if nFits > (2 * (nFree - nFreeBackgroundParameters)):
                # we are probably in an endless loop
                # force negative pixels
                for item in zeroList:
                    i = item[1]
                    badMask = item[2]
                    results[i][badMask] = 0.0
                    _logger.warning("WARNING: %d pixels of parameter %s forced to zero",
                                    item[0], freeNames[i])
                continue
            zeroList.sort()
            zeroList.reverse()

            badParameters = []
            badParameters.append(zeroList[0][1])
            badMask = zeroList[0][2]
            if 1:
                # prevent and endless loop if two or more parameters have common pixels where they are
                # negative and one of them remains negative when forcing other one to zero
                for i, item in enumerate(zeroList):
                    if item[1] not in badParameters:
                        if item[0] > 0:
                            #check if they have common negative pixels
                            t = badMask * item[-1]
                            if t.sum() > 0:
                                badParameters.append(item[1])
                                badMask = t
            if badMask.sum() < (0.0025 * nPixels):
                # fit not worth
                for i in badParameters:
                    results[i][badMask] = 0.0
                    uncertainties[i][badMask] = 0.0
                    _logger.debug("WARNING: %d pixels of parameter %s set to zero",
                                  badMask.sum(), freeNames[i])
            else:
                _logger.debug("Number of secondary fits = %d", nFits + 1)
                nFits += 1
                A = derivatives[:, [i for i in range(nFree) if i not in badParameters]]
                #assume we'll not have too many spectra
                if data.dtype not in [numpy.float32, numpy.float64]:
                    if data.itemsize < 5:
                        data_dtype = numpy.float32
                    else:
                        data_dtype = numpy.floa64
                else:
                    data_dtype = data.dtype
                try:
                    if data.dtype != data_dtype:
                        spectra = numpy.zeros((int(badMask.sum()), 1 + iXMax - iXMin),
                                          data_dtype)
                        spectra[:] = data[badMask, iXMin:iXMax+1]
                    else:
                        spectra = data[badMask, iXMin:iXMax+1]
                    spectra = spectra.reshape(int(badMask.sum()), -1)
                except TypeError:
                    # in case of dynamic arrays, two dimensional indices are not
                    # supported by h5py
                    spectra = numpy.zeros((int(badMask.sum()), 1 + iXMax - iXMin),
                                          data_dtype)
                    selectedIndices = numpy.nonzero(badMask > 0)
                    tmpData = numpy.zeros((1, 1 + iXMax - iXMin), data_dtype)
                    oldDataRow = -1
                    j = 0
                    for i in range(len(selectedIndices[0])):
                        j = selectedIndices[0][i]
                        if j != oldDataRow:
                            tmpData = data[j]
                            olddataRow = j
                        spectra[i] = tmpData[selectedIndices[1][i], iXMin:iXMax+1]
                spectra = spectra.T
                #
                if config['fit']['stripflag']:
                    for k in range(spectra.shape[1]):
                        # obtain the smoothed spectrum
                        background=SpecfitFuns.SavitskyGolay(spectra[:, k],
                                                config['fit']['stripfilterwidth'])
                        lastAnchor = 0
                        for anchor in anchorslist:
                            if (anchor > lastAnchor) and (anchor < background.size):
                                background[lastAnchor:anchor] =\
                                        SpecfitFuns.snip1d(background[lastAnchor:anchor],
                                                           config['fit']['snipwidth'],
                                                           0)
                                lastAnchor = anchor
                        if lastAnchor < background.size:
                            background[lastAnchor:] =\
                                    SpecfitFuns.snip1d(background[lastAnchor:],
                                                       config['fit']['snipwidth'],
                                                       0)
                        spectra[:, k] -= background
                ddict = lstsq(A, spectra,
                              sigma_b=sigma_b,
                              weight=weight,
                              digested_output=True,
                              svd=SVD)
                idx = 0
                for i in range(nFree):
                    if i in badParameters:
                        results[i][badMask] = 0.0
                        uncertainties[i][badMask] = 0.0
                    else:
                        results[i][badMask] = ddict['parameters'][idx]
                        uncertainties[i][badMask] = ddict['uncertainties'][idx]
                        idx += 1

        if refit:
            t = time.time() - t0
            _logger.debug("Fit of negative peaks elapsed = %f", t)
            t0 = time.time()

        outputDict = {'parameters':results, 'uncertainties':uncertainties, 'names':freeNames}

        if concentrations:
            # check if an internal reference is used and if it is set to auto
            ####################################################
            # CONCENTRATIONS
            cTool = ConcentrationsTool.ConcentrationsTool()
            cToolConf = cTool.configure()
            cToolConf.update(config['concentrations'])

            fitFirstSpectrum = False
            if config['concentrations']['usematrix']:
                _logger.debug("USING MATRIX")
                if config['concentrations']['reference'].upper() == "AUTO":
                    fitFirstSpectrum = True
            elif autotime:
                # we have to calculate with the time in the configuration
                # and correct later on
                cToolConf["autotime"] = 0

            fitresult = {}
            if fitFirstSpectrum:
                # we have to fit the "reference" spectrum just to get the reference element
                mcafitresult = self._mcaTheory.startfit(digest=0, linear=True)
                # if one of the elements has zero area this cannot be made directly
                fitresult['result'] = self._mcaTheory.imagingDigestResult()
                fitresult['result']['config'] = config
                concentrationsResult, addInfo = cTool.processFitResult(config=cToolConf,
                                                    fitresult=fitresult,
                                                    elementsfrommatrix=False,
                                                    fluorates=self._mcaTheory._fluoRates,
                                                    addinfo=True)
                # and we have to make sure that all the areas are positive
                for group in fitresult['result']['groups']:
                    if fitresult['result'][group]['fitarea'] <= 0.0:
                        # give a tiny area
                        fitresult['result'][group]['fitarea'] = 1.0e-6
                config['concentrations']['reference'] = addInfo['ReferenceElement']
            else:
                fitresult['result'] = {}
                fitresult['result']['config'] = config
                fitresult['result']['groups'] = []
                idx = 0
                for i, param in enumerate(self._mcaTheory.PARAMETERS):
                    if self._mcaTheory.codes[0][i] == Gefit.CFIXED:
                        continue
                    if i < self._mcaTheory.NGLOBAL:
                        # background
                        pass
                    else:
                        fitresult['result']['groups'].append(param)
                        fitresult['result'][param] = {}
                        # we are just interested on the factor to be applied to the area to get the
                        # concentrations
                        fitresult['result'][param]['fitarea'] = 1.0
                        fitresult['result'][param]['sigmaarea'] = 1.0
                    idx += 1
            concentrationsResult, addInfo = cTool.processFitResult(config=cToolConf,
                                                    fitresult=fitresult,
                                                    elementsfrommatrix=False,
                                                    fluorates=self._mcaTheory._fluoRates,
                                                    addinfo=True)
            nValues = 1
            if len(concentrationsResult['layerlist']) > 1:
                nValues += len(concentrationsResult['layerlist'])
            nElements = len(list(concentrationsResult['mass fraction'].keys()))
            massFractions = numpy.zeros((nValues * nElements, nRows, nColumns),
                                        numpy.float32)


            referenceElement = addInfo['ReferenceElement']
            referenceTransitions = addInfo['ReferenceTransitions']
            _logger.debug("Reference <%s>  transition <%s>",
                          referenceElement, referenceTransitions)
            if referenceElement in ["", None, "None"]:
                _logger.debug("No reference")
                counter = 0
                for i, group in enumerate(fitresult['result']['groups']):
                    if group.lower().startswith("scatter"):
                        _logger.debug("skept %s", group)
                        continue
                    outputDict['names'].append("C(%s)" % group)
                    if counter == 0:
                        if hasattr(liveTimeFactor, "shape"):
                            liveTimeFactor = liveTimeFactor.reshape(results[nFreeBackgroundParameters+i].shape)
                    massFractions[counter] = liveTimeFactor * \
                        results[nFreeBackgroundParameters+i] * \
                        (concentrationsResult['mass fraction'][group] / \
                         fitresult['result'][group]['fitarea'])
                    counter += 1
                    if len(concentrationsResult['layerlist']) > 1:
                        for layer in concentrationsResult['layerlist']:
                            outputDict['names'].append("C(%s)-%s" % (group, layer))
                            massFractions[counter] = liveTimeFactor * \
                                    results[nFreeBackgroundParameters+i] * \
                                    (concentrationsResult[layer]['mass fraction'][group] / \
                                     fitresult['result'][group]['fitarea'])
                            counter += 1
            else:
                _logger.debug("With reference")
                idx = None
                testGroup = referenceElement+ " " + referenceTransitions.split()[0]
                for i, group in enumerate(fitresult['result']['groups']):
                    if group == testGroup:
                        idx = i
                if idx is None:
                    raise ValueError("Invalid reference:  <%s> <%s>" %\
                                     (referenceElement, referenceTransitions))

                group = fitresult['result']['groups'][idx]
                referenceArea = fitresult['result'][group]['fitarea']
                referenceConcentrations = concentrationsResult['mass fraction'][group]
                goodIdx = results[nFreeBackgroundParameters+idx] > 0
                massFractions[idx] = referenceConcentrations
                counter = 0
                for i, group in enumerate(fitresult['result']['groups']):
                    if group.lower().startswith("scatter"):
                        _logger.debug("skept %s", group)
                        continue
                    outputDict['names'].append("C(%s)" % group)
                    goodI = results[nFreeBackgroundParameters+i] > 0
                    tmp = results[nFreeBackgroundParameters+idx][goodI]
                    massFractions[counter][goodI] = (results[nFreeBackgroundParameters+i][goodI]/(tmp + (tmp == 0))) *\
                                ((referenceArea/fitresult['result'][group]['fitarea']) *\
                                (concentrationsResult['mass fraction'][group]))
                    counter += 1
                    if len(concentrationsResult['layerlist']) > 1:
                        for layer in concentrationsResult['layerlist']:
                            outputDict['names'].append("C(%s)-%s" % (group, layer))
                            massFractions[counter][goodI] = (results[nFreeBackgroundParameters+i][goodI]/(tmp + (tmp == 0))) *\
                                ((referenceArea/fitresult['result'][group]['fitarea']) *\
                                (concentrationsResult[layer]['mass fraction'][group]))
                            counter += 1
            outputDict['concentrations'] = massFractions
            t = time.time() - t0
            _logger.debug("Calculation of concentrations elapsed = %f", t)
            ####################################################
        return outputDict

def getFileListFromPattern(pattern, begin, end, increment=None):
    if type(begin) == type(1):
        begin = [begin]
    if type(end) == type(1):
        end = [end]
    if len(begin) != len(end):
        raise ValueError(\
            "Begin list and end list do not have same length")
    if increment is None:
        increment = [1] * len(begin)
    elif type(increment) == type(1):
        increment = [increment]
    if len(increment) != len(begin):
        raise ValueError(\
            "Increment list and begin list do not have same length")
    fileList = []
    if len(begin) == 1:
        for j in range(begin[0], end[0] + increment[0], increment[0]):
            fileList.append(pattern % (j))
    elif len(begin) == 2:
        for j in range(begin[0], end[0] + increment[0], increment[0]):
            for k in range(begin[1], end[1] + increment[1], increment[1]):
                fileList.append(pattern % (j, k))
    elif len(begin) == 3:
        raise ValueError("Cannot handle three indices yet.")
        for j in range(begin[0], end[0] + increment[0], increment[0]):
            for k in range(begin[1], end[1] + increment[1], increment[1]):
                for l in range(begin[2], end[2] + increment[2], increment[2]):
                    fileList.append(pattern % (j, k, l))
    else:
        raise ValueError("Cannot handle more than three indices.")
    return fileList


def save(result, outputDir, fileRoot=None, tif=False, csv=True):
    from PyMca5.PyMca import ArraySave
    if 'concentrations' in result:
        imageNames = result['names']
        images = numpy.concatenate((result['parameters'],
                                    result['concentrations']), axis=0)
    else:
        images = result['parameters']
        imageNames = result['names']
    nImages = images.shape[0]

    if fileRoot in [None, ""]:
        fileRoot = "images"
    if not os.path.exists(outputDir):
        os.mkdir(outputDir)
    imagesDir = os.path.join(outputDir, "IMAGES")
    if not os.path.exists(imagesDir):
        os.mkdir(imagesDir)
    imageList = [None] * (nImages + len(result['uncertainties']))
    fileImageNames = [None] * (nImages + len(result['uncertainties']))
    j = 0
    for i in range(nImages):
        name = imageNames[i].replace(" ","-")
        fileImageNames[j] = name
        imageList[j] = images[i]
        j += 1
        if not imageNames[i].startswith("C("):
            # fitted parameter
            fileImageNames[j] = "s(%s)" % name
            imageList[j] = result['uncertainties'][i]
            j += 1
    fileName = os.path.join(imagesDir, fileRoot+".edf")
    ArraySave.save2DArrayListAsEDF(imageList, fileName,
                                    labels=fileImageNames)
    if csv:
        ext = '.csv'
    else:
        ext = '.dat'
    fileName = os.path.join(imagesDir, fileRoot+ext)
    ArraySave.save2DArrayListAsASCII(imageList, fileName, csv=csv,
                                     labels=fileImageNames)
    if tif:
        i = 0
        for i in range(len(fileImageNames)):
            label = fileImageNames[i]
            if label.startswith("s("):
                continue
            elif label.startswith("C("):
                mass_fraction = "_" + label[2:-1] + "_mass_fraction"
            else:
                mass_fraction  = "_" + label
            fileName = os.path.join(imagesDir,
                                    fileRoot + mass_fraction + ".tif")
            ArraySave.save2DArrayListAsMonochromaticTiff([imageList[i]],
                                    fileName,
                                    labels=[label],
                                    dtype=numpy.float32)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _logger.setLevel(logging.DEBUG)
    import glob
    import sys
    import getopt
    from PyMca5.PyMca import EDFStack
    options     = ''
    longoptions = ['cfg=', 'outdir=', 'concentrations=', 'weight=', 'refit=',
                   'tif=', #'listfile=',
                   'filepattern=', 'begin=', 'end=', 'increment=',
                   "outfileroot="]
    try:
        opts, args = getopt.getopt(
                     sys.argv[1:],
                     options,
                     longoptions)
    except Exception:
        print(sys.exc_info()[1])
        sys.exit(1)
    fileRoot = ""
    outputDir = None
    refit = None
    fileindex = 0
    filepattern=None
    begin = None
    end = None
    increment=None
    backend=None
    weight=0
    tif=0
    concentrations=0
    for opt, arg in opts:
        if opt in ('--cfg'):
            configurationFile = arg
        elif opt in '--begin':
            if "," in arg:
                begin = [int(x) for x in arg.split(",")]
            else:
                begin = [int(arg)]
        elif opt in '--end':
            if "," in arg:
                end = [int(x) for x in arg.split(",")]
            else:
                end = int(arg)
        elif opt in '--increment':
            if "," in arg:
                increment = [int(x) for x in arg.split(",")]
            else:
                increment = int(arg)
        elif opt in '--filepattern':
            filepattern = arg.replace('"', '')
            filepattern = filepattern.replace("'", "")
        elif opt in '--outdir':
            outputDir = arg
        elif opt in '--weight':
            weight = int(arg)
        elif opt in '--refit':
            refit = int(arg)
        elif opt in '--concentrations':
            concentrations = int(arg)
        elif opt in '--outfileroot':
            fileRoot = arg
        elif opt in ['--tif', '--tiff']:
            tif = int(arg)
    if filepattern is not None:
        if (begin is None) or (end is None):
            raise ValueError(\
                "A file pattern needs at least a set of begin and end indices")
    if filepattern is not None:
        fileList = getFileListFromPattern(filepattern, begin, end, increment=increment)
    else:
        fileList = args
    if refit is None:
        refit = 0
        print("WARNING: --refit=%d taken as default" % refit)
    if len(fileList):
        if (not os.path.exists(fileList[0])) and \
           os.path.exists(fileList[0].split("::")[0]):
            # odo convention to get a dataset form an HDF5
            fname, dataPath = fileList[0].split("::")
            # compared to the ROI imaging tool, this way of reading puts data
            # into memory while with the ROI imaging tool, there is a check.
            if 0:
                import h5py
                h5 = h5py.File(fname, "r")
                dataStack = h5[dataPath][:]
                h5.close()
            else:
                from PyMca5.PyMcaIO import HDF5Stack1D
                # this way reads information associated to the dataset (if present)
                if dataPath.startswith("/"):
                    pathItems = dataPath[1:].split("/")
                else:
                    pathItems = dataPath.split("/")
                if len(pathItems) > 1:
                    scanlist = ["/" + pathItems[0]]
                    selection = {"y":"/" + "/".join(pathItems[1:])}
                else:
                    selection = {"y":dataPath}
                    scanlist = None
                print(selection)
                print("scanlist = ", scanlist)
                dataStack = HDF5Stack1D.HDF5Stack1D([fname],
                                                    selection,
                                                    scanlist=scanlist)
        else:
            dataStack = EDFStack.EDFStack(fileList, dtype=numpy.float32)
    else:
        print("OPTIONS:", longoptions)
        sys.exit(0)
    if outputDir is None:
        print("RESULTS WILL NOT BE SAVED: No output directory specified")
    t0 = time.time()
    fastFit = FastXRFLinearFit()
    fastFit.setFitConfigurationFile(configurationFile)
    print("Main configuring Elapsed = % s " % (time.time() - t0))
    result = fastFit.fitMultipleSpectra(y=dataStack,
                                         weight=weight,
                                         refit=refit,
                                         concentrations=concentrations)
    print("Total Elapsed = % s " % (time.time() - t0))
    if outputDir is not None:
        save(result, outputDir, fileRoot=fileRoot, tif=False)
