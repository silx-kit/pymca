#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2026 European Synchrotron Radiation Facility
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
__author__ = "V. Armando Sole - ESRF"
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
from PyMca5.PyMcaPhysics import Elements
from PyMca5.PyMcaGui.plotting import PyMca_Icons
IconDict = PyMca_Icons.IconDict
QTVERSION = qt.qVersion()

_logger = logging.getLogger(__name__)


class PeakIdentifier(qt.QWidget):
    sigPeakIdentifierSignal = qt.pyqtSignal(object)
    def __init__(self,parent=None,energy=None,threshold=None,useviewer=None,
                 name="Peak Identifier"):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle(name)
        self.setWindowIcon(qt.QIcon(qt.QPixmap(IconDict['gioconda16'])))

        if energy    is None: energy    = 5.9
        if threshold is None: threshold = 0.030
        if useviewer is None: useviewer = 0
        self.__useviewer = useviewer

        layout = qt.QVBoxLayout(self)
        #heading
        self.__energyHBox=qt.QWidget(self)
        hbox = self.__energyHBox
        hbox.layout = qt.QHBoxLayout(hbox)
        hbox.layout.setContentsMargins(0, 0, 0, 0)
        hbox.layout.setSpacing(0)
        layout.addWidget(hbox)
        hbox.layout.addWidget(qt.HorizontalSpacer(hbox))

        l1=qt.QLabel(hbox)
        l1.setText('<b><nobr>Energy (keV)</nobr></b>')
        hbox.layout.addWidget(l1)
        self.energy=MyQLineEdit(hbox)
        self.energy.setText("%.3f" % energy)
        self.energy._validator = qt.CLocaleQDoubleValidator(self.energy)
        self.energy.setValidator(self.energy._validator)
        self.energy.setToolTip('Press enter to validate your energy')
        hbox.layout.addWidget(self.energy)
        hbox.layout.addWidget(qt.HorizontalSpacer(hbox))
        self.energy.editingFinished.connect(self._energySlot)
        #parameters
        self.__hbox2 = qt.QWidget(self)
        hbox2 = self.__hbox2

        layout.addWidget(hbox2)
        hbox2.layout = qt.QHBoxLayout(hbox2)
        hbox2.layout.setContentsMargins(0, 0, 0, 0)
        hbox2.layout.setSpacing(0)
        font=hbox2.font()
        font.setBold(1)
        hbox2.setFont(font)


        l2=qt.QLabel(hbox2)
        l2.setText('Energy Threshold (eV)')
        self.threshold=qt.QSpinBox(hbox2)
        self.threshold.setMinimum(0)
        self.threshold.setMaximum(1000)
        self.threshold.setValue(int(threshold*1000))
        self.k = qt.QCheckBox(hbox2)
        self.k.setText('K')
        self.k.setChecked(1)
        self.l1 = qt.QCheckBox(hbox2)
        self.l1.setText('L1')
        self.l1.setChecked(1)
        self.l2 = qt.QCheckBox(hbox2)
        self.l2.setText('L2')
        self.l2.setChecked(1)
        self.l3 = qt.QCheckBox(hbox2)
        self.l3.setText('L3')
        self.l3.setChecked(1)
        self.m = qt.QCheckBox(hbox2)
        self.m.setText('M')
        self.m.setChecked(1)
        self.threshold.valueChanged[int].connect(self._thresholdSlot)
        self.k.clicked.connect(self._mySlot)
        self.l1.clicked.connect(self._mySlot)
        self.l2.clicked.connect(self._mySlot)
        self.l3.clicked.connect(self._mySlot)
        self.m.clicked.connect(self._mySlot)

        hbox2.layout.addWidget(l2)
        hbox2.layout.addWidget(self.threshold)
        hbox2.layout.addWidget(self.k)
        hbox2.layout.addWidget(self.l1)
        hbox2.layout.addWidget(self.l2)
        hbox2.layout.addWidget(self.l3)
        hbox2.layout.addWidget(self.m)

        if self.__useviewer:
            self.__browsertext = qt.QTextEdit(self)
            layout.addWidget(self.__browsertext)
        self.setEnergy(energy)

    def setEnergy(self, energy = None):
        if energy is None:
            energy = 5.9
        if type(energy) == type(""):
            self.energy.setText("%s" % energy)
            self._energySlot()
        else:
            self.energy.setText("%.3f" % energy)
            self.mySlot(energy=energy)

    def _energySlot(self):
        qstring = self.energy.text()
        try:
            value = float(qt.safe_str(qstring))
            self.energyvalue = value
            self.mySlot()
            self.energy.setPaletteBackgroundColor(
                qt.QApplication.instance().palette().color(qt.QPalette.Base))
            cursor = self.__browsertext.textCursor()
            cursor.movePosition(qt.QTextCursor.Start)
            self.__browsertext.setTextCursor(cursor)
            self.threshold.setFocus()
        except Exception:
            msg=qt.QMessageBox(self.energy)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Invalid Float")
            msg.setWindowTitle("Invalid entry")
            msg.exec()
            self.energy.setFocus()
            return

    def myslot(self):
        _logger.info("PeakIdentifier.py myslot deprecated, use mySlot")
        return self.mySlot()

    def _thresholdSlot(self, value):
        self.mySlot()

    def _mySlot(self):
        # this intermediate is needed to prevent passing a boolean to
        # mySlot when receiving the signal from the checkboxes.
        return self.mySlot()

    def mySlot(self, energy=None):
        if energy is None:
            try:
                energy  = float(qt.safe_str(self.energy.text()))
            except ValueError:
                msg=qt.QMessageBox(self.energy)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Invalid Energy Value")
                msg.setWindowTitle("Invalid energy")
                msg.exec()
                self.energy.setFocus()
                return

        threshold = float(self.threshold.value())/1000.
        lines=[]
        if self.k.isChecked():
             lines.append('K')
        if self.l1.isChecked():
             lines.append('L1')
        if self.l2.isChecked():
             lines.append('L2')
        if self.l3.isChecked():
             lines.append('L3')
        if self.m.isChecked():
             lines.append('M')
        ddict=Elements.getcandidates(energy,threshold,lines)[0]
        ddict['text'] =self.getHtmlText(ddict)
        ddict['event']='Candidates'
        ddict['lines']=lines
        if self.__useviewer:
            self.__browsertext.clear()
            #self.__browsertext.insertHtml("<CENTER>"+dict['text']+\
            #                              "</CENTER>")
            self.__browsertext.insertHtml(ddict['text'])
        self.sigPeakIdentifierSignal.emit(ddict)

    def getHtmlText(self, ddict):
        text  = ""
        if QTVERSION < '4.0.0':
            text += "<br>"
        labels=['Element','Line','Energy','Rate']
        try:
            _palette = qt.QApplication.instance().palette()
            _Base = _palette.color(qt.QPalette.Base)
            _mid = _palette.color(qt.QPalette.AlternateBase)
            lemmon = _Base.name().upper()
            hcolor = _mid.name().upper()
        except Exception:
            lemmon = ("#%x%x%x" % (255,250,205))
            lemmon = lemmon.upper()
            hcolor = ("#%x%x%x" % (230,240,249))
            hcolor = hcolor.upper()
        text+="<CENTER>"
        text+=("<nobr>")
        text+=( "<table WIDTH=80%%>")
        text+=( "<tr>")
        for l in labels:
            text+=('<td align="left" bgcolor="%s"><b>' % hcolor)
            text+=l
            text+=("</b></td>")
        text+=("</tr>")
        for ele in ddict['elements']:
            oldline=""
            for line in ddict[ele]:
                if   line[0][0:1] == 'K':
                    group0 = 'K  rays'
                elif line[0][0:2] == 'L1':
                    group0 = 'L1 rays'
                elif line[0][0:2] == 'L2':
                    group0 = 'L2 rays'
                elif line[0][0:2] == 'L3':
                    group0 = 'L3 rays'
                elif line[0][0:1] == 'M':
                    group0 = 'M rays'
                else:
                    group0 = 'Unknown'
                if group0 != oldline:
                    text +="<tr>"
                    text += '<td align="left"><b>%s</b></td>' % ele
                    text += '<td align="left"><b>%s</b></td>' % group0
                    text += '</tr>'
                    oldline = group0
            #for peak in result[group]['peaks']:
                text += '<tr><td></td>'
                name   = line[0]
                energy = ("%.3f" % line[1])
                ratio  = ("%.5f" % line[2])
                fields = [name,energy,ratio]
                for field in fields:
                    if field == name:
                        text+=('<td align="left"  bgcolor="%s">%s</td>' % (lemmon,field))
                    else:
                        text+=('<td align="right" bgcolor="%s">%s</td>' % (lemmon,field))
                text+="</tr>"
        text+=("</table>")
        text+=("</nobr>")
        text+="</CENTER>"
        return text

