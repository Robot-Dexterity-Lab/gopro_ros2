# gopro_ros2

ROS2 package for GoPro video streaming via USB capture card.

## Overview

```
GoPro --HDMI--> Capture Card --USB3.0--> PC --ROS2 Topic-->
```

Publishes GoPro 1080p60 video as `sensor_msgs/CompressedImage` on `/gopro/image_raw/compressed`.

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
git clone https://github.com/Robot-Dexterity-Lab/gopro_ros2.git

pip install opencv-python numpy

cd ~/colcon_ws
colcon build --packages-select gopro_ros2
source install/setup.bash
```

## Quick Start

```bash
ros2 run gopro_ros2 gopro_stream
# or via launch file
ros2 launch gopro_ros2 gopro_stream.launch.py
```

## Parameters

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

## ROS2 Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/gopro/image_raw/compressed` | `sensor_msgs/CompressedImage` | GoPro video stream (JPEG) |
