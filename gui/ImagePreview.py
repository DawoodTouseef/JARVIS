from PyQt5.QtWidgets import (
     QLabel, QVBoxLayout,   QDialog
)

import cv2
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt



class ImagePreviewDialog(QDialog):
    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Captured Image Preview")
        self.setModal(False)  # Non-modal so code can continue

        # Convert OpenCV BGR image to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Convert to QImage
        h, w, ch = image_rgb.shape
        bytes_per_line = ch * w
        q_image = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Create pixmap and scale it
        pixmap = QPixmap.fromImage(q_image)
        pixmap = pixmap.scaled(640, 480, Qt.KeepAspectRatio)

        # Setup UI
        layout = QVBoxLayout()
        self.image_label = QLabel()
        self.image_label.setPixmap(pixmap)
        layout.addWidget(self.image_label)
        self.setLayout(layout)

        # Adjust window size to image
        self.adjustSize()