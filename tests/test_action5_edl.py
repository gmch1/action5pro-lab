import tempfile
import unittest
from pathlib import Path
from unittest import mock

import action5_edl


RAWPROGRAM = """<?xml version="1.0" ?>
<data>
  <program SECTOR_SIZE_IN_BYTES="4096" filename="" label="abl_a"
    num_partition_sectors="256" physical_partition_number="4" start_sector="1000" />
  <program SECTOR_SIZE_IN_BYTES="4096" filename="" label="abl_b"
    num_partition_sectors="256" physical_partition_number="4" start_sector="2000" />
  <program SECTOR_SIZE_IN_BYTES="4096" filename="" label="devinfo"
    num_partition_sectors="1" physical_partition_number="4" start_sector="3000" />
  <program SECTOR_SIZE_IN_BYTES="4096" filename="gpt_backup4.bin" label="BackupGPT"
    num_partition_sectors="5" physical_partition_number="4" start_sector="NUM_DISK_SECTORS-5." />
</data>
"""


class RawprogramTests(unittest.TestCase):
    def test_parses_action5_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rawprogram4.xml"
            path.write_text(RAWPROGRAM, encoding="utf-8")
            partitions = action5_edl.parse_rawprogram_files([path])
        by_name = {partition.label: partition for partition in partitions}
        self.assertEqual(by_name["devinfo"].lun, 4)
        self.assertEqual(by_name["devinfo"].start_sector, 3000)
        self.assertEqual(by_name["devinfo"].size_bytes, 4096)
        self.assertEqual(by_name["abl_a"].size_bytes, 1048576)
        self.assertNotIn("BackupGPT", by_name)

    def test_rejects_incomplete_program(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rawprogram4.xml"
            path.write_text('<data><program label="devinfo" /></data>', encoding="utf-8")
            with self.assertRaises(action5_edl.Action5Error):
                action5_edl.parse_rawprogram_files([path])


class SafetyTests(unittest.TestCase):
    def test_read_commands_are_allowed(self):
        for command in ("printgpt", "gpt", "rl", "rs"):
            action5_edl.assert_read_only_edl_args([command])

    def test_write_and_erase_commands_are_rejected(self):
        for command in ("w", "ws", "wl", "e", "reset", "setactiveslot"):
            with self.assertRaises(action5_edl.Action5Error):
                action5_edl.assert_read_only_edl_args([command])


class ActiveSlotTests(unittest.TestCase):
    def test_best_effort_active_parser(self):
        text = "abl_a: Offset 0x1, Length 0x2, Active True\nabl_b: Active False\n"
        self.assertEqual(action5_edl.parse_active_slots(text), {"abl_a": True, "abl_b": False})


class PythonPathTests(unittest.TestCase):
    def test_keeps_explicit_virtualenv_launcher_path(self):
        with tempfile.TemporaryDirectory() as directory:
            launcher = Path(directory) / "python"
            launcher.symlink_to(Path(action5_edl.sys.executable))
            with mock.patch.object(action5_edl.Path, "cwd", return_value=Path(directory)):
                selected = action5_edl.python_for_edl(str(launcher), Path(directory) / "edl.py")
        self.assertEqual(selected, str(launcher.absolute()))


if __name__ == "__main__":
    unittest.main()
