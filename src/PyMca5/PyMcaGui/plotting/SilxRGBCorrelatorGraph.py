#/*##########################################################################
# Copyright (C) 2004-2023 European Synchrotron Radiation Facility
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
import logging
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from silx.gui.plot import PlotWidget
from silx.gui.plot.PrintPreviewToolButton import SingletonPrintPreviewToolButton
from .PyMca_Icons import IconDict
from PyMca5.PyMcaCore import PyMcaDirs
from silx.gui import icons as silx_icons

from io import BytesIO

QTVERSION = qt.qVersion()
_logger = logging.getLogger(__name__)



def convertToRowAndColumn(x, y, shape, xScale=None, yScale=None, safe=True):
    if xScale is None:
        c = x
    else:
        c = (x - xScale[0]) / xScale[1]
    if yScale is None:
        r = y
    else:
        r = ( y - yScale[0]) / yScale[1]

    if safe:
        c = min(int(c), shape[1] - 1)
        c = max(c, 0)
        r = min(int(r), shape[0] - 1)
        r = max(r, 0)
    else:
        c = int(c)
        r = int(r)
    return r, c


class RGBCorrelatorGraph(qt.QWidget):
    sigProfileSignal = qt.pyqtSignal(object)

    def __init__(self, parent = None, backend=None, selection=False, aspect=True,
                 colormap=False,
                 imageicons=False, standalonesave=True, standalonezoom=True,
                 profileselection=False, polygon=False):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        self._keepDataAspectRatioFlag = False
        self.graph = PlotWidget(parent=self, backend=backend)
        self.graph.setGraphXLabel("Column")
        self.graph.setGraphYLabel("Row")
        self.graph.setYAxisAutoScale(True)
        self.graph.setXAxisAutoScale(True)
        plotArea = self.graph.getWidgetHandle()
        plotArea.setContextMenuPolicy(qt.Qt.CustomContextMenu)
        plotArea.customContextMenuRequested.connect(self._zoomBack)

        self._buildToolBar(selection, colormap, imageicons,
                           standalonesave,
                           standalonezoom=standalonezoom,
                           profileselection=profileselection,
                           aspect=aspect,
                           polygon=polygon)

        if profileselection:
            if len(self._pickerSelectionButtons):
                self.graph.sigPlotSignal.connect(\
                    self._graphPolygonSignalReceived)
                self._pickerSelectionWidthValue.valueChanged[int].connect( \
                             self.setPickerSelectionWith)

        self.saveDirectory = os.getcwd()
        self.mainLayout.addWidget(self.graph)

    def sizeHint(self):
        return qt.QSize(int(1.5 * qt.QWidget.sizeHint(self).width()),
                        qt.QWidget.sizeHint(self).height())

    def _buildToolBar(self, selection=False, colormap=False,
                      imageicons=False, standalonesave=True,
                      standalonezoom=True, profileselection=False,
                      aspect=False, polygon=False):
        self.solidCircleIcon = qt.QIcon(qt.QPixmap(IconDict["solidcircle"]))
        self.solidEllipseIcon = qt.QIcon(qt.QPixmap(IconDict["solidellipse"]))
        self.colormapIcon   = qt.QIcon(qt.QPixmap(IconDict["colormap"]))
        self.selectionIcon = qt.QIcon(qt.QPixmap(IconDict["normal"]))
        self.zoomResetIcon = qt.QIcon(qt.QPixmap(IconDict["zoomreset"]))
        self.polygonIcon = qt.QIcon(qt.QPixmap(IconDict["polygon"]))
        self.printIcon	= qt.QIcon(qt.QPixmap(IconDict["fileprint"]))
        self.saveIcon	= qt.QIcon(qt.QPixmap(IconDict["filesave"]))
        self.xAutoIcon	= qt.QIcon(qt.QPixmap(IconDict["xauto"]))
        self.yAutoIcon	= qt.QIcon(qt.QPixmap(IconDict["yauto"]))
        self.hFlipIcon	= qt.QIcon(qt.QPixmap(IconDict["gioconda16mirror"]))
        self.imageIcon     = qt.QIcon(qt.QPixmap(IconDict["image"]))
        self.eraseSelectionIcon = qt.QIcon(qt.QPixmap(IconDict["eraseselect"]))
        self.rectSelectionIcon  = qt.QIcon(qt.QPixmap(IconDict["boxselect"]))
        self.brushSelectionIcon = qt.QIcon(qt.QPixmap(IconDict["brushselect"]))
        self.brushIcon          = qt.QIcon(qt.QPixmap(IconDict["brush"]))
        self.additionalIcon     = qt.QIcon(qt.QPixmap(IconDict["additionalselect"]))
        self.hLineIcon     = qt.QIcon(qt.QPixmap(IconDict["horizontal"]))
        self.vLineIcon     = qt.QIcon(qt.QPixmap(IconDict["vertical"]))
        self.lineIcon     = qt.QIcon(qt.QPixmap(IconDict["diagonal"]))
        self.copyIcon     = silx_icons.getQIcon("edit-copy")

        self.toolBar = qt.QWidget(self)
        self.toolBarLayout = qt.QHBoxLayout(self.toolBar)
        self.toolBarLayout.setContentsMargins(0, 0, 0, 0)
        self.toolBarLayout.setSpacing(0)
        self.mainLayout.addWidget(self.toolBar)
        #Autoscale
        if standalonezoom:
            tb = self._addToolButton(self.zoomResetIcon,
                            self.__zoomReset,
                            'Auto-Scale the Graph')
        else:
            tb = self._addToolButton(self.zoomResetIcon,
                            None,
                            'Auto-Scale the Graph')
        self.zoomResetToolButton = tb
        #y Autoscale
        tb = self._addToolButton(self.yAutoIcon,
                            self._yAutoScaleToggle,
                            'Toggle Autoscale Y Axis (On/Off)',
                            toggle = True, state=True)
        tb.setDown(True)

        self.yAutoScaleToolButton = tb
        tb.setDown(True)

        #x Autoscale
        tb = self._addToolButton(self.xAutoIcon,
                            self._xAutoScaleToggle,
                            'Toggle Autoscale X Axis (On/Off)',
                            toggle = True, state=True)
        self.xAutoScaleToolButton = tb
        tb.setDown(True)

        #Aspect ratio
        if aspect:
            self.aspectButton = self._addToolButton(self.solidCircleIcon,
                                                    self._aspectButtonSignal,
                                                    'Keep data aspect ratio',
                                                    toggle=False)
            self.aspectButton.setChecked(False)

        #colormap
        if colormap:
            tb = self._addToolButton(self.colormapIcon,
                                     None,
                                     'Change Colormap')
            self.colormapToolButton = tb

        #flip
        tb = self._addToolButton(self.hFlipIcon,
                                 None,
                                 'Flip Horizontal')
        self.hFlipToolButton = tb


        #save
        if standalonesave:
            tb = self._addToolButton(self.saveIcon,
                                 self._saveIconSignal,
                                 'Save Graph')
        else:
            tb = self._addToolButton(self.saveIcon,
                                 None,
                                 'Save')
        self.saveToolButton = tb

        self.copyToolButton = self._addToolButton(self.copyIcon,
                                                  self._copyIconSignal,
                                                  "Copy graph to clipboard")

        #Selection
        if selection:
            tb = self._addToolButton(self.selectionIcon,
                                None,
                                'Toggle Selection Mode',
                                toggle = True,
                                state = False)
            tb.setDown(False)
            self.selectionToolButton = tb
        #image selection icons
        if imageicons:
            tb = self._addToolButton(self.imageIcon,
                                     None,
                                     'Reset')
            self.imageToolButton = tb

            tb = self._addToolButton(self.eraseSelectionIcon,
                                     None,
                                     'Erase Selection')
            self.eraseSelectionToolButton = tb

            tb = self._addToolButton(self.rectSelectionIcon,
                                     None,
                                     'Rectangular Selection')
            self.rectSelectionToolButton = tb

            tb = self._addToolButton(self.brushSelectionIcon,
                                     None,
                                     'Brush Selection')
            self.brushSelectionToolButton = tb

            tb = self._addToolButton(self.brushIcon,
                                     None,
                                     'Select Brush')
            self.brushToolButton = tb

            if polygon:
                tb = self._addToolButton(self.polygonIcon,
                                     None,
                        'Polygon selection\nRight click to finish')
                self.polygonSelectionToolButton = tb

            tb = self._addToolButton(self.additionalIcon,
                                     None,
                                     'Additional Selections Menu')
            self.additionalSelectionToolButton = tb
        else:
            if polygon:
                tb = self._addToolButton(self.polygonIcon,
                                     None,
                        'Polygon selection\nRight click to finish')
                self.polygonSelectionToolButton = tb
            self.imageToolButton = None
        #picker selection
        self._pickerSelectionButtons = []
        if profileselection:
            self._profileSelection = True
            self._polygonSelection = False
            self._pickerSelectionButtons = []
            if self._profileSelection:
                tb = self._addToolButton(self.hLineIcon,
                                     self._hLineProfileClicked,
                                     'Horizontal Profile Selection',
                                     toggle=True,
                                     state=False)
                self.hLineProfileButton = tb
                self._pickerSelectionButtons.append(tb)

                tb = self._addToolButton(self.vLineIcon,
                                     self._vLineProfileClicked,
                                     'Vertical Profile Selection',
                                     toggle=True,
                                     state=False)
                self.vLineProfileButton = tb
                self._pickerSelectionButtons.append(tb)

                tb = self._addToolButton(self.lineIcon,
                                     self._lineProfileClicked,
                                     'Line Profile Selection',
                                     toggle=True,
                                     state=False)
                self.lineProfileButton = tb
                self._pickerSelectionButtons.append(tb)

                self._pickerSelectionWidthLabel = qt.QLabel(self.toolBar)
                self._pickerSelectionWidthLabel.setText("W:")
                self.toolBar.layout().addWidget(self._pickerSelectionWidthLabel)
                self._pickerSelectionWidthValue = qt.QSpinBox(self.toolBar)
                self._pickerSelectionWidthValue.setMinimum(0)
                self._pickerSelectionWidthValue.setMaximum(1000)
                self._pickerSelectionWidthValue.setValue(1)
                self.toolBar.layout().addWidget(self._pickerSelectionWidthValue)
                #tb = self._addToolButton(None,
                #                     self._lineProfileClicked,
                #                     'Line Profile Selection',
                #                     toggle=True,
                #                     state=False)
                #tb.setText = "W:"
                #self.lineWidthProfileButton = tb
                #self._pickerSelectionButtons.append(tb)
            if self._polygonSelection:
                _logger.info("Polygon selection not implemented yet")
        #hide profile selection buttons
        if imageicons:
            for button in self._pickerSelectionButtons:
                button.hide()

        self.infoWidget = qt.QWidget(self.toolBar)
        self.infoWidget.mainLayout = qt.QHBoxLayout(self.infoWidget)
        self.infoWidget.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.infoWidget.mainLayout.setSpacing(0)
        self.infoWidget.label = qt.QLabel(self.infoWidget)
        self.infoWidget.label.setText("X = ???? Y = ???? Z = ????")
        self.infoWidget.mainLayout.addWidget(self.infoWidget.label)
        self.toolBarLayout.addWidget(self.infoWidget)
        self.infoWidget.hide()

        self.toolBarLayout.addWidget(qt.HorizontalSpacer(self.toolBar))

        # ---print
        self.printPreview = SingletonPrintPreviewToolButton(parent=self,
                                                            plot=self.graph)
        self.printPreview.setIcon(self.printIcon)
        self.toolBarLayout.addWidget(self.printPreview)

    def _aspectButtonSignal(self):
        _logger.debug("_aspectButtonSignal")
        if self._keepDataAspectRatioFlag:
            self.keepDataAspectRatio(False)
        else:
            self.keepDataAspectRatio(True)

    def keepDataAspectRatio(self, flag=True):
        if flag:
            self._keepDataAspectRatioFlag = True
            self.aspectButton.setIcon(self.solidEllipseIcon)
            self.aspectButton.setToolTip("Set free data aspect ratio")
        else:
            self._keepDataAspectRatioFlag = False
            self.aspectButton.setIcon(self.solidCircleIcon)
            self.aspectButton.setToolTip("Keep data aspect ratio")
        self.graph.setKeepDataAspectRatio(self._keepDataAspectRatioFlag)

    def showInfo(self):
        self.infoWidget.show()

    def hideInfo(self):
        self.infoWidget.hide()

    def setInfoText(self, text):
        self.infoWidget.label.setText(text)

    def setMouseText(self, text=""):
        try:
            if len(text):
                qt.QToolTip.showText(self.cursor().pos(),
                                     text, self, qt.QRect())
            else:
                qt.QToolTip.hideText()
        except Exception:
            _logger.warning("Error trying to show mouse text <%s>" % text)

    def focusOutEvent(self, ev):
        qt.QToolTip.hideText()

    def infoText(self):
        return self.infoWidget.label.text()

    def setXLabel(self, label="Column"):
        return self.graph.setGraphXLabel(label)

    def setYLabel(self, label="Row"):
        return self.graph.setGraphYLabel(label)

    def getXLabel(self):
        return self.graph.getGraphXLabel()

    def getYLabel(self):
        return self.graph.getGraphYLabel()

    def hideImageIcons(self):
        if self.imageToolButton is None:return
        self.imageToolButton.hide()
        self.eraseSelectionToolButton.hide()
        self.rectSelectionToolButton.hide()
        self.brushSelectionToolButton.hide()
        self.brushToolButton.hide()
        if hasattr(self, "polygonSelectionToolButton"):
            self.polygonSelectionToolButton.hide()
        self.additionalSelectionToolButton.hide()

    def showImageIcons(self):
        if self.imageToolButton is None:return
        self.imageToolButton.show()
        self.eraseSelectionToolButton.show()
        self.rectSelectionToolButton.show()
        self.brushSelectionToolButton.show()
        self.brushToolButton.show()
        if hasattr(self, "polygonSelectionToolButton"):
            self.polygonSelectionToolButton.show()
        self.additionalSelectionToolButton.show()

    def _hLineProfileClicked(self):
        for button in self._pickerSelectionButtons:
            if button != self.hLineProfileButton:
                button.setChecked(False)

        if self.hLineProfileButton.isChecked():
            self._setPickerSelectionMode("HORIZONTAL")
        else:
            self._setPickerSelectionMode(None)

    def _vLineProfileClicked(self):
        for button in self._pickerSelectionButtons:
            if button != self.vLineProfileButton:
                button.setChecked(False)
        if self.vLineProfileButton.isChecked():
            self._setPickerSelectionMode("VERTICAL")
        else:
            self._setPickerSelectionMode(None)

    def _lineProfileClicked(self):
        for button in self._pickerSelectionButtons:
            if button != self.lineProfileButton:
                button.setChecked(False)
        if self.lineProfileButton.isChecked():
            self._setPickerSelectionMode("LINE")
        else:
            self._setPickerSelectionMode(None)

    def setPickerSelectionWith(self, intValue):
        self._pickerSelectionWidthValue.setValue(intValue)
        #get the current mode
        mode = "NONE"
        for button in self._pickerSelectionButtons:
            if button.isChecked():
                if button == self.hLineProfileButton:
                    mode = "HORIZONTAL"
                elif button == self.vLineProfileButton:
                    mode = "VERTICAL"
                elif button == self.lineProfileButton:
                    mode = "LINE"
        ddict = {}
        ddict['event'] = "profileWidthChanged"
        ddict['pixelwidth'] = self._pickerSelectionWidthValue.value()
        ddict['mode'] = mode
        self.sigProfileSignal.emit(ddict)

    def hideProfileSelectionIcons(self):
        if not len(self._pickerSelectionButtons):
            return
        for button in self._pickerSelectionButtons:
            button.setChecked(False)
            button.hide()
        self._pickerSelectionWidthLabel.hide()
        self._pickerSelectionWidthValue.hide()
        if self.graph.getInteractiveMode()['mode'] == 'draw':
            self.graph.setInteractiveMode('select')

    def showProfileSelectionIcons(self):
        if not len(self._pickerSelectionButtons):
            return
        for button in self._pickerSelectionButtons:
            button.show()
        self._pickerSelectionWidthLabel.show()
        self._pickerSelectionWidthValue.show()

    def getPickerSelectionMode(self):
        if not len(self._pickerSelectionButtons):
            return None
        if self.hLineProfileButton.isChecked():
            return "HORIZONTAL"
        if self.vLineProfileButton.isChecked():
            return "VERTICAL"
        if self.lineProfileButton.isChecked():
            return "LINE"
        return None

    def _setPickerSelectionMode(self, mode=None):
        if mode is None:
            self.graph.setInteractiveMode('zoom')
        else:
            if mode == "HORIZONTAL":
                shape = "hline"
            elif mode == "VERTICAL":
                shape = "vline"
            else:
                shape = "line"
            self.graph.setInteractiveMode('draw',
                                          shape=shape,
                                          label=mode)
        ddict = {}
        if mode is None:
            mode = "NONE"
        ddict['event'] = "profileModeChanged"
        ddict['mode'] = mode
        self.sigProfileSignal.emit(ddict)

    def _graphPolygonSignalReceived(self, ddict):
        _logger.debug("PolygonSignal Received")
        for key in ddict.keys():
            _logger.debug("%s: %s", key, ddict[key])

        if ddict['event'] not in ['drawingProgress', 'drawingFinished']:
            return
        label = ddict['parameters']['label']
        if label not in ['HORIZONTAL', 'VERTICAL', 'LINE']:
            return
        ddict['mode'] = label
        ddict['pixelwidth'] = self._pickerSelectionWidthValue.value()
        self.sigProfileSignal.emit(ddict)

    def _addToolButton(self, icon, action, tip, toggle=None, state=None, position=None):
        tb      = qt.QToolButton(self.toolBar)
        if icon is not None:
            tb.setIcon(icon)
        tb.setToolTip(tip)
        if toggle is not None:
            if toggle:
                tb.setCheckable(1)
                if state is not None:
                    if state:
                        tb.setChecked(state)
                else:
                    tb.setChecked(False)
        if position is not None:
            self.toolBarLayout.insertWidget(position, tb)
        else:
            self.toolBarLayout.addWidget(tb)
        if action is not None:
            tb.clicked.connect(action)
        return tb

    def __zoomReset(self):
        self._zoomReset()

    def _zoomReset(self, replot=None):
        _logger.debug("_zoomReset")
        if self.graph is not None:
            self.graph.resetZoom()

    def _yAutoScaleToggle(self):
        if self.graph is not None:
            self.yAutoScaleToolButton.setDown(
                    not self.graph.isYAxisAutoScale())
            self.graph.setYAxisAutoScale(
                    not self.graph.isYAxisAutoScale())

    def _xAutoScaleToggle(self):
        if self.graph is not None:
            self.xAutoScaleToolButton.setDown(
                    not self.graph.isXAxisAutoScale())
            self.graph.setXAxisAutoScale(
                    not self.graph.isXAxisAutoScale())

    def _copyIconSignal(self):
        pngFile = BytesIO()
        self.graph.saveGraph(pngFile, fileFormat='png')
        pngFile.flush()
        pngFile.seek(0)
        pngData = pngFile.read()
        pngFile.close()
        image = qt.QImage.fromData(pngData, 'png')
        qt.QApplication.clipboard().setImage(image)

    def _saveIconSignal(self):
        self.saveDirectory = PyMcaDirs.outputDir

        fileTypeList = ["Image *.png",
                        "Image *.jpg",
                        "ZoomedImage *.png",
                        "ZoomedImage *.jpg",
                        "Widget *.png",
                        "Widget *.jpg"]

        outputFile, filterused = PyMcaFileDialogs.getFileList(self,
                                                              filetypelist=fileTypeList,
                                                              message="Output File Selection",
                                                              currentdir=self.saveDirectory,
                                                              mode="SAVE", getfilter=True,
                                                              single=False, currentfilter=None, native=None)
        if not len(outputFile):
            return
        
        outputFile = outputFile[0]

        filterused = filterused.split()
        filetype = filterused[0]
        extension = filterused[1]

        outputDir  = os.path.dirname(outputFile)
        self.saveDirectory = outputDir
        PyMcaDirs.outputDir = outputDir

        #always overwrite for the time being
        if len(outputFile) < len(extension[1:]):
            outputFile += extension[1:]
        elif outputFile[-4:] != extension[1:]:
            outputFile += extension[1:]
        outputFile = os.path.join(outputDir, outputFile)
        if os.path.exists(outputFile):
            try:
                os.remove(outputFile)
            except Exception:
                qt.QMessageBox.critical(self, "Save Error",
                                        "Cannot overwrite existing file")
                return

        if filetype.upper() == "IMAGE":
            self.saveGraphImage(outputFile, original=True)
        elif filetype.upper() == "ZOOMEDIMAGE":
            self.saveGraphImage(outputFile, original=False)
        else:
            self.saveGraphWidget(outputFile)

    def saveGraphImage(self, filename, original=False):
        format_ = filename[-3:].upper()
        activeImage = self.graph.getActiveImage()
        rgbdata = activeImage.getRgbaImageData()
        # silx to pymca scale convention (a + b x)
        xScale = activeImage.getOrigin()[0], activeImage.getScale()[0]
        yScale = activeImage.getOrigin()[1], activeImage.getScale()[1]
        if original:
            # save whole image
            bgradata = numpy.array(rgbdata, copy=True)
            bgradata[:, :, 0] = rgbdata[:, :, 2]
            bgradata[:, :, 2] = rgbdata[:, :, 0]
        else:
            shape = rgbdata.shape[:2]
            xmin, xmax = self.graph.getGraphXLimits()
            ymin, ymax = self.graph.getGraphYLimits()
            # save zoomed image, for that we have to get the limits
            r0, c0 = convertToRowAndColumn(xmin, ymin, shape, xScale=xScale, yScale=yScale, safe=True)
            r1, c1 = convertToRowAndColumn(xmax, ymax, shape, xScale=xScale, yScale=yScale, safe=True)
            row0 = int(min(r0, r1))
            row1 = int(max(r0, r1))
            col0 = int(min(c0, c1))
            col1 = int(max(c0, c1))
            if row1 < shape[0]:
                row1 += 1
            if col1 < shape[1]:
                col1 += 1
            tmpArray = rgbdata[row0:row1, col0:col1, :]
            bgradata = numpy.array(tmpArray, copy=True, dtype=rgbdata.dtype)
            bgradata[:, :, 0] = tmpArray[:, :, 2]
            bgradata[:, :, 2] = tmpArray[:, :, 0]
        if self.graph.isYAxisInverted():
            qImage = qt.QImage(bgradata, bgradata.shape[1], bgradata.shape[0],
                               qt.QImage.Format_ARGB32)
        else:
            qImage = qt.QImage(bgradata, bgradata.shape[1], bgradata.shape[0],
                               qt.QImage.Format_ARGB32).mirrored(False, True)
        pixmap = qt.QPixmap.fromImage(qImage)
        if pixmap.save(filename, format_):
            return
        else:
            qt.QMessageBox.critical(self, "Save Error",
                                    "%s" % sys.exc_info()[1])
            return
    
    def saveGraphWidget(self, filename):
        format_ = filename[-3:].upper()
        if hasattr(qt.QPixmap, "grabWidget"):
            # Qt4
            pixmap = qt.QPixmap.grabWidget(self.graph.getWidgetHandle())
        else:
            # Qt5
            pixmap = self.graph.getWidgetHandle().grab()
        if pixmap.save(filename, format_):
            return
        else:
            qt.QMessageBox.critical(self, "Save Error", "%s" % sys.exc_info()[1])
            return

    def setSaveDirectory(self, wdir):
        if os.path.exists(wdir):
            self.saveDirectory = wdir
            return True
        else:
            return False

    def selectColormap(self):
        qt.QMessageBox.information(self, "Open", "Not implemented (yet)")

    def _zoomBack(self, pos):
        self.graph.getLimitsHistory().pop()

class MyQLabel(qt.QLabel):
    def __init__(self,parent=None,name=None,fl=0,bold=True, color= qt.Qt.red):
        qt.QLabel.__init__(self,parent)
        palette = qt.QPalette(self.palette())
        role = self.foregroundRole()
        palette.setColor(role,color)
        self.setPalette(palette)
        self.font().setBold(bold)

def test():
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)

    container = RGBCorrelatorGraph()
    container.show()
    app.exec()

if __name__ == "__main__":
    test()

