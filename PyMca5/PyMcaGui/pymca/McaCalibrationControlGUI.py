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
import sys
import os
import logging

from PyMca5.PyMcaGui import PyMcaQt as qt
QTVERSION = qt.qVersion()
if hasattr(qt, "QString"):
    QString = qt.QString
else:
    QString = qt.safe_str

from PyMca5 import PyMcaDirs

_logger = logging.getLogger(__name__)

class McaCalibrationControlGUI(qt.QWidget):
    sigMcaCalibrationControlGUISignal = qt.pyqtSignal(object)

    def __init__(self, parent=None, name=""):
        qt.QWidget.__init__(self, parent)
        if name is not None:
            self.setWindowTitle(name)
        self.lastInputDir = None
        self.build()
        self.connections()

    def build(self):
        layout = qt.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.calbox =    None
        self.calbut =    None

        calibration  = McaCalibrationControlLine(self)
        self.calbox  = calibration.calbox
        self.calbut  = calibration.calbut
        self.calinfo = McaCalibrationInfoLine(self)

        self.calmenu = qt.QMenu()
        self.calmenu.addAction(QString("Edit"),    self._copysignal)
        self.calmenu.addAction(QString("Compute") ,self._computesignal)
        self.calmenu.addSeparator()
        self.calmenu.addAction(QString("Load") ,   self._loadsignal)
        self.calmenu.addAction(QString("Save") ,   self._savesignal)

        layout.addWidget(calibration)
        layout.addWidget(self.calinfo)

    def connections(self):
        #selection changed
        #self.connect(self.calbox,qt.SIGNAL("activated(const QString &)"),
        #            self._calboxactivated)
        self.calbox.activated.connect(self._calboxactivated)
        self.calbut.clicked.connect(self._calbuttonclicked)

    def _calboxactivated(self, item=None):
        _logger.debug("Calibration box activated %s", qt.safe_str(item))
        comboitem, combotext = self.calbox.getCurrent()
        self._emitpysignal(box=[comboitem, combotext],
                           boxname='Calibration',
                           event='activated')

    def _calbuttonclicked(self):
        _logger.debug("Calibration button clicked")
        self.calmenu.exec_(self.cursor().pos())

    def _copysignal(self):
        comboitem, combotext = self.calbox.getCurrent()
        self._emitpysignal(button="CalibrationCopy",
                           box=[comboitem, combotext],
                           event='clicked')

    def _computesignal(self):
        comboitem, combotext = self.calbox.getCurrent()
        self._emitpysignal(button="Calibration",
                           box=[comboitem, combotext],
                           event='clicked')

    def _loadsignal(self):
        if self.lastInputDir is None:
            self.lastInputDir = PyMcaDirs.inputDir
        if self.lastInputDir is not None:
            if not os.path.exists(self.lastInputDir):
                self.lastInputDir = None
        self.lastInputFilter = "Calibration files (*.calib)\n"
        if sys.platform == "win32":
            windir = self.lastInputDir
            if windir is None:
                windir = os.getcwd()
            filename = qt.safe_str(qt.QFileDialog.getOpenFileName(self,
                          "Load existing calibration file",
                          windir,
                          self.lastInputFilter))
        else:
            windir = self.lastInputDir
            if windir is None:windir = os.getcwd()
            filename = qt.QFileDialog(self)
            filename.setWindowTitle("Load existing calibration file")
            filename.setModal(1)
            if hasattr(qt, "QStringList"):
                strlist = qt.QStringList()
            else:
                strlist = []
            tmp = [self.lastInputFilter.replace("\n","")]
            for filetype in tmp:
                strlist.append(filetype.replace("(","").replace(")",""))
            if hasattr(filename, "setFilters"):
                filename.setFilters(strlist)
            else:
                filename.setNameFilters(strlist)
            filename.setFileMode(qt.QFileDialog.ExistingFile)
            filename.setDirectory(windir)
            ret = filename.exec_()
            if ret:
                if len(filename.selectedFiles()):
                    filename = qt.safe_str(filename.selectedFiles()[0])
                else:
                    return
            else:
                return
        if not len(filename):
            return
        if len(filename) < 6:
            filename = filename + ".calib"
        elif filename[-6:] != ".calib":
            filename = filename + ".calib"
        self.lastInputDir = os.path.dirname(filename)
        comboitem,combotext = self.calbox.getCurrent()
        self._emitpysignal(button="CalibrationLoad",
                           box=[comboitem,combotext],
                           line_edit = filename,
                           event='clicked')

    def _savesignal(self):
        if self.lastInputDir is None:
            self.lastInputDir = PyMcaDirs.outputDir
        if self.lastInputDir is not None:
            if not os.path.exists(self.lastInputDir):
                self.lastInputDir = None
        self.lastInputFilter = "Calibration files (*.calib)\n"
        if sys.platform == "win32":
            windir = self.lastInputDir
            if windir is None:
                windir = ""
            filename= qt.safe_str(qt.QFileDialog.getSaveFileName(self,
                          "Save a new calibration file",
                          windir,
                          self.lastInputFilter))
        else:
            windir = self.lastInputDir
            if windir is None:windir = os.getcwd()
            filename = qt.QFileDialog(self)
            filename.setWindowTitle("Save a new calibration file")
            filename.setModal(1)
            if hasattr(qt, "QStringList"):
                strlist = qt.QStringList()
            else:
                strlist = []
            tmp = [self.lastInputFilter.replace("\n","")]
            for filetype in tmp:
                strlist.append(filetype.replace("(","").replace(")",""))
            if hasattr(filename, "setFilters"):
                filename.setFilters(strlist)
            else:
                filename.setNameFilters(strlist)
            filename.setFileMode(qt.QFileDialog.AnyFile)
            filename.setDirectory(windir)
            ret = filename.exec_()
            if ret:
                if len(filename.selectedFiles()):
                    filename = qt.safe_str(filename.selectedFiles()[0])
                else:
                    return
            else:
                return

        if not len(filename):
            return
        if len(filename) < 6:
            filename = filename + ".calib"
        elif filename[-6:] != ".calib":
            filename = filename + ".calib"
        self.lastInputDir = os.path.dirname(filename)
        PyMcaDirs.outputDir = os.path.dirname(filename)
        comboitem,combotext = self.calbox.getCurrent()
        self._emitpysignal(button="CalibrationSave",
                            box=[comboitem,combotext],
                            line_edit = filename,
                            event='clicked')

    def _emitpysignal(self,button=None,
                            box=None,
                            boxname=None,
                            checkbox=None,
                            line_edit=None,
                            event=None):
        _logger.debug("_emitpysignal called %s %s", button, box)
        data={}
        data['button']        = button
        data['box']           = box
        data['checkbox']      = checkbox
        data['line_edit']     = line_edit
        data['event']         = event
        data['boxname']       = boxname
        self.sigMcaCalibrationControlGUISignal.emit(data)

