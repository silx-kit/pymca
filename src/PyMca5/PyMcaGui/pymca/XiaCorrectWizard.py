#/*##########################################################################
# Copyright (C) 2004-2024 European Synchrotron Radiation Facility
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
__author__ = "E. Papillon - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5 import PyMcaDirs

import os.path


class XiaCorrectionWidget(qt.QWizardPage):
    def __init__(self, parent=None):
        qt.QWizardPage.__init__(self, parent)

        layout= qt.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        self.deadCheck= qt.QCheckBox("DeadTime correction", self)
        self.liveCheck= qt.QCheckBox("LiveTime normalization", self)

        lineSep= qt.QFrame(self)
        lineSep.setFrameStyle(qt.QFrame.HLine|qt.QFrame.Sunken)

        optWidget= qt.QWidget(self)
        optLayout= qt.QHBoxLayout(optWidget)
        self.sumCheck= qt.QCheckBox("SUM or", optWidget)
        self.avgCheck= qt.QCheckBox("AVERAGE selected detectors", optWidget)

        optLayout.addWidget(self.sumCheck, 0)
        optLayout.addWidget(self.avgCheck, 1)

        layout.addWidget(self.deadCheck)
        layout.addWidget(self.liveCheck)
        layout.addWidget(lineSep)
        layout.addWidget(optWidget)

        self.sumCheck.toggled[bool].connect(self.__sumCheckChanged)
        self.avgCheck.toggled[bool].connect(self.__avgCheckChanged)

        sumWidget= qt.QWidget(self)
        sumLayout= qt.QHBoxLayout(sumWidget)
        sumLayout.setContentsMargins(0, 0, 0, 0)
        sumLayout.setSpacing(5)

        butWidget= qt.QWidget(sumWidget)
        butLayout= qt.QVBoxLayout(butWidget)
        butLayout.setContentsMargins(0, 0, 0, 0)
        butLayout.setSpacing(0)

        self.sumTable= qt.QTableWidget(sumWidget)
        self.sumTable.setRowCount(0)
        self.sumTable.setColumnCount(1)
        item = self.sumTable.horizontalHeaderItem(0)
        if item is None:
            item = qt.QTableWidgetItem("Detectors",
                                    qt.QTableWidgetItem.Type)
        item.setText("Detectors")
        self.sumTable.setHorizontalHeaderItem(0, item)

        self.sumTable.cellChanged[int,int].connect(self.__valueChanged)

        buttonAdd= qt.QPushButton("Add", butWidget)
        buttonDel= qt.QPushButton("Remove", butWidget)

        butLayout.addWidget(buttonAdd)
        butLayout.addWidget(buttonDel)
        butLayout.addStretch()

        buttonAdd.clicked.connect(self.__add)
        buttonDel.clicked.connect(self.__remove)

        sumLayout.addWidget(self.sumTable)
        sumLayout.addWidget(butWidget)

        layout.addWidget(sumWidget)

    def set(self, pars= {}):
        self.deadCheck.setChecked(pars.get("deadtime", 0))
        self.liveCheck.setChecked(pars.get("livetime", 0))
        sums= pars.get("sums", None)
        self.sumTable.setNumRows(0)
        if sums is None:
            self.sumCheck.setChecked(0)
        else:
            self.sumCheck.setChecked(1)
            for sum in sums:
                self.addSum(sum)

    def check(self):
        pars= self.get()
        if not pars["deadtime"] and not pars["livetime"] and pars["sums"] is None:
            qt.QMessageBox.warning(self, "No corections or sum", \
                    "You must at least choose one of livetime, deadtime or sum detectors.", \
                    qt.QMessageBox.Ok, qt.QMessageBox.NoButton)
            return None
        else:
            return pars

    def get(self):
        pars= {}
        pars["deadtime"]= int(self.deadCheck.isChecked())
        pars["livetime"]= int(self.liveCheck.isChecked())
        pars["avgflag"]= int(self.avgCheck.isChecked())
        pars["sums"]= None
        if self.sumCheck.isChecked() or self.avgCheck.isChecked():
            sums= []
            for row in range(self.sumTable.rowCount()):
                dets= qt.safe_str(self.sumTable.item(row, 0).text())
                if dets.find("All")!=-1:
                    sums.append([])
                else:
                    sums.append([ int(det) for det in dets.split() ])
            if len(sums):
                pars["sums"]= sums
        return pars


    def addSum(self, detectors= [], name=None):
        num= self.sumTable.rowCount()
        self.sumTable.setRowCount(num + 1)

        if len(detectors):
            itemText= " ".join(detectors)
        else:
            itemText= "All"
        item = self.sumTable.item(num, 0)
        if item is None:
            item = qt.QTableWidgetItem("Detectors",
                                    qt.QTableWidgetItem.Type)
            self.sumTable.setItem(num, 0, item)
        item.setText(itemText)

    def __add(self):
        if not self.sumCheck.isChecked() and not self.avgCheck.isChecked():
            self.sumCheck.setChecked(1)
        else:
            self.addSum()

    def __remove(self):
        self.sumTable.removeRow(self.sumTable.currentRow())
        if not self.sumTable.rowCount():
            self.sumCheck.setChecked(0)

    def __valueChanged(self, row, col):
        if col==0:
            item = self.sumTable.item(row, col)
            if item is None:
                item = qt.QTableWidgetItem("",
                                           qt.QTableWidgetItem.Type)
                self.sumTable.setItem(row, col, item)
            text= qt.safe_str(item.text())
            if text.find("All")!=-1 or text.find("all")!=-1 or text.find("-1")!=-1:
                item.setText("All")
            else:
                detsplit= text.replace(",", " ")
                detsplit= detsplit.replace(";", " ")
                detsplit= detsplit.replace(":", " ")
                detsplit= detsplit.split()
                dets= []
                for det in detsplit:
                    try:
                        detno= int(det)
                    except Exception:
                        detno= -1
                    if detno>=0:
                        dets.append(det)

                if len(dets):
                    item.setText(' '.join(dets))
                else:
                    item.setText("All")

    def __sumCheckChanged(self, state):
        if state:
            if self.avgCheck.isChecked():
                self.avgCheck.setChecked(0)
            if not self.sumTable.rowCount():
                self.addSum()

    def __avgCheckChanged(self, state):
        if state:
            if self.sumCheck.isChecked():
                self.sumCheck.setChecked(0)
            if not self.sumTable.rowCount():
                self.addSum()


