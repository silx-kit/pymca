#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2024 European Synchrotron Radiation Facility
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
__doc__ = """This set of routines performs normalization of X-ray absorption
spectra for qualitative/preliminary analysis. For state-of-the-art XAS you
should take a look at dedicated and well-tested packages like IFEFFIT or
Viper/XANES dactyloscope """
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import numpy
import logging
from PyMca5.PyMcaMath.fitting import SpecfitFuns
from PyMca5.PyMcaMath import SGModule
from PyMca5.PyMcaMath.fitting.Gefit import LeastSquaresFit
_logger = logging.getLogger(__name__)

if _logger.getEffectiveLevel() == logging.DEBUG:
    from pylab import *


def e2k(energy, e0=0.0, units="eV"):
    r"""
        e2k(energy, e0=0.0): converts from E (eV) to k (A^-1)
        note: we use the convention that points with E<e0 will have negative k
    """
    energy = numpy.asarray(energy, dtype=numpy.float64)
    if units.lower() != "ev":
        energy *= 1000.
        e0 *= 1000.
    codata_ec = numpy.array(1.602176565e-19)
    codata_me = numpy.array(9.10938291e-31)
    codata_h = numpy.array(6.62606957e-34)
    codata_hbar = codata_h/2.0/numpy.pi
    #; converts a set in energy to a set in k
    #; the negative energies (below edge) are treated as negative k
    tmpx = energy - e0
    ccte = numpy.sqrt(codata_ec*2*codata_me/codata_hbar/codata_hbar)*1e-10
    tmpxx = ((tmpx > 0) * 2-1) * numpy.sqrt(numpy.abs(tmpx)) * ccte
    return tmpxx

def k2e(kValues):
    r"""
        k2e(x): converts from k (A^-1) to E (eV)
        The negative energies (below edge) are treated as negative k
    """
    codata_ec = numpy.array(1.602176565e-19)
    codata_me = numpy.array(9.10938291e-31)
    codata_h = numpy.array(6.62606957e-34)
    codata_hbar = codata_h/2.0/numpy.pi

    #; converts a set in k to energy
    #; the negative energies (below edge) are treated as negative k
    ccte = numpy.power(codata_hbar,2) / 2 / codata_me / codata_ec * 1e20
    tmpx = kValues
    tmpx = ((tmpx > 0) * 2-1) * tmpx * tmpx * ccte
    return tmpx

def polynom(parameter_list, x):
    if hasattr(x, 'shape'):
        output = numpy.zeros(x.shape)
    else:
        output = 0.0
    for i in range(len(parameter_list)):
        output += parameter_list[i] * pow(x, i)
    return output

def polynomDerivative(parameter_list, parameter_index, x):
    return pow(x, parameter_index)

def victoreen(parameter_list, x):
    return parameter_list[0] * pow(x, -3) + parameter_list[1] * pow(x, -4)

def victoreenDerivative(parameter_list, parameter_index, x):
    if parameter_index == 0:
        return pow(x, -3)
    else:
        return pow(x, -4)

def modifiedVictoreen(parameter_list, x):
    return parameter_list[0] * pow(x, -3) + parameter_list[1]

def modifiedVictoreenDerivative(parameter_list, parameter_index, x):
    if parameter_index == 0:
        return pow(x, -3)
    else:
        return numpy.ones(x.shape, dtype=numpy.float64)

def getE0SavitzkyGolay(energy, mu, points=5, full=False):
    # It does not check anything, data have to be prepared before!!!
    # take the first derivative
    yPrime = SGModule.getSavitzkyGolay(mu, npoints=points, degree=2, order=1)
    xPrime = energy[:]

    # get the index at maximum value
    iMax = numpy.argmax(yPrime)

    # get the center of mass
    w = points
    selection = yPrime[iMax-w:iMax+w+1]
    edge = (selection * xPrime[iMax-w:iMax+w+1]).sum(dtype=numpy.float64)/\
           selection.sum(dtype=numpy.float64)

    if full:
        # return intermediate information
        return {"edge":edge,
                "iMax": iMax,
                "xPrime": xPrime,
                "yPrime": yPrime}
    else:
        # return the corresponding x value
        return edge


