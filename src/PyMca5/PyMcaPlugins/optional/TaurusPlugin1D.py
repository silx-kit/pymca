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
__author__ = "V.A. Sole & T. Coutinho - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__doc__ = """
    This plugin allows to monitor TANGO attributes in a plot window.

    It needs PyTango and Taurus installed to be operational.

    To use it from withing PyMca, just add this file to your PyMca/plugins folder.

    You can also run it as a stand alone script.
"""
import numpy
from PyMca5.PyMcaCore import Plugin1DBase
from PyMca5.PyMcaGui import PyMcaQt as qt
Qt = qt
from taurus import Attribute
from taurus.core import TaurusEventType
from taurus.qt.qtcore.taurusqlistener import QObjectTaurusListener
from taurus.qt.qtgui.panel import TaurusModelChooser

class TaurusPlugin1D(Plugin1DBase.Plugin1DBase, QObjectTaurusListener):
    def __init__(self, plotWindow, **kw):
        Plugin1DBase.Plugin1DBase.__init__(self, plotWindow, **kw)
        QObjectTaurusListener.__init__(self)
        
        # "standard" way to handle multiple calls
        self.methodDict = {}
        text  = "Show the device selector.\n"
        text += "Make sure your TANGO_HOST\n"
        text += "environment variable is set"
        function = self._showTaurusTree
        info = text
        icon = None
        self.methodDict["Show"] =[function,
                                       info,
                                       icon]
        self._oldModels = []
        self._newModels = []
        self._widget = None

    def handleEvent(self, evt_src, evt_type, evt_value):
        if evt_type not in (TaurusEventType.Change,
                            TaurusEventType.Periodic):
            return
        y = evt_value.value
        x = numpy.arange(y.shape[0])
        self.addCurve(x, y, legend=evt_src.getNormalName())

    def onSelectionChanged(self, models):
        if self._oldModels in [None, []]:
            self._attrDict = {}
            for model in models:
                try:
                    attr = Attribute(model)
                except Exception:
                    # old PyTango versions do not handle unicode
                    attr = Attribute(str(model))
                #force a read -> attr.read()
                attr.addListener(self)
                legend = qt.safe_str(attr.getNormalName())
                self._attrDict[legend] = attr
            self._oldModels = models
        else:
            keptModels = []
            newModels = []
            for model in models:
                if model in self._oldModels:
                    keptModels.append(model)
                else:
                    newModels.append(model)
            for model in self._oldModels:
                if model not in keptModels:
                    attr = Attribute(model)
                    attr.removeListener(self)
                    legend = qt.safe_str(attr.getNormalName())
                    if legend in self._attrDict:
                        del self._attrDict[legend]
                    print("Trying to remove ", legend)
                    self.removeCurve(legend, replot=False)
            for model in newModels:
                attr = Attribute(model)
                # attr.read()
                attr.addListener(self)
                legend = qt.safe_str(attr.getNormalName())
                self._attrDict[legend] = attr
            self._oldModels = keptModels + newModels

    #Methods to be implemented by the plugin
    # I should put this mechanism in the base class ...
    def getMethods(self, plottype=None):
        """
        A list with the NAMES  associated to the callable methods
        that are applicable to the specified plot.

        Plot type can be "SCAN", "MCA", None, ...
        """
        # visualize everywhere, therefore ignore MCA or SCAN
        # if plottype in ["MCA"]:
        #    return []
        names = list(self.methodDict.keys())
        names.sort()
        return names

    def getMethodToolTip(self, name):
        """
        Returns the help associated to the particular method name or None.
        """
        return self.methodDict[name][1]

    def getMethodPixmap(self, name):
        """
        Returns the pixmap associated to the particular method name or None.
        """
        return self.methodDict[name][2]

    def applyMethod(self, name):
        """
        The plugin is asked to apply the method associated to name.
        """
        self.methodDict[name][0]()
        return


    def _showTaurusTree(self):
        if self._widget is None:
            self._widget = TaurusModelChooser()
            #self._adapter = TaurusPyMcaAdapter()
            self._widget.updateModels.connect(self.onSelectionChanged)
        self._widget.show()

MENU_TEXT = "Taurus Device Browser"
def getPlugin1DInstance(plotWindow, **kw):
    ob = TaurusPlugin1D(plotWindow)
    return ob

if __name__ == "__main__":
    app = qt.QApplication([])
    import os
    from PyMca5.PyMcaGui import ScanWindow
    plot = ScanWindow.ScanWindow()
    pluginDir = os.path.dirname(os.path.abspath(__file__))
    SILX = False
    if silx:
        plot.pluginsToolButton.setPluginDirectoryList([pluginDir])
        plot.pluginsToolButton.getPlugins()
    else:
        plot.setPluginDirectoryList([pluginDir])
        plot.getPlugins()
    plot.show()
    app.exec()
