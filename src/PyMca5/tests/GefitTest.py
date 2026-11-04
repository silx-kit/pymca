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
__author__ = "V. Armando Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import unittest
import os
import numpy

class testGefit(unittest.TestCase):
    def setUp(self):
        """
        import the module
        """
        try:
            from PyMca5.PyMcaMath.fitting import Gefit
            self.gefit = Gefit
        except Exception:
            self.gefit = None

    def gaussianPlusLinearBackground(self, param, t):
        dummy = 2.3548200450309493 * (t - param[3])/ param[4]
        return param[0] + param[1] * t +\
               param[2] * numpy.exp(-0.5 * dummy * dummy)

    def testGefitImport(self):
        self.assertTrue(self.gefit is not None)

    def testGefitLeastSquares(self):
        self.testGefitImport()
        x = numpy.arange(500.)
        originalParameters = numpy.array([10.5, 2, 1000.0, 200., 100],
                                         numpy.float64)
        fitFunction = self.gaussianPlusLinearBackground
        y = fitFunction(originalParameters, x)

        startingParameters = [0.0 ,1.0,900.0, 150., 90]
        fittedpar, chisq, sigmapar =self.gefit.LeastSquaresFit(fitFunction,
                                                     startingParameters,
                                                     xdata=x,
                                                     ydata=y,
                                                     sigmadata=None)
        for i in range(len(originalParameters)):
            self.assertTrue(abs(fittedpar[i] - originalParameters[i]) < 0.01)

    def testSpecfitStepUpEstimate(self):
        # steep edge: no peak found, the forced one is used
        from PyMca5.PyMcaMath.fitting import Specfit, SpecfitFunctions
        fit = Specfit.Specfit()
        fit.importfun(SpecfitFunctions.__file__)
        fit.configure(fittheory="Step Up", fitbkg="No Background",
                      ForcePeakPresence=1)
        fit.setdata(x=numpy.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
                    y=numpy.array([0, 0, 0, 0, 0, 0.5, 1, 1, 1, 1]))
        fit.estimate()
        # Height, Position, FWHM
        self.assertTrue(abs(fit.paramlist[1]["estimation"] - 5.0) < 0.1)

def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(\
            unittest.TestLoader().loadTestsFromTestCase(testGefit))
    else:
        # use a predefined order
        testSuite.addTest(testGefit("testGefitImport"))
        testSuite.addTest(testGefit("testGefitLeastSquares"))
        testSuite.addTest(testGefit("testSpecfitStepUpEstimate"))
    return testSuite

def test(auto=False):
    unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))

if __name__ == '__main__':
    test()
