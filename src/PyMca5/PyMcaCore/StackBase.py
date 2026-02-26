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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
"""
Base class to handle stacks.

"""
from PyMca5.PyMcaCore import DataObject
import numpy
import time
import os
import sys
import glob
import logging

logger = logging.getLogger(__name__)


PLUGINS_DIR = None
try:
    import PyMca5
    if os.path.exists(os.path.join(os.path.dirname(__file__), "PyMcaPlugins")):
        from PyMca5 import PyMcaPlugins
        PLUGINS_DIR = os.path.dirname(PyMcaPlugins.__file__)
    else:
        directory = os.path.dirname(__file__)
        while True:
            if os.path.exists(os.path.join(directory, "PyMcaPlugins")):
                PLUGINS_DIR = os.path.join(directory, "PyMcaPlugins")
                break
            directory = os.path.dirname(directory)
            if len(directory) < 5:
                break
    userPluginsDirectory = PyMca5.getDefaultUserPluginsDirectory()
    PYMCA_PLUGINS_DIR = PLUGINS_DIR
    if userPluginsDirectory is not None:
        if PLUGINS_DIR is None:
            PLUGINS_DIR = userPluginsDirectory
        else:
            PLUGINS_DIR = [PLUGINS_DIR, userPluginsDirectory]
except Exception:
    PYMCA_PLUGINS_DIR = None
    pass

