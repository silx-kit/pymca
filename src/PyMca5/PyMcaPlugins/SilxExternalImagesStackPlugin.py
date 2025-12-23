# /*#########################################################################
# Copyright (C) 2004-2022 European Synchrotron Radiation Facility
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
# ###########################################################################*/
"""This plugin open a file selection dialog to open an image in a
new window. Usual image data formats are supported, as well as standard
image formats (JPG, PNG).

The tool is meant to view an alternative view of the data, such as a
photograph of the sample or a different type of scientific measurement
of the same sample, and to compare it with the image displayed in the
primary stack window.

The primary image is overlaid with the newly opened image, and its
level of transparency can be configured with a slider.

The window offer a cropping tool, to crop the image to the current visible
zoomed area and then resize it to fit the original size. It also provides
a tool to rotate the image.

The mask of the plot widget is synchronized with the primary stack widget."""

__authors__ = ["V.A. Sole", "P. Knobel", "W. De Nolf"]
__contact__ = "sole@esrf.fr"
__license__ = "MIT"


import os
import numpy

from PyMca5.PyMcaGui import ExternalImagesStackPluginBase
from PyMca5.PyMcaGui import SilxExternalImagesWindow
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui import PyMca_Icons as PyMca_Icons

# temporarily disable logging when importing silx and fabio
import logging
logging.basicConfig()
logging.disable(logging.ERROR)

from silx.image.bilinear import BilinearImage

logging.disable(logging.NOTSET)


# TODO: in the future maybe we want to change the RGB correlator to accept different image
# sizes and we won't need resizing anymore
def resize_image(original_image, new_shape):
    """Return resized image

    :param original_image:
    :param tuple(int) new_shape: New image shape (rows, columns)
    :return: New resized image, as a 2D numpy array
    """
    bilinimg = BilinearImage(original_image)

    row_array, column_array = numpy.meshgrid(
            numpy.linspace(0, original_image.shape[0], int(new_shape[0])),
            numpy.linspace(0, original_image.shape[1], int(new_shape[1])),
            indexing="ij")

    interpolated_values = bilinimg.map_coordinates((row_array, column_array))

    interpolated_values = interpolated_values.reshape(*new_shape)
    return interpolated_values


