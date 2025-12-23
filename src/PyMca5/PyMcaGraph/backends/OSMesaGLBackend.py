# /*#########################################################################
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
# ###########################################################################*/
__author__ = "T. Vincent - ESRF Data Analysis"
__contact__ = "thomas.vincent@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__doc__ = """
Experimental Off-Screen Mesa/Qt OpenGL backend.

This backend is based on the OSMesa software backend (http://www.mesa3d.org/).
It can be used when OpenGL is not available.
It depends on libOSMesa, PyOpenGL (tested with v3.1.1) and Qt.

Information on how to compile libOSMesa can be found here:

- http://www.mesa3d.org/osmesa.html
- http://www.paraview.org/Wiki/ParaView/ParaView_And_Mesa_3D

The --enable-texture-float flag is required to support float32 textures.

The environment variable PYOPENGL_PLATFORM MUST be set to osmesa before
the first import of PyOpenGL.
This module adds it to the environment variables, but in case another module
imports PyOpenGL before, PYOPENGL_PLATFORM must already be set at that time
(e.g., from the shell).
"""


# import ######################################################################

import numpy as np

# PyOpenGL
# Tells PyOpenGL to use libOSMesa
# This only works if PyOpenGL has not yet been imported
import os
os.environ['PYOPENGL_PLATFORM'] = 'osmesa'

# Test PyOpenGL version
import OpenGL
if OpenGL.version.__version__ < '3.1.0':
    raise ImportError(
        "PyOpenGL version >= 3.1.0 is required for OS Mesa backend.")
try:
    from OpenGL.raw.osmesa import mesa
except Exception:
    raise RuntimeError(
        """PyOpenGL is not set to use OSMesa.
         Add PYOPENGL_PLATFORM=osmesa to the environment variables.""")

from .GLSupport import gl
from .GLSupport import setGLContextGetter

# Qt
try:
    from PyMca5.PyMcaGui.PyMcaQt import pyqtSignal, QCursor, QSize, Qt, QLabel
    from PyMca5.PyMcaGui.PyMcaQt import QPixmap, QImage
except ImportError:
    try:
        from PyQt4.QtCore import pyqtSignal, QSize, Qt
        from PyQt4.QtGui import QLabel, QPixmap, QImage
        from PyQt4.Qt import QCursor
    except ImportError:
        from PyQt5.QtCore import pyqtSignal, QSize, Qt
        from PyQt5.QtGui import QLabel, QPixmap
        from PyQt5.Qt import QCursor

from ._OpenGLPlotCanvas import OpenGLPlotCanvas
from ._OpenGLPlotCanvas import CURSOR_DEFAULT, CURSOR_POINTING, \
    CURSOR_SIZE_HOR, CURSOR_SIZE_VER, CURSOR_SIZE_ALL


# OS Mesa #####################################################################

class OSMesaGLBackend(QLabel, OpenGLPlotCanvas):
    _signalRedisplay = pyqtSignal()  # PyQt binds it to instances

    _currentContext = None

    def __init__(self, parent=None, **kw):
        # Qt init
        QLabel.__init__(self, parent)
        self._signalRedisplay.connect(self.update)

        self.setAutoFillBackground(False)
        self.setMouseTracking(True)

        # OS Mesa init
        self.__dirtyPixmap = True
        self.__context = mesa.OSMesaCreateContext(mesa.OSMESA_BGRA, None)
        assert self.__context != 0

        # OpenGL Plot backend init
        OpenGLPlotCanvas.__init__(self, parent, **kw)

    def __del__(self):
        mesa.OSMesaDestroyContext(self.__context)

    @classmethod
    def getCurrentContext(cls):
        """Returns the current OSMesa GL context."""
        return cls._currentContext

    def makeCurrent(self):
        """Set the current OSMesa GL context to this instance.
        There is one context per OSMesaGLBackend instance.
        """
        OSMesaGLBackend._currentContext = self

    def postRedisplay(self):
        self.__dirtyPixmap = True
        self._signalRedisplay.emit()

    # Paint #
    def paintEvent(self, event):
        # Only refresh content when paint comes from backend
        if self.__dirtyPixmap:
            self.__dirtyPixmap = False

            height, width = self.__pixmap.shape[0:2]
            assert width == self.size().width()
            assert height == self.size().height()
            errCode = mesa.OSMesaMakeCurrent(self.__context,
                                             self.__pixmap,
                                             gl.GL_UNSIGNED_BYTE,
                                             width,
                                             height)
            assert errCode == gl.GL_TRUE

            self.makeCurrent()
            self.paintGL()
            gl.glFinish()

            image = QImage(self.__pixmap.data, width, height,
                           QImage.Format_ARGB32)
            self.setPixmap(QPixmap.fromImage(image))
        QLabel.paintEvent(self, event)

    def resizeEvent(self, event):
        width, height = self.size().width(), self.size().height()

        # Update underlying pixmap
        self.__dirtyPixmap = True
        self.__pixmap = np.empty((height, width, 4), dtype=np.uint8)
        errCode = mesa.OSMesaMakeCurrent(self.__context,
                                         self.__pixmap,
                                         gl.GL_UNSIGNED_BYTE,
                                         width,
                                         height)
        assert errCode == gl.GL_TRUE
        mesa.OSMesaPixelStore(mesa.OSMESA_Y_UP, 0)

        self.makeCurrent()
        gl.testGL()
        self.initializeGL()
        self.resizeGL(width, height)

        QLabel.resizeEvent(self, event)

    # Mouse events #
    _MOUSE_BTNS = {1: 'left', 2: 'right', 4: 'middle'}

    def sizeHint(self):
        return QSize(8 * 80, 6 * 80)  # Mimic MatplotlibBackend

    def mousePressEvent(self, event):
        xPixel, yPixel = event.x(), event.y()
        btn = self._MOUSE_BTNS[event.button()]
        self.onMousePress(xPixel, yPixel, btn)
        event.accept()

    def mouseMoveEvent(self, event):
        xPixel, yPixel = event.x(), event.y()
        self.onMouseMove(xPixel, yPixel)
        event.accept()

    def mouseReleaseEvent(self, event):
        xPixel, yPixel = event.x(), event.y()
        btn = self._MOUSE_BTNS[event.button()]
        self.onMouseRelease(xPixel, yPixel, btn)
        event.accept()

    def wheelEvent(self, event):
        xPixel, yPixel = event.x(), event.y()
        angleInDegrees = event.delta() / 8.
        self.onMouseWheel(xPixel, yPixel, angleInDegrees)
        event.accept()

    _CURSORS = {
        CURSOR_DEFAULT: Qt.ArrowCursor,
        CURSOR_POINTING: Qt.PointingHandCursor,
        CURSOR_SIZE_HOR: Qt.SizeHorCursor,
        CURSOR_SIZE_VER: Qt.SizeVerCursor,
        CURSOR_SIZE_ALL: Qt.SizeAllCursor,
    }

    def setCursor(self, cursor=CURSOR_DEFAULT):
        cursor = self._CURSORS[cursor]
        QLabel.setCursor(self, QCursor(cursor))

    # Widget handle

    def getWidgetHandle(self):
        return self

# Init GL context getter
setGLContextGetter(OSMesaGLBackend.getCurrentContext)
# OSMesaGetCurrentContext does not return the same object for the context.
# setGLContextGetter(mesa.OSMesaGetCurrentContext)


# main ########################################################################

if __name__ == "__main__":
    import sys
    try:
        from PyQt4.QtGui import QApplication
    except ImportError:
        from PyQt5.QtWidgets import QApplication

    from PyMca5.PyMcaGraph.Plot import Plot

    app = QApplication([])
    w = Plot(None, backend=OSMesaGLBackend)

    size = 1024
    data = np.arange(float(size)*size, dtype=np.uint16)
    data = data.reshape(size, size)

    colormap = {'name': 'gray', 'normalization': 'linear',
                'autoscale': True, 'vmin': 0.0, 'vmax': 1.0,
                'colors': 256}
    w.addImage(data, legend="image 1",
               xScale=(25, 1.0), yScale=(-1000, 1.0),
               replot=False, colormap=colormap)
    w.insertXMarker(512, 'testX', 'markerX', color='pink',
                    selectable=False, draggable=True)

    w.getWidgetHandle().show()
    sys.exit(app.exec())