class StackBase(object):
    def __init__(self):
        self._stack = DataObject.DataObject()
        self._stack.x = None
        self._stackImageData = None
        self._selectionMask = None
        self._finiteData = True
        self._ROIDict = {'name': "ICR",
                         'type': "CHANNEL",
                         'calibration': [0, 1.0, 0.0],
                         'from': 0,
                         'to': -1}

        self._ROIImageDict = {'ROI': None,
                              'Maximum': None,
                              'Minimum': None,
                              'Left': None,
                              'Middle': None,
                              'Right': None,
                              'Background': None}

        self.__ROIImageCalculationIsUsingSuppliedEnergyAxis = False

        self._ROIImageList = []
        self._ROIImageNames = []

        self.__pluginDirList = []
        self.pluginList = []
        self.pluginInstanceDict = {}
        self.getPlugins()
        # beyond 5 million elements, iterate to calculate the sums
        # preventing huge intermediate use of memory when calculating
        # the sums.
        self._dynamicLimit = 5.0E6
        self._tryNumpy = True

    def setPluginDirectoryList(self, dirlist):
        for directory in dirlist:
            if not os.path.exists(directory):
                raise IOError("Directory:\n%s\ndoes not exist." % directory)

        self.__pluginDirList = dirlist

    def getPluginDirectoryList(self):
        return self.__pluginDirList

    def getPlugins(self):
        """
        Import or reloads all the available plugins.
        It returns the number of plugins loaded.
        """

        if PLUGINS_DIR is not None:
            if self.__pluginDirList == []:
                if type(PLUGINS_DIR) == type([]):
                    self.__pluginDirList = PLUGINS_DIR
                else:
                    self.__pluginDirList = [PLUGINS_DIR]
        self.pluginList = []
        for directory in self.__pluginDirList:
            if directory is None:
                continue
            if not os.path.exists(directory):
                raise IOError("Directory:\n%s\ndoes not exist." % directory)

            fileList = glob.glob(os.path.join(directory, "*.py"))
            targetMethod = 'getStackPluginInstance'
            # prevent unnecessary imports
            moduleList = []
            for fname in fileList:
                # in Python 3, rb implies bytes and not strings
                f = open(fname, 'r')
                lines = f.readlines()
                f.close()
                f = None
                for line in lines:
                    if line.startswith("def"):
                        if line.split(" ")[1].startswith(targetMethod):
                            moduleList.append(fname)
                            break
            for module in moduleList:
                try:
                    pluginName = os.path.basename(module)[:-3]
                    if directory == PYMCA_PLUGINS_DIR:
                        plugin = "PyMcaPlugins." + pluginName
                    else:
                        plugin = pluginName
                        if directory not in sys.path:
                            sys.path.insert(0, directory)
                    if pluginName in self.pluginList:
                        idx = self.pluginList.index(pluginName)
                        del self.pluginList[idx]
                    if plugin in self.pluginInstanceDict.keys():
                        del self.pluginInstanceDict[plugin]
                    if plugin in sys.modules:
                        if hasattr(sys.modules[plugin], targetMethod):
                            if sys.version < '3.0':
                                reload(sys.modules[plugin])
                            else:
                                import imp
                                imp.reload(sys.modules[plugin])
                    else:
                        try:
                            __import__(plugin)
                        except Exception:
                            if directory == PYMCA_PLUGINS_DIR:
                                plugin = "PyMca5.PyMcaPlugins." + pluginName
                                __import__(plugin)
                            else:
                                raise
                    if hasattr(sys.modules[plugin], targetMethod):
                        self.pluginInstanceDict[plugin] = \
                                sys.modules[plugin].getStackPluginInstance(self)
                        self.pluginList.append(plugin)
                except Exception:
                    logger.debug("Problem importing module %s", plugin)
                    if logger.getEffectiveLevel() == logging.DEBUG:
                        raise
        return len(self.pluginList)

    def setStack(self, stack, mcaindex=2, fileindex=None):
        #unfortunaly python 3 reports
        #isinstance(stack, DataObject.DataObject) as false
        #for DataObject derived classes like OmnicMap!!!!
        if id(stack) == id(self._stack):
            # just updated
            pass
        elif hasattr(stack, "shape") and\
             hasattr(stack, "dtype"):
            # array like
            self._stack.x = None
            self._stack.data = stack
            self._stack.info['SourceName'] = "Data of unknown origin"
        elif isinstance(stack, DataObject.DataObject) or\
           ("DataObject.DataObject" in ("%s" % type(stack))) or\
           ("QStack" in ("%s" % type(stack))) or\
           ("Map" in ("%s" % type(stack)))or\
           ("Stack" in ("%s" % type(stack))) or\
           (hasattr(stack, "data") and hasattr(stack, "info")):
            self._stack = stack
            self._stack.info['SourceName'] = stack.info.get('SourceName',
                                                            "Data of unknown origin")
        else:
            self._stack.x = None
            self._stack.data = stack
            self._stack.info['SourceName'] = "Data of unknown origin"

        info = self._stack.info
        mcaIndex = info.get('McaIndex', mcaindex)
        if (mcaIndex < 0) and (len(self._stack.data.shape) == 3):
            mcaIndex = len(self._stack.data.shape) + mcaIndex

        fileIndex = info.get('FileIndex', fileindex)

        if fileIndex is None:
            if mcaIndex == 2:
                fileIndex = 0
            elif mcaIndex == 0:
                fileIndex = 1
            else:
                fileIndex = 0

        for i in range(3):
            if i not in [mcaIndex, fileIndex]:
                otherIndex = i
                break
        self.mcaIndex = mcaIndex
        self.fileIndex = fileIndex
        self.otherIndex = otherIndex

        self._stack.info['McaCalib'] = info.get('McaCalib', [0.0, 1.0, 0.0])
        self._stack.info['Channel0'] = info.get('Channel0', 0.0)
        self._stack.info['McaIndex'] = mcaIndex
        self._stack.info['FileIndex'] = fileIndex
        self._stack.info['OtherIndex'] = otherIndex
        self.stackUpdated(info.get("positioners", None))

    def stackUpdated(self, positioners=None):
        """
        Recalculates the different images associated to the stack
        """
        self._tryNumpy = True
        if hasattr(self._stack.data, "size"):
            if self._stack.data.size > self._dynamicLimit:
                self._tryNumpy = False
        else:
            # is not a numpy ndarray in any case
            self._tryNumpy = False

        previousStackImageSize = None
        if self._stackImageData is not None:
            previousStackImageSize = self._stackImageData.size

        mcaMax = None
        if self._tryNumpy and isinstance(self._stack.data, numpy.ndarray):
            self._stackImageData = numpy.sum(self._stack.data,
                                             axis=self.mcaIndex,
                                             dtype=numpy.float64)
            #original ICR mca
            logger.debug("(self.otherIndex, self.fileIndex) = (%d, %d)",
                         self.otherIndex, self.fileIndex)
            i = max(self.otherIndex, self.fileIndex)
            j = min(self.otherIndex, self.fileIndex)
            mcaData0 = numpy.sum(numpy.sum(self._stack.data,
                                           axis=i,
                                           dtype=numpy.float64), j)

            # max MCA
            if self.mcaIndex == -1 or (self.mcaIndex == (len(self._stack.data.shape) - 1)):
                if not numpy.all(numpy.isnan(self._stack.data)):
                    mcaMax = numpy.nanmax(numpy.nanmax(self._stack.data, axis=0), axis=0)
                else:
                    mcaMax = None  # or some default value
            elif self.mcaIndex == 0:
                if not numpy.all(numpy.isnan(self._stack.data)):
                    mcaMax = numpy.nanmax(numpy.nanmax(self._stack.data, axis=-1), axis=-1)
                else:
                    mcaMax = None
            else:
                logger.info("Unsupported index for max spectrum calculation")
        else:
            t0 = time.time()
            shape = self._stack.data.shape
            if self.mcaIndex in [2, -1]:
                self._stackImageData = numpy.zeros((shape[0], shape[1]),
                                                dtype=numpy.float64)
                mcaData0 = numpy.zeros((shape[2],), numpy.float64)
                if hasattr(numpy, "NINF"):
                    mcaMax = mcaData0 + numpy.NINF
                else:
                    mcaMax = mcaData0 - numpy.inf
                step = 1
                for i in range(shape[0]):
                    tmpData = self._stack.data[i:i+step,:,:]
                    numpy.add(self._stackImageData[i:i+step,:],
                              numpy.sum(tmpData, 2),
                              self._stackImageData[i:i+step,:])
                    tmpData = tmpData.reshape(step*shape[1], shape[2])
                    tmpMax = numpy.nanmax(tmpData, axis=0)
                    numpy.add(mcaData0, numpy.sum(tmpData, 0), mcaData0)
                    mcaMax =numpy.max([mcaMax, tmpMax], axis=0)
            elif self.mcaIndex == 0:
                self._stackImageData = numpy.zeros((shape[1], shape[2]),
                                                dtype=numpy.float64)
                mcaData0 = numpy.zeros((shape[0],), numpy.float64)
                if hasattr(numpy, "NINF"):
                    mcaMax = mcaData0 + numpy.NINF
                else:
                    mcaMax = mcaData0 - numpy.inf
                step = 1
                for i in range(shape[0]):
                    tmpData = self._stack.data[i:i+step,:,:]
                    tmpData = tmpData.reshape(tmpData.shape[1:])
                    numpy.add(self._stackImageData,
                              tmpData,
                              self._stackImageData)
                    mcaData0[i] = tmpData.sum()
                    mcaMax[i] = numpy.nanmax(tmpData)
            else:
                raise ValueError("Unhandled case 1D index = %d" % self.mcaIndex)
            logger.debug("Print dynamic loading elapsed = %f", time.time() - t0)

        logger.debug("__stackImageData.shape = %s", self._stackImageData.shape)

        if previousStackImageSize:
            if previousStackImageSize != self._stackImageData.size:
                self._clearPositioners()

        calib = self._stack.info.get('McaCalib', [0.0, 1.0, 0.0])
        dataObject = DataObject.DataObject()
        dataObject.info = {"McaCalib": calib,
                           "selectiontype": "1D",
                           "SourceName": "Stack",
                           "Key": "SUM"}
        if "McaLiveTime" in self._stack.info:
            if hasattr(self._stack.info["McaLiveTime"], "sum"):
                dataObject.info["McaLiveTime"] = \
                                self._stack.info["McaLiveTime"].sum()
            else:
                print("Not an array. Skipping time information")
                #del dataObject.info["McaLiveTime"]
        if not hasattr(self._stack, 'x'):
            self._stack.x = None
        if self._stack.x in [None, []]:
            self._stack.x = [numpy.arange(len(mcaData0)).astype(numpy.float64)+\
                                self._stack.info.get('Channel0', 0.0)]
        # for the time being it can only contain one axis
        dataObject.x = [self._stack.x[0]]

        dataObject.y = [mcaData0]

        #store the original spectrum
        self._mcaData0 = dataObject

        #store the original max spectrum
        self._mcaMax = mcaMax

        #add the original image
        self.showOriginalImage()

        #add the mca
        goodData = numpy.isfinite(self._mcaData0.y[0].sum())
        if goodData:
            self._finiteData = True
            self.showOriginalMca()
        else:
            self._finiteData = False
            self.handleNonFiniteData()

        #calculate the ROIs
        self._ROIDict = {'name': "ICR",
                         'type': "CHANNEL",
                         'calibration': calib,
                         'from': dataObject.x[0][0],
                         'to': dataObject.x[0][-1]}

        self.updateROIImages()
        if positioners is not None:
            try:
                self.setPositioners(positioners)
            except Exception:
                logging.error("Error setting positioners. Ignoring them")
                self._clearPositioners()
        for key in self.pluginInstanceDict.keys():
            self.pluginInstanceDict[key].stackUpdated()

    def getStackOriginalCurve(self):
        # TODO: Make sure copies are returned
        x = self._mcaData0.x[0]
        y = self._mcaData0.y[0]
        legend = "Stack SUM"
        info = self._mcaData0.info
        return [x, y, legend, info]

    def isStackFinite(self):
        """
        Returns True if stack does not contain inf or nans
        Returns False if stack is not finite
        """
        return self._finiteData

    def handleNonFiniteData(self):
        text  = "Your data contain infinite values or nans.\n"
        text += "Pixels containing those values will be ignored."
        logger.info(text)

    def updateROIImages(self, ddict=None):
        if ddict is None:
            updateROIDict = False
            ddict = self._ROIDict
        else:
            updateROIDict = True
        xw = ddict['calibration'][0] + \
             ddict['calibration'][1] * self._mcaData0.x[0] + \
             ddict['calibration'][2] * (self._mcaData0.x[0] ** 2)
        if ddict["name"] == "ICR":
            i1 = 0
            i2 = self._stack.data.shape[self.mcaIndex]
            imiddle = int(0.5 * (i1 + i2))
            pos = 0.5 * (ddict['from'] + ddict['to'])
            if ddict["type"].upper() != "CHANNEL":
                imiddle = max(numpy.nonzero(xw <= pos)[0])
        elif ddict["type"].upper() != "CHANNEL":
            #energy like ROI
            if xw[0] < xw[-1]:
                i1 = numpy.nonzero(ddict['from'] <= xw)[0]
                if len(i1):
                    i1 = min(i1)
                else:
                    logger.debug("updateROIImages: nothing to be made")
                    return
                i2 = numpy.nonzero(xw <= ddict['to'])[0]
                if len(i2):
                    i2 = max(i2) + 1
                else:
                    logger.debug("updateROIImages: nothing to be made")
                    return
                pos = 0.5 * (ddict['from'] + ddict['to'])
                imiddle = max(numpy.nonzero(xw <= pos)[0])
            else:
                i2 = numpy.nonzero(ddict['from'] <= xw)[0]
                if len(i2):
                    i2 = max(i2)
                else:
                    logger.debug("updateROIImages: nothing to be made")
                    return
                i1 = numpy.nonzero(xw <= ddict['to'])[0]
                if len(i1):
                    i1 = min(i1) + 1
                else:
                    logger.debug("updateROIImages: nothing to be made")
                    return
                pos = 0.5 * (ddict['from'] + ddict['to'])
                imiddle = min(numpy.nonzero(xw <= pos)[0])
        else:
            i1 = numpy.nonzero(ddict['from'] <= self._mcaData0.x[0])[0]
            if len(i1):
                if self._mcaData0.x[0][0] > self._mcaData0.x[0][-1]:
                    i1 = max(i1)
                else:
                    i1 = min(i1)
            else:
                i1 = 0
            i1 = max(i1, 0)

            i2 = numpy.nonzero(self._mcaData0.x[0] <= ddict['to'])[0]
            if len(i2):
                if self._mcaData0.x[0][0] > self._mcaData0.x[0][-1]:
                    i2 = min(i2)
                else:
                    i2 = max(i2)
            else:
                i2 = 0
            i2 = min(i2 + 1, self._stack.data.shape[self.mcaIndex])
            pos = 0.5 * (ddict['from'] + ddict['to'])
            if self._mcaData0.x[0][0] > self._mcaData0.x[0][-1]:
                imiddle = min(numpy.nonzero(self._mcaData0.x[0] <= pos)[0])
            else:
                imiddle = max(numpy.nonzero(self._mcaData0.x[0] <= pos)[0])
            xw = self._mcaData0.x[0]

        self._ROIImageDict = self.calculateROIImages(i1, i2, imiddle, energy=xw)
        if updateROIDict:
            self._ROIDict.update(ddict)

        roiKeys = ['ROI', 'Maximum', 'Minimum', 'Left', 'Middle', 'Right', 'Background']
        nImages = len(roiKeys)
        imageList = [None] * nImages
        for i in range(nImages):
            key = roiKeys[i]
            imageList[i] = self._ROIImageDict[key]

        title = "%s" % ddict["name"]
        if ddict["name"] == "ICR":
            cursor = "Energy"
            if abs(ddict['calibration'][0]) < 1.0e-5:
                if abs(ddict['calibration'][1] - 1) < 1.0e-5:
                    if abs(ddict['calibration'][2]) < 1.0e-5:
                        cursor = "Channel"
        elif ddict["type"].upper() == "CHANNEL":
            cursor = "Channel"
        else:
            cursor = ddict["type"]

        imageNames = [title,
                      '%s Maximum' % title,
                      '%s Minimum' % title,
                      '%s %.6g' % (cursor, xw[i1]),
                      '%s %.6g' % (cursor, xw[imiddle]),
                      '%s %.6g' % (cursor, xw[(i2 - 1)]),
                      '%s Background' % title]

        if self.__ROIImageCalculationIsUsingSuppliedEnergyAxis:
            imageNames[1] = "%s %s at Max." % (title, cursor)
            imageNames[2] = "%s %s at Min." % (title, cursor)

        self.showROIImageList(imageList, image_names=imageNames)

    def showOriginalImage(self):
        logger.debug("showOriginalImage to be implemented")

    def showOriginalMca(self):
        logger.debug("showOriginalMca to be implemented")

    def showROIImageList(self, imageList, image_names=None):
        self._ROIImageList = imageList
        self._ROIImageNames = image_names
        self._stackROIImageListUpdated()

    def _stackROIImageListUpdated(self):
        for key in self.pluginInstanceDict.keys():
            self.pluginInstanceDict[key].stackROIImageListUpdated()

    def getStackROIImagesAndNames(self):
        return self._ROIImageList, self._ROIImageNames

    def getStackOriginalImage(self):
        return self._stackImageData

    def calculateMcaDataObject(self, normalize=False, mask=None, mcamax=False):
        #original ICR mca
        if self._stackImageData is None:
            return
        if mask is None:
            selectionMask = self._selectionMask
        else:
            selectionMask = mask
        mcaData = None
        mcaMax = None
        goodData = numpy.isfinite(self._mcaData0.y[0].sum())
        logger.debug("Stack data is not finite")
        if (selectionMask is None) and goodData:
            if mcamax:
                # return the default maximum MCA spectrum
                dataObject = copy.deepcopy(self._mcaData0)
                dataObject.y = [self._mcaMax]
                return DataObject
            elif normalize:
                logger.debug("Case 1")
                npixels = self._stackImageData.shape[0] *\
                          self._stackImageData.shape[1] * 1.0
                dataObject = DataObject.DataObject()
                dataObject.info.update(self._mcaData0.info)
                dataObject.x = [self._mcaData0.x[0]]
                dataObject.y = [self._mcaData0.y[0] / float(npixels)]
                if "McaLiveTime" in dataObject.info:
                    dataObject.info["McaLiveTime"] /= float(npixels)
            else:
                logger.debug("Case 2")
                dataObject = self._mcaData0
            return dataObject

        #deal with NaN and inf values
        if selectionMask is None:
            if (self._ROIImageDict["ROI"] is not None) and\
               (self.mcaIndex != 0) and \
               (self._ROIImageDict["ROI"].shape == self._stackImageData.shape):
                actualSelectionMask = numpy.isfinite(self._ROIImageDict["ROI"])
            else:
                actualSelectionMask = numpy.isfinite(self._stackImageData)
        else:
            if (self._ROIImageDict["ROI"] is not None) and\
               (self.mcaIndex != 0) and \
               (self._ROIImageDict["ROI"].shape == self._stackImageData.shape):
                actualSelectionMask = selectionMask * numpy.isfinite(self._ROIImageDict["ROI"])
            else:
                actualSelectionMask = selectionMask * numpy.isfinite(self._stackImageData)

        npixels = actualSelectionMask.sum()
        if (npixels == 0) and goodData:
            if mcamax:
                # return the default maximum MCA spectrum
                dataObject = copy.deepcopy(self._mcaData0)
                dataObject.y = [self._mcaMax]
                return DataObject
            elif normalize:
                logger.debug("Case 3")
                npixels = self._stackImageData.shape[0] * self._stackImageData.shape[1] * 1.0
                dataObject = DataObject.DataObject()
                dataObject.info.update(self._mcaData0.info)
                dataObject.x = [self._mcaData0.x[0]]
                dataObject.y = [self._mcaData0.y[0] / float(npixels)]
                if "McaLiveTime" in dataObject.info:
                    dataObject.info["McaLiveTime"] /= float(npixels)
            else:
                logger.debug("Case 4")
                dataObject = self._mcaData0
            return dataObject

        mcaData = numpy.zeros(self._mcaData0.y[0].shape, dtype=numpy.float64)

        n_nonselected = self._stackImageData.shape[0] *\
                        self._stackImageData.shape[1] - npixels

        if mcamax:
            # we cannot calculate the maximum without using the actually selected pixels
            arrayMask = (actualSelectionMask > 0)
        elif goodData:
            if n_nonselected < npixels:
                arrayMask = (actualSelectionMask == 0)
            else:
                arrayMask = (actualSelectionMask > 0)
        else:
            arrayMask = (actualSelectionMask > 0)

        logger.debug("Reached MCA calculation")

        cleanMask = numpy.nonzero(arrayMask)

        logger.debug("self.fileIndex, self.mcaIndex = %d , %d",
                     self.fileIndex, self.mcaIndex)
        t0 = time.time()
        if len(cleanMask[0]) and len(cleanMask[1]):
            logger.debug("USING MASK")
            cleanMask = numpy.array(cleanMask).transpose()
            if self.fileIndex == 2:
                if self.mcaIndex == 0:
                    if isinstance(self._stack.data, numpy.ndarray):
                        logger.debug("In memory case 0")
                        for r, c in cleanMask:
                            tmpData = self._stack.data[:, r, c]
                            mcaData += tmpData
                            if mcamax:
                                if mcaMax is None:
                                    mcaMax = tmpData
                                else:
                                    mcaMax = numpy.max([mcaMax, tmpData], axis=0)
                    else:
                        logger.debug("Dynamic loading case 0")
                        #no other choice than to read all images
                        #for the time being, one by one
                        rMin = cleanMask[0][0]
                        rMax = cleanMask[-1][0]
                        cMin = cleanMask[:, 1].min()
                        cMax = cleanMask[:, 1].max()
                        #rMin, cMin = cleanMask.min(axis=0)
                        #rMax, cMax = cleanMask.max(axis=0)
                        tmpMask = arrayMask[rMin:(rMax+1),cMin:(cMax+1)]
                        tmpData = numpy.zeros((1, rMax-rMin+1,cMax-cMin+1))
                        mcaMax = numpy.zeros((self._stack.data.shape[0],), dtype=numpy.float64)
                        for i in range(self._stack.data.shape[0]):
                            tmpData[0:1,:,:] = self._stack.data[i:i+1,rMin:(rMax+1),cMin:(cMax+1)]
                            #multiplication is faster than selection
                            mcaData[i] = (tmpData[0]*tmpMask).sum(dtype=numpy.float64)
                            if mcamax:
                                mcaMax[i] = numpy.max(tmpData[0][tmpMask])
                elif self.mcaIndex == 1:
                    if isinstance(self._stack.data, numpy.ndarray):
                        for r, c in cleanMask:
                            tmpData = self._stack.data[r,:,c]
                            mcaData += tmpData
                            if mcamax:
                                if mcaMax is None:
                                    mcaMax = tmpData
                                else:
                                    mcaMax = numpy.max([mcaMax, tmpData], axis=0)
                    else:
                        raise IndexError("Dynamic loading case 1")
                else:
                    raise IndexError("Wrong combination of indices. Case 0")
            elif self.fileIndex == 1:
                if self.mcaIndex == 0:
                    if isinstance(self._stack.data, numpy.ndarray):
                        logger.debug("In memory case 2")
                        for r, c in cleanMask:
                            tmpData = self._stack.data[:, r, c]
                            mcaData += tmpData
                            if mcamax:
                                if mcaMax is None:
                                    mcaMax = tmpData
                                else:
                                    mcaMax = numpy.max([mcaMax, tmpData], axis=0)
                    else:
                        logger.debug("Dynamic loading case 2")
                        #no other choice than to read all images
                        #for the time being, one by one
                        if 1:
                            rMin = cleanMask[0][0]
                            rMax = cleanMask[-1][0]
                            cMin = cleanMask[:, 1].min()
                            cMax = cleanMask[:, 1].max()
                            #rMin, cMin = cleanMask.min(axis=0)
                            #rMax, cMax = cleanMask.max(axis=0)
                            tmpMask = arrayMask[rMin:(rMax + 1), cMin:(cMax + 1)]
                            tmpData = numpy.zeros((1, rMax - rMin + 1, cMax - cMin + 1))
                            mcaMax = numpy.zeros((self._stack.data.shape[0],), dtype=numpy.float64)
                            for i in range(self._stack.data.shape[0]):
                                tmpData[0:1, :, :] = self._stack.data[i:i + 1, rMin:(rMax + 1), cMin:(cMax + 1)]
                                # multiplication is faster than selection
                                mcaData[i] = (tmpData[0] * tmpMask).sum(dtype=numpy.float64)
                                # Multiplication does not work with negative data
                                # because zero it's already a maximum
                                if mcamax:
                                    mcaMax[i] = numpy.max(tmpData[0][tmpMask])
                        if 0:
                            tmpData = numpy.zeros((1, self._stack.data.shape[1], self._stack.data.shape[2]))
                            for i in range(self._stack.data.shape[0]):
                                tmpData[0:1, :, :] = self._stack.data[i:i + 1,:,:]
                                #multiplication is faster than selection
                                #tmpData[arrayMask].sum() in my machine
                                mcaData[i] = (tmpData[0] * arrayMask).sum(dtype=numpy.float64)
                elif self.mcaIndex == 2:
                    if isinstance(self._stack.data, numpy.ndarray):
                        logger.debug("In memory case 3")
                        for r, c in cleanMask:
                            tmpData = self._stack.data[r, c, :]
                            mcaData += tmpData
                            if mcamax:
                                if mcaMax is None:
                                    mcaMax = tmpData
                                else:
                                    mcaMax = numpy.max([mcaMax, tmpData], axis=0) 
                    else:
                        logger.debug("Dynamic loading case 3")
                        #try to minimize access to the file
                        row_list = []
                        row_dict = {}
                        for r, c in cleanMask:
                            if mcaMax is None:
                                self._stack.data[r, c, :]
                            if r not in row_list:
                                row_list.append(r)
                                row_dict[r] = []
                            row_dict[r].append(c)
                        for r in row_list:
                            tmpMcaData = self._stack.data[r:r + 1, row_dict[r], :]
                            tmpMcaData = tmpMcaData.reshape(-1, mcaData.shape[0])
                            mcaData += numpy.sum(tmpMcaData, axis=0, dtype=numpy.float64)
                            if mcamax:
                                mcaMax = numpy.max([mcaMax, numpy.max(tmpMcaData, axis=0)], axis=0)
                else:
                    raise IndexError("Wrong combination of indices. Case 1")
            elif self.fileIndex == 0:
                if self.mcaIndex == 1:
                    if isinstance(self._stack.data, numpy.ndarray):
                        logger.debug("In memory case 4")
                        for r, c in cleanMask:
                            tmpData = self._stack.data[r, :, c]
                            mcaData += tmpData
                            if mcamax:
                                if mcaMax is None:
                                    mcaMax = tmpData
                                else:
                                    mcaMax = numpy.max([mcaMax, tmpData], axis=0)
                    else:
                        raise IndexError("Dynamic loading case 4")
                elif self.mcaIndex in [2, -1]:
                    if isinstance(self._stack.data, numpy.ndarray):
                        logger.debug("In memory case 5")
                        for r, c in cleanMask:
                            tmpData = self._stack.data[r, c, :]
                            mcaData += tmpData
                            if mcamax:
                                if mcaMax is None:
                                    mcaMax = tmpData
                                else:
                                    mcaMax = numpy.max([mcaMax, tmpData], axis=0) 
                    else:
                        logger.debug("Dynamic loading case 5")
                        #try to minimize access to the file
                        row_list = []
                        row_dict = {}
                        for r, c in cleanMask:
                            if mcaMax is None:
                                mcaMax = self._stack.data[r, c, :]
                            if r not in row_list:
                                row_list.append(r)
                                row_dict[r] = []
                            row_dict[r].append(c)
                        for r in row_list:
                            tmpMcaData = self._stack.data[r:r + 1, row_dict[r], :]
                            tmpMcaData = tmpMcaData.reshape(-1, mcaData.shape[0])
                            mcaData += tmpMcaData.sum(axis=0, dtype=numpy.float64)
                            if mcamax:
                                mcaMax = numpy.max([mcaMax, numpy.max(tmpMcaData, axis=0)], axis=0)
                else:
                    raise IndexError("Wrong combination of indices. Case 2")
            else:
                raise IndexError("File index undefined")
        else:
            logger.debug("NOT USING MASK !")

        if mcamax:
            calib = self._stack.info['McaCalib']
            dataObject = DataObject.DataObject()
            dataObject.info = {"McaCalib": calib,
                               "selectiontype": "1D",
                               "SourceName": "Stack",
                               "Key": "Selection"}
            dataObject.x = [self._mcaData0.x[0]]
            dataObject.y = [mcaMax]
            return dataObject

        logger.debug("Mca sum elapsed = %f", time.time() - t0)
        if goodData:
            if n_nonselected < npixels:
                mcaData = self._mcaData0.y[0] - mcaData

        if normalize:
            mcaData = mcaData / float(npixels)

        calib = self._stack.info['McaCalib']
        dataObject = DataObject.DataObject()
        dataObject.info = {"McaCalib": calib,
                           "selectiontype": "1D",
                           "SourceName": "Stack",
                           "Key": "Selection"}
        if "McaLiveTime" in self._stack.info:
            selectedPixels = actualSelectionMask > 0
            liveTime = self._stack.info["McaLiveTime"][:]
            liveTime = liveTime.reshape(actualSelectionMask.shape)
            liveTime = liveTime[selectedPixels].sum()
            if normalize:
                liveTime = liveTime / float(npixels)
            dataObject.info["McaLiveTime"] = liveTime

        dataObject.x = [self._mcaData0.x[0]]
        dataObject.y = [mcaData]

        return dataObject

    def calculateROIImages(self, index1, index2, imiddle=None, energy=None):
        logger.debug("Calculating ROI images")
        i1 = min(index1, index2)
        i2 = max(index1, index2)
        if imiddle is None:
            imiddle = int(0.5 * (i1 + i2))
        if energy is None:
            energy = self._mcaData0.x[0]

        if i1 == i2:
            dummy = numpy.zeros(self._stackImageData.shape, numpy.float64)
            imageDict = {'ROI': dummy,
                      'Maximum': dummy,
                      'Minimum': dummy,
                      'Left': dummy,
                      'Middle': dummy,
                      'Right': dummy,
                      'Background': dummy}
            return imageDict

        isUsingSuppliedEnergyAxis = False
        if self.fileIndex == 0:
            if self.mcaIndex == 1:
                leftImage = self._stack.data[:, i1, :]
                middleImage = self._stack.data[:, imiddle, :]
                rightImage = self._stack.data[:, i2 - 1, :]
                dataImage = self._stack.data[:, i1:i2, :]
                background = 0.5 * (i2 - i1) * (leftImage + rightImage)
                roiImage = numpy.sum(dataImage, axis=1, dtype=numpy.float64)
                maxImage = energy[(numpy.argmax(dataImage, axis=1) + i1)]
                minImage = energy[(numpy.argmin(dataImage, axis=1) + i1)]
                isUsingSuppliedEnergyAxis = True
            else:
                t0 = time.time()
                if self._tryNumpy and\
                   isinstance(self._stack.data, numpy.ndarray):
                    leftImage = self._stack.data[:, :, i1]
                    middleImage = self._stack.data[:, :, imiddle]
                    rightImage = self._stack.data[:, :, i2 - 1]
                    dataImage = self._stack.data[:, :, i1:i2]
                    background = 0.5 * (i2 - i1) * (leftImage + rightImage)
                    roiImage = numpy.sum(dataImage, axis=2, dtype=numpy.float64)
                    maxImage = energy[numpy.argmax(dataImage, axis=2) + i1]
                    minImage = energy[numpy.argmin(dataImage, axis=2) + i1]
                    isUsingSuppliedEnergyAxis = True
                    logger.debug("Case 1 ROI image calculation elapsed = %f ",
                                 time.time() - t0)
                else:
                    shape = self._stack.data.shape
                    roiImage = numpy.zeros(self._stackImageData.shape,
                                           numpy.float64)
                    background = roiImage * 1
                    leftImage = roiImage * 1
                    middleImage = roiImage * 1
                    rightImage = roiImage * 1
                    maxImage = numpy.zeros(self._stackImageData.shape,
                                           numpy.uint)
                    minImage = numpy.zeros(self._stackImageData.shape,
                                           numpy.uint)
                    step = 1
                    for i in range(shape[0]):
                        tmpData = self._stack.data[i:i+step,:, i1:i2] * 1
                        numpy.add(roiImage[i:i+step,:],
                              numpy.sum(tmpData, axis=2,dtype=numpy.float64),
                              roiImage[i:i+step,:])
                        
                        minImage[i:i + step,:] = i1 + numpy.argmin(tmpData, axis=2)
                        maxImage[i:i + step, :] =  i1 + numpy.argmax(tmpData, axis=2)
                        leftImage[i:i + step, :] += tmpData[:, :, 0]
                        middleImage[i:i + step, :] += tmpData[:, :, imiddle - i1]
                        rightImage[i:i + step, :] += tmpData[:, :, -1]
                    background = 0.5 * (i2 - i1) * (leftImage + rightImage)
                    isUsingSuppliedEnergyAxis = True
                    minImage = energy[minImage]
                    maxImage = energy[maxImage]
                    logger.debug("2 Dynamic ROI image calculation elapsed = %f ",
                                 time.time() - t0)
        elif self.fileIndex == 1:
            if self.mcaIndex == 0:
                t0 = time.time()
                if isinstance(self._stack.data, numpy.ndarray) and\
                   self._tryNumpy:
                    leftImage = self._stack.data[i1, :, :]
                    middleImage= self._stack.data[imiddle, :, :]
                    rightImage = self._stack.data[i2 - 1, :, :]
                    dataImage = self._stack.data[i1:i2, :, :]
                    # this calculation is very slow but it is extremely useful
                    # for XANES studies
                    if 1:
                        maxImage = energy[numpy.argmax(dataImage, axis=0) + i1]
                        minImage = energy[numpy.argmin(dataImage, axis=0) + i1]
                    else:
                        # this is slower, but uses less memory
                        maxImage = numpy.zeros(leftImage.shape, numpy.int32)
                        minImage = numpy.zeros(leftImage.shape, numpy.int32)
                        for i in range(i1, i2):
                            tmpData = self._stack.data[i]
                            tmpData = tmpData.reshape(leftImage.shape)
                            if i == i1:
                                minImageData = tmpData * 1.0
                                maxImageData = tmpData * 1.0
                                minImage[:,:] = i1
                                maxImage[:,:] = i1
                            else:
                                tmpIndex = numpy.where(tmpData < minImageData)
                                minImage[tmpIndex] = i
                                minImageData[tmpIndex] = tmpData[tmpIndex]

                                tmpIndex = numpy.where(tmpData > maxImageData)
                                maxImage[tmpIndex] = i
                                maxImageData[tmpIndex] = tmpData[tmpIndex]
                        minImage = energy[minImage]
                        maxImage = energy[maxImage]
                    isUsingSuppliedEnergyAxis = True
                    background = 0.5 * (i2 - i1) * (leftImage + rightImage)
                    roiImage = numpy.sum(dataImage, axis=0, dtype=numpy.float64)
                    logger.debug("Case 3 ROI image calculation elapsed = %f ",
                                 time.time() - t0)
                else:
                    shape = self._stack.data.shape
                    roiImage = numpy.zeros(self._stackImageData.shape,
                                           numpy.float64)
                    background = roiImage * 1
                    leftImage = roiImage * 1
                    middleImage = roiImage * 1
                    rightImage = roiImage * 1
                    maxImage = numpy.zeros(roiImage.shape, numpy.int32)
                    minImage = numpy.zeros(roiImage.shape, numpy.int32)
                    istep = 1
                    for i in range(i1, i2):
                        tmpData = self._stack.data[i:i + istep]
                        tmpData = tmpData.reshape(roiImage.shape)
                        if i == i1:
                            minImageData = tmpData * 1.0
                            maxImageData = tmpData * 1.0
                            minImage[:,:] = i1
                            maxImage[:,:] = i1
                        else:
                            tmpIndex = numpy.where(tmpData < minImageData)
                            minImage[tmpIndex] = i
                            minImageData[tmpIndex] = tmpData[tmpIndex]

                            tmpIndex = numpy.where(tmpData > maxImageData)
                            maxImage[tmpIndex] = i
                            maxImageData[tmpIndex] = tmpData[tmpIndex]
                        numpy.add(roiImage, tmpData, roiImage)
                        if (i == i1):
                            leftImage = tmpData
                        elif (i == imiddle):
                            middleImage = tmpData
                        elif i == (i2 - 1):
                            rightImage = tmpData
                    # the used approach is twice slower than argmax, but it
                    # requires much less memory
                    isUsingSuppliedEnergyAxis = True
                    minImage = energy[minImage]
                    maxImage = energy[maxImage]
                    if i2 > i1:
                        background = (leftImage + rightImage) * 0.5 * (i2 - i1)
                    logger.debug("Case 4 Dynamic ROI elapsed = %f",
                                 time.time() - t0)
            else:
                t0 = time.time()
                if self._tryNumpy and\
                   isinstance(self._stack.data, numpy.ndarray):
                    leftImage = self._stack.data[:, :, i1]
                    middleImage = self._stack.data[:, :, imiddle]
                    rightImage = self._stack.data[:, :, i2 - 1]
                    dataImage = self._stack.data[:, :, i1:i2]
                    background = 0.5 * (i2 - i1) * (leftImage + rightImage)
                    roiImage = numpy.sum(dataImage, axis=2, dtype=numpy.float64)
                    maxImage = energy[numpy.argmax(dataImage, axis=2) + i1]
                    minImage = energy[numpy.argmin(dataImage, axis=2) + i1]
                    isUsingSuppliedEnergyAxis = True
                    logger.debug("Case 5 ROI Image elapsed = %f",
                                 time.time() - t0)
                else:
                    shape = self._stack.data.shape
                    roiImage = numpy.zeros(self._stackImageData.shape,
                                           numpy.float64)
                    background = roiImage * 1
                    leftImage = roiImage * 1
                    middleImage = roiImage * 1
                    rightImage = roiImage * 1
                    maxImage = roiImage * 1
                    minImage = roiImage * 1
                    step = 1
                    for i in range(shape[0]):
                        tmpData = self._stack.data[i:i+step,:, i1:i2] * 1
                        numpy.add(roiImage[i:i+step,:],
                              numpy.sum(tmpData, axis=2, dtype=numpy.float64),
                              roiImage[i:i+step,:])
                        numpy.add(minImage[i:i+step,:],
                                  numpy.min(tmpData, 2),
                                  minImage[i:i+step,:])
                        numpy.add(maxImage[i:i+step,:],
                                  numpy.max(tmpData, 2),
                                  maxImage[i:i+step,:])
                        leftImage[i:i+step, :]   += tmpData[:, :, 0]
                        middleImage[i:i+step, :] += tmpData[:, :, imiddle-i1]
                        rightImage[i:i+step, :]  += tmpData[:, :,-1]
                    background = 0.5*(i2-i1)*(leftImage+rightImage)
                    logger.debug("Case 6 Dynamic ROI image calculation elapsed = %f",
                                 time.time() - t0)
        else:
            #self.fileIndex = 2
            t0 = time.time()
            if self.mcaIndex == 0:
                leftImage = self._stack.data[i1]
                middleImage = self._stack.data[imiddle]
                rightImage = self._stack.data[i2 - 1]
                background = 0.5 * (i2 - i1) * (leftImage + rightImage)
                dataImage = self._stack.data[i1:i2]
                roiImage = numpy.sum(dataImage, axis=0, dtype=numpy.float64)
                minImage = energy[numpy.argmin(dataImage, axis=0) + i1]
                maxImage = energy[numpy.argmax(dataImage, axis=0) + i1]
                isUsingSuppliedEnergyAxis = True
                logger.debug("Case 7 Default ROI image calculation elapsed = %f",
                             time.time() - t0)
            else:
                leftImage = self._stack.data[:, i1, :]
                middleImage = self._stack.data[:, imiddle, :]
                rightImage = self._stack.data[:, i2 - 1, :]
                background = 0.5 * (i2 - i1) * (leftImage + rightImage)
                dataImage = self._stack.data[:, i1:i2, :]
                roiImage = numpy.sum(dataImage, axis=1, dtype=numpy.float64)
                minImage = energy[numpy.argmin(dataImage, axis=1) + i1]
                maxImage = energy[numpy.argmax(dataImage, axis=1) + i1]
                isUsingSuppliedEnergyAxis = True
                logger.debug("Case 8 Default ROI image calculation elapsed = %f",
                             time.time() - t0)

        imageDict = {'ROI': roiImage,
                     'Maximum': maxImage,
                     'Minimum': minImage,
                     'Left': leftImage,
                     'Middle': middleImage,
                     'Right': rightImage,
                     'Background': background}
        self.__ROIImageCalculationIsUsingSuppliedEnergyAxis = isUsingSuppliedEnergyAxis
        logger.debug("ROI images calculated")
        return imageDict

    def setSelectionMask(self, mask):
        logger.debug("setSelectionMask called")
        goodData = numpy.isfinite(self._mcaData0.y[0].sum())

        if goodData:
            self._selectionMask = mask
        else:
            if (self._ROIImageDict["ROI"] is not None) and\
               (self.mcaIndex != 0):
                self._selectionMask = mask * numpy.isfinite(self._ROIImageDict["ROI"])
            else:
                self._selectionMask = mask * numpy.isfinite(self._stackImageData)

        for key in self.pluginInstanceDict.keys():
            self.pluginInstanceDict[key].selectionMaskUpdated()

    def getSelectionMask(self):
        logger.debug("getSelectionMask called")
        return self._selectionMask

    def addImage(self, image, name, info=None, replace=False, replot=True):
        """
        Add image data to the RGB correlator
        """
        print("Add image data not implemented")

    def removeImage(self, name, replace=True):
        """
        Remove image data from the RGB correlator
        """
        print("Remove image data not implemented")


    def addCurve(self, x, y, legend=None, info=None, replace=False, replot=True):
        """
        Add the 1D curve given by x an y to the graph.
        """
        print("addCurve not implemented")
        return None

    def removeCurve(self, legend, replot=True):
        """
        Remove the curve associated to the supplied legend from the graph.
        The graph will be updated if replot is true.
        """
        print("removeCurve not implemented")
        return None

    def getGraphXLabel(self):
        print("getGraphXLabel not implemented")
        return None

    def getGraphYLabel(self):
        print("getGraphYLabel not implemented")
        return None

    def getActiveCurve(self):
        """
        Function to access the currently active curve.
        It returns None in case of not having an active curve.

        Default output has the form:
            xvalues, yvalues, legend, dict
            where dict is a dictionary containing curve info.
            For the time being, only the plot labels associated to the
            curve are warranted to be present under the keys xlabel, ylabel.

        If just_legend is True:
            The legend of the active curve (or None) is returned.
        """
        logger.debug("getActiveCurve default implementation")
        info = {}
        info['xlabel'] = 'Channel'
        info['ylabel'] = 'Counts'
        legend = 'ICR Spectrum'
        return self._mcaData0.x[0], self._mcaData0.y[0], legend, info

    def getGraphXLimits(self):
        logger.debug("getGraphXLimits default implementation")
        return self._mcaData0.x[0].min(), self._mcaData0.x[0].max()

    def getGraphYLimits(self):
        logger.debug("getGraphYLimits default implementation")
        return self._mcaData0.y[0].min(), self._mcaData0.y[0].max()

    def getStackDataObject(self):
        return self._stack

    def getStackData(self):
        return self._stack.data

    def getStackInfo(self):
        return self._stack.info

    def setPositioners(self, positioners, copy=True):
        """Updates the "positioners" field in the stack info, after
        checking that the provided positioners have the proper number of
        values.

        :param dict positioners: Dictionary of positioners. The keys are
            the motor names. The values should preferably be arrays with
            the same number of values as there are stack pixels. Scalars
            are accepted if the positioner has a constant value.
        :param bool copy: If *True* (default), store a copy of the data.
            If *False*, store the original data whenever it is possible.
            If the dictionary contains lists, they need to be converted to
            numpy arrays and a copy is mandatory.
        :raise: TypeError if positioners is not a dict or if any positioner
            is not a scalar, list or numpy array.
        :raise: RuntimeError if any positioner is a list and copy=False
        """
        if not hasattr(positioners, "items"):
            raise TypeError("Dictionary expected for positioners")

        npixels = self.getStackOriginalImage().size
        stackPositioners = {}

        for motorName, motorValues in positioners.items():
            if numpy.isscalar(motorValues) or \
                    (hasattr(motorValues, "ndim") and
                     motorValues.ndim == 0):
                stackPositioners[motorName] = motorValues
            elif hasattr(motorValues, "size"):
                # numpy array
                numMotorValues = motorValues.size
                if numMotorValues == npixels:
                    stackPositioners[motorName] = numpy.array(motorValues,
                                                              copy=copy)
            elif hasattr(motorValues, "__len__") and numpy.isscalar(motorValues[0]):
                # list: convert to numpy array before storing in info
                numMotorValues = len(motorValues)
                if numMotorValues == npixels:
                    stackPositioners[motorName] = numpy.array(motorValues)
            else:
                raise TypeError(
                        "Wrong type for positioner %s. " % motorName +
                        "Valid types are numpy arrays, scalars or list of scalars.")

        if len(stackPositioners) != len(positioners):
            ignored_motors = list(set(positioners.keys()) -
                                  set(stackPositioners.keys()))
            logger.debug("Ignored motors due to mismatch in number of values: %s",
                          ', '.join(ignored_motors))

        self._stack.info["positioners"] = stackPositioners

    def _clearPositioners(self):
        """Removes the "positioners" field in the stack info"""
        if "positioners" in self._stack.info:
            self._stack.info["positioners"] = {}

    def getPositionersFromIndex(self, index):
        """Return the value of all positioners for the spectrum identified by
        its 1D index.

        If positioners are stored as 1D arrays ``a``, the value returned
        is simply ``a[index]``.

        If positioners are stored as 2D arrays, the index is applied to the
        flattened array.

        :param int index: Index of spectrum for which the the positioners
            value is to be returned.
        :return: dictionary of positioners values whose keys are the motor
            name
        :rtype: dict
        """
        positioners = self._stack.info.get("positioners", {})
        positionersAtIdx = {}

        if index >= self.getStackOriginalImage().size or index < 0:
            raise IndexError("index out of bounds")

        for motorName, motorValues in positioners.items():
            # assert numpy.isscalar(motorValues) or hasattr(motorValues, "shape")
            if numpy.isscalar(motorValues):
                positionersAtIdx[motorName] = motorValues
            elif len(motorValues.shape) == 1:
                positionersAtIdx[motorName] = motorValues[index]
            else:
                positionersAtIdx[motorName] = motorValues.reshape((-1,))[index]

        return positionersAtIdx


def test():
    #create a dummy stack
    nrows = 100
    ncols = 200
    nchannels = 1024
    a = numpy.ones((nrows, ncols), numpy.float64)
    stackData = numpy.zeros((nrows, ncols, nchannels), numpy.float64)
    for i in range(nchannels):
        stackData[:, :, i] = a * i
    stack = StackBase()

    stack.setStack(stackData, mcaindex=2)
    print("This should be 0 = %f" % stack.calculateROIImages(0, 0)['ROI'].sum())
    print("This should be 0 = %f" % stack.calculateROIImages(0, 1)['ROI'].sum())
    print("%f should be = %f" %\
          (stackData[:, :, 0:10].sum(),
           stack.calculateROIImages(0, 10)['ROI'].sum()))


if __name__ == "__main__":
    test()