def estimateXANESEdge(spectrum, energy=None, npoints=5, full=False,
                      sanitize=True):
    if sanitize:
        if energy is None:
            energy = numpy.arange(len(spectrum))
        x = numpy.asarray(energy, dtype=numpy.float64)
        y = numpy.asarray(spectrum, dtype=numpy.float64)
        # make sure data are sorted
        idx = energy.argsort(kind='mergesort')
        x = numpy.take(energy, idx)
        y = numpy.take(spectrum, idx)

        # make sure data are strictly increasing
        delta = x[1:] - x[:-1]
        dmin = delta.min()
        dmax = delta.max()
        if delta.min() <= 1.0e-10:
            # force data are strictly increasing
            # although we do not consider last point
            idx = numpy.nonzero(delta>0)[0]
            x = numpy.take(x, idx)
            y = numpy.take(y, idx)
            delta = None

        # use a regularly spaced spectrum
        if dmax != dmin:
            # choose the number of points or deduce it from
            # the input data length?
            nchannels = 10 * x.size
            xi = numpy.linspace(x[1], x[-2], nchannels).reshape(-1, 1)
            x = numpy.ravel(x)
            y = numpy.ravel(y)
            y = SpecfitFuns.interpol([x], y, xi, y.min())
            x = xi
    else:
        # take views
        x = energy[:]
        y = spectrum[:]

    x = numpy.ravel(x)
    y = numpy.ravel(y)

    # Sorted and regularly spaced values
    sortedX = x
    sortedY = y    

    ddict = getE0SavitzkyGolay(sortedX,
                               sortedY,
                               points=npoints,
                               full=full)
    if full:
        # return intermediate information
        return ddict["edge"], sortedX, sortedY, ddict["xPrime"], ddict["yPrime"]
    else:
        # return the corresponding x value
        return ddict

def getRegionsData(x0, y0, regions, edge=0.0):
    """
    x - 1D array
    y - 1D array of the same dimension as x
    regions - List of (xmin, xmax) values defining the regions.
    edge - Supplied edge energy
           The default is 0. That means regions are absolute energies.
           The actual regions are defined as (xmin + edge, xmax + edge)
    """
    # take a view of the data
    x = x0[:]
    y = y0[:]

    x = numpy.ravel(x)
    y = numpy.ravel(y)

    i = 0
    for region in regions:
        xmin = region[0] + edge
        xmax = region[1] + edge
        toidx = numpy.nonzero((x >= xmin) & (x <= xmax))[0]
        if i == 0:
            i = 1
            idx = toidx
        else:
            idx = numpy.concatenate((idx, toidx), axis=0)

    xOut = numpy.take(x, idx)
    yOut = numpy.take(y, idx)

    if len(x0.shape) == 1:
        xOut = numpy.ravel(xOut)
        yOut = numpy.ravel(yOut)
    elif x0.shape[0] == 1:
        xOut = xOut.reshape(1, -1)
        yOut = yOut.reshape(1, -1)
    else:
        xOut = xOut.reshape(-1, 1)
        yOut = yOut.reshape(-1, 1)

    return xOut, yOut

def XASNormalization(spectrum,
                     energy=None,
                     edge=None,
                     pre_edge_regions=None,
                     post_edge_regions=None,
                     algorithm='polynomial',
                     algorithm_parameters=None):
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError("Unsupported algorithm %s" % algorithm)
    if energy is None:
        energy = numpy.arange(len(spectrum))
    if edge in [None, 'Auto']:
        edge = estimateXANESEdge(spectrum, energy=energy)

    if pre_edge_regions is None:
        # divide pre-edge zone in 4 regions and take the 3rd?
        if edge < 200:
            # data assumed to be in keV
            pre_edge_regions = [[-0.4, -0.05]]
        else:
            # data assumend to be in eV
            pre_edge_regions = [[-400., -50.]]

    if post_edge_regions is None:
        #divide post-edge by 20 and leave out the first one?
        if edge < 200:
            # data assumed to be in keV
            post_edge_regions = [[0.020, energy.max()-edge]]
        else:
            # data assumend to be in eV
            post_edge_regions = [[20., energy.max()-edge]]

    return SUPPORTED_ALGORITHMS[algorithm](spectrum,
                                           energy,
                                           edge,
                                           pre_edge_regions,
                                           post_edge_regions,
                                           parameters=algorithm_parameters)

