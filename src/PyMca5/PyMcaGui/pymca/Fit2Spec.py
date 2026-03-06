#!/usr/bin/env python
#/*##########################################################################
# Copyright (C) 2004-2026 V.A. Sole, European Synchrotron Radiation Facility
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
        self.outputDir = None
        self.setFileList(filelist or [])
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

    def setFileList(self, filelist=None):
        filelist = filelist or []
        if True or self.__goodFileList(filelist):
            filelist = sorted(filelist)
            text = "\n".join(filelist)
            self.fileList = filelist
            self.__listView.setText(text)

    def setOutputDir(self, outputdir=None):
        if not outputdir:
            return
        if self.__goodOutputDir(outputdir):
            self.outputDir = outputdir
            self.__outLine.setText(outputdir)
        else:
            qt.QMessageBox.critical(self, "ERROR", f"Cannot use output directory:\n{outputdir}")

    def __goodFileList(self, filelist):
        for file in filelist:
            if not os.path.exists(file):
                qt.QMessageBox.critical(self, "ERROR", f'File {file}\ndoes not exist')
                self.raiseW()
                return False
        return True

    def __goodOutputDir(self, outputdir):
        return os.path.isdir(outputdir)

    def browseList(self):
        filedialog = qt.QFileDialog(self, "Open a set of files")
        filedialog.setFileMode(qt.QFileDialog.ExistingFiles)
        filedialog.setNameFilters(["Fit Files (*.fit)"])

        if filedialog.exec() == qt.QDialog.Accepted:
            filelist0 = filedialog.selectedFiles()
        else:
            self.raiseW()
            return

        filelist = [qt.safe_str(f) for f in filelist0]
        if filelist:
            self.setFileList(filelist)
        self.raiseW()

    def browseConfig(self):
        dialog = qt.QFileDialog(self, "Open a new fit config file")
        dialog.setFileMode(qt.QFileDialog.ExistingFile)
        dialog.setNameFilters(["Config Files (*.cfg)", "All files (*)"])

        if dialog.exec() == qt.QDialog.Accepted:
            filename = dialog.selectedFiles()[0]
        else:
            self.raiseW()
            return

        filename = qt.safe_str(filename)
        if filename:
            self.setConfigFile(filename)
        self.raiseW()

    def browseOutputDir(self):
        dialog = qt.QFileDialog(self, "Output Directory Selection")
        dialog.setFileMode(qt.QFileDialog.Directory)
        dialog.setOption(qt.QFileDialog.ShowDirsOnly, True)

        if dialog.exec() == qt.QDialog.Accepted:
            outdir = qt.safe_str(dialog.selectedFiles()[0])
            self.setOutputDir(outdir)
        self.raiseW()

    def start(self):
        if not getattr(self, "fileList", []):
            qt.QMessageBox.critical(self, "ERROR", 'Empty file list')
            self.raiseW()
            return
        if (self.outputDir is None) or (not self.__goodOutputDir(self.outputDir)):
            qt.QMessageBox.critical(self, "ERROR", 'Invalid output directory')
            self.raiseW()
            return

        name = f"Batch from {os.path.basename(self.fileList[0])} to {os.path.basename(self.fileList[-1])}"
        window = Fit2SpecWindow(name="Fit 2 Spec " + name, actions=1)
        b = Fit2SpecBatch(window, self.fileList, self.outputDir)

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
        qt.QApplication.instance().aboutToQuit.connect(cleanup)

        self.__window = window
        self.__b = b
        window.show()
        b.start()

    def raiseW(self):
        self.raise_()
        self.activateWindow()


class Fit2SpecBatch(qt.QThread):
    def __init__(self, parent, filelist=None, outputdir=None):
        super().__init__(parent)
        self.parent = parent
        self._filelist = filelist or []
        self.outputdir = outputdir
        self.pleasePause = 0
        self.pleaseBreak = 0

    def _postEvent(self, event):
        qt.QApplication.postEvent(self.parent, event)

    def processList(self):
        for fitfile in self._filelist:
            if self.pleaseBreak:
                break
            self.onNewFile(fitfile, self._filelist)

            d = ConfigDict.ConfigDict()
            d.read(fitfile)

            outfile = os.path.join(self.outputdir, os.path.basename(fitfile) + ".dat")
            with open(outfile, "w") as f:
                npoints = len(d['result']['xdata'])
                f.write("\n")
                f.write(f"#S 1 {fitfile}\n")
                for i, parameter in enumerate(d['result']['parameters']):
                    f.write(f"#U{i} {parameter} {d['result']['fittedpar'][i]:.6g} +/- {d['result']['sigmapar'][i]:.3g}\n")
                f.write("#N 6\n")
                f.write("#L Energy  channel  counts  fit  continuum  pileup\n")
                for i in range(npoints):
                    f.write(f"{d['result']['energy'][i]:.6g}  {d['result']['xdata'][i]:.6g}  "
                            f"{d['result']['ydata'][i]:.6g}  {d['result']['yfit'][i]:.6g}  "
                            f"{d['result']['continuum'][i]:.6g}  {d['result']['pileup'][i]:.6g}\n")
        self.onEnd()

    def run(self):
        self.processList()

    def onNewFile(self, file, filelist):
        self._postEvent(McaCustomEvent.McaCustomEvent({'file': file,
                                                       'filelist': filelist,
                                                       'event': 'onNewFile'}))
        if self.pleasePause:
            self.__pauseMethod()

    def onEnd(self):
        self._postEvent(McaCustomEvent.McaCustomEvent({'event': 'onEnd'}))
        if self.pleasePause:
            self.__pauseMethod()

    def __pauseMethod(self):
        self._postEvent(McaCustomEvent.McaCustomEvent({'event': 'batchPaused'}))
        while self.pleasePause:
            time.sleep(1)
        self._postEvent(McaCustomEvent.McaCustomEvent({'event': 'batchResumed'}))


