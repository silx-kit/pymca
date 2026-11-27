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
import os
from PyMca5.PyMcaGui import PyMcaQt as qt
QTVERSION = qt.qVersion()
from PyMca5.PyMcaGui.math.fitting import SpecfitGui
from PyMca5.PyMcaMath.fitting import Specfit

class McaSimpleFit(qt.QWidget):
    sigMcaSimpleFitSignal = qt.pyqtSignal(object)
    def __init__(self, parent=None, name="McaSimpleFit", specfit=None,fl=0):
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle(name)
        if specfit is None:
            self.specfit = Specfit.Specfit()
        else:
            self.specfit = specfit
        layout = qt.QVBoxLayout(self)
        ##############
        self.headerlabel = qt.QLabel(self)
        self.headerlabel.setAlignment(qt.Qt.AlignHCenter)
        self.setheader('<b>Fit of XXXXXXXXXX from Channel XXXXX to XXXX<\b>')
        ##############
        defaultFunctions = "SpecfitFunctions.py"
        if not os.path.exists(defaultFunctions):
            defaultFunctions = os.path.join(os.path.dirname(__file__),
                                            defaultFunctions)
        self.specfit.importfun(defaultFunctions)
        self.specfit.settheory('Area Gaussians')
        self.specfit.setbackground('Linear')

        fitconfig = {}
        fitconfig.update(self.specfit.fitconfig)
        fitconfig['WeightFlag'] = 1
        fitconfig['McaMode']    = 1
        self.specfit.configure(**fitconfig)
        self.specfitGui = SpecfitGui.SpecfitGui(self,config=1, status=1, buttons=0,
                                    specfit = self.specfit,eh=self.specfit.eh)

        layout.addWidget(self.headerlabel)
        layout.addWidget(self.specfitGui)

        hbox = qt.QWidget(self)
        hboxLayout = qt.QHBoxLayout(hbox)
        self.estimatebutton = qt.QPushButton(hbox)
        self.estimatebutton.setText("Estimate")
        hs1 = qt.HorizontalSpacer(hbox)
        self.fitbutton = qt.QPushButton(hbox)
        self.fitbutton.setText("Fit Again!")
        self.dismissbutton = qt.QPushButton(hbox)
        self.dismissbutton.setText("Dismiss")
        self.estimatebutton.clicked.connect(self.estimate)
        self.fitbutton.clicked.connect(self.fit)
        self.dismissbutton.clicked.connect(self.dismiss)
        self.specfitGui.sigSpecfitGuiSignal.connect(self.__anasignal)
        hs2 = qt.HorizontalSpacer(hbox)
        hboxLayout.addWidget(hs1)
        hboxLayout.addWidget(self.estimatebutton)
        hboxLayout.addWidget(self.fitbutton)
        hboxLayout.addWidget(self.dismissbutton)
        hboxLayout.addWidget(hs2)
        layout.addWidget(hbox)
        self.estimatebutton.hide()

    def setdata(self,*var,**kw):
        self.info ={}
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
        self.specfit.setdata(var,**kw)
        try:
            self.info['xmin'] = "%.3f" % min(self.specfit.xdata[0], self.specfit.xdata[-1])
        except Exception:
            self.info['xmin'] = 'First'
        try:
            self.info['xmax'] = "%.3f" % max(self.specfit.xdata[0], self.specfit.xdata[-1])
        except Exception:
            self.info['xmax'] = 'Last'
        self.setheader(text="Fit of %s from %s %s to %s" % (self.info['legend'],
                                                            self.info['xlabel'],
                                                            self.info['xmin'],
                                                            self.info['xmax']))

    def setheader(self,*var,**kw):
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
            #the GUI already takes care of mcafit
            self.specfitGui.estimate()
        else:
            #self.specfitGui.estimate()
            self.specfitGui.startfit()

    def estimate(self):
        fitconfig = {}
        fitconfig.update(self.specfit.fitconfig)
        self.specfitGui.updateGui(configuration=fitconfig)
        self.specfitGui.estimate()

    def _emitSignal(self, ddict):
        self.sigMcaSimpleFitSignal.emit(ddict)

    def __anasignal(self,ddict):
        if type(ddict) != type({}):
            return
        if 'event' in ddict:
            if ddict['event'].upper() == "PRINT":
                h = self.__htmlheader()
                ndict={}
                ndict['event'] = "McaSimpleFitPrint"
                ndict['text' ] = h+ddict['text']
                ndict['info' ] = {}
                ndict['info'].update(self.info)
                self.sigMcaSimpleFitSignal.emit(ndict)
            if ddict['event'] == "McaModeChanged":
                if ddict['data']:
                    self.estimatebutton.hide()
                else:
                    self.estimatebutton.show()
            else:
                ddict['info'] = {}
                ddict['info'].update(self.info)
                if ddict['event'] == 'FitFinished':
                    #write the simple fit output in a form acceptable by McaWindow
                    ddict['event'] = 'McaFitFinished'
                    ddict['data'] = [self.specfitGui.specfit.mcagetresult()]
                self.sigMcaSimpleFitSignal.emit(ddict)

    def dismiss(self):
        self.close()

    def closeEvent(self, event):
        ddict = {}
        ddict["event"] = "McaSimpleFitClosed"
        self.sigMcaSimpleFitSignal.emit(ddict)
        return qt.QWidget.closeEvent(self, event)

    def __htmlheader(self):
        try:
            header="Fit of %s from %s %s to %s" % (self.info['legend'],
                                            self.info['xlabel'],
                                            self.info['xmin'],
                                            self.info['xmax'])
        except Exception:
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
        h=""
        h+="    <CENTER>"
        h+="<B>%s</B>" % header
        h+="<BR></BR>"
        h+="<TABLE>"
        h+="<TR>"
        h+="    <TD ALIGN=LEFT><B>Function</B></TD>"
        h+="    <TD><B>:</B></TD>"
        h+="    <TD ALIGN=LEFT>%s</TD>" % theory
        h+="    <TD><SPACER TYPE=BLOCK WIDTH=50></TD>"
        h+="    <TD ALIGN=RIGHT><B>Weight</B></TD>"
        h+="    <TD><B>:</B></TD>"
        h+="    <TD ALIGN=LEFT>%s</TD>" % weight
        h+="    <TD><SPACER TYPE=BLOCK WIDTH=10></B></TD>"
        h+="    <TD ALIGN=RIGHT><B>FWHM</B></TD>"
        h+="    <TD><B>:</B></TD></TD>"
        h+="    <TD ALIGN=LEFT>%d</TD>" % fwhm
        h+="</TR>"
        h+="<TR>"
        h+="    <TD ALIGN=LEFT><B>Background</B></TH>"
        h+="    <TD><B>:</B></TD>"
        h+="    <TD ALIGN=LEFT>%s</TD>" % bkg
        h+="    <TD><SPACER TYPE=BLOCK WIDTH=50></B></TD>"
        h+="    <TD ALIGN=RIGHT><B>MCA Mode</B></TD>"
        h+="    <TD><B>:</B></TD>"
        h+="    <TD ALIGN=LEFT>%s</TD>" % mode
        h+="    <TD><SPACER TYPE=BLOCK WIDTH=10></B></TD>"
        h+="    <TD ALIGN=RIGHT><B>Scaling</B></TD>"
        h+="    <TD><B>:</B></TD>"
        h+="    <TD ALIGN=LEFT>%g</TD>" % scaling
        h+="</TR>"
        h+="</TABLE>"
        h+="</CENTER>"
        return h


if __name__ == "__main__":
    import sys
    app = qt.QApplication(sys.argv)
    demo = McaSimpleFit()
    demo.show()
    app.exec()
