#/*##########################################################################
# Copyright (C) 2004-2025 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__version__ = '5.9.5.dev12'

import os
import sys

from PyMca5.PyMcaDataDir import PYMCA_DATA_DIR
try:
    from fisx.DataDir import FISX_DATA_DIR
except ImportError:
    FISX_DATA_DIR = None

import logging as _logging
_logging.getLogger(__name__).addHandler(_logging.NullHandler())
_logger = _logging.getLogger(__name__)


if sys.platform.startswith("win"):
    import ctypes
    from ctypes.wintypes import MAX_PATH

def version():
    return __version__

def getDefaultSettingsDirectory():
    """
    Return the path to the directory containing the default settings file,
    user plugins and user fit functions.

    This function tries to create the directory if not already created.
    """
    if sys.platform == 'win32':
        # recipe based on: http://bugs.python.org/issue1763#msg62242
        dll = ctypes.windll.shell32
        buf = ctypes.create_unicode_buffer(MAX_PATH + 1)
        if dll.SHGetSpecialFolderPathW(None, buf, 0x0005, False):
            directory = buf.value
        else:
            # the above should have worked
            home = os.getenv('USERPROFILE')
            try:
                directory = os.path.join(home, "My Documents")
            except Exception:
                home = '\\'
                directory = '\\'
        if os.path.isdir('%s' % directory):
            directory = os.path.join(directory, "PyMca")
        else:
            directory = os.path.join(home, "PyMca")
    else:
        home = os.getenv('HOME')
        directory = os.path.join(home, ".pymca")
        if not os.path.isdir('%s' % directory):
            # if legacy directory exists, possibly containing user plugins,
            # we should keep using it
            legacy_directory = os.path.join(home, "PyMca")
            if os.path.exists(os.path.join(legacy_directory, "plugins")):
                directory = legacy_directory

    if not os.path.exists('%s' % directory):
        os.mkdir('%s' % directory)
    return directory

def getDefaultSettingsFile():
    """
    Return the path to the default settings file (PyMca.ini).

    The file itself may not exist, but this function tries to create
    the containing directory if not already created.
    """
    filename = "PyMca.ini"
    return os.path.join(getDefaultSettingsDirectory(),
                        filename)

def getDefaultUserPluginsDirectory():
    """
    Return the default directory to look for user defined plugins.

    The directory will be created if not existing. In case of error it returns None.
    """
    try:
        settingsDir = getDefaultSettingsDirectory()
        if os.path.exists(settingsDir):
            userPluginDir = os.path.join(settingsDir, "plugins")
            if not os.path.exists(userPluginDir):
                os.mkdir(userPluginDir)
            return userPluginDir
        else:
            return None
    except Exception:
        _logger.info("WARNING: Cannot initialize plugins directory")
        return None

def getDefaultUserFitFunctionsDirectory():
    """
    Return the default directory to look for user defined fit functions.

    The directory will be created if not existing. In case of error it returns None.
    """
    try:
        settingsDir = os.path.dirname(getDefaultSettingsFile())
        if os.path.exists(settingsDir):
            fitFunctionsDir = os.path.join(settingsDir, "fit")
            if not os.path.exists(fitFunctionsDir):
                os.mkdir(fitFunctionsDir)
            return fitFunctionsDir
        else:
            return None
    except Exception:
        print("WARNING: Cannot initialize fit functions directory")
        return None

def getUserDataFile(fileName, directory=""):
    """
    Look for an alternative to the given filename in the default user data directory
    """
    userDataDir = None
    try:
        settingsDir = getDefaultSettingsDirectory()
        if os.path.exists(settingsDir):
            userDataDir = os.path.join(settingsDir, "data")
            if not os.path.exists(userDataDir):
                os.mkdir(userDataDir)
    except Exception:
        _logger.info("WARNING: cannot initialize user data directory")
        
    if userDataDir is None:
        return fileName

    baseName = os.path.basename(fileName)
    if len(directory):
        userDataFile = os.path.join(userDataDir, directory, baseName)
    else:
        userDataFile = os.path.join(userDataDir, baseName)
    if os.path.exists(userDataFile):
        _logger.debug("Using user data file: %s", userDataFile)
        return userDataFile
    else:
        _logger.debug("Using data file: %s", fileName)
        return fileName

def getDataFile(fileName, directory=None):
    """
    Look for the provided file name in directories following the priority:

    0 - The provided file
    1 - User data directory (~/.pymca/PyMcaData)
    2 - PyMca data directory (PyMcaDataDir.PYMCA_DATA_DIR)
    3 - fisx data directory (fisx.DataDir.FISX_DATA_DIR)
    """

    # return the input file name if exists
    if os.path.exists(fileName):
        _logger.debug("Filename as supplied <%s>", fileName)
        return fileName

    # the list of sub-directories where to look for the file
    if directory is None:
        directoryList = [""]
    else:
        directoryList = [directory, ""]

    # user
    for subdirectory in directoryList:
        newFileName = getUserDataFile(fileName, directory=subdirectory)
        if os.path.exists(newFileName):
            _logger.debug("Filename from user <%s>", newFileName)
            return newFileName

    # PyMca
    for subdirectory in directoryList:
        newFileName = os.path.join(PYMCA_DATA_DIR,
                                   subdirectory,
                                   os.path.basename(fileName))
        if os.path.exists(newFileName):
            _logger.debug("Filename from PyMca Data Directory <%s>", newFileName)
            return newFileName

    # fisx
    if FISX_DATA_DIR is not None:
        for subdirectory in directoryList:
            newFileName = os.path.join(FISX_DATA_DIR,
                                       subdirectory,
                                       os.path.basename(fileName))
            if os.path.exists(newFileName):
                _logger.debug("Filename from fisx Data Directory <%s>",
                              newFileName)
                return newFileName

    # file not found
    txt = "File not found:  <%s>" % fileName
    if FISX_DATA_DIR is None:
        txt += " Please install fisx module (command 'pip install fisx [--user]')."
    raise IOError(txt)

# workaround matplotlib MPLCONFIGDIR issues under windows
if sys.platform.startswith("win"):
    try:
        #try to avoid matplotlib config dir problem under windows
        if os.getenv("MPLCONFIGDIR") is None:
            os.environ['MPLCONFIGDIR'] = getDefaultSettingsDirectory()
    except Exception:
        _logger.info("WARNING: Could not set MPLCONFIGDIR. %s", sys.exc_info()[1])

# mandatory modules for backwards compatibility
from .PyMcaCore import Plugin1DBase, StackPluginBase, PyMcaDirs, DataObject

#all the rest can be imported using from PyMca5.PyMca import ...
from . import PyMca
