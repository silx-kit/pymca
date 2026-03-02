#!/usr/bin/env python
#/*##########################################################################
# Copyright (C) 2004-2016 V.A. Sole, European Synchrotron Radiation Facility
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

from PyMca5.PyMcaGui import PyMcaAppInit

if __name__== '__main__':
    PyMcaAppInit.init_before_app_import()

import os
import sys
import time

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaIO import ConfigDict
from PyMca5.PyMcaMisc import CliUtils

from . import McaCustomEvent

ROIWIDTH = 250.


class Fit2SpecGUI(qt.QWidget):
    def __init__(self, parent=None, name="Fit to Spec Conversion",
                 filelist=None, outputdir=None, actions=0):
        super().__init__(parent)
        self.setWindowTitle(name)

        # Main vertical layout
        main_layout = qt.QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Form grid (input files + output dir)
        self.__grid = qt.QWidget(self)
        grid = qt.QGridLayout(self.__grid)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 0)
        grid.setRowStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)

        # Input file list
        list_label = qt.QLabel("Input File list:", self.__grid)
        list_label.setAlignment(qt.Qt.AlignVCenter | qt.Qt.AlignLeft)
        list_label.setWordWrap(True)

        self.__listView = qt.QTextEdit(self.__grid)
        self.__listView.setReadOnly(True)
        self.__listView.setMinimumHeight(120)
        self.__listView.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Expanding)

        self.__listButton = qt.QPushButton("Browse", self.__grid)
        self.__listButton.clicked.connect(self.browseList)

        grid.addWidget(list_label, 0, 0, alignment=qt.Qt.AlignTop | qt.Qt.AlignLeft)
        grid.addWidget(self.__listView, 0, 1)
        grid.addWidget(self.__listButton, 0, 2, alignment=qt.Qt.AlignTop | qt.Qt.AlignRight)

        # Output directory
        out_label = qt.QLabel("Output dir:", self.__grid)
        out_label.setAlignment(qt.Qt.AlignLeft | qt.Qt.AlignVCenter)
        out_label.setWordWrap(True)

        self.__outLine = qt.QLineEdit(self.__grid)
        self.__outLine.setReadOnly(True)
        self.__outLine.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed)

        self.__outButton = qt.QPushButton("Browse", self.__grid)
        self.__outButton.clicked.connect(self.browseOutputDir)

        grid.addWidget(out_label, 1, 0, alignment=qt.Qt.AlignLeft)
        grid.addWidget(self.__outLine, 1, 1)
        grid.addWidget(self.__outButton, 1, 2, alignment=qt.Qt.AlignLeft)

        main_layout.addWidget(self.__grid)

        # Action buttons
        if actions:
            self.__buildActions()

        # Initialize file list & output dir
        if filelist is None:
            filelist = []
        self.outputDir = None
        self.setFileList(filelist)
        self.setOutputDir(outputdir)

    def __buildActions(self):
        box = qt.QHBoxLayout()
        box.addStretch(1)

        self.__dismissButton = qt.QPushButton("Close")
        self.__startButton = qt.QPushButton("Start")

        box.addWidget(self.__dismissButton)
        box.addSpacing(20)
        box.addWidget(self.__startButton)
        box.addStretch(1)

        self.__dismissButton.clicked.connect(self.close)
        self.__startButton.clicked.connect(self.start)

        container = qt.QWidget(self)
        container.setLayout(box)
        self.layout().addWidget(container)

    def setFileList(self,filelist=None):
        if filelist is None:
            filelist = []
        if True or self.__goodFileList(filelist):
            text = ""
            filelist.sort()
            for ffile in filelist:
                text += "%s\n" % ffile
            self.fileList = filelist
            self.__listView.setText(text)

    def setOutputDir(self,outputdir=None):
        if outputdir is None:return
        if self.__goodOutputDir(outputdir):
            self.outputDir = outputdir
            self.__outLine.setText(outputdir)
        else:
            qt.QMessageBox.critical(self, "ERROR",
            "Cannot use output directory:\n%s"% (outputdir))

    def __goodFileList(self,filelist):
        if not len(filelist):return True
        for file in filelist:
            if not os.path.exists(file):
                qt.QMessageBox.critical(self, "ERROR",'File %s\ndoes not exists' % file)
                self.raiseW()
                return False
        return True

    def __goodOutputDir(self,outputdir):
        if os.path.isdir(outputdir):return True
        else:return False

    def browseList(self):
        filedialog = qt.QFileDialog(self,"Open a set of files",1)
        filedialog.setMode(filedialog.ExistingFiles)
        if hasattr(filedialog, "setFilters"):
            filedialog.setFilters("Fit Files (*.fit)\n")
        else:
            filedialog.setNameFilters("Fit Files (*.fit)\n")
        if filedialog.exec_loop() == qt.QDialog.Accepted:
            filelist0= filedialog.selectedFiles()
        else:
            self.raiseW()
            return
        filelist = []
        for f in filelist0:
            filelist.append(qt.safe_str(f))
        if len(filelist):self.setFileList(filelist)
        self.raiseW()

    def browseConfig(self):
        filename= qt.QFileDialog(self,"Open a new fit config file",1)
        filename.setMode(filename.ExistingFiles)
        filename.setFilters("Config Files (*.cfg)\nAll files (*)")
        if filename.exec_loop() == qt.QDialog.Accepted:
            filename = filename.selectedFile()
        else:
            self.raiseW()
            return
        filename = qt.safe_str(filename)
        if len(filename):
            self.setConfigFile(filename)
        self.raiseW()

    def browseOutputDir(self):
        outfile = qt.QFileDialog(self,"Output Directory Selection",1)
        outfile.setMode(outfile.DirectoryOnly)
        ret = outfile.exec_loop()
        if ret:
            outdir = qt.safe_str(outfile.selectedFile())
            outfile.close()
            del outfile
            self.setOutputDir(outdir)
        else:
            outfile.close()
            del outfile
        self.raiseW()

    def start(self):
        if not len(self.fileList):
            qt.QMessageBox.critical(self, "ERROR",'Empty file list')
            self.raiseW()
            return
        if (self.outputDir is None) or (not self.__goodOutputDir(self.outputDir)):
            qt.QMessageBox.critical(self, "ERROR",'Invalid output directory')
            self.raiseW()
            return
        name = "Batch from %s to %s " % (os.path.basename(self.fileList[ 0]),
                                          os.path.basename(self.fileList[-1]))

        window =  Fit2SpecWindow(name="Fit 2 Spec "+name,actions=1)
        b = Fit2SpecBatch(window,self.fileList,self.outputDir)
        def cleanup():
            b.pleasePause = 0
            b.pleaseBreak = 1
            b.wait()
            qApp = qt.QApplication.instance()
            qApp.processEvents()

        def pause():
            if b.pleasePause:
                b.pleasePause=0
                window.pauseButton.setText("Pause")
            else:
                b.pleasePause=1
                window.pauseButton.setText("Continue")
        window.pauseButton.clicked.connect(pause)
        window.abortButton.clicked.connect(window.close)
        qApp = qt.QApplication.instance()
        qApp.aboutToQuit.connect(cleanup)
        self.__window = window
        self.__b      = b
        window.show()
        b.start()


