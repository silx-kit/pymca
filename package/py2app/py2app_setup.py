#
# These Python modules have been developed by V.A. Sole, from the European
# Synchrotron Radiation Facility (ESRF) to build a frozen version of PyMca.
# Given the nature of this work, these module can be considered public domain.
# Therefore redistribution and use in source and binary forms, with or without
# modification, are permitted provided the following disclaimer is accepted:
#
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR(S) AND THE ESRF ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE AUTHOR(S) AND/OR THE ESRF BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
"""
Script for building the PyMca bundle.
For a distributable application Platypus is needed

Usage:
    python py2app_setup.py py2app
"""
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import py2app
import os
import sys

#force a clean build
os.system("/bin/rm -rf dist")
os.system("/bin/rm -rf build")
os.system("/bin/rm -rf *.pyc")

BUNDLE_ICON = os.path.join(os.path.abspath('icons'), 'PyMca.icns')

#obtain the current PyMca version from the source file
ffile = open(os.path.join('src', 'PyMca5', '__init__.py'), 'r').readlines()
for line in ffile:
    if line.startswith('__version__'):
        #remove spaces and split
        __version__ = "%s" % line.replace(' ','').split("=")[-1][:-1]
        #remove " or ' present
        __version__ = __version__[1:-1]
        break

PyMcaInstallationDir = os.path.abspath("build")
PyMcaDir = os.path.join(PyMcaInstallationDir, "PyMca5")
#make sure PyMca is freshly built
cmd = "setup.py install --distutils --install-lib %s --install-data %s --install-scripts /tmp/scripts" % \
                          (PyMcaInstallationDir, PyMcaInstallationDir)
cmd = sys.executable + " " + cmd
if os.system(cmd):
    print("Error building PyMca")
    sys.exit(1)

# awful workaround because py2app picks PyMca form the source directory
os.chdir(PyMcaInstallationDir)
sys.path.insert(0, PyMcaInstallationDir)
pymcapath = PyMcaDir
application=os.path.join(pymcapath, 'PyMcaGui','pymca', "PyMcaMain.py")

#The options below are equivalent to running from the command line
#python py2app_setup.py py2app --packages=matplotlib,ctypes,h5py,Object3D
#probably matplotlib and PyOpenGL are properly detected by py2app
PACKAGES = ['fisx', 'OpenGL','ctypes','matplotlib', 'h5py','hdf5plugin','logging', 'PyMca5']
PACKAGES.append("PyQt5")

import silx
PACKAGES.append("silx")
SILX = True

try:
   import IPython
   import pygments
   PACKAGES.append("IPython")
   PACKAGES.append("pygments")
except:
   pass

try:
    import fabio
    PACKAGES.append("fabio")
except:
    pass

try:
    import mdp
    PACKAGES.append('mdp')
except:
    pass
try:
    import pyopencl
    PACKAGES.append('pyopencl')
    PYOPENCL = True
except:
    PYOPENCL = False

try:
    import tomogui
    PACKAGES.append('tomogui')
    try:
       import freeart
       PACKAGES.append('freeart')
    except:
       pass
except:
    pass

PY2APP_OPTIONS = {'packages':PACKAGES}
if "PyQt5" in PACKAGES:
    PY2APP_OPTIONS['qt_plugins'] = ["cocoa"]

if os.path.exists(BUNDLE_ICON):
    PY2APP_OPTIONS['iconfile'] = BUNDLE_ICON
else:
    BUNDLE_ICON = None
PY2APP_OPTIONS["excludes"] = ["scipy"]

if sys.version.startswith("2"):
    PY2APP_OPTIONS["excludes"].append("PyQt4.uic.port_v3")
    PY2APP_OPTIONS["excludes"].append("PyQt5.uic.port_v3")

setup(
    app=[application],
    options={'py2app':PY2APP_OPTIONS}
)

# move to the proper place
os.system("mv -f ./dist ../dist")
os.chdir(os.path.dirname(PyMcaInstallationDir))

# patch problematic modules
patching_dir = os.path.join(os.getcwd(),
                    "dist/PyMcaMain.app/Contents/Resources/lib/python%s/" % \
                            sys.version[:3])
if SILX:
    # silx gui._qt module needs to be patched to get rid of uic
    initFile = os.path.join(patching_dir, "silx", "gui", "qt", "_qt.py")
    print("###################################################################")
    print("Patching silx file")
    print(initFile)
    print("###################################################################")
    f = open(initFile, "r")
    content = f.readlines()
    f.close()
    f = open(initFile, "w")
    for line in content:
        if ("PyQt4.uic" in line) or ("PyQt5.uic" in line):
            continue
        f.write(line)
    f.close()

if PYOPENCL:
    # pyopencl __init__.py needs to be patched
    initFile = os.path.join(patching_dir, "pyopencl", "__init__.py")
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

#Command line call to Platypus ...
platypusFile = '/usr/local/bin/platypus'
if os.path.exists(platypusFile):
    import subprocess
    args = [platypusFile,
            '-R',
            '-a',
            'PyMca%s' % __version__,
            '-o',
            'Progress Bar',
            '-p',
            '/bin/bash',
            '-V',
            '%s' % __version__,
            '-I',
            'ESRF.sole.PyMca%s' % __version__,
            '-y', #force overwrite
            '-f',
            os.path.join(os.getcwd(),'dist', 'PyMcaMain.app')]
    if BUNDLE_ICON is not None:
        args.append('-i')
        args.append(BUNDLE_ICON)
    args.append(os.path.join(os.getcwd(), 'PlatypusScript'))
    process = subprocess.call(args)
    py2app_bundle = os.path.join(os.getcwd(), 'PyMca%s.app' % __version__, "Contents", "Resources", "PyMcaMain.app")
    if not os.path.exists(py2app_bundle):
        print("Forcing copy")
        os.system("cp -R ./dist/PyMcaMain.app "+ os.path.dirname(py2app_bundle)) 
