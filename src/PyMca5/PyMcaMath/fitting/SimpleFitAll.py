#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2017-2023 European Synchrotron Radiation Facility
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
import sys
import os
import numpy
import h5py
import datetime
import logging

from PyMca5.PyMcaIO import ConfigDict
import PyMca5


text_dtype = h5py.special_dtype(vlen=str)


_logger = logging.getLogger(__name__)


CONS = ['FREE',
        'POSITIVE',
        'QUOTED',
        'FIXED',
        'FACTOR',
        'DELTA',
        'SUM',
        'IGNORE']


def to_h5py_utf8(str_list):
    """Convert a string or a list of strings to a numpy array of
    unicode strings that can be written to HDF5 as utf-8.
    """
    return numpy.array(str_list, dtype=text_dtype)

def to_utf8(x):
    if hasattr(x, 'decode'):
        return x.decode('utf-8')
    else:
        return x

class SimpleFitAll(object):
    """Fit module designed to fit a number of curves, and save its
    output to HDF5 - nexus."""
    def __init__(self, fit):
        self.fit = fit
        self.curves_x = None
        self.curves_y = None
        self.curves_sigma = None
        self.legends = None
        self.xlabels = None
        self.ylabels = None
        self.xMin = None
        self.xMax = None
        self.outputDir = PyMca5.PyMcaDirs.outputDir
        self.outputFileName = None
        self._progress = 0.0
        self._status = "Ready"
        self._currentFitIndex = None
        self._currentSigma = None
        self._nSpectra = None
        self.progressCallback = None
        # optimization variables
        self.__estimationPolicy = "always"
        self._currentFitStartTime = ""
        self._currentFitEndTime = ""

    def setProgressCallback(self, method):
        """
        The method will be called as method(current_fit_index, total_fit_index)
        """
        self.progressCallback = method

    def progressUpdate(self):
        """
        This method returns a dictionary with the keys
        progress: A number between 0 and 100 indicating the fit progress
        status: Status of the calculation thread.
        """
        ddict = {
            'progress': self._progress,
            'status': self._status}
        return ddict

    def setOutputDirectory(self, outputdir):
        self.outputDir = outputdir

    def setOutputFileName(self, outputfile):
        self.outputFileName = outputfile

    def setData(self, curves_x, curves_y, sigma=None, xmin=None, xmax=None,
                legends=None, xlabels=None, ylabels=None):
        """

        :param curves_x: List of 1D arrays, one per curve, or single 1D array
        :param curves_y: List of 1D arrays, one per curve
        :param sigma: List of 1D arrays, one per curve, or single 1D array
        :param float xmin:
        :param float xmax:
        :param List[str] legends: List of curve legends. If None, defaults to
            ``["curve0", "curve1"...]``
        """
        self.curves_x = curves_x
        self.curves_y = curves_y
        self.curves_sigma = sigma
        self.xMin = xmin
        self.xMax = xmax
        self.legends = legends or ["curve%d" % i for i in range(len(curves_y))]
        self.xlabels = xlabels or ["X" for _cy in curves_y]
        self.ylabels = ylabels or ["Y" for _cy in curves_y]

    def setConfigurationFile(self, fname):
        if not os.path.exists(fname):
            raise IOError("File %s does not exist" % fname)
        w = ConfigDict.ConfigDict()
        w.read(fname)
        self.setConfiguration(w)

    def setConfiguration(self, ddict):
        self.fit.setConfiguration(ddict, try_import=True)

    def processAll(self):
        assert self.curves_y is not None, "You must first call setData()!"
        data = self.curves_y

        # create output file
        with h5py.File(self.getOutputFileName(), mode="w-") as h5f:
            h5f.attrs["NX_class"] = "NXroot"

        # get the total number of fits to be performed
        self._nSpectra = len(data)

        # a watcher to verify if a table can be generated
        self._referenceParameters = None

        # optimization
        self.__estimationPolicy = "always"
        backgroundPolicy = self.fit._fitConfiguration['fit']['background_estimation_policy']
        functionPolicy = self.fit._fitConfiguration['fit']['function_estimation_policy']
        if "Estimate always" in [functionPolicy, backgroundPolicy]:
            self.__estimationPolicy = "always"
        elif "Estimate once" in [functionPolicy, backgroundPolicy]:
            self.__estimationPolicy = "once"
        else:
            self.__estimationPolicy = "never"

        # initialize control variables
        self._parameters = None
        self._progress = 0
        self._status = "Fitting"
        for i in range(self._nSpectra):
            self._progress = (i * 100.) / self._nSpectra
            try:
                self.processSpectrum(i)
            except Exception:
                _logger.error(
                        "Error %s processing index = %d", sys.exc_info()[1], i)
                if _logger.getEffectiveLevel() == logging.DEBUG:
                    raise
        self.onProcessSpectraFinished()
        self._status = "Ready"
        if self.progressCallback is not None:
            self.progressCallback(self._nSpectra, self._nSpectra)

    def processSpectrum(self, i):
        self._currentFitStartTime = datetime.datetime.now().isoformat()
        self.aboutToGetSpectrum(i)
        x, y, sigma, xmin, xmax = self.getFitInputValues(i)
        self.fit.setData(x, y, sigma=sigma, xmin=xmin, xmax=xmax)
        if self._parameters is None and self.__estimationPolicy != "never":
            _logger.debug("First estimation")
            self.fit.estimate()
        elif self.__estimationPolicy == "always":
            _logger.debug("Estimation due to settings")
            self.fit.estimate()
        else:
            _logger.debug("Using user estimation")

        self.estimateFinished()
        values, chisq, sigmaFromFit, niter, lastdeltachi = self.fit.startFit()
        self._currentSigma = abs(sigma + (sigma == 0)) if sigma is not None else\
            numpy.sqrt(abs(y) + (y == 0))

        self._currentFitEndTime = datetime.datetime.now().isoformat()
        self.fitOneSpectrumFinished()

    def getFitInputValues(self, index):
        """
        Returns the fit parameters x, y, sigma, xmin, xmax
        """
        # get y (always a list of 1D arrays)
        y = self.curves_y[index]

        # get x
        if self.curves_x is None:
            nValues = y.size
            x = numpy.arange(float(nValues))
            x = x.reshape(*y.shape)
            self.curves_x = x
        elif hasattr(self.curves_x, "shape") and len(self.curves_x.shape) == 1:
            # same x array for all curves
            x = self.curves_x
        else:
            # list of abscissas, one per curve
            x = self.curves_x[index]

        assert x.shape == y.shape

        if self.curves_sigma is None:
            return x, y, None, self.xMin, self.xMax

        # get sigma
        if hasattr(self.curves_sigma, "shape") and len(self.curves_sigma.shape) == 1:
            # only one sigma for all the y values
            sigma = self.curves_sigma
        else:
            sigma = self.curves_sigma[index]
        assert sigma.shape == y.shape

        return x, y, sigma, self.xMin, self.xMax

    def estimateFinished(self):
        _logger.debug("Estimate finished")

    def aboutToGetSpectrum(self, idx):
        _logger.debug("New spectrum %d", idx)
        self._currentFitIndex = idx
        if self.progressCallback is not None:
            self.progressCallback(idx, self._nSpectra)

    def fitOneSpectrumFinished(self):
        _logger.debug("fit finished")

        # get parameter results
        fitOutput = self.fit.getResult(configuration=False)
        result = fitOutput['result']
        idx = self._currentFitIndex
        parNames = [x["name"] for x in self.fit.paramlist]
        if idx == 0:
            self._referenceParameters = parNames
        if self._referenceParameters is not None:
            if self._referenceParameters == parNames:
                _logger.info("Fit of spectrum %d has same parameters" % idx)
            else:
                _logger.info("Fit of spectrum %d has different parameters" % idx)
                self._referenceParameters = None

        if result is None:
            _logger.warning("result not valid for index %d", idx)
            return

        self._appendOneResultToHdf5(resultDict=fitOutput["result"])

    def _appendOneResultToHdf5(self, resultDict):
        # Get all the  necessary data (TODO: pass it to method as attrs)
        idx = self._currentFitIndex
        end_time = self._currentFitEndTime
        start_time = self._currentFitStartTime
        sigma = self._currentSigma
        legend = self.legends[idx]
        xlabel = self.xlabels[idx]
        ylabel = self.ylabels[idx]
        x, y, _inSigma, xMin, xMax = self.getFitInputValues(idx)
        fitted_data = self.fit.evaluateDefinedFunction(x)
        configIni = ConfigDict.ConfigDict(self.fit.getConfiguration()).tostring()
        fit_paramlist = self.fit.paramlist
        filename = self.getOutputFileName()

        # Write the data to file (append)
        self._entryNameFormat = "fit_%d"
        with h5py.File(filename, mode="r+") as h5f:
            entry = h5f.create_group(self._entryNameFormat % idx)
            entry.attrs["NX_class"] = to_h5py_utf8("NXentry")
            entry.attrs["default"] = to_h5py_utf8("fit_process/results/plot")
            entry.create_dataset("start_time",
                                 data=to_h5py_utf8(start_time))
            entry.create_dataset("end_time", data=to_h5py_utf8(end_time))
            entry.create_dataset("title",
                                 data=to_h5py_utf8("Fit of '%s'" % legend))

            process = entry.create_group("fit_process")
            process.attrs["NX_class"] = to_h5py_utf8("NXprocess")
            process.create_dataset("program", data=to_h5py_utf8("pymca"))
            process.create_dataset("version", data=to_h5py_utf8(PyMca5.version()))
            process.create_dataset("date", data=to_h5py_utf8(end_time))

            configuration = process.create_group("configuration")
            configuration.attrs["NX_class"] = to_h5py_utf8("NXnote")
            configuration.create_dataset("type", data=to_h5py_utf8("text/plain"))
            configuration.create_dataset("data", data=to_h5py_utf8(configIni))
            configuration.create_dataset("file_name", data=to_h5py_utf8("SimpleFit.ini"))
            configuration.create_dataset("description",
                                         data=to_h5py_utf8("Fit configuration"))

            results = process.create_group("results")
            results.attrs["NX_class"] = to_h5py_utf8("NXcollection")

            estimation = results.create_group("estimation")
            estimation.attrs["NX_class"] = to_h5py_utf8("NXcollection")

            for p in fit_paramlist:
                pgroup = estimation.create_group(p["name"])
                # constraint code can be an int, convert to str
                if numpy.issubdtype(numpy.array(p['code']).dtype,
                                    numpy.integer):
                    pgroup.create_dataset('code', data=to_h5py_utf8(CONS[p['code']]))
                else:
                    pgroup.create_dataset('code', data=to_h5py_utf8(p['code']))
                pgroup.create_dataset('cons1', data=p['cons1'])
                pgroup.create_dataset('cons2', data=p['cons2'])
                pgroup.create_dataset('estimation', data=p['estimation'])

            for key, value in resultDict.items():
                if not numpy.issubdtype(type(key), numpy.character):
                    _logger.debug("skipping key %s (not a text string)", key)
                    continue
                if key == "fittedvalues":
                    output_key = "parameter_values"
                elif key == "parameters":
                    output_key = "parameter_names"
                elif key == "sigma_values":
                    output_key = "parameter_sigmas"
                else:
                    output_key = key

                value_dtype = numpy.array(value).dtype
                if numpy.issubdtype(value_dtype, numpy.number) or\
                        numpy.issubdtype(value_dtype, numpy.bool_):
                    # straightforward conversion to HDF5
                    results.create_dataset(output_key,
                                           data=value)
                elif numpy.issubdtype(value_dtype, numpy.character):
                    # ensure utf-8 output
                    results.create_dataset(output_key,
                                           data=to_h5py_utf8(value))

            plot = results.create_group("plot")
            plot.attrs["NX_class"] = to_h5py_utf8("NXdata")
            plot.attrs["signal"] = to_h5py_utf8("raw_data")
            plot.attrs["auxiliary_signals"] = to_h5py_utf8(["fitted_data"])
            plot.attrs["axes"] = to_h5py_utf8(["x"])
            plot.attrs["title"] = to_h5py_utf8("Fit of '%s'" % legend)
            signal = plot.create_dataset("raw_data", data=y)
            if ylabel is not None:
                signal.attrs["long_name"] = to_h5py_utf8(ylabel)
            axis = plot.create_dataset("x", data=x)
            if xlabel is not None:
                axis.attrs["long_name"] = to_h5py_utf8(xlabel)
            if sigma is not None:
                plot.create_dataset("errors", data=sigma)
            plot.create_dataset("fitted_data", data=fitted_data)

    def getOutputFileName(self):
        return os.path.join(self.outputDir,
                            self.outputFileName)

    def _isSummaryEntryAcceptable(self):
        if self._referenceParameters is not None:
            if self._nSpectra > 1:
                return True

    def _createSummaryEntry(self):
        filename = self.getOutputFileName()
        with h5py.File(filename, mode="r+") as h5f:
            for idx in range(self._nSpectra):
                inputEntryName = os.path.join("/", self._entryNameFormat % idx)
                inputEntry = h5f[inputEntryName]
                start_time = inputEntry["start_time"]
                end_time = inputEntry["end_time"]
                chisq = inputEntry["fit_process/results/chisq"]
                parameterValues = inputEntry["fit_process/results/parameter_values"]
                parameterErrors = inputEntry["fit_process/results/parameter_sigmas"]
                parameterNames = inputEntry["fit_process/results/parameter_names"]
                if idx == 0:
                    entry = h5f.create_group("fit_summary")
                    entry.attrs["NX_class"] = u"NXentry"
                    entry.attrs["default"] = u"result"
                    entry["start_time"] = to_h5py_utf8(datetime.datetime.now().isoformat())
                    result = entry.create_group("result")
                    result.attrs["NX_class"] = u"NXdata"
                    result.attrs["axes"] = to_h5py_utf8(["index"])
                    result.attrs["signal"] = to_h5py_utf8("chisq")
                    result["index"] = numpy.arange(self._nSpectra)
                    result.create_dataset("chisq",
                                          shape=(self._nSpectra,),
                                          dtype=numpy.float32)
                    for parameter0 in parameterNames:
                        parameter = to_utf8(parameter0)
                        result.create_dataset(parameter,
                                              shape=(self._nSpectra,),
                                              dtype=numpy.float32)
                        result.create_dataset(parameter + "_errors",
                                              shape=(self._nSpectra,),
                                              dtype=numpy.float32)
                        result.create_dataset(parameter + "_estimation",
                                              shape=(self._nSpectra,),
                                              dtype=numpy.float32)
                result["chisq"][idx] = chisq
                for par in range(len(parameterNames)):
                    parameter = to_utf8(parameterNames[par])
                    estimationName = "fit_process/results/estimation/%s/estimation" % \
                                     parameter
                    estimation = inputEntry[estimationName]
                    result[parameter][idx] = parameterValues[par]
                    result[parameter + "_errors"][idx] = parameterErrors[par]
                    result[parameter + "_estimation"][idx] = estimation
            
            entry["end_time"] = to_h5py_utf8(datetime.datetime.now().isoformat())
            first = self._entryNameFormat % 0
            last = self._entryNameFormat % (self._nSpectra - 1)
            entry["title"] = "Summary of %s to %s" % (first, last)
            
    def onProcessSpectraFinished(self):
        _logger.debug("All curves processed")
        self._status = "Curves Fitting finished"
        if self._isSummaryEntryAcceptable():
            self._createSummaryEntry()
