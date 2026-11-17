PyMca
=====

This is the MIT version of the PyMca XRF Toolkit. Please read the
`LICENSE <./LICENSE>`_ file for details.

Installation
------------

Ready-to-use packages are available for the most common platforms.

PyMca frozen binaries for MacOS and Windows can be obtained from
`Sourceforge <https://sourceforge.net/projects/pymca/files/pymca>`_

Official packages are available for common Linux distributions.

Please continue reading if you want to use PyMca with your existing
Python installation.

The simplest solution is to use ``pip``:

.. code:: bash

   pip install PyMca5

You can add the usual ``--user`` qualifier to install only for your
local user rather than system-wide:

.. code:: bash

   pip install PyMca5 --user

If you want to build from the source distribution or from a git
repository checkout, you may want to have Cython installed on your
system.

Examples of source installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. In your default system-wide python installation, run one or the other
   of the two (not both) commands below (may require root/administrator
   access):

   .. code:: bash

      # Run one of the following (not both); pip is preferred
      python setup.py install    # use python setuptools
      pip install .              # use the pip package manager

2. Or, to install just in your local user account:

   .. code:: bash

      # Run one of the following (not both); pip is preferred
      python setup.py install --user   # use python setuptool
      pip install . --user               # use the pip package manager

You will need the following dependencies installed:

-  `python <https://www.python.org/>`_ (3.10 or higher)
-  `numpy <https://www.numpy.org/>`_
-  `fisx <https://github.com/vasole/fisx>`_
-  `h5py <https://github.com/h5py/h5py>`_

If you want to use the graphical interface provided, you will need a
running python installation with one of the following combinations:

-  ``PyQt5`` + ``matplotlib`` (PyMca license will be
   `GPL <https://www.gnu.org/licenses/gpl-3.0.en.html>`_ unless you
   have a commercial PyQt5 license)
-  ``PyQt6`` + ``matplotlib`` (PyMca license will be
   `GPL <https://www.gnu.org/licenses/gpl-3.0.en.html>`_ unless you
   have a commercial PyQt6 license)
-  ``PySide6`` + ``matplotlib`` (PyMca license will be
   `MIT <https://tldrlegal.com/license/mit-license>`_ because PySide6 is
   `LGPL <https://www.gnu.org/licenses/lgpl-3.0.en.html>`_)

If you want to embed ``PyMca`` in your own graphical applications, I
recommend you to use the
`McaAdvancedFit.py <PyMca5/PyMcaGui/physics/xrf/McaAdvancedFit.py>`_
module. It is very easy to embed.

Testing
-------

To run the tests **after installation** run::

    python -m PyMca5.tests.TestAll

Development Plans
-----------------

-  Use the ``fisx`` library for all Physics calculations and not just
   for corrections.
-  Compound fitting.

If you have any questions or comments (or contributions!), please feel
free to contact me or submit a pull request.

Enjoy,

\V. Armando Sole