class SilxExternalImagesStackPlugin(ExternalImagesStackPluginBase.ExternalImagesStackPluginBase):

    def __init__(self, stackWindow):
        ExternalImagesStackPluginBase.ExternalImagesStackPluginBase.__init__(self, stackWindow)
        self.methodDict = {'Load': [self._loadImageFiles,
                                    "Load Images",
                                    PyMca_Icons.fileopen],
                           'Show': [self._showMenu,
                                    "Select an image to show it",
                                    PyMca_Icons.brushselect],
                           'Clear images': [self._clearAllWidgets,
                                            "Clear open images"]}
        self.__methodKeys = ['Load', 'Show', 'Clear images']
        self.windows = {}
        """Dictionary of SilxExternalImagesWindow widgets indexed
        by their background image label."""

    def stackUpdated(self):
        self.windows = {}

    def selectionMaskUpdated(self):
        if not self.windows:
            return
        mask = self.getStackSelectionMask()
        for w in self.windows.values():
            if not w.isHidden():
                w.setSelectionMask(mask)

    def stackClosed(self):
        for label in self.windows:
            self.windows[label].close()

    def onWidgetSignal(self, ddict):
        """triggered by self.windows["foo"].sigMaskImageWidget"""
        if ddict['event'] == "selectionMaskChanged":
            self.setStackSelectionMask(ddict["current"])
        elif ddict['event'] == "removeImageClicked":
            self.removeImage(ddict['title'])
        elif ddict['event'] in ["addImageClicked", "replaceImageClicked"]:
            # resize external image to the stack shape
            stack_image_shape = self._getStackImageShape()
            external_image = ddict['image']
            resized_image = resize_image(external_image, stack_image_shape)

            if ddict['event'] == "addImageClicked":
                self.addImage(resized_image, ddict['title'])
            elif ddict['event'] == "replaceImageClicked":
                self.replaceImage(resized_image, ddict['title'])
        elif ddict['event'] == "resetSelection":
            self.setStackSelectionMask(None)
        elif ddict['event'] in ["cropSignal", "flipUpDownSignal",
                                "flipLeftRightSignal", "rotateRight",
                                "rotateLeft"]:
            self._onBgImageChanged()

    #Methods implemented by the plugin
    def getMethods(self):
        if not self.windows:
            return [self.__methodKeys[0]]  # only Load
        else:
            return self.__methodKeys  # Load and show

    def getMethodToolTip(self, name):
        return self.methodDict[name][1]

    def getMethodPixmap(self, name):
        if len(self.methodDict[name]) < 3:
            return None
        return self.methodDict[name][2]

    def applyMethod(self, name):
        return self.methodDict[name][0]()

    def _createStackPluginWindow(self, imagenames, imagelist):
        image_shape = self._getStackImageShape()
        origin, delta = self._getStackOriginDelta()
        h = delta[1] * image_shape[0]
        w = delta[0] * image_shape[1]
        stack_images, stack_names = self.getStackROIImagesAndNames()
        stack_info = self.getStackInfo()
        if "bgimages" not in stack_info:
            stack_info["bgimages"] = {}
        for bgimg, bglabel in zip(imagelist, imagenames):
            if bglabel not in self.windows:
                self.windows[bglabel] = SilxExternalImagesWindow.SilxExternalImagesWindow()
                self.windows[bglabel].sigMaskImageWidget.connect(
                        self.onWidgetSignal)
            self.windows[bglabel].show()
            # add the stack image for mask operation
            self.windows[bglabel].setImages([stack_images[0]],
                                            labels=[stack_names[0]],
                                            origin=origin, width=w, height=h)
            self.windows[bglabel].plot.getImage("current").setAlpha(0)
            # add the external image
            self.windows[bglabel].setBackgroundImages([bgimg],
                                                      labels=[bglabel],
                                                      origins=[origin],
                                                      widths=[w],
                                                      heights=[h])
            self.windows[bglabel].plot.setGraphTitle(bglabel)
            # also store bg images as a stack info attribute
            stack_info["bgimages"][bglabel] = {"data": bgimg,
                                               "origin": origin,
                                               "width": w,
                                               "height": h}
            self._showWidget(bglabel)

    def _createStackPluginWindowQImage(self, imagenames, imagelist):
        imagelist = list(map(self.qImageToRgba, imagelist))
        self._createStackPluginWindow(imagenames, imagelist)

    def _onBgImageChanged(self):
        """Update bg images in stack info dict"""
        stack_info = self.getStackInfo()
        if "bgimages" not in stack_info:
            stack_info["bgimages"] = {}
        for win in self.windows.values():
            stack_info["bgimages"].update(win.getBgImagesDict())

    def _getStackOriginDelta(self):
        info = self.getStackInfo()

        xscale = info.get("xScale", [0.0, 1.0])
        yscale = info.get("yScale", [0.0, 1.0])

        origin = xscale[0], yscale[0]
        delta = xscale[1], yscale[1]

        return origin, delta

    def _getStackImageShape(self):
        """Return 2D stack image shape"""
        image_shape = list(self.getStackOriginalImage().shape)
        return image_shape

    def _showWidget(self, label):
        if label not in self.windows:
            return

        #Show
        self.windows[label].show()
        self.windows[label].raise_()

        #update
        self.selectionMaskUpdated()

    def _showMenu(self):
        """Create a show menu allowing to show any of the existing external
        image windows"""
        if len(self.windows) == 1:
            label = self.windows.keys()[0]
            self.windows[label].showAndRaise()
            return
        showMenu = qt.QMenu()
        for label in self.windows:
            action = qt.QAction(label, showMenu)
            action.setToolTip('Show window displaying image "%s"' % label)
            action.triggered.connect(self.windows[label].showAndRaise)
            showMenu.addAction(action)

        showMenu.exec_(qt.QCursor.pos())

    def _clearAllWidgets(self):
        # delete widgets
        for label in self.windows:
            self.windows[label].deleteLater()
        # clear dict
        self.windows.clear()

    @staticmethod
    def qImageToRgba(qimage):
        width = qimage.width()
        height = qimage.height()
        if qimage.format() == qt.QImage.Format_Indexed8:
            pixmap0 = numpy.frombuffer(qimage.bits().asstring(width * height),
                                       dtype=numpy.uint8)
            pixmap = numpy.zeros((height * width, 4), numpy.uint8)
            pixmap[:, 0] = pixmap0[:]
            pixmap[:, 1] = pixmap0[:]
            pixmap[:, 2] = pixmap0[:]
            pixmap[:, 3] = 255
            pixmap = pixmap.reshape(height, width, 4)
        else:
            qimage = qimage.convertToFormat(qt.QImage.Format_ARGB32)
            pixmap0 = numpy.frombuffer(qimage.bits().asstring(width * height * 4),
                                       dtype=numpy.uint8)
            pixmap = numpy.array(pixmap0)  # copy
            pixmap = pixmap.reshape(height, width, -1)
            # Qt uses BGRA, convert to RGBA
            tmpBuffer = numpy.array(pixmap[:, :, 0], copy=True, dtype=pixmap.dtype)
            pixmap[:, :, 0] = pixmap[:, :, 2]
            pixmap[:, :, 2] = tmpBuffer
        return pixmap

    @property
    def _dialogParent(self):
        if self.windows:
            return next(iter(self.windows.values()))
        else:
            return None


MENU_TEXT = "Silx External Images Tool"


def getStackPluginInstance(stackWindow, **kw):
    ob = SilxExternalImagesStackPlugin(stackWindow)
    return ob
