# coding: utf-8
# /*#########################################################################
# Copyright (C) 2019-2023 European Synchrotron Radiation Facility
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
# ###########################################################################*/
__authors__ = ["V.A. Sole"]
import sys
import time
import os
import glob
import shutil
from cx_Freeze import setup, Executable, hooks
try:
    from cx_Freeze import version as cxVersion
except ImportError:
    import cx_Freeze
    cxVersion = cx_Freeze.__version__

if not sys.platform.startswith("win"):
    print("Warning: Only windows usage tested!")

tested_versions = ["6.11.1", "6.14.3", "6.14.4", "6.14.7"]
if ("%s" % cxVersion) not in tested_versions:
    print("Warning: cx_Freeze version %s not tested" % cxVersion)

if "build_exe" not in sys.argv:
    print("Usage:")
    print("python setup_cx.py build_exe")
    sys.exit()

#
SPECPATH = os.path.abspath(__file__)
PROJECT_PATH = SPECPATH
while not os.path.exists(os.path.join(PROJECT_PATH, "icons")):
    PROJECT_PATH = os.path.dirname(PROJECT_PATH)

if sys.platform.startswith('darwin'):
   exe_icon = os.path.join(PROJECT_PATH, "icons", "PyMca.icns")
else:
   exe_icon = os.path.join(PROJECT_PATH, "icons", "PyMca.ico")

# special modules are included completely, with their data files, by scripts
# run after the actual cx_Freeze operation. You may try to add them as packages
# adding the module name as string in packages. If you add a module as special
# module, you should consider to add that module to the excludes list
packages = []
special_modules = []
excludes = []
includes = []

# This module basically does not work with frozen versions
excludes.append("multiprocessing")

#some standard encodings
#includes.append('encodings.ascii')
#includes.append('encodings.utf_8')
#includes.append('encodings.latin_1')

# needed by numpy.random
includes.append('secrets')

# exec_dict is a dictionnary whose keys are the name of the .exe files to be
# generated and the values are the paths to the scripts to be frozen.
exec_dict = {}

# Program and version are used for the eventual NSIS installer
program = ""
version = ""


# a hook to bypass cx_Freeze hooks if needed
def dummy_hook(*var, **kw):
    return

# what follows is the customization for PyMca
USE_QT = True
if USE_QT:
    # If Qt is used, there is no reason to pack tkinter
    hooks.load_tkinter = dummy_hook
    excludes.append("tcl")
    excludes.append("tk")
    excludes.append("tkinter")

# Mandatory modules to be integrally included in the frozen version.
# One can add other modules here if not properly detected by cx_Freeze
# (PyQt5 and matplotlib seem to be properly handled, if not, add them
# to special_modules)
import PyMca5
import fisx
import h5py
import numpy
import matplotlib
import ctypes
import hdf5plugin

packages = ["PyMca5"] # is this line needed having PyMca5 as special module?
program = "PyMca"
version = PyMca5.version()
special_modules = [os.path.dirname(PyMca5.__file__),
                   os.path.dirname(fisx.__file__),
                   os.path.dirname(h5py.__file__),
                   os.path.dirname(numpy.__file__),
                   os.path.dirname(matplotlib.__file__),
                   os.path.dirname(ctypes.__file__),
                   os.path.dirname(hdf5plugin.__file__)]
try:
    import OpenGL
    special_modules += [os.path.dirname(OpenGL.__file__)]
except ImportError:
    print("OpenGL not available, not added to the frozen executables")

# This adds the interactive console but probably I should aim at an older
# version to reduce binary size. Tested with IPython 7.4.0
try:
    import IPython
    import pygments
    import qtconsole
    import asyncio
    import ipykernel
    import zmq
    includes.append("colorsys")
    special_modules += [os.path.dirname(IPython.__file__)]
    special_modules += [os.path.dirname(pygments.__file__)]
    special_modules += [os.path.dirname(qtconsole.__file__)]
    special_modules += [os.path.dirname(asyncio.__file__)]
    special_modules += [os.path.dirname(ipykernel.__file__)]
    special_modules += [os.path.dirname(zmq.__file__)]
