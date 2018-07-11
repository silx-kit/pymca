#/*##########################################################################
# Copyright (C) 2004-2017 V.A. Sole, European Synchrotron Radiation Facility
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
"""
This plugin open a file selection dialog to open one or more images in a
new window. Usual image data formats are supported, as well as standard
image formats (JPG, PNG).

The tool is meant to view an alternative view of the data, such as a
photograph of the sample or a different type of scientific measurement
of the same sample.

The window offer a cropping tool, to crop the image to the current visible
zoomed area and then resize it to fit the original size.

The mask of this plot widget is synchronized with the master stack widget.
"""
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import os
import logging
from PyMca5 import StackPluginBase
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaIO import EDFStack
from PyMca5.PyMcaGui import PyMcaFileDialogs
from PyMca5.PyMcaGui import StackPluginResultsWindow
from PyMca5.PyMcaGui import ExternalImagesWindow
from PyMca5.PyMcaGui import PyMca_Icons as PyMca_Icons

_logger = logging.getLogger(__name__)


class ExternalImagesStackPlugin(StackPluginBase.StackPluginBase):
    def __init__(self, stackWindow, **kw):
        if _logger.getEffectiveLevel() == logging.DEBUG:
            StackPluginBase.pluginBaseLogger.setLevel(logging.DEBUG)
        StackPluginBase.StackPluginBase.__init__(self, stackWindow, **kw)
        self.methodDict = {'Load':[self._loadImageFiles,
                                   "Load Images",
                                   PyMca_Icons.fileopen],
                           'Show':[self._showWidget,
                                   "Show Image Browser",
                                   PyMca_Icons.brushselect]}
        self.__methodKeys = ['Load', 'Show']
        self.widget = None

    def stackUpdated(self):
        self.widget = None

    def selectionMaskUpdated(self):
        if self.widget is None:
            return
        if self.widget.isHidden():
            return
        mask = self.getStackSelectionMask()
        self.widget.setSelectionMask(mask)

    def mySlot(self, ddict):
        _logger.debug("mySlot %s %s", ddict['event'], ddict.keys())
        if ddict['event'] == "selectionMaskChanged":
            self.setStackSelectionMask(ddict['current'])
        elif ddict['event'] == "addImageClicked":
            self.addImage(ddict['image'], ddict['title'])
        elif ddict['event'] == "removeImageClicked":
            self.removeImage(ddict['title'])
        elif ddict['event'] == "replaceImageClicked":
            self.replaceImage(ddict['image'], ddict['title'])
        elif ddict['event'] == "resetSelection":
            self.setStackSelectionMask(None)

    #Methods implemented by the plugin
    def getMethods(self):
        if self.widget is None:
            return [self.__methodKeys[0]]
        else:
            return self.__methodKeys

    def getMethodToolTip(self, name):
        return self.methodDict[name][1]

    def getMethodPixmap(self, name):
        return self.methodDict[name][2]

    def applyMethod(self, name):
        return self.methodDict[name][0]()

    def _loadImageFiles(self):
        if self.getStackDataObject() is None:
            return
        getfilter = True
        fileTypeList = ["PNG Files (*png)",
                        "JPEG Files (*jpg *jpeg)",
                        "IMAGE Files (*)",
                        "DAT Files (*dat)",
                        "CSV Files (*csv)",
                        "EDF Files (*edf)",
                        "EDF Files (*ccd)",
                        "EDF Files (*)"]
        message = "Open image file"
        filenamelist, filefilter = PyMcaFileDialogs.getFileList(parent=None,
                                    filetypelist=fileTypeList,
                                    message=message,
                                    getfilter=getfilter,
                                    single=False,
                                    currentfilter=None)
        if len(filenamelist) < 1:
            return
        imagelist = []
        imagenames= []
        mask = self.getStackSelectionMask()
        if mask is None:
            r, n = self.getStackROIImagesAndNames()
            shape = r[0].shape
        else:
            shape = mask.shape
        extension = qt.safe_str(os.path.splitext(filenamelist[0])[1])
        if (filefilter.split()[0] in ["EDF"]) or \
           (extension.upper() in [".EDF", ".TIF"]):
            for filename in filenamelist:
                #read the edf file
                edf = EDFStack.EdfFileDataSource.EdfFileDataSource(filename)

                #the list of images
                keylist = edf.getSourceInfo()['KeyList']
                if len(keylist) < 1:
                    msg = qt.QMessageBox(None)
                    msg.setIcon(qt.QMessageBox.Critical)
                    msg.setText("Cannot read image from file")
                    msg.exec_()
                    return

                for key in keylist:
                    #get the data
                    dataObject = edf.getDataObject(key)
                    data = dataObject.data
                    if data.shape[0] not in shape:
                        continue
                    if data.shape[1] not in shape:
                        continue
                    imagename  = dataObject.info.get('Title', "")
                    if imagename != "":
                        imagename += " "
                    imagename += os.path.basename(filename)+" "+key
                    imagelist.append(data)
                    imagenames.append(imagename)
            if len(imagelist) == 0:
                msg = qt.QMessageBox(None)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Cannot read a valid image from the file")
                msg.exec_()
                return
            crop = False
            self.widget = StackPluginResultsWindow.StackPluginResultsWindow(parent=None,
                                                    usetab=False)
            self.widget.buildAndConnectImageButtonBox()
            self.widget.sigMaskImageWidgetSignal.connect(self.mySlot)
            self.widget.setStackPluginResults(imagelist,
                                              image_names=imagenames)
            self._showWidget()
            return
        elif extension.lower() in [".csv", ".dat"]:
            # what to do if more than one file selected ?
            from PyMca5.PyMca import specfilewrapper as Specfile
            sf = Specfile.Specfile(filenamelist[0])
            scan = sf[0]
            labels = scan.alllabels()
            data = scan.data()
            scan = None
            sf = None
            if "column" in labels:
                offset = labels.index("column")
                ncols = int(data[offset].max() + 1)
                offset += 1
            else:
                raise IOError("Only images exported as csv supported")
            imagelist = []
            imagenames= []
            for i in range(offset, len(labels)):
                if labels[i].startswith("s("):
                    continue
                tmpData = data[i]
                tmpData.shape = -1, ncols
                imagelist.append(tmpData)
                imagenames.append(labels[i])
            crop = False
            self.widget = StackPluginResultsWindow.StackPluginResultsWindow(parent=None,
                                                    usetab=False)
            self.widget.buildAndConnectImageButtonBox()
            self.widget.sigMaskImageWidgetSignal.connect(self.mySlot)
            self.widget.setStackPluginResults(imagelist,
                                              image_names=imagenames)
            self._showWidget()
            return
        else:
            #Try pure Image formats
            for filename in filenamelist:
                image = qt.QImage(filename)
                if image.isNull():
                    msg = qt.QMessageBox(None)
                    msg.setIcon(qt.QMessageBox.Critical)
                    msg.setText("Cannot read file %s as an image" % filename)
                    msg.exec_()
                    return
                imagelist.append(image)
                imagenames.append(os.path.basename(filename))

            if len(imagelist) == 0:
                msg = qt.QMessageBox(None)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Cannot read a valid image from the file")
                msg.exec_()
                return
            self.widget = ExternalImagesWindow.ExternalImagesWindow(parent=None,
                                                    rgbwidget=None,
                                                    selection=True,
                                                    colormap=True,
                                                    imageicons=True,
                                                    standalonesave=True)
            self.widget.buildAndConnectImageButtonBox()
            self.widget.sigMaskImageWidgetSignal.connect(self.mySlot)
            self.widget.setImageData(None)
            self.widget.setQImageList(imagelist, shape[1], shape[0],
                                                clearmask=False,
                                                data=None,
                                                imagenames=imagenames)
                                                #data=self.__stackImageData)
            self._showWidget()
            return


    def _showWidget(self):
        if self.widget is None:
            return

        #Show
        self.widget.show()
        self.widget.raise_()

        #update
        self.selectionMaskUpdated()


MENU_TEXT = "External Images Tool"
def getStackPluginInstance(stackWindow, **kw):
    ob = ExternalImagesStackPlugin(stackWindow)
    return ob
