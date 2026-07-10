#/*##########################################################################
# Copyright (C) 2004-2019 V.A. Sole, European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import logging

from PyMca5.PyMcaGui import PyMcaQt as qt
from .Q4PyMcaPrintPreview import PyMcaPrintPreview as PrintPreview

_logger = logging.getLogger(__name__)

def PyMcaPrintPreview(*var, **kw):
    _logger.debug("PyMcaPrintPreview kept for backwards compatibility")
    return getSingletonPrintPreview(*var, **kw)

def getSingletonPrintPreview(*var, **kw):
    if not hasattr(PrintPreview, "_preview_instance") or \
       PrintPreview._preview_instance:
        _logger.debug("Instantiating preview instance")
        PrintPreview._preview_instance = PrintPreview(modal=0)
    return PrintPreview._preview_instance

def resetSingletonPrintPreview():
    """
    To be called on Application to get rid of internal reference.
    """
    _logger.debug("resetSingletonPrintPreview CALLED")
    needed = False
    if not hasattr(PrintPreview, "_preview_instance"):
        _logger.debug("PrintPreview never instantiated")
        return needed
    import gc
    _logger.debug("_preview_instance before = %s", PrintPreview._preview_instance)
    try:
        if PrintPreview._preview_instance:
            needed = True
        PrintPreview._preview_instance = None
        gc.collect()
    except NameError:
        needed = False
    _logger.debug("RETURNING = %s", needed)
    return needed

if qt.QApplication.instance():
    if not hasattr(PrintPreview, "_preview_instance"):
        _logger.debug("PrintPreview not there creating it")
        PrintPreview._preview_instance = PrintPreview()
    else:
        _logger.debug("PrintPreview already there = %s",
                      PrintPreview._preview_instance)

def testPreview():
    """
    """
    import sys
    import os.path

    if len(sys.argv) < 2:
        print("give an image file as parameter please.")
        sys.exit(1)

    if len(sys.argv) > 2:
        print("only one parameter please.")
        sys.exit(1)

    filename = sys.argv[1]

    a = qt.QApplication(sys.argv)

    p = qt.QPrinter()
    p.setOutputFileName(os.path.splitext(filename)[0]+".ps")
    p.setColorMode(qt.QPrinter.Color)

    w = PyMcaPrintPreview( parent = None, printer = p, name = 'Print Prev',
                      modal = 0, fl = 0)
    w.resize(400,500)
    w.addPixmap(qt.QPixmap.fromImage(qt.QImage(filename)))
    w.addImage(qt.QImage(filename))
    sys.exit(w.exec())

if  __name__ == '__main__':
    testPreview()
