# -*- mode: python -*-
import sys
import os
from pathlib import Path
import shutil
import subprocess
import time
import logging

import PyInstaller
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs
from PyInstaller.config import CONF

import numpy
import glob

logger = logging.getLogger("pyinstaller")

DISTDIR = os.path.abspath(CONF["distpath"])
BUILDDIR = os.path.abspath(CONF["workpath"])

logger.info("Using temporary build dir <%s>" % BUILDDIR)
logger.info("Using temporary dist dir <%s>" % DISTDIR)

datas = []

PROJECT_PATH = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
datas.append((os.path.join(PROJECT_PATH, "README.rst"), "."))
datas.append((os.path.join(PROJECT_PATH, "LICENSE"), "."))
datas.append((os.path.join(PROJECT_PATH, "copyright"), "."))
#datas += collect_data_files("silx.resources")

datas += collect_data_files('numpy')

if sys.platform.startswith('darwin'):
   icon = os.path.join(PROJECT_PATH, "icons", "PyMca.icns")
else:
   icon = os.path.join(PROJECT_PATH, "icons", "PyMca.ico")

logger.info("Using icon <%s>" % icon)

hiddenimports = ["secrets"] # needed by numpy 1.23.2
hiddenimports += collect_submodules('encodings.ascii')
hiddenimports += collect_submodules('encodings.utf_8')
hiddenimports += collect_submodules('encodings.latin_1')
hiddenimports += collect_submodules('fabio')
hiddenimports += collect_submodules('PyQt5.uic')
hiddenimports += collect_submodules('hdf5plugin')
hiddenimports += collect_submodules('fisx')
hiddenimports += collect_submodules('PyMca5.PyMcaGui.PyMcaQt')
hiddenimports += collect_submodules('PyMca5.PyMcaGui.pymca')

my_binaries = []

if sys.platform.startswith("win"):
    # hiddenimports += collect_submodules('multiprocessing')
    hiddenimports += collect_submodules('numpy')
    hiddenimports += ['numpy.core._multiarray_umath', 'numpy.core.multiarray']

    my_binaries += collect_dynamic_libs('numpy')

else:
    import h5py
#    possible_dirs = [
#        os.path.join(os.path.dirname(h5py.__file__), '.dylibs'),
#        '/usr/local/lib',  # Homebrew typical location
#        '/opt/homebrew/lib',  # Apple Silicon Homebrew
#        os.path.join(os.path.dirname(h5py.__file__), 'hdf5'),
#    ]
#    hdf5_libs = []
#    for d in possible_dirs:
#        if os.path.isdir(d):
#            dylibs = glob.glob(os.path.join(d, 'libhdf5*.dylib'))
#            for dylib in dylibs:
#                hdf5_libs.append((dylib, os.path.join('h5py', '.dylibs', os.path.basename(dylib))))
#
#    my_binaries += hdf5_libs

   # hiddenimports += collect_submodules('h5py')
   # hiddenimports += [
   #     'h5py',
   #     'h5py.defs',
   #     'h5py._errors',
   #     'h5py._objects',
   # ]
   # my_binaries += collect_dynamic_libs('h5py')
#    my_binaries += collect_dynamic_libs('hdf5')
#    my_binaries += [('/usr/local/opt/hdf5/lib/libhdf5.200.dylib', 'h5py/.dylibs')]
    print('this is a Mac, so shut up and listen')

excludes = []

# they will be added in full
excludes += ["fabio", "hdf5plugin", "silx"]

# if this module is included, the interactive console does not work
excludes.append("debugpy")

# This module basically does not work with frozen versions
# excludes.append("multiprocessing")


# get the script list
import PyMca5
version = PyMca5.version()
PyMcaDir = os.path.abspath(os.path.dirname(PyMca5.__file__))
exec_dict = {"PyMcaMain": os.path.join(PyMcaDir, "PyMcaGui", \
                                     "pymca", "PyMcaMain.py"),
             "PyMcaBatch": os.path.join(PyMcaDir, "PyMcaGui", \
                                   "pymca", "PyMcaBatch.py"),
             "QStackWidget":os.path.join(PyMcaDir, "PyMcaGui", \
                                    "pymca", "QStackWidget.py"),
             "PyMcaPostBatch": os.path.join(PyMcaDir, "PyMcaGui", \
                                    "pymca", "PyMcaPostBatch.py"),
             "EdfFileSimpleViewer": os.path.join(PyMcaDir, "PyMcaGui", \
                                      "pymca", "EdfFileSimpleViewer.py"),
            }