def XASPolynomialNormalization(spectrum,
                             energy,
                             edge=None,
                             pre_edge_regions=None,
                             post_edge_regions=None,
                             parameters=None):
    if edge in [None, 'Auto']:
        edge = estimateXANESEdge(spectrum, energy=energy)
    if parameters is None:
        parameters = {}
    pre_edge_order = parameters.get('pre_edge_order', 1)
    post_edge_order = parameters.get('post_edge_order', 3)

    xPre, yPre = getRegionsData(energy, spectrum, pre_edge_regions, edge=edge)
    xPost, yPost = getRegionsData(energy, spectrum, post_edge_regions, edge=edge)

    # get the proper pre-edge function to be used
    pre_edge_function = polynom
    if pre_edge_order in [0, 'Constant']:
        pre_edge_order = 0
    elif pre_edge_order in [1, 'Linear']:
        pre_edge_order = 1
    elif pre_edge_order in [2, 'Parabolic']:
        pre_edge_order = 2
    elif pre_edge_order in [3, 'Cubic']:
        pre_edge_order = 3
    elif pre_edge_order in [-1, 'Victoreen']:
        pre_edge_order = -1
        pre_edge_function = victoreen
    elif pre_edge_order in [-2, 'Modif. Victoreen']:
        pre_edge_order = -2
        pre_edge_function = modifiedVictoreen
    else:
        # case of arriving with a 4th order polynom, for instance
        pass

    # calculate pre-edge
    if pre_edge_order == 0:
        prePol = [yPre.mean()]
    elif pre_edge_order > 0:
        p = numpy.arange(pre_edge_order + 1).astype(numpy.float64)
        prePol = LeastSquaresFit(pre_edge_function, p,
                                 xdata=xPre, ydata=yPre,
                                 model_deriv=polynomDerivative,
                                 weightflag=0, linear=1)[0]
    elif pre_edge_order == -1:
        p = numpy.array([1.0, 1.0])
        prePol = LeastSquaresFit(pre_edge_function, p,
                                 xdata=xPre, ydata=yPre,
                                 model_deriv=victoreenDerivative,
                                 weightflag=0, linear=1)[0]
    elif pre_edge_order == -2:
        p = numpy.array([1.0, 1.0])
        prePol = LeastSquaresFit(pre_edge_function, p,
                                 xdata=xPre, ydata=yPre,
                                 model_deriv=modifiedVictoreenDerivative,
                                 weightflag=0, linear=1)[0]

    # get the proper post-edge function to be used
    post_edge_function = polynom
    if post_edge_order in [0, 'Constant']:
        post_edge_order = 0
    elif post_edge_order in [1, 'Linear']:
        post_edge_order = 1
    elif post_edge_order in [2, 'Parabolic']:
        post_edge_order = 2
    elif post_edge_order in [3, 'Cubic']:
        post_edge_order = 3
    elif post_edge_order in [-1, 'Victoreen']:
        post_edge_order = -1
        post_edge_function = victoreen
    elif post_edge_order in [-2, 'Modif. Victoreen']:
        post_edge_order = -2
        post_edge_function = modifiedVictoreen
    else:
        # case of arriving with a 4th order polynom, for instance
        pass

    # calculate post-edge
    baseLine = pre_edge_function(prePol, xPost)
    if post_edge_order == 0:
        # just take the average
        postPol = [(yPost-baseLine).mean()]
        normalizedSpectrum = (spectrum - pre_edge_function(prePol, energy))/postPol[0]
    elif post_edge_order > 0:
        p = numpy.arange(post_edge_order + 1).astype(numpy.float64)
        postPol = LeastSquaresFit(post_edge_function, p,
                                  xdata=xPost,
                                  ydata=yPost-baseLine,
                                  model_deriv=polynomDerivative,
                                  weightflag=0, linear=1)[0]
        normalizedSpectrum = (spectrum - pre_edge_function(prePol, energy))\
                             /post_edge_function(postPol, energy)
    elif post_edge_order == -1:
        p = numpy.array([1.0, 1.0])
        postPol = LeastSquaresFit(post_edge_function, p,
                                  xdata=xPost,
                                  ydata=yPost-baseLine,
                                  model_deriv=victoreenDerivative,
                                  weightflag=0, linear=1)[0]
        normalizedSpectrum = (spectrum - pre_edge_function(prePol, energy))\
                             /post_edge_function(postPol, energy)
    elif post_edge_order == -2:
        p = numpy.array([1.0, 1.0])
        postPol = LeastSquaresFit(post_edge_function, p,
                                  xdata=xPost,
                                  ydata=yPost-baseLine,
                                  model_deriv=modifiedVictoreenDerivative,
                                  weightflag=0, linear=1)[0]
        normalizedSpectrum = (spectrum - pre_edge_function(prePol, energy))\
                             /post_edge_function(postPol, energy)
    jump = post_edge_function(postPol, edge)
    if _logger.getEffectiveLevel() == logging.DEBUG:
        plot(energy, spectrum, 'o')
        plot(xPre, pre_edge_function(prePol, xPre), 'r')
        plot(xPost, post_edge_function(postPol, xPost)+pre_edge_function(prePol, xPost), 'y')
        show()
    return energy, normalizedSpectrum, edge, jump, pre_edge_function, prePol, post_edge_function, postPol

