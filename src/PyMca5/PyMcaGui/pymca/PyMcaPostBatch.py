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

from PyMca5.PyMcaGui import PyMcaAppInit

if __name__== '__main__':
    PyMcaAppInit.init_before_app_import()

import sys
import os
import logging

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5 import PyMcaDirs
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaGui.pymca import RGBCorrelator
from PyMca5.PyMcaMisc import CliUtils

if hasattr(qt, "QString"):
    QString = qt.QString
    QStringList = qt.QStringList
else:
    QString = qt.safe_str
    QStringList = list
QTVERSION = qt.qVersion()

_logger = logging.getLogger(__name__)


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


def main(args):
    app = qt.QApplication([])
    PyMcaAppInit.init_before_app_start(qt_app=app, cli_args=args)

    if args.shape:
        split_on = "x" if "x" in args.shape else ","
        image_shape = tuple(int(n) for n in args.shape.split(split_on))
    else:
        image_shape = None

    # Create the widget
    w = PyMcaPostBatch(image_shape=image_shape)
    w.layout().setContentsMargins(11, 11, 11, 11)

    # Handle files
    filelist = args.files
    if not filelist and not args.cli_test:
        w._getStackOfFiles()

    if filelist:
        w.addFileList(filelist)
    else:
        print("Usage: python PyMcaPostBatch.py PyMCA_BATCH_RESULT_DOT_DAT_FILE")

    # Optional behaviors
    if args.transpose:
        w.transposeImages()

    w.show()

    # Auto-close Qt application for tests
    if args.cli_test:
        qt.QTimer.singleShot(0, app.quit)

    return app.exec()


def build_parser():
    parser = CliUtils.create_parser(description="PyMca Post-Batch Processing GUI", add_qt_options=True)

    parser.add_argument("--transpose", "--fileindex", type=int, default=0, help="Transpose all images")
    parser.add_argument("--shape", type=str, default=None, help="Image shape as WxH or W,H")

    parser.add_argument("files", nargs="*", help="Optional list of data files to open")

    return parser


if __name__ == "__main__":
    PyMcaAppInit.init_before_app_create()
    exit_code = CliUtils.cli_main(main, build_parser(), loggers=(_logger,))
    sys.exit(exit_code)
