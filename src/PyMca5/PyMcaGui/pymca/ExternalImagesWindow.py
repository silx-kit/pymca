#/*##########################################################################
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
#############################################################################*/
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import sys
import os
import numpy

from PyMca5.PyMcaGui import PyMcaQt as qt
if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = str
from PyMca5.PyMcaGui.plotting.PyMca_Icons import IconDict
from PyMca5.PyMcaGui.plotting import MaskImageWidget
from PyMca5.PyMcaIO import EdfFile
EDF = True

class ExternalImagesWindow(MaskImageWidget.MaskImageWidget):
    def __init__(self, *var, **kw):
        ddict = {}
        ddict['usetab'] = False
        ddict.update(kw)
        ddict['standalonesave'] = False
        if 'aspect' not in kw:
            ddict['aspect'] = True
        if 'dynamic' in kw:
            del ddict['dynamic']
        if 'crop' in kw:
            del ddict['crop']
        if 'depthselection' in kw:
            del ddict['depthselection']
        self._depthSelection = kw.get('depthselection', False)
        MaskImageWidget.MaskImageWidget.__init__(self, *var, **ddict)
        self.slider = qt.QSlider(self)
        self.slider.setOrientation(qt.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)

        self.mainLayout.addWidget(self.slider)
        self.slider.valueChanged[int].connect(self._showImage)

        self.imageList = None
        self._imageDict = None
        self.imageNames = None
        self._stack = None
        standalonesave = kw.get("standalonesave", True)
        if standalonesave:
            self.graphWidget.saveToolButton.clicked.connect(\
                         self._saveToolButtonSignal)
            self._saveMenu = qt.QMenu()
            self._saveMenu.addAction(QString("Image Data"),
                                     self.saveImageList)
            self._saveMenu.addAction(QString("Standard Graphics"),
                                     self.graphWidget._saveIconSignal)
            self._saveMenu.addAction(QString("Matplotlib") ,
                                     self._saveMatplotlibImage)

        dynamic = kw.get("dynamic", False)
        self._dynamic = dynamic

        crop = kw.get("crop", True)
        if crop:
            self.cropIcon = qt.QIcon(qt.QPixmap(IconDict["crop"]))
            infotext = "Crop image to the currently zoomed window"
            cropPosition = 6
            #if 'imageicons' in kw:
            #    if not kw['imageicons']:
            #        cropPosition = 6
            self.cropButton = self.graphWidget._addToolButton(\
                                            self.cropIcon,
                                            self._cropIconChecked,
                                            infotext,
                                            toggle = False,
                                            position = cropPosition)

            infotext = "Flip image and data, not the scale."
            self.graphWidget.hFlipToolButton.setToolTip('Flip image')
            self._flipMenu = qt.QMenu()
            self._flipMenu.addAction(QString("Flip Image and Vertical Scale"),
                                     self.__hFlipIconSignal)
            self._flipMenu.addAction(QString("Flip Image Left-Right"),
                                     self._flipLeftRight)
            self._flipMenu.addAction(QString("Flip Image Up-Down"),
                                     self._flipUpDown)
        else:
            self.graphWidget.hFlipToolButton.clicked.connect(\
                                     self.__hFlipIconSignal)


    def sizeHint(self):
        return qt.QSize(400, 400)

    def _cropIconChecked(self):
        #get current index
        index = self.slider.value()
        #current image
        label = self.imageNames[index]
        qimage = self._imageDict[label]
        width = qimage.width()
        height = qimage.height()

        xmin, xmax = self.graphWidget.graph.getGraphXLimits()
        ymin, ymax = self.graphWidget.graph.getGraphYLimits()
        xmin = int(xmin)
        xmax = int(xmax)
        ymin = int(ymin)
        ymax = int(ymax)
        dummy = xmin
        if (xmin > xmax):
            xmin = xmax
            xmax = dummy
        dummy = ymin
        if (ymin > ymax):
            ymin = ymax
            ymax = dummy
        xmin = max(xmin, 0)
        xmax = min(xmax, width)

        ymin = max(ymin, 0)
        ymax = min(ymax, height)

        rect = qt.QRect(xmin, ymin, xmax-xmin, ymax-ymin)
        newImageList = []
        for i in range(len(self.imageList)):
            image = self._imageDict[self.imageNames[i]].copy(rect)
            newImageList.append(image)

        #replace current image by the new one
        self.setQImageList(newImageList, width, height,
                       clearmask=False,
                       data=None,
                       imagenames=self.imageNames*1)

        ###self._imageDict[label] = self.getQImage()
        ###self.imageList.append(self.getImageData())
        self._showImage(index)

    def _flipIconChecked(self):
        if not self.graphWidget.graph.yAutoScale:
            qt.QMessageBox.information(self, "Open",
                    "Please set Y Axis to AutoScale first")
            return
        if not self.graphWidget.graph.xAutoScale:
            qt.QMessageBox.information(self, "Open",
                    "Please set X Axis to AutoScale first")
            return
        if self.imageList is None:
            return
        if self._imageDict is None:
            return
        if self.imageNames is None:
            return
        self._flipMenu.exec(self.cursor().pos())

    def _hFlipIconSignal(self):
        if self.getQImage() is None:
            return
        if self.imageNames is None:
            #just setImage data used
            #I use the default flip
            self.__hFlipIconSignal()
            return
        if self.imageList is None:
            return
        if self._imageDict is None:
            return
        self._flipMenu.exec(self.cursor().pos())

    def __hFlipIconSignal(self):
        MaskImageWidget.MaskImageWidget._hFlipIconSignal(self)

    def _flipUpDown(self):
        for i in range(len(self.imageList)):
            label = self.imageNames[i]
            self._imageDict[label] = self._imageDict[label].mirrored(0, 1)
            self.imageList[i] = numpy.flipud(self.getImageData())
        self.showImage(self.slider.value())

    def _flipLeftRight(self):
        for i in range(len(self.imageList)):
            label = self.imageNames[i]
            self._imageDict[label] = self._imageDict[label].mirrored(1, 0)
            self.imageList[i] = numpy.fliplr(self.getImageData())
        self.showImage(self.slider.value())

    def _showImage(self, index):
        if len(self.imageList):
            self.showImage(index, moveslider=False)

    def showImage(self, index=0, moveslider=True):
        if self.imageList is None:
            return
        if len(self.imageList) == 0:
            return
        if self._dynamic:
            self._dynamicAction(index)
        elif self._stack:
            # with matplotlib 2.2.2 the graph title is not updated
            # if set after the image data
            if self.imageNames is None:
                self.graphWidget.graph.setGraphTitle("Image %d" % index)
            else:
                self.graphWidget.graph.setGraphTitle(self.imageNames[index])
            self.setImageData(self.imageList[index])
        else:
            qimage = self._imageDict[self.imageNames[index]]
            # with matplotlib 2.2.2 the graph title is not updated
            # if set after the image data
            self.graphWidget.graph.setGraphTitle(self.imageNames[index])
            self.setQImage(qimage,
                       qimage.width(),
                       qimage.height(),
                       clearmask=False,
                       data=self.imageList[index])
        if moveslider:
            self.slider.setValue(index)

    def _dynamicAction(self, index):
        #just support edffiles
        fileName = self.imageList[index]
        edf = EdfFile.EdfFile(fileName)
        self.setImageData(edf.GetData(0))
        self.graphWidget.graph.setGraphTitle(os.path.basename(fileName))

    def setQImageList(self, images, width, height,
                      clearmask = False, data=None, imagenames = None):
        self._dynamic = False
        nimages = len(images)
        if imagenames is None:
            self.imageNames = []
            for i in range(nimages):
                self.imageNames.append("ExternalImage %02d" % i)
        else:
            self.imageNames = imagenames

        i = 0
        self._imageDict = {}
        self.imageList = []
        for label in self.imageNames:
            self.setQImage(images[i], width, height,
                           clearmask=clearmask,
                           data=data)
            self._imageDict[label] = self.getQImage()
            self.imageList.append(self.getImageData())
            i += 1

        if self.imageList is not None:
            self.slider.setMaximum(len(self.imageList)-1)
            self.showImage(0)
        else:
            self.slider.setMaximum(0)

        self.slider.setValue(0)


    def saveImageList(self, filename=None, imagelist=None, labels=None):
        if self.imageList is None:
            return
        if self._dynamic:
            #save only one image
            MaskImageWidget.MaskImageWidget.saveImageList(self)
            return
        labels = []
        for i in range(len(self.imageList)):
            labels.append(self.imageNames[i].replace(" ","_"))
        if len(labels):
            mask = self.getSelectionMask()
            if mask is not None:
                labels.append("Mask")
                return MaskImageWidget.MaskImageWidget.saveImageList(self,
                                          imagelist=self.imageList+[mask],
                                          labels=labels)
        return MaskImageWidget.MaskImageWidget.saveImageList(self,
                                          imagelist=self.imageList,
                                          labels=labels)

    def setImageList(self, imagelist, imagenames=None, dynamic=False):
        if hasattr(imagelist, 'shape'):
            #should I only accept lists?
            if len(imagelist.shape) == 3:
                return self.setStack(imagelist, index=0, imagenames=imagenames)
        if type(imagelist) in [type([0]), type((0,))]:
            if not len(imagelist):
                return
            if hasattr(imagelist[0],'shape'):
                #I have a list of images
                #I can treat it as a stack
                return self.setStack(imagelist, index=0, imagenames=imagenames)
        self._stack = False
        self._dynamic = dynamic
        self.imageList = imagelist
        self.imageNames = imagenames
        if imagelist is not None:
            if imagenames is None:
                nImages = len(self.imageList)
                self.imageNames = [None] * nImages
                for i in range(nImages):
                    self.imageNames[i] = "Image %02d" % i
            current = self.slider.value()
            self.slider.setMaximum(len(self.imageList)-1)
            if current < len(self.imageList):
                self.showImage(current)
            else:
                self.showImage(0)

    def setStack(self, stack, index=None, imagenames=None):
        if index is None:
            index = 0
        if hasattr(stack, "shape"):
            shape = stack.shape
            nImages = shape[index]
            imagelist = [None] * nImages
            for i in range(nImages):
                if index == 0:
                    imagelist[i] = stack[i, :, :]
                    imagelist[i] = imagelist[i].reshape(shape[1], shape[2])
                elif index == 1:
                    imagelist[i] = stack[:, i, :]
                    imagelist[i] = imagelist[i].reshape(shape[0], shape[2])
                elif index == 2:
                    imagelist[i] = stack[:, :, i]
                    imagelist[i] = imagelist[i].reshape(shape[0], shape[1])
        else:
            nImages = len(stack)
            imagelist = stack
        self.imageList = imagelist
        self.imageNames = imagenames
        self._dynamic = False
        self._stack = True
        mask = self.getSelectionMask()
        if mask is not None:
            shape = imagelist[0].shape
            if mask.shape != shape:
                mask = numpy.zeros(shape, numpy.uint8)
                self.setSelectionMask(mask, plot=False)
        current = self.slider.value()
        self.slider.setMaximum(len(self.imageList)-1)
        if current < len(self.imageList):
            self.showImage(current)
        else:
            self.showImage(0)

    def _updateProfileCurve(self, ddict):
        if not self._depthSelection:
            return MaskImageWidget.MaskImageWidget._updateProfileCurve(self,
                                                                       ddict)
        nImages = len(self.imageNames)
        for i in range(nImages):
            image=self.imageList[i]
            overlay = False
            if i == 0:
                overlay = MaskImageWidget.OVERLAY_DRAW
                replace = True
                if len(self.imageNames) == 1:
                    replot = True
                else:
                    replot = False
            elif i == (nImages -1):
                replot = True
                replace = False
            else:
                replot = False
                replace = False
            curve = self._getProfileCurve(ddict, image=image, overlay=overlay)
            if curve is None:
                return
            xdata, ydata, legend, info = curve
            newLegend = self.imageNames[i]+ " " + legend
            self._profileSelectionWindow.addCurve(xdata, ydata,
                                                  legend=newLegend,
                                                  info=info,
                                                  replot=replot,
                                                  replace=replace)

    def getCurrentIndex(self):
        return self.slider.value()


def test():
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)
    if len(sys.argv) > 1:
        if sys.argv[1][-3:].upper() in ['EDF', 'CCD']:
            container = ExternalImagesWindow(selection=False,
                                             colormap=True,
                                             imageicons=False,
                                             standalonesave=True)
                                             #,
                                             #dynamic=True)
            container.setImageList(sys.argv[1:], dynamic=True)
        else:
            container = ExternalImagesWindow()
            image = qt.QImage(sys.argv[1])
            #container.setQImage(image, image.width(),image.height())
            container.setQImageList([image], 200, 100)
    else:
        container = ExternalImagesWindow()
        data = numpy.arange(10000)
        data = data.reshape(100, 100)
        container.setImageData(data)
    container.show()
    def theSlot(ddict):
        print(ddict['event'])

    if not container._dynamic:
        container.sigMaskImageWidgetSignal.connect(theSlot)
    app.exec()

if __name__ == "__main__":
    test()
