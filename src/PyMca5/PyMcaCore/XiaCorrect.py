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
__author__ = "E. Papillon - ESRF Software group"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

from PyMca5.PyMcaGui import PyMcaAppInit

if __name__== '__main__':
    PyMcaAppInit.init_before_app_import()

import os
import sys
import time

from PyMca5.PyMcaGui import PyMcaQt as qt
from PyMca5.PyMcaGui.pymca import XiaCorrectWizard
from PyMca5.PyMcaMisc import CliUtils
from . import XiaEdf


__version__="$Revision: 1.11 $"

def defaultErrorCB(message):
    print(message)

def defaultLogCB(message, verbose_level=None, verbose_ask=None):
    if verbose_level is None:
        print(message)
    elif verbose_level <= verbose_ask:
        print(message)

def defaultDoneCB(nbdone, total):
    pass

def checkCB(log_cb=None, done_cb=None, error_cb=None):
    if log_cb is None:
        log_cb= defaultLogCB
    if done_cb is None:
        done_cb= defaultDoneCB
    if error_cb is None:
        error_cb= defaultErrorCB

    return (log_cb, done_cb, error_cb)


def parseFiles(filelist, verbose=0, keep_sum=0, log_cb=None, done_cb=None, error_cb=None):
    (log_cb, done_cb, error_cb)= checkCB(log_cb, done_cb, error_cb)

    log_cb("Checking xia files ...")
    xiafiles= []

    for file in filelist:
        xf= XiaEdf.XiaFilename(file)
        if xf.isValid():
            log_cb(" - Parsing %s (OK - %s)"%(file, xf.getType()), 1, verbose)
            if not keep_sum:
                if not xf.isSum():
                    xiafiles.append(xf)
            else:
                xiafiles.append(xf)
        else:
            log_cb(" - Parsing %s (Not Xia)"%file, 1, verbose)

    if len(xiafiles):
        log_cb("Sorting xia files ...")
        xiafiles.sort()

        groupfiles= []
        group= None

        for xf in xiafiles:
            if group is None:
                group= [ xf ]
            else:
                if xf.isGroupedWith(group[0]):
                    group.append(xf)
                else:
                    groupfiles.append(group)
                    group= [ xf ]
        if group is not None:
            groupfiles.append(group)

        grouperrors= []
        for group in groupfiles:
            if group[0].isScan():
                if not group[-1].isStat():
                    stat= group[0].findStatFile()
                    if stat is not None:
                        log_cb(" - Find stat file for group <%s>"%stat.get(), 1, verbose)
                        group.append(stat)
                    else:
                        error_cb("XiaCorrect ERROR: no stat file in current group <%s>"%group[0].get())
                        grouperrors.append(group)

        for group in grouperrors:
            groupfiles.remove(group)

        if not len(groupfiles):
            error_cb("XiaCorrect ERROR: No valid XIA group files")
            return None

        return groupfiles

    else:
        error_cb("XiaCorrect ERROR: No XIA files found.")
        return None


def correctFiles(xiafiles, deadtime=1, livetime=0, sums=None, avgflag=0, outdir=None, outname="corr", force=0, \
		    verbose=0, log_cb=None, done_cb=None, error_cb=None):
    (log_cb, done_cb, error_cb)= checkCB(log_cb, done_cb, error_cb)

    processed= 0
    saved= 0
    total= 0
    errors= 0
    tps= time.time()

    done_cb(0, total)
    total= len(xiafiles)

    log_cb("Correcting xia files ...")

    for group in xiafiles:
        if not group[0].isScan():
            file= group[0]
            name= file.get()
            log_cb("Working on %s"%name, 1, verbose)

            try:
                xia= XiaEdf.XiaEdfCountFile(name)
                file.setDirectory(outdir)
                file.appendPrefix(outname)
                name= file.get()

                if sums is not None:
                    err= xia.sum(sums, deadtime, livetime, avgflag)
                    file.setType("sum", -1)
                else:
                    err= xia.correct(deadtime, livetime)
                if len(err):
                    error_cb(" - WARNING: in %s"%name)
                    for msg in err:
                        error_cb("     * " + msg)

                log_cb(" - Saving %s"%name)
                xia.save(name, force)
                saved += 1

            except XiaEdf.XiaEdfError:
                errors += 1
                log_cb(sys.exc_info()[1])

        else:
            groupfiles= [ file.get() for file in group ]
            name= groupfiles[-1]
            log_cb("Reading %s"%name, 1, verbose)

            try:
                xia= XiaEdf.XiaEdfScanFile(name, groupfiles[:-1])
            except XiaEdf.XiaEdfError:
                xia= None
                errors += 1
                error_cb(sys.exc_info()[1])

            if xia is not None:
                for file in group:
                    file.setDirectory(outdir)
                    file.appendPrefix(outname)

                if sums is None:
                    for file in group[:-1]:
                        det= file.getDetector()

                        if det is not None:
                            log_cb("Working on detector #%02d"%det, 1, verbose)
                            try:
                                err= xia.correct(det, deadtime, livetime)
                                name= file.get()

                                if len(err):
                                    error_cb(" - WARNING: in %s"%name)
                                    for msg in err:
                                        error_cb("     * " + msg)

                                log_cb(" - Saving %s"%name)
                                xia.save(name, force)

                                saved += 1

                            except XiaEdf.XiaEdfError:
                                errors += 1
                                error_cb(sys.exc_info()[1])
                else:
                    log_cb("Working on group %s"%name, 1, verbose)
                    file= group[-1]
                    for isum in range(len(sums)):
                        try:
                            err= xia.sum(sums[isum], deadtime, livetime, avgflag)

                            file.setType("sum", isum+1)
                            name= file.get()

                            if len(err):
                                error_cb(" - WARNING: in %s"%name)
                                for msg in err:
                                    error_cb("     * " + msg)

                            log_cb(" - Saving %s"%name)
                            xia.save(name, force)

                            saved += 1
                        except XiaEdf.XiaEdfError:
                            errors += 1
                            error_cb(sys.exc_info()[1])

        processed += 1
        done_cb(processed, total)

    done_cb(total, total)
    log_cb("\n* %d groups processed and %d files saved in %.2f sec"%(processed, saved, time.time()-tps))
    if not errors:
        log_cb("* No errors found")
    else:
        log_cb("* %d errors found"%errors)
    log_cb("\n")



