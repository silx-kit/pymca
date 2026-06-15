#!/usr/bin/env python
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

from PyMca5.PyMcaGui import PyMcaAppInit

if __name__== '__main__':
    PyMcaAppInit.init_before_app_import()

import sys
import os
import copy
import traceback
import logging

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5 import PyMcaDirs
from PyMca5 import DataObject
from PyMca5.PyMcaGui.io import PyMcaFileDialogs
from PyMca5.PyMcaIO import MRCMap
from PyMca5.PyMcaIO import OmnicMap
from PyMca5.PyMcaIO import OpusDPTMap
from PyMca5.PyMcaIO import LuciaMap
from PyMca5.PyMcaIO import SupaVisioMap
from PyMca5.PyMcaIO import AifiraMap
from PyMca5.PyMcaIO import TextImageStack
from PyMca5.PyMcaIO import TiffStack
from PyMca5.PyMcaIO import RTXMap
from PyMca5.PyMcaIO import LispixMap
from PyMca5.PyMcaIO import RenishawMap
from PyMca5.PyMcaIO import OmdaqLmf
from PyMca5.PyMcaIO import JcampOpusStack
from PyMca5.PyMcaIO import FsmMap
from PyMca5.PyMcaIO import LabSpec6TxtMap
from PyMca5.PyMcaIO import BrukerBCF
from PyMca5.PyMcaMisc import CliUtils


from .QStack import QStack, QSpecFileStack
try:
    from PyMca5.PyMcaGui.pymca import QHDF5Stack1D
    import h5py
    HDF5 = True
except ImportError:
    HDF5 = False
    pass

QTVERSION = qt.qVersion()
_logger = logging.getLogger(__name__)


