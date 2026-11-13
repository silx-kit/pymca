#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# This file is part of the PyMca X-ray Fluorescence Toolkit.
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
__author__ = "Henry Towbin"
__license__ = "MIT"
import os
import shutil
import struct
import tempfile
import unittest
import warnings

import numpy

N_CHANNELS = 37
FIRST_X = 650.0
LAST_X = 4000.0


def _spectralHeader(nChannels):
    header = bytearray(140)
    struct.pack_into("<II", header, 0, 3, nChannels)
    struct.pack_into("<ff", header, 16, LAST_X, FIRST_X)
    struct.pack_into("<I", header, 36, 16)
    return bytes(header)


def _spectrumHeader(title):
    header = bytearray(96)
    struct.pack_into("<I", header, 0, 16)
    title = title.encode("ascii")
    header[16:16 + len(title)] = title
    return bytes(header)


def _labels(size, offsets):
    block = bytearray(size)
    for offset in offsets:
        block[offset:offset + 22] = b"Position (micrometers)"
    return block


def writeOmnicMap(fname, spectra, positions, extended=True, titles=None,
                  description=None):
    """
    Write a minimal OMNIC map with the block layout of the
    "Spectral Exte File" (extended=True) or "Spectral Data File"
    (extended=False) containers. description is the map description
    (y0, y1, deltaY, x0, x1, deltaX) stored with the "Position" labels.
    """
    spectra = numpy.asarray(spectra, dtype=numpy.float32)
    nSpectra, nChannels = spectra.shape
    if titles is None:
        titles = ["Spectrum %d of %d" % (i + 1, nSpectra)
                  for i in range(nSpectra)]
    header = _spectralHeader(nChannels)
    if description is None:
        # labels 150 bytes apart: no map description
        display = (0x92, 2, bytes(_labels(728, [128, 278])))
    else:
        block = _labels(264, [156, 222])
        struct.pack_into("<6f", block, 66, *description)
        display = (0x145, 1, bytes(block))
    xy = struct.pack("<HHH", nSpectra, 2, 0) + \
         numpy.asarray(positions, dtype="<f4").tobytes() + b"\x00\x00"
    background = numpy.ones(nChannels, dtype="<f4").tobytes()
    blocks = [(2, 1, header), (0x6a, 1, bytes(56))]
    if extended:
        blocks += [(0x69, 1, bytes(12)), (0x92, 1, bytes(728))]
    blocks += [display, (6, 1, xy), (2, 0, header), (3, 0, background)]
    if extended:
        series = header + bytes(56)
        for i in range(nSpectra):
            series += _spectrumHeader(titles[i]) + bytes(4) + \
                      spectra[i].astype("<f4").tobytes()
        blocks.append((0x12d, 1, series))
        magic, fmt = b"Spectral Exte File", "<HQIII"
    else:
        for i in range(nSpectra):
            blocks += [(0x94, i + 1, _spectrumHeader(titles[i])),
                       (3, i + 1, spectra[i].astype("<f4").tobytes())]
        magic, fmt = b"Spectral Data File", "<HIIIH"
    entrySize = struct.calcsize(fmt)
    # blocks start on a 16-byte boundary, as in OMNIC files
    start = (304 + entrySize * len(blocks) + 15) // 16 * 16
    fileHeader = bytearray(304)
    fileHeader[0:18] = magic
    struct.pack_into("<H", fileHeader, 294, len(blocks))
    directory = b""
    body = b""
    for key, index, content in blocks:
        directory += struct.pack(fmt, key, start + len(body), len(content),
                                 index, 0)
        body += content
    with open(fname, "wb") as fid:
        fid.write(bytes(fileHeader) + directory +
                  bytes(start - 304 - len(directory)) + body)


