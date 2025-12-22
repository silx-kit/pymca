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
"""
This plugin opens a widget to view a stack as a scatter plot, by using
positioner data as X and Y coordinates.

"""
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import logging
import numpy
from contextlib import contextmanager

# import order may matter for qt binding selection
from PyMca5.PyMcaGui import PyMcaQt as qt
from silx.gui import qt as silx_qt

from PyMca5 import StackPluginBase

from silx.gui.plot.ScatterView import ScatterView
from silx.gui.widgets.BoxLayoutDockWidget import BoxLayoutDockWidget
from silx.gui.colors import Colormap

_logger = logging.getLogger(__name__)
# _logger.setLevel(logging.DEBUG)


# Probe OpenGL availability and widget
isGLAvailable = False
try:
    import OpenGL
except ImportError:
    _logger.debug("pyopengl not installed")
else:
    # sanity check from silx.gui._glutils.OpenGLWidget
    if not hasattr(silx_qt, 'QOpenGLWidget') and\
            (not silx_qt.HAS_OPENGL or
             silx_qt.QApplication.instance() and not silx_qt.QGLFormat.hasOpenGL()):
        _logger.debug("qt has a QOpenGLWidget: %s", hasattr(silx_qt, 'QOpenGLWidget'))
        _logger.debug("qt.HAS_OPENGL: %s", silx_qt.HAS_OPENGL)
        _logger.debug("silx_qt.QGLFormat.hasOpenGL(): %s",
                      silx_qt.QApplication.instance() and not silx_qt.QGLFormat.hasOpenGL())

    else:
        isGLAvailable = True

_logger.debug("GL availability: %s", isGLAvailable)


class AxesPositionersSelector(qt.QWidget):
    sigSelectionChanged = qt.pyqtSignal(object, object)

    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        hlayout = qt.QHBoxLayout()
        self.setLayout(hlayout)
        self._initializing = True
        xlabel = qt.QLabel("X:", parent=parent)
        self.xPositioner = qt.QComboBox(parent)
        self.xPositioner.currentIndexChanged.connect(self._emitSelectionChanged)

        ylabel = qt.QLabel("Y:", parent=parent)
        self.yPositioner = qt.QComboBox(parent)
        self.yPositioner.currentIndexChanged.connect(self._emitSelectionChanged)
        self._initializing = False

        hlayout.addWidget(xlabel)
        hlayout.addWidget(self.xPositioner)
        hlayout.addWidget(ylabel)
        hlayout.addWidget(self.yPositioner)

        self._nPoints = None
        """If set to an integer, only motors with this number of data points
        can be added."""

        self._initComboBoxes()

    def _initComboBoxes(self):
        self.xPositioner.clear()
        self.xPositioner.insertItem(0, "None")
        self.yPositioner.clear()
        self.yPositioner.insertItem(0, "None")

    def _emitSelectionChanged(self, idx):
        if not self._initializing:
            self.sigSelectionChanged.emit(*self.getSelectedPositioners())

    def setNumPoints(self, n):
        self._nPoints = n

    def unsetNumPoints(self):
        self._nPoints = None

    def fillPositioners(self, positioners):
        """

        :param dict positioners: Dictionary of positioners
            The key is the motor name, the value are the motor's position data
        """
        currentX, currentY = self.getSelectedPositioners()

        self._initializing = True
        self._initComboBoxes()
        i = 0
        for motorName, motorValues in positioners.items():
            if not numpy.isscalar(motorValues) and self._nPoints is not None and self._nPoints != motorValues.size:
                # checks consistency of number of data points (but accepts scalars)
                continue
            else:
                i += 1
                self.xPositioner.insertItem(i, motorName)
                self.yPositioner.insertItem(i, motorName)

        if currentX in positioners and currentY in positioners:
            self.xPositioner.setCurrentIndex(self.xPositioner.findText(currentX))
            self.yPositioner.setCurrentIndex(self.yPositioner.findText(currentY))
        self._initializing = False
    def getSelectedPositioners(self):
        """

        :return: 2-tuple of selected positioner names (or None)
        """
        selected = [None, None]
        if self.xPositioner.currentText() != "None":
            selected[0] = self.xPositioner.currentText()
        if self.yPositioner.currentText() != "None":
            selected[1] = self.yPositioner.currentText()
        return selected


