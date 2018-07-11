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
import traceback
import logging
from PyMca5.PyMcaCore import EventHandler
from PyMca5.PyMcaMath.fitting import Specfit
from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui import PyMcaFileDialogs

QTVERSION = qt.qVersion()
from . import FitConfigGui
from . import MultiParameters
from . import FitActionsGui
from . import FitStatusGui
from . import QScriptOption

_logger = logging.getLogger(__name__)


class SpecfitGui(qt.QWidget):
    sigSpecfitGuiSignal = qt.pyqtSignal(object)

    def __init__(self,parent = None,name = None,fl = 0, specfit = None,
                 config = 0, status = 0, buttons = 0, eh = None):
        if name == None:
            name = "SpecfitGui"
        qt.QWidget.__init__(self, parent)
        self.setWindowTitle(name)
        layout= qt.QVBoxLayout(self)
        #layout.setAutoAdd(1)
        if eh == None:
            self.eh = EventHandler.EventHandler()
        else:
            self.eh = eh
        if specfit is None:
            self.specfit = Specfit.Specfit(eh=self.eh)
        else:
            self.specfit = specfit

        #initialize the default fitting functions in case
        #none is present
        if not len(self.specfit.theorylist):
            funsFile = "SpecfitFunctions.py"
            if not os.path.exists(funsFile):
                funsFile = os.path.join(os.path.dirname(Specfit.__file__),\
                                funsFile)
            self.specfit.importfun(funsFile)

        #copy specfit configure method for direct access
        self.configure=self.specfit.configure
        self.fitconfig=self.specfit.fitconfig

        self.setdata=self.specfit.setdata
        self.guiconfig=None
        if config:
            self.guiconfig = FitConfigGui.FitConfigGui(self)
            self.guiconfig.MCACheckBox.stateChanged[int].connect(self.mcaevent)
            self.guiconfig.WeightCheckBox.stateChanged[int].connect(self.weightevent)
            self.guiconfig.AutoFWHMCheckBox.stateChanged[int].connect(self.autofwhmevent)
            self.guiconfig.AutoScalingCheckBox.stateChanged[int].connect(self.autoscaleevent)
            self.guiconfig.ConfigureButton.clicked.connect(self.__configureGuiSlot)
            self.guiconfig.PrintPushButton.clicked.connect(self.printps)
            self.guiconfig.BkgComBox.activated[str].connect(self.bkgevent)
            self.guiconfig.FunComBox.activated[str].connect(self.funevent)
            layout.addWidget(self.guiconfig)

        self.guiparameters = MultiParameters.ParametersTab(self)
        layout.addWidget(self.guiparameters)
        self.guiparameters.sigMultiParametersSignal.connect(self.__forward)
        if config:
            for key in self.specfit.bkgdict.keys():
                self.guiconfig.BkgComBox.addItem(str(key))
            for key in self.specfit.theorylist:
                self.guiconfig.FunComBox.addItem(str(key))
            configuration={}
            if specfit is not None:
                configuration = specfit.configure()
                if configuration['fittheory'] is None:
                    self.guiconfig.FunComBox.setCurrentIndex(1)
                    self.funevent(self.specfit.theorylist[0])
                else:
                    self.funevent(configuration['fittheory'])
                if configuration['fitbkg']    is None:
                    self.guiconfig.BkgComBox.setCurrentIndex(1)
                    self.bkgevent(list(self.specfit.bkgdict.keys())[0])
                else:
                    self.bkgevent(configuration['fitbkg'])
            else:
                self.guiconfig.BkgComBox.setCurrentIndex(1)
                self.guiconfig.FunComBox.setCurrentIndex(1)
                self.funevent(self.specfit.theorylist[0])
                self.bkgevent(list(self.specfit.bkgdict.keys())[0])
            configuration.update(self.configure())
            if configuration['McaMode']:
                self.guiconfig.MCACheckBox.setChecked(1)
            else:
                self.guiconfig.MCACheckBox.setChecked(0)
            if configuration['WeightFlag']:
                self.guiconfig.WeightCheckBox.setChecked(1)
            else:
                self.guiconfig.WeightCheckBox.setChecked(0)
            if configuration['AutoFwhm']:
                self.guiconfig.AutoFWHMCheckBox.setChecked(1)
            else:
                self.guiconfig.AutoFWHMCheckBox.setChecked(0)
            if configuration['AutoScaling']:
                self.guiconfig.AutoScalingCheckBox.setChecked(1)
            else:
                self.guiconfig.AutoScalingCheckBox.setChecked(0)

        if status:
            self.guistatus =  FitStatusGui.FitStatusGui(self)
            self.eh.register('FitStatusChanged',self.fitstatus)
            layout.addWidget(self.guistatus)
        if buttons:
            self.guibuttons = FitActionsGui.FitActionsGui(self)
            self.guibuttons.EstimateButton.clicked.connect(self.estimate)
            self.guibuttons.StartfitButton.clicked.connect(self.startfit)
            self.guibuttons.DismissButton.clicked.connect(self.dismiss)
            layout.addWidget(self.guibuttons)

    def updateGui(self,configuration=None):
        self.__configureGui(configuration)

    def _emitSignal(self, ddict):
        self.sigSpecfitGuiSignal.emit(ddict)

    def __configureGuiSlot(self):
        self.__configureGui()

    def __configureGui(self, newconfiguration=None):
        if self.guiconfig is not None:
            #get current dictionary
            #print "before ",self.specfit.fitconfig['fitbkg']
            configuration=self.configure()
            #get new dictionary
            if newconfiguration is None:
                newconfiguration=self.configureGui(configuration)
            #update configuration
            configuration.update(self.configure(**newconfiguration))
            #print "after =",self.specfit.fitconfig['fitbkg']
            #update Gui
            #current function
            #self.funevent(self.specfit.theorylist[0])
            try:
                i=1+self.specfit.theorylist.index(self.specfit.fitconfig['fittheory'])
                self.guiconfig.FunComBox.setCurrentIndex(i)
                self.funevent(self.specfit.fitconfig['fittheory'])
            except:
                _logger.warning("Function not in list %s",
                                self.specfit.fitconfig['fittheory'])
                self.funevent(self.specfit.theorylist[0])
            #current background
            try:
                #the list conversion is needed in python 3.
                i=1+list(self.specfit.bkgdict.keys()).index(self.specfit.fitconfig['fitbkg'])
                self.guiconfig.BkgComBox.setCurrentIndex(i)
            except:
                _logger.warning("Background not in list %s",
                                self.specfit.fitconfig['fitbkg'])
                self.bkgevent(list(self.specfit.bkgdict.keys())[0])
            #and all the rest
            if configuration['McaMode']:
                self.guiconfig.MCACheckBox.setChecked(1)
            else:
                self.guiconfig.MCACheckBox.setChecked(0)
            if configuration['WeightFlag']:
                self.guiconfig.WeightCheckBox.setChecked(1)
            else:
                self.guiconfig.WeightCheckBox.setChecked(0)
            if configuration['AutoFwhm']:
                self.guiconfig.AutoFWHMCheckBox.setChecked(1)
            else:
                self.guiconfig.AutoFWHMCheckBox.setChecked(0)
            if configuration['AutoScaling']:
                self.guiconfig.AutoScalingCheckBox.setChecked(1)
            else:
                self.guiconfig.AutoScalingCheckBox.setChecked(0)
            #update the Gui
            self.__initialparameters()


    def configureGui(self,oldconfiguration):
        #this method can be overwritten for custom
        #it should give back a new dictionary
        newconfiguration={}
        newconfiguration.update(oldconfiguration)
        if (0):
        #example to force a given default configuration
            newconfiguration['FitTheory']="Pseudo-Voigt Line"
            newconfiguration['AutoFwhm']=1
            newconfiguration['AutoScaling']=1

        #example script options like
        if (1):
            sheet1={'notetitle':'Restrains',
                'fields':(["CheckField",'HeightAreaFlag','Force positive Height/Area'],
                          ["CheckField",'PositionFlag','Force position in interval'],
                          ["CheckField",'PosFwhmFlag','Force positive FWHM'],
                          ["CheckField",'SameFwhmFlag','Force same FWHM'],
                          ["CheckField",'EtaFlag','Force Eta between 0 and 1'],
                          ["CheckField",'NoConstrainsFlag','Ignore Restrains'])}

            sheet2={'notetitle':'Search',
                'fields':(["EntryField",'FwhmPoints', 'Fwhm Points: '],
                          ["EntryField",'Sensitivity','Sensitivity: '],
                          ["EntryField",'Yscaling',   'Y Factor   : '],
                          ["CheckField",'ForcePeakPresence',   'Force peak presence '])}
            w=QScriptOption.QScriptOption(self,name='Fit Configuration',
                            sheets=(sheet1,sheet2),
                            default=oldconfiguration)

            w.show()
            w.exec_()
            if w.result():
                newconfiguration.update(w.output)
            #we do not need the dialog any longer
            del w
            newconfiguration['FwhmPoints']=int(float(newconfiguration['FwhmPoints']))
            newconfiguration['Sensitivity']=float(newconfiguration['Sensitivity'])
            newconfiguration['Yscaling']=float(newconfiguration['Yscaling'])
        return newconfiguration

    def estimate(self):
        if self.specfit.fitconfig['McaMode']:
            try:
                mcaresult=self.specfit.mcafit()
            except:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setWindowTitle("Error on mcafit")
                msg.setInformativeText(str(sys.exc_info()[1]))
                msg.setDetailedText(traceback.format_exc())
                msg.exec_()
                ddict={}
                ddict['event'] = 'FitError'
                self._emitSignal(ddict)
                if _logger.getEffectiveLevel() == logging.DEBUG:
                    raise
                return
            self.guiparameters.fillfrommca(mcaresult)
            ddict={}
            ddict['event'] = 'McaFitFinished'
            ddict['data']  = mcaresult
            self._emitSignal(ddict)
            #self.guiparameters.removeallviews(keep='Region 1')
        else:
            try:
                if self.specfit.theorydict[self.specfit.fitconfig['fittheory']][2] is not None:
                    self.specfit.estimate()
                else:
                    msg = qt.QMessageBox(self)
                    msg.setIcon(qt.QMessageBox.Information)
                    text  = "Function does not define a way to estimate\n"
                    text += "the initial parameters. Please, fill them\n"
                    text += "yourself in the table and press Start Fit\n"
                    msg.setText(text)
                    msg.setWindowTitle('SpecfitGui Message')
                    msg.exec_()
                    return
            except:
                if _logger.getEffectiveLevel() == logging.DEBUG:
                    raise
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Error on estimate: %s" % sys.exc_info()[1])
                msg.exec_()
                return
            self.guiparameters.fillfromfit(self.specfit.paramlist,current='Fit')
            self.guiparameters.removeallviews(keep='Fit')
            ddict={}
            ddict['event'] = 'EstimateFinished'
            ddict['data']  = self.specfit.paramlist
            self._emitSignal(ddict)

        return

    def __forward(self,ddict):
        self._emitSignal(ddict)

    def startfit(self):
        if self.specfit.fitconfig['McaMode']:
            try:
                mcaresult=self.specfit.mcafit()
            except:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Error on mcafit: %s" % sys.exc_info()[1])
                msg.exec_()
                if _logger.getEffectiveLevel() == logging.DEBUG:
                    raise
                return
            self.guiparameters.fillfrommca(mcaresult)
            ddict={}
            ddict['event'] = 'McaFitFinished'
            ddict['data']  = mcaresult
            self._emitSignal(ddict)
            #self.guiparameters.removeview(view='Fit')
        else:
            #for param in self.specfit.paramlist:
            #    print param['name'],param['group'],param['estimation']
            self.specfit.paramlist=self.guiparameters.fillfitfromtable()
            for param in self.specfit.paramlist:
                _logger.debug("name %s; group %s; estimation %s",
                              param['name'], param['group'], param['estimation'])
            _logger.debug("TESTING")

            try:
                self.specfit.startfit()
            except:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Error on Fit")
                msg.exec_()
                if _logger.getEffectiveLevel() == logging.DEBUG:
                    raise
                return
            self.guiparameters.fillfromfit(self.specfit.paramlist,current='Fit')
            self.guiparameters.removeallviews(keep='Fit')
            ddict={}
            ddict['event'] = 'FitFinished'
            ddict['data']  = self.specfit.paramlist
            self._emitSignal(ddict)
        return


    def printps(self,**kw):
        text = self.guiparameters.gettext(**kw)
        if __name__ == "__main__":
            self.__printps(text)
        else:
            ddict={}
            ddict['event'] = 'print'
            ddict['text']  = text
            self._emitSignal(ddict)
        return

    def __printps(self, text):
        msg = qt.QMessageBox(self)
        msg.setIcon(qt.QMessageBox.Critical)
        msg.setText("Sorry, Qt4 printing not implemented yet")
        msg.exec_()

    def mcaevent(self,item):
        if int(item):
            self.configure(McaMode=1)
            mode = 1
        else:
            self.configure(McaMode=0)
            mode = 0
        self.__initialparameters()
        ddict={}
        ddict['event'] = 'McaModeChanged'
        ddict['data']  = mode
        self._emitSignal(ddict)
        return

    def weightevent(self,item):
        if int(item):
            self.configure(WeightFlag=1)
        else:
            self.configure(WeightFlag=0)
        return

    def autofwhmevent(self,item):
        if int(item):
            self.configure(AutoFwhm=1)
        else:
            self.configure(AutoFwhm=0)
        return

    def autoscaleevent(self,item):
        if int(item):
            self.configure(AutoScaling=1)
        else:
            self.configure(AutoScaling=0)
        return

    def bkgevent(self,item):
        item=str(item)
        if item in self.specfit.bkgdict.keys():
            self.specfit.setbackground(item)
        else:
            qt.QMessageBox.information(self, "Info", "Function not implemented")
            return
            i=1+self.specfit.bkgdict.keys().index(self.specfit.fitconfig['fitbkg'])
            self.guiconfig.BkgComBox.setCurrentIndex(i)
        self.__initialparameters()
        return

    def funevent(self,item):
        item=str(item)
        if item in self.specfit.theorylist:
            self.specfit.settheory(item)
        else:
            filelist = PyMcaFileDialogs.getFileList(self,
                         message="Select python module with your function(s)",
                         filetypelist=["Python Files (*.py)",
                                       "All Files (*)"],
                         mode="OPEN",
                         single=True,
                         getfilter=False)
                                
            if not len(filelist):           
                functionsfile = ""
            else:
                functionsfile = filelist[0]
            if len(functionsfile):
                try:
                    if self.specfit.importfun(functionsfile):
                        qt.QMessageBox.critical(self, "ERROR",
                                                "Function not imported")
                        return
                    else:
                        #empty the ComboBox
                        n=self.guiconfig.FunComBox.count()
                        while(self.guiconfig.FunComBox.count()>1):
                          self.guiconfig.FunComBox.removeItem(1)
                        #and fill it again
                        for key in self.specfit.theorylist:
                            if QTVERSION < '4.0.0':
                                self.guiconfig.FunComBox.insertItem(str(key))
                            else:
                                self.guiconfig.FunComBox.addItem(str(key))
                except:
                    qt.QMessageBox.critical(self, "ERROR",
                                            "Function not imported")
            i=1+self.specfit.theorylist.index(self.specfit.fitconfig['fittheory'])
            if QTVERSION < '4.0.0':
                self.guiconfig.FunComBox.setCurrentItem(i)
            else:
                self.guiconfig.FunComBox.setCurrentIndex(i)
        self.__initialparameters()
        return

    def __initialparameters(self):
        self.specfit.final_theory=[]
        self.specfit.paramlist=[]
        for pname in self.specfit.bkgdict[self.specfit.fitconfig['fitbkg']][1]:
            self.specfit.final_theory.append(pname)
            self.specfit.paramlist.append({'name':pname,
                                       'estimation':0,
                                       'group':0,
                                       'code':'FREE',
                                       'cons1':0,
                                       'cons2':0,
                                       'fitresult':0.0,
                                       'sigma':0.0,
                                       'xmin':None,
                                       'xmax':None})
        if self.specfit.fitconfig['fittheory'] is not None:
          for pname in self.specfit.theorydict[self.specfit.fitconfig['fittheory']][1]:
            self.specfit.final_theory.append(pname+"1")
            self.specfit.paramlist.append({'name':pname+"1",
                                       'estimation':0,
                                       'group':1,
                                       'code':'FREE',
                                       'cons1':0,
                                       'cons2':0,
                                       'fitresult':0.0,
                                       'sigma':0.0,
                                       'xmin':None,
                                       'xmax':None})
        if self.specfit.fitconfig['McaMode']:
            self.guiparameters.fillfromfit(self.specfit.paramlist,current='Region 1')
            self.guiparameters.removeallviews(keep='Region 1')
        else:
            self.guiparameters.fillfromfit(self.specfit.paramlist,current='Fit')
            self.guiparameters.removeallviews(keep='Fit')
        return

    def fitstatus(self,data):
        if 'chisq' in data:
            if data['chisq'] is None:
                self.guistatus.ChisqLine.setText(" ")
            else:
                chisq=data['chisq']
                self.guistatus.ChisqLine.setText("%6.2f" % chisq)

        if 'status' in data:
            status=data['status']
            self.guistatus.StatusLine.setText(str(status))
        return



    def dismiss(self):
        self.close()
        return