class XiaInputWidget(qt.QWizardPage):
    def __init__(self, parent=None):
        qt.QWizardPage.__init__(self, parent)

        layout= qt.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        self.listFiles= qt.QListWidget(self)
        self.listFiles.setSelectionMode(qt.QAbstractItemView.ExtendedSelection)

        butWidget= qt.QWidget(self)
        butLayout= qt.QHBoxLayout(butWidget)
        butLayout.setContentsMargins(0, 0, 0, 0)
        butLayout.setSpacing(5)

        butRemove= qt.QPushButton("Remove", butWidget)
        butFiles= qt.QPushButton("Add Files", butWidget)
        butDirectory= qt.QPushButton("Add Directory", butWidget)

        butRemove.clicked.connect(self.__remove)
        butFiles.clicked.connect(self.__addFiles)
        butDirectory.clicked.connect(self.__addDirectory)

        butLayout.addWidget(butRemove)
        butLayout.addWidget(butFiles)
        butLayout.addWidget(butDirectory)

        layout.addWidget(self.listFiles)
        layout.addWidget(butWidget)

    def __addFiles(self):
        files = PyMcaFileDialogs.getFileList(self,
                                             filetypelist=["Edf Files (*.edf)",
                                                           "All Files (*)"],
                                             message="Add XIA Edf Files",
                                             getfilter=False,
                                             mode="OPEN",
                                             single=False)
        for name in files:
            self.__addInFileList("file", name)

    def __addInFileList(self, type, name):
        itemname= "%s:%s"%(type, name)
        for i in range(self.listFiles.count()):
            item = self.listFiles.item(i)
            if qt.safe_str(item.text())==itemname:
                return 0
        self.listFiles.addItem(itemname)
        return 1

    def __addDirectory(self):
        directory = PyMcaFileDialogs.getExistingDirectory(self,
                                                          message="Add Full Directory",
                                                          mode="OPEN")
        if directory not in [None, ""]:
            self.__addInFileList("directory", directory)

    def __remove(self):
        todel= []
        for i in range(self.listFiles.count()):
            item = self.listFiles.item(i)
            if item.isSelected():
                todel.append(i)

        todel.reverse()
        for item in todel:
            self.listFiles.takeItem(item)

    def __getFileList(self):
        files= []
        for i in range(self.listFiles.count()):
            item = self.listFiles.item(i)
            (type, name)= qt.safe_str(item.text()).split(":", 1)
            if type=="file":
                files.append(os.path.normpath(name))
            else:
                files += [os.path.join(name, file) for file in os.listdir(name)]
        return files

    def get(self):
        pars= {}
        pars["files"]= self.__getFileList()
        return pars

    def check(self):
        pars= self.get()
        if not len(pars["files"]):
            return None
        else:
            return pars