class StackSelector(object):
    def __init__(self, parent=None):
        self.parent = parent

    def getStack(self, filelist=None, imagestack=None):
        if filelist in [None, []]:
            filelist, filefilter = self._getStackOfFiles(getfilter=True)
        else:
            filefilter = ""

        if not len(filelist):
            return None

        if filefilter in ["", "All Files (*)"]:
            if HDF5:
                if h5py.is_hdf5(filelist[0]):
                    filefilter = "HDF5"

        fileindex = 0
        begin = None
        end = None
        aifirafile = False
        if len(filelist):
            PyMcaDirs.inputDir = os.path.dirname(filelist[0])
            #if we are dealing with HDF5, no more tests needed
            if not filefilter.upper().startswith('HDF5'):
                f = open(filelist[0], 'rb')
                #read 10 characters
                try:
                    line = str(f.read(10).decode())
                except UnicodeDecodeError:
                    #give a dummy value
                    line = "          "
                f.close()
            omnicfile = False
            if filefilter.upper().startswith('HDF5'):
                stack = QHDF5Stack1D.QHDF5Stack1D(filelist)
                omnicfile = True
            elif filefilter.upper().startswith('OPUS-DPT'):
                stack = OpusDPTMap.OpusDPTMap(filelist[0])
                omnicfile = True
            elif filefilter.upper().startswith("AIFIRA"):
                stack = AifiraMap.AifiraMap(filelist[0])
                omnicfile = True
                aifirafile = True
            elif filefilter.upper().startswith("SUPAVISIO"):
                stack = SupaVisioMap.SupaVisioMap(filelist[0])
                omnicfile = True
            elif filefilter.upper().startswith("TEXTIMAGE"):
                imagestack = True
                fileindex = 0
                stack = TextImageStack.TextImageStack(imagestack=True)
            elif filefilter.upper().startswith("LABSPEC6") and\
                 (filelist[0].upper().endswith("TIF") or\
                  filelist[0].upper().endswith("TIFF")):
                stack = TiffStack.TiffStack(imagestack=True)
                stack.loadFileList(filelist[0])
                stack.info["FileIndex"] = 0
                stack.info["McaIndex"] = 2
                omnicfile = True
            elif filefilter.upper().startswith("LABSPEC6") and\
                 filelist[0].upper().endswith("TXT"):
                stack = LabSpec6TxtMap.LabSpec6TxtMap(filelist[0])
                omnicfile = True
            elif filefilter.upper().startswith("IMAGE") and\
                 (filelist[0].upper().endswith("TIF") or\
                  filelist[0].upper().endswith("TIFF")):
                stack = TiffStack.TiffStack(imagestack=True)
            elif filefilter.upper().startswith("RENISHAW"):
                stack = RenishawMap.RenishawMap(filelist[0])
                omnicfile = True
            elif filefilter.upper().startswith("PerkinElmer-FSM"):
                stack = FsmMap.FsmMap(filelist[0])
                omnicfile = True
            elif filefilter == "" and\
                 (filelist[0].upper().endswith("TIF") or\
                  filelist[0].upper().endswith("TIFF")):
                stack = TiffStack.TiffStack(imagestack=True)
            elif filefilter.upper().startswith("IMAGE"):
                if imagestack is None:
                    imagestack = True
                fileindex = 0
                stack = QStack(imagestack=imagestack)
            elif line[0] == "{":
                if filelist[0].upper().endswith("RAW"):
                    if imagestack is None:
                        imagestack=True
                stack = QStack(imagestack=imagestack)
            elif line[0:2] in ["II", "MM"]:
                if imagestack is None:
                    imagestack = True
                stack = QStack(imagestack=imagestack)
            elif line.startswith('Spectral'):
                stack = OmnicMap.OmnicMap(filelist[0])
                omnicfile = True
            elif line.startswith('#\tDate'):
                stack = LuciaMap.LuciaMap(filelist[0])
                omnicfile = True
            elif filelist[0].upper().endswith("RAW.GZ")or\
                 filelist[0].upper().endswith("EDF.GZ")or\
                 filelist[0].upper().endswith("CCD.GZ")or\
                 filelist[0].upper().endswith("RAW.BZ2")or\
                 filelist[0].upper().endswith("EDF.BZ2")or\
                 filelist[0].upper().endswith("CCD.BZ2")or\
                 filelist[0].upper().endswith(".CBF"):
                if imagestack is None:
                    imagestack = True
                stack = QStack(imagestack=imagestack)
            elif filelist[0].upper().endswith(".RTX"):
                stack = RTXMap.RTXMap(filelist[0])
                omnicfile = True
            elif filelist[0][-4:].upper() in ["PIGE", "PIGE"]:
                stack = SupaVisioMap.SupaVisioMap(filelist[0])
                omnicfile = True
            elif filelist[0][-3:].upper() in ["RBS"]:
                stack = SupaVisioMap.SupaVisioMap(filelist[0])
                omnicfile = True
            elif filelist[0][-3:].upper() in ["SPE"] and\
                 (line[0] not in ['$', '#']):
                #Roper Scientific format
                #handle it as MarCCD stack
                stack = QStack(imagestack=True)
            elif MRCMap.isMRCFile(filelist[0]):
                stack = MRCMap.MRCMap(filelist[0])
                omnicfile = True
                imagestack = True
            elif LispixMap.isLispixMapFile(filelist[0]):
                stack = LispixMap.LispixMap(filelist[0])
                omnicfile = True
            elif RenishawMap.isRenishawMapFile(filelist[0]):
                # This is dangerous. Any .txt file with four
                # columns would be accepted as a Renishaw Map
                # by other hand, I do not know how to handle
                # that case as a stack.
                _logger.info("RenishawMap")
                stack = RenishawMap.RenishawMap(filelist[0])
                omnicfile = True
            elif OmdaqLmf.isOmdaqLmf(filelist[0]):
                _logger.info("OmdaqLmf")
                stack = OmdaqLmf.OmdaqLmf(filelist[0])
                omnicfile = True
            elif FsmMap.isFsmFile(filelist[0]):
                _logger.info("FsmMap")
                stack = FsmMap.FsmMap(filelist[0])
                omnicfile = True
            elif JcampOpusStack.isJcampOpusStackFile(filelist[0]):
                _logger.info("JcampOpusStack")
                stack = JcampOpusStack.JcampOpusStack(filelist[0])
                omnicfile = True
            elif BrukerBCF.isBrukerBCFFile(filelist[0]):
                _logger.info("Bruker bcf")
                stack = BrukerBCF.BrukerBCF(filelist[0])
                omnicfile = True
            else:
                stack = QSpecFileStack()

        if len(filelist) == 1:
            if not omnicfile:
                try:
                    stack.loadIndexedStack(filelist[0], begin, end,
                                           fileindex=fileindex)
                except Exception:
                    msg = qt.QMessageBox()
                    msg.setIcon(qt.QMessageBox.Critical)
                    msg.setInformativeText("%s" % sys.exc_info()[1])
                    msg.setDetailedText(traceback.format_exc())
                    msg.exec()
                    if _logger.getEffectiveLevel() == logging.DEBUG:
                        raise
        elif len(filelist):
            if not omnicfile:
                try:
                    stack.loadFileList(filelist, fileindex=fileindex)
                except Exception:
                    msg = qt.QMessageBox()
                    msg.setIcon(qt.QMessageBox.Critical)
                    msg.setText("%s" % sys.exc_info()[1])
                    msg.exec()
                    if _logger.getEffectiveLevel() == logging.DEBUG:
                        raise
        if aifirafile:
            primaryStack = DataObject.DataObject()
            primaryStack.info = copy.deepcopy(stack.info)
            primaryStack.data = stack.data[:, :, 0:1024]
            primaryStack.info['Dim_2'] = int(primaryStack.info['Dim_2'] / 2)

            secondaryStack = DataObject.DataObject()
            secondaryStack.info = copy.deepcopy(stack.info)
            secondaryStack.data = stack.data[:, :, 1024:]
            secondaryStack.info['Dim_2'] = int(secondaryStack.info['Dim_2'] / 2)
            return [primaryStack, secondaryStack]
        else:
            return stack

    def getStackFromPattern(self, filepattern, begin, end, increment=None,
                            imagestack=None, fileindex=0):
        #get the first filename
        filename = filepattern % tuple(begin)
        if not os.path.exists(filename):
            raise IOError("Filename %s does not exist." % filename)
        #get the file list
        args = self.getFileListFromPattern(filepattern, begin, end,
                                           increment=increment)

        #get the file type
        f = open(args[0], 'rb')
        #read 10 characters
        line = f.read(10)
        f.close()
        if hasattr(line, "decode"):
            # convert to string ignoring errors
            line = line.decode("utf-8", "ignore")

        specfile = False
        marCCD = False
        if line.startswith("II") or line.startswith("MM"):
            marCCD = True
        if line[0] == "\n":
            line = line[1:]
        if line.startswith("{") or marCCD:
            if imagestack is None:
                if marCCD:
                    imagestack = True
            if imagestack:
                #prevent any modification
                fileindex = 0
            if filepattern is not None:
                #this dows not seem to put any trouble
                #(because of no redimensioning attempt)
                if False and (len(begin) != 1):
                    raise IOError("EDF stack redimensioning not supported yet")
            stack = QStack(imagestack=imagestack)
        elif line.startswith('Spectral'):
            stack = OmnicMap.OmnicMap(args[0])
        elif line.startswith('#\tDate:'):
            stack = LuciaMap.LuciaMap(args[0])
        elif args[0][-4:].upper() in ["PIGE", "PIXE"]:
            stack = SupaVisioMap.SupaVisioMap(args[0])
        elif args[0][-3:].upper() in ["RBS"]:
            stack = SupaVisioMap.SupaVisioMap(args[0])
        elif args[0][-3:].lower() in [".h5", "nxs", "hdf", "hdf5"]:
            if not HDF5:
                raise IOError(\
                    "No HDF5 support while trying to read an HDF5 file")
            stack = QHDF5Stack1D.QHDF5Stack1D(args)
        elif args[0].upper().endswith("RAW.GZ")or\
             args[0].upper().endswith("EDF.GZ")or\
             args[0].upper().endswith("CCD.GZ")or\
             args[0].upper().endswith("RAW.BZ2")or\
             args[0].upper().endswith("EDF.BZ2")or\
             args[0].upper().endswith("CCD.BZ2"):
            if imagestack is None:
                imagestack = True
            stack = QStack(imagestack=imagestack)
        else:
            if HDF5:
                if h5py.is_hdf5(args[0]):
                    stack = QHDF5Stack1D.QHDF5Stack1D(args)
                else:
                    stack = QSpecFileStack()
                    specfile = True
            else:
                stack = QSpecFileStack()
                specfile = True

        if specfile and (len(begin) == 2):
            if increment is None:
                increment = [1] * len(begin)
            shape = (len(range(begin[0], end[0] + 1, increment[0])),
                     len(range(begin[1], end[1] + 1, increment[1])))
            stack.loadFileList(args, fileindex=fileindex, shape=shape)
        else:
            stack.loadFileList(args, fileindex=fileindex)
        return stack

    def _getFileList(self, fileTypeList, message=None, getfilter=None):
        if message is None:
            message = "Please select a file"
        if getfilter is None:
            getfilter = False
        wdir = PyMcaDirs.inputDir
        filterused = None
        if getfilter:
            filelist, filterused = PyMcaFileDialogs.getFileList(self.parent,
                            filetypelist=fileTypeList,
                            mode="OPEN",
                            message=message,
                            currentdir=wdir,
                            getfilter=True,
                            single=False,
                            native=True)
        else:
            filelist = PyMcaFileDialogs.getFileList(self.parent,
                            filetypelist=fileTypeList,
                            mode="OPEN",
                            message=message,
                            currentdir=wdir,
                            getfilter=False,
                            single=False,
                            native=True)

        if len(filelist):
            PyMcaDirs.inputDir = os.path.dirname(filelist[0])
            if PyMcaDirs.outputDir is None:
                PyMcaDirs.outputDir = os.path.dirname(filelist[0])

        if getfilter:
            return filelist, filterused
        else:
            return filelist

    def _getStackOfFiles(self, getfilter=None):
        if getfilter is None:
            getfilter = False
        fileTypeList = ["HDF5 Files (*.nxs *.hdf *.hdf5 *.h5)",
                        "EDF Files (*edf *edf.gz)",
                        "EDF Files (*ccd)",
                        "Image Files (*edf *ccd *raw *edf.gz *ccd.gz *raw.gz *cbf)",
                        "Image Files (*tif *tiff *TIF *TIFF)",
                        "TextImage Files (*txt)",
                        "Specfile Files (*mca)",
                        "Specfile Files (*dat)",
                        "OMNIC Files (*map)",
                        "OPUS-DPT Files (*.DPT *.dpt)",
                        "JCAMP-DX Files (*.JDX *.jdx *.DX *.dx)",
                        "LabSpec6 Files (*.tif *.TIF *.TIFF *.TIFF *.txt *.TXT)",
                        "RTX Files (*.rtx *.RTX)",
                        "Lispix-RPL Files (*.rpl)",
                        "Renishaw-ASCII Files (*.txt *.TXT)",
                        "PerkinElmer-FSM Files (*.fsm *.FSM)",
                        "AIFIRA Files (*DAT)",
                        "SupaVisio Files (*pige *pixe *rbs)",
                        "MRC files (*.mrc *.st)",
                        "All Files (*)"]
        if not HDF5:
            idx = fileTypeList.index("HDF5 Files (*.nxs *.hdf *.hdf5 *.h5)")
            del fileTypeList[idx]
        if BrukerBCF.HAS_BCF_SUPPORT:
            idx = fileTypeList.index("RTX Files (*.rtx *.RTX)")
            fileTypeList.insert(idx+1, "BCF Files (*.bcf *.BCF)")
        message = "Open ONE indexed stack or SEVERAL files"
        return self._getFileList(fileTypeList, message=message,
                                 getfilter=getfilter)

    def getFileListFromPattern(self, pattern, begin, end, increment=None):
        if type(begin) == type(1):
            begin = [begin]
        if type(end) == type(1):
            end = [end]
        if len(begin) != len(end):
            raise ValueError(\
                "Begin list and end list do not have same length")
        if increment is None:
            increment = [1] * len(begin)
        elif type(increment) == type(1):
            increment = [increment]
        if len(increment) != len(begin):
            raise ValueError(\
                "Increment list and begin list do not have same length")
        fileList = []
        if len(begin) == 1:
            for j in range(begin[0], end[0] + increment[0], increment[0]):
                fileList.append(pattern % (j))
        elif len(begin) == 2:
            for j in range(begin[0], end[0] + increment[0], increment[0]):
                for k in range(begin[1], end[1] + increment[1], increment[1]):
                    fileList.append(pattern % (j, k))
        elif len(begin) == 3:
            raise ValueError("Cannot handle three indices yet.")
        else:
            raise ValueError("Cannot handle more than three indices.")
        return fileList


