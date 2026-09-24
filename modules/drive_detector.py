import os
import psutil


def find_camera_sources():

    drives = []

    for partition in psutil.disk_partitions():

        try:

            paths_to_test = [
                os.path.join(partition.mountpoint, "DCIM")
            ]

            for test_path in paths_to_test:

                if os.path.exists(test_path):
                    drives.append(test_path)

        except Exception:
            pass

    return drives