class Fit2SpecBatch(qt.QThread):
    def __init__(self, parent, filelist=None, outputdir = None):
        self._filelist  = filelist
        self.outputdir = outputdir
        qt.QThread.__init__(self)
        self.parent = parent
        self.pleasePause = 0

    def processList(self):
        for fitfile in self._filelist:
            self.onNewFile(fitfile, self._filelist)
            d = ConfigDict.ConfigDict()
            d.read(fitfile)
            f = open(os.path.join(self.outputdir,os.path.basename(fitfile)+".dat"),'w+')
            npoints = len(d['result']['xdata'])
            f.write("\n")
            f.write("#S 1 %s\n" % fitfile)
            i=0
            for parameter in d['result']['parameters']:
                f.write("#U%d %s %.6g +/- %.3g\n" % (i, parameter,
                                                     d['result']['fittedpar'][i],
                                                     d['result']['sigmapar'][i]))
                i+=1
            f.write("#N 6\n")
            f.write("#L Energy  channel  counts  fit  continuum  pileup\n")
            for i in range(npoints):
                f.write("%.6g  %.6g   %.6g  %.6g  %.6g  %.6g\n" % (d['result']['energy'][i],
                                   d['result']['xdata'][i],
                                   d['result']['ydata'][i],
                                   d['result']['yfit'][i],
                                   d['result']['continuum'][i],
                                   d['result']['pileup'][i]))
            f.close()
        self.onEnd()

    def run(self):
        self.processList()

    def onNewFile(self, file, filelist):
        self.postEvent(self.parent, McaCustomEvent.McaCustomEvent({'file':file,
                                                                   'filelist':filelist,
                                                                   'event':'onNewFile'}))
        if self.pleasePause:self.__pauseMethod()

    def onEnd(self):
        self.postEvent(self.parent, McaCustomEvent.McaCustomEvent({'event':'onEnd'}))
        if self.pleasePause:self.__pauseMethod()


    def __pauseMethod(self):
        self.postEvent(self.parent, McaCustomEvent.McaCustomEvent({'event':'batchPaused'}))
        while(self.pleasePause):
            time.sleep(1)
        self.postEvent(self.parent, McaCustomEvent.McaCustomEvent({'event':'batchResumed'}))


