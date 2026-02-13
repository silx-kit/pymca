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
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import logging
if __name__== '__main__':
    # avoid issues if some module or dependency tries to use multiprocessing in frozen binaries
    if getattr(sys, "frozen", False):
        try:
            import multiprocessing
            multiprocessing.freeze_support()
        except Exception:
            pass
from PyMca5.PyMcaGui import PyMcaQt as qt

QTVERSION = qt.qVersion()
_logger = logging.getLogger(__name__)

from PyMca5.PyMcaGui.io import QSourceSelector
from PyMca5.PyMcaGui.pymca import QDataSource
from PyMca5.PyMcaGui.io import QEdfFileWidget

class EdfFileSimpleViewer(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        self.sourceList = []
        filetypelist = ["EDF Files (*edf)",
                        "EDF Files (*ccd)",
                        "All Files (*)"]

        self.sourceSelector = QSourceSelector.QSourceSelector(self, filetypelist = filetypelist)
        self.sourceSelector.specButton.hide()
        self.selectorWidget = {}
        self.selectorWidget[QEdfFileWidget.SOURCE_TYPE] = QEdfFileWidget.\
                                        QEdfFileWidget(self,justviewer=1)
        self.mainLayout.addWidget(self.sourceSelector)
        self.mainLayout.addWidget(self.selectorWidget[QEdfFileWidget.SOURCE_TYPE])

        self.sourceSelector.sigSourceSelectorSignal.connect( \
                self._sourceSelectorSlot)

    def _sourceSelectorSlot(self, ddict):
        _logger.debug("_sourceSelectorSlot(self, ddict)")
        _logger.debug("ddict = %s", ddict)
        if ddict["event"] == "NewSourceSelected":
            source = QDataSource.QDataSource(ddict["sourcelist"])
            self.sourceList.append(source)
            sourceType = source.sourceType
            self.selectorWidget[sourceType].setDataSource(source)
        elif ddict["event"] == "SourceSelected":
            found = 0
            for source in self.sourceList:
                if source.sourceName == ddict["sourcelist"]:
                    found = 1
                    break
            if not found:
                _logger.debug("WARNING: source not found")
                return
            sourceType = source.sourceType
            self.selectorWidget[sourceType].setDataSource(source)
        elif ddict["event"] == "SourceClosed":
            found = 0
            for source in self.sourceList:
                if source.sourceName == ddict["sourcelist"]:
                    found = 1
                    break
            if not found:
                _logger.debug("WARNING: source not found")
                return
            sourceType = source.sourceType
            del self.sourceList[self.sourceList.index(source)]
            for source in self.sourceList:
                if sourceType == source.sourceType:
                    self.selectorWidget[sourceType].setDataSource(source)
                    return
            #there is no other selection of that type
            if len(self.sourceList):
                source = self.sourceList[0]
                sourceType = source.sourceType
                self.selectorWidget[sourceType].setDataSource(source)
            else:
                self.selectorWidget[sourceType].setDataSource(None)

    def setFileList(self, filelist):
        for ffile in filelist:
            self.sourceSelector.openFile(ffile, justloaded = 1)


def main():
    import sys
    import getopt
    import glob
    from PyMca5.PyMcaCore.LoggingLevel import getLoggingLevel
    app=qt.QApplication(sys.argv)
    winpalette = qt.QPalette(qt.QColor(230,240,249),qt.QColor(238,234,238))
    app.setPalette(winpalette)
    options=''
    longoptions=['logging=', 'debug=']
    opts, args = getopt.getopt(
                    sys.argv[1:],
                    options,
                    longoptions)
    logging.basicConfig(level=getLoggingLevel(opts))
    _logger.setLevel(getLoggingLevel(opts))
    filelist = args
    if len(filelist) == 1:
        if sys.platform.startswith("win")  and '*' in filelist[0]:
            filelist = glob.glob(filelist[0])
    app.lastWindowClosed.connect(app.quit)
    w=EdfFileSimpleViewer()
    if len(filelist):
        w.setFileList(filelist)
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
