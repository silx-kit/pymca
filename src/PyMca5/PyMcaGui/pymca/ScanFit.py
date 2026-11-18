#/*##########################################################################
# Copyright (C) 2004-2023 European Synchrotron Radiation Facility
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
import os
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.math.fitting import SpecfitGui
from PyMca5.PyMcaMath.fitting import Specfit
QTVERSION = qt.qVersion()


class ScanFit(qt.QWidget):
    sigScanFitSignal = qt.pyqtSignal(object)
    def __init__(self, parent=None, name="ScanFit", specfit=None, fl=0):
                #fl=qt.Qt.WDestructiveClose):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle(name)

        if specfit is None:
            self.specfit = Specfit.Specfit()
        else:
            self.specfit = specfit
        self.info = None
        layout = qt.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        ##############
        self.headerlabel = qt.QLabel(self)
        self.headerlabel.setAlignment(qt.Qt.AlignHCenter)
        self.setHeader('<b>Fit of XXXXXXXXXX from X XXXXX to XXXX<\b>')
        ##############
        if not len(self.specfit.theorylist):
            funsFile = "SpecfitFunctions.py"
            if not os.path.exists(funsFile):
                funsFile = os.path.join(os.path.dirname(Specfit.__file__),
                                        funsFile)
            self.specfit.importfun(funsFile)
        if 'Area Gaussians' not in self.specfit.theorylist:
            funsFile = "SpecfitFunctions.py"
            if not os.path.exists(funsFile):
                funsFile = os.path.join(os.path.dirname(Specfit.__file__),
                                        funsFile)
            self.specfit.importfun(funsFile)
        self.specfit.settheory('Area Gaussians')
        self.specfit.setbackground('Linear')
        fitconfig = {}
        fitconfig.update(self.specfit.fitconfig)
        fitconfig['WeightFlag'] = 0
        fitconfig['ForcePeakPresence'] = 1
        fitconfig['McaMode']    = 0
        self.specfit.configure(**fitconfig)
        self.specfitGui = SpecfitGui.SpecfitGui(self, config=1, status=1,
                                                buttons=0,
                                                specfit=self.specfit,
                                                eh=self.specfit.eh)
        #self.specfitGui.updateGui(configuration=fitconfig)
        #self.setdata = self.specfit.setdata

        self.specfitGui.guiconfig.MCACheckBox.setEnabled(1)
        palette = self.specfitGui.guiconfig.MCACheckBox.palette()
        ##############
        hbox = qt.QWidget(self)
        hboxlayout = qt.QHBoxLayout(hbox)
        hboxlayout.setContentsMargins(0, 0, 0, 0)
        hboxlayout.setSpacing(0)
        self.estimatebutton = qt.QPushButton(hbox)
        self.estimatebutton.setText("Estimate")
        self.fitbutton = qt.QPushButton(hbox)
        self.fitbutton.setText("Fit")
        hboxlayout.addWidget(self.estimatebutton)
        hboxlayout.addWidget(qt.HorizontalSpacer(hbox))
        hboxlayout.addWidget(self.fitbutton)

        self.dismissbutton = qt.QPushButton(hbox)
        self.dismissbutton.setText("Dismiss")
        self.estimatebutton.clicked.connect(self.estimate)
        self.fitbutton.clicked.connect(self.fit)
        self.dismissbutton.clicked.connect(self.dismiss)
        self.specfitGui.sigSpecfitGuiSignal.connect(self._specfitGuiSignal)
        hboxlayout.addWidget(qt.HorizontalSpacer(hbox))
        hboxlayout.addWidget(self.dismissbutton)
        layout.addWidget(self.headerlabel)
        layout.addWidget(self.specfitGui)
        layout.addWidget(hbox)

    def setData(self, *var, **kw):
        self.info = {}
        if 'legend' in kw:
            self.info['legend'] = kw['legend']
            del kw['legend']
        else:
            self.info['legend'] = 'Unknown Origin'
        if 'xlabel' in kw:
            self.info['xlabel'] = kw['xlabel']
            del kw['xlabel']
        else:
            self.info['xlabel'] = 'X'
        self.specfit.setdata(var, **kw)
        try:
            self.info['xmin'] = "%.3f" % self.specfit.xdata[0]
        except Exception:
            self.info['xmin'] = 'First'
        try:
            self.info['xmax'] = "%.3f" % self.specfit.xdata[-1]
        except Exception:
            self.info['xmax'] = 'Last'
        self.setHeader(text="Fit of %s from %s %s to %s" % (self.info['legend'],
                                                            self.info['xlabel'],
                                                            self.info['xmin'],
                                                            self.info['xmax']))

    def setheader(self, *var, **kw):
        return self.setHeader(*var, **kw)

    def setHeader(self, *var, **kw):
        if len(var):
            text = var[0]
        elif 'text' in kw:
            text = kw['text']
        elif 'header' in kw:
            text = kw['header']
        else:
            text = ""
        self.headerlabel.setText("<b>%s<\b>" % text)

    def fit(self):
        if self.specfit.fitconfig['McaMode']:
            fitconfig = {}
            fitconfig.update(self.specfit.fitconfig)
            self.specfitGui.updateGui(configuration=fitconfig)
            #the Gui already takes care of mcafit
            self.specfitGui.estimate()
        else:
            #exception handler to be implemented
            #self.specfitGui.estimate()
            self.specfitGui.startfit()

    def estimate(self):
        fitconfig = {}
        fitconfig.update(self.specfit.fitconfig)
        self.specfitGui.updateGui(configuration=fitconfig)
        self.specfitGui.estimate()

    def _specfitGuiSignal(self, ddict):
        if not hasattr(ddict, "keys"):
            return
        if 'event' in ddict:
            if ddict['event'].upper() == "PRINT":
                h = self.__htmlheader()
                ndict = {}
                ndict['event'] = "ScanFitPrint"
                ndict['text' ] = h + ddict['text']
                ndict['info' ] = {}
                ndict['info'].update(self.info)
                self.sigScanFitSignal.emit(ndict)
            else:
                if self.info is None:
                    self.info = {}
                ddict['info'] = {}
                ddict['info'].update(self.info)
                self.sigScanFitSignal.emit(ddict)

    def dismiss(self):
        self.close()

    def __htmlheader(self):
        try:
            header = "Fit of %s from %s %s to %s" % (self.info['legend'],
                                                     self.info['xlabel'],
                                                     self.info['xmin'],
                                                     self.info['xmax'])
        except Exception:
            # I cannot afford any unicode, key or whatever error, so,
            # provide a default value for the label.
            header = 'Fit of XXXXXXXXXX from Channel XXXXX to XXXX'
        if self.specfit.fitconfig['WeightFlag']:
            weight = "YES"
        else:
            weight = "NO"
        if self.specfit.fitconfig['McaMode']:
            mode = "YES"
        else:
            mode = "NO"
        theory   = self.specfit.fitconfig['fittheory']
        bkg      = self.specfit.fitconfig['fitbkg']
        fwhm     = self.specfit.fitconfig['FwhmPoints']
        scaling  = self.specfit.fitconfig['Yscaling']
        h = ""
        h += "    <CENTER>"
        h += "<B>%s</B>" % header
        h += "<BR></BR>"
        h += "<TABLE>"
        h += "<TR>"
        h += "    <TD ALIGN=LEFT><B>Function</B></TD>"
        h += "    <TD><B>:</B></TD>"
        h += "    <TD ALIGN=LEFT>%s</TD>" % theory
        h += "    <TD><SPACER TYPE=BLOCK WIDTH=50></TD>"
        h += "    <TD ALIGN=RIGHT><B>Weight</B></TD>"
        h += "    <TD><B>:</B></TD>"
        h += "    <TD ALIGN=LEFT>%s</TD>" % weight
        h += "    <TD><SPACER TYPE=BLOCK WIDTH=10></B></TD>"
        h += "    <TD ALIGN=RIGHT><B>FWHM</B></TD>"
        h += "    <TD><B>:</B></TD></TD>"
        h += "    <TD ALIGN=LEFT>%d</TD>" % fwhm
        h += "</TR>"
        h += "<TR>"
        h += "    <TD ALIGN=LEFT><B>Background</B></TH>"
        h += "    <TD><B>:</B></TD>"
        h += "    <TD ALIGN=LEFT>%s</TD>" % bkg
        h += "    <TD><SPACER TYPE=BLOCK WIDTH=50></B></TD>"
        h += "    <TD ALIGN=RIGHT><B>MCA Mode</B></TD>"
        h += "    <TD><B>:</B></TD>"
        h += "    <TD ALIGN=LEFT>%s</TD>" % mode
        h += "    <TD><SPACER TYPE=BLOCK WIDTH=10></B></TD>"
        h += "    <TD ALIGN=RIGHT><B>Scaling</B></TD>"
        h += "    <TD><B>:</B></TD>"
        h += "    <TD ALIGN=LEFT>%g</TD>" % scaling
        h += "</TR>"
        h += "</TABLE>"
        h += "</CENTER>"
        return h

    def getText(self):
        try:
            header = "Fit of %s from %s %s to %s" % (self.info['legend'],
                                                     self.info['xlabel'],
                                                     self.info['xmin'],
                                                     self.info['xmax'])
        except Exception:
            # I cannot afford any unicode, key or whatever error, so,
            # provide a default value for the header text.
            header = 'Fit of XXXXXXXXXX from Channel XXXXX to XXXX'
        text = header + "\n"
        if self.specfit.fitconfig['WeightFlag']:
            weight = "YES"
        else:
            weight = "NO"
        if self.specfit.fitconfig['McaMode']:
            mode = "YES"
        else:
            mode = "NO"
        theory   = self.specfit.fitconfig['fittheory']
        bkg      = self.specfit.fitconfig['fitbkg']
        fwhm     = self.specfit.fitconfig['FwhmPoints']
        scaling  = self.specfit.fitconfig['Yscaling']
        text += "Fit Function: %s\n" % theory
        text += "Background: %s\n" % bkg
        text += "Weight: %s  McaMode: %s  FWHM: %d  Yscaling: %f\n" % (weight[0],
                                                                       mode[0],
                                                                       fwhm,
                                                                       scaling)
        text += self.specfitGui.guiparameters.getText()
        return text

    def getConfiguration(self):
        return self.specfit.configure()

    def setConfiguration(self, fitconfig):
        self.specfit.configure(**fitconfig)
        self.specfitGui.updateGui(configuration=fitconfig)

def main():
    app = qt.QApplication([])
    w = ScanFit()
    app.lastWindowClosed.connect(app.quit)
    w.show()
    app.exec()

if __name__ == "__main__":
    main()