class McaCalibrationControlLine(qt.QWidget):
    def __init__(self, parent=None, name=None, calname="",
                 caldict = None):
        if caldict is None:
            caldict = {}
        qt.QWidget.__init__(self, parent)
        if name is not None:
            self.setWindowTitle(name)
        self.l = qt.QHBoxLayout(self)
        self.l.setContentsMargins(0, 0, 0, 0)
        self.l.setSpacing(0)
        self.build()

    def build(self):
        widget = self
        callabel    = qt.QLabel(widget)
        callabel.setText(str("<b>%s</b>" % 'Calibration'))
        self.calbox = SimpleComboBox(widget,
                                     options=['None',
                                              'Original (from Source)',
                                              'Internal (from Source OR PyMca)'])
        self.calbox.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Expanding,
                                                 qt.QSizePolicy.Fixed))
        self.calbut = qt.QPushButton(widget)
        self.calbut.setText('Calibrate')
        self.calbut.setSizePolicy(qt.QSizePolicy(qt.QSizePolicy.Fixed,
                                                 qt.QSizePolicy.Fixed))

        self.l.addWidget(callabel)
        self.l.addWidget(self.calbox)
        self.l.addWidget(self.calbut)


class McaCalibrationInfoLine(qt.QWidget):
    def __init__(self, parent=None, name=None, calname="",
                 caldict = None):
        if caldict is None:
            caldict = {}
        qt.QWidget.__init__(self, parent)
        if name is not None:self.setWindowTitle(name)
        self.caldict=caldict
        if calname not in self.caldict.keys():
            self.caldict[calname] = {}
            self.caldict[calname]['order'] = 1
            self.caldict[calname]['A'] = 0.0
            self.caldict[calname]['B'] = 1.0
            self.caldict[calname]['C'] = 0.0
        self.currentcal = calname
        self.build()
        self.setParameters(self.caldict[calname])

    def build(self):
        layout= qt.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        parw = self

        self.lab= qt.QLabel("<nobr><b>Active Curve Uses</b></nobr>", parw)
        layout.addWidget(self.lab)

        lab= qt.QLabel("A:", parw)
        layout.addWidget(lab)

        self.AText= qt.QLineEdit(parw)
        self.AText.setReadOnly(1)
        layout.addWidget(self.AText)

        lab= qt.QLabel("B:", parw)
        layout.addWidget(lab)

        self.BText= qt.QLineEdit(parw)
        self.BText.setReadOnly(1)
        layout.addWidget(self.BText)

        lab= qt.QLabel("C:", parw)
        layout.addWidget(lab)

        self.CText= qt.QLineEdit(parw)
        self.CText.setReadOnly(1)
        layout.addWidget(self.CText)

    def setParameters(self, pars, name = None):
        if name is not None:
            self.currentcal = name
        if 'order' in pars:
            order = pars['order']
        elif pars["C"] != 0.0:
            order = 2
        else:
            order = 1
        self.AText.setText("%.8g" % pars["A"])
        self.BText.setText("%.8g" % pars["B"])
        self.CText.setText("%.8g" % pars["C"])
        """
        if pars['order'] > 1:
            self.orderbox.setCurrentItem(1)
            self.CText.setReadOnly(0)
        else:
            self.orderbox.setCurrentItem(0)
            self.CText.setReadOnly(1)
        """
        self.caldict[self.currentcal]["A"] = pars["A"]
        self.caldict[self.currentcal]["B"] = pars["B"]
        self.caldict[self.currentcal]["C"] = pars["C"]
        self.caldict[self.currentcal]["order"] = order

class SimpleComboBox(qt.QComboBox):
        def __init__(self, parent=None, name=None, options=['1','2','3']):
            qt.QComboBox.__init__(self,parent)
            self.setOptions(options)

        def setOptions(self,options=['1','2','3']):
            self.clear()
            for item in options:
                self.addItem(item)

        def getCurrent(self):
            return   self.currentIndex(), qt.safe_str(self.currentText())


if __name__ == '__main__':
    app = qt.QApplication(sys.argv)
    demo = McaCalibrationControlGUI()
    demo.show()
    app.exec_()
