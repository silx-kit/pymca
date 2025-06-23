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
import time
import h5py
import collections
from . import ClassMcaTheory
from . import ConcentrationsTool
from PyMca5.PyMcaMath.linalg import lstsq
from PyMca5.PyMcaMath.fitting import Gefit
from PyMca5.PyMcaMath.fitting import SpecfitFuns
from PyMca5.PyMcaIO import ConfigDict
from .XRFBatchFitOutput import OutputBuffer
from PyMca5.PyMcaCore import McaStackView

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
        if not os.path.exists(ffile.split('::')[0]):
            raise IOError("File <%s> does not exists" % ffile)
        configuration = ConfigDict.ConfigDict()
        configuration.read(ffile)
        self.setFitConfiguration(configuration)

    def fitMultipleSpectra(self, x=None, y=None, xmin=None, xmax=None,
                           configuration=None, concentrations=False,
                           ysum=None, weight=None, refit=True, livetime=None,
                           outbuffer=None, save=True, **outbufferinitargs):
        """
        This method performs the actual fit. The y keyword is the only mandatory input argument.

        :param x: 1D array containing the x axis (usually the channels) of the spectra.
        :param y: nD array containing the spectra
        :param xmin: lower limit of the fitting region
        :param xmax: upper limit of the fitting region
        :param ysum: sum spectrum
        :param weight: 0 Means no weight, 1 Use an average weight, 2 Individual weights (slow)
        :param concentrations: 0 Means no calculation, 1 Calculate elemental concentrations
        :param refit: if False, no check for negative results. Default is True.
        :param livetime: It will be used if not different from None and concentrations
                         are to be calculated by using fundamental parameters with
                         automatic time. The default is None.
        :param outbuffer:
        :param save: set to False to postpone saving the in-memory buffers
        :return OutputBuffer: works like a dict
        """
        # Parse data
        x, data, mcaIndex, livetime = self._fitParseData(x=x, y=y,
                                                         livetime=livetime)

        # Calculation needs buffer for memory allocation (memory or H5)
        if outbuffer is None:
            outbuffer = OutputBuffer(**outbufferinitargs)
        with outbuffer.Context(save=save):
            t0 = time.time()

            # Configure fit
            nSpectra = data.size // data.shape[mcaIndex]
            configorg, config, weight, weightPolicy, \
            autotime, liveTimeFactor = self._fitConfigure(
                                                configuration=configuration,
                                                concentrations=concentrations,
                                                livetime=livetime,
                                                weight=weight,
                                                nSpectra=nSpectra)
            outbuffer['configuration'] = configorg

            # Sum spectrum
            if ysum is None:
                if weightPolicy == 1:
                    # we need to calculate the sum spectrum
                    # to derive the uncertainties
                    sumover = 'all'
                elif not concentrations:
                    # one spectrum is enough
                    sumover = 'first pixel'
                else:
                    sumover = 'first vector'
                yref = self._fitReferenceSpectrum(data=data, mcaIndex=mcaIndex,
                                                  sumover=sumover)
            else:
                yref = ysum

            # Force fit limits to be used, whether the user enabled it or not.
            config['fit']['use_limit'] = 1

            # Get the basis of the linear models (i.e. derivative to peak areas)
            dtypeCalculcation = self._fitDtypeCalculation(data)
            self._mcaTheory.setData(x=x, y=yref, xmin=xmin, xmax=xmax)
            derivatives, freeNames, nFree, nFreeBkg = self._fitCreateModel(dtype=dtypeCalculcation)

            # Background anchor points (if any)
            anchorslist = self._fitBkgAnchorList(config=config)

            # MCA trimming: [iXMin:iXMax]
            iXMin, iXMax = self._fitMcaTrimInfo(x=x)
            sliceChan = slice(iXMin, iXMax)
            nObs = iXMax-iXMin

            # Least-squares parameters
            if weightPolicy == 2:
                # Individual spectrum weights (assumed Poisson)
                SVD = False
                sigma_b = None
            elif weightPolicy == 1:
                # Average weight from sum spectrum (assume Poisson)
                # the +1 is to prevent misbehavior due to weights less than 1.0
                sigma_b = 1 + numpy.sqrt(yref[sliceChan])/nSpectra
                sigma_b = sigma_b.reshape(-1, 1)
                SVD = True
            else:
                # No weights
                SVD = True
                sigma_b = None
            lstsq_kwargs = {'svd': SVD, 'sigma_b': sigma_b, 'weight': weight}

            # Allocate output buffers
            stackShape = data.shape
            imageShape = list(stackShape)
            imageShape.pop(mcaIndex)
            imageShape = tuple(imageShape)
            paramShape = (nFree,) + imageShape
            dtypeResult = self._fitDtypeResult(data)
            dataAttrs = {}  #{'units':'counts'})
            paramAttrs = {'errors': 'uncertainties',
                          'default': not concentrations}
            results = outbuffer.allocateMemory('parameters',
                                                shape=paramShape,
                                                dtype=dtypeResult,
                                                labels=freeNames,
                                                dataAttrs=dataAttrs,
                                                groupAttrs=paramAttrs,
                                                memtype='ram')
            uncertainties = outbuffer.allocateMemory('uncertainties',
                                                shape=paramShape,
                                                dtype=dtypeResult,
                                                labels=freeNames,
                                                dataAttrs=dataAttrs,
                                                groupAttrs=None,
                                                memtype='ram')
            fitAttrs = {}
            if outbuffer.saveDataDiagnostics:
                # Generic axes
                dataAxesNames = ['dim{}'.format(i) for i in range(data.ndim)]
                dataAxes = [(name, numpy.arange(n, dtype=dtypeResult), {})
                            for name, n in zip(dataAxesNames, stackShape)]
                # MCA axis: use energy and add channels as extra (unused) axis
                xdata = self._mcaTheory.xdata0.flatten()
                zero, gain = self._mcaTheory.parameters[:2]
                xenergy = zero + gain*xdata
                dataAxesNames[mcaIndex] = 'energy'
                dataAxes[mcaIndex] = 'energy', xenergy.astype(dtypeResult), {'units': 'keV'}
                dataAxes.append(('channels', xdata.astype(numpy.float32), {}))
                fitAttrs['axes'] = dataAxes
                fitAttrs['axesused'] = dataAxesNames

            if outbuffer.saveDataDiagnostics:
                derivAttrs = {}
                derivAttrs['axes'] = [('energy', xenergy.astype(dtypeResult), {'units': 'keV'}),
                                      ('channels', xdata.astype(numpy.float32), {})]
                derivAttrs['axesused'] = ["energy"]
                _derivatives = outbuffer.allocateMemory('derivatives',
                                        shape=(nFree, xdata.size),
                                        dtype=derivatives.dtype,
                                        fill_value=numpy.nan,
                                        labels=freeNames,
                                        dataAttrs=dataAttrs,
                                        groupAttrs=derivAttrs,
                                        memtype='ram')
                _derivatives[:, iXMin:iXMax] = derivatives.T

            dataAttrs = {}
            if outbuffer.saveFOM:
                nFreeParameters = outbuffer.allocateMemory('nFreeParameters',
                                                           group='diagnostics',
                                                           shape=imageShape,
                                                           fill_value=nFree,
                                                           dtype=numpy.int32,
                                                           dataAttrs=dataAttrs,
                                                           groupAttrs=None,
                                                           memtype='ram')
                nObservations = outbuffer.allocateMemory('nObservations',
                                                         group='diagnostics',
                                                         shape=imageShape,
                                                         fill_value=nObs,
                                                         dtype=numpy.int32,
                                                         dataAttrs=dataAttrs,
                                                         groupAttrs=None,
                                                         memtype='ram')
            else:
                nFreeParameters = None
            if outbuffer.saveFit:
                fitmodel = outbuffer.allocateMemory('model',
                                                    group='fit',
                                                    shape=stackShape,
                                                    dtype=dtypeResult,
                                                    chunks=True,
                                                    fill_value=0,
                                                    dataAttrs=dataAttrs,
                                                    groupAttrs=fitAttrs,
                                                    memtype='hdf5')
                idx = [slice(None)]*fitmodel.ndim
                idx[mcaIndex] = slice(0, iXMin)
                fitmodel[tuple(idx)] = numpy.nan
                idx[mcaIndex] = slice(iXMax, None)
                fitmodel[tuple(idx)] = numpy.nan
            else:
                fitmodel = None

            _logger.debug("Configuration elapsed = %f", time.time() - t0)
            t0 = time.time()

            # Fit all spectra
            self._fitLstSqAll(data=data, sliceChan=sliceChan, mcaIndex=mcaIndex,
                            derivatives=derivatives, fitmodel=fitmodel,
                            results=results, uncertainties=uncertainties,
                            config=config, anchorslist=anchorslist,
                            lstsq_kwargs=lstsq_kwargs)

            t = time.time() - t0
            _logger.debug("First fit elapsed = %f", t)
            if t > 0.:
                _logger.debug("Spectra per second = %f",
                              numpy.prod(imageShape)/float(t))
            t0 = time.time()

            # Refit spectra with negative peak areas
            if refit:
                self._fitLstSqNegative(data=data, sliceChan=sliceChan, mcaIndex=mcaIndex,
                            derivatives=derivatives, fitmodel=fitmodel,
                            results=results, uncertainties=uncertainties,
                            config=config, anchorslist=anchorslist,
                            lstsq_kwargs=lstsq_kwargs, freeNames=freeNames,
                            nFreeBkg=nFreeBkg, nFreeParameters=nFreeParameters)
                t = time.time() - t0
                _logger.debug("Fit of negative peaks elapsed = %f", t)
                t0 = time.time()

            # Return results as a dictionary
            if outbuffer.saveData:
                outbuffer.allocateMemory('data',
                                     group='fit',
                                     data=data,
                                     dtype=dtypeResult,
                                     chunks=True,
                                     dataAttrs=dataAttrs,
                                     groupAttrs=fitAttrs,
                                     memtype='hdf5')
            if outbuffer.saveResiduals:
                residuals = outbuffer.allocateMemory('residuals',
                                                 group='fit',
                                                 data=data,
                                                 dtype=dtypeResult,
                                                 chunks=True,
                                                 dataAttrs=dataAttrs,
                                                 groupAttrs=fitAttrs,
                                                 memtype='hdf5')
                residuals[()] -= fitmodel

            if concentrations:
                t0 = time.time()
                labels, concentrations = self._fitDeriveMassFractions(config=config,
                                             nFreeBkg=nFreeBkg,
                                             results=results,
                                             autotime=autotime,
                                             liveTimeFactor=liveTimeFactor)
                dataAttrs = {}  #{'units':'dimensionless'})
                massfracAttrs = {'default': True}
                outbuffer.allocateMemory('massfractions',
                                         data=concentrations,
                                         labels=labels,
                                         dataAttrs=dataAttrs,
                                         groupAttrs=massfracAttrs,
                                         memtype='ram')
                t = time.time() - t0
                _logger.debug("Calculation of concentrations elapsed = %f", t)
            return outbuffer

    @staticmethod
    def _fitParseData(x=None, y=None, livetime=None):
        """Parse the input data (MCA and livetime)
        """
        # Extract counts
        if y is None:
            raise RuntimeError("y keyword argument is mandatory!")
        if hasattr(y, "info") and hasattr(y, "data"):
            data = y.data
            mcaIndex = y.info.get("McaIndex", -1)
        else:
            data = y
            mcaIndex = -1

        # Extract channels
        if x is None:
            if hasattr(y, "info") and hasattr(y, "x"):
                x = y.x[0]
        if livetime is None:
            if hasattr(y, "info"):
                if "McaLiveTime" in y.info:
                    livetime = y.info["McaLiveTime"]

        # At least 2D
        ndim = data.ndim
        if ndim == 0:
            shape = (1, 1)
        elif ndim == 1:
            shape = (1, data.size)
        else:
            shape = None
        if shape is not None:
            data = data.reshape(shape)
            if livetime is not None:
                livetime = livetime.reshape(shape)

        return x, data, mcaIndex, livetime

    def _fitConfigure(self, configuration=None, concentrations=False,
                      livetime=None, weight=None, nSpectra=None):
        """Prepare configuration for fitting
        """
        if configuration is not None:
            self._mcaTheory.setConfiguration(configuration)
        elif self._config is None:
            raise ValueError("Fit configuration missing")
        else:
            _logger.debug("Setting default configuration")
            self._mcaTheory.setConfiguration(self._config)
        # read the current configuration
        # it is a copy, we can modify it at will
        configorg = self._mcaTheory.getConfiguration()
        config = self._mcaTheory.getConfiguration()
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
                    raise RuntimeError(
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
            # make sure we force a linear fit
            config['fit']['linearfitflag'] = 1
            toReconfigure = True

        if toReconfigure:
            # we must configure again the fit
            self._mcaTheory.setConfiguration(config)

        # make sure we calculate the matrix of the contributions
        self._mcaTheory.enableOptimizedLinearFit()

        return configorg, config, weight, weightPolicy, \
               autotime, liveTimeFactor

    def _fitReferenceSpectrum(self, data=None, mcaIndex=None, sumover='all'):
        """Get sum spectrum
        """
        dtype = self._fitDtypeCalculation(data)
        if sumover == 'all':
            nMca = 20, 'MB'
            _logger.debug('Add spectra in chunks of {}'.format(nMca))
            datastack = McaStackView.FullView(data, mcaAxis=mcaIndex, nMca=nMca)
            yref = numpy.zeros((data.shape[mcaIndex],), dtype)
            for key, chunk in datastack.items():
                yref += chunk.sum(axis=0, dtype=dtype)
        elif sumover == 'first vector':
            # Sum spectrum of the first row
            ndim = data.ndim
            idx = [0]*ndim
            while mcaIndex < 0:
                mcaIndex += ndim
            idx[mcaIndex] = slice(None)
            for axis in range(data.ndim-1, -1, -1):
                if idx[axis] != slice(None):
                    idx[axis] = slice(None)
                    break
            axis = int(axis > mcaIndex)
            yref = data[tuple(idx)].sum(axis=axis, dtype=dtype)
        else:
            # First spectrum
            idx = [0]*data.ndim
            idx[mcaIndex] = slice(None)
            yref = data[tuple(idx)].astype(dtype)
        return yref

    def _fitCreateModel(self, dtype=None):
        """Get linear model for fitting
        """
        # Initialize the derivatives
        self._mcaTheory.estimate()

        # now we can get the derivatives respect to the free parameters
        # These are the "derivatives" respect to the peaks
        # linearMatrix = self._mcaTheory.linearMatrix

        # but we are still missing the derivatives from the background
        nFree = 0
        freeNames = []
        nFreeBkg = 0
        for iParam, param in enumerate(self._mcaTheory.PARAMETERS):
            if self._mcaTheory.codes[0][iParam] != ClassMcaTheory.Gefit.CFIXED:
                nFree += 1
                freeNames.append(param)
                if iParam < self._mcaTheory.NGLOBAL:
                    nFreeBkg += 1
        if nFree == 0:
            txt = "No free parameters to be fitted!\n"
            txt += "No peaks inside fitting region?"
            raise ValueError(txt)

        # build the matrix of derivatives
        derivatives = None
        idx = 0
        for iParam, param in enumerate(self._mcaTheory.PARAMETERS):
            if self._mcaTheory.codes[0][iParam] == ClassMcaTheory.Gefit.CFIXED:
                continue
            deriv = self._mcaTheory.linearMcaTheoryDerivative(self._mcaTheory.parameters,
                                                              iParam,
                                                              self._mcaTheory.xdata)
            deriv.shape = -1
            if derivatives is None:
                derivatives = numpy.zeros((deriv.shape[0], nFree), dtype=dtype)
            derivatives[:, idx] = deriv
            idx += 1

        return derivatives, freeNames, nFree, nFreeBkg

    def _fitBkgAnchorList(self, config=None):
        """Get anchors for background subtraction
        """
        xdata = self._mcaTheory.xdata  # trimmed
        if config['fit']['stripflag']:
            anchorslist = []
            if config['fit']['stripanchorsflag']:
                if config['fit']['stripanchorslist'] is not None:
                    ravelled = numpy.ravel(xdata)
                    for channel in config['fit']['stripanchorslist']:
                        if channel <= ravelled[0]:
                            continue
                        index = numpy.nonzero(ravelled >= channel)[0]
                        if len(index):
                            index = min(index)
                            if index > 0:
                                anchorslist.append(index)
            if len(anchorslist) == 0:
                anchorslist = [0, self._mcaTheory.ydata.size - 1]
            anchorslist.sort()
        else:
            anchorslist = None
        return anchorslist

    def _fitMcaTrimInfo(self, x=None):
        """Start and end channels for MCA trimming
        """
        xdata = self._mcaTheory.xdata

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
        return iXMin, iXMax+1

    def _dataChunkIter(self, slicecls, data=None, fitmodel=None, **kwargs):
        dtype = self._fitDtypeResult(data)
        datastack = slicecls(data, dtype=dtype,
                             readonly=True, **kwargs)
        chunkItems = datastack.items(keyType='select')
        if fitmodel is not None:
            modelstack = slicecls(fitmodel, dtype=dtype,
                                  readonly=False, **kwargs)
            modeliter = modelstack.items()
            chunkItems = McaStackView.izipChunkItems(chunkItems, modeliter)
        return chunkItems

    def _fitLstSqAll(self, data=None, sliceChan=None, mcaIndex=None,
                     derivatives=None, results=None, uncertainties=None,
                     fitmodel=None, config=None, anchorslist=None,
                     lstsq_kwargs=None):
        """
        Fit all spectra
        """
        nChan, nFree = derivatives.shape
        bkgsub = bool(config['fit']['stripflag'])

        nMca = 1, 'MB'
        _logger.debug('Fit spectra in chunks of {}'.format(nMca))
        chunkItems = self._dataChunkIter(McaStackView.FullView,
                                         data=data,
                                         fitmodel=fitmodel,
                                         mcaSlice=sliceChan,
                                         mcaAxis=mcaIndex,
                                         nMca=nMca)
        for chunk in chunkItems:
            if fitmodel is None:
                (idx, idxShape), chunk = chunk
                chunkModel = None
            else:
                ((idx, idxShape), chunk), (_, chunkModel) = chunk
                chunkModel = chunkModel.T
            chunk = chunk.T

            # Subtract background
            if bkgsub:
                self._fitBkgSubtract(chunk, config=config,
                                     anchorslist=anchorslist,
                                     fitmodel=chunkModel)

            # Solve linear system of equations
            ddict = lstsq(derivatives, chunk, digested_output=True,
                          **lstsq_kwargs)
            lstsq_kwargs['last_svd'] = ddict.get('svd', None)

            # Save results
            idx = (slice(None),) + idx
            idxShape = (nFree,) + idxShape
            results[idx] = ddict['parameters'].reshape(idxShape)
            uncertainties[idx] = ddict['uncertainties'].reshape(idxShape)
            if chunkModel is not None:
                if bkgsub:
                    chunkModel += numpy.dot(derivatives, ddict['parameters'])
                else:
                    chunkModel[()] = numpy.dot(derivatives, ddict['parameters'])

    def _fitLstSqReduced(self, data=None, sliceChan=None, mcaIndex=None,
                         derivatives=None, results=None, uncertainties=None,
                         fitmodel=None, config=None, anchorslist=None,
                         lstsq_kwargs=None, mask=None,
                         skipNames=None, skipParams=None,
                         nFreeParameters=None, nmin=None):
        """
        Fit reduced number of spectra (mask) with a reduced model (skipped parameters will be set to zero)
        """
        npixels = int(mask.sum())
        nMca = 1, 'MB'
        if npixels < nmin:
            _logger.debug("Not worth refitting #%d pixels", npixels)
            for iFree, name in zip(skipParams, skipNames):
                results[iFree][mask] = 0.0
                uncertainties[iFree][mask] = 0.0
                _logger.debug("%d pixels of parameter %s set to zero",
                              npixels, name)
            if nFreeParameters is not None:
                nFreeParameters[mask] = 0
        else:
            _logger.debug("Refitting #{} spectra in chunks of {}".format(npixels, nMca))
            nChan, nFreeOrg = derivatives.shape
            idxFree = [i for i in range(nFreeOrg) if i not in skipParams]
            nFree = len(idxFree)
            A = derivatives[:, idxFree]
            lstsq_kwargs['last_svd'] = None

            # Fit all selected spectra in one chunk
            bkgsub = bool(config['fit']['stripflag'])
            chunkItems = self._dataChunkIter(McaStackView.MaskedView,
                                             data=data,
                                             fitmodel=fitmodel,
                                             mask=mask,
                                             mcaSlice=sliceChan,
                                             mcaAxis=mcaIndex,
                                             nMca=nMca)
            for chunk in chunkItems:
                if fitmodel is None:
                    (idx, idxShape), chunk = chunk
                    chunkModel = None
                else:
                    ((idx, idxShape), chunk), (_, chunkModel) = chunk
                    chunkModel = chunkModel.T
                chunk = chunk.T

                # Subtract background
                if bkgsub:
                    self._fitBkgSubtract(chunk, config=config,
                                         anchorslist=anchorslist,
                                         fitmodel=chunkModel)

                # Solve linear system of equations
                ddict = lstsq(A, chunk, digested_output=True,
                              **lstsq_kwargs)
                lstsq_kwargs['last_svd'] = ddict.get('svd', None)

                # Save results
                iParam = 0
                for iFree in range(nFreeOrg):
                    if iFree in skipParams:
                        results[iFree][idx] = 0.0
                        uncertainties[iFree][idx] = 0.0
                    else:
                        results[iFree][idx] = ddict['parameters'][iParam]\
                                                .reshape(idxShape)
                        uncertainties[iFree][idx] = ddict['uncertainties'][iParam]\
                                                .reshape(idxShape)
                        iParam += 1
                if chunkModel is not None:
                    if bkgsub:
                        chunkModel += numpy.dot(A, ddict['parameters'])
                    else:
                        chunkModel[()] = numpy.dot(A, ddict['parameters'])
                if nFreeParameters is not None:
                    nFreeParameters[idx] = nFree

    @staticmethod
    def _fitDtypeResult(data):
        if data.dtype not in [numpy.float32, numpy.float64]:
            if hasattr(data, "itemsize"):
                if data.itemsize < 5:
                    return numpy.float32
            elif hasattr(data, "nbytes"):
                if (data.nbytes / data.size) < 5:
                    return numpy.float32
            return numpy.float64
        else:
            return data.dtype

    @staticmethod
    def _fitDtypeCalculation(data):
        # TODO: always 64bit?
        return numpy.float64

    @staticmethod
    def _fitBkgSubtract(spectra, config=None, anchorslist=None, fitmodel=None):
        """Subtract brackground from data and add it to fit model
        """
        for k in range(spectra.shape[1]):
            # obtain the smoothed spectrum
            background = SpecfitFuns.SavitskyGolay(spectra[:, k],
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
            if fitmodel is not None:
                fitmodel[:, k] = background

    def _fitLstSqNegative(self, data=None, freeNames=None, nFreeBkg=None,
                          results=None, **kwargs):
        """Refit pixels with negative peak areas (remove the parameters from the model)
        """
        nFree = len(freeNames)
        iIter = 1
        nIter = 2 * (nFree - nFreeBkg) + iIter
        negativePresent = True
        while negativePresent:
            # Pixels with negative peak areas
            negList = []
            for iFree in range(nFreeBkg, nFree):
                negMask = results[iFree] < 0
                nNeg = negMask.sum()
                if nNeg > 0:
                    negList.append((nNeg, iFree, negMask))

            # No refit needed when no negative peak areas
            if not negList:
                negativePresent = False
                continue

            # Set negative peak areas to zero when
            # the maximal iterations is reached
            if iIter > nIter:
                for nNeg, iFree, negMask in negList:
                    results[iFree][negMask] = 0.0
                    _logger.warning("%d pixels of parameter %s forced to zero",
                                    nNeg, freeNames[iFree])
                continue

            # Bad pixels: use peak area with the most negative values
            negList.sort()
            negList.reverse()
            badParameters = []
            badParameters.append(negList[0][1])
            badMask = negList[0][2]

            # Combine with masks of all other peak areas
            # (unless none of them has negative pixels)
            # This is done to prevent endless loops:
            # if two or more parameters have common negative pixels
            # and one of them remains negative when forcing other one to zero
            for iFree, (nNeg, iFree, negMask) in enumerate(negList):
                if iFree not in badParameters and nNeg:
                    combMask = badMask & negMask
                    if combMask.sum():
                        badParameters.append(iFree)
                        badMask = combMask

            # Fit with a reduced model (skipped parameters are fixed at zero)
            badNames = [freeNames[iFree] for iFree in badParameters]
            nmin = 0.0025 * badMask.size
            _logger.debug("Refit iteration #{}. Fixed to zero: {}"
                          .format(iIter, badNames))
            self._fitLstSqReduced(data=data, mask=badMask,
                                  skipParams=badParameters,
                                  skipNames=badNames,
                                  results=results,
                                  nmin=nmin, **kwargs)
            iIter += 1

    def _fitDeriveMassFractions(self, config=None, results=None, nFreeBkg=None,
                                autotime=None, liveTimeFactor=None):
        """Calculate concentrations from peak areas
        """
        # check if an internal reference is used and if it is set to auto
        cTool = ConcentrationsTool.ConcentrationsTool()
        cToolConf = cTool.configure()
        cToolConf.update(config['concentrations'])

        fitreference = False
        if config['concentrations']['usematrix']:
            _logger.debug("USING MATRIX")
            if config['concentrations']['reference'].upper() == "AUTO":
                fitreference = True
        elif autotime:
            # we have to calculate with the time in the configuration
            # and correct later on
            cToolConf["autotime"] = 0

        fitresult = {}
        if fitreference:
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
            for iParam, param in enumerate(self._mcaTheory.PARAMETERS):
                if self._mcaTheory.codes[0][iParam] == Gefit.CFIXED:
                    continue
                if iParam < self._mcaTheory.NGLOBAL:
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
        massShape = list(results.shape)
        massShape[0] = nValues * nElements
        massFractions = numpy.zeros(massShape, dtype=results.dtype)

        referenceElement = addInfo['ReferenceElement']
        referenceTransitions = addInfo['ReferenceTransitions']
        _logger.debug("Reference <%s>  transition <%s>",
                      referenceElement, referenceTransitions)
        labels = []
        if referenceElement in ["", None, "None"]:
            _logger.debug("No reference")
            counter = 0
            for i, group in enumerate(fitresult['result']['groups']):
                if group.lower().startswith("scatter"):
                    _logger.debug("skept %s", group)
                    continue
                labels.append(group)
                if counter == 0:
                    if hasattr(liveTimeFactor, "shape"):
                        liveTimeFactor.shape = results[nFreeBkg+i].shape
                massFractions[counter] = liveTimeFactor * \
                    results[nFreeBkg+i] * \
                    (concentrationsResult['mass fraction'][group] / \
                        fitresult['result'][group]['fitarea'])
                counter += 1
                if len(concentrationsResult['layerlist']) > 1:
                    for layer in concentrationsResult['layerlist']:
                        labels.append((group, layer))
                        massFractions[counter] = liveTimeFactor * \
                                results[nFreeBkg+i] * \
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
            goodIdx = results[nFreeBkg+idx] > 0
            massFractions[idx] = referenceConcentrations
            counter = 0
            for i, group in enumerate(fitresult['result']['groups']):
                if group.lower().startswith("scatter"):
                    _logger.debug("skept %s", group)
                    continue
                labels.append(group)
                goodI = results[nFreeBkg+i] > 0
                tmp = results[nFreeBkg+idx][goodI]
                massFractions[counter][goodI] = (results[nFreeBkg+i][goodI]/(tmp + (tmp == 0))) *\
                            ((referenceArea/fitresult['result'][group]['fitarea']) *\
                            (concentrationsResult['mass fraction'][group]))
                counter += 1
                if len(concentrationsResult['layerlist']) > 1:
                    for layer in concentrationsResult['layerlist']:
                        labels.append((group, layer))
                        massFractions[counter][goodI] = (results[nFreeBkg+i][goodI]/(tmp + (tmp == 0))) *\
                            ((referenceArea/fitresult['result'][group]['fitarea']) *\
                            (concentrationsResult[layer]['mass fraction'][group]))
                        counter += 1
        return labels, massFractions


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
        raise ValueError(
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


def prepareDataStack(fileList):
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
        from PyMca5.PyMca import EDFStack
        dataStack = EDFStack.EDFStack(fileList, dtype=numpy.float32)
    return dataStack


def main():
    import sys
    import getopt
    options     = ''
    longoptions = ['cfg=', 'outdir=', 'concentrations=', 'weight=', 'refit=',
                   'tif=', 'edf=', 'csv=', 'h5=', 'dat=',
                   'filepattern=', 'begin=', 'end=', 'increment=',
                   'outroot=', 'outentry=', 'outprocess=',
                   'diagnostics=', 'debug=', 'overwrite=', 'multipage=']
    try:
        opts, args = getopt.getopt(
                     sys.argv[1:],
                     options,
                     longoptions)
    except Exception:
        print(sys.exc_info()[1])
        sys.exit(1)
    outputDir = None
    outputRoot = ""
    fileEntry = ""
    fileProcess = ""
    refit = None
    filepattern = None
    begin = None
    end = None
    increment = None
    backend = None
    weight = 0
    tif = 0
    edf = 0
    csv = 0
    h5 = 1
    dat = 0
    concentrations = 0
    diagnostics = 0
    debug = 0
    overwrite = 1
    multipage = 0
    for opt, arg in opts:
        if opt == '--cfg':
            configurationFile = arg
        elif opt == '--begin':
            if "," in arg:
                begin = [int(x) for x in arg.split(",")]
            else:
                begin = [int(arg)]
        elif opt == '--end':
            if "," in arg:
                end = [int(x) for x in arg.split(",")]
            else:
                end = int(arg)
        elif opt == '--increment':
            if "," in arg:
                increment = [int(x) for x in arg.split(",")]
            else:
                increment = int(arg)
        elif opt == '--filepattern':
            filepattern = arg.replace('"', '')
            filepattern = filepattern.replace("'", "")
        elif opt == '--outdir':
            outputDir = arg
        elif opt == '--weight':
            weight = int(arg)
        elif opt == '--refit':
            refit = int(arg)
        elif opt == '--concentrations':
            concentrations = int(arg)
        elif opt == '--diagnostics':
            diagnostics = int(arg)
        elif opt == '--outroot':
            outputRoot = arg
        elif opt == '--outentry':
            fileEntry = arg
        elif opt == '--outprocess':
            fileProcess = arg
        elif opt in ('--tif', '--tiff'):
            tif = int(arg)
        elif opt == '--edf':
            edf = int(arg)
        elif opt == '--csv':
            csv = int(arg)
        elif opt == '--h5':
            h5 = int(arg)
        elif opt == '--dat':
            dat = int(arg)
        elif opt == '--debug':
            debug = int(arg)
        elif opt == '--overwrite':
            overwrite = int(arg)
        elif opt == '--multipage':
            multipage = int(arg)

    logging.basicConfig()
    if debug:
        _logger.setLevel(logging.DEBUG)
    else:
        _logger.setLevel(logging.INFO)
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
        _logger.warning("--refit=%d taken as default" % refit)
    if len(fileList):
        dataStack = prepareDataStack(fileList)
    else:
        print("OPTIONS:", longoptions)
        sys.exit(0)
    if outputDir is None:
        print("RESULTS WILL NOT BE SAVED: No output directory specified")

    t0 = time.time()
    fastFit = FastXRFLinearFit()
    fastFit.setFitConfigurationFile(configurationFile)
    print("Main configuring Elapsed = % s " % (time.time() - t0))

    outbuffer = OutputBuffer(outputDir=outputDir,
                             outputRoot=outputRoot,
                             fileEntry=fileEntry,
                             fileProcess=fileProcess,
                             diagnostics=diagnostics,
                             tif=tif, edf=edf, csv=csv,
                             h5=h5, dat=dat,
                             multipage=multipage,
                             overwrite=overwrite)

    from PyMca5.PyMcaMisc import ProfilingUtils
    with ProfilingUtils.profile(memory=debug, time=debug):
        with outbuffer.saveContext():
            outbuffer = fastFit.fitMultipleSpectra(y=dataStack,
                                                weight=weight,
                                                refit=refit,
                                                concentrations=concentrations,
                                                outbuffer=outbuffer)
        print("Total Elapsed = % s " % (time.time() - t0))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
