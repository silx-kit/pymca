# /*#########################################################################
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
# ###########################################################################*/
__authors__ = ["V.A. Sole", "P. Knobel"]
__contact__ = "sole@esrf.fr"
__license__ = "MIT"


import numpy

from PyMca5.PyMcaGui import PyMcaQt as qt
if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = str
from PyMca5.PyMcaGui.plotting.PyMca_Icons import IconDict
from PyMca5.PyMcaGui.plotting import SilxMaskImageWidget


class SilxExternalImagesWindow(SilxMaskImageWidget.SilxMaskImageWidget):
    """Widget displaying a single external image meant to be used as a
    background image underneath the stack data (e.g. sample photo).

    Crop and rotate operations can be applied to the image to align it
    with the data.

    It is technically possible to add multiple background image with
    different origins and sizes. They will all be plotted on the same
    background layer. But he crop and rotation operations will only be
    applied to the first image.
    """
    def __init__(self, parent=None):
        SilxMaskImageWidget.SilxMaskImageWidget.__init__(self, parent=parent)

        # Additional actions added to action group
        self.cropIcon = qt.QIcon(qt.QPixmap(IconDict["crop"]))
        self.cropButton = qt.QToolButton(self)
        self.cropButton.setIcon(self.cropIcon)
        self.cropButton.setToolTip("Crop image to current zoomed area")
        self.cropButton.clicked.connect(self._cropIconChecked)

        self.hFlipIcon = qt.QIcon(qt.QPixmap(IconDict["gioconda16mirror"]))
        self.hFlipToolButton = qt.QToolButton(self)
        self.hFlipToolButton.setIcon(self.hFlipIcon)
        self.hFlipToolButton.setToolTip("Flip image and data, not the scale.")
        self._flipMenu = qt.QMenu()
        self._flipMenu.addAction(QString("Flip Image Left-Right"),
                                 self._flipLeftRight)
        self._flipMenu.addAction(QString("Flip Image Up-Down"),
                                 self._flipUpDown)

        self.hFlipToolButton.setMenu(self._flipMenu)
        self.hFlipToolButton.setPopupMode(qt.QToolButton.InstantPopup)

        self.rotateLeftIcon = qt.QIcon(qt.QPixmap(IconDict["rotate_left"]))
        self.rotateRightIcon = qt.QIcon(qt.QPixmap(IconDict["rotate_right"]))
        self.rotateButton = qt.QToolButton(self)
        self.rotateButton.setIcon(self.rotateLeftIcon)
        self.rotateButton.setToolTip("Rotate image by 90 degrees")
        self._rotateMenu = qt.QMenu()
        self.rotateLeftAction = qt.QAction(self.rotateLeftIcon,
                                           QString("Rotate left"),
                                           self)
        self.rotateLeftAction.triggered.connect(self._rotateLeft)
        self._rotateMenu.addAction(self.rotateLeftAction)
        self.rotateRightAction = qt.QAction(self.rotateRightIcon,
                                            QString("Rotate right"),
                                            self)
        self.rotateRightAction.triggered.connect(self._rotateRight)
        self._rotateMenu.addAction(self.rotateRightAction)

        self.rotateButton.setMenu(self._rotateMenu)
        self.rotateButton.setPopupMode(qt.QToolButton.InstantPopup)

        toolbar = qt.QToolBar("Image edition", parent=self)

        # custom widgets added to the end
        toolbar.addWidget(self.cropButton)
        toolbar.addWidget(self.hFlipToolButton)
        toolbar.addWidget(self.rotateButton)
        self.addToolBar(toolbar)

        # hide stack image slider, show transparency slider
        self.slider.hide()
        self.setAlphaSliderVisible(True)
        self.setImagesAlpha(0.)

    def _getCurrentBgHeightWidth(self):
        """Return height and width for the main bg image"""
        image = self._bg_images[0]
        ncols = image.shape[1]
        nrows = image.shape[0]
        width = ncols * self._bg_deltaXY[0][0]   # X
        height = nrows * self._bg_deltaXY[0][1]  # Y
        return height, width

    def _getAllBgHeightsWidths(self):
        widths = []
        heights = []
        for i, img in enumerate(self._bg_images):
            ncols = img.shape[1]
            nrows = img.shape[0]
            widths.append(ncols * self._bg_deltaXY[i][0])
            heights.append(nrows * self._bg_deltaXY[i][1])
        return heights, widths

    def _updateBgImages(self):
        """Reset background images after they changed"""
        heights, widths = self._getAllBgHeightsWidths()

        self.setBackgroundImages(self._bg_images,
                                 self._bg_labels,
                                 origins=self._bg_origins,
                                 widths=widths,
                                 heights=heights)

    def _cropIconChecked(self):
        """Crop first background image to the X and Y ranges
        currently displayed (crop to zoomed area)"""
        heights, widths = self._getAllBgHeightsWidths()

        xmin, xmax = self.plot.getGraphXLimits()
        ymin, ymax = self.plot.getGraphYLimits()

        # crop must select an area within the original image's bounds
        xmin = max(xmin, self._bg_origins[0][0])
        xmax = min(xmax, self._bg_origins[0][0] + widths[0])
        ymin = max(ymin, self._bg_origins[0][1])
        ymax = min(ymax, self._bg_origins[0][1] + heights[0])

        cols_min = int((xmin - self._bg_origins[0][0]) / self._bg_deltaXY[0][0])
        cols_max = int((xmax - self._bg_origins[0][0]) / self._bg_deltaXY[0][0])
        rows_min = int((ymin - self._bg_origins[0][1]) / self._bg_deltaXY[0][1])
        rows_max = int((ymax - self._bg_origins[0][1]) / self._bg_deltaXY[0][1])

        self._bg_images[0] = self._bg_images[0][rows_min:rows_max, cols_min:cols_max]
        # after a crop, we need to recalculate :attr:`_bg_deltaXY`
        self._updateBgScales(heights, widths)

        self._updateBgImages()

        self.sigMaskImageWidget.emit(
                {'event': "cropSignal"})

    def _flipUpDown(self):
        """Flip 1st bg image upside down"""
        self._bg_images[0] = numpy.flipud(self._bg_images[0])

        self.sigMaskImageWidget.emit(
                {'event': "flipUpDownSignal"})

        self._updateBgImages()

    def _flipLeftRight(self):
        self._bg_images[0] = numpy.fliplr(self._bg_images[0])

        self.sigMaskImageWidget.emit(
                {'event': "flipLeftRightSignal"})

        self._updateBgImages()

    def _rotateRight(self):
        """Rotate the image 90 degrees clockwise.

        Depending on the Y axis orientation, the array must be
        rotated by 90 or 270 degrees."""
        heights, widths = self._getAllBgHeightsWidths()
        if not self.plot.isYAxisInverted():
            self._bg_images[0] = numpy.rot90(self._bg_images[0], 1)
        else:
            self._bg_images[0] = numpy.rot90(self._bg_images[0], 3)

        self.sigMaskImageWidget.emit(
                {'event': "rotateRight"})

        self._updateBgScales(heights, widths)
        self._updateBgImages()

    def _rotateLeft(self):
        """Rotate the image 90 degrees counterclockwise.

        Depending on the Y axis orientation, the array must be
        rotated by 90 or 270 degrees."""
        heights, widths = self._getAllBgHeightsWidths()
        if not self.plot.isYAxisInverted():
            self._bg_images[0] = numpy.rot90(self._bg_images[0], 3)
        else:
            self._bg_images[0] = numpy.rot90(self._bg_images[0], 1)

        self.sigMaskImageWidget.emit(
                {'event': "rotateLeft"})

        self._updateBgScales(heights, widths)
        self._updateBgImages()

    # overload methods to send the bg image in the signal
    def _addImageClicked(self):
        imageData = self.getFirstBgImageData()
        ddict = {
            'event': "addImageClicked",
            'image': imageData,
            'title': self.plot.getGraphTitle(),
            'id': id(self)}
        self.sigMaskImageWidget.emit(ddict)

    def _replaceImageClicked(self):
        imageData = self.getFirstBgImageData()
        ddict = {
            'event': "replaceImageClicked",
            'image': imageData,
            'title': self.plot.getGraphTitle(),
            'id': id(self)}
        self.sigMaskImageWidget.emit(ddict)

    def _removeImageClicked(self):
        imageData = self.getFirstBgImageData()
        ddict = {
            'event': "removeImageClicked",
            'image': imageData,
            'title': self.plot.getGraphTitle(),
            'id': id(self)}
        self.sigMaskImageWidget.emit(ddict)

    # overload show image to ensure the stack data
    # does not change the background title
    def showImage(self, index=0):
        SilxMaskImageWidget.SilxMaskImageWidget.showImage(self, index)
        if self._bg_labels:
            self.plot.setGraphTitle(self._bg_labels[0])


def test():
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)

    data = numpy.arange(10000)
    data = data.reshape(50, 200)
    data[8:12, 48:52] = 10000
    data[6:14, 146:154] = 10000
    data[34:46, 44:56] = 0
    data[32:48, 142:158] = 0

    container = SilxExternalImagesWindow()
    container.setBackgroundImages([data])
    container.show()

    def theSlot(ddict):
        print(ddict)

    container.sigMaskImageWidget.connect(theSlot)

    app.exec()

if __name__ == "__main__":
    test()