if not sys.platform.startswith("darwin"):
    exec_dict["PeakIdentifier"] = os.path.join(PyMcaDir, "PyMcaGui", \
                                      "physics", "xrf", "PeakIdentifier.py")
    exec_dict["Mca2Edf"] = os.path.join(PyMcaDir, "PyMcaGui", \
                                      "pymca", "Mca2Edf.py")
    exec_dict["ElementsInfo"] = os.path.join(PyMcaDir, "PyMcaGui", \
                                      "physics", "xrf", "ElementsInfo.py")

# for fast testing uncomment the following two lines
#exec_dict = {"PyMcaMain": os.path.join(PyMcaDir, "PyMcaGui", \
#                                     "pymca", "PyMcaMain.py")}

script_n = []
script_l = []
for key in exec_dict:
    script_l.append(exec_dict[key])
    script_n.append(key)

block_cipher = None

script_a = []

for i in range(len(script_l)):
    script = script_l[i]
    cwd = Path(SPECPATH)
    print("Copying %s to %s" % (script, script_n[i]))
    if os.path.exists(script_n[i]):
        os.remove(script_n[i])
    shutil.copy2(
        src = script,
        dst = os.path.join(cwd, script_n[i]),
    )
    script_a.append(Analysis(
                            [script_n[i]],
                            pathex=[],
                            binaries=my_binaries,
                            datas=datas,
                            hiddenimports=hiddenimports,
                            hookspath=[],
                            runtime_hooks=[],
                            excludes=excludes,
                            win_no_prefer_redirects=False,
                            win_private_assemblies=False,
                            cipher=block_cipher,
                            noarchive=False))
    #script_a[-1].pure = [x for x in script_a[-1].pure if not x[0].startswith("PyMca5.")]


if 0: # avoid merge
    if len(script_a) == 2:
        MERGE(
            (script_a[0], script_n[0], os.path.join(script_n[0], script_n[0])), 
            (script_a[1], script_n[1], os.path.join(script_n[1], script_n[1])),
        )
    elif len(script_a) == 3:
        MERGE(
            (script_a[0], script_n[0], os.path.join(script_n[0], script_n[0])), 
            (script_a[1], script_n[1], os.path.join(script_n[1], script_n[1])),
            (script_a[2], script_n[2], os.path.join(script_n[2], script_n[2])), 
        )
    elif len(script_a) == 4:
        MERGE(
            (script_a[0], script_n[0], os.path.join(script_n[0], script_n[0])), 
            (script_a[1], script_n[1], os.path.join(script_n[1], script_n[1])),
            (script_a[2], script_n[2], os.path.join(script_n[2], script_n[2])), 
            (script_a[3], script_n[3], os.path.join(script_n[3], script_n[3])),
        )
    elif len(script_a) >= 5:
        MERGE(
            (script_a[0], script_n[0], os.path.join(script_n[0], script_n[0])), 
            (script_a[1], script_n[1], os.path.join(script_n[1], script_n[1])),
            (script_a[2], script_n[2], os.path.join(script_n[2], script_n[2])), 
            (script_a[3], script_n[3], os.path.join(script_n[3], script_n[3])),
            (script_a[4], script_n[4], os.path.join(script_n[4], script_n[4])),
        )

script_pyz = []
script_exe = []
script_col = []
for i in range(len(script_a)):        
    script_pyz.append(PYZ(script_a[i].pure,
                          script_a[i].zipped_data,
                          cipher=block_cipher))

    arch = os.getenv("PYMCA_PYINSTALLER_TARGET_ARCH") 
    if arch:
        script_exe.append(
            EXE(
                script_pyz[i],
                script_a[i].scripts,
                script_a[i].dependencies,
                [],
                exclude_binaries=True,
                name=script_n[i],
                debug=False,
                bootloader_ignore_signals=False,
                strip=False,
                upx=False,
                console=True,
                icon=icon,
                target_arch=arch)
            )
    else:
        script_exe.append(
            EXE(
                script_pyz[i],
                script_a[i].scripts,
                script_a[i].dependencies,
                [],
                exclude_binaries=True,
                name=script_n[i],
                debug=False,
                bootloader_ignore_signals=False,
                strip=False,
                upx=False,
                console=True,
                icon=icon)
            )
    script_col.append(
        COLLECT(
            script_exe[i],
            script_a[i].binaries,
            script_a[i].zipfiles,
            script_a[i].datas,
            strip=False,
            upx=False,
            name=script_n[i])
        )