class Fit2SpecWindow(qt.QWidget):
    def __init__(self,parent=None, name="BatchWindow", fl=0, actions = 0):
        super().__init__(parent)

        self.setObjectName(name)
        self.setWindowTitle(name)

        self.setCaption(name)

        self.l = qt.QVBoxLayout(self)
        self.bars =qt.QWidget(self)
        self.barsLayout = qt.QGridLayout(self.bars,2,3)
        self.progressBar   = qt.QProgressBar(self.bars)
        self.progressLabel = qt.QLabel(self.bars)
        self.progressLabel.setText('File Progress:')

        self.barsLayout.addWidget(self.progressLabel,0,0)
        self.barsLayout.addWidget(self.progressBar,0,1)
        self.status      = qt.QLabel(self)
        self.status.setText(" ")
        self.timeLeft      = qt.QLabel(self)
        self.timeLeft.setText("Estimated time left = ???? min")
        self.time0 = None

        if actions:
            self.addButtons()

        self.show()
        self.raiseW()

    def addButtons(self):
        self.actions = 1
        self.buttonsBox = qt.QWidget(self)
        l = qt.QHBoxLayout(self.buttonsBox)
        l.setAutoAdd(1)
        qt.HorizontalSpacer(self.buttonsBox)
        self.pauseButton = qt.QPushButton(self.buttonsBox)
        qt.HorizontalSpacer(self.buttonsBox)
        self.pauseButton.setText("Pause")
        self.abortButton   = qt.QPushButton(self.buttonsBox)
        qt.HorizontalSpacer(self.buttonsBox)
        self.abortButton.setText("Abort")
        self.update()

    def customEvent(self,event):
        if   event.dict['event'] == 'onNewFile':self.onNewFile(event.dict['file'],
                                                               event.dict['filelist'])
        elif event.dict['event'] == 'onEnd':    self.onEnd(event.dict)

        elif event.dict['event'] == 'batchPaused': self.onPause()

        elif event.dict['event'] == 'batchResumed':self.onResume()

        else:
            print("Unhandled event",event)


    def onNewFile(self, file, filelist):
        indexlist = range(0,len(filelist))
        index  = indexlist.index(filelist.index(file))
        nfiles = len(indexlist)
        self.status.setText("Processing file %s" % file)
        e = time.time()
        self.progressBar.setTotalSteps(nfiles)
        self.progressBar.setProgress(index)
        if self.time0 is not None:
            t = (e - self.time0) * (nfiles - index)
            self.time0 =e
            if t < 120:
                self.timeLeft.setText("Estimated time left = %d sec" % (t))
            else:
                self.timeLeft.setText("Estimated time left = %d min" % (int(t / 60.)))
        else:
            self.time0 = e

    def onEnd(self,dict):
        n = self.progressBar.progress()
        self.progressBar.setProgress(n+1)
        self.status.setText  ("Batch Finished")
        self.timeLeft.setText("Estimated time left = 0 sec")
        if self.actions:
            self.pauseButton.hide()
            self.abortButton.setText("OK")

    def onPause(self):
        pass

    def onResume(self):
        pass


def main(args):
    # Prepare file list
    if args.listfile is None:
        filelist = args.files or []
    else:
        with open(args.listfile, 'r') as fd:
            filelist = [line.strip() for line in fd.readlines()]

    # Qt application
    app = PyMcaAppInit.create_qt_app(cli_args=args)

    # Launch GUI if no files provided
    if len(filelist) == 0:
        w = Fit2SpecGUI(actions=1)
        w.show()
    else:
        # Otherwise launch batch processing
        text = f"Batch from {os.path.basename(filelist[0])} to {os.path.basename(filelist[-1])}"
        window = Fit2SpecWindow(name=text, actions=1)
        b = Fit2SpecBatch(window, filelist, args.outdir)

        # Cleanup and pause handling
        def cleanup():
            b.pleasePause = 0
            b.pleaseBreak = 1
            if hasattr(b, "wait"):
                b.wait()
            qt.QApplication.instance().processEvents()

        def pause():
            if b.pleasePause:
                b.pleasePause = 0
                window.pauseButton.setText("Pause")
            else:
                b.pleasePause = 1
                window.pauseButton.setText("Continue")

        window.pauseButton.clicked.connect(pause)
        window.abortButton.clicked.connect(window.close)
        app.aboutToQuit.connect(cleanup)

        window.show()
        b.start()

    # Auto-close Qt for tests
    if args.cli_test:
        qt.QTimer.singleShot(0, app.quit)

    return app.exec()


def build_parser():
    parser = CliUtils.create_parser(description="Fit2Spec GUI launcher", add_qt_options=True)

    parser.add_argument("--outdir", type=str, default=None, help="Output directory")
    parser.add_argument("--listfile", type=str, default=None, help="File containing list of input files")

    parser.add_argument("files", nargs="*", help="Files to process if --listfile not provided")

    return parser


if __name__ == "__main__":
    PyMcaAppInit.init_before_app_create()
    exit_code = CliUtils.cli_main(main, build_parser())
    sys.exit(exit_code)
