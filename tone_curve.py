import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QComboBox, QWidget
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QPoint

class ToneCurveWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(256, 256)
        self.curve = np.linspace(0, 255, 256).astype(np.uint8)
        self.drawing = False
        self.last_point = QPoint()
        self.update_curve()

    def reset_curve(self):
        self.curve = np.linspace(0, 255, 256).astype(np.uint8)
        self.update_curve()

    def update_curve(self):
        self.image = np.zeros((256, 256, 3), dtype=np.uint8)
        self.image.fill(255)

        # Draw 45 degree and -45 degree lines
        for i in range(256):
            self.image[i, i] = [200, 200, 200]
            if i % 2 == 0:
                self.image[i, 255 - i] = [200, 200, 200]

        for i in range(255):
            self.image[255 - self.curve[i], i] = [0, 0, 0]
            self.image[255 - self.curve[i + 1], i + 1] = [0, 0, 0]
            cv2.line(self.image, (i, 255 - self.curve[i]), (i + 1, 255 - self.curve[i + 1]), (0, 0, 0))

        self.setPixmap(QPixmap.fromImage(QImage(self.image.data, 256, 256, 3 * 256, QImage.Format_RGB888)))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()
            self.curve[self.last_point.x()] = 255 - self.last_point.y()
            self.update_curve()

    def mouseMoveEvent(self, event):
        if self.drawing:
            point = event.pos()
            if 0 <= point.x() < 256 and 0 <= point.y() < 256:
                self.draw_line(self.last_point, point)
                self.last_point = point
                self.update_curve()

    def draw_line(self, start_point, end_point):
        x0, y0 = start_point.x(), start_point.y()
        x1, y1 = end_point.x(), end_point.y()

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            if 0 <= x0 < 256 and 0 <= y0 < 256:
                self.curve[x0] = 255 - y0
            if x0 == x1 and y0 == y1:
                break
            e2 = err * 2
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False

class ImageProcessor:
    def __init__(self):
        self.image = None
        self.processed_image = None

    def load_image(self, path):
        self.image = cv2.imread(path, cv2.IMREAD_COLOR)
        self.processed_image = self.image.copy()

    def apply_tone_curve(self, curve):
        if self.image is not None:
            gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
            self.processed_image = cv2.LUT(gray, curve)

    def get_processed_image(self):
        if self.processed_image is not None:
            height, width = self.processed_image.shape
            qimg = QImage(self.processed_image.data, width, height, QImage.Format_Grayscale8)
            return QPixmap.fromImage(qimg)
        return QPixmap()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('インタラクティブなトーンカーブ実験ツール')
        self.tone_curve_widget = ToneCurveWidget()
        self.image_processor = ImageProcessor()
        self.image_label = QLabel()
        self.image_label.setFixedSize(256, 256)

        load_button = QPushButton('画像を読み込む')
        load_button.clicked.connect(self.load_image)

        reset_button = QPushButton('リセット')
        reset_button.clicked.connect(self.reset_curve)

        curve_selector = QComboBox()
        curve_selector.addItems(['ガンマ補正', '線形', '対数', '逆対数'])
        curve_selector.currentIndexChanged.connect(self.select_preset_curve)

        layout = QVBoxLayout()
        layout.addWidget(load_button)
        layout.addWidget(self.image_label)
        layout.addWidget(reset_button)
        layout.addWidget(curve_selector)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.tone_curve_widget)
        main_layout.addLayout(layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.tone_curve_widget.mouseMoveEvent = self.wrap_event(self.tone_curve_widget.mouseMoveEvent)
        self.tone_curve_widget.mouseReleaseEvent = self.wrap_event(self.tone_curve_widget.mouseReleaseEvent)

    def wrap_event(self, func):
        def wrapper(event):
            func(event)
            self.update_image()
        return wrapper

    def load_image(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "画像を選択", "", "Images (*.png *.jpg *.bmp)", options=options)
        if file_name:
            self.image_processor.load_image(file_name)
            self.update_image()

    def reset_curve(self):
        self.tone_curve_widget.reset_curve()
        self.update_image()

    def select_preset_curve(self, index):
        if index == 0:
            gamma = 2.2
            self.tone_curve_widget.curve = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)], dtype=np.uint8)
        elif index == 1:
            self.tone_curve_widget.curve = np.linspace(0, 255, 256).astype(np.uint8)
        elif index == 2:
            self.tone_curve_widget.curve = np.array([np.log2(1 + i) / np.log2(256) * 255 for i in range(256)], dtype=np.uint8)
        elif index == 3:
            self.tone_curve_widget.curve = np.array([255 * (1 - np.log2(1 + (255 - i)) / np.log2(256)) for i in range(256)], dtype=np.uint8)
        self.tone_curve_widget.update_curve()
        self.update_image()

    def update_image(self):
        self.image_processor.apply_tone_curve(self.tone_curve_widget.curve)
        self.image_label.setPixmap(self.image_processor.get_processed_image())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
