import os
import time
import shutil
import tempfile
import unittest
import datetime
import h5py
import sys

from PyMca5.PyMcaIO import HDF5Utils

def _pass_through():
    return 0

def _cause_segfault(*args, **kwargs):
    import ctypes

    i = ctypes.c_char(b"a")
    j = ctypes.pointer(i)
    c = 0
    while True:
        j[c] = b"a"
        c += 1

class testHDF5Utils(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp(prefix="pymca")

    def tearDown(self):
        shutil.rmtree(self.path)

    @unittest.skipIf(getattr(sys, 'frozen', False), "skipped running as frozen binary")
    def testHdf5GroupKeys(self):
        filename = os.path.join(self.path, "test.h5")
        with h5py.File(filename, "w", track_order=True) as f:
            for i in range(5):
                f[str(i)] = i

        names = list(map(str, range(5)))
        self.assertEqual(HDF5Utils.get_hdf5_group_keys(filename), names)
        self.assertEqual(HDF5Utils.safe_hdf5_group_keys(filename), names)

    def testSegFault(self):
        # Verify that run_in_subprocess can be used
        try:
            result = HDF5Utils.run_in_subprocess(_pass_through, default=123)
        except Exception:
            if not getattr(sys, "frozen", False):
                raise
            self.skipTest("multiprocessing does not work for the current frozen binary")
        self.assertEqual(result, 0)

        # Check that run_in_subprocess works as intended when the function segfaults
        result = HDF5Utils.run_in_subprocess(_cause_segfault, default=123)
        self.assertEqual(result, 123)

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

    def testHdf5GroupSortByStartTimeThenEndTime(self):
        # sequential ordering (same start_time must be ordered by the end_time),
        filename = os.path.join(self.path, "test.h5")
        with h5py.File(filename, "w", track_order=True) as f:
            scanA = f.create_group("scanA")
            scanA["start_time"] = "2026-01-01T00:00:01"
            scanA["end_time"] = "2026-01-01T00:00:09"
            scanB = f.create_group("scanB")
            scanB["start_time"] = "2026-01-01T00:00:01"
            scanB["end_time"] = "2026-01-01T00:00:08"
            scanC = f.create_group("scanC")
            scanC["start_time"] = "2026-01-01T00:00:00"
            scanC["end_time"] = "2026-01-01T00:00:09"

        with h5py.File(filename, "r") as f:
            h5_items = list(f.items())
            keys = [key for key, _ in HDF5Utils.sort_h5items(h5_items)]
        assert keys == ["scanC", "scanB", "scanA"]

    def testHdf5GroupSortByStartTimeMissingForSome(self):
        # entries without the sort key must go last
        filename = os.path.join(self.path, "test.h5")
        with h5py.File(filename, "w", track_order=True) as f:
            scanA = f.create_group("scanA")
            scanA["start_time"] = "2026-01-01T00:00:01"
            f.create_group("scanB")  # no start_time
            scanC = f.create_group("scanC")
            scanC["start_time"] = "2026-01-01T00:00:00"

        with h5py.File(filename, "r") as f:
            h5_items = list(f.items())
            keys = [key for key, _ in HDF5Utils.sort_h5items(h5_items)]
        # present sorted by start_time (scanC, scanA), missing (scanB) last
        assert keys == ["scanC", "scanA", "scanB"]

    def testHdf5GroupSortByTitleNaturalOrder(self):
        # titles natural order: "scan 2" before "scan 10"
        filename = os.path.join(self.path, "test.h5")
        with h5py.File(filename, "w", track_order=True) as f:
            f.create_group("1.1")["title"] = "scan 10"
            f.create_group("1.2")["title"] = "scan 2"
            f.create_group("1.3")["title"] = "scan 1"

        with h5py.File(filename, "r") as f:
            h5_items = list(f.items())
            keys = [key for key, _ in HDF5Utils.sort_h5items(h5_items, ["title"])]
        assert keys == ["1.3", "1.2", "1.1"]

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
        if not getattr(sys, 'frozen', False):
            testSuite.addTest(testHDF5Utils("testHdf5GroupKeys"))
        testSuite.addTest(testHDF5Utils("testSegFault"))
    return testSuite


def test(auto=False):
    unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))


if __name__ == "__main__":
    test()
