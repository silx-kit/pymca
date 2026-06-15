# /*#########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2019 European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF by the Software group.
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
__author__ = "T. Vincent - ESRF Data Analysis"
__contact__ = "thomas.vincent@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__doc__ = """
This module provides a PyMca plugin allowing to either download or receive
`JSON-RPC 2.0 <http://www.jsonrpc.org/specification>`_ requests that are
interpreted as commands for the 1D plot window.

Two modes are supported:

- *A client mode*, where the plugin downloads JSON-RPC files.
  In this mode, it is possible to download files from a given URL
  either on demand or at regular intervals (i.e., polling).
- *A server mode*, where the plugin is a TCP server that parses incoming data
  as JSON-RPC files.

As is, only :meth:`Plugin1DBase.addCurve` is available through RPC, but
more methods can be supported by populating the ``_handlers`` attribute of
:class:`PyMcaJsonRpc1DPlugin`.

Remote code in either server or client mode can use the
:func:`addCurveToJsonRpc` that has the same signature as
:meth:`Plugin1DBase.addCurve` and returns the corresponding JSON-RPC string
that can be interpreted by the plugin.
"""


# import ######################################################################

import json
import sys
import numpy as np

from urllib.request import urlopen
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import StreamRequestHandler, TCPServer

from PyMca5.PyMcaCore import Plugin1DBase
from PyMca5.PyMcaGui import PyMcaQt as qt


# JSON-RPC ####################################################################
# Light implementation of JSON-RPC 2.0 : http://www.jsonrpc.org/specification

_PARSE_ERROR = -32700
_INVALID_REQUEST = -32600
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602
_INTERNAL_ERROR = -32603
_SERVER_ERROR = -32000

_ERRORS = {
    _PARSE_ERROR: 'Parse Error',
    _INVALID_REQUEST: 'Invalid Request',
    _METHOD_NOT_FOUND: 'Method Not Found',
    _INVALID_PARAMS: 'Invalid Parameters',
    _INTERNAL_ERROR: 'Internal Error',
    _SERVER_ERROR: 'Server Error',
}


def _jsonRpcError(code, data=None):
    assert code in _ERRORS
    return {'code': code, 'message': _ERRORS[code], 'data': data}


def jsonRpcProcessRequest(requestFileObj, handlers):
    """Parse a single JSON-RPC request and call the associated handler function

    Limitations: Do not support batch, not checking parameters

    :param requestFileObj: JSON-RPC request document
    :type requestFileObj: A .read()-supporting file-like object
    :param dict handlers: RPC method handlers: {method name: handler function}
    :returns: The JSON-RPC reply or None if request was a notification
    :rtype: str
    """
    try:
        request = json.load(requestFileObj)
    except ValueError:
        return {'jsonrpc': '2.0',
                'id': None,
                'error': _jsonRpcError(_PARSE_ERROR)}

    try:
        reply = {'jsonrpc': '2.0', 'id': request['id']}
    except KeyError:
        reply = None

    try:
        methodName = request['method']
    except KeyError:
        if reply is not None:
            reply['error'] = _jsonRpcError(_INVALID_REQUEST,
                                           'Request has no method name')
        return reply

    try:
        method = handlers[methodName]
    except KeyError:
        if reply is not None:
            data = 'Unknown method: {}'.format(methodName)
            reply['error'] = _jsonRpcError(_METHOD_NOT_FOUND, data)
        return reply

    params = request.get('params', {})

    # Convert list to np.array
    if isinstance(params, dict):
        for key in params:
            value = params[key]
            if isinstance(value, list):
                params[key] = np.array(value)
    else:
        params = [np.array(v) if isinstance(v, list) else v for v in params]

    try:
        if isinstance(params, dict):
            result = method(**params)
        else:
            result = method(*params)
    except Exception as exception:
        if reply is not None:
            if isinstance(exception, TypeError):
                reply['error'] = _jsonRpcError(_INVALID_PARAMS,
                                               params)
            else:
                reply['error'] = _jsonRpcError(_SERVER_ERROR,
                                               (exception.errno,
                                                exception.strerror))
        return reply

    if reply is not None:
        reply['result'] = result
        reply = json.dumps(reply)

    return reply


# dialog box ##################################################################

class _DialogBox(qt.QDialog):
    LOAD = "Load"
    START_POLL = "Start Polling"
    STOP_POLL = "Stop Polling"
    START_SERVER = "Start Server"
    STOP_SERVER = "Stop Server"

    def __init__(self, parent, plugin):
        self._plugin = plugin

        qt.QDialog.__init__(self, parent)
        self.setWindowTitle('JSON-RPC Plugin')

        # Poll GUI
        pollLayout = qt.QFormLayout()
        pollGroup = qt.QGroupBox()
        pollGroup.setTitle('Client mode (Polling)')
        pollGroup.setLayout(pollLayout)

        pollUrlLabel = qt.QLabel("URL:")
        pollUrlLabel.setToolTip(
            "The URL to download JSON-RPC file from\n" +
            "Supported protocols: http:, ftp: file:")
        self.pollUrlLineEdit = qt.QLineEdit(self._plugin.pollUrl)
        pollLayout.addRow(pollUrlLabel, self.pollUrlLineEdit)

        pollTimeoutLabel = qt.QLabel("Timeout (s):")
        pollTimeoutLabel.setToolTip(
            "The interval in seconds at which the plugin is polling the URL")
        self.pollTimeoutLineEdit = qt.QLineEdit(str(self._plugin.pollTimeout))
        # Bounds timeout to avoid to small timeout
        self.pollTimeoutLineEdit.setValidator(
            qt.CLocaleQDoubleValidator(0.02, 1000.0, 2))
        pollLayout.addRow(pollTimeoutLabel, self.pollTimeoutLineEdit)

        self.pollLoadBtn = qt.QPushButton(self.LOAD)
        pollLayout.addRow(self.pollLoadBtn)

        if self._plugin.isPollRunning():
            pollBtnText = self.STOP_POLL
        else:
            pollBtnText = self.START_POLL
        self.pollBtn = qt.QPushButton(pollBtnText)
        pollLayout.addRow(self.pollBtn)

        # Server GUI
        serverLayout = qt.QFormLayout()
        serverGroup = qt.QGroupBox()
        serverGroup.setTitle('TCP Server mode')
        serverGroup.setLayout(serverLayout)

        serverPortLabel = qt.QLabel("TCP Port:")
        serverPortLabel.setToolTip(
            "The TCP port the server is listening to.\n" +
            "Ranging in [1024-65535]")
        self.serverPortLineEdit = qt.QLineEdit(str(self._plugin.serverPort))
        # Bounds port to 'user' ports
        self.serverPortLineEdit.setValidator(qt.QIntValidator(1024, 65535))
        serverLayout.addRow(serverPortLabel, self.serverPortLineEdit)

        if self._plugin.isServerRunning():
            serverBtnText = self.STOP_SERVER
        else:
            serverBtnText = self.START_SERVER
        self.serverBtn = qt.QPushButton(serverBtnText)
        serverLayout.addRow(self.serverBtn)

        # Main layout
        closeBtn = qt.QPushButton('Close')

        mainLayout = qt.QVBoxLayout()
        mainLayout.addWidget(pollGroup)
        mainLayout.addWidget(serverGroup)
        mainLayout.addWidget(closeBtn)

        self.setLayout(mainLayout)

        # Signals
        self.pollTimeoutLineEdit.editingFinished.connect(self.pollTimeoutCB)
        self.pollUrlLineEdit.editingFinished.connect(self.pollUrlCB)
        self.serverPortLineEdit.editingFinished.connect(self.serverPortCB)

        self.pollLoadBtn.clicked.connect(self.pollLoadBtnCB)
        self.pollBtn.clicked.connect(self.pollBtnCB)
        self.serverBtn.clicked.connect(self.serverBtnCB)
        closeBtn.clicked.connect(self.accept)

    def pollTimeoutCB(self):
        self._plugin.pollTimeout = float(self.pollTimeoutLineEdit.text())

    def pollUrlCB(self):
        self._plugin.pollUrl = self.pollUrlLineEdit.text()

    def serverPortCB(self):
        self._plugin.serverPort = int(self.serverPortLineEdit.text())

    def pollLoadBtnCB(self):
        self._plugin.load()

    def pollBtnCB(self):
        if self.pollBtn.text() == self.START_POLL:
            self._plugin.startPoll()
        else:
            self._plugin.stopPoll()

        if self._plugin.isPollRunning():
            pollBtnText = self.STOP_POLL
        else:
            pollBtnText = self.START_POLL
        self.pollBtn.setText(pollBtnText)

    def serverBtnCB(self):
        if self.serverBtn.text() == self.START_SERVER:
            self._plugin.startTcpServer()
        else:
            self._plugin.stopTcpServer()

        if self._plugin.isServerRunning():
            serverBtnText = self.STOP_SERVER
        else:
            serverBtnText = self.START_SERVER
        self.serverBtn.setText(serverBtnText)


# plugin ######################################################################

class PyMcaJsonRpc1DPlugin(Plugin1DBase.Plugin1DBase):
    def __init__(self, *args, **kwargs):
        super(PyMcaJsonRpc1DPlugin, self).__init__(*args, **kwargs)
        self._handlers = {
            'addCurve': self.addCurve,
        }

        # Parameters used by poll and server
        self.pollTimeout = 1.
        self.pollUrl = ''
        self.serverPort = 8000
        self._serverTimeout = 0.1

    def __del__(self):
        self.stopPoll()
        self.stopTcpServer()

    def getMethods(self, plottype=None):
        return ("JSON-RPC",)

    def getMethodToolTip(self, methodName):
        return "Allow to control the plot through JSON-RPC"

    def applyMethod(self, methodName):
        dialogBox = _DialogBox(None, self)
        dialogBox.exec()

    def load(self):
        try:
            fileObj = urlopen(self.pollUrl)
        except ValueError:
            print('PyMcaJsonRpc1DPlugin.load: Bad URL:', self.pollUrl)
            return False
        else:
            jsonRpcProcessRequest(fileObj, self._handlers)
            fileObj.close()
            return True

    def startPoll(self):
        self.stopPoll()

        # Load file once to check if URL is correct
        if not self.load():
            return False
        else:
            self._pollTimer = qt.QTimer()
            self._pollTimer.timeout.connect(self.load)
            self._pollTimer.start(1000. * self.pollTimeout)
            return True

    def stopPoll(self):
        if hasattr(self, '_pollTimer'):
            self._pollTimer.stop()
            del self._pollTimer

    def isPollRunning(self):
        return hasattr(self, '_pollTimer')

    def startTcpServer(self):
        self.stopTcpServer()

        handlers = self._handlers

        class RequestHandler(StreamRequestHandler):
            def handle(self):
                reply = jsonRpcProcessRequest(self.rfile, handlers)
                if reply is not None:
                    self.wfile.write(reply)

        self._server = TCPServer(('', self.serverPort), RequestHandler,
                                 bind_and_activate=False)
        self._server.allow_reuse_address = True
        self._server.timeout = 0.01
        self._server.server_bind()
        self._server.server_activate()

        # Should do it differently
        self._serverTimer = qt.QTimer()
        self._serverTimer.timeout.connect(self._server.handle_request)
        self._serverTimer.start(1000. * self._serverTimeout)

    def stopTcpServer(self):
        if hasattr(self, '_serverTimer'):
            self._serverTimer.stop()
            del self._serverTimer
        if hasattr(self, '_server'):
            del self._server

    def isServerRunning(self):
        return hasattr(self, '_server')


MENU_TEXT = "JSON-RPC"


def getPlugin1DInstance(plotWindow, **kwargs):
    return PyMcaJsonRpc1DPlugin(plotWindow)


# helper ######################################################################

def addCurveToJsonRpc(x, y, legend=None, info=None,
                      replace=False, replot=True, **kw):
    """Generate a JSON-RPC request for calling :meth:`Plugin1DBase.addCurve`
    on a :class:`PyMcaJsonRpc1DPlugin` plugin.

    See :class:`Plugin1DBase` for details.

    :returns: A JSON-RPC request corresponding to the addCurve call
    :rtype: str
    """
    if not isinstance(x, (list, tuple)):
        x = tuple(x)
    if not isinstance(y, (list, tuple)):
        y = tuple(y)

    params = {
        "info": info,
        "x": x,
        "y": y,
        "legend": legend,
        "replace": replace,
        "replot": replot
    }
    params.update(kw)

    request = {
        "jsonrpc": "2.0",
        "method": "addCurve",
        "params": params
    }
    return json.dumps(request)


# demo polling ################################################################

def _testServer(address):
    # Create a test http server
    class TestRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            request = addCurveToJsonRpc(
                np.arange(100.),
                np.random.random(100) * 10,
                legend="test {:.2f}".format(time.time()),
                replace=True,
                replot=True)
            self.wfile.write(request)

    return HTTPServer(address, TestRequestHandler)


class _DemoClientModeAuto(object):
    def __init__(self, plugin, onFinish):
        self._plugin = plugin
        self._onFinish = onFinish

    def start(self):
        import threading

        # Start server in a thread
        self._httpdServer = _testServer(('localhost', 8000))
        self._httpdThread = threading.Thread(
            target=self._httpdServer.serve_forever)
        self._httpdThread.start()

        # Set-up URL to download
        self._plugin.pollUrl = 'http://localhost:8000'

        print("Load JSON from server once")
        self._plugin.load()

        qt.QTimer.singleShot(2000., self._startPoll)

    def _startPoll(self):
        print("Start polling JSON from server")
        self._plugin.startPoll()
        qt.QTimer.singleShot(5000., self._stopPoll)

    def _stopPoll(self):
        print("Stop polling JSON from server")
        self._plugin.stopPoll()
        self._httpdServer.shutdown()
        self._httpdServer.socket.close()

        self._onFinish()


# demo server mode ############################################################

def _sendJsonRpcAddCurve(address):
    import socket

    request = addCurveToJsonRpc(
        np.arange(100.),
        np.random.random(100) * 10,
        legend="test {:.2f}".format(time.time()),
        replace=True,
        replot=True
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(address)
    sock.send(request)
    sock.close()


class _DemoServerModeAuto(object):
    def __init__(self, plugin, onFinish):
        self._plugin = plugin
        self._onFinish = onFinish

    def start(self):
        import threading

        print("Start TCP server")
        self._plugin.startTcpServer()

        print("Start sending JSON-RPC through TCP")
        self._isSending = True
        self._senderThread = threading.Thread(target=self._sender)
        self._senderThread.start()

        qt.QTimer.singleShot(5000., self._stop)

    def _sender(self):
        while self._isSending:
            _sendJsonRpcAddCurve(('localhost', 8000))
            time.sleep(1)
        print("Stop sending JSON-RPC through TCP")

    def _stop(self):
        self._isSending = False
        self._senderThread.join()

        print('Stop server')
        self._plugin.stopTcpServer()

        self._onFinish()


# main ########################################################################

if __name__ == "__main__":
    import time
    import sys
    import os.path
    from PyMca5.PyMcaGui.plotting.PlotWindow import PlotWindow

    if len(sys.argv) == 1 or \
       sys.argv[1] not in ('plugin', 'demoServer', 'demoClient', 'auto'):
        print("""
