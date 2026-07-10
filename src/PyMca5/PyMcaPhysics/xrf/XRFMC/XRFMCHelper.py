#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
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
import tempfile
import subprocess
import time
import shutil
from PyMca5.PyMcaIO import ConfigDict
from . import XMSOParser

getXMSOFileFluorescenceInformation =\
                        XMSOParser.getXMSOFileFluorescenceInformation

XMIMSIM_PYMCA = None
if sys.platform == "win32":
    try:
        # try to get the installation directory from the registry
        import winreg
        HKLM = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        try:
            # 32 bit
            softwareKey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                         r"Software\XMI-MSIM")
        except Exception:
            try:
                # 64 bit
                softwareKey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                             r"Software\Wow6432Node\XMI-MSIM")
            except Exception:
                # XMI-MSIM not installed ...
                softwareKey = None
        if softwareKey is not None:
            subKeyName = "InstallationDirectory"
            value = winreg.QueryValueEx(softwareKey, subKeyName)
            pathToExecutable = os.path.join(value[0], "bin", "xmimsim-pymca.exe")
            if not os.path.exists(pathToExecutable):
                pathToExecutable = None
            XMIMSIM_PYMCA = pathToExecutable
    except Exception:
        # this cannot afford failing
        pass
else:
    try:
        testDirectories = ["/Applications", "/usr/local/bin", "/usr/bin", os.getcwd()]
        #look in the user PATH
        path = os.getenv('PATH')
        if path is not None:
            testDirectories += path.split(":")
        scriptName = "xmimsim-pymca"
        if sys.platform == "darwin":
            scriptName = os.path.join("XMI-MSIM.app",
                                      "Contents",
                                      "Resources",
                                       scriptName)
        for dirName in testDirectories:
            pathToExecutable = os.path.join(dirName, scriptName)
            if not os.path.exists(pathToExecutable):
                pathToExecutable = None
            else:
                break
        XMIMSIM_PYMCA = pathToExecutable
    except Exception:
        # this cannot afford failing
        pass

def getScriptFile(pathToExecutable=None, args=None, name=None):
    if pathToExecutable is None:
        pathToExecutable = XMIMSIM_PYMCA
    if pathToExecutable is None:
        raise ValueError("Path to xmimsim-pymca needed")
    if not os.path.exists(pathToExecutable):
        raise IOError("xmimsim-pymca executable does not exist")
    if args is None:
        args = []
    executable = os.path.basename(pathToExecutable)
    if not executable.startswith("xmimsim-pymca"):
        if sys.platform == "win32":
            raise ValueError("Path to xmimsim-pymca.exe needed")
        else:
            raise ValueError("Path to xmimsim-pymca needed")
    xmimsim_directory = os.path.dirname(pathToExecutable)
    if os.path.basename(xmimsim_directory).lower() == "bin":
        xmimsim_directory = os.path.dirname(xmimsim_directory)

    if sys.platform == "win32":
        binDir = os.path.join(xmimsim_directory, "bin")
        libDir = os.path.join(xmimsim_directory, "lib")
        gtkDir = os.path.join(xmimsim_directory, "GTK")
        if os.path.exists(gtkDir+"2"):
            gtkDir += "2"
        path = os.getenv("PATH")
        txt = "echo off\n"
        txt += "set PATH=%s;%s;%s;%s\n" % (binDir, libDir, gtkDir, os.getenv("PATH"))
        txt += "%s " % executable
        if len(args):
            for arg in args:
                txt += arg + " ";
            txt += "\n"
        else:
            txt += "%*"
        if name is None:
            handle, fullPath = tempfile.mkstemp(suffix=".bat", prefix="pymca", text=False)
            os.write(handle, txt)
            os.close(handle)
        else:
            fullPath = name
            if not fullPath.endswith(".bat"):
                fullPath = name + ".bat"
            f = open(fullPath, "w", newline='')
            f.write(txt)
            f.close()
    elif sys.platform == "darwin":
        #the bundle has everything needed
        txt = "#!/bin/bash\n"
        #this line is critical in order to avoid interference by the bundled PyMca
        txt += 'DYLD_LIBRARY_PATH=""\n'
        txt += "%s " % pathToExecutable
        if len(args):
            for arg in args:
                txt += arg + " ";
            txt += "\n"
        else:
            txt += "$*"
        if name is None:
            handle, fullPath = tempfile.mkstemp(suffix=".sh", prefix="pymca", text=False)
            os.write(handle, txt)
            os.close(handle)
        else:
            fullPath = name
            if not fullPath.endswith(".sh"):
                fullPath = name + ".sh"
            f = open(fullPath, "w")
            f.write(txt)
            f.close()
        os.system("chmod +x %s"  % fullPath)
    else:
        binDir = xmimsim_directory
        libDir = os.path.join(xmimsim_directory, "lib")
        path = os.getenv("PATH")
        txt = "#!/bin/bash\n"
        txt += "export PATH=%s:%s:%s\n" % (binDir, libDir, os.getenv("PATH"))
        txt += "%s " % executable
        if len(args):
            for arg in args:
                txt += arg + " ";
            txt += "\n"
        else:
            txt += "$*"
        if name is None:
            handle, fullPath = tempfile.mkstemp(suffix=".sh", prefix="pymca", text=False)
            os.write(handle, txt)
            os.close(handle)
        else:
            fullPath = name
            if not fullPath.endswith(".sh"):
                fullPath = name + ".sh"
            f = open(fullPath, "w")
            f.write(txt)
            f.close()
        os.system("chmod +x %s"  % fullPath)
    return fullPath

