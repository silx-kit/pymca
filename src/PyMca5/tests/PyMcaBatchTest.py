#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2019 European Synchrotron Radiation Facility
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
#############################################################################*/
__author__ = "Wout De Nolf"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import unittest
import sys
import os
import numpy
from random import randint
import tempfile
import shutil
from glob import glob
import logging
from PyMca5.tests import XrfData
import PyMca5.PyMcaGui.PyMcaQt as qt
from PyMca5.PyMcaGui.misc.testutils import TestCaseQt
try:
    import h5py
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False


_logger = logging.getLogger(__name__)


class testPyMcaBatch(TestCaseQt):

    _rtolLegacy = 1e-5

    def setUp(self):
        self.path = tempfile.mkdtemp(prefix='pymca')
        super(testPyMcaBatch, self).setUp()

    def tearDown(self):
        shutil.rmtree(self.path)
        from PyMca5.PyMcaGui.plotting import PyMcaPrintPreview
        PyMcaPrintPreview.resetSingletonPrintPreview()        
        super(testPyMcaBatch, self).tearDown()

    def testCommand(self):
        from PyMca5.PyMcaGui.pymca import PyMcaBatch
        cmd = PyMcaBatch.Command('command')
        cmd.addOption('a', value=1, format='"{:04d}"')
        cmd.b = 2
        parts = {'command', '--a="0001"', '--b=2'}
        self.assertEqual(parts, set(str(cmd).split(' ')))
        cmd.a = 10
        parts = {'command', '--a="0010"', '--b=2'}
        self.assertEqual(parts, set(str(cmd).split(' ')))
        cmd['a'] = 5
        cmd['c'] = 'test'
        parts = {'command', '--a=5', '--b=2', '--c=test'}
        self.assertEqual(parts, set(str(cmd).split(' ')))
        dict1 = cmd.getAllOptions()
        dict2 = {'a': 5, 'b': 2, 'c': 'test'}
        self.assertEqual(dict1, dict2)
        dict1 = cmd.getAllOptionsBut('a', 'b')
        dict2 = {'c': 'test'}
        self.assertEqual(dict1, dict2)
        dict1 = cmd.getOptions('a', 'b')
        dict2 = {'a': 5, 'b': 2}
        self.assertEqual(dict1, dict2)

    def testSubCommands(self):
        """
        Check multi processing slicing of 2D maps for different
        map dimensions, number of files and number of processes.
        Assumes a file contains one or more rows (i.e. columns are
        never split over files).
        """
        for i in range(10000):
            nRows = randint(1, 10)
            nColumns = randint(1, 10)
            nRowsPerFile = randint(1, 5)
            if (nRows % nRowsPerFile) == 0:
                nFiles = nRows//nRowsPerFile
            else:
                nFiles = nRows
            nBatches = randint(1, 30)
            chunks = (i % 2) == 0
            self.assertSubCommands(nRows, nColumns, nFiles, nBatches, chunks)

    def assertSubCommands(self, nRows, nColumns, nFiles, nBatches, bchunks):
        """
        Checks whether each spectrum is processed exactly once and chunk
        indices are sequential.
        """
        from PyMca5.PyMcaGui.pymca import PyMcaBatch
        msg = '\nnRows={}, nColumns={}, nFiles={}, nBatches={}'\
              .format(nRows, nColumns, nFiles, nBatches)
        coverage = numpy.zeros((nRows, nColumns), dtype=int)
        nRowsPerFile = nRows//nFiles
        chunks = []

        def runProcess(cmd):
            iFiles = list(range(cmd.filebeginoffset, nFiles-cmd.fileendoffset, cmd.filestep))
            iCols = list(range(cmd.mcaoffset, nColumns, cmd.mcastep))
            iRows = list(range(nRowsPerFile))
            for ifile in iFiles:
                for irow in iRows:
                    for icol in iCols:
                        coverage[ifile*nRowsPerFile+irow, icol] += 1
            self.assertTrue(bool(iFiles), msg + '\n no files processed')
            if bool(iCols):
                chunks.append(cmd.chunk)

        cmd = PyMcaBatch.Command()
        PyMcaBatch.subCommands(cmd, nFiles, nBatches, runProcess, chunks=bchunks)

        # Check: each spectrum is processed exactly once
        self.assertTrue((coverage == 1).all(), msg + '\n {}'.format(coverage))

        # Check: chunk indices sequential
        self.assertTrue((numpy.diff(sorted(chunks)) == 1).all(), msg)
        self.assertTrue(len(chunks) <= nBatches, msg)

    def testFastFitEdfMap(self):
        self._assertFastFitMap('edf')

    def testSlowFitEdfMap(self):
        self._assertSlowFitMap('edf')

    def testSlowRoiFitEdfMap(self):
        self._assertSlowFitMap('edf', roiwidth=100, outputdir='fitresulta')
        self._assertSlowGuiFitMap('edf', roiwidth=100, outputdir='fitresultb')

    @unittest.skipIf(getattr(sys, 'frozen', False) or numpy.version.version == '1.17.0', "skipped running as frozen binary or numpy issue 13715")
    def testSlowMultiFitEdfMap(self):
        self._assertSlowMultiFitMap('edf')

    def testFastFitSpecMap(self):
        self._assertFastFitMap('specmesh')

    def testSlowFitSpecMap(self):
        self._assertSlowFitMap('specmesh')

    def testSlowRoiFitSpecMap(self):
        self._assertSlowFitMap('specmesh', roiwidth=100, outputdir='fitresulta')
        self._assertSlowGuiFitMap('specmesh', roiwidth=100, outputdir='fitresultb')

    @unittest.skipIf(getattr(sys, 'frozen', False) or numpy.version.version == '1.17.0', "skipped running as frozen binary or numpy issue 13715")
    def testSlowMultiFitSpecMap(self):
        self._assertSlowMultiFitMap('specmesh')

    @unittest.skipIf(not HAS_H5PY, "skipped h5py missing")
    def testFastFitHdf5Map(self):
        self._assertFastFitMap('hdf5')

    @unittest.skipIf(not HAS_H5PY, "skipped h5py missing")
    def testSlowFitHdf5Map(self):
        self._assertSlowFitMap('hdf5')

    @unittest.skipIf(not HAS_H5PY, "skipped h5py missing")
    def testSlowRoiFitHdf5Map(self):
        self._assertSlowFitMap('hdf5', roiwidth=100, outputdir='fitresulta')
        self._assertSlowGuiFitMap('hdf5', roiwidth=100, outputdir='fitresultb')

    @unittest.skipIf(not HAS_H5PY, "skipped h5py missing")
    def testSlowMultiFitHdf5Map(self):
        self._assertSlowMultiFitMap('hdf5')

    def _assertFastFitMap(self, typ, outputdir='fitresults'):
        info = self._generateData(fast=True, typ=typ)
        # Compare with legacy FastXRFLinearFit
        result1 = self._fitMap(info, fast=True, outputdir=outputdir+'1')
        result2 = self._fitMap(info, fast=True, legacy=True, outputdir=outputdir+'2')
        self._assertEqualFitResults(result1, result2, rtol=self._rtolLegacy)

    def _assertSlowFitMap(self, typ, outputdir='fitresults', **kwargs):
        info = self._generateData(typ=typ)
        # Compare with legacy McaAdvancedFitBatch
        result1 = self._fitMap(info, outputdir=outputdir+'1', **kwargs)
        result2 = self._fitMap(info, legacy=True, outputdir=outputdir+'2', **kwargs)
        self._assertEqualFitResults(result1, result2, rtol=self._rtolLegacy)

    def _assertSlowMultiFitMap(self, typ, outputdir='fitresults', **kwargs):
        from PyMca5.PyMcaGui.pymca.PyMcaBatch import ranAsBootstrap
        info = self._generateData(typ=typ)

        # Compare single vs. multi processing
        result1 = self._fitMap(info, nBatches=2, outputdir=outputdir+'1', **kwargs)
        result2 = self._fitMap(info, nBatches=1, outputdir=outputdir+'2', **kwargs)
        self._assertEqualFitResults(result1, result2, rtol=0)

        if not ranAsBootstrap() and typ != 'hdf5':
            # REMARK: not supported by legacy code
            #  - testing from source
            #  - hdf5 selection without user interaction
            #  - multi process on single non-hdf5 file
            # Compare legacy single vs. multi processing
            if typ != 'specmesh':
                result3 = self._fitMap(info, nBatches=2, legacy=True,
                                       outputdir=outputdir+'3', **kwargs)
            result4 = self._fitMap(info, nBatches=1, legacy=True,
                                   outputdir=outputdir+'4', **kwargs)
            if typ != 'specmesh':
                self._assertEqualFitResults(result3, result4, rtol=0)

            # Compare with legacy PyMcaBatch
            if typ != 'specmesh':
                self._assertEqualFitResults(result1, result3, rtol=self._rtolLegacy)
            self._assertEqualFitResults(result2, result4, rtol=self._rtolLegacy)

        # Compare thread vs. process
        result5 = self._fitMap(info, nBatches=0,
                               outputdir=outputdir+'5', **kwargs)
        self._assertEqualFitResults(result2, result5, rtol=0)

        # Compare blocking vs. non-blocking process
        result6 = self._fitMap(info, nBatches=1, blocking=True,
                               outputdir=outputdir+'6', **kwargs)
        self._assertEqualFitResults(result2, result6, rtol=0)

    def _assertSlowGuiFitMap(self, typ, outputdir='fitresults', **kwargs):
        from PyMca5.PyMcaGui.pymca.PyMcaBatch import ranAsBootstrap
        info = self._generateData(typ=typ)
        result1 = self._fitMap(info, nBatches=1, outputdir=outputdir+'1', **kwargs)

        if not ranAsBootstrap() and typ != 'hdf5':
            # Compare with legacy PyMcaBatch
            result2 = self._fitMap(info, nBatches=1, legacy=True,
                                   outputdir=outputdir+'2', **kwargs)
            self._assertEqualFitResults(result1, result2, rtol=self._rtolLegacy)

    def _fitMap(self, info, fast=False, nBatches=-1,
                outputdir='fitresults', **kwargs):
        outputdir = os.path.join(self.path, outputdir)
        if fast:
            # Single process fast fitting (FastXRFLinearFit)
            result = self._fastFitMap(info, outputdir, **kwargs)
        elif nBatches < 0:
            # Single process slow fitting (McaAdvancedFitBatch)
            result = self._slowFitMap(info, outputdir, **kwargs)
        else:
            # Multi process slow fitting (PyMcaBatch)
            result = self._slowMultiFitMap(info, outputdir,
                                           nBatches, **kwargs)
        # Validate result
        labels, scanData = self._readResult(result)
        self._checkFitResult(labels, scanData, info['liveTimeCorrection'],
                             multiprocessing=nBatches > 1, fast=fast)
        return labels, scanData

    def _fastFitMap(self, info, outputdir, legacy=False):
        """
        Multi process fast fitting
        """
        if legacy:
            from PyMca5.PyMcaPhysics.xrf import LegacyFastXRFLinearFit as FastXRFLinearFit
        else:
            from PyMca5.PyMcaPhysics.xrf import FastXRFLinearFit
        batch = FastXRFLinearFit.FastXRFLinearFit()
        kwargs = {'y': info['input'],
                  'livetime': info['liveTime'],
                  'weight': 0,
                  'configuration': info['configuration'],
                  'concentrations': True,
                  'refit': 1}
        if not legacy:
            kwargs['outputDir'] = outputdir
            kwargs['dat'] = True
            kwargs['edf'] = False
            kwargs['h5'] = False
            kwargs['diagnostics'] = True
        outbuffer = batch.fitMultipleSpectra(**kwargs)
        if legacy:
            FastXRFLinearFit.save(outbuffer, outputdir, csv=False)
        return self._fitResultFileName(None, outputdir, fast=True, legacy=legacy)

    def _slowFitMap(self, info, outputdir, legacy=False, roiwidth=0):
        """
        Single process slow fitting
        """
        if legacy:
            from PyMca5.PyMcaPhysics.xrf import LegacyMcaAdvancedFitBatch as McaAdvancedFitBatch
            os.mkdir(outputdir)
        else:
            from PyMca5.PyMcaPhysics.xrf import McaAdvancedFitBatch
        kwargs = {'filelist': info['input'],
                  'outputdir': outputdir,
                  'concentrations': True,
                  'selection': info['selection'],
                  'quiet': True,
                  'roifit': bool(roiwidth),
                  'roiwidth': roiwidth}
        if not legacy:
            kwargs['dat'] = True
            kwargs['edf'] = False
            kwargs['h5'] = False
            kwargs['diagnostics'] = True
        batch = McaAdvancedFitBatch.McaAdvancedFitBatch(info['cfgname'], **kwargs)
        batch.processList()
        return self._fitResultFileName(info['input'], outputdir,
                                       legacy=legacy, roiwidth=roiwidth)

    def _slowMultiFitMap(self, info, outputdir, nBatches, legacy=False,
                         roiwidth=0, **startargs):
        """
        Multi process slow fitting

        nBatches == 0: thread
        nBatches == 1, blocking == False: single monitored process
        nBatches == 1, blocking == True: single unmonitored process
        nBatches > 1: multi processing
        """
        os.mkdir(outputdir)
        kwargs = {'actions': True,
                  'showresult': False,
                  'filelist': info['input'],
                  'config': info['cfgname'],
                  'outputdir': outputdir}
        if legacy:
            from PyMca5.PyMcaGui.pymca.LegacyPyMcaBatch import McaBatchGUI
        else:
            from PyMca5.PyMcaGui.pymca.PyMcaBatch import McaBatchGUI
            kwargs['dat'] = True
            kwargs['edf'] = False
            kwargs['h5'] = False
            kwargs['diagnostics'] = True
            kwargs['concentrations'] = True
            kwargs['roifit'] = bool(roiwidth)
            kwargs['roiwidth'] = roiwidth
            kwargs['nproc'] = nBatches
            kwargs['selection'] = info['selection']
        result = self._fitResultFileName(info['input'], outputdir,
                                         legacy=legacy, roiwidth=roiwidth)

        widget = McaBatchGUI(**kwargs)
        if legacy:
            widget._McaBatchGUI__concentrationsBox.setChecked(True)
            widget._McaBatchGUI__roiBox.setChecked(bool(roiwidth))
            widget._McaBatchGUI__roiSpin.setValue(roiwidth)
            widget._McaBatchGUI__splitSpin.setValue(min(nBatches, 1))
            widget._McaBatchGUI__splitBox.setChecked(nBatches > 1)

        #widget.show()  # show widget for debugging
        self.qapp.processEvents()
        widget.start(**startargs)
        self._waitForFitResult(result)
        widget.close()
        self.qapp.processEvents()
        #self.qapp.exec()  # block for debugging
        return result

    def _fitResultFileName(self, filelist, outputdir, fast=False,
                           legacy=False, roiwidth=0):
        ext = '.dat'
        if filelist:
            # Slow fit
            from PyMca5.PyMcaPhysics.xrf import McaAdvancedFitBatch
            rootname = McaAdvancedFitBatch.getRootName(filelist)
            if legacy:
                subdir = 'IMAGES'
            else:
                #subdir = rootname
                subdir = 'IMAGES'
        else:
            # Fast fit
            rootname = 'images'
            subdir = 'IMAGES'
        if roiwidth:
            if legacy:
                rootname += '_*'
                ext = '.edf'
            rootname += '_{:04d}eVROI'.format(roiwidth)
        return os.path.join(outputdir, subdir, rootname+ext)

    def _generateData(self, fast=False, typ='hdf5'):
        # Generate data (in memory + save in requested format)
        nDet = 1  # TODO: currently only works with 1 detector
        nRows = 5
        nColumns = 4
        nTimes = 3
        filename = os.path.join(self.path, 'Map')
        if typ == 'edf':
            genFunc = XrfData.generateEdfMap
            filename += '.edf'
        elif typ == 'specmesh':
            genFunc = XrfData.generateSpecMesh
            filename += '.dat'
        elif typ == 'hdf5':
            genFunc = XrfData.generateHdf5Map
            filename += '.h5'
        else:
            raise ValueError('Unknown data type {} for XRF map'.format(repr(typ)))
        # TODO: cannot provide live time when fitting .edf list of files
        liveTimeIsProvided = fast or typ == 'hdf5'

        def modfunc(configuration):
            configuration["concentrations"]["usematrix"] = 0
            configuration["concentrations"]["useautotime"] = int(liveTimeIsProvided)
            if fast:
                configuration['fit']['stripalgorithm'] = 1
            else:
                configuration['fit']['linearfitflag'] = 1
        info = genFunc(filename, nDet=nDet, nRows=nRows,
                       nColumns=nColumns, nTimes=nTimes,
                       modfunc=modfunc)

        # Concentrations are multiplied by this factor to
        # normalize live time to preset time
        # TODO: currently only works with 1 detector
        info['liveTime'] = info['liveTime'][0, ...]
        if liveTimeIsProvided:
            info['liveTimeCorrection'] = float(info['presetTime'])/info['liveTime']
        else:
            info['liveTimeCorrection'] = numpy.ones_like(info['liveTime'])
        if typ == 'specmesh':
            # REMARK: spec file data is flattened by the spec loaders
            nRows, nColumns = info['liveTimeCorrection'].shape
            info['liveTimeCorrection'] = info['liveTimeCorrection'].reshape((1, nRows*nColumns))

        # Batch fit input (list of strings or stack object)
        filelist = info['filelist']
        if typ == 'edf':
            if fast:
                from PyMca5.PyMca import EDFStack
                info['input'] = EDFStack.EDFStack(filelist, dtype=numpy.float32)
            else:
                info['input'] = filelist
                info['selection'] = None
        elif typ == 'specmesh':
            if fast:
                from PyMca5.PyMcaIO import SpecFileStack
                info['input'] = SpecFileStack.SpecFileStack(filelist)
            else:
                info['input'] = filelist
                info['selection'] = None
        elif typ == 'hdf5':
            datasets = ['/xrf/mca{:02d}/data'.format(k) for k in range(nDet)]
            if fast:
                from PyMca5.PyMcaIO import HDF5Stack1D
                info['selection'] = selection = {'y': datasets[0]}
                info['input'] = HDF5Stack1D.HDF5Stack1D(filelist, selection)
            else:
                info['selection'] = {'x': [], 'm': [], 'y': [datasets[0]]}
                info['input'] = filelist

        # Batch fit configuration
        info['cfgname'] = os.path.join(self.path, 'Map.cfg')
        return info

    def _assertEqualFitResults(self, result1, result2, rtol=0, atol=0):
        labels1, scanData1 = result1
        labels2, scanData2 = result2
        self.assertEqual(set(labels1), set(labels2))
        for label, data in zip(labels1, scanData1):
            idx = labels2.index(label)
            numpy.testing.assert_allclose(data, scanData2[idx, :],
                                          err_msg=label, rtol=rtol,
                                          atol=atol)

    def _convertLegacyLabel(self, label):
        if label.endswith('-mass-fraction'):
            label = label.replace('-mass-fraction', '')
            label = 'w({})'.format(label)
        label = label.replace('C(', 'w(')
        label = label.replace('-', '_')
        label = label.replace(' ', '_')
        if label.endswith('_ROI'):
            label = label[:-4]
        return label

    def _convertLegacyLabels(self, labels, data):
        labels = list(map(self._convertLegacyLabel, labels))
        excluded_labels = 'row', 'column', 'point'
        included = [label.lower() not in excluded_labels for label in labels]
        if not all(included):
            # woraround numpy issue https://github.com/numpy/numpy/pull/13715
            # by creating an intermediate array
            # data = data[included, ...]
            data = data[numpy.array(included, copy=True), ...]
            labels = [label for label, b in zip(labels, included) if b]
        return labels, data

    def _readResult(self, filenames):
        """
        :param str or list filenames:
        :returns tuple: list(nparams), ndarray(nparams, nrows, ncolumns)
        """
        if isinstance(filenames, list):
            filename0 = filenames[0]
        elif '*' in filenames:
            filenames = glob(filenames)
            filename0 = filenames[0]
        else:
            filename0 = filenames
            filenames = [filenames]
        ext = os.path.splitext(filename0)[1]
        if ext == '.dat':
            labels, data = self._parseDatResults(filenames[0])
        elif ext == '.edf':
            labels, data = self._parseEdfResults(filenames)
        else:
            raise NotImplementedError
        return self._convertLegacyLabels(labels, data)

    def _parseDatResults(self, filename):
        """
        :param str filename:
        :returns tuple: list(nparams), ndarray(nparams, nrows, ncolumns)
        """
        from PyMca5.PyMcaIO import specfilewrapper as specfile
        self.assertTrue(os.path.isfile(filename),
                        "Batch fit result file <%s> not present" % filename)
        sf = specfile.Specfile(filename)
        labels = sf[0].alllabels()
        scanData = sf[0].data()
        sf = None
        nParams, nPoints = scanData.shape
        idxRow = labels.index('row')
        idxColumn = labels.index('column')
        nRows = int(numpy.round(max(scanData[idxRow, :]))) + 1
        nColumns = int(numpy.round(max(scanData[idxColumn, :]))) + 1
        colfast = scanData[idxRow, 0] == scanData[idxRow, 1]
        if colfast:
            order = 'C'
        else:
            order = 'F'
        scanData = scanData.reshape((nParams, nRows, nColumns), order=order)
        return labels, scanData

    def _parseEdfResults(self, filenames):
        """
        :param list filenames:
        :returns tuple: list(nparams), ndarray(nparams, nrows, ncolumns)
        """
        labels = []
        data = []
        from PyMca5.PyMcaIO import EdfFile
        for filename in filenames:
            # REMARK: each file can contain multiple images (roifit)
            #stack = EDFStack.EDFStack(filename)
            stack = EdfFile.EdfFile(filename)
            for i in range(stack.GetNumImages()):
                data.append(stack.GetData(i))
                labels.append(stack.GetHeader(i)['Title'])
        return labels, numpy.asarray(data)

    def _waitForFitResult(self, filenames):
        """
        :param list filenames:
        """
        # Wait until result is created
        from time import sleep
        msg = 'Waiting for {} ...'.format(filenames)
        while not self._resultExists(filenames):
            sleep(3)
            if msg:
                _logger.info(msg)
                msg = ''
            self.qapp.processEvents()

        # Wait until result is finished writting
        bytes0 = self._resultSize(filenames)
        nfiles0 = self._resultNFiles(filenames)
        while True:
            sleep(1)
            bytes1 = self._resultSize(filenames)
            nfiles1 = self._resultNFiles(filenames)
            if bytes1 == bytes0 and nfiles0 == nfiles1:
                break
            else:
                bytes0 = bytes1
                nfiles0 = nfiles1
        _logger.info('Finished {}'.format(filenames))

    def _resultExists(self, filenames):
        if isinstance(filenames, list):
            if filenames:
                return all(map(self._resultExists, filenames))
            else:
                return False
        elif '*' in filenames:
            return self._resultExists(glob(filenames))
        elif filenames:
            return os.path.exists(filenames)
        else:
            return False

    def _resultSize(self, filenames):
        if isinstance(filenames, list):
            if filenames:
                return sum(map(self._resultExists, filenames))
            else:
                return 0
        elif '*' in filenames:
            return self._resultExists(glob(filenames))
        elif filenames:
            return os.stat(filenames).st_size
        else:
            return 0

    def _resultNFiles(self, filenames):
        if isinstance(filenames, list):
            if filenames:
                return sum(map(self._resultExists, filenames))
            else:
                return 0
        elif '*' in filenames:
            return self._resultExists(glob(filenames))
        elif filenames:
            return int(os.path.exists(filenames))
        else:
            return 0

    def _checkFitResult(self, labels, paramStack, liveTimeCorrection,
                        multiprocessing=False, fast=False):
        """
        Validate fit result

        :param list labels: parameter names
        :param ndarray paramStack: nParams x nRows x nColumns
        :param ndarray liveTimeCorrection: nRows x nColumns
        :param bool multiprocessing: merged result of multiple processes
        :param bool fast: result of fast processing
        """
        nParams, nRows, nColumns = paramStack.shape
        self.assertTrue((nRows, nColumns), liveTimeCorrection.shape)
        for label, param in zip(labels, paramStack):
            if label in ["Point", "row", "column"]:
                continue
            if label.startswith("w("):
                # Same spectrum in each pixel but live time changes.
                # This means peak areas are the same but concentrations
                # are corrected for this live time.
                param = param/liveTimeCorrection
                # TODO: why rounding errors?
                rtol = 1e-5
            else:
                # Same spectrum in each pixel so fitted parameters
                # should have the same value in each pixel
                rtol = 0
            numpy.testing.assert_allclose(param, param[0, 0], err_msg=label,
                                          rtol=rtol, atol=0)