def move_exe(name):
    dist = DISTDIR
    if sys.platform.startswith("darwin"):
        shutil.copy2(
            src=os.path.join(dist, name, name),
            dst=os.path.join(dist, script_n[0])
        )
    else:
        shutil.copy2(
            src=os.path.join(dist, name, name + ".exe"),
            dst=os.path.join(dist, script_n[0])
        )
    shutil.rmtree(os.path.join(dist, name))

if len(script_a) > 1:
    for n in script_n[1:]:
        move_exe(n)


# Mandatory modules to be integrally included in the frozen version.
# One can add other modules here if not properly detected
# (PyQt5 and PySide6 seem to be properly handled, if not, add to special_modules)
import PyMca5
import fisx
import h5py
import numpy
import matplotlib
import ctypes
import hdf5plugin

program = "PyMca"
version = PyMca5.version()
special_modules = [os.path.dirname(PyMca5.__file__),
                   os.path.dirname(fisx.__file__),
                   os.path.dirname(h5py.__file__),
                   #os.path.dirname(numpy.__file__),
                   #os.path.dirname(ctypes.__file__),
                   os.path.dirname(hdf5plugin.__file__),
                   ]

# this block  can be needed for matplotlib
MATPLOTLIB_FROM_PYINSTALLER = True
if not MATPLOTLIB_FROM_PYINSTALLER:
    special_modules.append(os.path.dirname(matplotlib.__file__))

    # recent versions of matplotlib need packaging, PIL and pyparsing
    try:
        import packaging
        special_modules.append(os.path.dirname(packaging.__file__))
    except:
        pass
    try:
        import PIL
        special_modules.append(os.path.dirname(PIL.__file__))
    except:
        pass
    try:
        import pyparsing
        special_modules.append(os.path.dirname(pyparsing.__file__))
    except:
        pass
    try:
        import dateutil
        special_modules.append(os.path.dirname(dateutil.__file__))
    except:
        pass
    try:
        import mpl_toolkits.mplot3d.axes3d as axes3d
        special_modules.append(os.path.dirname(os.path.dirname(axes3d.__file__)))
    except:
        pass
    try:
        import six
        special_modules.append(six.__file__)
    except:
        pass
    try:
        import cycler
        special_modules.append(cycler.__file__)
    except:
        pass
    try:
        import uuid
        special_modules.append(uuid.__file__)
    except:
        pass

excludes = []

try:
    import OpenGL
    special_modules += [os.path.dirname(OpenGL.__file__)]
except ImportError:
    logger.info("OpenGL not available, not added to the frozen executables")

# This adds the interactive console but probably I should aim at an older
# version to reduce binary size. Tested with IPython 7.4.0
try:
    import IPython
    import pygments
    import qtconsole
    import asyncio
    import ipykernel
    import zmq
    #includes.append("colorsys")
    special_modules += [os.path.dirname(IPython.__file__)]
    special_modules += [os.path.dirname(pygments.__file__)]
    special_modules += [os.path.dirname(qtconsole.__file__)]
    special_modules += [os.path.dirname(asyncio.__file__)]
    special_modules += [os.path.dirname(ipykernel.__file__)]
    special_modules += [os.path.dirname(zmq.__file__)]
    try:
        import ipython_genutils
        special_modules += [os.path.dirname(ipython_genutils.__file__)]
    except:
        pass
    try:
        import qtpy
        special_modules += [os.path.dirname(qtpy.__file__)]
    except:
        pass
except ImportError:
    logger.info("qtconsole not available, not added to the frozen executables")

try:
    import silx
    import fabio
    import xml # needed by fabio
    special_modules += [os.path.dirname(silx.__file__),
                        os.path.dirname(fabio.__file__),
                        os.path.dirname(xml.__file__),]
    SILX = True
except ImportError:
    logger.info("silx not available, not added to the frozen executables")
    SILX = False

try:
    import freeart
    import tomogui
    special_modules += [os.path.dirname(freeart.__file__),
                        os.path.dirname(tomogui.__file__)]
except ImportError:
    logger.info("tomogui not available, not added to the frozen executables")

# package used by silx and probably others that is not always added properly
# always add it because it is small
try:
    import pkg_resources
    special_modules += [os.path.dirname(pkg_resources.__file__)]
    excludes += ["pkg_resources"]
except ImportError:
    logger.info("pkg_resources could not be imported")

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
    #includes.append("decorator")
