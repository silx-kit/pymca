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

from PyMca5.PyMcaGui.plotting.MaskScatterViewWidget import MaskScatterViewWidget

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