class MaskScatterViewWidget(qt.QMainWindow):
    def __init__(self, parent=None, backend="mpl"):
        qt.QMainWindow.__init__(self, parent)
        self._scatterView = ScatterView(parent=self, backend=backend)
        self._scatterView.setColormap(Colormap("temperature"))
        self._scatterView.getScatterItem().setSymbol("s")

        self._axesSelector = AxesPositionersSelector(parent=self._scatterView)
        self._axesSelector.sigSelectionChanged.connect(self._setAxesData)

        self.setCentralWidget(self._scatterView)
        _axesSelectorDock = BoxLayoutDockWidget()
        _axesSelectorDock.setWindowTitle('Axes selection')
        _axesSelectorDock.setWidget(self._axesSelector)
        self.addDockWidget(qt.Qt.BottomDockWidgetArea, _axesSelectorDock)

        self._positioners = {}
        self._xdata = None
        self._ydata = None
        self._stackImage = None

    def getMaskToolsWidget(self):
        return self._scatterView.getMaskToolsWidget()

    def resetZoom(self):
        return self._scatterView.resetZoom()

    def fillPositioners(self, positioners):
        self._positioners = positioners
        self._axesSelector.fillPositioners(positioners)

    def setNumPoints(self, n):
        self._axesSelector.setNumPoints(n)

    def _setAxesData(self, xPositioner, yPositioner):
        """

        :param str xPositioner: motor name, or None
        :param str yPositioner: motor name, or None
        :return:
        """
        if xPositioner not in [None, ""]:
            assert xPositioner in self._positioners
            self._xdata = self._positioners[xPositioner]
        else:
            self._xdata = None
        if yPositioner not in [None, ""]:
            assert yPositioner in self._positioners
            self._ydata = self._positioners[yPositioner]
        else:
            self._ydata = None
        if self._stackImage is not None:
            self.setData()
            if not self._scatterView.getMaskToolsWidget().isVisible():
                # synchronization inactive, force mask redrawing
                mask = self._scatterView.getMaskToolsWidget().getSelectionMask()
                if mask is not None:
                    self._scatterView.getMaskToolsWidget().setSelectionMask(mask)

            self._scatterView.resetZoom()

    def setData(self, stackImage=None):
        first_time = self._stackImage is None
        if first_time:
            assert stackImage is not None

        if stackImage is None:
            # use previous data
            stackImage = self._stackImage
        else:
            # update stored data
            self._stackImage = stackImage
        nrows, ncols = stackImage.shape

        # flatten image
        stackValues = stackImage.reshape((-1,))

        # get regular grid coordinates as a 1D array
        if self._xdata is None or self._ydata is None:
            defaultX, defaultY = numpy.meshgrid(numpy.arange(ncols),
                                                numpy.arange(nrows))
            defaultX = defaultX.reshape(stackValues.shape)
            defaultY = defaultY.reshape(stackValues.shape)

        xdata = self._xdata if self._xdata is not None else defaultX
        ydata = self._ydata if self._ydata is not None else defaultY

        if numpy.isscalar(xdata):
            xdata = xdata * numpy.ones_like(stackValues)
            _logger.debug("converting scalar to constant 1D array for x")
        elif len(xdata.shape) > 1:
            _logger.debug("flattening %s array", str(xdata.shape))
            xdata = xdata.reshape((-1,))

        if numpy.isscalar(ydata):
            ydata = ydata * numpy.ones_like(stackValues)
            _logger.debug("converting scalar to constant 1D array for y")
        elif len(ydata.shape) > 1:
            _logger.debug("flattening %s array", str(ydata.shape))
            ydata = ydata.reshape((-1,))

        self._scatterView.setData(xdata, ydata, stackValues,
                                  copy=False)
        if first_time:
            self._scatterView.resetZoom()


