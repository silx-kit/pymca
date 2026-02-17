import os
import time
import shutil
import tempfile
import unittest
import datetime
import h5py
import sys
try:
    import multiprocessing
except Exception:
    pass

from PyMca5.PyMcaIO import HDF5Utils


def _cause_segfault(*args, **kwargs):
    import ctypes

    i = ctypes.c_char(b"a")
    j = ctypes.pointer(i)
    c = 0
    while True:
        j[c] = b"a"
        c += 1


def _safe_cause_segfault(*args, **kwargs):
    return HDF5Utils.run_in_subprocess(_cause_segfault, *args, **kwargs)


class testHDF5Utils(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp(prefix="pymca")

    def tearDown(self):
        shutil.rmtree(self.path)

    @unittest.skipIf(hasattr(sys, 'frozen'), "skipped running as frozen binary")
    def testHdf5GroupKeys(self):
        filename = os.path.join(self.path, "test.h5")
        with h5py.File(filename, "w", track_order=True) as f:
            for i in range(5):
                f[str(i)] = i

        names = list(map(str, range(5)))
        self.assertEqual(HDF5Utils.get_hdf5_group_keys(filename), names)
        self.assertEqual(HDF5Utils.safe_hdf5_group_keys(filename), names)

    @unittest.skipIf("multiprocessing" not in sys.modules), "skipped multiprocessing missing")
    def testSegFault(self):
        self.assertEqual(_safe_cause_segfault(default=123), 123)

    def testHdf5GroupSortByName(self):
        filename = os.path.join(self.path, "test.h5")

        with h5py.File(filename, "w", track_order=True) as f:
            _ = f.create_group("c")
            _ = f.create_group("b")
            _ = f.create_group("a")

        with h5py.File(filename, "r") as f:
            h5_items = list(f.items())
            keys = [key for key, _ in HDF5Utils.sort_h5items(h5_items)]
        assert keys == ["a", "b", "c"]

    def testHdf5GroupSortByNameWithNumbers(self):
        filename = os.path.join(self.path, "test.h5")

        expected = []
        with h5py.File(filename, "w", track_order=True) as f:
            for i in list(range(1, 11))[::-1]:
                key = f"1.{i}"
                _ = f.create_group(key)
                expected.insert(0, key)

        with h5py.File(filename, "r") as f:
            h5_items = list(f.items())
            keys = [key for key, _ in HDF5Utils.sort_h5items(h5_items)]
        assert keys == expected

    def testHdf5GroupSortByStartTime(self):
        filename = os.path.join(self.path, "test.h5")
        expected = []
        with h5py.File(filename, "w", track_order=True) as f:
            for i in list(range(1, 11))[::-1]:
                key = f"1.{i}"
                grp = f.create_group(key)
                grp["start_time"] = datetime.datetime.now().astimezone().isoformat()
                expected.append(key)
                time.sleep(0.1)  # make sure the start_time is unique

        with h5py.File(filename, "r") as f:
            h5_items = list(f.items())
            keys = [key for key, _ in HDF5Utils.sort_h5items(h5_items)]
        assert keys == expected

    def testHdf5GroupSortByIdenticalStartTime(self):
        filename = os.path.join(self.path, "test.h5")
        expected = []
        with h5py.File(filename, "w", track_order=True) as f:
            start_time = datetime.datetime.now().astimezone().isoformat()
            for i in list(range(1, 11))[::-1]:
                key = f"1.{i}"
                grp = f.create_group(key)
                grp["start_time"] = start_time
                expected.insert(0, key)

        with h5py.File(filename, "r") as f:
            h5_items = list(f.items())
            keys = [key for key, _ in HDF5Utils.sort_h5items(h5_items)]
        assert keys == expected

    def testHdf5GroupSortByTitle(self):
        filename = os.path.join(self.path, "test.h5")
        expected = []
        with h5py.File(filename, "w", track_order=True) as f:
            for i in range(1, 11)[::-1]:
                key = f"1.{11 - i}"
                grp = f.create_group(key)
                grp["title"] = chr(i + 65)
                expected.insert(0, key)

        with h5py.File(filename, "r") as f:
            h5_items = list(f.items())
            keys = [key for key, _ in HDF5Utils.sort_h5items(h5_items, ["title"])]
        assert keys == expected

    def testHdf5GroupSortByIdenticalTitle(self):
        filename = os.path.join(self.path, "test.h5")
        expected = []
        with h5py.File(filename, "w", track_order=True) as f:
            for i in range(1, 11)[::-1]:
                key = f"1.{i}"
                grp = f.create_group(key)
                grp["title"] = "same title"
                expected.insert(0, key)

        with h5py.File(filename, "r") as f:
            h5_items = list(f.items())
            keys = [key for key, _ in HDF5Utils.sort_h5items(h5_items, ["title"])]
        assert keys == expected


def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(unittest.TestLoader().loadTestsFromTestCase(testHDF5Utils))
    else:
        # use a predefined order
        if not hasattr(sys, 'frozen'):
            testSuite.addTest(testHDF5Utils("testHdf5GroupKeys"))
        testSuite.addTest(testHDF5Utils("testSegFault"))
    return testSuite


def test(auto=False):
    unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))


if __name__ == "__main__":
    test()
