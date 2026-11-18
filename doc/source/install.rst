
Installation steps
==================

*PyMca* supports most operating systems and different version of the Python programming language.

It can be installed as a stand alone application or as a Python module. The later offer a greater flexibility besides the possibility to
make use of different features of *PyMca* in your own Python programs.

Stand-alone Executable
----------------------

Stand-alone applications (aka. frozen binaries) are supplied for Windows and MacOS and can be downloaded from `here <https://sourceforge.net/projects/pymca/files/pymca/>`_. Just download the installer for your platform.

On Windows, the Microsoft Visual C++ Redistributable needs to be installed for using the PyMca frozen binary. It is likely that you already have it installed, but in case the application crashes at startup, please make sure it is installed.
The installer can be downloaded from the `Microsoft website <https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist>`_. There are no additional dependencies on macOS.


Python module
-------------

The best use of PyMca can be achieved installing PyMca as a python package inside an existing Python installation. For Windows and MacOS there are pre-compiled modules available in order to simplify the task.

This table summarized the the support matrix of PyMca:

+------------+--------------+---------------------+
| System     | Python vers. | Qt and its bindings |
+------------+--------------+---------------------+
| `Windows`_ | 2.7, 3.5-3.6 | PyQt4.8+, PyQt5.3+  |
+------------+--------------+---------------------+
| `MacOS`_   | 2.7, 3.5-3.6 | PyQt4.8+, PyQt5.3+  |
+------------+--------------+---------------------+
| `Linux`_   | 2.7, 3.4-3.6 | PyQt4.8+, PyQt5.3+  |
+------------+--------------+---------------------+

For all platforms, you can install *PyMca5* from the source, see `Installing from source`_.


Installing Python
+++++++++++++++++

You can skip this section if you already have a properly configured Python installation.

Windows
.......

Download and install `Python <https://www.python.org/downloads/windows/>`_.

We recommend that you install the 64bits version of Python, which is not the
default version suggested on the Python website.
The 32bits version is limited to 2 GB of memory, and also we don't provide a
binary wheel for it what means that you would have to install *PyMca5* from its sources, which requires you to install a C compiler first.

We also encourage you to use Python 3.5 or newer, former versions are no more
officially supported.

Configure Python as explained on
`docs.python.org <https://docs.python.org/3/using/windows.html#configuring-python>`_
to add the python installation directory to your PATH environment variable.

You may need to configure your PATH environment variable to include the pip installation directory.

MacOS
.....

Python 2.7 is shipped by default but we recommend using Python 3.5 or newer to simplify the installation of the Qt library.

Download and install Python from `python.org <https://www.python.org/downloads/mac-osx/>`_ or, alternatively, install Python from the `anaconda distribution <https://www.anaconda.com/download/>`_

Open a terminal and type ``which python3`` and ``which pip3``. Those commands should give you back the location of the respective scripts if you have properly installed python.

Linux
.....

For Linux please refer to the relevant documentation of your linux distribution.


Installing PyMca
++++++++++++++++

This assumes you have Python and pip installed and configured. If you don't, read the previous sections.

For MacOS and Windows this should work without issues, as binary wheels of *PyMca* are provided on PyPI.

.. _Windows:

Windows
.......

The simple way of installing *PyMca*  on Windows is to type the following
commands in a command prompt:

.. code-block:: bash

    pip install PyMca5

That install *PyMca* for command line use but all dependencies may be simply installed with pip.

A convenient set of dependencies can be installed with:

.. code-block:: bash 

    pip install -r https://raw.githubusercontent.com/vasole/pymca/master/requirements.txt

.. note::
    
    Detailed instructions on how to install dependencies are given in the
    `Installing dependencies`_ section.


.. _MacOS:

MacOS
.....


It is exactly like with windows, perhaps you may need to replace pip by pip3 as follows:

.. code-block:: bash 

    pip uninstall pymca
    pip uninstall PyMca5
    pip install pymca

or 

.. code-block:: bash 

    pip3 uninstall pymca
    pip3 uninstall PyMca5
    pip3 install PyMca5

A convenient set of dependencies can be installed with:

.. code-block:: bash 

    pip3 install -r https://raw.githubusercontent.com/vasole/pymca/master/requirements.txt

.. note::
    
    Detailed instructions on how to install dependencies are given in the
    `Installing dependencies`_ section.

.. _Linux:

Linux
.....

There are no frozen binaries or wheels available for linux. Nevertheless, there are strong chances that *PyMca*  is available as a native package for your distribution. 

If you need to build *PyMca* from its source code, and NumPy and fisx are not installed on your system, you need to install them first, preferably with the package manager of your system. If you cannot use the package manager of your system (which requires the root access), please refer to the Virtual Environment procedure explained in the `silx documentation <http://www.silx.org/doc/silx/latest/install.html>`_

Please refer to `Installing from source`_

.. note::

    The Debian packages `python-pymca5` and `python3-pymca5` will not install executables 
    (`pymca`, `pymcaroitool` ...). Please install the pymca package.


You can also install PyMca from its source code. While `numpy <http://www.numpy.org/>`_ and `fisx <https://github.com/vasole/fisx>`_ are the only mandatory dependencies for command line usage,
graphical widgets require Qt and `matplotlib <http://matplotlib.org/>`_ and management of HDF5 data files requires
`h5py <http://docs.h5py.org/en/latest/build.html>`_.