def getOutputFileNames(fitFile, outputDir=None):
    if outputDir is None:
        outputDir = os.path.dirname(fitFile)
    ddict = {}
    newFile = os.path.join(outputDir, os.path.basename(fitFile))
    if newFile.lower().endswith(".fit"):
        rootName = newFile[:-4]
    elif newFile.lower().endswith(".cfg"):
        rootName = newFile[:-4]
    else:
        rootName = newFile
    scriptName = rootName + "_script"
    csvName = rootName + ".csv"
    speName = rootName + ".spe"
    xmsoName = rootName + ".xmso"
    if sys.platform == 'win32':
        scriptName = scriptName + ".bat"
    fitName = rootName + ".fit"
    ddict={}
    ddict['fit'] = rootName + ".fit"
    ddict['script'] = scriptName
    ddict['csv'] = csvName
    ddict['spe'] = speName
    ddict['xmso'] = xmsoName
    return ddict

def getXRFMCCorrectionFactors(fitConfiguration, xmimsim_pymca=None, verbose=False):
    outputDir=tempfile.mkdtemp(prefix="pymcaTmp")
    if 'result' in fitConfiguration:
        # we have to create a .fit file with the information
        ddict = ConfigDict.ConfigDict()
        ddict.update(fitConfiguration)
    else:
        # for the time being we have to build a "fit-like" file with the information
        import numpy
        from PyMca5.PyMca import ClassMcaTheory
        fitConfiguration['fit']['linearfitflag']=1
        fitConfiguration['fit']['stripflag']=0
        fitConfiguration['fit']['stripiterations']=0
        xmin = fitConfiguration['fit']['xmin']
        xmax = fitConfiguration['fit']['xmax']
        #xdata = numpy.arange(xmin, xmax + 1) * 1.0
        xdata = numpy.arange(0, xmax + 1) * 1.0
        ydata = 0.0 + 0.1 * xdata
        mcaFit = ClassMcaTheory.McaTheory()
        mcaFit.configure(fitConfiguration)
        #a dummy time
        dummyTime = 1.0
        if "concentrations" in fitConfiguration:
            dummyTime = fitConfiguration["concentrations"].get("time",
                                                          dummyTime)
        mcaFit.setData(x=xdata, y=ydata,
                       xmin=xmin, xmax=xmax, time=dummyTime)
        mcaFit.estimate()
        fitresult, result = mcaFit.startfit(digest=1)
        ddict=ConfigDict.ConfigDict()
        ddict['result'] = result
        ddict['xrfmc'] = fitConfiguration['xrfmc']
    handle, fitFile = tempfile.mkstemp(suffix=".fit", prefix="pymca",
                                       dir=outputDir, text=False)
    os.close(handle)
    ddict.write(fitFile)
    ddict = None

    # we have the input file ready
    fileNamesDict = getOutputFileNames(fitFile, outputDir)
    scriptFile = getScriptFile(pathToExecutable=xmimsim_pymca,
                                    name=fileNamesDict['script'])
    xmsoName = fileNamesDict['xmso']
    # basic parameters
    args = [scriptFile,
           "--enable-single-run",
           #"--set-threads=2",
           #"--verbose",
           #"--spe-file=%s" % speName,
           #"--csv-file=%s" % csvName,
           #"--enable-roi-normalization",
           #"--disable-roi-normalization", #default
           #"--enable-pile-up"
           #"--disable-pile-up" #default
           #"--enable-poisson",
           #"--disable-poisson", #default no noise
           #"--set-threads=2", #overwrite default maximum
           fitFile,
           xmsoName]
    if verbose:
        args.insert(2, "--verbose")
    process = subprocess.Popen(args,
                               bufsize=0,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               universal_newlines=True)
    while process.poll() is None:
        # process did not finish yet
        time.sleep(0.1)
        line = process.stdout.readline()
        if verbose:
            if len(line) > 1:
                print("OUTPUT = <%s>" % line[:-1])
    returnCode = process.returncode
    line = process.stdout.readline()
    while len(line) > 1:
        if verbose:
            print("OUTPUT = %s" % line[:-1])
        line = process.stdout.readline()
    if returnCode:
        text = ""
        line = process.stderr.readline()
        while len(line) > 1:
            text += line
            if verbose:
                print("ERROR = %s" % line[:-1])
            line = process.stderr.readline()
            removeDirectory(outputDir)
        raise IOError("Program terminated with error code %d:\n%s" % (returnCode, text))
    corrections = getXMSOFileFluorescenceInformation(xmsoName)
    xmsoName = None
    removeDirectory(outputDir)
    return corrections