else:
    excludes.append("pyopencl")

# other generic packages not always properly detected but that are small and
# desirable to have
import collections
special_modules += [os.path.dirname(collections.__file__)]

# no scipy (huge package not used by PyMca)
excludes += ["scipy"]

# give some time to read the output
time.sleep(2)

def cleanup_cache(topdir): 
    # cleanup __pycache__
    for root, dirs, files in os.walk(topdir):
        for dirname in dirs:
            if dirname == "__pycache__": 
               print("deleting ",os.path.join(topdir, dirname))
               shutil.rmtree(os.path.join(topdir, dirname))
            else:
               cleanup_cache(os.path.join(topdir, dirname))

def replace_module(name):
    dest = os.path.join(DISTDIR, script_n[0])
    if PyInstaller.__version__ >= '6.0.0':
        if sys.platform.startswith("darwin"):
            target = os.path.join(dest, "special_modules")
        else:
            target = os.path.join(dest, "_internal")
        if not os.path.exists(target):
            os.mkdir(target)
        target = os.path.join(target, os.path.basename(name))
    else:
        target = os.path.join(dest, os.path.basename(name))
    print("source = ", name)
    print("dest = ", target)
    if os.path.exists(target):
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)
    if os.path.isdir(name):
        shutil.copytree(name, target)
    else:
        shutil.copy2(src=name, dst=target)
    cleanup_cache(target)

for name in special_modules:
    replace_module(name)

# cleanup copied files
for fname in script_n:
    os.remove(fname)

# cleanup copied files
for fname in script_n:
    if os.path.exists(fname):
        os.remove(fname)

# patch silx
if SILX:
    if PyInstaller.__version__ >= '6.0.0':
        if sys.platform.startswith("darwin"):
            fname_dir = os.path.join(DISTDIR, script_n[0], "special_modules", "silx", "gui","qt")
        else:
            fname_dir = os.path.join(DISTDIR, script_n[0], "_internal", "silx", "gui","qt")
    else:
        fname_dir = os.path.join(DISTDIR, script_n[0], "silx", "gui","qt")
    for name in ["_qt.py", "__init__.py"]:
        fname = os.path.join(fname_dir, name)
        if os.path.exists(fname):
            logger.info("###################################################################")
            logger.info("Patching silx")
            logger.info(fname)
            logger.info("###################################################################")
            f = open(fname, "r")
            content = f.readlines()
            f.close()
            f = open(fname, "w")
            for line in content:
                #f.write(line.replace("from PyQt5.uic import loadUi", "pass"))
                #f.write(line.replace("from PyQt6.uic import loadUi", "pass"))
                if "import loadUi" in line:
                    f.write(line.replace("from ", "pass #"))
                else:
                    f.write(line)
            f.close()
        else:
            logger.info("###################################################################")
            logger.info("Cannot patch silx. File not found")
            logger.info(fname)
            logger.info("###################################################################")

# patch OpenCL
if OPENCL:
    # pyopencl __init__.py needs to be patched
    if PyInstaller.__version__ >= '6.0.0':
        exe_win_dir = os.path.join(DISTDIR, script_n[0], "_internal")
    else:
        exe_win_dir = os.path.join(DISTDIR, script_n[0])
    initFile = os.path.join(exe_win_dir, "pyopencl", "__init__.py")
    logger.info("###################################################################")
    logger.info("Patching pyopencl file")
    logger.info(initFile)
    logger.info("###################################################################")
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
time.sleep(2)

for i in range(len(script_col)):
    app = BUNDLE(
        script_col[i],
        name=script_n[i] + ".app",
        icon=icon,
        bundle_identifier="com.esrf.pymca.mac",
        info_plist={
            "CFBundleIdentifier": "com.github.vasole.pymca",
            "CFBundleShortVersionString": version,
            "CFBundleVersion": "PyMca " + version,
            "LSBackgroundOnly": False,
            "LSTypeIsPackage": True,
            "LSMinimumSystemVersion": "10.9.0",
            "NSHumanReadableCopyright": "MIT",
            "NSHighResolutionCapable": True,
            "NSPrincipalClass": "NSApplication",
            "NSAppleScriptEnabled": False,
       },
    )