class XiaOutputWidget(qt.QWizardPage):

    DefaultOutname= "corr"

    def __init__(self, parent=None):
        qt.QWizardPage.__init__(self, parent)
        #, name, fl)

        layout= qt.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        topWidget= qt.QWidget(self)
        topLayout= qt.QGridLayout(topWidget)
        topLayout.setContentsMargins(0, 0, 0, 0)
        topLayout.setSpacing(5)

        dirLabel=  qt.QLabel("Directory", topWidget)
        nameLabel= qt.QLabel("Prefix name", topWidget)

        topLayout.addWidget(dirLabel, 0, 0)
        topLayout.addWidget(nameLabel, 1, 0)

        self.directory= qt.QLineEdit(topWidget)
        self.outname= qt.QLineEdit(topWidget)

        topLayout.addWidget(self.directory, 0, 1)
        topLayout.addWidget(self.outname, 1, 1)

        self.directory.returnPressed[()].connect(self.__directoryCheck)

        butDirectory= qt.QPushButton("Find", topWidget)
        butOutname= qt.QPushButton("Default", topWidget)

        topLayout.addWidget(butDirectory, 0, 2)
        topLayout.addWidget(butOutname, 1, 2)

        butDirectory.clicked.connect(self.__openDirectory)
        butOutname.clicked.connect(self.__defaultOutname)

        lineSep= qt.QFrame(self)
        lineSep.setFrameStyle(qt.QFrame.HLine|qt.QFrame.Sunken)

        self.forceCheck= qt.QCheckBox("Force overwriting existing files", self)
        self.verboseCheck= qt.QCheckBox("Verbose mode", self)

        layout.addWidget(topWidget)
        layout.addWidget(lineSep)
        layout.addWidget(self.forceCheck)
        layout.addWidget(self.verboseCheck)
        layout.addStretch()

        self.__defaultOutname()

    def __openDirectory(self):
        wdir = PyMcaDirs.outputDir
        outfile = qt.QFileDialog(self)
        outfile.setWindowTitle("Set Output Directory")
        outfile.setModal(1)
        outfile.setDirectory(wdir)
        outfile.setFileMode(outfile.DirectoryOnly)
        ret = outfile.exec()
        directory = None
        if ret:
            directory = qt.safe_str(outfile.selectedFiles()[0])
            outfile.close()
        else:
            outfile.close()
        del outfile
        if directory is not None:
            self.directory.setText(directory)

    def __directoryCheck(self):
        dirname= qt.safe_str(self.directory.text())
        if len(dirname):
            if not os.path.isdir(dirname):
                qt.QMessageBox.warning(self, "Output Directory", \
                    "The output directory specified does not exist !!", \
                    qt.QMessageBox.Ok, qt.QMessageBox.NoButton)
                return 0
        else:
            dirname= None
        return dirname

    def __defaultOutname(self):
        self.outname.setText(self.DefaultOutname)

    def get(self):
        pars= {}
        pars["force"]= int(self.forceCheck.isChecked())
        pars["verbose"]= int(self.verboseCheck.isChecked())
        pars["output"]= self.__directoryCheck()
        if pars["output"]==0:
            pars["output"]= None
        pars["name"]= qt.safe_str(self.outname.text())
        if not len(pars["name"]):
            pars["name"]= self.DefaultOutname

        return pars

    def check(self):
        if self.__directoryCheck()==0:
            return None
        else:
            return self.get()


