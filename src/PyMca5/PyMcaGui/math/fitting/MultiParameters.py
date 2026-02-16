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
import sys
import logging
from PyMca5.PyMcaGui import PyMcaQt as qt
from . import Parameters
QTVERSION = qt.qVersion()
from . import McaTable

_logger = logging.getLogger(__name__)


class ParametersTab(qt.QTabWidget):
    sigMultiParametersSignal = qt.pyqtSignal(object)
    def __init__(self,parent = None, name = "FitParameters"):
        qt.QTabWidget.__init__(self, parent)
        self.setWindowTitle(name)

        #geometry
        #self.resize(570,300)
        #self.setCaption(self.trUtf8(name))

        #initialize the numer of tabs to 1
        #self.TabWidget=QTabWidget(self,"ParametersTab")
        #self.TabWidget.setGeometry(QRect(25,25,450,350))
        #the widgets in the notebook
        self.views={}
        #the names of the widgets (to have them in order)
        self.tabs=[]
        #the widgets/tables themselves
        self.tables={}
        self.mcatable=None
        self.setContentsMargins(10, 10, 10, 10)
        self.setview(name="Region 1")

    def setview(self,name=None,fitparameterslist=None):
        if name is None:
            name = self.current
        if name in self.tables.keys():
            table=self.tables[name]
        else:
            #create the parameters instance
            self.tables[name]=Parameters.Parameters(self)
            table=self.tables[name]
            self.tabs.append(name)
            self.views[name]=table
            #if qVersion() >= '3.0.0':
            #    self.addTab(table,self.trUtf8(name))
            #else:
            #    self.addTab(table,self.tr(name))
            self.addTab(table,str(name))
        if fitparameterslist is not None:
            table.fillfromfit(fitparameterslist)
        self.setCurrentWidget(self.views[name])
        self.current=name

    def renameview(self,oldname=None,newname=None):
        error = 1
        if newname is not None:
            if newname not in self.views.keys():
                if oldname in self.views.keys():
                    parameterlist=self.tables[oldname].fillfitfromtable()
                    self.setview(name=newname,fitparameterslist=parameterlist)
                    self.removeview(oldname)
                    error = 0
        return error

    def fillfromfit(self,fitparameterslist,current=None):
        if current is None:
            current=self.current
        #for view in self.tables.keys():
        #    self.removeview(view)
        self.setview(fitparameterslist=fitparameterslist,name=current)

    def fillfitfromtable(self,*vars,**kw):
        if len(vars) > 0:
            name=vars[0]
        elif 'view' in kw:
            name=kw['view']
        elif 'name' in kw:
            name=kw['name']
        else:
            name=self.current
        if hasattr(self.tables[name],'fillfitfromtable'):
            return self.tables[name].fillfitfromtable()
        else:
            return None

    def removeview(self,*vars,**kw):
        error = 1
        if len(vars) > 0:
            view=vars[0]
        elif 'view' in kw:
            view=kw['view']
        elif 'name' in kw:
            view=kw['name']
        else:
            return error
        if view == self.current:
            return error
        if view in self.views.keys():
                self.tabs.remove(view)
                index = self.indexOf(self.tables[view])
                self.removeTab(index)
                index = self.indexOf(self.views[view])
                self.removeTab(index)
                del self.tables[view]
                del self.views[view]
                error =0
        return error

    def removeallviews(self,keep='Fit'):
        for view in list(self.tables.keys()):
            if view != keep:
                self.removeview(view)

    def fillfrommca(self,mcaresult):
        #for view in self.tables.keys():
        #    self.removeview(view)
        self.removeallviews()
        region = 0
        for result in mcaresult:
             #if result['chisq'] is not None:
                region=region+1
                self.fillfromfit(result['paramlist'],current='Region '+\
                                 "%d" % region)
        name='MCA'
        if name in self.tables:
           table=self.tables[name]
        else:
           self.tables[name]=McaTable.McaTable(self)
           table=self.tables[name]
           self.tabs.append(name)
           self.views[name]=table
           #self.addTab(table,self.trUtf8(name))
           self.addTab(table,str(name))
           table.sigMcaTableSignal.connect(self.__forward)
        table.fillfrommca(mcaresult)
        self.setview(name=name)
        return

    def __forward(self,ddict):
        self.sigMultiParametersSignal.emit(ddict)


    def gettext(self,**kw):
        if "name" in kw:
            name = kw["name"]
        else:
            name = self.current
        table = self.tables[name]
        lemon = ("#%x%x%x" % (255,250,205)).upper()
        _logger.debug("Actual color to ge got")
        hcolor = ("#%x%x%x" % (230,240,249)).upper()
        text=""
        text+=("<nobr>")
        text+=( "<table>")
        text+=( "<tr>")
        ncols = table.columnCount()
        for l in range(ncols):
            text+=('<td align="left" bgcolor="%s"><b>' % hcolor)
            text+=(str(table.horizontalHeaderItem(l).text()))
            text+=("</b></td>")
        text+=("</tr>")
        nrows = table.rowCount()
        for r in range(nrows):
            text+=("<tr>")
            item = table.item(r, 0)
            newtext = ""
            if item is not None:
                newtext = str(item.text())
            if len(newtext):
                color = "white"
                b="<b>"
            else:
                b=""
                color = lemon
            try:
                #MyQTable item has color defined
                cc = table.item(r,0).color
                cc = ("#%x%x%x" % (cc.red(),cc.green(),cc.blue())).upper()
                color = cc
            except Exception:
                pass
            for c in range(ncols):
                item = table.item(r, c)
                newtext = ""
                if item is not None:
                    newtext = str(item.text())
                if len(newtext):
                    finalcolor = color
                else:
                    finalcolor = "white"
                if c<2:
                    text+=('<td align="left" bgcolor="%s">%s' % (finalcolor,b))
                else:
                    text+=('<td align="right" bgcolor="%s">%s' % (finalcolor,b))
                text+=(newtext)
                if len(b):
                    text+=("</td>")
                else:
                    text+=("</b></td>")
            item = table.item(r, 0)
            newtext = ""
            if item is not None:
                newtext = str(item.text())
            if len(newtext):
                text+=("</b>")
            text+=("</tr>")
            #text+=( str(qt.QString("<br>"))
            text+=("\n")
        text+=("</table>")
        text+=("</nobr>")
        return text

    def getHTMLText(self, **kw):
        return self.gettext(**kw)

    if QTVERSION > '4.0.0':
        def getText(self, **kw):
            if "name" in kw:
                name = kw["name"]
            else:
                name = self.current
            table = self.tables[name]
            text=""
            ncols = table.columnCount()
            for l in range(ncols):
                text+=(str(table.horizontalHeaderItem(l).text()))+"\t"
            text+=("\n")
            nrows = table.rowCount()
            for r in range(nrows):
                item = table.item(r, 0)
                newtext = ""
                if item is not None:
                    newtext = str(item.text())+"\t"
                for c in range(ncols):
                    newtext = ""
                    if c != 4:
                        item = table.item(r, c)
                        if item is not None:
                            newtext = str(item.text())
                    else:
                        item = table.cellWidget(r, c)
                        if item is not None:
                            newtext = str(item.currentText())
                    text+=(newtext)+"\t"
                text+=("\n")
            text+=("\n")
            return text