# make all the .app share the same resources
if sys.platform.startswith("darwin"):
    source = os.path.join(DISTDIR, script_n[0],"")
    destination = os.path.join(DISTDIR, script_n[0] + ".app", "Contents", "MacOS")
    cmd = "cp -Rf %s %s" % (source, destination)
    result = os.system(cmd)
    if result:
        raise IOError("Unsuccessful copy command <%s>" % cmd)
    subprocess.call(
        [
             "codesign",
             "--remove-signature",
             os.path.join(DISTDIR, script_n[0] + ".app", "Contents", "MacOS", "Python"),
        ]
    )
    if len(script_n) > 1:
        cwd = os.getcwd()
        for script in script_n[1:]:
            source = os.path.join(DISTDIR, script + ".app" ,"Contents", "MacOS")
            os.chdir(os.path.dirname(source))
            cmd = "rm -Rf MacOS"
            result = os.system(cmd)
            if result:
                os.chdir(cwd)
                raise IOError("Unsuccessful command <%s>" % cmd)
            target = os.path.join("..", "..", script_n[0] + ".app", "Contents", "MacOS")
            cmd = "ln -s %s %s" % (target, "MacOS")
            result = os.system(cmd)
            if result:
                os.chdir(cwd)
                raise IOError("Unsuccessful %s" % cmd)
            os.chdir(cwd)

    # rename the application
    version = PyMca5.version()
    source = os.path.join(DISTDIR, script_n[0] + ".app")
    dest = os.path.join(DISTDIR, "PyMca%s.app" % version)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.rename(source, dest)

    # Rename __dot__dylibs to .dylibs inside the bundled h5py package
    h5py_dylibs_old = os.path.join(
        dest,
        "Contents",
        "Frameworks",
        "h5py",
        "__dot__dylibs"
    )
    h5py_dylibs_new = os.path.join(
        dest,
        "Contents",
        "Frameworks",
        "h5py",
        ".dylibs"
    )
#    if os.path.exists(h5py_dylibs_old):
#        os.rename(h5py_dylibs_old, h5py_dylibs_new)
#        print("Renamed __dot__ to . in h5py")
#    else:
#        print("__dot__ not found, skipping rename")

    # relocate the special modules
    special_modules_dir = os.path.join(dest, "Contents", "MacOS", "special_modules")
    if os.path.exists(special_modules_dir):
        source = os.path.join(special_modules_dir, "*")
        dest = os.path.join(dest, "Contents", "Frameworks")
        cmd = "cp -Rf %s %s" % (source, dest)
        print(cmd)
        os.system(cmd)
        source = source[:-1]
        print("deleting %s" % source)
        shutil.rmtree(source)
        # remove the duplicated _internal directory
        internal_modules_dir = os.path.join( \
            DISTDIR, "PyMca%s.app" % version, "Contents", "MacOS", "_internal")
        if os.path.exists(internal_modules_dir):
             print("deleting %s" % internal_modules_dir)
             shutil.rmtree(internal_modules_dir)

    # Pack the application
    destination = os.path.join(SPECPATH, "artifacts")
    if os.path.exists(destination):
        shutil.rmtree(destination)
    outFile = os.path.join(SPECPATH, "create-dmg.sh")
    f = open(os.path.join(SPECPATH, "create-dmg.sh.in"), "r")
    content = f.readlines()
    f.close()
    if os.path.exists(outFile):
        os.remove(outFile)
    f = open(outFile, "w")
    for line in content:
        if "__VERSION__" in line:
            line = line.replace("__VERSION__", version)
        if "__DISTDIR__" in line:
            line = line.replace("__DISTDIR__", DISTDIR)
        f.write(line)
    f.close()
    subprocess.call(["bash", "create-dmg.sh"])
    if os.path.exists(outFile):
        os.remove(outFile)

    # move the image to the top level dist directory
    dist = os.path.join(PROJECT_PATH, "dist")
    if not os.path.exists(dist):
        os.mkdir(dist)
    source = os.path.join(SPECPATH, "artifacts", "PyMca%s.dmg" % version)
    destination = os.path.join(PROJECT_PATH, "dist", "PyMca%s.dmg" % version)
    if os.path.exists(destination):
        os.remove(destination)
    os.rename(source, destination)
    # get rid of the artifacts directory
    shutil.rmtree(os.path.dirname(source))

    program = "PyMca"
    version = PyMca5.version()
    source = os.path.join(DISTDIR, "PyMca%s.app" % version)
    # create intermediate directory for packaging
    tmpdir = os.path.join(os.path.dirname(source), "ROOT")
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)
    scriptsdir = os.path.join(os.path.dirname(source), "scripts")
    if os.path.exists(scriptsdir):
        shutil.rmtree(scriptsdir)
    os.mkdir(tmpdir)
    os.mkdir(scriptsdir)
    postinstall = os.path.join(scriptsdir, "postinstall") 
    with open(postinstall, "w") as f:
        f.write("#!/bin/sh\n")
        f.write("\n")
        #f.write('echo $0 "$1" "$2" "$3" > /Users/sole/called.txt\n')
        f.write('/usr/bin/xattr -cr "$2"/Applications/PyMca%s.app\n' % version)
    os.system("chmod +x %s" % postinstall)
    os.system("cat %s"  % postinstall)
    tmpdir = os.path.join(tmpdir, "Applications")
    os.mkdir(tmpdir)
    tmpsource = os.path.join(tmpdir, os.path.basename(source))
    shutil.move(source, tmpsource)
    cmd = "pkgbuild --root %s --scripts %s %s"  % \
                                     (os.path.dirname(tmpdir),
                                      scriptsdir,
                                      os.path.join(PROJECT_PATH,
                                                  "dist",
                                                  "PyMca%s.pkg" % version)
                                     )
    os.system(cmd)
    shutil.move(tmpsource, source)
    shutil.rmtree(os.path.dirname(tmpdir))
    shutil.rmtree(scriptsdir)
    # end of generation of .pkg

    # move the generated .app to top level dist for debugging purposes
    target = os.path.join(PROJECT_PATH, "dist", "%s%s.app" % (program, version))
    if os.path.exists(target):
        shutil.rmtree(target)
    shutil.move(source, target)
