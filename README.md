# cam_recorder

A USB camera live preview and video recording package.

This package provides a PyQt5-based GUI for camera preview and recording control. Video capture is implemented using an OpenCV + V4L2 backend, following the architecture of the `usb_cam` V4L2 driver used in `robocup_vision`.

## Features

* Automatic detection of `/dev/video*` devices
* Selectable resolutions:

  * 320×240
  * 640×480
  * 1280×720
  * 1280×960
  * 1920×1080
* Selectable frame rates:

  * 15 FPS
  * 30 FPS
  * 60 FPS
* Live camera preview
* Recording status indicator (red dot overlay during recording)
* Supported output formats:

  * MP4V (`.mp4`)
  * XVID (`.avi`)
  * MJPG (`.avi`)
* Automatic timestamp-based filenames:

  * `recording_YYYYMMDD_HHMMSS`

## Dependencies

* PyQt5
* OpenCV (`python3-opencv`)

## Build and Run

```bash
colcon build --packages-select cam_recorder
source install/setup.bash

# Run
ros2 launch cam_recorder cam_recorder.launch.py
```