def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(unittest.TestLoader().loadTestsFromTestCase(testPyMcaBatch))
    else:
        # use a predefined order
        testSuite.addTest(testPyMcaBatch("testCommand"))
        testSuite.addTest(testPyMcaBatch("testSubCommands"))
        testSuite.addTest(testPyMcaBatch("testFastFitEdfMap"))
        testSuite.addTest(testPyMcaBatch("testSlowFitEdfMap"))
        testSuite.addTest(testPyMcaBatch("testSlowRoiFitEdfMap"))
        if not getattr(sys, 'frozen', False):
            testSuite.addTest(testPyMcaBatch("testSlowMultiFitEdfMap"))
        testSuite.addTest(testPyMcaBatch("testFastFitHdf5Map"))
        testSuite.addTest(testPyMcaBatch("testSlowFitHdf5Map"))
        testSuite.addTest(testPyMcaBatch("testSlowRoiFitHdf5Map"))
        testSuite.addTest(testPyMcaBatch("testSlowMultiFitHdf5Map"))
        testSuite.addTest(testPyMcaBatch("testFastFitSpecMap"))
        testSuite.addTest(testPyMcaBatch("testSlowFitSpecMap"))
        testSuite.addTest(testPyMcaBatch("testSlowRoiFitSpecMap"))
        if not getattr(sys, 'frozen', False):
            testSuite.addTest(testPyMcaBatch("testSlowMultiFitSpecMap"))
    return testSuite


def test(auto=False):
    return unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        auto = False
    else:
        auto = True
    app = qt.QApplication([])
    result = test(auto)
    app = None
    sys.exit(not result.wasSuccessful())
