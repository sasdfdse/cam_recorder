# cam_recorder
USB camera live preview and video recorder with PyQt5 GUI

# cam_recorder

USB 카메라 라이브 프리뷰 및 영상 녹화 패키지.  
PyQt5 GUI로 카메라 미리보기와 녹화를 제어하며, 기존 `robocup_vision`의 `usb_cam` V4L2 드라이버 구조를 참고해 OpenCV + V4L2 백엔드로 캡처합니다.

## 기능

- `/dev/video*` 디바이스 자동 탐색
- 해상도 선택: 320x240 / 640x480 / 1280x720 / 1280x960 / 1920x1080
- FPS 선택: 15 / 30 / 60
- 라이브 프리뷰 (녹화 중 빨간 점 오버레이)
- 저장 포맷: mp4v(.mp4), XVID(.avi), MJPG(.avi)
- 저장 경로 및 파일명 자동 타임스탬프 (`recording_YYYYMMDD_HHMMSS`)

## 의존성

- PyQt5
- OpenCV (`python3-opencv`)

## 빌드 및 실행

```bash
colcon build --packages-select cam_recorder
source install/setup.bash

# 직접 실행
ros2 run cam_recorder cam_recorder

# 런치파일
ros2 launch cam_recorder cam_recorder.launch.py