class testOmnicMap(unittest.TestCase):
    def setUp(self):
        from PyMca5.PyMcaIO import OmnicMap
        self.module = OmnicMap
        self.tmpDir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpDir)

    def _spectra(self, nSpectra):
        spectra = numpy.arange(nSpectra * N_CHANNELS, dtype=numpy.float32)
        return spectra.reshape(nSpectra, N_CHANNELS) / 100.

    def _read(self, spectra, positions, **kw):
        fname = os.path.join(self.tmpDir, "test.map")
        writeOmnicMap(fname, spectra, positions, **kw)
        stack = self.module.OmnicMap(fname)
        info = stack.info["OmnicInfo"]
        self.assertTrue(info is not None)
        self.assertEqual(info["Number of points"], N_CHANNELS)
        self.assertAlmostEqual(info["First X value"], FIRST_X, 3)
        self.assertAlmostEqual(info["Last X value"], LAST_X, 3)
        self.assertTrue(numpy.array_equal(
            stack.data.reshape(-1, N_CHANNELS), spectra))
        return stack

    def _checkPositions(self, stack, positions):
        positions = numpy.asarray(positions, dtype=numpy.float32)
        self.assertTrue(numpy.array_equal(stack.info["positioners"]["X"],
                                          positions[:, 0]))
        self.assertTrue(numpy.array_equal(stack.info["positioners"]["Y"],
                                          positions[:, 1]))

    def testPointMapClassicLayout(self):
        # "Spectral Data File" point map: the map description holds point
        # indices, the stage positions are in the directory
        positions = [[556.36, 17357.45], [281.99, 17492.40],
                     [291.36, 17130.62], [429.38, 17150.00]]
        spectra = self._spectra(4)
        stack = self._read(spectra, positions, extended=False,
                           description=(1, 4, 1, 1, 2, 1))
        self.assertEqual(stack.data.shape, (1, 4, N_CHANNELS))
        self._checkPositions(stack, positions)

    def testPointMapSingleSpectrum(self):
        # the directory is enough: there is no second title to search for
        positions = [[556.36, 17357.45]]
        stack = self._read(self._spectra(1), positions, extended=False)
        self.assertEqual(stack.data.shape, (1, 1, N_CHANNELS))
        self._checkPositions(stack, positions)

    def testPointMapOtherTitles(self):
        # the directory is enough: titles need not be "Spectrum i of n"
        positions = [[556.36, 17357.45], [281.99, 17492.40]]
        stack = self._read(self._spectra(2), positions, extended=False,
                           titles=["Grain 1 core", "Grain 1 rim"])
        self.assertEqual(stack.data.shape, (1, 2, N_CHANNELS))
        self._checkPositions(stack, positions)

    def testPointMapBackToFirstX(self):
        # a point coming back to the first X is not the start of a new row
        positions = [[100.0, 200.0], [150.0, 210.0], [100.0, 260.0]]
        stack = self._read(self._spectra(3), positions, extended=False)
        self.assertEqual(stack.data.shape, (1, 3, N_CHANNELS))
        self._checkPositions(stack, positions)

    def testPointMapNotAGrid(self):
        # points coming back to the first X that divide evenly into rows
        # are still not a grid
        positions = [[100.0, 200.0], [150.0, 210.0], [100.0, 260.0],
                     [120.0, 300.0]]
        stack = self._read(self._spectra(4), positions, extended=False)
        self.assertEqual(stack.data.shape, (1, 4, N_CHANNELS))
        self._checkPositions(stack, positions)
        self.assertTrue("xScale" not in stack.info)

    def testPointMapNoScales(self):
        # a point list has no pixel size, and no division by zero
        positions = [[100.0 + 10.0 * i, 200.0 + 7.0 * i] for i in range(4)]
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            stack = self._read(self._spectra(4), positions, extended=False)
        self.assertTrue("xScale" not in stack.info)
        self.assertTrue("yScale" not in stack.info)
        self.assertEqual([str(w.message) for w in caught], [])

    def testPointMapWithoutPositionLabels(self):
        # the spectral header is kept when the map description is missing
        fname = os.path.join(self.tmpDir, "test.map")
        positions = [[556.36, 17357.45], [281.99, 17492.40]]
        spectra = self._spectra(2)
        writeOmnicMap(fname, spectra, positions, extended=False)
        with open(fname, "rb") as fid:
            content = fid.read()
        with open(fname, "wb") as fid:
            fid.write(content.replace(b"Position", b"Distance"))
        stack = self.module.OmnicMap(fname)
        info = stack.info["OmnicInfo"]
        self.assertEqual(info["Number of points"], N_CHANNELS)
        self.assertTrue(numpy.array_equal(
            stack.data.reshape(-1, N_CHANNELS), spectra))
        self._checkPositions(stack, positions)

    def testGridMapExtendedLayout(self):
        # 2 rows of 3 spectra, X varying first
        positions = [[100.0 + 25.0 * (i % 3), 200.0 + 50.0 * (i // 3)]
                     for i in range(6)]
        stack = self._read(self._spectra(6), positions,
                           description=(200, 250, 50, 100, 150, 25))
        self.assertEqual(stack.data.shape, (2, 3, N_CHANNELS))
        self._checkPositions(stack, positions)
        self.assertEqual(stack.info["xScale"], [100.0, 25.0])
        self.assertEqual(stack.info["yScale"], [200.0, 50.0])

    def testLineScanStagePositions(self):
        # line scans have no map description: positions come from the file
        positions = [[411.15 + 11.9 * i, 17109.14 + 21.92 * i]
                     for i in range(5)]
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            stack = self._read(self._spectra(5), positions)
        self.assertEqual(stack.data.shape, (1, 5, N_CHANNELS))
        self._checkPositions(stack, positions)
        self.assertTrue("yScale" not in stack.info)
        # no division by zero when calculating the scales
        self.assertEqual([str(w.message) for w in caught], [])

    def testStaleMapDescription(self):
        # a map description left over from an earlier map is ignored
        positions = [[7116.8 - 23.6 * i, 2078.2 + 16.4 * i]
                     for i in range(4)]
        stack = self._read(self._spectra(4), positions,
                           description=(1110, 2810, 1e-40, 6179, 7379, 100))
        self._checkPositions(stack, positions)

    def testUnusableMapDescription(self):
        # a description that cannot be evaluated (NaN step, last X before
        # the first) is ignored when stored positions are available
        positions = [[7116.8 - 23.6 * i, 2078.2 + 16.4 * i]
                     for i in range(4)]
        for description in [(1110, 2810, 100, 6179, 7379, numpy.nan),
                            (1110, 2810, 100, 7379, 6179, 100)]:
            stack = self._read(self._spectra(4), positions,
                               description=description)
            self._checkPositions(stack, positions)

    def testGridKeepsComputedPositions(self):
        # stored positions within half a step of the map description are
        # not used, so existing results do not change
        computed = [[100.0 + 25.0 * (i % 3), 200.0 + 50.0 * (i // 3)]
                    for i in range(6)]
        stored = numpy.array(computed) + 0.004
        stack = self._read(self._spectra(6), stored,
                           description=(200, 250, 50, 100, 150, 25))
        self.assertEqual(stack.data.shape, (2, 3, N_CHANNELS))
        self._checkPositions(stack, computed)

    def testSmallStepGridOffDescription(self):
        # the tolerance follows the step: with a 0.005 um step, stored
        # positions 0.008 um away from the description are another grid
        stored = [[100.0 + 0.005 * (i % 3) + 0.008, 200.0 + 0.005 * (i // 3)]
                  for i in range(6)]
        stack = self._read(self._spectra(6), stored,
                           description=(200, 200.005, 0.005,
                                        100, 100.01, 0.005))
        self.assertEqual(stack.data.shape, (2, 3, N_CHANNELS))
        self._checkPositions(stack, stored)


def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    testSuite.addTest(
        unittest.TestLoader().loadTestsFromTestCase(testOmnicMap))
    return testSuite


def test(auto=False):
    unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))


if __name__ == '__main__':
    test()