class Fit2SpecWindow(qt.QWidget):
    def __init__(self, parent=None, name="BatchWindow", actions=0):
        super().__init__(parent)

        self.setObjectName(name)
        self.setWindowTitle(name)

        self.l = qt.QVBoxLayout(self)

        # Progress section
        self.bars = qt.QWidget(self)
        barsLayout = qt.QGridLayout(self.bars)
        self.progressLabel = qt.QLabel("File Progress:", self.bars)
        self.progressBar = qt.QProgressBar(self.bars)
        barsLayout.addWidget(self.progressLabel, 0, 0)
        barsLayout.addWidget(self.progressBar, 0, 1)
        self.l.addWidget(self.bars)

        # Status labels
        self.status = qt.QLabel(" ", self)
        self.timeLeft = qt.QLabel("Estimated time left = ???? min", self)
        self.l.addWidget(self.status)
        self.l.addWidget(self.timeLeft)

        self.time0 = None
        self.actions = actions
        if actions:
            self.addButtons()

        self.show()
        self.raiseW()

    def addButtons(self):
        self.buttonsBox = qt.QWidget(self)
        l = qt.QHBoxLayout(self.buttonsBox)
        l.addStretch(1)
        self.pauseButton = qt.QPushButton("Pause", self.buttonsBox)
        l.addWidget(self.pauseButton)
        l.addSpacing(10)
        self.abortButton = qt.QPushButton("Abort", self.buttonsBox)
        l.addWidget(self.abortButton)
        l.addStretch(1)
        self.l.addWidget(self.buttonsBox)

    def customEvent(self, event):
        if event.dict['event'] == 'onNewFile':
            self.onNewFile(event.dict['file'], event.dict['filelist'])
        elif event.dict['event'] == 'onEnd':
            self.onEnd(event.dict)
        elif event.dict['event'] == 'batchPaused':
            self.onPause()
        elif event.dict['event'] == 'batchResumed':
            self.onResume()
        else:
            print("Unhandled event", event)

    def onNewFile(self, file, filelist):
        index = filelist.index(file)
        nfiles = len(filelist)
        self.status.setText(f"Processing file {file}")
        self.progressBar.setMaximum(nfiles)
        self.progressBar.setValue(index)

        now = time.time()
        if self.time0 is not None:
            t = (now - self.time0) * (nfiles - index)
            self.time0 = now
            if t < 120:
                self.timeLeft.setText(f"Estimated time left = {int(t)} sec")
            else:
                self.timeLeft.setText(f"Estimated time left = {int(t / 60)} min")
        else:
            self.time0 = now

    def onEnd(self, dict=None):
        n = self.progressBar.value()
        self.progressBar.setValue(n + 1)
        self.status.setText("Batch Finished")
        self.timeLeft.setText("Estimated time left = 0 sec")
        if self.actions:
            self.pauseButton.hide()
            self.abortButton.setText("OK")

    def onPause(self):
        pass

    def onResume(self):
        pass

    def raiseW(self):
        self.raise_()
        self.activateWindow()


def main(args):
    # Prepare file list
    if args.listfile is None:
        filelist = args.files or []
    else:
        with open(args.listfile, 'r') as fd:
            filelist = [line.strip() for line in fd.readlines()]

    # Qt application
    app = qt.QApplication([])
    PyMcaAppInit.init_before_app_start(qt_app=app, cli_args=args)

    # Launch GUI if no files provided
    if not filelist:
        w = Fit2SpecGUI(actions=1)
        w.show()
    else:
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


# Example FIT file:
#
# [result]
# parameters = [100.0 5.89 0.12]
# fittedpar  = [98.0 5.87 0.13]
# sigmapar   = [5.0 0.02 0.01]
# xdata      = [1 2 3 4 5 6 7 8 9 10]
# ydata      = [10 12 15 18 25 35 30 20 12 5]
# yfit       = [9.8 11.9 14.7 17.9 24.8 34.9 30.2 19.8 12.1 4.9]
# energy     = [1.0 2.0 3.0 4.0 5.0 6.0 7.0 8.0 9.0 10.0]
# continuum  = [0.5 0.5 0.5 0.5 0.5 0.5 0.5 0.5 0.5 0.5]
# pileup     = [0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0]
#
# The resulting SPEC file:
#
# #S 1 example.fit
# #U0 100.0 98 +/- 5
# #U1 5.89 5.87 +/- 0.02
# #U2 0.12 0.13 +/- 0.01
# #N 6
# #L Energy  channel  counts  fit  continuum  pileup
# 1  1  10  9.8  0.5  0
# 2  2  12  11.9  0.5  0
# 3  3  15  14.7  0.5  0
# 4  4  18  17.9  0.5  0
# 5  5  25  24.8  0.5  0
# 6  6  35  34.9  0.5  0
# 7  7  30  30.2  0.5  0
# 8  8  20  19.8  0.5  0
# 9  9  12  12.1  0.5  0
# 10  10  5  4.9  0.5  0
