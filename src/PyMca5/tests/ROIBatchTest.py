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
__author__ = "V. Armando Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import unittest
import os
import sys
import numpy
import gc
import shutil

DEBUG = 0

try:
    from PyMca5.PyMcaCore import LegacyStackROIBatch
    from PyMca5.PyMcaCore import StackROIBatch
except ImportError:
    LegacyStackROIBatch = StackROIBatch = None


def generatePeakDataPositiveX():
    x = numpy.arange(2000) / 2.
    peakpos = 500
    y = 2*x + 200 * numpy.exp(-0.5*(x-peakpos)**2)
    config = {}
    config["ROI"] = {}
    config["ROI"]["roilist"] = ["roi1", "roi2", "roi3"]
    config["ROI"]["roidict"] = {}
    config["ROI"]["roidict"]["roi1"] = {}
    config["ROI"]["roidict"]["roi1"]["from"] = 10.01
    config["ROI"]["roidict"]["roi1"]["to"] = 20.01
    config["ROI"]["roidict"]["roi1"]["type"] = "Channel"
    config["ROI"]["roidict"]["roi2"] = {}
    config["ROI"]["roidict"]["roi2"]["from"] = 400.01
    config["ROI"]["roidict"]["roi2"]["to"] = 600.01
    config["ROI"]["roidict"]["roi2"]["type"] = "Channel"
    config["ROI"]["roidict"]["roi3"] = {}
    config["ROI"]["roidict"]["roi3"]["from"] = 700.01
    config["ROI"]["roidict"]["roi3"]["to"] = 800.01
    config["ROI"]["roidict"]["roi3"]["type"] = "Channel"
    return x, y, config, peakpos


def generatePeakDataNegativeX():
    x = numpy.arange(2000) / 2.
    peakpos = 500
    y = x + 200.0 * numpy.exp(-0.5*(x-peakpos)**2)
    x = -x
    peakpos = -peakpos
    config = {}
    config["ROI"] = {}
    config["ROI"]["roilist"] = ["roi1", "roi2", "roi3"]
    config["ROI"]["roidict"] = {}
    config["ROI"]["roidict"]["roi1"] = {}
    config["ROI"]["roidict"]["roi1"]["to"] = -10.01
    config["ROI"]["roidict"]["roi1"]["from"] = -20.01
    config["ROI"]["roidict"]["roi1"]["type"] = "Channel"
    config["ROI"]["roidict"]["roi2"] = {}
    config["ROI"]["roidict"]["roi2"]["to"] = -400.01
    config["ROI"]["roidict"]["roi2"]["from"] = -600.01
    config["ROI"]["roidict"]["roi2"]["type"] = "Channel"
    config["ROI"]["roidict"]["roi3"] = {}
    config["ROI"]["roidict"]["roi3"]["to"] = -700.01
    config["ROI"]["roidict"]["roi3"]["from"] = -800.01
    config["ROI"]["roidict"]["roi3"]["type"] = "Channel"
    return x, y, config, peakpos