else:
    # move generated directory to top level dist
    program = "PyMca"
    version = PyMca5.version()
    source = os.path.join(DISTDIR, script_n[0])
    dist = os.path.join(PROJECT_PATH, "dist",)
    if not os.path.exists(dist):
        os.mkdir(dist)
    target = os.path.join(dist, "%s%s" % (program, version))
    if os.path.exists(target):
        print("Removing target")
        shutil.rmtree(target)
    shutil.move(source, target)
    frozenDir = target

    #  generation of the NSIS executable
    # nsis = os.path.join(r"\Program Files (x86)", "NSIS", "makensis.exe")
    # if sys.platform.startswith("win") and os.path.exists(nsis):
    nsis = shutil.which("makensis")
    if sys.platform.startswith("win") and shutil.which("makensis"):
        print('_ _ _ start NSIS _ _ _')
        # check if we can perform the packaging
        outFile = os.path.join(SPECPATH, "nsisscript.nsi")
        f = open(os.path.join(SPECPATH,"nsisscript.nsi.in"), "r")
        content = f.readlines()
        f.close()
        if os.path.exists(outFile):
            os.remove(outFile)
        pymcaexe = os.path.join(PROJECT_PATH, "dist", "%s%s-win64.exe" % (program.lower(), version))
        if os.path.exists(pymcaexe):
            os.remove(pymcaexe)
        pymcalicense = os.path.join(SPECPATH, "PyMca.txt")
        f = open(outFile, "w")
        for line in content:
            if "__LICENSE_FILE__" in line:
                line = line.replace("__LICENSE_FILE__", pymcalicense)
            if "__VERSION__" in line:
                line = line.replace("__VERSION__", version)
            if "__PROGRAM__" in line:
                line = line.replace("__PROGRAM__", program)
            if "__OUTFILE__" in line:
                line = line.replace("__OUTFILE__", pymcaexe)
            if "__SOURCE_DIRECTORY__" in line:
                line = line.replace("__SOURCE_DIRECTORY__", frozenDir)
            if "__ICON_PATH__" in line:
                line = line.replace("__ICON_PATH__", icon)
            f.write(line)
        f.close()
        cmd = '"%s" %s' % (nsis, outFile)
        logger.info("Issuing NSIS command <%s>" % cmd)
        os.system(cmd)

# cleanup intermediate files
for dname in ["build", "dist", "__pycache__"]:
    ddir = os.path.join(SPECPATH, dname)
    if os.path.exists(ddir):
        shutil.rmtree(ddir)

for ddir in [DISTDIR, BUILDDIR]:
    if os.path.exists(ddir):
        shutil.rmtree(ddir)
        if os.path.basename(ddir) == "pyinstaller":
            if os.path.basename(os.path.dirname(ddir)).startswith("build"):
                if os.path.isdir(os.path.dirname(ddir)):
                    shutil.rmtree(os.path.dirname(ddir))

