#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2019-2022 European Synchrotron Radiation Facility
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
import sys
import numpy
import itertools
from contextlib import contextmanager
try:
    from PyMca5.PyMcaCore import McaStackView
except ImportError:
    McaStackView = None
try:
    import h5py
except ImportError:
    h5py = None


class testMcaStackView(unittest.TestCase):

    def setUp(self):
        self.path = tempfile.mkdtemp(prefix='pymca')

    def tearDown(self):
        shutil.rmtree(self.path)

    @unittest.skipIf(McaStackView is None,
                     'PyMca5.PyMcaCore.McaStackView cannot be imported')
    def testViewUtils(self):
        n = 20
        slices = [slice(None), slice(1, -2),
                  slice(8, 2, -1), slice(0, n, 3),
                  slice(0, n, -2), slice(n-2, 2, -3),
                  slice(n-1, None, -1), slice(None, -2, 3)]
        lst = list(range(n))
        for idx in slices:
            idxn = McaStackView.sliceNormalize(idx, n)
            self.assertEqual(lst[idx], lst[idxn])
        for idx in slices:
            self.assertEqual(McaStackView.sliceLen(idx, n), len(lst[idx]))
        for idx in slices:
            idxi = McaStackView.sliceReverse(idx, n)
            self.assertEqual(lst[idx][::-1], lst[idxi])
        for idx in slices:
            idxc = McaStackView.sliceComplement(idx, n)
            self.assertEqual(list(sorted(lst[idx]+idxc)), lst)
        for idx in slices:
            start, stop, step = idx.indices(n)
            lst1 = list(range(start, stop, int(numpy.sign(step))))
            it = McaStackView.chunkIndexGen(start, stop, step)
            self.assertEqual(len(lst1), sum(ns for it, ns in it))
            it = McaStackView.chunkIndexGen(start, stop, step)
            lst2 = [i for idxc, ns in it for i in lst[idxc]]
            self.assertEqual(lst1, lst2)

    @unittest.skipIf(McaStackView is None,
                     'PyMca5.PyMcaCore.McaStackView cannot be imported')
    def testfullChunkIndex(self):
        for ndim in [2, 3, 4]:
            shape = tuple(range(3, 3+ndim))
            data = numpy.zeros(shape, dtype=int)
            for chunkAxes, axesOrder, nChunksTot in self._chunkIndexAxes(shape, ndim):
                for nChunksMax in range(nChunksTot+2):
                    data[()] = 0
                    result = McaStackView.fullChunkIndex(shape, nChunksMax,
                                                         chunkAxes=chunkAxes,
                                                         axesOrder=axesOrder)
                    chunkIndex, chunkAxes, axesOrder, nChunksMax2 = result
                    self.assertTrue(nChunksMax2 <= max(nChunksMax, 1))
                    for i, (idxChunk, idxShape, nChunks) in enumerate(chunkIndex, 1):
                        data[idxChunk] += i
                        self.assertEqual(data[idxChunk].shape, idxShape)
                        self.assertTrue(nChunks <= nChunksMax2)
                    # Verify data coverage:
                    self.assertFalse((data == 0).any())
                    # Verify single element access and chunk access order:
                    arr = data.transpose(axesOrder[::-1]+chunkAxes).flatten()
                    lst1 = [k for k, g in itertools.groupby(arr)]
                    lst2 = list(range(1, i+1))
                    self.assertEqual(lst1, lst2)

    def _chunkIndexAxes(self, shape, ndim):
        axes = set(range(ndim))
        for ndimChunk in range(ndim+1):
            nOther = ndim-ndimChunk
            for chunkAxes in itertools.permutations(axes, ndimChunk):
                nChunksTot = numpy.prod([shape[i] for i in axes])
                yield chunkAxes, None, nChunksTot
                other = axes-set(chunkAxes)
                if other:
                    nChunksTot = numpy.prod([shape[i] for i in other])
                else:
                    nChunksTot = 1
                for axesOrder in itertools.permutations(other, nOther):
                    yield chunkAxes, axesOrder, nChunksTot

    def assert_array_equal(self, *var):
        if sys.maxsize > 2**32:
            # 64-bit interpreter
            return numpy.testing.assert_array_equal(*var)
        else:
            # 32-bit interpreter
            return numpy.testing.assert_allclose(*var)

    @unittest.skipIf(McaStackView is None,
                     'PyMca5.PyMcaCore.McaStackView cannot be imported')
    def testMaskedChunkIndex(self):
        for ndim in [2, 3, 4]:
            shape = tuple(range(3, 3+ndim))
            data = numpy.zeros(shape, dtype=int)
            for chunkAxes, axesOrder, nChunksTot in self._chunkIndexAxes(shape, ndim):
                # Create Mask
                mask, indices, nmask = self._randomMask(shape, chunkAxes, axesOrder)
                # Mask entire array
                maskFull = numpy.zeros(shape, dtype=bool)
                if mask is None:
                    maskFull[()] = False
                    nmask = 0
                else:
                    indicesFull = [slice(None)]*ndim
                    if axesOrder:
                        for i, ind in zip(axesOrder, indices):
                            indicesFull[i] = ind
                    elif chunkAxes:
                        tmp = tuple(i for i in range(ndim)
                                    if i not in chunkAxes)
                        for i, ind in zip(tmp, indices):
                            indicesFull[i] = ind
                    else:
                        indicesFull = indices
                    indicesFull = tuple(indicesFull)
                    maskFull[indicesFull] = True
                for nChunksMax in [2, nmask//3, nmask-1, nmask+1]:
                    for usedmask in [mask, None]:
                        data[()] = 0
                        self.assertFalse((data != 0).any())
                        chunkIndex, chunkAxes2, axesOrder, nChunksMax2 =\
                        McaStackView.maskedChunkIndex(shape, nChunksMax,
                                                      mask=usedmask,
                                                      chunkAxes=chunkAxes,
                                                      axesOrder=axesOrder)
                        for i, (idxChunk, idxShape, nChunks) in enumerate(chunkIndex, 1):
                            data[idxChunk] += i
                            self.assertEqual(data[idxChunk].shape, idxShape)
                            self.assertTrue(nChunks <= nChunksMax2)
                        # Verify data coverage:
                        if usedmask is None:
                            self.assertFalse((data == 0).any())
                        else:
                            self.assertFalse((data[maskFull] == 0).any())
                            self.assertTrue((data[~maskFull] == 0).all())
                        # Verify single element access:
                        lst1 = numpy.unique(data).tolist()
                        lst2 = list(range(int(usedmask is None), i+1))
                        self.assertEqual(lst1, lst2)

    def _randomMask(self, shape, chunkAxes, axesOrder):
        if axesOrder:
            mshape = tuple(shape[i] for i in axesOrder)
        elif chunkAxes:
            mshape = tuple(shape[i] for i in range(len(shape))
                                    if i not in chunkAxes)
        else:
            mshape = shape
        if mshape:
            mask = numpy.zeros(mshape, dtype=bool)
            indices = numpy.arange(mask.size)
            numpy.random.shuffle(indices)
            indices = indices[:mask.size//2]
            nmask = indices.size
            indices = numpy.unravel_index(indices, mshape)
            mask[indices] = True
        else:
            mask = None
            indices = None
            nmask = 0
        return mask, indices, nmask

    @unittest.skipIf(McaStackView is None,
                     'PyMca5.PyMcaCore.McaStackView cannot be imported')
    def testFullViewNumpy(self):
        for ndim in [2, 3, 4]:
            shape = range(6, 6+ndim)
            data = numpy.random.uniform(size=shape)
            self._assertFullView(data)
    
    @unittest.skipIf(McaStackView is None,
                     'PyMca5.PyMcaCore.McaStackView cannot be imported')
    @unittest.skipIf(h5py is None,
                     'h5py cannot be imported')
    def testFullViewH5py(self):
        for ndim in [2, 3]:
            shape = range(6, 6+ndim)
            data = numpy.random.uniform(size=shape)
            with self.h5Open('testFullView') as f:
                name = 'data{}'.format(ndim)
                f.create_dataset(name, data=data, chunks=(1,)*ndim)
                self._assertFullView(f[name])

    @unittest.skipIf(McaStackView is None,
                     'PyMca5.PyMcaCore.McaStackView cannot be imported')
    def testMaskedViewNumpy(self):
        for ndim in [2, 3, 4]:
            shape = range(6, 6+ndim)
            data = numpy.random.uniform(size=shape)
            self._assertMaskedView(data)

    @unittest.skipIf(McaStackView is None,
                     'PyMca5.PyMcaCore.McaStackView cannot be imported')
    @unittest.skipIf(h5py is None,
                     'h5py cannot be imported')
    def testMaskedViewH5py(self):
        for ndim in [2, 3]:
            shape = range(6, 6+ndim)
            data = numpy.random.uniform(size=shape)
            with self.h5Open('testMaskedView') as f:
                name = 'data{}'.format(ndim)
                f.create_dataset(name, data=data, chunks=(1,)*ndim)
                self._assertMaskedView(f[name])

    def _assertFullView(self, data):
        mcaSlice = slice(2, -1)
        for nMca in range(numpy.prod(data.shape[1:])+2):
            for mcaAxis in range(data.ndim):
                dataView = McaStackView.FullView(data,
                                                 readonly=False,
                                                 mcaAxis=mcaAxis,
                                                 mcaSlice=mcaSlice,
                                                 nMca=nMca)
                npAdd = numpy.arange(data.size).reshape(data.shape)
                addView = McaStackView.FullView(npAdd,
                                                readonly=True,
                                                mcaAxis=mcaAxis,
                                                mcaSlice=mcaSlice,
                                                nMca=nMca)
                idxFull = dataView.idxFull
                for readonly in [True, False]:
                    dataView.readonly = readonly
                    dataOrg = numpy.copy(data)
                    iters = dataView.items(), addView.items()
                    chunks = McaStackView.izipChunkItems(*iters)
                    for (key, chunk), (addKey, add) in chunks:
                        chunk += add
                    for idxFullComplement in dataView.idxFullComplement:
                        self.assert_array_equal(data[idxFullComplement],
                                                         dataOrg[idxFullComplement])
                    if readonly:
                        self.assert_array_equal(data[idxFull],
                                                         dataOrg[idxFull])
                    else:
                        self.assert_array_equal(data[idxFull],
                                                         dataOrg[idxFull]+npAdd[idxFull])

    def _assertMaskedView(self, data):
        mcaSlice = slice(2, -1)
        isH5py = isinstance(data, h5py.Dataset)
        for mcaAxis in range(data.ndim):
            mask, indices, nmask = self._randomMask(data.shape, (mcaAxis,), None)
            it = itertools.product([2, nmask//3, nmask-1, nmask+1], [mask, None])
            for nMca, usedmask in it:
                dataView = McaStackView.MaskedView(data,
                                                mask=usedmask,
                                                readonly=False,
                                                mcaAxis=mcaAxis,
                                                mcaSlice=mcaSlice,
                                                nMca=nMca)
                npAdd = numpy.arange(data.size).reshape(data.shape)
                addView = McaStackView.MaskedView(npAdd,
                                                mask=usedmask,
                                                readonly=True,
                                                mcaAxis=mcaAxis,
                                                mcaSlice=mcaSlice,
                                                nMca=nMca)
                idxFull = dataView.idxFull
                for readonly in [True, False]:
                    dataView.readonly = readonly
                    dataOrg = numpy.copy(data)
                    iters = dataView.items(), addView.items()
                    chunks = McaStackView.izipChunkItems(*iters)
                    for (key, chunk), (addKey, add) in chunks:
                        chunk += add
                    if isH5py:
                        _data = data[()]
                    else:
                        _data = data
                    for idxFullComplement in dataView.idxFullComplement:
                        self.assert_array_equal(_data[idxFullComplement],
                                                         dataOrg[idxFullComplement])
                    if readonly:
                        self.assert_array_equal(_data[idxFull],
                                                         dataOrg[idxFull])
                    else:
                        self.assert_array_equal(_data[idxFull],
                                                         dataOrg[idxFull]+npAdd[idxFull])

    @contextmanager
    def h5Open(self, name):
        filename = os.path.join(self.path, name+'.h5')
        with h5py.File(filename, mode='a') as f:
            yield f


def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(
            unittest.TestLoader().loadTestsFromTestCase(testMcaStackView))
    else:
        # use a predefined order
        testSuite.addTest(testMcaStackView('testViewUtils'))
        testSuite.addTest(testMcaStackView('testfullChunkIndex'))
        testSuite.addTest(testMcaStackView('testFullViewNumpy'))
        testSuite.addTest(testMcaStackView('testFullViewH5py'))
        testSuite.addTest(testMcaStackView('testMaskedChunkIndex'))
        testSuite.addTest(testMcaStackView('testMaskedViewNumpy'))
        testSuite.addTest(testMcaStackView('testMaskedViewH5py'))
    return testSuite


def test(auto=False):
    unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))


if __name__ == '__main__':
    test()
