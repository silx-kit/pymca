# coding: utf8
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
__author__ = "Jérôme Kieffer and V.Armando Solé"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__date__ = "20151002"
__doc__ = "This is a python module to measure image offsets"

import os, time
import numpy
from numpy.fft import fft2, ifft2, fftshift, ifftshift
PYMCA = False
SCIPY = False
try:
    from PyMca5.PyMca import SpecfitFuns
    PYMCA = True
except ImportError:
    try:
        import scipy.ndimage.interpolation
        SCIPY = True
    except Exception:
        print("Shift bilinear relaced by shiftFFT")

def shiftFFT(img, shift):
    """
    Shift an array using FFTs
    :param input: 2d numpy array
    :param shift: 2-tuple of float
    :return: shifted image

    """
    d0, d1 = img.shape
    v0, v1 = shift
    f0 = ifftshift(numpy.arange(-d0 // 2, d0 // 2))
    f1 = ifftshift(numpy.arange(-d1 // 2, d1 // 2))
    m1, m0 = numpy.meshgrid(f1, f0)
    e0 = numpy.exp(-2j * numpy.pi * v0 * m0 / float(d0))
    e1 = numpy.exp(-2j * numpy.pi * v1 * m1 / float(d1))
    e = e0 * e1
    out = ifft2(fft2(img) * e)
    return abs(out)

def shiftBilinear(img, shift):
    """
    Shift an array like  scipy.ndimage.interpolation.shift(input, shift, mode="wrap", order="infinity")
    :param input: 2d numpy array
    :param shift: 2-tuple of float
    :return: shifted image

    """
    shape = img.shape
    x = numpy.zeros((shape[0] * shape[1], 2), numpy.float64)
    x[:,0] = shift[0] + numpy.outer(numpy.arange(shape[0]), numpy.ones(shape[1])).reshape(-1)
    x[:,1] = shift[1] + numpy.outer(numpy.ones(shape[0]), numpy.arange(shape[1])).reshape(-1)
    shifted = SpecfitFuns.interpol([numpy.arange(shape[0]),
                                    numpy.arange(shape[1])], img, x)
    shifted = shifted.reshape(shape[0], shape[1])
    return shifted

def shiftImage(img, shift, method=None):
    """
    Shift an array like  scipy.ndimage.interpolation.shift(input, shift, mode="wrap", order="infinity")
    :param input: 2d numpy array
    :param shift: 2-tuple of float
    :param method: string set to PYMCA, SCIPY or FFT. Default is to try the first of those that is possible.
    :return: shifted image

    """
    if method is None:
        if PYMCA:
            return shiftBilinear(img, shift)
        elif SCIPY:
            return scipy.ndimage.interpolation.shift(img, shift, mode="wrap")
        else:
            return shiftFFT(img, shift)
    elif method.lower() == "pymca":
        return shiftBilinear(img, shift)
    elif method.lower() == "scipy":
        return scipy.ndimage.interpolation.shift(img, shift, mode="wrap")
    else:
        return shiftFFT(img, shift)

def measure_offset(img1, img2, method="fft", withLog=False):
    """
    Measure the actual offset between 2 images. The first one is the reference. That means, if
    the image to be shifted is the second one, the shift has to be multiplied byt -1.
    :param img1: ndarray, first image
    :param img2: ndarray, second image, same shape as img1
    :param withLog: shall we return logs as well ? boolean
    :return: tuple of floats with the offsets of the second respect to the first
    """
    method = str(method)
    shape = img1.shape
    assert img2.shape == shape
    if 1:
        #use numpy fftpack
        if img1.dtype not in [numpy.float32, numpy.float64, numpy.float]:
            i1f = fft2(img1.astype(numpy.float32))
            i2f = fft2(img2.astype(numpy.float32))
        else:
            i1f = fft2(img1)
            i2f = fft2(img2)
        return measure_offset_from_ffts(i1f, i2f, withLog=withLog)

def measure_offset_from_ffts(img0_fft2, img1_fft2, withLog=False):
    """
    Convenience method to measure the actual offset between 2 images taing their FFTs as inpuy
    The first FFT one is the one of the reference. That means, if the image to be shifted is the
    second one, the shift has to be multiplied byt -1.
    :param img1: ndarray, FFT of first image
    :param img2: ndarray, FFT of the second image, same shape as img1
    :param withLog: shall we return logs as well ? boolean
    :return: tuple of floats with the offsets of the second respect to the first
    """
    shape = img0_fft2.shape
    logs = []
    f0 = img0_fft2
    f1 = img1_fft2
    t0 = time.time()
    absf0 = abs(f0)
    absf1 = abs(f1)
    if 0:
        # one way to deal with zeros
        if (absf0 < 1.0e-20).any() or (absf1 < 1.0e-20).any():
            offset = [0.0, 0.0]
            logs.append("MeasureOffset: empty or uniform image?")
            if withLog:
                return offset, logs
            else:
                return offset
    else:
        # this one seems better because numerator is expected to be zero
        idx = absf0 < 1.0e-20
        if idx.any():
            absf0[idx] = 1.0
        idx = absf1 < 1.0e-20
        if idx.any():
            absf1[idx] = 1.0
    res = abs(fftshift(ifft2((f0 * f1.conjugate()) / (absf0 * absf1))))
    t1 = time.time()
    a0, a1 = numpy.unravel_index(numpy.argmax(res), shape)
    resmax = res[a0, a1]
    coarse_result =  (shape[0]//2 - a0, shape[1] // 2 - a1)
    logs.append("ImageRegistration: coarse result : %d %d " % \
                               (coarse_result[0], coarse_result[1]))
    # refine a bit the position
    w = 3
    x0 = 0.0
    x1 = 0.0
    total = 0.0
    a00 = int(max(a0-w, 0))
    a01 = int(min(a0+w+1, shape[0]))
    a10 = int(max(a1-w, 0))
    a11 = int(min(a1+w+1, shape[1]))
    if a00 == a01:
        a01 = a00 + 1
    if a10 == a11:
        a11 = a10 + 1
    for i in range(a00, a01):
        for j in range(a10, a11):
            if res[i, j] > 0.1 * resmax:
                tmp = res[i, j]
                x0 += i * tmp
                x1 += j * tmp
                total += tmp
    offset = [shape[0]//2 - x0/total, shape[1] // 2 - x1/total]
    logs.append("MeasureOffset: fine result of the centered image: %.3f %.3fs " % (offset[0], offset[1]))
    t3 = time.time()
    logs.append("Total execution time %.3fs" % (t3 - t0))
    if withLog:
        return offset, logs
    else:
        return offset

def get_crop_indices(shape, shifts0, shifts1):
    """
    Get the indices of the valid region to be used when aligning a set of images
    :param shitfs0: Shifts applied to the first dimension
    :param shitfs1: Shifts applied to the second dimension
    """
    shifts0_min = numpy.min(shifts0)
    shifts0_max = numpy.max(shifts0)
    shifts1_min = numpy.min(shifts1)
    shifts1_max = numpy.max(shifts1)

    d0_start = int(numpy.ceil(shifts0_max))
    d0_end = int(min(shape[0], numpy.floor(shape[0] + shifts0_min)))

    d1_start = int(numpy.ceil(shifts1_max))
    d1_end = int(min(shape[1], numpy.floor(shape[1] + shifts1_min)))
    return d0_start, d0_end, d1_start, d1_end

