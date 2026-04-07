"""Data collection node — records GoPro images + robot state to HDF5."""

import csv
import threading
from collections import deque
from datetime import datetime
from pathlib import Path

import cv2
import h5py
import numpy as np
import pandas as pd
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import CompressedImage
from geometry_msgs.msg import PoseStamped
from tqdm import tqdm


class DataCollector(Node):
    def __init__(self):
        super().__init__("gopro_data_collector")

        # --- Parameters ---
        self.declare_parameter("video_topic", "/gopro/image_raw/compressed")
        self.declare_parameter("ee_pose_topic", "/robot/ee_pose")
        self.declare_parameter("target_action_topic", "/robot/target_action")
        self.declare_parameter("task_name", "gopro_task")
        self.declare_parameter("output_dir", "data_dir/dataset")
        self.declare_parameter("no_gui", False)
        self.declare_parameter("use_audio", False)

        self.video_topic = self.get_parameter("video_topic").value
        self.ee_pose_topic = self.get_parameter("ee_pose_topic").value
        self.target_action_topic = self.get_parameter("target_action_topic").value
        self.task_name = self.get_parameter("task_name").value
        self.output_dir = self.get_parameter("output_dir").value
        self.no_gui = self.get_parameter("no_gui").value
        self.use_audio = self.get_parameter("use_audio").value

        # --- Session paths ---
        self.session_ts = datetime.now().strftime("%m.%d-%H:%M")
        self.root_dir = Path(self.output_dir) / self.task_name / self.session_ts
        self.img_dir = self.root_dir / "images"
        self.state_path = self.root_dir / "states.csv"
        self.hdf5_path = self.root_dir / f"data_{self.session_ts}.hdf5"
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.img_dir.mkdir(parents=True, exist_ok=True)

        # --- Buffers ---
        self.video_buffer = deque()
        self.ee_pose_buffer = deque()
        self.target_action_buffer = deque()
        self.buffer_lock = threading.Lock()
        self.is_recording = False

        # --- Audio (optional) ---
        self.audio_file = None
        self.sample_rate = 44100
        self.num_channels = 1
        self.subtype = "FLOAT"
        self.audio_info_received = threading.Event()
        self.aud_dir = self.root_dir / "audio"
        self.wav_path = self.aud_dir / f"audio_{self.session_ts}.wav"

        # --- Subscriptions ---
        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.create_subscription(CompressedImage, self.video_topic, self._on_video, qos)
        self.create_subscription(PoseStamped, self.ee_pose_topic, self._on_ee_pose, qos)
        self.create_subscription(
            PoseStamped, self.target_action_topic, self._on_target_action, qos
        )

        if self.use_audio:
            self.aud_dir.mkdir(parents=True, exist_ok=True)
            try:
                from sounddevice_ros.msg import AudioInfo, AudioData

                self.create_subscription(AudioData, "/audio", self._on_audio, qos)
                self.create_subscription(AudioInfo, "/audio_info", self._on_audio_info, 10)
            except ImportError:
                self.get_logger().warn(
                    "sounddevice_ros not found — audio recording disabled"
                )
                self.use_audio = False

        self.get_logger().info(f"Session: {self.session_ts} | Output: {self.root_dir}")

    # --- Callbacks ---
    def _on_video(self, msg: CompressedImage) -> None:
        if not self.is_recording:
            return
        ts = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        frame = cv2.imdecode(np.frombuffer(msg.data, np.uint8), cv2.IMREAD_COLOR)
        with self.buffer_lock:
            self.video_buffer.append((frame, ts))

    def _on_ee_pose(self, msg: PoseStamped) -> None:
        if not self.is_recording:
            return
        ts = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        p = msg.pose.position
        q = msg.pose.orientation
        with self.buffer_lock:
            self.ee_pose_buffer.append((ts, p.x, p.y, p.z, q.x, q.y, q.z, q.w))

    def _on_target_action(self, msg: PoseStamped) -> None:
        if not self.is_recording:
            return
        ts = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        p = msg.pose.position
        q = msg.pose.orientation
        with self.buffer_lock:
            self.target_action_buffer.append((ts, p.x, p.y, p.z, q.x, q.y, q.z, q.w))

    def _on_audio_info(self, msg) -> None:
        if not self.audio_info_received.is_set():
            self.sample_rate = msg.sample_rate
            self.num_channels = msg.num_channels
            if msg.subtype:
                self.subtype = msg.subtype
            self.audio_info_received.set()
            self.get_logger().info(f"Audio configured: {self.sample_rate}Hz")

    def _on_audio(self, msg) -> None:
        if not self.is_recording or self.audio_file is None:
            return
        try:
            audio_data = np.asarray(msg.data).reshape((-1, self.num_channels))
            self.audio_file.write(audio_data)
        except Exception as e:
            self.get_logger().warn(f"Audio write failed: {e}")

    # --- Processing ---
    def process_episode(self) -> None:
        with self.buffer_lock:
            local_video = list(self.video_buffer)
            local_pose = list(self.ee_pose_buffer)
            local_action = list(self.target_action_buffer)

        if not local_video:
            self.get_logger().error("No data to process")
            return

        pose_df = pd.DataFrame(
            local_pose, columns=["ts", "PX", "PY", "PZ", "QX", "QY", "QZ", "QW"]
        )
        action_df = pd.DataFrame(
            local_action, columns=["ts", "AX", "AY", "AZ", "AQX", "AQY", "AQZ", "AQW"]
        )

        data_dict = {"img": [], "qpos": [], "action": []}
        show_progress = not self.no_gui
        iterator = tqdm(range(len(local_video)), desc="Processing") if show_progress else range(len(local_video))

        # Write CSV header if new
        if not self.state_path.exists():
            with open(self.state_path, "w", newline="") as f:
                csv.writer(f).writerow(
                    ["Idx", "TS", "PX", "PY", "PZ", "QX", "QY", "QZ", "QW",
                     "AX", "AY", "AZ", "AQX", "AQY", "AQZ", "AQW"]
                )

        with open(self.state_path, "a", newline="") as f:
            writer = csv.writer(f)
            for i in iterator:
                frame, frame_ts = local_video[i]
                cv2.imwrite(str(self.img_dir / f"frame_{i:05d}.jpg"), frame)

                if not pose_df.empty:
                    p_idx = (pose_df["ts"] - frame_ts).abs().argmin()
                    pose = pose_df.iloc[p_idx][1:].tolist()
                else:
                    pose = [0.0] * 7

                if not action_df.empty:
                    a_idx = (action_df["ts"] - frame_ts).abs().argmin()
                    action = action_df.iloc[a_idx][1:].tolist()
                else:
                    action = [0.0] * 7

                data_dict["img"].append(frame)
                data_dict["qpos"].append(pose)
                data_dict["action"].append(action)
                writer.writerow([i, frame_ts, *pose, *action])

        self.get_logger().info("Saving HDF5...")
        with h5py.File(self.hdf5_path, "w") as h5:
            obs = h5.create_group("observations")
            obs.create_dataset(
                "images/front",
                data=np.array(data_dict["img"], dtype=np.uint8),
                compression="gzip",
            )
            obs.create_dataset(
                "qpos", data=np.array(data_dict["qpos"], dtype=np.float32)
            )
            h5.create_dataset(
                "action", data=np.array(data_dict["action"], dtype=np.float32)
            )
        self.get_logger().info(
            f"Saved {len(local_video)} frames to {self.hdf5_path}"
        )


def main(args=None):
    rclpy.init(args=args)
    node = DataCollector()

    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    try:
        # Wait for audio info if needed
        if node.use_audio:
            print(f"\n[Session: {node.session_ts}] Waiting for audio info...")
            while rclpy.ok() and not node.audio_info_received.wait(timeout=0.1):
                pass

        input("\nPress Enter to START recording...")

        if node.use_audio:
            import soundfile as sf

            with sf.SoundFile(
                str(node.wav_path),
                mode="x",
                samplerate=node.sample_rate,
                channels=node.num_channels,
                subtype=node.subtype,
            ) as node.audio_file:
                node.is_recording = True
                input("RECORDING... Press Enter to STOP.\n")
                node.is_recording = False
            node.audio_file = None
        else:
            node.is_recording = True
            input("RECORDING... Press Enter to STOP.\n")
            node.is_recording = False

        node.process_episode()
        print("Done.")

    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