def main(args):
    if args.cli_test and args.filepattern is None and not args.files:
        print("No input files provided.")
        return 0

    from PyMca5.PyMcaGui.pymca import QStackWidget

    if args.filepattern is not None:
        if (args.begin is None) or (args.end is None):
            raise ValueError(
                "A file pattern needs at least a set of begin and end indices"
            )

    app = qt.QApplication([])
    PyMcaAppInit.init_before_app_start(qt_app=app, cli_args=args)

    widget = QStackWidget.QStackWidget()
    w = StackSelector(widget)

    if args.filepattern is not None:
        stack = w.getStackFromPattern(
            args.filepattern,
            args.begin,
            args.end,
            increment=args.increment,
            imagestack=args.imagestack,
        )
    else:
        stack = w.getStack(args.files, imagestack=args.imagestack)

    if stack is None:
        print("No files selected.")
        return 0

    if isinstance(stack, list):
        widget.setStack(stack[0])
        secondary = QStackWidget.QStackWidget(
            primary=False,
            rgbwidget=widget.rgbWidget,
        )
        secondary.setStack(stack[1])
        widget.setSecondary(secondary)
    else:
        widget.setStack(stack)

    widget.show()

    # Auto-close Qt application for tests
    if args.cli_test:
        qt.QTimer.singleShot(0, app.quit)

    return app.exec()


def build_parser():
    parser = CliUtils.create_parser(description="PyMca Stack Viewer", add_qt_options=True)

    parser.add_argument("--fileindex", type=int, default=0)

    parser.add_argument("--filepattern", type=str, default=None, help="File pattern")
    parser.add_argument("--begin", type=CliUtils.int_or_list, default=None, help="Begin index/indices, comma-separated")
    parser.add_argument("--end", type=CliUtils.int_or_list, default=None, help="End index/indices, comma-separated")
    parser.add_argument("--increment", type=CliUtils.int_or_list, default=None, help="Increment(s), comma-separated")

    parser.add_argument("--imagestack", type=int, default=0)

    parser.add_argument("files", nargs="*", help="Input files if not using filepattern")

    return parser


if __name__ == "__main__":
    PyMcaAppInit.init_before_app_create()
    exit_code = CliUtils.cli_main(main, build_parser(), loggers=(_logger,))
    sys.exit(exit_code)
