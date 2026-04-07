# gopro_ros2

ROS2 package for GoPro video streaming and robot data collection via USB capture card.

## Overview

```
GoPro --HDMI--> Capture Card --USB3.0--> PC --ROS2 Topic--> Data Collection
```

- **Streamer** : GoPro 1080p60 -> `/gopro/image_raw/compressed`
- **Collector** : Synchronized video + robot pose -> HDF5 (ACT / Diffusion Policy compatible)
- **TCP Transform** : Tracker pose -> Robot base-frame TCP coordinates

## Hardware

| Item | Note |
|------|------|
| GoPro (Hero 9+) | Install [GoPro Labs firmware](https://gopro.com/en/us/info/gopro-labs), scan QR code in `asset/` for clean HDMI output |
| USB Capture Card | [Elgato HD60 X](https://www.amazon.com/dp/B09V1KJ3J4) (USB 3.0 required) |
| HDMI Cable | GoPro HDMI out -> Capture card in |

Connection: **GoPro --HDMI--> Elgato HD60 X --USB 3.0--> PC**

> If the stream doesn't show up, unplug the Elgato cable and reconnect.

## Install

```bash
cd ~/colcon_ws/src
git clone https://github.com/kingchou007/gopro_ros2.git

pip install opencv-python numpy h5py pandas scipy tqdm

cd ~/colcon_ws
colcon build --packages-select gopro_ros2
source install/setup.bash
```

## Quick Start

**Terminal 1** - Start GoPro streaming:
```bash
ros2 run gopro_ros2 gopro_stream
# or via launch file
ros2 launch gopro_ros2 gopro_stream.launch.py
```

**Terminal 2** - Collect data:
```bash
ros2 run gopro_ros2 data_collect
# Press Enter to start recording, Enter again to stop
```

## Streamer Parameters

```bash
ros2 run gopro_ros2 gopro_stream --ros-args \
  -p width:=1920 \
  -p height:=1080 \
  -p fps:=60 \
  -p image_topic:=/gopro/image_raw \
  -p frame_id:=gopro_camera \
  -p jpeg_quality:=90 \
  -p no_gui:=false \
  -p preview_scale:=0.5
```

## Collector Parameters

```bash
ros2 run gopro_ros2 data_collect --ros-args \
  -p task_name:=my_task \
  -p output_dir:=data_dir/dataset \
  -p video_topic:=/gopro/image_raw/compressed \
  -p ee_pose_topic:=/robot/ee_pose \
  -p target_action_topic:=/robot/target_action \
  -p use_audio:=false
```

Output:
```
data_dir/dataset/<task_name>/<MM.DD-HH:MM>/
  images/frame_00000.jpg ...
  states.csv
  data_<timestamp>.hdf5
```

HDF5 format:
```
/observations/images/front   (N, H, W, 3) uint8
/observations/qpos           (N, 7)        float32  [x, y, z, qx, qy, qz, qw]
/action                      (N, 7)        float32  [x, y, z, qx, qy, qz, qw]
```

## TCP Transform

Convert tracker recordings to robot TCP coordinates:

```bash
# Single file
ros2 run gopro_ros2 tcp_transform --input raw.h5 --output tcp.h5 --skip 10

# Batch mode (uses paths from config)
ros2 run gopro_ros2 tcp_transform --batch --config config/default.json
```

Edit `config/default.json` to set your robot's base pose and tool offset before running.

## ROS2 Topics

| Topic | Type | Direction |
|-------|------|-----------|
| `/gopro/image_raw/compressed` | `sensor_msgs/CompressedImage` | Published by streamer |
| `/robot/ee_pose` | `geometry_msgs/PoseStamped` | Subscribed by collector |
| `/robot/target_action` | `geometry_msgs/PoseStamped` | Subscribed by collector |

## Package Structure

```
gopro_ros2/
├── gopro_ros2/
│   ├── video_capture.py       # Threaded MJPEG capture (V4L2)
│   ├── streamer_node.py       # GoPro -> CompressedImage publisher
│   ├── collector_node.py      # Video + pose -> HDF5 recorder
│   └── tcp_transform.py       # Tracker -> TCP coordinate transform
├── config/default.json        # Robot & processing config
├── launch/gopro_stream.launch.py
└── asset/                     # GoPro Labs QR code
```
