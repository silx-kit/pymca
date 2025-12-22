#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2018-2023 European Synchrotron Radiation Facility
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
__author__ = "V. Armando Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import unittest
import os
import sys
import numpy
import gc
import shutil

try:
    import h5py
    HAS_H5PY = True
except Exception:
    HAS_H5PY = None
if sys.version_info < (3,):
    from StringIO import StringIO
else:
    from io import StringIO

DEBUG = 0

class testStackInfo(unittest.TestCase):
    def setUp(self):
        """
        Get the data directory
        """
        self._importSuccess = False
        self._outputDir = None
        self._h5File = None
        try:
            from PyMca5 import PyMcaDataDir
            self._importSuccess = True
            self.dataDir = PyMcaDataDir.PYMCA_DATA_DIR
        except Exception:
            self.dataDir = None

    def tearDown(self):
        gc.collect()
        if self._outputDir is not None:
            shutil.rmtree(self._outputDir, ignore_errors=True)
            if os.path.exists(self._outputDir):
                raise IOError("Directory <%s> not deleted" % self._outputDir)
        if self._h5File is not None:
            fileName = self._h5File
            if os.path.exists(fileName):
                os.remove(fileName)
            fileName = self._h5File + "external.h5"
            if os.path.exists(fileName):
                os.remove(fileName)

    def testDataDirectoryPresence(self):
        self.assertTrue(self._importSuccess,
                        'Unsuccessful PyMca5.PyMcaDataDir import')
        self.assertTrue(self.dataDir is not None,
                        'Unassigned PyMca5.PyMcaDataDir.PYMCA_DATA_DIR')
        self.assertTrue(os.path.exists(self.dataDir),
                        'Directory "%s" does not exist' % self.dataDir)
        self.assertTrue(os.path.isdir(self.dataDir),
                        '"%s" expected to be a directory' % self.dataDir)

    def testDataFilePresence(self):
        for fileName in ["Steel.spe", "Steel.cfg"]:
            dataFile = os.path.join(self.dataDir, fileName)
            self.assertTrue(os.path.exists(dataFile),
                            "File %s does not exists" % dataFile)
            self.assertTrue(os.path.isfile(dataFile),
                            "File %s is not an actual file" % dataFile)

    def testStackBaseAverageAndSum(self):
        from PyMca5.PyMcaIO import specfilewrapper as specfile
        from PyMca5.PyMcaIO import ConfigDict
        from PyMca5.PyMcaCore import DataObject
        from PyMca5.PyMcaCore import StackBase
        from PyMca5.PyMcaPhysics.xrf import FastXRFLinearFit
        spe = os.path.join(self.dataDir, "Steel.spe")
        cfg = os.path.join(self.dataDir, "Steel.cfg")
        sf = specfile.Specfile(spe)
        self.assertTrue(len(sf) == 1, "File %s cannot be read" % spe)
        self.assertTrue(sf[0].nbmca() == 1,
                        "Spe file should contain MCA data")

        y = counts = sf[0].mca(1)
        x = channels = numpy.arange(y.size).astype(numpy.float64)
        sf = None
        configuration = ConfigDict.ConfigDict()
        configuration.read(cfg)
        calibration = configuration["detector"]["zero"], \
                      configuration["detector"]["gain"], 0.0
        initialTime = configuration["concentrations"]["time"]
        # create the data
        nRows = 5
        nColumns = 10
        nTimes = 3
        data = numpy.zeros((nRows, nColumns, counts.size), dtype = numpy.float64)
        live_time = numpy.zeros((nRows * nColumns), dtype=numpy.float64)
        mcaIndex = 0
        for i in range(nRows):
            for j in range(nColumns):
                data[i, j] = counts
                live_time[i * nColumns + j] = initialTime * \
                                              (1 + mcaIndex % nTimes)
                mcaIndex += 1

        # create the stack data object
        stack = DataObject.DataObject()
        stack.data = data
        stack.info = {}
        stack.info["McaCalib"] = calibration
        stack.info["McaLiveTime"] = live_time
        stack.x = [channels]

        # let's play
        sb = StackBase.StackBase()
        sb.setStack(stack)
        x, y, legend, info = sb.getStackOriginalCurve()

        readCalib = info["McaCalib"]
        readLiveTime = info["McaLiveTime"]
        self.assertTrue(abs(readCalib[0] - calibration[0]) < 1.0e-10,
                "Calibration zero. Expected %f got %f" % \
                             (calibration[0], readCalib[0]))
        self.assertTrue(abs(readCalib[1] - calibration[1]) < 1.0e-10,
                "Calibration gain. Expected %f got %f" % \
                             (calibration[1], readCalib[0]))
        self.assertTrue(abs(readCalib[2] - calibration[2]) < 1.0e-10,
                "Calibration 2nd order. Expected %f got %f" % \
                             (calibration[2], readCalib[2]))
        self.assertTrue(abs(live_time.sum() - readLiveTime) < 1.0e-5,
                "Incorrect sum of live time data")

        mask = sb.getSelectionMask()
        if mask is None:
            mask = numpy.zeros((nRows, nColumns), dtype=numpy.uint8)
        mask[2, :] = 1
        mask[0, 0:2] = 1
        live_time = live_time.reshape(mask.shape)
        sb.setSelectionMask(mask)
        mcaObject = sb.calculateMcaDataObject(normalize=False)
        live_time = live_time.reshape(mask.shape)
        readLiveTime = mcaObject.info["McaLiveTime"]
        self.assertTrue(abs(live_time[mask > 0].sum() - readLiveTime) < 1.0e-5,
                "Incorrect sum of masked live time data")

        mcaObject = sb.calculateMcaDataObject(normalize=True)
        live_time = live_time.reshape(mask.shape)
        tmpBuffer = numpy.zeros(mask.shape, dtype=numpy.int32)
        tmpBuffer[mask > 0] = 1
        nSelectedPixels = float(tmpBuffer.sum())
        readLiveTime = mcaObject.info["McaLiveTime"]
        self.assertTrue( \
            abs((live_time[mask > 0].sum() / nSelectedPixels) - readLiveTime) < 1.0e-5,
                "Incorrect average of masked live time data")

    def testStackFastFit(self):
        # TODO: this is done in PyMcaBatchTest on multiple input formats
        # so not needed here
        return
        from PyMca5.PyMcaIO import specfilewrapper as specfile
        from PyMca5.PyMcaIO import ConfigDict
        from PyMca5.PyMcaCore import DataObject
        spe = os.path.join(self.dataDir, "Steel.spe")
        cfg = os.path.join(self.dataDir, "Steel.cfg")
        sf = specfile.Specfile(spe)
        self.assertTrue(len(sf) == 1, "File %s cannot be read" % spe)
        self.assertTrue(sf[0].nbmca() == 1,
                        "Spe file should contain MCA data")

        counts = sf[0].mca(1)
        channels = numpy.arange(counts.size)
        sf = None
        configuration = ConfigDict.ConfigDict()
        configuration.read(cfg)
        calibration = configuration["detector"]["zero"], \
                      configuration["detector"]["gain"], 0.0
        initialTime = configuration["concentrations"]["time"]

        # Fit MCA data with different dimensions: vector, image, stack
        for ndim in [1, 2, 3]:
            # create the data
            imgShape = tuple(range(3, 3+ndim))
            data = numpy.tile(counts, imgShape+(1,))
            nTimes = 3
            live_time = numpy.arange(numpy.prod(imgShape), dtype=int)
            live_time = initialTime + (live_time % nTimes)*initialTime

            # create the stack data object
            stack = DataObject.DataObject()
            stack.data = data
            stack.info = {}
            stack.info["McaCalib"] = calibration
            stack.info["McaLiveTime"] = live_time
            stack.x = [channels]

            # Test the fast XRF
            # we need to make sure we use fundamental parameters and
            # the time read from the file
            configuration["concentrations"]["usematrix"] = 0
            configuration["concentrations"]["useautotime"] = 1
            # make sure we use the SNIP background
            configuration['fit']['stripalgorithm'] = 1
            self._verifyFastFit(stack, configuration, live_time, nTimes)

    def _verifyFastFit(self, stack, configuration, live_time, nTimes):
        from PyMca5.PyMcaPhysics.xrf import FastXRFLinearFit
        ffit = FastXRFLinearFit.FastXRFLinearFit()
        firstIndex = tuple([0]*(stack.data.ndim-1))
        for refit in [0, 1]:
            outputDict = ffit.fitMultipleSpectra(y=stack,
                                                 weight=0,
                                                 configuration=configuration,
                                                 concentrations=True,
                                                 refit=refit)

            parameter_names = outputDict.labels('parameters')
            parameters = outputDict["parameters"].astype(numpy.float32)
            uncertainties = outputDict["uncertainties"].astype(numpy.float32)
            for i, (name, values, uvalues) in enumerate(zip(parameter_names, parameters, uncertainties)):
                if DEBUG:
                    print(name, values[firstIndex])
                delta = (values - values[firstIndex])
                self.assertTrue(delta.max() == 0,
                    "Different fit value for parameter %s delta %f" % \
                                (name, delta.max()))
                self.assertTrue(delta.min() == 0,
                    "Different fit value for parameter %s delta %f" % \
                                (name, delta.min()))
                delta = (uvalues - uvalues[firstIndex])
                self.assertTrue(delta.max() == 0,
                    "Different sigma value for parameter %s delta %f" % \
                                (name, delta.max()))
                self.assertTrue(delta.min() == 0,
                    "Different sigma value for parameter %s delta %f" % \
                                (name, delta.min()))

            massfraction_names = outputDict.labels('massfractions')
            massfractions = outputDict["massfractions"]
            for i, (name, fractions) in enumerate(zip(massfraction_names, massfractions)):
                # verify that massfractions took into account the time
                reference = fractions[firstIndex]
                cTime = configuration['concentrations']['time']
                values = fractions.flatten()
                for point in range(live_time.size):
                    current = values[point]
                    if DEBUG:
                        print(name, point, reference, current, point % nTimes)
                    if (point % nTimes) and (abs(reference) > 1.0e-10):
                        self.assertTrue(reference != current,
                            "Incorrect concentration for point %d" % point)
                    corrected = current * live_time[point] / cTime
                    if abs(reference) > 1.0e-10:
                        delta = 100 * abs((reference - corrected) / reference)
                        self.assertTrue(delta < 0.01,
                            "Incorrect concentration(t) for point %d" % point)
                    else:
                        self.assertTrue(abs(reference - corrected) < 1.0e-5,
                            "Incorrect concentration(t) for point %d" % point)

    @unittest.skipIf(not HAS_H5PY, "skipped h5py missing")
    def testFitHdf5Stack(self):
        import tempfile
        from PyMca5.PyMcaIO import specfilewrapper as specfile
        from PyMca5.PyMcaIO import ConfigDict
        from PyMca5.PyMcaIO import HDF5Stack1D
        from PyMca5.PyMcaPhysics.xrf import McaAdvancedFitBatch
        from PyMca5.PyMcaPhysics.xrf import LegacyMcaAdvancedFitBatch
        spe = os.path.join(self.dataDir, "Steel.spe")
        cfg = os.path.join(self.dataDir, "Steel.cfg")
        sf = specfile.Specfile(spe)
        self.assertTrue(len(sf) == 1, "File %s cannot be read" % spe)
        self.assertTrue(sf[0].nbmca() == 1,
                        "Spe file should contain MCA data")
        y = counts = sf[0].mca(1)
        x = channels = numpy.arange(y.size).astype(numpy.float64)
        sf = None
        configuration = ConfigDict.ConfigDict()
        configuration.read(cfg)
        calibration = configuration["detector"]["zero"], \
                      configuration["detector"]["gain"], 0.0
        initialTime = configuration["concentrations"]["time"]

        # create the data
        nRows = 5
        nColumns = 10
        nTimes = 3
        data = numpy.zeros((nRows, nColumns, counts.size), dtype = numpy.float64)
        live_time = numpy.zeros((nRows * nColumns), dtype=numpy.float64)

        mcaIndex = 0
        for i in range(nRows):
            for j in range(nColumns):
                data[i, j] = counts
                live_time[i * nColumns + j] = initialTime * \
                                              (1 + mcaIndex % nTimes)
                mcaIndex += 1
        self._h5File = os.path.join(tempfile.gettempdir(), "Steel.h5")

        # write the stack to an HDF5 file
        if os.path.exists(self._h5File):
            os.remove(self._h5File)
        h5 = h5py.File(self._h5File, "w")
        h5["/entry/instrument/detector/calibration"] = calibration
        h5["/entry/instrument/detector/channels"] = channels
        h5["/entry/instrument/detector/data"] = data
        h5["/entry/instrument/detector/live_time"] = live_time

        # add nexus conventions
        h5["/entry"].attrs["NX_class"] = u"NXentry"
        h5["/entry/instrument"].attrs["NX_class"] = u"NXinstrument"
        h5["/entry/instrument/detector/"].attrs["NX_class"] = u"NXdetector"
        h5["/entry/instrument/detector/data"].attrs["interpretation"] = \
                                                              u"spectrum"

        # case with softlink
        h5["/entry/measurement/mca_soft/data"] = \
                    h5py.SoftLink("/entry/instrument/detector/data")
        # case with info
        h5["/entry/measurement/mca_with_info/data"] = \
                    h5["/entry/instrument/detector/data"]
        h5["/entry/measurement/mca_with_info/info"] = \
                    h5["/entry/instrument/detector"]
        h5.flush()
        h5.close()
        h5 = None

        # check that the data can be read as a stack as
        # single top level dataset (issue #226)
        external = self._h5File + "external.h5"
        if os.path.exists(external):
            os.remove(external)
        h5 = h5py.File(external, "w")
        h5["/data_at_top"] = h5py.ExternalLink(self._h5File,
                                           "/entry/measurement/mca_soft/data")
        h5.flush()
        h5.close()
        h5 = None
        stack = HDF5Stack1D.HDF5Stack1D([external], {"y":"/data_at_top"})

        # check that the data can be read as a stack through a external link
        external = self._h5File + "external.h5"
        if os.path.exists(external):
            os.remove(external)
        h5 = h5py.File(external, "w")
        h5["/data_at_top"] = h5py.ExternalLink(self._h5File,
                                           "/entry/measurement/mca_soft/data")
        h5["/entry/data"] = h5py.ExternalLink(self._h5File,
                                            "/entry/measurement/mca_soft/data")
        h5.flush()
        h5.close()
        h5 = None
        fileList = [external]
        for selection in [{"y":"/data_at_top"}, # dataset at top level
                          {"y":"/data"},        # GOOD: selection inside /entry
                          {"y":"/entry/data"}]: # WRONG: complete path
            stack = HDF5Stack1D.HDF5Stack1D(fileList, selection)
            info = stack.info
            for key in ["McaCalib", "McaLiveTime"]:
                self.assertTrue(key in info,
                            "Key <%s>  not present but it should be there")

            readCalib = info["McaCalib"]
            readLiveTime = info["McaLiveTime"]
            self.assertTrue(abs(readCalib[0] - calibration[0]) < 1.0e-10,
                    "Calibration zero. Expected %f got %f" % \
                                 (calibration[0], readCalib[0]))
            self.assertTrue(abs(readCalib[1] - calibration[1]) < 1.0e-10,
                    "Calibration gain. Expected %f got %f" % \
                                 (calibration[1], readCalib[0]))
            self.assertTrue(abs(readCalib[2] - calibration[2]) < 1.0e-10,
                    "Calibration 2nd order. Expected %f got %f" % \
                                 (calibration[2], readCalib[2]))
            self.assertTrue(live_time.size == readLiveTime.size,
                            "Incorrect size of live time data")
            self.assertTrue(numpy.allclose(live_time, readLiveTime),
                            "Incorrect live time read")
            self.assertTrue(numpy.allclose(stack.x, channels),
                            "Incorrect channels read")
            self.assertTrue(numpy.allclose(stack.data, data),
                            "Incorrect data read")

        # check that the data can be read as a stack
        fileList = [self._h5File]
        for selection in [{"y":"/measurement/mca_with_info/data"},
                          {"y":"/measurement/mca_soft/data"},
                          {"y":"/instrument/detector/data"}]:
            stack = HDF5Stack1D.HDF5Stack1D(fileList, selection)
            info = stack.info
            for key in ["McaCalib", "McaLiveTime"]:
                self.assertTrue(key in info,
                            "Key <%s>  not present but it should be there")

            readCalib = info["McaCalib"]
            readLiveTime = info["McaLiveTime"]
            self.assertTrue(abs(readCalib[0] - calibration[0]) < 1.0e-10,
                    "Calibration zero. Expected %f got %f" % \
                                 (calibration[0], readCalib[0]))
            self.assertTrue(abs(readCalib[1] - calibration[1]) < 1.0e-10,
                    "Calibration gain. Expected %f got %f" % \
                                 (calibration[1], readCalib[0]))
            self.assertTrue(abs(readCalib[2] - calibration[2]) < 1.0e-10,
                    "Calibration 2nd order. Expected %f got %f" % \
                                 (calibration[2], readCalib[2]))
            self.assertTrue(live_time.size == readLiveTime.size,
                            "Incorrect size of live time data")
            self.assertTrue(numpy.allclose(live_time, readLiveTime),
                            "Incorrect live time read")
            self.assertTrue(numpy.allclose(stack.x, channels),
                            "Incorrect channels read")
            self.assertTrue(numpy.allclose(stack.data, data),
                            "Incorrect data read")

        # TODO: this is done in PyMcaBatchTest on multiple input formats
        # so not needed here
        return

        # perform the batch fit
        self._outputDir = os.path.join(tempfile.gettempdir(), "SteelTestDir")
        if not os.path.exists(self._outputDir):
            os.mkdir(self._outputDir)
        cfgFile = os.path.join(tempfile.gettempdir(), "SteelNew.cfg")
        if os.path.exists(cfgFile):
            try:
                os.remove(cfgFile)
            except Exception:
                print("Cannot remove file %s" % cfgFile)
        # we need to make sure we use fundamental parameters and
        # the time read from the file
        configuration["concentrations"]["usematrix"] = 0
        configuration["concentrations"]["useautotime"] = 1
        if not os.path.exists(cfgFile):
            configuration.write(cfgFile)
            os.chmod(cfgFile, 0o777)

        # Test batch fitting (legacy)
        batch = LegacyMcaAdvancedFitBatch.McaAdvancedFitBatch(cfgFile,
                                        filelist=[self._h5File],
                                        outputdir=self._outputDir,
                                        concentrations=True,
                                        selection=selection,
                                        quiet=True)
        batch.processList()
        imageFile = os.path.join(self._outputDir, "IMAGES", "Steel.dat")
        self._verifyBatchFitResult(imageFile, nRows, nColumns, live_time, nTimes, legacy=True)

        # Test batch fitting
        batch = McaAdvancedFitBatch.McaAdvancedFitBatch(cfgFile,
                                                        filelist=[self._h5File],
                                                        outputdir=self._outputDir,
                                                        concentrations=True,
                                                        selection=selection,
                                                        quiet=True)
        batch.outbuffer.extensions = ['.dat']
        batch.processList()
        imageFile = batch.outbuffer.filename('.dat')
        self._verifyBatchFitResult(imageFile, nRows, nColumns, live_time, nTimes)
    
        # Batch fitting went well
        # Test the fast XRF
        configuration["concentrations"]["usematrix"] = 0
        configuration["concentrations"]["useautotime"] = 1
        configuration['fit']['stripalgorithm'] = 1
        self._verifyFastFit(stack, configuration, live_time, nTimes)

    def _verifyBatchFitResult(self, imageFile, nRows, nColumns, live_time, nTimes, legacy=False):
        from PyMca5.PyMcaIO import specfilewrapper as specfile

        # recover the results
        self.assertTrue(os.path.isfile(imageFile),
                        "Batch fit result file <%s> not present" % imageFile)
        sf = specfile.Specfile(imageFile)
        labels = sf[0].alllabels()
        scanData = sf[0].data()
        sf = None
        self.assertTrue(scanData.shape[-1] == (nRows * nColumns),
           "Expected %d values got %d" % (nRows * nColumns, scanData.shape[-1]))

        if legacy:
            ismassfrac = lambda label: label.endswith("-mass-fraction")
        else:
            ismassfrac = lambda label: label.startswith("w(")

        referenceResult = {}
        for point in range(scanData.shape[-1]):
            for label in labels:
                idx = labels.index(label)
                if label in ["Point", "row", "column"]:
                    continue
                elif point == 0:
                    referenceResult[label] = scanData[idx, point]
                elif ismassfrac(label):
                    #print("label = ", label)
                    #print("reference = ", referenceResult[label])
                    #print("current = ", scanData[idx, point])
                    reference = referenceResult[label]
                    current = scanData[idx, point]
                    #print("ratio = ", current / reference)
                    #print("time ratio = ", live_time[point] / live_time[0])
                    if point % nTimes:
                        if abs(reference) > 1.0e-10:
                            self.assertNotEqual(reference, current,
                                "Incorrect concentration for point %d" % point)
                        corrected = current * \
                                    (live_time[point] / live_time[0])
                        if abs(reference) > 1.0e-10:
                            delta = \
                                100 * abs((reference - corrected) / reference)
                            self.assertTrue(delta < 0.01,
                                "Incorrect concentration(t) for point %d" % point)
                        else:
                            self.assertTrue(abs(reference - corrected) < 1.0e-5,
                                 "Incorrect concentration(t) for point %d" % point)
                    else:
                        self.assertEqual(reference, current,
                            "Incorrect concentration for point %d" % point)
                else:
                    reference = referenceResult[label]
                    current = scanData[idx, point]
                    self.assertEqual(reference, current,
                                    "Incorrect value for point %d" % point)


def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(unittest.TestLoader().loadTestsFromTestCase(testStackInfo))
    else:
        # use a predefined order
        testSuite.addTest(testStackInfo("testDataDirectoryPresence"))
        testSuite.addTest(testStackInfo("testStackBaseAverageAndSum"))
        testSuite.addTest(testStackInfo("testDataFilePresence"))
        testSuite.addTest(testStackInfo("testStackFastFit"))
        testSuite.addTest(testStackInfo("testFitHdf5Stack"))
    return testSuite

def test(auto=False):
    return unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))

if __name__ == '__main__':
    if len(sys.argv) > 1:
        auto = False
    else:
        auto = True
    result = test(auto)
    sys.exit(not result.wasSuccessful())