if __name__ == "__main__":
    import numpy
    from PyMca5 import SpecfitFunctions
    a=SpecfitFunctions.SpecfitFunctions()
    x = numpy.arange(2000).astype(numpy.float)
    p1 = numpy.array([1500,100.,30.0])
    p2 = numpy.array([1500,300.,30.0])
    p3 = numpy.array([1500,500.,30.0])
    p4 = numpy.array([1500,700.,30.0])
    p5 = numpy.array([1500,900.,30.0])
    p6 = numpy.array([1500,1100.,30.0])
    p7 = numpy.array([1500,1300.,30.0])
    p8 = numpy.array([1500,1500.,30.0])
    p9 = numpy.array([1500,1700.,30.0])
    p10 = numpy.array([1500,1900.,30.0])
    y = a.gauss(p1,x)+1
    y = y + a.gauss(p2,x)
    y = y + a.gauss(p3,x)
    y = y + a.gauss(p4,x)
    y = y + a.gauss(p5,x)
    #y = y + a.gauss(p6,x)
    #y = y + a.gauss(p7,x)
    #y = y + a.gauss(p8,x)
    #y = y + a.gauss(p9,x)
    #y = y + a.gauss(p10,x)
    y=y/1000.0
    a = qt.QApplication(sys.argv)
    a.lastWindowClosed.connect(a.quit)
    w = SpecfitGui(config=1, status=1, buttons=1)
    w.setdata(x=x,y=y)
    w.show()
    a.exec_()
