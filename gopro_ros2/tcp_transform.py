"""Transform tracker poses to robot TCP (Tool Center Point) coordinates.

Converts raw tracker data (translation + quaternion) from HDF5 files into
robot base-frame TCP poses, with configurable base pose and offset compensation.

Usage:
    # Single file
    ros2 run gopro_ros2 tcp_transform --input raw.h5 --output tcp.h5

    # Batch mode (process entire directory)
    ros2 run gopro_ros2 tcp_transform --batch --config config.json
"""

import argparse
import json
import os

import h5py
import numpy as np
from scipy.spatial.transform import Rotation as R


def load_config(config_path: str) -> dict:
    with open(config_path, "r") as f:
        return json.load(f)["data_process_config"]


def transform_to_base(x, y, z, qx, qy, qz, qw, T_base_to_local):
    """Transform a pose from tracker frame to robot base frame."""
    rot_local = R.from_quat([qx, qy, qz, qw]).as_matrix()

    T_local = np.eye(4)
    T_local[:3, :3] = rot_local
    T_local[:3, 3] = [x, y, z]

    rot_base = T_local[:3, :3] @ T_base_to_local[:3, :3]
    pos_base = T_base_to_local[:3, 3] + T_local[:3, 3]

    quat_base = R.from_matrix(rot_base).as_quat()
    return (*pos_base, *quat_base)


def process_file(input_file: str, output_file: str, config: dict, skip: int = 10):
    """Process a single HDF5 file: tracker coords -> TCP coords."""
    bp = config["base_position"]
    bo = config["base_orientation"]
    offset = config["offset"]

    base_rpy = np.deg2rad([bo["roll"], bo["pitch"], bo["yaw"]])
    rot_base = R.from_euler("xyz", base_rpy).as_matrix()

    T_base_to_local = np.eye(4)
    T_base_to_local[:3, :3] = rot_base
    T_base_to_local[:3, 3] = [bp["x"], bp["y"], bp["z"]]

    try:
        with h5py.File(input_file, "r") as f_in:
            translation = f_in["translation"][::skip]
            rotation = f_in["rotation"][::skip]

            n = len(translation)
            qpos = np.zeros((n, 7))

            for i in range(n):
                x, y, z = translation[i]
                qx, qy, qz, qw = rotation[i]

                # Apply pre-offset
                x -= offset["x"]
                z += offset["z"]

                bx, by, bz, bqx, bqy, bqz, bqw = transform_to_base(
                    x, y, z, qx, qy, qz, qw, T_base_to_local
                )

                # Apply tool offset along orientation axes
                ori = R.from_quat([bqx, bqy, bqz, bqw]).as_matrix()
                pos = np.array([bx, by, bz])
                pos += offset["x"] * ori[:, 2]
                pos -= offset["z"] * ori[:, 0]

                qpos[i] = [*pos, bqx, bqy, bqz, bqw]

            with h5py.File(output_file, "w") as f_out:
                f_out.create_dataset("action", data=qpos)
                obs = f_out.create_group("observations")
                obs.create_dataset("qpos", data=qpos)

            print(f"Saved {output_file} ({n} samples)")

    except Exception as e:
        print(f"Error processing {input_file}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Tracker pose -> Robot TCP transform")
    parser.add_argument("--input", type=str, default=None, help="Input HDF5 file")
    parser.add_argument("--output", type=str, default=None, help="Output HDF5 file")
    parser.add_argument("--skip", type=int, default=10, help="Subsample every N frames")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config JSON (default: config/default.json in package)",
    )
    parser.add_argument("--batch", action="store_true", help="Process entire directory")
    args = parser.parse_args()

    # Resolve config
    if args.config:
        config_path = args.config
    else:
        try:
            from ament_index_python.packages import get_package_share_directory
            config_path = os.path.join(
                get_package_share_directory("gopro_ros2"), "config", "default.json"
            )
        except ImportError:
            # Fallback for running outside colcon workspace
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config",
                "default.json",
            )
    config = load_config(config_path)

    if args.batch:
        from multiprocessing import Pool, cpu_count
        from tqdm import tqdm

        input_dir = config["input_dir"]
        output_dir = config["output_tcp_dir"]
        os.makedirs(output_dir, exist_ok=True)

        file_pairs = [
            (os.path.join(input_dir, f), os.path.join(output_dir, f))
            for f in os.listdir(input_dir)
            if f.endswith((".h5", ".hdf5"))
        ]

        def _process(pair):
            process_file(pair[0], pair[1], config, skip=args.skip)

        with Pool(cpu_count()) as pool:
            list(tqdm(pool.imap_unordered(_process, file_pairs), total=len(file_pairs)))
    else:
        input_file = args.input or "new.h5"
        output_file = args.output or "output_tcp.h5"
        process_file(input_file, output_file, config, skip=args.skip)


if __name__ == "__main__":
    main()
