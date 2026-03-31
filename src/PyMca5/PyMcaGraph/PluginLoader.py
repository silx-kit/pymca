#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
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
__doc__ = """

Class to handle loading of plugins according to target method.

On instantiation, this clase imports all the plugins found in the PLUGINS_DIR
directory and stores them into the attributes pluginList and pluginInstanceDict

"""
import os
import sys
import glob
import logging

PLUGINS_DIR = None

_logger = logging.getLogger(__name__)


class PluginLoader(object):
    def __init__(self, method=None, directoryList=None):
        self._pluginDirList = []
        self.pluginList = []
        self.pluginInstanceDict = {}
        self.getPlugins(method=method, directoryList=directoryList)

    def setPluginDirectoryList(self, dirlist):
        """
        :param dirlist: Set directories to search for plugins
        :type dirlist: list
        """
        for directory in dirlist:
            if not os.path.exists(directory):
                raise IOError("Directory:\n%s\ndoes not exist." % directory)
        self._pluginDirList = dirlist

    def getPluginDirectoryList(self):
        """
        :return dirlist: List of directories for searching plugins
        """
        return self._pluginDirList

    def getPlugins(self, method=None, directoryList=None, exceptions=False):
        """
        Import or reloads all the available plugins with the target method

        :param method: The method to be searched for.
        :type method: string, default "getPlugin1DInstance"
        :param directoryList: The list of directories for the search.
        :type directoryList: list or None (default).
        :param exceptions: If True, return the list of error messages
        :type exceptions: boolean (default False)
        :return: The number of plugins loaded. If exceptions is True, also the
                 text with the error encountered.
        """
        if method is None:
            method = 'getPlugin1DInstance'
        targetMethod = method
        if directoryList in [None, [] ]:
            directoryList = self._pluginDirList
            if directoryList in [None, []]:
                directoryList = [PLUGINS_DIR]
        _logger.debug("method: %s", targetMethod)
        _logger.debug("directoryList: %s", directoryList)
        exceptionMessage = ""
        self._pluginDirList = directoryList
        self.pluginList = []
        for directory in self._pluginDirList:
            if directory is None:
                continue
            if not os.path.exists(directory):
                raise IOError("Directory:\n%s\ndoes not exist." % directory)

            fileList = glob.glob(os.path.join(directory, "*.py"))
            # prevent unnecessary imports
            moduleList = []
            for fname in fileList:
                # in Python 3, rb implies bytes and not strings
                f = open(fname, 'r')
                lines = f.readlines()
                f.close()
                f = None
                for line in lines:
                    if line.startswith("def"):
                        if line.split(" ")[1].startswith(targetMethod):
                            moduleList.append(fname)
                            break
            for module in moduleList:
                try:
                    pluginName = os.path.basename(module)[:-3]
                    _logger.debug("pluginName %s", pluginName)
                    plugin = pluginName
                    if directory not in sys.path:
                        sys.path.insert(0, directory)
                    if pluginName in self.pluginList:
                        idx = self.pluginList.index(pluginName)
                        del self.pluginList[idx]
                    if plugin in self.pluginInstanceDict.keys():
                        del self.pluginInstanceDict[plugin]
                    if plugin in sys.modules:
                        if hasattr(sys.modules[plugin], targetMethod):
                            import importlib
                            importlib.reload(sys.modules[plugin])
                    else:
                        __import__(plugin)
                    if hasattr(sys.modules[plugin], targetMethod):
                        theCall = getattr(sys.modules[plugin], targetMethod)
                        self.pluginInstanceDict[plugin] = theCall(self)
                        self.pluginList.append(plugin)
                except Exception:
                    exceptionMessage += \
                        "Problem importing module %s\n" % plugin
                    exceptionMessage += "%s\n" % sys.exc_info()[0]
                    exceptionMessage += "%s\n" % sys.exc_info()[1]
                    exceptionMessage += "%s\n" % sys.exc_info()[2]

        if len(exceptionMessage) and _logger.getEffectiveLevel() == logging.DEBUG:
            raise IOError(exceptionMessage)
        if exceptions:
            return len(self.pluginList), exceptionMessage
        else:
            return len(self.pluginList)

def main(targetMethod, directoryList):
    loader = PluginLoader()
    n = loader.getPlugins(targetMethod, directoryList)
    print("Loaded %d plugins" % n)
    for m in loader.pluginList:
        print("Module %s" % m)
        module = sys.modules[m]
        if hasattr(module, 'MENU_TEXT'):
            text = module.MENU_TEXT
        else:
            text = os.path.basename(module.__file__)
            if text.endswith('.pyc'):
                text = text[:-4]
            elif text.endswith('.py'):
                text = text[:-3]
        print("\tMENU TEXT: %s" % text)
        methods = loader.pluginInstanceDict[m].getMethods()
        if not len(methods):
            continue
        for method in methods:
            print("\t\t %s" % method)

if __name__ == "__main__":
    if len(sys.argv) > 2:
        targetMethod  = sys.argv[1]
        directoryList = sys.argv[2:len(sys.argv)]
    elif len(sys.argv) > 1:
        targetMethod = None
        directoryList = sys.argv[1:len(sys.argv)]
    else:
        print("Usage: python PluginLoader.py [targetMethod] directory")
    main(targetMethod, directoryList)