def removeDirectory(dirName):
    if os.path.exists(dirName):
        if os.path.isdir(dirName):
            shutil.rmtree(dirName)

def start(fitFile, outputDir, xmimsim_pymca, parameters=None, verbose=True):
    args = getBasicSubprocessCommand(fitFile, outputDir, xmimsim_pymca)
    if parameters is None:
        parameters = ["--enable-single-run",
                      "--set-threads=2"]
    i = 0
    for parameter in parameters:
        i += 1
        args.insert(1, parameter)
    process = subprocess.Popen(args,
                               bufsize=0,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               universal_newlines=True)
    while process.poll() is None:
        # process did not finish yet
        time.sleep(0.1)
        line = process.stdout.readline()
        if verbose:
            if len(line) > 1:
                print("OUTPUT = <%s>" % line[:-1])
    returnCode = process.returncode
    line = process.stdout.readline()
    while len(line) > 1:
        if verbose:
            print("OUTPUT = %s" % line[:-1])
        line = process.stdout.readline()
    if returnCode:
        text = ""
        line = process.stderr.readline()
        while len(line) > 1:
            text += line
            if verbose:
                print("ERROR = %s" % line[:-1])
            line = process.stderr.readline()
        raise IOError("Program terminated with error code %d:\n%s" % (returnCode, text))

def getBasicSubprocessCommand(fitFile, outputDir=None, xmimsim_pymca=None):
     ddict = getOutputFileNames(fitFile, outputDir)
     scriptFile = getScriptFile(pathToExecutable=xmimsim_pymca,
                                    name=ddict['script'])
     if ddict['fit'] != fitFile:
         if outputDir is None:
             # this should never happen
            raise ValueError("Inconsistent internal behaviour!")
         # recreate input in output directory
         new = ConfigDict.ConfigDict()
         new.read(fitFile)
         if os.path.exists(ddict['fit']):
             os.remove(ddict['fit'])
         new.write(ddict['fit'])
         new = None
     speName = ddict['spe']
     csvName = ddict['csv']
     newFitFile = ddict['fit']
     xmsoName = ddict['xmsoName']
     args = [scriptFile,
            #"--enable-single-run",
            "--verbose",
            "--spe-file=%s" % speName,
            "--csv-file=%s" % csvName,
            #"--enable-roi-normalization",
            #"--disable-roi-normalization", #default
            #"--enable-pile-up"
            #"--disable-pile-up" #default
            #"--enable-poisson",
            #"--disable-poisson", #default no noise
            #"--set-threads=2", #overwrite default maximum
            newFitFile,
            xmsoName]
     return args


def test(filename):
    fitConfig = ConfigDict.ConfigDict()
    fitConfig.read(filename)
    ddict = getXRFMCCorrectionFactors(fitConfig, verbose=True)
    fitConfig = None
    for element in ddict:
        for line in ddict[element]:
            if line == "z":
                #atomic number
                continue
            if line in ['K', 'Ka', 'Kb', 'L', 'L1', 'L2', 'L3', 'M']:
                correction1 = ddict[element][line]['correction_factor'][1]
                correctionn = ddict[element][line]['correction_factor'][-1]
                print("Element %s Line %s Correction 2 = %f Correction n = %f" %\
                            (element, line,correction1, correctionn))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test(sys.argv[1])
    else:
        print("Usage:")
        print("python XRFMCHelper.py path_to_cfg_or_fit_file")

