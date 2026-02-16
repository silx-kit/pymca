#/*##########################################################################
# Copyright (C) 2004-2022 European Synchrotron Radiation Facility
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
from PyMca5 import PyMcaDirs
QTVERSION = qt.qVersion()

def getExistingDirectory(parent=None, message=None, mode=None, currentdir=None):
    if message is None:
        message = "Please select a directory"
    if mode is None:
        mode = "OPEN"
    else:
        mode = mode.upper()
    if currentdir is None:
        if mode == "OPEN":
            wdir = PyMcaDirs.inputDir
        else:
            wdir = PyMcaDirs.outputDir
    else:
        wdir = currentdir
    if PyMcaDirs.nativeFileDialogs:
        outdir = qt.safe_str(qt.QFileDialog.getExistingDirectory(parent,
                            message,
                            wdir))
    else:
        outfile = qt.QFileDialog(parent)
        outfile.setWindowTitle("Output Directory Selection")
        outfile.setModal(1)
        outfile.setDirectory(wdir)
        if hasattr(outfile, "Directory"):
            outfile.setFileMode(outfile.Directory)
            if hasattr(outfile, "ShowDirsOnly"):
                outfile.setOption(outfile.ShowDirsOnly)
        elif hasattr(outfile, "DirectoryOnly"):
            outfile.setFileMode(outfile.DirectoryOnly)
        else:
            outfile.setFileMode(qt.QFileDialog.FileMode.Directory)
        ret = outfile.exec()
        if ret:
            outdir = qt.safe_str(outfile.selectedFiles()[0])
        else:
            outdir = ""
            outfile.close()
            del outfile
    if len(outdir):
        if mode == "OPEN":
            PyMcaDirs.inputDir = os.path.dirname(outdir)
            if PyMcaDirs.outputDir is None:
                PyMcaDirs.outputDir = os.path.dirname(outdir)
        else:
            PyMcaDirs.outputDir = os.path.dirname(outdir)
            if PyMcaDirs.inputDir is None:
                PyMcaDirs.inputDir = os.path.dirname(outdir)
    return outdir