Options: plugin, demoServer demoClient, auto

- plugin: Start a 1D plot window with JSPON-RPC plugin available
- demoServer: HTTP server, to load JSON-RPC from URL: http://localhost:8000
- demoClient: TCP client that sends JSPN-RPC to localhost:8000
- auto: Starts demo of polling and server that runs alone

""")
        sys.exit()

    if sys.argv[1] in ('plugin', 'auto'):
        # Create Qt main application
        app = qt.QApplication([])

        # Create plot window
        plot = PlotWindow(roi=True)
        plot.show()

        # Load plugin
        pluginDir = os.path.dirname(os.path.abspath(__file__))
        pluginName = os.path.splitext(os.path.basename(__file__))[0]

        plot.setPluginDirectoryList([pluginDir])
        nbPlugins = plot.getPlugins()  # Update plug-in list
        assert nbPlugins >= 1
        plugin = plot.pluginInstanceDict[pluginName]

        if sys.argv[1] == 'auto':
            # Run automated demos
            serverDemo = _DemoServerModeAuto(plugin, onFinish=app.quit)
            clientDemo = _DemoClientModeAuto(plugin, onFinish=serverDemo.start)
            clientDemo.start()

        app.exec()

    elif sys.argv[1] == 'demoServer':
        httpdServer = _testServer(('localhost', 8000))
        httpdServer.serve_forever()

    elif sys.argv[1] == 'demoClient':
        while True:
            _sendJsonRpcAddCurve(('localhost', 8000))
            time.sleep(1)