def main(args):
    # If no CLI arguments -> GUI mode
    if (
        not args.input
        and not args.files
        and not args.deadtime
        and not args.livetime
        and not args.sums
    ):
        app = qt.QApplication([])
        PyMcaAppInit.init_before_app_start(qt_app=app, cli_args=args)

        wid = XiaCorrectWizard.XiaCorrectWizard()

        # Auto-close Qt for tests
        if args.cli_test:
            qt.QTimer.singleShot(0, wid.close)

        ret = wid.exec()

        if ret == qt.QDialog.Accepted:
            options = wid.get()
            files = parseFiles(options["files"], options["verbose"])
            if files is not None:
                correctFiles(
                    files,
                    options["deadtime"],
                    options["livetime"],
                    options["sums"],
                    options["avgflag"],
                    options["output"],
                    options["name"],
                    options["force"],
                    options["verbose"],
                )

        return 0

    options = {
        "input": args.input or [],
        "files": [],
        "output": args.output,
        "force": int(args.force),
        "name": args.name,
        "verbose": int(args.verbose),
        "deadtime": int(args.deadtime),
        "livetime": int(args.livetime),
        "sums": None,
        "avgflag": int(args.avgflag),
        "parsing": int(args.parsing),
    }

    # Handle sums
    if args.sums:
        options["sums"] = []
        for s in args.sums:
            try:
                ssum = [int(det) for det in s.split(",")]
                if ssum and ssum[0] == -1:
                    ssum = []
                options["sums"].append(ssum)
            except Exception:
                print("XiaCorrect ERROR: Cannot parse sum detectors")
                print("\t%s" % s)
                return 0

    # Expand input directories
    for iinput in options["input"]:
        if not os.path.isdir(iinput):
            print(f"XiaCorrect WARNING: Input directory <{iinput}> is not valid")
            continue

        files = [os.path.join(iinput, f) for f in os.listdir(iinput)]
        if not files:
            print(f"XiaCorrect WARNING: Input directory <{iinput}> is empty")
        else:
            options["files"] += files

    # Add explicit files
    options["files"] += args.files

    if not options["files"]:
        print("XiaCorrect ERROR: No input datafiles")
        return 0

    # Validation
    if not options["parsing"]:
        if not options["deadtime"] and not options["livetime"] and options["sums"] is None:
            print("XiaCorrect ERROR: Must have at least deadtime, livetime or sum options")
            return 0

        if options["output"] is not None and not os.path.isdir(options["output"]):
            print("XiaCorrect ERROR: output directory is not valid")
            return 0

    # Execute
    files = parseFiles(options["files"], options["verbose"])

    if files is None:
        return 0

    if options["parsing"]:
        for group in files:
            print("FileGroup:")
            for file in group:
                print(" - ", file.get())
    else:
        correctFiles(
            files,
            options["deadtime"],
            options["livetime"],
            options["sums"],
            options["avgflag"],
            options["output"],
            options["name"],
            options["force"],
            options["verbose"],
        )

    return 0


def build_parser():
    parser = CliUtils.create_parser(description="Xia Correct Tool", add_qt_options=True)

    parser.add_argument("-i", "--input", action="append", help="Input directory (can be used multiple times)")
    parser.add_argument("-o", "--output", help="Output directory")
    parser.add_argument("-f", "--force", action="store_true", help="Force writing output files if they already exists")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-d", "--deadtime", action="store_true", help="Perform deadtime correction")
    parser.add_argument("-l", "--livetime", action="store_true", help="Perform livetime normalization")
    parser.add_argument("-s", "--sum", action="append", dest="sums", help="Comma separated detector list")
    parser.add_argument("-a", "--avg", dest="avgflag", action="store_true")
    parser.add_argument("-n", "--name", default="corr", help="String to be appended to prefix for output filename")
    parser.add_argument("-p", "--parsing", action="store_true")

    parser.add_argument("files", nargs="*", help="Input files")

    return parser


if __name__ == "__main__":
    PyMcaAppInit.init_before_app_create()
    exit_code = CliUtils.cli_main(main, build_parser())
    sys.exit(exit_code)