class testROIBatch(unittest.TestCase):

    @unittest.skipIf(StackROIBatch is None,
                     "cannot import PyMca5.PyMcaCore.StackROIBatch")
    def testPeakPositiveX(self):
        self.assertROIsumWithLegacy(generatePeakDataPositiveX,
                                    xAtMinMax=True, net=True)

    @unittest.skipIf(StackROIBatch is None,
                     "cannot import PyMca5.PyMcaCore.StackROIBatch")
    def testPeakNegativeX(self):
        self.assertROIsumWithLegacy(generatePeakDataNegativeX,
                                    xAtMinMax=True, net=True)

    def assertROIsumWithLegacy(self, datagen, **parameters):
        result1 = self.assertROIsum(datagen, legacy=False, **parameters)
        result2 = self.assertROIsum(datagen, legacy=True, **parameters)
        self.assertEqual(set(result1.keys()), set(result2.keys()))
        for k1, v1 in result1.items():
            v2 = result2[k1]
            numpy.testing.assert_array_equal(v1, v2)

    def assertROIsum(self, datagen, legacy=False, **parameters):
        x, y, config, peakpos = datagen()
        y = y.reshape(1, 1, -1)
        y = y.repeat(2, axis=0).repeat(3, axis=1)
        if legacy:
            instance = LegacyStackROIBatch.StackROIBatch()
            outputDict = instance.batchROIMultipleSpectra(x=x,
                                                          y=y,
                                                          configuration=config,
                                                          **parameters)
            names = outputDict["names"]
            images = outputDict["images"]
        else:
            instance = StackROIBatch.StackROIBatch()
            outputDict = instance.batchROIMultipleSpectra(x=x,
                                                          y=y,
                                                          configuration=config,
                                                          save=False,
                                                          **parameters)
            names = outputDict.labels('roisum')
            images = outputDict['roisum']
        outputDict = dict(zip(names, images))
        for row in y:
            for yspectrum in row:
                self.assertResult(x, yspectrum, peakpos, outputDict,
                                  config["ROI"]["roidict"],
                                  **parameters)
        return outputDict

    def assertResult(self, x, y, peakpos, outputDict, roidict,
                     xAtMinMax=True, net=True):
        for roi in roidict:
            toData = roidict[roi]["to"]
            fromData = roidict[roi]["from"]
            idx = numpy.nonzero((fromData <= x) & (x <= toData))[0]
            if len(idx):
                xw = x[idx]
                yw = y[idx]
                rawCounts = yw.sum(dtype=numpy.float64)
                deltaX = xw[-1] - xw[0]
                deltaY = yw[-1] - yw[0]
                if abs(deltaX) > 0.0:
                    slope = (deltaY/deltaX)
                    background = yw[0] + slope * (xw - xw[0])
                    netCounts = rawCounts -\
                                background.sum(dtype=numpy.float64)
                else:
                    netCounts = 0.0
            else:
                rawCounts = 0.0
                netCounts = 0.0
            roidict[roi]["rawcounts"] = rawCounts
            roidict[roi]["netcounts"] = netCounts
            rawName = "ROI " + roi + ""
            netName = "ROI " + roi + " Net"
            imageRaw = outputDict[rawName]
            imageNet = outputDict[netName]
            self.assertTrue(imageRaw[0, 0] > -1.0e-10,
                            "Expected positive value for raw roi %s got %f" %
                            (roi, imageRaw[0, 0]))
            self.assertTrue(imageNet[0, 0] > -1.0e-10,
                            "Expected positive value for net roi %s got %f" %
                            (roi, imageNet[0, 0]))
            self.assertTrue(abs(imageRaw[0, 0] - rawCounts) < 1.0e-8,
                            "Incorrect calculation for raw roi %s" % roi)
            self.assertTrue(abs(imageNet[0, 0] - netCounts) < 1.0e-8,
                            "Incorrect calculation for net roi %s delta = %f" %
                            (roi, imageNet[0, 0] - netCounts))

            xAtMinName = "ROI " + roi + " Channel at Min."
            xAtMaxName = "ROI " + roi + " Channel at Max."
            if xAtMinMax:
                self.assertTrue(xAtMinName in outputDict,
                                "xAtMin not calculated for roi %s" % roi)
                self.assertTrue(xAtMaxName in outputDict,
                                "xAtMax not calculated for roi %s" % roi)
                imageMin = outputDict[xAtMinName]
                imageMax = outputDict[xAtMaxName]
                if roi == "roi2":
                    self.assertTrue(imageMax[0, 0] == peakpos,
                                    "Max expected at %d got %f" %
                                    (peakpos, imageMax[0, 0]))
            else:
                self.assertTrue(xAtMinName not in outputDict,
                                "xAtMin calculated for roi %s" % roi)
                self.assertTrue(xAtMaxName not in outputDict,
                                "xAtMax calculated for roi %s" % roi)


def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(unittest.TestLoader().loadTestsFromTestCase(testROIBatch))
    else:
        # use a predefined order
        testSuite.addTest(testROIBatch("testPeakPositiveX"))
        testSuite.addTest(testROIBatch("testPeakNegativeX"))
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
