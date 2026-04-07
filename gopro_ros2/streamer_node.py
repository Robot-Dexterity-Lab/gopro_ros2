"""GoPro ROS2 streamer node — captures video via USB capture card and publishes CompressedImage."""

import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import CompressedImage

from gopro_ros2.video_capture import (
    FastVideoCapture,
    configure_display,
    get_v4l_devices,
)


class GoProStreamer(Node):
    def __init__(self):
        super().__init__("gopro_streamer")

        # --- ROS2 Parameters ---
        self.declare_parameter("camera_idx", 0)
        self.declare_parameter("dev_path", "")
        self.declare_parameter("image_topic", "/gopro/image_raw")
        self.declare_parameter("frame_id", "gopro_camera")
        self.declare_parameter("qos_depth", 10)
        self.declare_parameter("width", 1920)
        self.declare_parameter("height", 1080)
        self.declare_parameter("fps", 60)
        self.declare_parameter("jpeg_quality", 90)
        self.declare_parameter("no_gui", False)
        self.declare_parameter("preview_scale", 0.5)
        self.declare_parameter("preview_fps", 30)

        self.camera_idx = self.get_parameter("camera_idx").value
        self.dev_path = self.get_parameter("dev_path").value
        self.image_topic = self.get_parameter("image_topic").value
        self.frame_id = self.get_parameter("frame_id").value
        self.qos_depth = self.get_parameter("qos_depth").value
        self.width = self.get_parameter("width").value
        self.height = self.get_parameter("height").value
        self.fps = self.get_parameter("fps").value
        self.jpeg_quality = self.get_parameter("jpeg_quality").value
        self.no_gui = self.get_parameter("no_gui").value
        self.preview_scale = self.get_parameter("preview_scale").value
        self.preview_fps = self.get_parameter("preview_fps").value

        # --- Publisher ---
        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=self.qos_depth,
        )
        self.image_pub = self.create_publisher(
            CompressedImage, f"{self.image_topic}/compressed", qos
        )
        self.get_logger().info(
            f"Publishing compressed images to {self.image_topic}/compressed"
        )

    def publish_frame(self, frame: np.ndarray) -> None:
        if frame is None:
            return
        msg = CompressedImage()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.format = "jpeg"
        ok, encoded = cv2.imencode(
            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        )
        if ok:
            msg.data = encoded.tobytes()
            self.image_pub.publish(msg)


def main(args=None):
    configure_display()
    rclpy.init(args=args)
    node = GoProStreamer()

    # Resolve device path
    dev_path = node.dev_path
    if not dev_path:
        devices = get_v4l_devices()
        if not devices:
            node.get_logger().fatal("No V4L2 devices found")
            node.destroy_node()
            rclpy.shutdown()
            return
        if node.camera_idx >= len(devices):
            node.get_logger().fatal(
                f"camera_idx={node.camera_idx} but only {len(devices)} device(s) found"
            )
            node.destroy_node()
            rclpy.shutdown()
            return
        dev_path = devices[node.camera_idx]

    node.get_logger().info(
        f"Opening {dev_path} @ {node.width}x{node.height} {node.fps}fps (MJPEG)"
    )

    try:
        capture = FastVideoCapture(dev_path, node.width, node.height, node.fps)
        capture.start()
    except RuntimeError as e:
        node.get_logger().fatal(str(e))
        node.destroy_node()
        rclpy.shutdown()
        return

    vis_interval = 1.0 / node.preview_fps
    last_vis = 0.0

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0)
            ret, frame = capture.read()

            if ret and frame is not None:
                node.publish_frame(frame)

                if not node.no_gui:
                    now = time.time()
                    if now - last_vis > vis_interval:
                        last_vis = now
                        h, w = frame.shape[:2]
                        s = node.preview_scale
                        preview = cv2.resize(
                            frame,
                            (int(w * s), int(h * s)),
                            interpolation=cv2.INTER_NEAREST,
                        )
                        cv2.imshow("GoPro", preview)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
            else:
                time.sleep(0.001)
    except KeyboardInterrupt:
        pass
    finally:
        capture.stop()
        node.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
