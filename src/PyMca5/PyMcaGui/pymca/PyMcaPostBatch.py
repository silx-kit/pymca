#!/usr/bin/env python
#/*##########################################################################
# Copyright (C) 2004-2026 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import logging
if __name__== '__main__':
    # avoid issues if some module or dependency tries to use multiprocessing in frozen binaries
    if getattr(sys, "frozen", False):
        try:
            import multiprocessing
            multiprocessing.freeze_support()
        except Exception:
            pass
_logger = logging.getLogger(__name__)
if __name__ == "__main__":    
    # We are going to read. Disable file locking.
    os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"
    _logger.info("%s set to %s" % ("HDF5_USE_FILE_LOCKING",
                                    os.environ["HDF5_USE_FILE_LOCKING"]))
    try:
        # make sure hdf5plugins are imported
        import hdf5plugin
    except Exception:
        _logger.info("Failed to import hdf5plugin")

from PyMca5 import PyMcaDirs
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaGui.pymca import RGBCorrelator
if hasattr(qt, "QString"):
    QString = qt.QString
    QStringList = qt.QStringList
else:
    QString = qt.safe_str
    QStringList = list
QTVERSION = qt.qVersion()


class PyMcaPostBatch(RGBCorrelator.RGBCorrelator):

    def addFileList(self, filelist):
        text = qt.safe_str(self.windowTitle())
        if len(filelist) == 1:
            text += ": " + qt.safe_str(os.path.basename(filelist[0]))
        else:
            text += ": from " + qt.safe_str(os.path.basename(filelist[0])) + \
                    " to " + qt.safe_str(os.path.basename(filelist[-1]))
        self.setWindowTitle(text)
        self.controller.addFileList(filelist)

    def _getStackOfFiles(self):
        wdir = PyMcaDirs.inputDir
        fileTypeList = ["Batch Result Files (*dat)",
                        "EDF Files (*edf)",
                        "EDF Files (*ccd)",
                        "TIFF Files (*tif *tiff *TIF *TIFF)",
                        "Image Files (* jpg *jpeg *tif *tiff *png)",
                        "All Files (*)"]
        message = "Open ONE Batch result file or SEVERAL EDF files"
        filelist = PyMcaFileDialogs.getFileList(parent=self,
                                                filetypelist=fileTypeList,
                                                message=message,
                                                currentdir=wdir,
                                                mode="OPEN",
                                                single=False)
        if filelist:
            PyMcaDirs.inputDir = os.path.dirname(filelist[0])
            return filelist
        else:
            return []


def main():
    from PyMca5.PyMcaCore.LoggingLevel import getLoggingLevel
    sys.excepthook = qt.exceptionHandler
    app = qt.QApplication([])
    app.lastWindowClosed.connect(app.quit)

    import getopt
    options = ''
    longoptions = ["nativefiledialogs=", "transpose=", "fileindex=",
                   "logging=", "debug=", "shape="]
    opts, args = getopt.getopt(
                    sys.argv[1:],
                    options,
                    longoptions)
    transpose = False
    image_shape = None
    for opt, arg in opts:
        if opt in '--nativefiledialogs':
            if int(arg):
                PyMcaDirs.nativeFileDialogs = True
            else:
                PyMcaDirs.nativeFileDialogs = False
        elif opt in '--transpose':
            if int(arg):
                transpose = True
        elif opt in '--fileindex':
            if int(arg):
                transpose = True
        elif opt in '--shape':
            if 'x' in arg:
                split_on = "x"
            else:
                split_on = ","
            image_shape = tuple(int(n) for n in arg.split(split_on))

    logging.basicConfig(level=getLoggingLevel(opts))

    filelist = args
    w = PyMcaPostBatch(image_shape=image_shape)
    w.layout().setContentsMargins(11, 11, 11, 11)
    if not filelist:
        filelist = w._getStackOfFiles()
    if filelist:
        w.addFileList(filelist)
    else:
        print("Usage:")
        print("python PyMcaPostBatch.py PyMCA_BATCH_RESULT_DOT_DAT_FILE")
    if transpose:
        w.transposeImages()
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