def XASVictoreenNormalization(spectrum,
                              energy,
                              edge=None,
                              pre_edge_regions=None,
                              post_edge_regions=None,
                              parameters=None):

    if edge in [None, 'Auto']:
        edge = estimateXANESEdge(spectrum, energy=energy)

    if parameters is None:
        parameters = {}

    xPre, yPre = getRegionsData(energy, spectrum, pre_edge_regions)
    xPost, yPost = getRegionsData(energy, spectrum, post_edge_regions)


    pre_edge_order = parameters.get('pre_edge_order', 1)
    post_edge_order = parameters.get('post_edge_order', 1)
    if pre_edge_order in [1, -1, 'Victoreen']:
        pre_edge_function = victoreen
    else:
        pre_edge_function = modifiedVictoreen

    if post_edge_order in [1, -1, 'Victoreen']:
        post_edge_function = victoreen
    else:
        post_edge_function = modifiedVictoreen

    p = numpy.array([1.0, 1.0])
    prePol = LeastSquaresFit(pre_edge_function, p, xdata=xPre, ydata=yPre,
                                 weightflag=0, linear=1)[0]
    postPol = LeastSquaresFit(post_edge_function, p,
                              xdata=xPost,
                              ydata=yPost-pre_edge_function(prePol, xPost),
                              weightflag=0, linear=1)[0]
    normalizedSpectrum = (spectrum - pre_edge_function(prePol, energy))\
                         /post_edge_function(postPol, energy)
    if _logger.getEffectiveLevel() == logging.DEBUG:
        _logger.info("VICTOREEN")
        plot(energy, spectrum, 'o')
        plot(xPre, pre_edge_function(prePol, xPre), 'r')
        plot(xPost,
             post_edge_function(postPol, xPost)+pre_edge_function(prePol, xPost), 'y')
        show()
    return energy, normalizedSpectrum, edge

SUPPORTED_ALGORITHMS = {"polynomial":XASPolynomialNormalization,
                        "victoreen": XASVictoreenNormalization}

if __name__ == "__main__":
    import sys
    from PyMca.PyMcaIO import specfilewrapper as specfile
    import time
    sf = specfile.Specfile(sys.argv[1])
    scan = sf[0]
    data = scan.data()
    energy = data[0, :]
    spectrum = data[1, :]
    n = 100
    t0 = time.time()
    for i in range(n):
        edge = estimateXANESEdge(spectrum+i, energy=energy)
    print("EDGE ELAPSED = ", (time.time() - t0)/float(n))
    print("EDGE = %f"  % edge)
    if _logger.getEffectiveLevel() == logging.DEBUG:
        n = 1
    else:
        n = 100
    t0 = time.time()
    for i in range(n):
        nEne0, nSpe0 = XASNormalization(spectrum+i, energy,
                                        edge=edge,
                                        algorithm='polynomial',
                                        algorithm_parameters={'pre_edge_order':0,
                                                              'post_edge_order':0})[0:2]
    print("ELAPSED 0 = ", (time.time() - t0)/float(n))
    t0 = time.time()
    for i in range(n):
        nEneP, nSpeP = XASNormalization(spectrum+i,
                                        energy,
                                        edge=edge,
                                        algorithm='polynomial',
                                        algorithm_parameters={'pre_edge_order':1,
                                                              'post_edge_order':2})[0:2]
    print("ELAPSED Poly = ", (time.time() - t0)/float(n))
    t0 = time.time()
    for i in range(n):
        nEneV, nSpeV = XASNormalization(spectrum+i,
                                        energy,
                                        edge=edge,
                                        algorithm='polynomial',
                                        algorithm_parameters={'pre_edge_order':'Victoreen',
                                                              'post_edge_order':'Victoreen'})[0:2]
    print("ELAPSED Victoreen = ", (time.time() - t0)/float(n))
    if _logger.getEffectiveLevel() == logging.DEBUG:
        #plot(energy, spectrum, 'b')
        plot(nEne0, nSpe0, 'k', label='Polynomial')
        plot(nEneP, nSpeP, 'b', label='Polynomial')
        plot(nEneV, nSpeV, 'r', label='Victoreen')
        show()
