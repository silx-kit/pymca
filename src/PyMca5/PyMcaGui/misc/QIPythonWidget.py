#/############################################################################
#
# This module is based on an answer published in:
#
# http://stackoverflow.com/questions/11513132/embedding-ipython-qt-console-in-a-pyqt-application
#
# by Tim Rae
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
__author__ = "Tim Rae, V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import os
import sys

from PyMca5.PyMcaGui.PyMcaQt import QApplication, QWidget, \
                                    QPushButton, QVBoxLayout, QMessageBox, \
                                    BINDING

QTCONSOLE = True
try:
    import qtconsole
except ImportError:
    QTCONSOLE = False
    import IPython

if QTCONSOLE:
    try:
        from qtconsole.rich_ipython_widget import RichJupyterWidget as RichIPythonWidget
    except Exception:
        from qtconsole.rich_ipython_widget import RichIPythonWidget
    from qtconsole.inprocess import QtInProcessKernelManager
else:
    # Import the console machinery from ipython
    # Check if we using a frozen version because
    # the test of IPython does not find the Qt bindings
    executables = ["PyMcaMain.exe", "QStackWidget.exe", "PyMcaPostBatch.exe"]
    if os.path.basename(sys.executable) in executables:
        import IPython.external.qt_loaders
        def has_binding(*var, **kw):
            return True
        IPython.external.qt_loaders.has_binding = has_binding 
    from IPython.qt.console.rich_ipython_widget import RichIPythonWidget
    from IPython.qt.inprocess import QtInProcessKernelManager

class QIPythonWidget(RichIPythonWidget):
    """ Convenience class for a live IPython console widget. We can replace the standard banner using the customBanner argument"""
    def __init__(self,customBanner=None,*args,**kwargs):
        super(QIPythonWidget, self).__init__(*args,**kwargs)
        if customBanner != None:
            self.banner = customBanner
        self.setWindowTitle(self.banner)
        self.kernel_manager = kernel_manager = QtInProcessKernelManager()
        kernel_manager.start_kernel()
        try:
            # https://github.com/ipython/ipykernel/issues/370
            from ipykernel import version_info
            if version_info < (5, 1, 1):
                def _abort_queues(kernel):
                    pass
                kernel_manager.kernel._abort_queues = _abort_queues
        except Exception:
            pass
        if BINDING in ["PySide", "PyQt4"]:
            kernel_manager.kernel.gui = 'qt4'
        self.kernel_client = kernel_client = self._kernel_manager.client()
        kernel_client.start_channels()

        def stop():
            #clear workspace
            msg = QMessageBox(self)
            msg.setWindowTitle("Console cleanup")
            msg.setText("Do you want to clean the console workspace?")
            msg.setStandardButtons(QMessageBox.No | QMessageBox.Yes)
            msg.setDefaultButton(QMessageBox.Yes)
            ret = msg.exec()
            try:
                if ret == QMessageBox.Yes:
                    self.kernel_manager.kernel.shell.magic('reset -sf')
                    kernel_client.stop_channels()
                    kernel_manager.shutdown_kernel()
            except Exception:
                print("Error cleaning console variables")
                kernel_client.stop_channels()
                kernel_manager.shutdown_kernel()
            # close widget instead of quitting application
            self.close()
        self.exit_requested.connect(stop)

    def pushVariables(self,variableDict):
        """ Given a dictionary containing name / value pairs, push those variables to the IPython console widget """
        self.kernel_manager.kernel.shell.push(variableDict)
    def clearTerminal(self):
        """ Clears the terminal """
        self._control.clear()
    def printText(self,text):
        """ Prints some plain text to the console """
        self._append_plain_text(text)
    def executeCommand(self,command):
        """ Execute a command in the frame of the console widget """
        self._execute(command,False)

    def show(self):
        if self.kernel_manager.kernel is None:
            # we need to restart the kernel
            self.kernel_manager.start_kernel()
            self.kernel_client.start_channels()
        return RichIPythonWidget.show(self)

class ExampleWidget(QWidget):
    """ Main GUI Widget including a button and IPython Console widget inside vertical layout """
    def __init__(self, parent=None):
        super(ExampleWidget, self).__init__(parent)
        layout = QVBoxLayout(self)
        self.button = QPushButton('Another widget')
        ipyConsole = QIPythonWidget(customBanner="Welcome to the embedded ipython console\n")
        layout.addWidget(self.button)
        layout.addWidget(ipyConsole)
        # This allows the variable foo and method print_process_id to be accessed from the ipython console
        ipyConsole.pushVariables({"foo":43,"print_process_id":print_process_id})
        ipyConsole.printText("The variable 'foo' and the method 'print_process_id()' are available. Use the 'whos' command for information.")

def print_process_id():
    print('Process ID is:', os.getpid())

def main():
    app  = QApplication([])
    widget = ExampleWidget()
    widget.show()
    app.exec()

if __name__ == '__main__':
    main()

