# /*#########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2015 European Synchrotron Radiation Facility
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
OpenGL/Qt QGLWidget backend.
"""


# import ######################################################################

from PyMca5.PyMcaGui.PyMcaQt import pyqtSignal, QSize, Qt
from PyMca5.PyMcaGui.PyMcaQt import QGLWidget, QGLContext
from PyMca5.PyMcaGui.PyMcaQt import QCursor

from ._OpenGLPlotCanvas import OpenGLPlotCanvas
from ._OpenGLPlotCanvas import CURSOR_DEFAULT, CURSOR_POINTING, \
    CURSOR_SIZE_HOR, CURSOR_SIZE_VER, CURSOR_SIZE_ALL
from .GLSupport import setGLContextGetter


# OpenGLBackend ###############################################################

# Init GL context getter
setGLContextGetter(QGLContext.currentContext)


class OpenGLBackend(QGLWidget, OpenGLPlotCanvas):
    _signalRedisplay = pyqtSignal()  # PyQt binds it to instances

    def __init__(self, parent=None, **kw):
        QGLWidget.__init__(self, parent)
        self._signalRedisplay.connect(self.update)

        self.setAutoFillBackground(False)
        self.setMouseTracking(True)

        OpenGLPlotCanvas.__init__(self, parent, **kw)

    def postRedisplay(self):
        """Thread-safe call to QWidget.update."""
        self._signalRedisplay.emit()

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
        if hasattr(event, 'angleDelta'):  # Qt 5
            delta = event.angleDelta().y()
        else:  # Qt 4 support
            delta = event.delta()
        angleInDegrees = delta / 8.
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
        super(OpenGLBackend, self).setCursor(QCursor(cursor))

    # Widget

    def getWidgetHandle(self):
        return self


    # PySide seems to need proxy methods

    def initializeGL(self):
        return OpenGLPlotCanvas.initializeGL(self)

    def paintGL(self):
        return OpenGLPlotCanvas.paintGL(self)

    def resizeGL(self, width, height):
        return OpenGLPlotCanvas.resizeGL(self, width, height)


# demo ########################################################################

if __name__ == "__main__":
    import numpy as np
    import sys
    from ..Plot import Plot

    try:
        from PyQt4.QtGui import QApplication
    except ImportError:
        try:
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            from PySide.QtGui import QApplication

    app = QApplication([])
    w = Plot(None, backend=OpenGLBackend)

    size = 4096
    data = np.arange(float(size)*size, dtype=np.dtype(np.float32))
    data = data.reshape(size, size)

    colormap = {'name': 'gray', 'normalization': 'linear',
                'autoscale': True, 'vmin': 0.0, 'vmax': 1.0,
                'colors': 256}
    w.addImage(data, legend="image 1",
               xScale=(25, 1.0), yScale=(-1000, 1.0),
               replot=False, colormap=colormap)

    w.getWidgetHandle().show()
    sys.exit(app.exec())
