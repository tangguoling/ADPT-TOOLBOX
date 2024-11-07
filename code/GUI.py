import sys
import os
import cv2
import json
import yaml
import tempfile
import subprocess
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog,
                             QStackedWidget, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QHBoxLayout,
                             QComboBox, QLineEdit, QMessageBox, QGraphicsPixmapItem, QSpinBox, QMenuBar, QAction, QDialog, QTextEdit)
from PyQt5.QtGui import QPixmap, QIcon, QPalette, QImage, QColor
from PyQt5.QtCore import Qt, QRectF

class AnnotateFrame(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.points = {}  # 存储每个动物每个部位的标注点，结构：{animal_id: {body_part: (x, y)}}
        self.point_colors = {}  # 存储每个点的颜色，结构：{animal_id: {body_part: color}}
        self.current_frame_loaded = False  # 标识帧是否加载
        self.original_pixmap = None  # 保存原始图像
        self.current_color = QColor(Qt.red)  # 初始化标注颜色

    def load_frame(self, image):
        """加载并显示图像帧"""
        if image is None:
            return
        height, width, channel = image.shape
        bytes_per_line = 3 * width
        q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        pixmap = QPixmap.fromImage(q_image)
        pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.scene().clear()  # 清空当前场景，确保没有残留点
        self.scene().addPixmap(pixmap)
        self.setSceneRect(QRectF(pixmap.rect()))
        self.original_pixmap = pixmap  # 保存原始图像
        self.points = {}  # 清空标注点
        self.point_colors = {}  # 清空颜色
        self.current_frame_loaded = True

    def set_color(self, color):
        """设置当前标注颜色，确保是 QColor 类型"""
        if isinstance(color, Qt.GlobalColor):
            self.current_color = QColor(color)  # 将全局颜色转换为 QColor
        else:
            self.current_color = color

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.current_frame_loaded:
            pos = self.mapToScene(event.pos())
            parent = self.get_parent_app()
            animal_id = parent.animal_selector.currentIndex() + 1  # 动物编号从1开始
            body_part = parent.region_selector.currentText()  # 获取当前身体部位

            # 初始化动物编号的标注点字典和颜色字典
            if animal_id not in self.points:
                self.points[animal_id] = {}
                self.point_colors[animal_id] = {}

            self.points[animal_id][body_part] = (pos.x(), pos.y())
            self.point_colors[animal_id][body_part] = self.current_color  # 保存颜色

            # 显示标注点
            ellipse = QGraphicsEllipseItem(pos.x() - 2.5, pos.y() - 2.5, 5, 5)
            ellipse.setBrush(self.current_color)
            self.scene().addItem(ellipse)

            # 标注完成后自动跳到下一个部位
            current_index = parent.region_selector.currentIndex()
            if current_index < parent.region_selector.count() - 1:
                parent.region_selector.setCurrentIndex(current_index + 1)
                parent.update_annotation_color()

    def erase_specific_point(self, animal_id, body_part):
        """擦除指定动物编号和部位的点"""
        if animal_id in self.points and body_part in self.points[animal_id]:
            del self.points[animal_id][body_part]  # 删除指定部位的点
            del self.point_colors[animal_id][body_part]  # 删除该部位的颜色
            self.scene().clear()  # 清空整个场景
            self.scene().addPixmap(self.original_pixmap)  # 恢复原始图像
            self.restore_annotations()  # 恢复其余标注点

    def restore_annotations(self):
        """恢复所有标注点"""
        for animal_id, parts in self.points.items():
            for body_part, point in parts.items():
                color = self.point_colors.get(animal_id, {}).get(body_part, self.current_color)
                ellipse = QGraphicsEllipseItem(point[0] - 2.5, point[1] - 2.5, 5, 5)
                ellipse.setBrush(color)
                self.scene().addItem(ellipse)

    def save_annotations(self, frame_index, annotations_file):
        """保存当前帧的标注数据到JSON文件，包括坐标和颜色"""
        annotations = {}
        for animal_id, body_parts in self.points.items():
            annotations[animal_id] = {"joints": {body_part: [x, y, self.point_colors[animal_id][body_part].name()]  # 将颜色保存为#RRGGBB格式
                                                 for body_part, (x, y) in body_parts.items()}}

        if os.path.exists(annotations_file):
            with open(annotations_file, 'r') as file:
                all_annotations = json.load(file)
        else:
            all_annotations = {}

        all_annotations[str(frame_index)] = annotations

        with open(annotations_file, 'w') as file:
            json.dump(all_annotations, file, indent=4)

    def load_annotations(self, frame_index, annotations_file):
        """从JSON文件加载指定帧的标注数据，包括坐标和颜色"""
        if os.path.exists(annotations_file):
            with open(annotations_file, 'r') as file:
                all_annotations = json.load(file)

            if str(frame_index) in all_annotations:
                self.points = {}
                self.point_colors = {}
                for animal_id, data in all_annotations[str(frame_index)].items():
                    self.points[int(animal_id)] = {}
                    self.point_colors[int(animal_id)] = {}
                    for body_part, (x, y, color_hex) in data["joints"].items():
                        self.points[int(animal_id)][body_part] = (x, y)
                        self.point_colors[int(animal_id)][body_part] = QColor(color_hex)  # 恢复颜色

                self.restore_annotations()

    def get_parent_app(self):
        """获取父类对象"""
        parent = self.parentWidget()
        while parent and not isinstance(parent, ADPTApp):
            parent = parent.parentWidget()
        return parent


class ADPTApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ADPT")
        self.setGeometry(100, 100, 1600, 900)
        self.setWindowIcon(QIcon('code/logo.png'))

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        palette = self.palette()
        palette.setColor(QPalette.Window, Qt.black)
        self.setPalette(palette)

        self.video_path = ""
        self.video_length = 0
        self.frame_count = 0
        self.base_output_folder = "output_frames"
        self.annotations_file = ""
        self.current_frame_index = 0
        self.frames_cache = []
        self.config = None
        self.bodyparts = []
        self.bodypart_colors = {}
        self.frame_interval = 1

        self.create_menu()
        self.create_welcome_page()
        self.create_video_extraction_page()
        self.create_annotation_page()
        self.create_training_page()
        self.create_prediction_page()

        self.stacked_widget.addWidget(self.welcome_page)
        self.stacked_widget.addWidget(self.video_extraction_page)
        self.stacked_widget.addWidget(self.annotation_page)
        self.stacked_widget.addWidget(self.training_page)
        self.stacked_widget.addWidget(self.prediction_page)
        self.stacked_widget.setCurrentIndex(0)

    def create_menu(self):
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""QMenuBar {background-color: #333333; color: white;}""")
        welcome_action = QAction("Welcome", self)
        welcome_action.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        menu_bar.addAction(welcome_action)

        extract_action = QAction("Extract Frames", self)
        extract_action.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        menu_bar.addAction(extract_action)

        annotate_action = QAction("Annotate Frames", self)
        annotate_action.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        menu_bar.addAction(annotate_action)

        train_action = QAction("Train Model", self)
        train_action.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        menu_bar.addAction(train_action)

        predict_action = QAction("Analyze Video", self)
        predict_action.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(4))
        menu_bar.addAction(predict_action)

    def create_welcome_page(self):
        self.welcome_page = QWidget()
        layout = QVBoxLayout()

        logo_label = QLabel(self.welcome_page)
        pixmap = QPixmap('code/logo.png')
        logo_width = self.width() - 200
        logo_height = int(logo_width / 16 * 9)
        logo_label.setPixmap(pixmap.scaled(logo_width, logo_height, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignTop | Qt.AlignCenter)
        layout.addWidget(logo_label)

        welcome_message = QLabel("Welcome to ADPT Application")
        welcome_message.setAlignment(Qt.AlignCenter)
        welcome_message.setStyleSheet("color: white; font-size: 30px;")
        layout.addWidget(welcome_message)

        self.welcome_page.setLayout(layout)

    def create_video_extraction_page(self):
        self.video_extraction_page = QWidget()
        layout = QVBoxLayout()

        load_button = QPushButton("Load Video")
        load_button.clicked.connect(self.load_video)
        load_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        layout.addWidget(load_button)

        self.frame_count_input = QLineEdit()
        self.frame_count_input.setPlaceholderText("Enter the number of frames to extract")
        layout.addWidget(self.frame_count_input)

        extract_button = QPushButton("Extract Frames")
        extract_button.clicked.connect(self.extract_frames)
        extract_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        layout.addWidget(extract_button)

        self.video_label = QLabel("No Video Loaded")
        self.video_label.setStyleSheet("color: white;")
        layout.addWidget(self.video_label)

        self.video_length_label = QLabel("Video length: 0 seconds")
        self.video_length_label.setStyleSheet("color: white;")
        layout.addWidget(self.video_length_label)

        self.video_extraction_page.setLayout(layout)

    def create_annotation_page(self):
        self.annotation_page = QWidget()
        layout = QHBoxLayout()

        right_layout = QVBoxLayout()

        # 右上方的 Load Config 和 Edit Config 按钮
        config_button_layout = QHBoxLayout()
        config_button = QPushButton("Load Config")
        config_button.clicked.connect(self.load_config)
        config_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        config_button_layout.addWidget(config_button)

        edit_config_button = QPushButton("Edit Config")
        edit_config_button.clicked.connect(self.edit_config)
        edit_config_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        config_button_layout.addWidget(edit_config_button)

        right_layout.addLayout(config_button_layout)

        # 右下方的选择框和操作按钮
        self.animal_selector = QComboBox()
        self.animal_selector.addItem("Select Animal")
        self.animal_selector.currentIndexChanged.connect(self.update_region_selector)

        self.region_selector = QComboBox()

        control_layout = QVBoxLayout()
        control_layout.addWidget(self.animal_selector)
        control_layout.addWidget(self.region_selector)

        prev_button = QPushButton("Previous Frame")
        prev_button.clicked.connect(self.load_prev_frame)
        control_layout.addWidget(prev_button)

        next_button = QPushButton("Next Frame")
        next_button.clicked.connect(self.load_next_frame)
        control_layout.addWidget(next_button)

        erase_button = QPushButton("Erase Last Point")
        erase_button.clicked.connect(self.erase_point)
        control_layout.addWidget(erase_button)

        right_layout.addLayout(control_layout)

        layout.addLayout(right_layout, 1)

        self.annotation_view = AnnotateFrame(self)
        layout.addWidget(self.annotation_view, 4)

        self.annotation_page.setLayout(layout)

    def erase_point(self):
        animal_id = self.animal_selector.currentIndex() + 1
        body_part = self.region_selector.currentText()
        self.annotation_view.erase_specific_point(animal_id, body_part)

    def update_region_selector(self):
        """每次选择动物后，将部位框自动切换到第一个部位"""
        if self.region_selector.count() > 0:
            self.region_selector.setCurrentIndex(0)
        self.update_annotation_color()

    def update_annotation_color(self):
        """根据选中的部位设置标注颜色"""
        body_part = self.region_selector.currentText()
        if body_part in self.bodypart_colors:
            self.annotation_view.set_color(self.bodypart_colors[body_part])

    def create_training_page(self):
        self.training_page = QWidget()
        layout = QVBoxLayout()

        train_button = QPushButton("Start Training")
        train_button.clicked.connect(self.train_model)
        train_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        layout.addWidget(train_button)

        self.training_page.setLayout(layout)

    def create_prediction_page(self):
        self.prediction_page = QWidget()
        layout = QVBoxLayout()

        config_button = QPushButton("Edit Prediction Config")
        config_button.clicked.connect(self.load_predict_config)
        config_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        layout.addWidget(config_button)

        predict_button = QPushButton("Start Analysis")
        predict_button.clicked.connect(self.predict_video)
        predict_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        layout.addWidget(predict_button)

        self.prediction_page.setLayout(layout)

    def load_video(self):
        """加载视频，创建新目录并清空标注点"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Video", "", "Video Files (*.mp4 *.avi)", options=options)
        if file_path:
            self.video_path = file_path
            cap = cv2.VideoCapture(self.video_path)
            self.frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            self.video_length = self.frame_count / fps
            self.video_label.setText(f"Video Loaded: {file_path}")
            self.video_length_label.setText(f"Video length: {self.video_length:.2f} seconds, {self.frame_count} frames")

            # 使用当前日期和时间创建文件夹
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_name = os.path.splitext(os.path.basename(file_path))[0]
            self.base_output_folder = os.path.join("output_frames", f"{video_name}_{current_time}")
            os.makedirs(self.base_output_folder, exist_ok=True)

            # 设置标注文件路径
            self.annotations_file = os.path.join(self.base_output_folder, "annotations.json")
        else:
            self.video_label.setText("No Video Loaded")

    def load_prev_frame(self):
        if self.current_frame_index > 0:
            self.save_annotations()  # 保存当前帧的标注数据
            self.current_frame_index -= 1
            self.load_frame_by_index(self.current_frame_index)

    def load_next_frame(self):
        if self.current_frame_index < len(self.frames_cache) - 1:
            self.save_annotations()  # 保存当前帧的标注数据
            self.current_frame_index += 1
            self.load_frame_by_index(self.current_frame_index)

    def load_frame_by_index(self, index):
        if 0 <= index < len(self.frames_cache):
            frame = self.frames_cache[index]
            self.annotation_view.load_frame(frame)
            self.annotation_view.load_annotations(self.current_frame_index, self.annotations_file)

    def extract_frames(self):
        if not self.video_path:
            QMessageBox.warning(self, "Warning", "Please load a video first")
            return

        frame_count = int(self.frame_count_input.text())
        cap = cv2.VideoCapture(self.video_path)
        count = 0
        self.frames_cache = []

        while cap.isOpened() and count < frame_count:
            ret, frame = cap.read()
            if not ret:
                break
            self.frames_cache.append(frame)
            count += 1

        cap.release()
        self.video_label.setText(f"Extracted {len(self.frames_cache)} frames")

        if self.frames_cache:
            self.stacked_widget.setCurrentIndex(2)  # 自动切换到标注页面
            self.load_frame_by_index(0)

    def load_config(self):
        options = QFileDialog.Options()
        config_path, _ = QFileDialog.getOpenFileName(self, "Load Config", "", "YAML Files (*.yaml)", options=options)
        if config_path:
            with open(config_path, 'r') as file:
                self.config = yaml.safe_load(file)

            self.bodyparts = self.config.get('bodyparts', [])
            animal_count = self.config.get('num_classes', 1)  # 从num_classes获取动物数量

            color_palette = [Qt.red, Qt.green, Qt.blue, Qt.darkRed, Qt.darkGreen, Qt.darkBlue, Qt.cyan, Qt.magenta, Qt.yellow, Qt.gray, Qt.darkCyan, Qt.darkMagenta, Qt.darkYellow, Qt.darkGray]
            for i, bodypart in enumerate(self.bodyparts):
                color_index = i % len(color_palette)
                self.bodypart_colors[bodypart] = QColor(color_palette[color_index])  # 确保颜色为 QColor

            self.region_selector.clear()
            self.region_selector.addItems(self.bodyparts)

            self.animal_selector.clear()
            for i in range(1, animal_count + 1):
                self.animal_selector.addItem(str(i))  # 动物编号为1到num_classes

            self.region_selector.setEnabled(True)
            self.animal_selector.setEnabled(True)
            QMessageBox.information(self, "Info", f"Config loaded: {config_path}")

    def edit_config(self):
        if self.config is None:
            QMessageBox.warning(self, "Warning", "Please load a config first.")
            return

        self.config_editor = QTextEdit()
        self.config_editor.setPlainText(yaml.dump(self.config))

        self.config_dialog = QDialog(self)
        self.config_dialog.setWindowTitle("Edit Config")
        self.config_dialog.setGeometry(200, 100, 800, 600)

        dialog_layout = QVBoxLayout()
        dialog_layout.addWidget(self.config_editor)

        save_button = QPushButton("Save Config")
        save_button.clicked.connect(self.save_config)
        dialog_layout.addWidget(save_button)

        self.config_dialog.setLayout(dialog_layout)
        self.config_dialog.exec_()

    def save_config(self):
        try:
            self.config = yaml.safe_load(self.config_editor.toPlainText())
            QMessageBox.information(self, "Info", "Config updated successfully.")
            self.update_config_selections()  # 保存后更新部位和动物选择框
            self.config_dialog.accept()
        except yaml.YAMLError as e:
            QMessageBox.critical(self, "Error", f"Failed to update config: {e}")

    def update_config_selections(self):
        """根据新的config内容，更新身体部位和动物的选择框"""
        if self.config:
            self.bodyparts = self.config.get('bodyparts', [])
            animal_count = self.config.get('num_classes', 1)

            self.region_selector.clear()
            self.region_selector.addItems(self.bodyparts)

            self.animal_selector.clear()
            for i in range(1, animal_count + 1):
                self.animal_selector.addItem(str(i))

            QMessageBox.information(self, "Info", "Selections updated after saving config.")

    def save_annotations(self):
        """保存当前帧的标注数据"""
        self.annotation_view.save_annotations(self.current_frame_index, self.annotations_file)

    def train_model(self):
        if self.config is None:
            QMessageBox.warning(self, "Warning", "Please load a config first")
            return
        try:
            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.yaml') as temp_config_file:
                yaml.dump(self.config, temp_config_file)
                temp_config_file_path = temp_config_file.name
            subprocess.run(['python', 'train.py', '--config', temp_config_file_path], check=True)
            os.remove(temp_config_file_path)
            QMessageBox.information(self, "Info", "Model training completed")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Model training failed: {e}")

    def load_predict_config(self):
        options = QFileDialog.Options()
        config_path, _ = QFileDialog.getOpenFileName(self, "Load Prediction Config", "", "YAML Files (*.yaml)", options=options)
        if config_path:
            with open(config_path, 'r') as file:
                self.predict_config = yaml.safe_load(file)
            QMessageBox.information(self, "Info", f"Prediction config loaded: {config_path}")

    def predict_video(self):
        if self.predict_config is None:
            QMessageBox.warning(self, "Warning", "Please load a prediction config first")
            return
        try:
            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.yaml') as temp_predict_file:
                yaml.dump(self.predict_config, temp_predict_file)
                temp_predict_file_path = temp_predict_file.name
            subprocess.run(['python', 'predict.py', '--config', temp_predict_file_path], check=True)
            os.remove(temp_predict_file_path)
            QMessageBox.information(self, "Info", "Video analysis completed")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Video analysis failed: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = ADPTApp()
    window.show()

    sys.exit(app.exec_())
