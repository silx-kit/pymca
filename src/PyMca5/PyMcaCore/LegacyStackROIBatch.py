#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
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
Module to calculate a set of ROIs on a stack of data.
"""

import os
import sys
import logging

import numpy

from PyMca5.PyMcaIO import ConfigDict
from PyMca5.PyMca import EDFStack
from PyMca5.PyMca import ArraySave
from PyMca5.PyMcaMisc import CliUtils

_logger = logging.getLogger(__name__)


class StackROIBatch(object):
    def __init__(self):
        self._config = {}

    def setConfiguration(self, configuration):
        self._config["ROI"] = configuration["ROI"]

    def getConfiguration(self):
        return self._config

    def setConfigurationFile(self, ffile):
        if not os.path.exists(ffile):
            raise IOError("File <%s> does not exists" % ffile)
        configuration = ConfigDict.ConfigDict()
        configuration.read(ffile)
        self.setConfiguration(configuration)

    def batchROIMultipleSpectra(self, x=None, y=None,
                           configuration=None, net=True,
                           xAtMinMax=False, index=None,
                           xLabel=None):
        """
        This method performs the actual fit. The y keyword is the only mandatory input argument.

        :param x: 1D array containing the x axis (usually the channels) of the spectra.
        :param y: 3D array containing the data, usually [nrows, ncolumns, nchannels]
        :param weight: 0 Means no weight, 1 Use an average weight, 2 Individual weights (slow)
        :param net: 0 Means no subtraction, 1 Calculate
        :param xAtMinMax: if True, calculate X at maximum and minimum Y . Default is false.
        :param index: Index of dimension where to apply the ROIs.
        :param xLabel: Type of ROI to be used.
        :return: A dictionary with the images and the image names as keys.
        """
        if y is None:
            raise RuntimeError("y keyword argument is mandatory!")
        if hasattr(y, "info") and hasattr(y, "data"):
            data = y.data
            mcaIndex = y.info.get("McaIndex", -1)
        else:
            data = y
            mcaIndex = -1
        if index is None:
            index = mcaIndex
        if index < 0:
            index = len(data.shape) - 1

        #workaround a problem with h5py
        try:
            if index in [0]:
                testException = data[0:1]
            else:
                if len(data.shape) == 2:
                    testException = data[0:1,-1]
                elif len(data.shape) == 3:
                    testException = data[0:1,0:1,-1]
        except AttributeError:
            txt = "%s" % type(data)
            if 'h5py' in txt:
                _logger.info("Implementing h5py workaround")
                import h5py
                data = h5py.Dataset(data.id)
            else:
                raise

        # make sure to get x data
        if x is None:
            x = numpy.arange(data.shape[index]).astype(numpy.float32)

        if configuration is not None:
            self.setConfiguration(configuration)

        # read the current configuration
        config = self.getConfiguration()

        # start the work
        roiList0 = config["ROI"]["roilist"]
        if type(roiList0) not in [type([]), type((1,))]:
            roiList0 = [roiList0]

        # operate only on compatible ROIs
        roiList = []
        for roi in roiList0:
            if roi.upper() == "ICR":
                roiList.append(roi)
            roiType = config["ROI"]["roidict"][roi]["type"]
            if xLabel is None:
                roiList.append(roi)
            elif xLabel.lower() == roiType.lower():
                roiList.append(roi)
            else:
                _logger.info("ROI <%s> ignored")

        # only usual spectra case supported
        if index != (len(data.shape) - 1):
            raise IndexError("Only stacks of spectra supported")

        if len(data.shape) != 3:
            txt  = "For the time being only "
            txt += "three dimensional arrays supported"
            raise NotImplemented(txt)

        if len(data.shape) != 3:
            txt  = "For the time being only "
            txt += "three dimensional arrays supported"
            raise NotImplemented(txt)
        totalSpectra = 1
        for i in range(len(data.shape)):
            if i != index:
                totalSpectra *= data.shape[i]

        if x.size != data.shape[index]:
            raise NotImplemented("All the spectra should share same X axis")

        jStep = min(1000, data.shape[1])
        nRois = len(roiList)
        idx = [None] * nRois
        xw = [None] * nRois
        iXMinList = [None] * nRois
        iXMaxList = [None] * nRois
        nRows = data.shape[0]
        nColumns = data.shape[1]
        if xAtMinMax:
            results = numpy.zeros((nRois * 4, nRows, nColumns), numpy.float64)
            names = [None] * 4 * nRois
        else:
            results = numpy.zeros((nRois * 2, nRows, nColumns), numpy.float64)
            names = [None] * 2 * nRois

        for i in range(0, data.shape[0]):
            if i == 0:
                chunk = numpy.zeros((jStep,
                                     data.shape[index]),
                                     numpy.float64)
                xData = x
            jStart = 0
            while jStart < data.shape[1]:
                jEnd = min(jStart + jStep, data.shape[1])
                chunk[:(jEnd - jStart)] = data[i, jStart: jEnd]
                for j, roi in enumerate(roiList):
                    if i == 0:
                        roiType = config["ROI"]["roidict"][roi]["type"]
                        roiLine = roi
                        roiFrom = config["ROI"]["roidict"][roi]["from"]
                        roiTo = config["ROI"]["roidict"][roi]["to"]
                        if roiLine == "ICR":
                            xw[j] = xData
                            idx[j] = numpy.arange(len(xData))
                            iXMinList[j] = idx[j][0]
                            iXMaxList[j] = idx[j][-1]
                        else:
                            idx[j] = numpy.nonzero((roiFrom <= xData) & (xData <= roiTo))[0]
                            if len(idx):
                                xw[j] = xData[idx[j]]
                                iXMinList[j] = numpy.argmin(xw[j])
                                iXMaxList[j] = numpy.argmax(xw[j])
                            else:
                                xw[j] = None
                        names[j] = "ROI " + roiLine
                        names[j + nRois] = "ROI "+ roiLine + " Net"
                        if xAtMinMax:
                            names[j + 2 * nRois] = "ROI "+ roiLine + (" %s at Max." % roiType)
                            names[j + 3 * nRois] = "ROI "+ roiLine + (" %s at Min." % roiType)
                    if xw[j] is None:
                        # no points in the ROI            
                        rawSum = 0.0
                        netSum = 0.0
                    else:
                        tmpArray = chunk[:(jEnd - jStart), idx[j]]
                        rawSum = tmpArray.sum(axis=-1, dtype=numpy.float64)
                        deltaX = xw[j][iXMaxList[j]] - xw[j][iXMinList[j]]
                        left = tmpArray[:, iXMinList[j]]
                        right = tmpArray[:, iXMaxList[j]]
                        deltaY = right - left
                        if abs(deltaX) > 0.0:
                            slope = deltaY / float(deltaX)
                            background = left * len(xw[j])+ slope * \
                                         (xw[j] - xw[j][iXMinList[j]]).sum(dtype=numpy.float64) 
                            netSum = rawSum - background
                        else:
                            netSum = 0.0
                    results[j][i,:(jEnd - jStart)] = rawSum
                    results[j + nRois][i,:(jEnd - jStart)] = netSum
                    if xAtMinMax:
                        if xw[j] is None:
                            # what can be the Min and the Max when there is nothing in the ROI?
                            _logger.warning("No Min. Max for ROI <%s>. Empty ROI" % roiLine)
                        else:
                            # maxImage
                            results[j + 2 * nRois][i, :(jEnd - jStart)] = \
                                     xw[j][numpy.argmax(tmpArray, axis=1)]
                            # minImage
                            results[j + 3 * nRois][i, :(jEnd - jStart)] = \
                                     xw[j][numpy.argmin(tmpArray, axis=1)]

                jStart = jEnd
        outputDict = {'images':results,
                      'names':names}
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
    else:
        raise ValueError("Cannot handle more than three indices.")
    return fileList


def main(args):
    if args.filepattern is not None:
        if args.begin is None or args.end is None:
            raise ValueError(
                "A file pattern needs at least a set of begin and end indices"
            )
        fileList = getFileListFromPattern(
            args.filepattern,
            args.begin,
            args.end,
            increment=args.increment,
        )
    else:
        fileList = args.files

    if not fileList:
        print("No input files provided")
        return 0

    dataStack = EDFStack.EDFStack(fileList, dtype=numpy.float32)

    if args.outdir is None:
        print("RESULTS WILL NOT BE SAVED: No output directory specified")

    worker = StackROIBatch()
    worker.setConfigurationFile(args.configurationFile)
    result = worker.batchROIMultipleSpectra(y=dataStack)

    if args.outdir is None:
        print("No output directory provided")
        return 0

    imageNames = result["names"]
    images = result["images"]
    nImages = images.shape[0]

    fileRoot = args.fileRoot
    if not fileRoot:
        fileRoot = "images"

    os.makedirs(args.outdir, exist_ok=True)
    imagesDir = os.path.join(args.outdir, "IMAGES")
    os.makedirs(imagesDir, exist_ok=True)

    imageList = []
    fileImageNames = []

    for i in range(nImages):
        name = imageNames[i].replace(" ", "-")
        fileImageNames.append(name)
        imageList.append(images[i])

    # Save EDF
    fileName = os.path.join(imagesDir, fileRoot + ".edf")
    ArraySave.save2DArrayListAsEDF(
        imageList,
        fileName,
        labels=fileImageNames,
    )

    # Save CSV
    fileName = os.path.join(imagesDir, fileRoot + ".csv")
    ArraySave.save2DArrayListAsASCII(
        imageList,
        fileName,
        csv=True,
        labels=fileImageNames,
    )

    # Optional TIFF
    if args.tif:
        for i, label in enumerate(fileImageNames):
            fileName = os.path.join(
                imagesDir,
                fileRoot + label + ".tif"
            )
            ArraySave.save2DArrayListAsMonochromaticTiff(
                [imageList[i]],
                fileName,
                labels=[label],
                dtype=numpy.float32,
            )

    return 0


def build_parser():
    parser = CliUtils.create_parser(description="Stack ROI Batch Processing")

    parser.add_argument("--cfg", type=str, dest="configurationFile")
    parser.add_argument("--outdir", type=str, default=None)
    parser.add_argument("--outfileroot", type=str, dest="fileRoot", default=None)

    parser.add_argument("--filepattern", type=str, default=None, help="File pattern")
    parser.add_argument("--begin", type=CliUtils.int_or_list, default=None, help="Begin index/indices, comma-separated")
    parser.add_argument("--end", type=CliUtils.int_or_list, default=None, help="End index/indices, comma-separated")
    parser.add_argument("--increment", type=CliUtils.int_or_list, default=None, help="Increment(s), comma-separated")

    parser.add_argument("--tif", type=int, default=0)

    parser.add_argument("files", nargs="*")

    return parser


if __name__ == "__main__":
    exit_code = CliUtils.cli_main(main, build_parser(), loggers=(_logger,))
    sys.exit(exit_code)
