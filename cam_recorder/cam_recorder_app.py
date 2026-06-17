import sys
import os
import glob
import datetime
import threading

# Import cv2 first so it sets its own QT_QPA_PLATFORM_PLUGIN_PATH.
# Then we override it to use system Qt5 before PyQt5's QApplication is created.
import cv2
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = \
    "/usr/lib/x86_64-linux-gnu/qt5/plugins/platforms"

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QFileDialog, QLineEdit, QGroupBox,
    QStatusBar, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap


def list_video_devices():
    devices = sorted(glob.glob("/dev/video*"))
    return [d for d in devices if os.path.exists(d)]


RESOLUTIONS = {
    "640x480 (VGA)": (640, 480),
    "1280x720 (HD)": (1280, 720),
    "1920x1080 (FHD)": (1920, 1080),
    "1280x960": (1280, 960),
    "320x240 (QVGA)": (320, 240),
}

FPS_OPTIONS = [15, 30, 60]


class CamRecorderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("USB Camera Recorder")
        self.setMinimumSize(900, 650)

        self.cap = None
        self.writer = None
        self.recording = False
        self.frame_count = 0
        self.record_start_time = None
        self.record_lock = threading.Lock()

        self._build_ui()

        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self._update_preview)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # --- Left: preview ---
        self.preview_label = QLabel("Camera preview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background: #111; color: #aaa;")
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.preview_label, stretch=3)

        # --- Right: controls ---
        ctrl_panel = QWidget()
        ctrl_panel.setFixedWidth(260)
        ctrl_layout = QVBoxLayout(ctrl_panel)
        ctrl_layout.setAlignment(Qt.AlignTop)
        root.addWidget(ctrl_panel)

        # Camera settings
        cam_group = QGroupBox("Camera Settings")
        cam_layout = QVBoxLayout(cam_group)

        cam_layout.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self._refresh_devices()
        cam_layout.addWidget(self.device_combo)

        refresh_btn = QPushButton("Refresh Devices")
        refresh_btn.clicked.connect(self._refresh_devices)
        cam_layout.addWidget(refresh_btn)

        cam_layout.addWidget(QLabel("Resolution:"))
        self.res_combo = QComboBox()
        for name in RESOLUTIONS:
            self.res_combo.addItem(name)
        self.res_combo.setCurrentText("640x480 (VGA)")
        cam_layout.addWidget(self.res_combo)

        cam_layout.addWidget(QLabel("FPS:"))
        self.fps_combo = QComboBox()
        for fps in FPS_OPTIONS:
            self.fps_combo.addItem(str(fps))
        self.fps_combo.setCurrentText("30")
        cam_layout.addWidget(self.fps_combo)

        self.open_btn = QPushButton("Open Camera")
        self.open_btn.clicked.connect(self._toggle_camera)
        cam_layout.addWidget(self.open_btn)

        ctrl_layout.addWidget(cam_group)

        # Recording settings
        rec_group = QGroupBox("Recording")
        rec_layout = QVBoxLayout(rec_group)

        rec_layout.addWidget(QLabel("Save Directory:"))
        dir_row = QHBoxLayout()
        self.save_dir_edit = QLineEdit(os.path.expanduser("~/Videos"))
        dir_row.addWidget(self.save_dir_edit)
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(30)
        browse_btn.clicked.connect(self._browse_dir)
        dir_row.addWidget(browse_btn)
        rec_layout.addLayout(dir_row)

        rec_layout.addWidget(QLabel("Codec:"))
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["mp4v (MP4)", "XVID (AVI)", "MJPG (AVI)"])
        rec_layout.addWidget(self.codec_combo)

        self.record_btn = QPushButton("Start Recording")
        self.record_btn.setEnabled(False)
        self.record_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        self.record_btn.clicked.connect(self._toggle_recording)
        rec_layout.addWidget(self.record_btn)

        ctrl_layout.addWidget(rec_group)

        # Info
        info_group = QGroupBox("Info")
        info_layout = QVBoxLayout(info_group)
        self.info_label = QLabel("Not connected")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        ctrl_layout.addWidget(info_group)

        ctrl_layout.addStretch()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _refresh_devices(self):
        current = self.device_combo.currentText()
        self.device_combo.clear()
        for d in list_video_devices():
            self.device_combo.addItem(d)
        idx = self.device_combo.findText(current)
        if idx >= 0:
            self.device_combo.setCurrentIndex(idx)

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Save Directory",
                                              self.save_dir_edit.text())
        if d:
            self.save_dir_edit.setText(d)

    def _toggle_camera(self):
        if self.cap is not None:
            self._close_camera()
        else:
            self._open_camera()

    def _open_camera(self):
        device = self.device_combo.currentText()
        if not device:
            self.status_bar.showMessage("No device selected")
            return

        res_text = self.res_combo.currentText()
        width, height = RESOLUTIONS[res_text]
        fps = int(self.fps_combo.currentText())

        cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

        if not cap.isOpened():
            self.status_bar.showMessage(f"Failed to open {device}")
            return

        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)

        self.cap = cap
        self.open_btn.setText("Close Camera")
        self.record_btn.setEnabled(True)
        self.info_label.setText(
            f"Device: {device}\n"
            f"Resolution: {actual_w}x{actual_h}\n"
            f"FPS: {actual_fps:.1f}"
        )

        interval_ms = max(1, int(1000 / (actual_fps if actual_fps > 0 else 30)))
        self.preview_timer.start(interval_ms)
        self.status_bar.showMessage(f"Opened {device} @ {actual_w}x{actual_h} {actual_fps:.0f}fps")

    def _close_camera(self):
        if self.recording:
            self._stop_recording()
        self.preview_timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.open_btn.setText("Open Camera")
        self.record_btn.setEnabled(False)
        self.preview_label.setText("Camera preview")
        self.info_label.setText("Not connected")
        self.status_bar.showMessage("Camera closed")

    def _update_preview(self):
        if self.cap is None:
            return
        ret, frame = self.cap.read()
        if not ret:
            return

        if self.recording:
            with self.record_lock:
                if self.writer is not None:
                    self.writer.write(frame)
                    self.frame_count += 1
            elapsed = (datetime.datetime.now() - self.record_start_time).total_seconds()
            self.status_bar.showMessage(
                f"Recording... {elapsed:.1f}s  |  {self.frame_count} frames"
            )
            # Red dot overlay
            cv2.circle(frame, (20, 20), 10, (0, 0, 255), -1)

        self._display_frame(frame)

    def _display_frame(self, frame):
        h, w, ch = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qt_img)
        scaled = pix.scaled(
            self.preview_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)

    def _toggle_recording(self):
        if self.recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        if self.cap is None:
            return

        save_dir = self.save_dir_edit.text()
        os.makedirs(save_dir, exist_ok=True)

        codec_text = self.codec_combo.currentText()
        if "mp4v" in codec_text:
            fourcc_str, ext = "mp4v", ".mp4"
        elif "XVID" in codec_text:
            fourcc_str, ext = "XVID", ".avi"
        else:
            fourcc_str, ext = "MJPG", ".avi"

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(save_dir, f"recording_{ts}{ext}")

        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = float(self.fps_combo.currentText())

        fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
        writer = cv2.VideoWriter(filename, fourcc, fps, (width, height))
        if not writer.isOpened():
            self.status_bar.showMessage(f"Failed to open video writer: {filename}")
            return

        with self.record_lock:
            self.writer = writer
            self.frame_count = 0
            self.record_start_time = datetime.datetime.now()

        self.recording = True
        self.record_btn.setText("Stop Recording")
        self.record_btn.setStyleSheet("background: #c0392b; color: white; font-weight: bold; padding: 8px;")
        self.status_bar.showMessage(f"Recording to {filename}")

    def _stop_recording(self):
        self.recording = False
        with self.record_lock:
            if self.writer is not None:
                self.writer.release()
                self.writer = None
        elapsed = (datetime.datetime.now() - self.record_start_time).total_seconds() if self.record_start_time else 0
        self.record_btn.setText("Start Recording")
        self.record_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        self.status_bar.showMessage(
            f"Recording saved. Duration: {elapsed:.1f}s  |  Frames: {self.frame_count}"
        )

    def closeEvent(self, event):
        self._close_camera()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = CamRecorderWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