def test():
    a = qt.QApplication(sys.argv)
    a.lastWindowClosed.connect(a.quit)
    w = ParametersTab()
    w.show()
    from PyMca5.PyMca import specfilewrapper as specfile
    from PyMca5.PyMca import Specfit
    from PyMca5 import PyMcaDataDir
    import numpy
    sf=specfile.Specfile(os.path.join(PyMcaDataDir.PYMCA_DATA_DIR,
                                      "XRFSpectrum.mca"))
    scan=sf.select('2.1')
    mcadata=scan.mca(1)
    y=numpy.array(mcadata)
    #x=numpy.arange(len(y))
    x=numpy.arange(len(y))*0.0502883-0.492773
    fit=Specfit.Specfit()
    fit.setdata(x=x,y=y)
    fit.importfun(os.path.join(os.path.dirname(Specfit.__file__),
                                   "SpecfitFunctions.py"))
    fit.settheory('Hypermet')
    fit.configure(Yscaling=1.,
                  WeightFlag=1,
                  PosFwhmFlag=1,
                  HeightAreaFlag=1,
                  FwhmPoints=16,
                  PositionFlag=1,
                  HypermetTails=1)
    fit.setbackground('Linear')
    if 1:
        mcaresult=fit.mcafit(x=x,xmin=x[300],xmax=x[1000])
        w.fillfrommca(mcaresult)
    else:
        fit.estimate()
        fit.startfit()
        w.fillfromfit(fit.paramlist,current='Fit')
        w.removeview(view='Region 1')
    a.exec()

if __name__ == "__main__":
    bench=0
    if bench:
        import pstats
        import profile
        profile.run('test()',"test")
        p=pstats.Stats("test")
        p.strip_dirs().sort_stats(-1).print_stats()
    else:
        test()
