#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2019-2023 European Synchrotron Radiation Facility
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
__author__ = "Wout De Nolf"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import unittest
import tempfile
import shutil
import os
import numpy
from contextlib import contextmanager
import itertools
try:
    import h5py
except Exception:
    h5py = None


class testXRFBatchFitOutput(unittest.TestCase):

    def setUp(self):
        self.path = tempfile.mkdtemp(prefix='pymca')
        self.saveall = {'outputDir': self.path,
                        'outputRoot': 'sample',
                        'fileEntry': 'sample_dataset',
                        'fileProcess': 'test',
                        'tif': True,
                        'edf': True,
                        'csv': True,
                        'h5': True,
                        'dat': True,
                        'multipage': True,
                        'diagnostics': True}

    def tearDown(self):
        if os.path.isdir(self.path):
            shutil.rmtree(self.path)

    def _getFiles(self, outputDir):
        files = []
        for root, dirnames, filenames in os.walk(outputDir):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        return files

    def testOverwrite(self):
        h5name = os.path.join(self.path, self.saveall['outputRoot']+'.h5')
        #subdir = os.path.join(self.path, self.saveall['outputRoot'])
        subdir = os.path.join(self.path, 'IMAGES')
        outbuffer = self._initOutBuffer(**self.saveall)
        outdata, outlabels, outaxes = self._generateData(outbuffer, memtype='mix')
        expected = self._getFiles(self.path)
        self._verifyHdf5(h5name, outdata, outlabels, outaxes)
        self._verifyEdf(subdir, self.saveall['multipage'], outdata, outlabels)
        for overwrite in ['False', 'True']:
            outbuffer = self._initOutBuffer(overwrite=overwrite, **self.saveall)
            outdata, outlabels, outaxes = self._generateData(outbuffer, memtype='mix')
            reality = self._getFiles(self.path)
            self.assertEqual(set(reality), set(expected))
            self._verifyHdf5(h5name, outdata, outlabels, outaxes)
            self._verifyEdf(subdir, self.saveall['multipage'], outdata, outlabels)

    def testNoSave(self):
        outbuffer = self._initOutBuffer(nosave=True, **self.saveall)
        outdata, outlabels, outaxes = self._generateData(outbuffer, memtype='hdf5')
        self.assertFalse(bool(self._getFiles(self.path)))

    def testOutputFormats(self):
        parameters = [(True, False)]*7 + [('ram', 'hdf5', 'mix')]
        for i, params in enumerate(itertools.product(*parameters)):
            outputDir = self.path+str(i)
            tif, h5, edf, csv, dat, multipage, diagnostics, memtype = params
            outbuffer = self._initOutBuffer(outputDir=outputDir,
                                            outputRoot='sample',
                                            fileEntry='sample_dataset',
                                            fileProcess='test',
                                            tif=tif, edf=edf, csv=csv,
                                            h5=h5, dat=dat,
                                            multipage=multipage,
                                            diagnostics=diagnostics)
            outdata, outlabels, outaxes = self._generateData(outbuffer, memtype=memtype)
            if h5py is None:
                h5 = False

            # Make sure the expected files are saved
            h5name = os.path.join(outputDir, 'sample.h5')
            #subdir = os.path.join(outputDir, 'sample')
            subdir = os.path.join(outputDir, 'IMAGES')
            expected = []
            if h5:
                expected.append(h5name)
            if multipage:
                for b, ext in zip([edf, tif], ['.edf', '.tif']):
                    if b:
                        expected.append(os.path.join(subdir, 'sample_dataset'+ext))
            else:
                for b, ext in zip([edf, tif], ['.edf', '.tif']):
                    if not b:
                        continue
                    expected += [os.path.join(subdir, 'sample_dataset_{}{}'.format(label, ext))
                                 for labeldict in outlabels['filename'].values()
                                 for label in labeldict.values()]
            if csv:
                expected.append(os.path.join(subdir, 'sample_dataset.csv'))
            if dat:
                expected.append(os.path.join(subdir, 'sample_dataset.dat'))
            reality = self._getFiles(outputDir)
            self.assertEqual(set(reality), set(expected))

            # Verify file content
            if h5:
                self._verifyHdf5(h5name, outdata, outlabels, outaxes)
            if edf:
                self._verifyEdf(subdir, multipage, outdata, outlabels)

    def _verifyEdf(self, subdir, multipage, outdata, outlabels):
        from PyMca5.PyMcaIO import EdfFile
        ext = '.edf'
        if multipage:
            filename = os.path.join(subdir, 'sample_dataset'+ext)
            f = EdfFile.EdfFile(filename)
            edfdata = {f.GetHeader(i)['Title']: f.GetData(i) for i in range(f.GetNumImages())}
        for group, datadict in outdata.items():
            if group not in outlabels['title']:
                continue
            if not multipage:
                edfdata = {}
                for label, data in datadict.items():
                    suffix = outlabels['filename'][group].get(label, None)
                    if not suffix:
                        continue
                    filename = os.path.join(subdir, 'sample_dataset_{}{}'.format(suffix, ext))
                    f = EdfFile.EdfFile(filename)
                    edfdata[f.GetHeader(0)['Title']] = f.GetData(0)
            for label, data in datadict.items():
                edflabel = outlabels['title'][group].get(label, None)
                if edflabel:
                    numpy.testing.assert_array_equal(data, edfdata[edflabel], '{}: {}'.format(group, label))

    def _verifyHdf5(self, filename, outdata, outlabels, outaxes):
        outlabels = outlabels['h5']
        with h5py.File(filename, mode='a') as f:
            nxprocess = f['sample_dataset']['test']
            self.assertEqual(set(nxprocess.keys()),
                             {'configuration', 'date', 'program', 'version', 'results'})
            nxresults = nxprocess['results']
            self.assertEqual(set(nxresults.keys()), set(outdata.keys()))
            for group, datadict in outdata.items():
                nxdata = nxresults[group]
                # Check signals attribute
                signals = [outlabels[group][label] for label in datadict.keys()]
                nxsignals = []
                name = nxdata.attrs.get('signal', None)
                if name:
                    nxsignals.append(name)
                names = nxdata.attrs.get('auxiliary_signals', numpy.array([])).tolist()
                if names:
                    nxsignals.extend(names)
                self.assertEqual(set(nxsignals), set(signals))
                # Check signals data
                for label, data in datadict.items():
                    numpy.testing.assert_array_equal(data, nxdata[outlabels[group][label]], '{}: {}'.format(group, label))
                if group in outaxes:
                    # Check axes attribute
                    names = nxdata.attrs.get('axes', numpy.array([])).tolist()
                    self.assertEqual(names, outaxes[group]['axesused'])
                    # Check axes data
                    for name in names:
                        i = outaxes[group]['axesused'].index(name)
                        data = outaxes[group]['axes'][i][1]
                        numpy.testing.assert_array_equal(data, nxdata[name], name)
                else:
                    # Check axes attribute
                    names = nxdata.attrs.get('axes', numpy.array([])).tolist()
                    self.assertEqual(names, [])

    def _initOutBuffer(self, **kwargs):
        from PyMca5.PyMcaPhysics.xrf.XRFBatchFitOutput import OutputBuffer
        return OutputBuffer(**kwargs)

    def _generateData(self, outbuffer, memtype='mix'):
        outaxes = {}
        outdata = {}
        outlabels = {}
        if memtype == 'mix':
            memsmall = 'ram'
            membig = 'hdf5'
        else:
            memsmall = membig = 'hdf5'

        labels = ['zero', 'Ca K', ('Ca K', 'Layer1'), 'Fe-K', ('Fe-K', 'Layer1')]
        nparams = len(labels)
        imgshape = 4, 5
        paramshape = (nparams,)+imgshape
        parameters = numpy.random.uniform(size=paramshape)
        uncertainties = numpy.random.uniform(size=paramshape)
        paramAttrs = {'default': True, 'errors': 'uncertainties'}
        uncertaintyAttrs = None

        axes = [('axis{}'.format(i), numpy.arange(n), {'units': 'um'})
                for i, n in enumerate(paramshape)]
        axesused = ['axis{}'.format(i) for i, n in enumerate(paramshape)]
        dummyAttrs = {'axes': axes, 'axesused': axesused}
        outaxes['dummy'] = dummyAttrs

        nmca = 6
        stackshape = imgshape+(nmca,)
        residuals = numpy.random.uniform(size=stackshape)
        axes = [('axis{}'.format(i), numpy.arange(n), {'units': 'um'})
                for i, n in enumerate(stackshape)]
        axes.append(('axis0_', numpy.arange(stackshape[0]), {}))
        axesused = ['axis{}'.format(i) for i, n in enumerate(stackshape)]
        fitAttrs = {'axes': axes, 'axesused': axesused}
        outaxes['fit'] = fitAttrs

        chisq = numpy.random.uniform(size=imgshape)
        axes = [('axis{}'.format(i), numpy.arange(n), {'units': 'um'})
                for i, n in enumerate(imgshape)]
        axesused = ['axis{}'.format(i) for i, n in enumerate(imgshape)]
        diagnosticsAttrs = {'axes': axes, 'axesused': axesused}
        outaxes['diagnostics'] = diagnosticsAttrs

        with outbuffer.saveContext():
            # Parameters + uncertainties
            buffer = outbuffer.allocateMemory('parameters',
                                              shape=parameters.shape,
                                              dtype=parameters.dtype,
                                              labels=labels,
                                              memtype=memsmall,
                                              groupAttrs=paramAttrs)
            for dout, din in zip(buffer, parameters):
                dout[()] = din
            outdata['parameters'] = {label: img for label, img
                                     in zip(labels, parameters)}
            buffer = outbuffer.allocateMemory('uncertainties',
                                              data=uncertainties,
                                              labels=labels,
                                              memtype=memsmall,
                                              groupAttrs=uncertaintyAttrs)
            outdata['uncertainties'] = {label: img for label, img
                                        in zip(labels, uncertainties)}
            # Diagnostics
            buffer = outbuffer.allocateMemory('residuals',
                                              group='fit',
                                              shape=residuals.shape,
                                              dtype=residuals.dtype,
                                              memtype=membig,
                                              groupAttrs=fitAttrs)
            buffer[:] = residuals
            outdata['fit'] = {'residuals': residuals}
            buffer = outbuffer.allocateMemory('chisq',
                                              group='diagnostics',
                                              data=chisq,
                                              memtype=memsmall,
                                              groupAttrs=diagnosticsAttrs)
            buffer = outbuffer.allocateMemory('nFree',
                                              group='diagnostics',
                                              shape=chisq.shape,
                                              dtype=chisq.dtype,
                                              memtype=memsmall,
                                              fill_value=nparams,
                                              groupAttrs=diagnosticsAttrs)
            outdata['diagnostics'] = {'nFree': numpy.full_like(chisq, nparams),
                                      'chisq': chisq}
            # Others
            buffer = outbuffer.allocateMemory('dummy',
                                              shape=parameters.shape,
                                              dtype=parameters.dtype,
                                              memtype=memsmall,
                                              fill_value=10,
                                              groupAttrs=dummyAttrs)
            outdata['dummy'] = {'dummy': numpy.full_like(parameters, 10)}
            # Non-data objects (not list or ndarray)
            outbuffer['misc'] = {'a': 1, 'b': 2}
        
        # Hdf5 group names, edf file suffixes and edf titles
        outlabels = {}
        outlabels['h5'] = h5labels = {}
        outlabels['title'] = titlelabels = {}
        outlabels['filename'] = filelabels = {}
        h5labels['parameters'] = {'zero': 'zero',
                                  'Ca K': 'Ca_K',
                                  ('Ca K', 'Layer1'): 'Ca_K_Layer1',
                                  'Fe-K': 'Fe-K',
                                  ('Fe-K', 'Layer1'): 'Fe-K_Layer1'}
        titlelabels['parameters'] = {'zero': 'zero',
                                     'Ca K': 'Ca_K',
                                     ('Ca K', 'Layer1'): 'Ca_K_Layer1',
                                     'Fe-K': 'Fe-K',
                                     ('Fe-K', 'Layer1'): 'Fe-K_Layer1'}
        filelabels['parameters'] = {'zero': 'zero',
                                    'Ca K': 'Ca_K',
                                    ('Ca K', 'Layer1'): 'Ca_K_Layer1',
                                    'Fe-K': 'Fe_K',
                                    ('Fe-K', 'Layer1'): 'Fe_K_Layer1'}
        h5labels['uncertainties'] = h5labels['parameters']
        titlelabels['uncertainties'] = {'zero': 's(zero)',
                                        'Ca K': 's(Ca_K)',
                                        ('Ca K', 'Layer1'): 's(Ca_K)_Layer1',
                                        'Fe-K': 's(Fe-K)',
                                        ('Fe-K', 'Layer1'): 's(Fe-K)_Layer1'}
        filelabels['uncertainties'] = {'zero': 'szero',
                                       'Ca K': 'sCa_K',
                                       ('Ca K', 'Layer1'): 'sCa_K_Layer1',
                                       'Fe-K': 'sFe_K',
                                       ('Fe-K', 'Layer1'): 'sFe_K_Layer1'}
        h5labels['diagnostics'] = {'nFree': 'nFree', 'chisq': 'chisq'}
        titlelabels['diagnostics'] = {'chisq': 'chisq'}
        filelabels['diagnostics'] = {'chisq': 'chisq'}
        h5labels['fit'] = {'residuals': 'residuals'}
        h5labels['dummy'] = {'dummy': 'dummy'}
        return outdata, outlabels, outaxes


def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(
            unittest.TestLoader().loadTestsFromTestCase(testXRFBatchFitOutput))
    else:
        # use a predefined order
        testSuite.addTest(testXRFBatchFitOutput('testOutputFormats'))
        testSuite.addTest(testXRFBatchFitOutput('testNoSave'))
        testSuite.addTest(testXRFBatchFitOutput('testOverwrite'))
    return testSuite


def test(auto=False):
    unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))


if __name__ == '__main__':
    test()