except ImportError:
    print("qtconsole not available, not added to the frozen executables")

try:
    import silx
    import fabio
    special_modules += [os.path.dirname(silx.__file__),
                        os.path.dirname(fabio.__file__)]
except ImportError:
    print("silx not available, not added to the frozen executables")

try:
    import bcflight
    special_modules += [os.path.dirname(bcflight.__file__)]
except ImportError:
    print("bcflight not available, not added to the frozen executables")

# package used by silx and probably others that is not always added properly
# always add it because it is small
try:
    import pkg_resources
    special_modules += [os.path.dirname(pkg_resources.__file__)]
    excludes += ["pkg_resources"]
except ImportError:
    print("pkg_resources could not be imported")

try:
    import importlib
    special_modules += [os.path.dirname(importlib.__file__)]
except ImportError:
    print("importlib could not be imported")

# pyopencl needs special treatment
try:
    import pyopencl
    import mako
    import cffi
    import pytools
    OPENCL = True
except:
    OPENCL = False

if sys.platform.lower().startswith("linux"):
    # no sense to freeze
    OPENCL = False

if OPENCL:
    special_modules.append(os.path.dirname(pyopencl.__file__))
    special_modules.append(os.path.dirname(mako.__file__))
    special_modules.append(os.path.dirname(cffi.__file__))
    special_modules.append(os.path.dirname(pytools.__file__))
    includes.append("decorator")
else:
    excludes.append("pyopencl")

# other generic packages not always properly detected but that are small and
# desirable to have
import collections
special_modules += [os.path.dirname(collections.__file__)]

# no scipy (huge package not used by PyMca)
#excludes += ["scipy"]
# community requested modules
try:
    import scipy
    special_modules.append(os.path.dirname(scipy.__file__))
except ImportError:
    print("scipy not available, not added to the frozen executables")

try:
    import sklearn
    import threadpoolctl
    import joblib
    import prompt_toolkit
    #special_modules.append(os.path.dirname(sklearn.__file__))
    includes.append("sklearn")
    special_modules.append(os.path.dirname(joblib.__file__))
    special_modules.append(threadpoolctl.__file__)
    special_modules.append(os.path.dirname(prompt_toolkit.__file__))
except ImportError:
    print("scikit-learn not available, not added to the frozen executables")
    sklearn = None

try:
    import umap
    import pynndescent
    includes.append("umap")
    special_modules.append(os.path.dirname(pynndescent.__file__))
except ImportError:
    print("umap-learn not available, not added to the frozen executables")

# give some time to read the output
time.sleep(2)

# executable scripts to be generated for PyMca
PyMcaDir = os.path.dirname(PyMca5.__file__)
exec_dict = {"PyMcaMain": os.path.join(PyMcaDir, "PyMcaGui", \
                                      "pymca", "PyMcaMain.py"),
            "PyMcaBatch": os.path.join(PyMcaDir, "PyMcaGui", \
                                       "pymca", "PyMcaBatch.py"),
            "QStackWidget":os.path.join(PyMcaDir, "PyMcaGui", \
                                        "pymca", "QStackWidget.py"),
            "PeakIdentifier":os.path.join(PyMcaDir, "PyMcaGui", \
                                         "physics", "xrf", "PeakIdentifier.py"),
            "EdfFileSimpleViewer": os.path.join(PyMcaDir, "PyMcaGui", \
                                                 "pymca", "EdfFileSimpleViewer.py"),
            "PyMcaPostBatch": os.path.join(PyMcaDir, "PyMcaGui", \
                                           "pymca", "PyMcaPostBatch.py"),
            "Mca2Edf": os.path.join(PyMcaDir, "PyMcaGui", \
                                    "pymca", "Mca2Edf.py"),
            "ElementsInfo":os.path.join(PyMcaDir, "PyMcaGui", \
                                        "physics", "xrf", "ElementsInfo.py"),
            }

include_files = []
for f in special_modules:
    include_files.append((f, os.path.basename(f)))