class MyQLineEdit(qt.QLineEdit):
    def __init__(self,parent=None,name=None):
        qt.QLineEdit.__init__(self,parent)
        self.setAutoFillBackground(True)

    def setPaletteBackgroundColor(self, color):
        palette = qt.QPalette()
        role = self.backgroundRole()
        palette.setColor(role,color)
        self.setPalette(palette)


    def focusInEvent(self,event):
        self.setPaletteBackgroundColor(
            qt.QApplication.instance().palette().color(qt.QPalette.Highlight))
        # TODO not like focusOutEvent ?
        '''
        if QTVERSION > '4.0.0':
            qt.QLineEdit.focusInEvent(self, event)
        '''

    def focusOutEvent(self,event):
        self.setPaletteBackgroundColor(
            qt.QApplication.instance().palette().color(qt.QPalette.Base))
        qt.QLineEdit.focusOutEvent(self, event)

def main():
    logging.basicConfig(level=logging.INFO)
    app  = qt.QApplication(sys.argv)
    if len(sys.argv) > 1:
        ene = float(sys.argv[1])
    else:
        ene = 5.9
    mw = qt.QWidget()
    l  = qt.QVBoxLayout(mw)
    l.setSpacing(0)
    w= PeakIdentifier(mw,energy=ene,useviewer=1)
    l.addWidget(w)
    mw.setWindowTitle("Peak Identifier")
    mw.show()
    app.exec()

if __name__ == "__main__":
    main()