.. _Installing from source:

Installing from source
----------------------

To build *PyMca* from source requires the use of compiler. While this is not a problem under linux, it can be problematic for Windows or MacOS users. The installation of Visual Studio under windows or XCode under MacOS is beyond the purpose of this tutorial. Please refer to appropriate documentation sources.

Build dependencies
++++++++++++++++++

In addition to run-time dependencies, building *PyMca* requires a C/C++ compiler, `numpy <http://www.numpy.org/>`_ and `cython <http://cython.org>`_ (optional).

This project uses Cython (version > 0.21) to generate C files.
Cython is now mandatory to build *PyMca* from the development branch and is only
needed when compiling binary modules.

Building *PyMca* from the source requires NumPy and fisx installed that can be installed using:

.. code-block:: bash 

    pip install numpy
    pip install fisx


Building from source
++++++++++++++++++++

The most straightforward way is to use pip to take the sources from PyPI:

.. code-block:: bash

    pip install PyMca5 --no-binary [--user]
    

Alternatively, the source package of *PyMca* releases can be downloaded from
`the pypi project page <https://pypi.python.org/pypi/PyMca5>`_.

After downloading the `PyMca5-x.y.z.tar.gz` archive, extract its content:

.. code-block:: bash 

    tar xzvf PyMca5-x.y.z.tar.gz
    cd PyMca5-x.y.z
    pip uninstall -y PyMca5
    pip install . [--user]
    
Alternatively, you can get the latest source code from the master branch of the
`git repository <https://github.com/vasole/pymca/silx/archive/master.zip>`_: https://github.com/vasole/pymca

Known issues
............

There are specific issues related to MacOSX. If you get this error::

  UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3 in position 1335: ordinal not in range(128)

This is related to the two environment variable LC_ALL and LANG not defined (or wrongly defined to UTF-8).
To set the environment variable, type on the command line:

.. code-block:: bash 

    export LC_ALL=en_US.UTF-8
    export LANG=en_US.UTF-8

Advanced build options
++++++++++++++++++++++

In case you want more control over the build procedure, the build command is:

.. code-block:: bash 

    python setup.py build

There are few advanced options to ``setup.py build``:

* ``--no-cython``: Prevent Cython (even if installed) to re-generate the C source code.
  Use the one provided by the development team.

It is recommended to run the test suite of *PyMca* only after installation:

.. code-block:: bash 

    python -m PyMca5.tests.TestAll

Package the built into a wheel and install it:

.. code-block:: bash 

    python setup.py bdist_wheel
    pip install dist/PyMca5*.whl 

To build the documentation, using  `Sphinx <http://www.sphinx-doc.org/>`_:

.. code-block:: bash 

    python setup.py build build_doc

.. _installing dependencies:

Dependencies
++++++++++++

Tools for reading and writing HDF5 files depend on:

* `h5py <http://docs.h5py.org/en/latest/build.html>`_

The GUI widgets depend on the following extra packages:

* A Qt binding: either `PySide6 <https://pypi.org/project/PySide6/>`_,
  `PyQt6 or PyQt5 <https://riverbankcomputing.com/software/pyqt/intro>`_
* `matplotlib <http://matplotlib.org/>`_

The following packages are optional dependencies:

* `silx <https://github.com/silx-kit/silx>`_ for enhanced widgets 
* `qt_console <https://pypi.python.org/pypi/qtconsole>`_ for the interactive console widget.
* `PyOpenGL <http://pyopengl.sourceforge.net/>`_ for 3D and scatter plot visualization

It is expected that h5py and silx become required dependencies within short because:

- h5py will become the preferred input/output file format of PyMca
- silx provides a better widget library than the one currently supplied by PyMca
  
The complete list of dependencies with the minimal version is described in the
`requirements.txt <https://github.com/vasole/pymca/requirements.txt>`_
at the top level of the source package.


Installing *PyMca*
++++++++++++++++++

Provided numpy is installed, you can install *PyMca* with:

.. code-block:: bash 

    pip install pymca

or 

.. code-block:: bash 

    pip install PyMca5

For MacOS and Windows this should work without issues, as binary wheels of *PyMca* are provided on PyPI.

Please remember to replace pip by pip3 if that is what you are using.

All dependencies may be simply installed with pip. Please replace pip by pip3 if that is what you are using:

.. code-block:: bash 

    pip install -r https://raw.githubusercontent.com/vasole/pymca/master/requirements.txt

Conda installation
------------------

*PyMca* can be installed with `conda` from the *conda-forge* repository
for all versions of Anaconda and Miniconda:

To install *PyMca* with all dependencies, including the GUI, use:

.. code-block:: bash

    conda install -c conda-forge pymca silx

If you do not need the GUI, you can simply install it with:

.. code-block:: bash

    conda install -c conda-forge pymca


Testing
-------

To run the tests of an installed version of *PyMca*, from the python interpreter, run:

.. code-block:: python
    
     import PyMca5.tests
     PyMca5.tests.testAll()

To run the test suite from the command line run:

.. code-block:: bash
    
     python -m PyMca5.tests.TestAll

or

.. code-block:: bash
    
     python3 -m PyMca5.tests.TestAll