build_options = {
    "packages": packages,
    "includes": includes,
    "include_files": include_files,
    "excludes": excludes,
    "zip_exclude_packages":["*"]}
    #"compressed": True, }

if sklearn:
    build_options["include_msvcr"] = True

if sys.platform.startswith("darwin") and cxVersion not in ["6.11.1"]:
    # something got wrong starting with cx_Freeze 6.12.0
    # see https://github.com/marcelotduarte/cx_Freeze/issues/1671
    build_options["bin_excludes"] = ["libiodbc",
                                     "libiodbc.2.dylib",
                                     "libpq.5.dylib"]

install_options = {}

# attempt to cleanup build directory
if os.path.exists("build"):
    try:
        shutil.rmtree("build")
    except:
        print("WARNING: Cannot cleanup build directory")
    time.sleep(0.1)

# generate intermediate scripts to deal with the path during execution
tmpDir = os.path.join("build", "tmp")
if os.path.exists(tmpDir):
    shutil.rmtree(tmpDir)
if not os.path.exists("build"):
    os.mkdir("build")
print("Creating temporary directory <%s>" % tmpDir)
os.mkdir(tmpDir)

for f in list(exec_dict.keys()):
    infile = open(exec_dict[f], "r")
    outname = os.path.join(tmpDir, os.path.basename(exec_dict[f]))
    outfile = open(outname, "w")
    outfile.write("import os\n")
    outfile.write("import ctypes\n")
    # weird, somehow writing something solves startup crashes that
    # do not occur when running in debug mode
    outfile.write("print('')\n")
    magic = 'os.environ["PATH"] += os.path.dirname(os.path.dirname(ctypes.__file__))\n'
    outfile.write(magic)
    for line in infile:
        outfile.write(line)
    outfile.close()
    infile.close()
    exec_dict[f] = outname

executables = []
for key in exec_dict:
    icon = None
    # this allows to map a different icon to each executable
    if sys.platform.startswith('win'):
        if key in ["PyMcaMain", "QStackWidget"]:
            icon = exe_icon
    executables.append(Executable(exec_dict[key],
                                  base="Console" if sys.platform == 'win32' else None,
                                  icon=icon))
# the actual call to cx_Freeze
setup(name='pymca',
      version=PyMca5.version(),
      description="PyMca %s" % PyMca5.version(),
      options=dict(build_exe=build_options,
                   install_exe=install_options),
      executables=executables)

# cleanup
if sys.version.startswith("3.7"):
    filesToRemove = ["MSVCP140.dll", "python37.dll"]
elif sys.version.startswith("3.6"):
    filesToRemove = ["MSVCP140.dll", "python36.dll"]
else:
    filesToRemove = []
    print("Your list of files to remove needs to be updated")

if sys.platform.startswith("win"):
    exe_win_dir = os.path.join("build",
                           "exe.win-amd64-%d.%d" %
                           (sys.version_info[0], sys.version_info[1]))
    REPLACE_BIG_FILES = True
    REMOVE_DUPLICATED_MODULES = True
    REMOVE_REPEATED_DLL =False# True
    RENAME_EXECUTABLES = True# False
    QTDIR = os.getenv("QTDIR")#False
else:
    exe_win_dir = os.path.join("build",
                           "exe.%s-x86_64-%d.%d" %
                           (sys.platform,
                            sys.version_info[0], sys.version_info[1]))

    if not os.path.exists(exe_win_dir) and sys.platform.startswith("darwin"):
        exe_win_dir = os.path.join("build",
                           "exe.%s-%d.%d" %
                           ("macosx-10.9-universal2", #TODO how to get this information?
                            sys.version_info[0], sys.version_info[1]))

    REPLACE_BIG_FILES = True
    REMOVE_DUPLICATED_MODULES = True
    REMOVE_REPEATED_DLL = False
    RENAME_EXECUTABLES = True
    QTDIR = os.getenv("QTDIR")

