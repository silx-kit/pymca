#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2019-2021 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import sys
import weakref

if 'PyQt5.QtCore' in sys.modules:
    from PyQt5 import QtCore
    from PyQt5.QtWidgets import QApplication
elif 'PyQt6.QtCore' in sys.modules:
    from PyQt6 import QtCore
    from PyQt6.QtWidgets import QApplication
elif 'PySide2.QtCore' in sys.modules:
    from PySide2 import QtCore
    from PySide2.QtWidgets import QApplication
elif 'PySide6.QtCore' in sys.modules:
    from PySide6 import QtCore
    from PySide6.QtWidgets import QApplication
else:
    raise ImportError("This module expects PySide2, PySide6 or PyQt5")

def patch_backend_qt():
    import matplotlib.backends.backend_qt5
    def _create_qApp():
        if QApplication.instance() is None:
            raise ValueError("A QApplication must be created before")
            __THOUGHTS__ = """
            if 'PyQt5.QtCore' in sys.modules:
                # Matplotlib is doing this but it only makes sense prior
                # to create the QApplication
                try:
                    QApplication.instance().setAttribute(\
                                QtCore.Qt.AA_UseHighDpiPixmaps)
                    QApplication.instance().setAttribute(\
                                QtCore.Qt.AA_EnableHighDpiScaling)
                except AttributeError:
                    pass
            """
        matplotlib.backends.backend_qt5.qApp = weakref.proxy(\
                                        QApplication.instance())
    matplotlib.backends.backend_qt5._create_qApp = _create_qApp