def getFileList(parent=None, filetypelist=None, message=None, currentdir=None,
                mode=None, getfilter=None, single=False, currentfilter=None, native=None):
    if filetypelist is None:
        fileTypeList = ['All Files (*)']
    else:
        fileTypeList = filetypelist
    if message is None:
        if single:
            message = "Please select one file"
        else:
            message = "Please select one or more files"
    if mode is None:
        mode = "OPEN"
    else:
        mode = mode.upper()
    if currentdir is None:
        if mode == "OPEN":
            wdir = PyMcaDirs.inputDir
        else:
            wdir = PyMcaDirs.outputDir
    else:
        wdir = currentdir
    if currentfilter is None:
        if mode == "OPEN":
            currentfilter = PyMcaDirs.openFilter
        else:
            currentfilter = PyMcaDirs.saveFilter
        # it can still be None
        if currentfilter is None:
            currentfilter = fileTypeList[0]
    if currentfilter not in fileTypeList:
        currentfilter = fileTypeList[0]
    if native is None:
        nativeFileDialogs = PyMcaDirs.nativeFileDialogs
    else:
        nativeFileDialogs = native
    if getfilter is None:
        getfilter = False
    if getfilter:
        native_possible = True
    else:
        native_possible = True
    filterused = None
    if native_possible and nativeFileDialogs:
        filetypes = currentfilter
        for filetype in fileTypeList:
            if filetype != currentfilter:
                filetypes += ";;" + filetype
        if getfilter:
            if mode == "OPEN":
                if single and hasattr(qt.QFileDialog, "getOpenFileNameAndFilter"):
                    filelist, filterused = qt.QFileDialog.getOpenFileNameAndFilter(parent,
                        message,
                        wdir,
                        filetypes,
                        currentfilter)
                    filelist =[filelist]
                elif single:
                    # PyQt5
                    filelist, filterused = qt.QFileDialog.getOpenFileName(parent,
                        message,
                        wdir,
                        filetypes,
                        currentfilter)
                    filelist =[filelist]
                elif hasattr(qt.QFileDialog, "getOpenFileNamesAndFilter"):
                    filelist, filterused = qt.QFileDialog.getOpenFileNamesAndFilter(parent,
                        message,
                        wdir,
                        filetypes,
                        currentfilter)
                else:
                    # PyQt5
                    filelist, filterused = qt.QFileDialog.getOpenFileNames(parent,
                        message,
                        wdir,
                        filetypes,
                        currentfilter)
                filterused = qt.safe_str(filterused)
            else:
                filelist = qt.QFileDialog.getSaveFileName(parent,
                        message,
                        wdir,
                        filetypes)
                if len(filelist[0]):
                    filterused = qt.safe_str(filelist[1])
                    filelist=[filelist[0]]
                else:
                    filelist = []
        else:
            if mode == "OPEN":
                if single:
                    filelist, filterused = qt.QFileDialog.getOpenFileName(parent,
                                message,
                                wdir,
                                filetypes)
                    filelist = [filelist]
                else:
                    filelist = qt.QFileDialog.getOpenFileNames(parent,
                            message,
                            wdir,
                            filetypes)
            else:
                filelist, filterused = qt.QFileDialog.getSaveFileName(parent,
                            message,
                            wdir,
                            filetypes)
                filelist = qt.safe_str(filelist)
                if len(filelist):
                    filelist = [filelist]
                else:
                    filelist = []
        if not len(filelist):
            if getfilter:
                return [], filterused
            else:
                return []
        elif filterused is None:
            sample  = qt.safe_str(filelist[0])
            for filetype in fileTypeList:
                ftype = filetype.replace("(", "")
                ftype = ftype.replace(")", "")
                extensions = ftype.split()[2:]
                for extension in extensions:
                    if sample.endswith(extension[-3:]):
                        filterused = filetype
                        break
    else:
        fdialog = qt.QFileDialog(parent)
        fdialog.setModal(True)
        fdialog.setWindowTitle(message)
        if hasattr(qt, "QStringList"):
            strlist = qt.QStringList()
        else:
            strlist = []
        strlist.append(currentfilter)
        for filetype in fileTypeList:
            if filetype != currentfilter:
                strlist.append(filetype)
        if hasattr(fdialog, "setFilters"):
            fdialog.setFilters(strlist)
        else:
            fdialog.setNameFilters(strlist)

        if mode == "OPEN":
            fdialog.setFileMode(qt.QFileDialog.FileMode.ExistingFiles)
        else:
            fdialog.setAcceptMode(qt.QFileDialog.AcceptMode.AcceptSave)
            fdialog.setFileMode(qt.QFileDialog.FileMode.AnyFile)

        fdialog.setDirectory(wdir)
        if QTVERSION > '4.3.0':
            history = fdialog.history()
            if len(history) > 6:
                fdialog.setHistory(history[-6:])
        ret = fdialog.exec()
        if ret != qt.QDialog.Accepted:
            fdialog.close()
            del fdialog
            if getfilter:
                return [], filterused
            else:
                return []
        else:
            filelist = fdialog.selectedFiles()
            if single:
                filelist = [filelist[0]]
            filterused = qt.safe_str(fdialog.selectedNameFilter())
            if mode != "OPEN":
                if "." in filterused:
                    extension = filterused.replace(")", "")
                    if "(" in extension:
                        extension = extension.split("(")[-1]
                    extensionList = extension.split()
                    txt = qt.safe_str(filelist[0])
                    for extension in extensionList:
                        extension = extension.split(".")[-1]
                        if extension != "*":
                            txt = qt.safe_str(filelist[0])
                            if txt.endswith(extension):
                                break
                            else:
                                txt = txt+"."+extension
                    filelist[0] = txt
            fdialog.close()
            del fdialog
    filelist = [qt.safe_str(x) for x in filelist]
    if filelist:
        if mode == "OPEN":
            PyMcaDirs.inputDir = os.path.dirname(filelist[0])
            if PyMcaDirs.outputDir is None:
                PyMcaDirs.outputDir = os.path.dirname(filelist[0])
        else:
            PyMcaDirs.outputDir = os.path.dirname(filelist[0])
            if PyMcaDirs.inputDir is None:
                PyMcaDirs.inputDir = os.path.dirname(filelist[0])
    #do not sort file list in order to allow the user other choices
    #filelist.sort()
    if getfilter:
        if mode == "OPEN":
            PyMcaDirs.openFilter = filterused
            if PyMcaDirs.saveFilter is None:
                PyMcaDirs.saveFilter = filterused
        else:
            PyMcaDirs.saveFilter = filterused
            if PyMcaDirs.openFilter is None:
                PyMcaDirs.openFilter = filterused
        return filelist, filterused
    else:
        return filelist

if __name__ == "__main__":
    app = qt.QApplication([])
    fileTypeList = ['PNG Files (*.png *.jpg)', 'TIFF Files (*.tif *.tiff)']
    print(getExistingDirectory())
    PyMcaDirs.nativeFileDialogs = False
    print(getExistingDirectory())
    PyMcaDirs.nativeFileDialogs = True
    print(getFileList(parent=None,
                      filetypelist=fileTypeList,
                      message="Please select a file",
                      mode="SAVE",
                      getfilter=True,
                      single=True))
    PyMcaDirs.nativeFileDialogs = False
    print(getFileList(parent=None,
                      filetypelist=fileTypeList,
                      message="Please select input files",
                      mode="OPEN",
                      getfilter=True,
                      currentfilter='TIFF Files (*.tif *.tiff)',
                      single=False))
    print("Last INPUT directory <%s>" % PyMcaDirs.inputDir)
    print("Last OPEN filter <%s>" % PyMcaDirs.openFilter)
    print("Last OUTPUT directory <%s>" % PyMcaDirs.outputDir)
    print("Last SAVE filter <%s>" % PyMcaDirs.saveFilter)
    #app.exec()