if REPLACE_BIG_FILES:
    # replace excessively big files
    # somehow some modules are bigger in the installation than just
    # copying them manually.
    destinationDir = exe_win_dir
    safe_replacement = [os.path.dirname(mod.__file__) \
                        for mod in [PyMca5, fisx, h5py, numpy, hdf5plugin] \
                        if mod is not None]
    for dirname in safe_replacement:
        destination = os.path.join(destinationDir, os.path.basename(dirname))
        if os.path.exists(destination):
            print("Deleting %s" % destination)
            shutil.rmtree(destination)
            print("Deleted")
    for dirname in safe_replacement:
        destination = os.path.join(destinationDir, os.path.basename(dirname))
        print("Copying %s" % destination)
        shutil.copytree(dirname, destination)


if REMOVE_DUPLICATED_MODULES:
    # remove duplicated modules
    import shutil
    destinationDir = os.path.join(exe_win_dir, "lib")
    for dirname in special_modules:
        destination = os.path.join(destinationDir, os.path.basename(dirname))
        if os.path.exists(destination):
            print("Deleting %s" % destination)
            shutil.rmtree(destination)
            print("Deleted")
        else:
            print("Not existing %s" % destination)
            time.sleep(0.1)

        # the directories were already copied as include_files
        print("moving %s" % destination)
        shutil.move(os.path.join(exe_win_dir, os.path.basename(dirname)),
                        destination)

if REMOVE_REPEATED_DLL:
    work0 = []
    work1 = []
    for root, directory, files in os.walk("build"):
        for fname in files:
            if fname in filesToRemove:
                work0.append(os.path.join(root, fname))
        for dire in directory:
            if dire == "__pycache__":
                work1.append(os.path.join(root, dire))

    for item in work0[2:]:
        os.remove(item)

    work1.reverse()
    for item in work1:
        shutil.rmtree(item)

if RENAME_EXECUTABLES:
    #rename the executables to .exe for easier handling by the start scripts
    for f in list(exec_dict.keys()):
        executable = os.path.join(exe_win_dir, f)
        if os.path.exists(executable):
            os.rename(executable, executable+".exe")
        #create the start script
        text  = "#!/bin/bash\n"
        text += 'if test -e "./%s.exe"; then\n' % f
        if QTDIR:
            text += '    export LD_LIBRARY_PATH=./:./Qt/lib:${LD_LIBRARY_PATH}\n'
        else:
            text += '    export LD_LIBRARY_PATH=./:${LD_LIBRARY_PATH}\n'
        text += '    exec ./%s.exe $*\n' % f
        text += 'else\n'
        text += '    if test -z "${PYMCAHOME}" ; then\n'
        text += '        thisdir=`dirname $0` \n'
        text += '        export PYMCAHOME=${thisdir}\n'
        text += '    fi\n'
        if QTDIR:
            text += '    export LD_LIBRARY_PATH=${PYMCAHOME}:${PYMCAHOME}/Qt/lib:${LD_LIBRARY_PATH}\n'
        else:
            text += '    export LD_LIBRARY_PATH=${PYMCAHOME}:${LD_LIBRARY_PATH}\n'
        text += '    exec ${PYMCAHOME}/%s.exe $*\n' % f
        text += 'fi\n'
        nfile = open(executable, 'w')
        nfile.write(text)
        nfile.close()
        os.system("chmod 775 %s"  % executable)
        #generate the lowercase commands
        if f == "PyMcaMain":
            os.system("cp -f %s %s" % (executable,
                                       os.path.join(exe_win_dir, 'pymca')))
        elif f == "QStackWidget":
            os.system("cp -f %s %s" % (executable,
                                       os.path.join(exe_win_dir, 'pymcaroitool')))
        elif f == "EdfFileSimpleViewer":
            os.system("cp -f %s %s" % (executable,
                                       os.path.join(exe_win_dir, 'edfviewer')))
        else:
            os.system("cp -f %s %s" % (executable,
                                       os.path.join(exe_win_dir, f.lower())))
            if f == "PyMcaPostBatch":
                os.system("cp -f %s %s" % (executable,
                                           os.path.join(exe_win_dir,
                                           'rgbcorrelator')))