class MaskScatterViewPlugin(StackPluginBase.StackPluginBase):
    """
    Widget to handle a stack as a scatter plot, by using
    positioner data as X and Y coordinates.

    The position data can be loaded via the load positioners plugin
    if not detected automatically.
    """
    def __init__(self, stackWindow, **kw):
        StackPluginBase.StackPluginBase.__init__(self, stackWindow, **kw)
        tooltip = "Stack as a scatter plot, using positioners as axes"
        self.methodDict = {'Show (mpl)': [self._showWidgetMpl,
                                          tooltip + " (matplotlib backend)",
                                          None]}
        self.__methodKeys = ['Show (mpl)']
        self._createdBackends = []
        if isGLAvailable:
            self.methodDict['Show (gl)'] = [self._showWidgetGL,
                                            tooltip + " (OpenGL backend)",
                                            None]
            self.__methodKeys.append('Show (gl)')

        self._scatterViews = {"gl": None,
                              "mpl": None}

    def _buildWidget(self, backend):
        scatterView = MaskScatterViewWidget(parent=None, backend=backend)
        self._scatterViews[backend] = scatterView
        self._createdBackends.append(backend)

        self._setData(backend)

        callback = self._scatterMaskChangedGl if backend == "gl" else self._scatterMaskChangedMpl
        scatterView.getMaskToolsWidget().sigMaskChanged.connect(
                callback)

        nPoints = self._getNumStackPoints()
        scatterView.setNumPoints(nPoints)
        positioners = self._getStackPositioners()
        scatterView.fillPositioners(positioners)

        # try to figure out if there are good X and Y candidates
        X = None
        Y = None
        for key in positioners:
            if key.lower() == "x":
                if len(positioners[key]) == nPoints: 
                    X = key
            elif key.lower() == "y":
                if len(positioners[key]) == nPoints: 
                    Y = key
        if X:
            scatterView._axesSelector.xPositioner.setCurrentText(X)
        if Y:
            scatterView._axesSelector.yPositioner.setCurrentText(Y)

    def _showWidgetMpl(self):
        self._showWidget(backend="mpl")

    def _showWidgetGL(self):
        self._showWidget(backend="gl")

    def _showWidget(self, backend):
        if self._scatterViews[backend] is None:
            self._buildWidget(backend=backend)

        # Show
        self._scatterViews[backend].show()
        self._scatterViews[backend].raise_()

        # Draw mask, if any
        self.selectionMaskUpdated()

    @contextmanager
    def _scatterMaskDisconnected(self, backend):
        # This context manager allows to call self.setStackSelectionMask
        # without entering an infinite loop, by temporarily disconnecting
        # callbacks from our mask signals.

        # Disconnect
        callback = self._scatterMaskChangedGl if backend == "gl" else self._scatterMaskChangedMpl
        self._scatterViews[backend].getMaskToolsWidget().sigMaskChanged.disconnect(
                callback)
        try:
            yield
        finally:
            # Reconnect
            callback = self._scatterMaskChangedGl if backend == "gl" else self._scatterMaskChangedMpl
            self._scatterViews[backend].getMaskToolsWidget().sigMaskChanged.connect(
                    callback)

    def _setData(self, backend):
        stack_images, stack_names = self.getStackROIImagesAndNames()

        self._scatterViews[backend].setData(stack_images[0])
        self._scatterViews[backend].resetZoom()

    def _isScatterViewVisible(self, backend):
        if self._scatterViews[backend] is None:
            return False
        if self._scatterViews[backend].isHidden():
            return False
        return True

    def _scatterMaskChangedGl(self):
        self._scatterMaskChanged("gl")

    def _scatterMaskChangedMpl(self):
        self._scatterMaskChanged("mpl")

    def _scatterMaskChanged(self, backend):
        scattermask = self._scatterViews[backend].getMaskToolsWidget().getSelectionMask()
        if scattermask is not None:
            shape = self.getStackOriginalImage().shape
            mask = scattermask.reshape(shape)
        else:
            mask = scattermask
        with self._scatterMaskDisconnected(backend):
            self.setStackSelectionMask(mask)

    def _getNumStackPoints(self):
        stack_images, stack_names = self.getStackROIImagesAndNames()
        return stack_images[0].size

    def _getStackPositioners(self):
        info = self.getStackInfo()
        return info.get("positioners", {})

    def stackUpdated(self):
        for backend in self._createdBackends:
            if not self._isScatterViewVisible(backend):
                return
            self._setData(backend)
            self._scatterViews[backend].setNumPoints(self._getNumStackPoints())
            self._scatterViews[backend].fillPositioners(self._getStackPositioners())

    def selectionMaskUpdated(self):
        for backend in self._createdBackends:
            if not self._isScatterViewVisible(backend):
                return
            mask = self.getStackSelectionMask()
            if mask is not None:
                scatterMask = mask.reshape((-1,))
            else:
                scatterMask = None
            self._scatterViews[backend].getMaskToolsWidget().setSelectionMask(scatterMask)

    def stackClosed(self):
        for sv in self._scatterViews.values():
            if sv is not None:
                sv.close()

    def stackROIImageListUpdated(self):
        self.stackUpdated()

    # Methods implemented by the plugin
    def getMethods(self):
        return self.__methodKeys

    def getMethodToolTip(self, name):
        return self.methodDict[name][1]

    def getMethodPixmap(self, name):
        return self.methodDict[name][2]

    def applyMethod(self, name):
        return self.methodDict[name][0]()


MENU_TEXT = "Mask Scatter View"


def getStackPluginInstance(stackWindow, **kw):
    ob = MaskScatterViewPlugin(stackWindow)
    return ob