class XiaRunWidget(qt.QWidget):
    sigStarted  = qt.pyqtSignal(())
    sigFinished  = qt.pyqtSignal(())
    def __init__(self, parent=None, name=None, fl=0):
        qt.QWidget.__init__(self, parent, name, fl)

        layout= qt.QVBoxLayout(self, 10, 5)

        self.logText= qt.QTextEdit(self)
        self.logText.setReadOnly(1)

        progressWidget= qt.QWidget(self)
        progressLayout= qt.QHBoxLayout(progressWidget, 0, 5)

        self.progressBar= qt.QProgressBar(progressWidget)
        self.startButton= qt.QPushButton("Start", progressWidget)
        font= self.startButton.font()
        font.setBold(1)
        self.startButton.setFont(font)

        progressLayout.addWidget(self.progressBar)
        progressLayout.addWidget(self.startButton)

        layout.addWidget(self.logText)
        layout.addWidget(progressWidget)

        self.startButton.clicked.connect(self.start)

        self.parameters= {}

    def set(self, pars):
        self.parameters= pars

    def start(self):
        self.sigStarted.emit(())
        import time
        for idx in range(30):
            self.logText.append("%d"%idx)
            qApp = qt.QApplication.instance()
            qApp.processEvents()
            time.sleep(.5)
            print(idx)
        self.sigFinished.emit(())

class XiaCorrectWizard(qt.QWizard):
    def __init__(self, parent=None, name=None, modal=0, fl=0):
        qt.QWizard.__init__(self, parent)
        self.setModal(modal)
        #fl)

        try:
            self.setWizardStyle(qt.QWizard.ClassicStyle)
        except AttributeError:
            self.setWizardStyle(qt.QWizard.WizardStyle.ClassicStyle)

        self.setWindowTitle("Xia Correction Tool")
        self.resize(qt.QSize(400,300))

        self.correction= XiaCorrectionWidget(self)
        self.input= XiaInputWidget(self)
        self.output= XiaOutputWidget(self)

        self.addPage(self.correction)
        #, "Corrections")
        self.addPage(self.input)
        #, "Input Files")
        self.addPage(self.output)
        #, "Output Directory")

        finish= self.button(qt.QWizard.FinishButton)
        font= finish.font()
        font.setBold(1)
        finish.setFont(font)
        finish.setText("Start")

        nnext = self.button(qt.QWizard.NextButton)
        nnext.clicked.connect(self.next)

        #self.setFinishEnabled(self.output, 1)
        self.output.setFinalPage(True)

        self.parameters= {}

    def next(self):
        widget= self.page(self.currentId() - 1)
        pars= widget.check()
        if pars is not None:
            self.parameters.update(pars)
            #qt.QWizard.next(self)

    def selected(self, name):
        if name==self.title(self.run):
            self.run.set(self.parameters)
            self.setBackEnabled(self.run, 0)

    def accept(self):
        pars= self.output.check()
        if pars is not None:
            self.parameters.update(pars)
            qt.QWizard.accept(self)

    def get(self):
        return self.parameters

if __name__=="__main__":
    import sys

    app= qt.QApplication(sys.argv)
    wid= XiaCorrectWizard()
    app.setMainWidget(wid)
    app.lastWindowClosed.connect(app.quit)
    wid.show()
    app.exec()
    print(wid.get())