if QTDIR:
    # copy the Qt library directory and create the qt.conf file
    destinationDir = exe_win_dir
    if not os.path.exists(os.path.join(QTDIR, "lib")):
        print("Cannot find lib folder. Invalid QTDIR <%s>" % QTDIR)
    os.system("cp -R -f %s %s" % (QTDIR, os.path.join(destinationDir, "Qt")))
    for d in ["mkspecs", "doc", "include"]:
        target = os.path.join(destinationDir, "Qt", d)
        if os.path.exists(target):
            os.system("rm -rf %s" % target)

    # generate qt.conf file
    qtconf = os.path.join(destinationDir, "qt.conf")
    if os.path.exists(qtconf):
        os.remove(qtconf)
    text = b"[Paths]\n"
    text += b"Prefix = ./Qt\n"
    f = open(qtconf, "wb")
    f.write(text)
    f.close()

if OPENCL:
    # pyopencl __init__.py needs to be patched
    initFile = os.path.join(exe_win_dir, "pyopencl", "__init__.py")
    print("###################################################################")
    print("Patching pyopencl file")
    print(initFile)
    print("###################################################################")
    f = open(initFile, "r")
    content = f.readlines()
    f.close()
    i = 0
    i0 = 0
    for line in content:
        if "def _find_pyopencl_include_path():" in line:
            i0 = i - 1
        elif (i0 != 0) and ("}}}" in line):
            i1 = i
            break
        i += 1
    f = open(initFile, "w")
    for i in range(0, i0):
        f.write(content[i])
    txt ='\n'
    txt +='def _find_pyopencl_include_path():\n'
    txt +='     from os.path import dirname, join, realpath\n'
    txt +="     return '\"%s\"' % join(realpath(dirname(__file__)), \"cl\")"
    txt +="\n"
    txt +="\n"
    f.write(txt)
    for line in content[i1:]:
        f.write(line)
    f.close()

if not sys.platform.startswith("win"):
    # rename final folder
    txt = "PyMca%s" % PyMca5.__version__
    os.system("mv %s %s" % (exe_win_dir, os.path.join("build", txt)))
    os.chdir("build")
    if sys.platform.startswith("darwin"):
        platform = "macosx"
    elif sys.platform.startswith("linux"):
        platform = "linux"
    else:
        platform = sys.platform
    os.system("tar -cvzf pymca%s-%s.tgz ./%s" % (PyMca5.__version__, platform, txt))
    os.system("mv *.tgz ../")
    os.chdir("../")


#  generation of the NSIS executable
# nsis = os.path.join(r"\Program Files (x86)", "NSIS", "makensis.exe")
# if sys.platform.startswith("win") and os.path.exists(nsis):
nsis = shutil.which("makensis")
if sys.platform.startswith("win") and shutil.which("makensis"):
    # check if we can perform the packaging
    outFile = "nsisscript.nsi"
    f = open("nsisscript.nsi.in", "r")
    content = f.readlines()
    f.close()
    if os.path.exists(outFile):
        os.remove(outFile)
    pymcaexe = "%s%s-win64.exe" % (program.lower(), version)
    if os.path.exists(pymcaexe):
        os.remove(pymcaexe)
    frozenDir = os.path.join(".", exe_win_dir)
    f = open(outFile, "w")
    for line in content:
        if "__VERSION__" in line:
            line = line.replace("__VERSION__", version)
        if "__PROGRAM__" in line:
            line = line.replace("__PROGRAM__", program)
        if "__OUTFILE__" in line:
            line = line.replace("__OUTFILE__", pymcaexe)
        if "__SOURCE_DIRECTORY__" in line:
            line = line.replace("__SOURCE_DIRECTORY__", frozenDir)
        if "__ICON__" in line:
            line = line.replace("__ICON__", exe_icon)
        f.write(line)
    f.close()
    cmd = '"%s" %s' % (nsis, outFile)
    print(cmd)
    os.system(cmd)
else:
    print("Cannot find makensis executable")