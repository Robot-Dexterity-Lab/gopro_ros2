ARG ROS_DISTRO=humble
FROM ros:${ROS_DISTRO}

ENV DEBIAN_FRONTEND=noninteractive

# V4L2 + GUI dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-opencv \
    v4l-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
RUN pip3 install --no-cache-dir numpy opencv-python h5py pandas scipy tqdm

# Copy package
WORKDIR /ros2_ws/src/gopro_ros2
COPY . .

# Build
ARG ROS_DISTRO=humble
WORKDIR /ros2_ws
RUN /bin/bash -c "source /opt/ros/${ROS_DISTRO}/setup.bash && colcon build --packages-select gopro_ros2"

# Source workspace on entry
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /root/.bashrc && \
    echo "source /ros2_ws/install/setup.bash" >> /root/.bashrc

CMD ["/bin/bash"]
