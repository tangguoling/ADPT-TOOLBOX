# -*- coding: utf-8 -*-
"""
Created on Tue Jul 15 22:21:17 2025

@author: 11748
"""

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
from PyQt5.QtGui import QPixmap, QIcon, QPalette, QImage, QColor, QPainter
from PyQt5.QtCore import Qt, QRectF
import numpy as np
import time
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
class AnnotateFrame(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.points = {}
        self.point_colors = {}
        self.current_frame_loaded = False
        self.original_pixmap = None
        self.current_color = QColor(Qt.red)

        self._enable_zoom_select = False
        self._zoom_start_pos = None
        self._zoom_rect_item = None
        self._zoom = 0
        self.shortcut_label = QLabel(self)
        self.shortcut_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 150);
                padding: 4px;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        self.shortcut_label.setText(
            "Shortcuts:\n"
            "Ctrl+A - Prev Frame\n"
            "Ctrl+S - Save All\n"
            "Ctrl+D - Next Frame\n"
            "Ctrl+Q - Zoom In/Crop\n"
            "Ctrl+W - Reset Zoom/Crop\n"
            "Ctrl+E - Erase Point"
        )
        self.shortcut_label.move(10, 10)
        self.shortcut_label.setFixedWidth(160)
        self.shortcut_label.setFixedHeight(110)
        self.shortcut_label.setVisible(True)
    def enable_zoom_select_mode(self):
        self._enable_zoom_select = True
        self.setDragMode(QGraphicsView.NoDrag)

    def load_frame(self, image):
        if image is None:
            return
        height, width, channel = image.shape
        bytes_per_line = 3 * width
        q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        pixmap = QPixmap.fromImage(q_image)
        pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.scene().clear()
        self.scene().addPixmap(pixmap)
        self.setSceneRect(QRectF(pixmap.rect()))
        self.original_pixmap = pixmap
        self.points = {}
        self.point_colors = {}
        self.current_frame_loaded = True

    def set_color(self, color):
        if isinstance(color, Qt.GlobalColor):
            self.current_color = QColor(color)
        else:
            self.current_color = color

    def reset_view(self):
        if self.original_pixmap:
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
            self._zoom = 0

    def mousePressEvent(self, event):
        if self._enable_zoom_select and event.button() == Qt.LeftButton:
            self._zoom_start_pos = self.mapToScene(event.pos())
            if self._zoom_rect_item:
                self.scene().removeItem(self._zoom_rect_item)
                self._zoom_rect_item = None
        else:
            if event.button() == Qt.LeftButton and self.current_frame_loaded:
                pos = self.mapToScene(event.pos())
                parent = self.get_parent_app()
                animal_id = parent.animal_selector.currentIndex() + 1
                body_part = parent.region_selector.currentText()

                if animal_id not in self.points:
                    self.points[animal_id] = {}
                    self.point_colors[animal_id] = {}

                color = parent.bodypart_colors.get(body_part, self.current_color)
                self.points[animal_id][body_part] = (pos.x(), pos.y())
                self.point_colors[animal_id][body_part] = color

                ellipse = QGraphicsEllipseItem(pos.x() - 2.5, pos.y() - 2.5, 5, 5)
                ellipse.setBrush(color)
                self.scene().addItem(ellipse)

                current_index = parent.region_selector.currentIndex()
                if current_index < parent.region_selector.count() - 1:
                    parent.region_selector.setCurrentIndex(current_index + 1)
                    parent.update_annotation_color()

    def mouseMoveEvent(self, event):
        if self._enable_zoom_select and self._zoom_start_pos:
            end_pos = self.mapToScene(event.pos())
            rect = QRectF(self._zoom_start_pos, end_pos).normalized()

            if not self._zoom_rect_item:
                from PyQt5.QtWidgets import QGraphicsRectItem
                from PyQt5.QtGui import QPen
                self._zoom_rect_item = QGraphicsRectItem(rect)
                self._zoom_rect_item.setPen(QPen(Qt.red, 2, Qt.DashLine))
                self.scene().addItem(self._zoom_rect_item)
            else:
                self._zoom_rect_item.setRect(rect)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._enable_zoom_select and event.button() == Qt.LeftButton and self._zoom_start_pos:
            end_pos = self.mapToScene(event.pos())
            rect = QRectF(self._zoom_start_pos, end_pos).normalized()

            if rect.width() > 5 and rect.height() > 5:
                self.fitInView(rect, Qt.KeepAspectRatio)
                self._zoom = 0

            if self._zoom_rect_item:
                self.scene().removeItem(self._zoom_rect_item)
                self._zoom_rect_item = None

            self._zoom_start_pos = None
            self._enable_zoom_select = False
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
            self._zoom += 1
        else:
            zoom_factor = zoom_out_factor
            self._zoom -= 1

        if self._zoom < -10:
            self._zoom = -10
            return
        elif self._zoom > 20:
            self._zoom = 20
            return

        self.scale(zoom_factor, zoom_factor)

    def erase_specific_point(self, animal_id, body_part):
        """擦除指定动物和部位的标注点"""
        if animal_id in self.points and body_part in self.points[animal_id]:
            del self.points[animal_id][body_part]
            del self.point_colors[animal_id][body_part]
            self.scene().clear()
            self.scene().addPixmap(self.original_pixmap)
            self.restore_annotations()

        # 保存擦除操作后的当前帧标注到 JSON
        app = self.get_parent_app()
        if app and app.annotations_file:
            frame_index = app.current_frame_index
            app.annotation_view.save_annotations(frame_index, app.annotations_file)

            # 更新当前帧标注图片（无弹框）
            annotated_dir = os.path.join("output_frames", "annotated_frames")
            os.makedirs(annotated_dir, exist_ok=True)
            video_name = os.path.splitext(os.path.basename(app.video_path))[0]
            annotated_img_path = os.path.join(annotated_dir, f"{video_name}_frame_{frame_index}_annotated.png")
            self.export_annotated_frame(annotated_img_path)


    def restore_annotations(self):
        for animal_id, parts in self.points.items():
            for body_part, point in parts.items():
                color = self.point_colors[animal_id].get(body_part, self.get_parent_app().bodypart_colors.get(body_part, self.current_color))
                ellipse = QGraphicsEllipseItem(point[0] - 2.5, point[1] - 2.5, 5, 5)
                ellipse.setBrush(color)
                self.scene().addItem(ellipse)

    def save_annotations(self, frame_index, annotations_file):
        """保存当前帧的标注到 JSON 文件"""
        parent_app = self.get_parent_app()
        if not parent_app:
            print("Error: Parent application not found.")
            return

        # 从主应用获取 base_output_folder
        img_path = os.path.join(parent_app.base_output_folder, f"frame_{frame_index}.png")
        annotations = {
            "img_path": img_path,
            "joints": [],
            "img_bbox": [float('nan'), float('nan'), float('nan'), float('nan')]
        }

        # 遍历标注点并保存
        for animal_id in range(1, parent_app.animal_selector.count() + 1):
            for idx, body_part in enumerate(parent_app.bodyparts):
                if animal_id in self.points and body_part in self.points[animal_id]:
                    x, y = self.points[animal_id][body_part]
                    annotations["joints"].append([x, y, animal_id])
                else:
                    annotations["joints"].append([float('nan'), float('nan'), animal_id])

        # 加载或创建标注文件
        if os.path.exists(annotations_file):
            with open(annotations_file, 'r') as file:
                all_annotations = json.load(file)
        else:
            all_annotations = []

        # 更新现有标注或追加新标注
        for i, existing_annotation in enumerate(all_annotations):
            if existing_annotation["img_path"] == img_path:
                all_annotations[i] = annotations
                break
        else:
            all_annotations.append(annotations)

        # 保存到文件
        with open(annotations_file, 'w') as file:
            json.dump(all_annotations, file, indent=4)
        print(f"Annotations saved for frame: {img_path}")

    def load_annotations(self, frame_index, annotations_file):
        """从 JSON 文件中加载并显示指定帧的标注"""
        if not os.path.exists(annotations_file):
            print(f"Annotations file not found: {annotations_file}")
            return False

        with open(annotations_file, 'r') as file:
            all_annotations = json.load(file)

        # 匹配当前帧的标注
        img_path = os.path.join(self.get_parent_app().base_output_folder, f"frame_{frame_index}.png")
        print(f"Looking for annotations for frame: {img_path}")

        for annotation in all_annotations:
            if os.path.normpath(annotation["img_path"]) == os.path.normpath(img_path):
                self.points = {}  # 清空现有点
                self.point_colors = {}
                joints = annotation.get("joints", [])

                # 恢复标注点
                for idx, (x, y, animal_id) in enumerate(joints):
                    body_part = self.get_parent_app().bodyparts[idx - (animal_id - 1) * len(self.get_parent_app().bodyparts)]
                    if not np.isnan(x) and not np.isnan(y):
                        if animal_id not in self.points:
                            self.points[animal_id] = {}
                            self.point_colors[animal_id] = {}

                        # 保存标注点及颜色
                        self.points[animal_id][body_part] = (x, y)
                        color = self.get_parent_app().bodypart_colors.get(body_part, self.current_color)
                        self.point_colors[animal_id][body_part] = color

                # 渲染标注点到画布
                self.restore_annotations()
                print(f"Annotations loaded for frame: {img_path}")
                return True

        print(f"No annotations for frame: {img_path}")
        return False


    def get_parent_app(self):
        parent = self.parentWidget()
        while parent and not isinstance(parent, ADPTApp):
            parent = parent.parentWidget()
        return parent

    def export_annotated_frame(self, file_path):
        """将当前帧和标注点导出为图片"""
        if self.original_pixmap is None:
            print("Error: No pixmap available for export.")
            return  # 如果没有加载任何帧，则不执行

        # 创建一个 QImage，用于将场景渲染成图片
        image = QImage(int(self.sceneRect().width()), int(self.sceneRect().height()), QImage.Format_ARGB32)
        image.fill(Qt.transparent)  # 背景透明

        # 使用 QPainter 渲染场景到 QImage
        painter = QPainter(image)
        self.render(painter)
        painter.end()

        # 保存渲染后的图片
        image.save(file_path, "PNG")

class ADPTApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ADPT")
        self.setGeometry(100, 100, 1600, 900)
        self.setWindowIcon(QIcon('logo.png'))

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
        # self.create_video_extraction_page()
        self.create_annotation_page()
        self.create_training_page()
        self.create_prediction_page()

        self.stacked_widget.addWidget(self.welcome_page)
        # self.stacked_widget.addWidget(self.video_extraction_page)
        self.stacked_widget.addWidget(self.annotation_page)
        self.stacked_widget.addWidget(self.training_page)
        self.stacked_widget.addWidget(self.prediction_page)
        self.stacked_widget.setCurrentIndex(0)
        # self.create_discussion_page()
        # self.stacked_widget.addWidget(self.discussion_page)
        
    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_A:
            self.load_prev_frame()
            self._reset_zoom()
            event.accept()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_D:
            self.load_next_frame()
            self._reset_zoom()
            event.accept()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_S:
            self._reset_zoom()
            self.merge_all_annotations()
            event.accept()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_E:
            self.erase_point()
            event.accept()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Q:
            self._zoom_in_img()
            event.accept()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_W:
            self._reset_zoom()
            event.accept()
        else:
            super().keyPressEvent(event)

    def create_menu(self):
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""QMenuBar {background-color: #333333; color: white;}""")
        welcome_action = QAction("Welcome", self)
        welcome_action.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        menu_bar.addAction(welcome_action)

        # extract_action = QAction("Extract Frames", self)
        # extract_action.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        # menu_bar.addAction(extract_action)

        annotate_action = QAction("Annotate Frames", self)
        annotate_action.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        menu_bar.addAction(annotate_action)

        train_action = QAction("Train Model", self)
        train_action.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        menu_bar.addAction(train_action)

        predict_action = QAction("Analyze Video", self)
        predict_action.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        menu_bar.addAction(predict_action)
        
    def create_welcome_page(self):
        self.welcome_page = QWidget()
        layout = QVBoxLayout()

        logo_label = QLabel(self.welcome_page)
        pixmap = QPixmap('logo.png')
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

    def extract_frames_no_switch(self):
        if not self.video_path:
            QMessageBox.warning(self, "Warning", "Please load a video first")
            return

        frame_count = int(self.frame_count_input.text())
        cap = cv2.VideoCapture(self.video_path)
        base_output_folder = os.path.join(self.base_output_folder, self.video_path).split('.')[0]
        base_output_folder = 'output_frames/' + base_output_folder.split('/')[-1]
        frame_num = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        gap = frame_num // frame_count  # 计算帧的间隔
        frame_selected = [i for i in range(0, frame_num, gap)]  # 选取的帧索引

        self.frames_cache = []  # 缓存帧数据到内存
        count = 0

        while cap.isOpened() and count < frame_count:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_selected[count])
            ret, frame = cap.read()
            if not ret:
                break
            frame_path = os.path.join(base_output_folder, f"frame_{count}.png")
            print(frame_path)
            cv2.imwrite(frame_path, frame)
            self.frames_cache.append(frame)  # 保存帧数据到内存
            count += 1

        cap.release()
        self.video_label.setText(f"Extracted {len(self.frames_cache)} frames")

        if self.frames_cache:
            self.load_frame_by_index(0)  # 加载第一帧

    def create_annotation_page(self):
        self.annotation_page = QWidget()
        layout = QHBoxLayout()

        # 左侧控制面板布局
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignVCenter)  # 布局调整到上下界面的中间部分

        # 左侧控制面板宽度固定
        left_widget = QWidget()
        left_widget.setFixedWidth(300)  # 固定宽度
        left_widget_layout = QVBoxLayout()
        left_widget_layout.setAlignment(Qt.AlignVCenter)  # 控件整体居中

        # 配置加载和编辑按钮布局
        config_button_layout = QHBoxLayout()
        config_button = QPushButton("Load Config")
        config_button.clicked.connect(self.load_config)
        config_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        config_button_layout.addWidget(config_button)

        edit_config_button = QPushButton("Edit Config")
        edit_config_button.clicked.connect(self.edit_config)
        edit_config_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        config_button_layout.addWidget(edit_config_button)

        left_widget_layout.addLayout(config_button_layout)

        # 中间部分的功能按钮布局
        middle_layout = QVBoxLayout()
        middle_layout.setAlignment(Qt.AlignCenter)

        # 加载视频按钮
        load_button = QPushButton("Load Video")
        load_button.clicked.connect(self.load_video)
        load_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        middle_layout.addWidget(load_button)

        # 输入帧数文本框
        self.frame_count_input = QLineEdit()
        self.frame_count_input.setPlaceholderText("Enter the number of frames to extract")
        middle_layout.addWidget(self.frame_count_input)

        # 抽取帧按钮
        extract_button = QPushButton("Extract Frames")
        extract_button.clicked.connect(self.extract_frames_no_switch)  # 使用不切换页面的版本
        extract_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        middle_layout.addWidget(extract_button)

        # 动物和身体部位选择器
        self.animal_selector = QComboBox()
        self.animal_selector.addItem("Select Animal")
        self.animal_selector.currentIndexChanged.connect(self.update_region_selector)
        middle_layout.addWidget(self.animal_selector)

        self.region_selector = QComboBox()
        middle_layout.addWidget(self.region_selector)

        # 帧切换按钮
        prev_button = QPushButton("Previous Frame")
        prev_button.clicked.connect(self.load_prev_frame)
        middle_layout.addWidget(prev_button)

        layout_btn_zoom = QHBoxLayout()

        btn_zoom_in = QPushButton("Zoom In/Crop")
        btn_zoom_in.clicked.connect(self._zoom_in_img)
        layout_btn_zoom.addWidget(btn_zoom_in)

        btn_reset_zoom= QPushButton("Reset Zoom/Crop")
        btn_reset_zoom.clicked.connect(self._reset_zoom)
        layout_btn_zoom.addWidget(btn_reset_zoom)

        middle_layout.addLayout(layout_btn_zoom)

        next_button = QPushButton("Next Frame")
        next_button.clicked.connect(self.load_next_frame)
        middle_layout.addWidget(next_button)

        # 擦除点按钮
        erase_button = QPushButton("Erase Last Point")
        erase_button.clicked.connect(self.erase_point)
        middle_layout.addWidget(erase_button)

        # Save Annotations按钮
        save_button = QPushButton("Save Annotations")
        # save_button.clicked.connect(self.save_annotations_to_file)  # 保存标注
        save_button.clicked.connect(self.merge_all_annotations)  # 合并所有标注
        save_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        middle_layout.addWidget(save_button)

        # 将中间部分布局添加到左侧布局
        left_widget_layout.addLayout(middle_layout)

        # 视频信息标签
        self.video_label = QLabel("No Video Loaded")
        self.video_label.setStyleSheet("color: white;")
        self.video_label.setWordWrap(True)  # 自动换行
        left_widget_layout.addWidget(self.video_label)

        self.video_length_label = QLabel("Video length: 0 seconds")
        self.video_length_label.setStyleSheet("color: white;")
        self.video_length_label.setWordWrap(True)  # 自动换行
        left_widget_layout.addWidget(self.video_length_label)

        # 左侧容器设置布局
        left_widget.setLayout(left_widget_layout)
        left_layout.addWidget(left_widget)

        # 标注区域视图
        self.annotation_view = AnnotateFrame(self)

        # 主布局调整：左侧布局先添加，右侧标注区域后添加
        layout.addLayout(left_layout, 1)
        layout.addWidget(self.annotation_view, 4)

        self.annotation_page.setLayout(layout)

    def save_annotations(self):
        """保存当前视频并合并所有视频的标注为总的JSON文件"""
        if self.frames_cache:
            # 保存当前视频最后一帧的标注和图片
            self.save_current_frame_annotations(self.current_frame_index)

            # 整合当前视频所有标注页到一个 JSON 文件
            self.finalize_current_video()

        # 合并所有视频的 JSON 文件
        self.merge_all_annotations()
        QMessageBox.information(self, "Info", "All annotations saved and merged successfully.")

    def finalize_current_video(self):
        """保存当前视频的所有标注到单独的 JSON 文件"""
        if not self.frames_cache or not self.annotations_file:
            return  # 如果没有帧缓存或没有标注文件路径，则不保存

        # 保存所有帧的标注到当前视频的 JSON 文件
        for index in range(len(self.frames_cache)):
            self.annotation_view.save_annotations(index, self.annotations_file)

        QMessageBox.information(self, "Info", f"Annotations saved for video: {self.video_path}")

    def merge_all_annotations(self):
        """合并所有视频的标注文件为一个总 JSON 文件"""
        output_dir = "output_frames"
        all_annotations = []
        seen_files = set()  # 避免重复处理

        self.save_current_frame_annotations(self.current_frame_index)
        if os.path.exists(output_dir + "/merged_annotations.json"):  # 检查文件是否存在
            os.remove(output_dir + "/merged_annotations.json")       # 删除文件


        for subdir, _, files in os.walk(output_dir):
            for file in files:
                if file.endswith("_annotations.json"):  # 匹配单个视频的标注文件
                    file_path = os.path.join(subdir, file)
                    if file_path not in seen_files:
                        seen_files.add(file_path)
                        with open(file_path, 'r') as f:
                            annotations = json.load(f)
                            for annotation in annotations:
                                # 更新图片路径，确保全局唯一
                                annotated_frame = cv2.imread(
                                    "output_frames/annotated_frames/" + annotation['img_path'].split('\\')[-2] + '_' + annotation['img_path'].split('\\')[-1].split('.')[0] + '_annotated.png'
                                )
                                
                                h,w = annotated_frame.shape[:2]
                                # print(h,w)
                                
                                ori_frame = cv2.imread(annotation['img_path'])
                                
                                ori_h,ori_w = ori_frame.shape[:2]
                                # print(ori_h,ori_w)
                                joints = annotation['joints']
                                #print(len(joints))
                                for kp in range(len(joints)):
                                    joints[kp][0] = joints[kp][0] / w * ori_w
                                    joints[kp][1] = joints[kp][1] / h * ori_h
                                annotation["img_path"] = annotation['img_path']
                                annotation["joints"] = joints
                                if annotation not in all_annotations:
                                    all_annotations.append(annotation)

        # 保存总的 JSON 文件
        merged_file = os.path.join(output_dir, "merged_annotations.json")
        with open(merged_file, 'w') as f:
            json.dump(all_annotations, f, indent=4)

        print(f"Merged annotations saved to: {merged_file}")


    def export_current_video_annotated_frames(self):
        """导出当前视频的所有已标注帧图片到统一的 output_frames/annotated_frames 文件夹"""
        if not self.frames_cache or not self.annotations_file:
            print("No frames loaded or annotations file found. Skipping export.")
            return

        annotated_dir = os.path.join("output_frames", "annotated_frames")
        os.makedirs(annotated_dir, exist_ok=True)

        try:
            # 加载当前视频的标注 JSON 文件
            with open(self.annotations_file, 'r') as f:
                annotations = json.load(f)

            for annotation in annotations:
                img_path = annotation["img_path"]
                joints = annotation.get("joints", [])

                # 加载原始图片
                original_img_path = os.path.join(self.base_output_folder, os.path.basename(img_path))
                if not os.path.exists(original_img_path):
                    print(f"Image not found: {original_img_path}")
                    continue

                frame_image = cv2.imread(original_img_path)
                if frame_image is None:
                    print(f"Failed to load image: {original_img_path}")
                    continue

                # 绘制标注点到图片
                for joint in joints:
                    x, y, animal_id = joint
                    if not np.isnan(x) and not np.isnan(y):
                        color = (0, 0, 255)  # 红色标注点
                        cv2.circle(frame_image, (int(x), int(y)), 5, color, -1)

                # 保存带标注的图片到统一目录
                annotated_img_name = f"{os.path.basename(self.base_output_folder)}_{os.path.basename(img_path)}"
                annotated_img_path = os.path.join(annotated_dir, annotated_img_name)
                cv2.imwrite(annotated_img_path, frame_image)

            print(f"Annotated frames saved to: {annotated_dir}")
        except Exception as e:
            print(f"Error during export: {e}")

    def erase_point(self):
        animal_id = self.animal_selector.currentIndex() + 1
        body_part = self.region_selector.currentText()
        self.annotation_view.erase_specific_point(animal_id, body_part)

    def update_region_selector(self):
        if self.region_selector.count() > 0:
            self.region_selector.setCurrentIndex(0)
        self.update_annotation_color()

    def update_annotation_color(self):
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

        config_button = QPushButton("Load Prediction Config")
        config_button.clicked.connect(self.load_predict_config)
        config_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        layout.addWidget(config_button)

        edit_config_button = QPushButton("Edit Config")
        edit_config_button.clicked.connect(self.edit_predict_config)
        edit_config_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        layout.addWidget(edit_config_button)
        
        predict_button = QPushButton("Start Analysis")
        predict_button.clicked.connect(self.predict_video)
        predict_button.setStyleSheet("background-color: #5F9EA0; color: white;")
        layout.addWidget(predict_button)

        self.prediction_page.setLayout(layout)

    def load_video(self):
        """加载一个新视频并保存当前视频的最后一帧和整合的JSON文件"""
        if self.frames_cache:
            # 保存当前视频最后一帧的标注和图片
            self.save_current_frame_annotations(self.current_frame_index)

            # # 整合当前视频所有标注页到一个 JSON 文件
            # self.finalize_current_video()

        # 加载新视频逻辑
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Video", "", "Video Files (*.mp4 *.avi)", options=options)
        if file_path:
            self.video_path = file_path
            cap = cv2.VideoCapture(self.video_path)
            self.frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            self.video_length = self.frame_count / fps

            # 显示视频信息
            self.video_label.setText(f"Video Loaded: {file_path}")
            self.video_length_label.setText(f"Video length: {self.video_length:.2f} seconds, {self.frame_count} frames")

            # 设置输出目录和标注文件路径
            video_name = os.path.splitext(os.path.basename(self.video_path))[0]
            self.base_output_folder = os.path.join("output_frames", video_name)
            os.makedirs(self.base_output_folder, exist_ok=True)
            self.annotations_file = os.path.join(self.base_output_folder, f"{video_name}_annotations.json")

            # 初始化新视频的标注环境
            self.frames_cache = []
            self.current_frame_index = 0

            QMessageBox.information(self, "Info", "Please enter the number of frames to extract.")

            # 重置选择器到第一项
            if self.region_selector.count() > 0:
                self.region_selector.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, "Warning", "No video selected.")

    def load_prev_frame(self):
        """加载上一帧并保存当前帧的标注和图片"""
        if self.current_frame_index > 0:
            # 保存当前帧的标注
            self.save_current_frame_annotations(self.current_frame_index)

            # 切换到上一帧
            self.current_frame_index -= 1
            self.load_frame_by_index(self.current_frame_index)

            # 重置选择器到第一项
            self.region_selector.setCurrentIndex(0)
        else:
            QMessageBox.information(self, "Info", "Already at the first frame.")

    def load_next_frame(self):
        """加载下一帧并保存上一帧的标注和图片"""
        if self.current_frame_index < len(self.frames_cache) - 1:
            # 保存当前帧的标注和图片
            self.save_current_frame_annotations(self.current_frame_index)

            # 加载下一帧
            self.current_frame_index += 1
            self.load_frame_by_index(self.current_frame_index)

            # 重置选择器到第一项
            self.region_selector.setCurrentIndex(0)
        else:
            QMessageBox.information(self, "Info", "Already at the last frame.")

    def save_current_frame_annotations(self, frame_index):
        """保存指定帧的标注到JSON文件和带标注的图片"""
        if not self.frames_cache or not self.annotations_file or frame_index >= len(self.frames_cache):
            print("Warning: No frames or invalid frame index.")
            return

        # 保存标注到单个视频的 JSON 文件
        self.annotation_view.save_annotations(frame_index, self.annotations_file)

        # 保存标记图片
        annotated_dir = os.path.join("output_frames", "annotated_frames")
        os.makedirs(annotated_dir, exist_ok=True)

        # 获取当前视频的名称作为前缀
        video_name = os.path.splitext(os.path.basename(self.video_path))[0]
        frame_image = self.frames_cache[frame_index]
        if frame_image is not None:
            annotated_img_name = f"{video_name}_frame_{frame_index}_annotated.png"
            annotated_img_path = os.path.join(annotated_dir, annotated_img_name)
            self.annotation_view.export_annotated_frame(annotated_img_path)
            print(f"Annotated image saved: {annotated_img_path}")
        else:
            print(f"Warning: Frame {frame_index} is invalid or could not be saved.")


    def load_frame_by_index(self, index):
        """加载指定索引的帧和标注"""
        if 0 <= index < len(self.frames_cache):
            frame = self.frames_cache[index]
            self.annotation_view.load_frame(frame)

            # 确保加载标注点
            success = self.annotation_view.load_annotations(index, self.annotations_file)
            if not success:
                print(f"No annotations found for frame {index}.")
            else:
                print(f"Annotations loaded for frame {index}.")
        else:
            print(f"Invalid frame index: {index}")

    def extract_frames(self):
        """根据输入帧数抽取固定的帧，帧位置固定"""
        if not self.video_path:
            QMessageBox.warning(self, "Warning", "Please load a video first.")
            return

        try:
            # 获取用户输入的目标帧数
            frame_count_input = int(self.frame_count_input.text())
            if frame_count_input <= 0:
                raise ValueError("Frame count must be greater than 0.")

            # 打开视频文件
            cap = cv2.VideoCapture(self.video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # 计算帧率间隔
            if frame_count_input >= total_frames:
                QMessageBox.warning(self, "Warning", "Input frame count exceeds total frames. Using all frames.")
                frame_indices = list(range(total_frames))  # 使用所有帧
            else:
                gap = total_frames // frame_count_input
                frame_indices = [i * gap for i in range(frame_count_input)]

            # 抽取帧并保存
            self.frames_cache = []
            video_name = os.path.splitext(os.path.basename(self.video_path))[0]
            base_output_folder = os.path.join(self.base_output_folder, video_name)
            os.makedirs(base_output_folder, exist_ok=True)

            count = 0
            while cap.isOpened() and count < len(frame_indices):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_indices[count])
                ret, frame = cap.read()
                if not ret:
                    break
                frame_path = os.path.join(base_output_folder, f"frame_{count}.png")
                cv2.imwrite(frame_path, frame)
                self.frames_cache.append(frame)
                count += 1

            cap.release()

            self.video_label.setText(f"Extracted {len(self.frames_cache)} frames.")
            if self.frames_cache:
                self.stacked_widget.setCurrentIndex(2)  # 切换到标注页面
                self.load_frame_by_index(0)  # 加载第一帧
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Invalid frame count input: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during frame extraction: {e}")


    def load_config(self):
        options = QFileDialog.Options()
        config_path, _ = QFileDialog.getOpenFileName(self, "Load Config", "", "YAML Files (*.yaml)", options=options)
        if config_path:
            with open(config_path, 'r') as file:
                self.config = yaml.safe_load(file)

            self.bodyparts = self.config.get('bodyparts', [])
            animal_count = self.config.get('num_classes', 1)

            color_palette = [Qt.red, Qt.green, Qt.blue, Qt.darkRed, Qt.darkGreen, Qt.darkBlue, Qt.cyan, Qt.magenta, Qt.yellow]
            for i, bodypart in enumerate(self.bodyparts):
                color_index = i % len(color_palette)
                self.bodypart_colors[bodypart] = QColor(color_palette[color_index])

            self.region_selector.clear()
            self.region_selector.addItems(self.bodyparts)

            self.animal_selector.clear()
            for i in range(1, animal_count + 1):
                self.animal_selector.addItem(str(i))

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
            self.update_config_selections()
            self.config_dialog.accept()
        except yaml.YAMLError as e:
            QMessageBox.critical(self, "Error", f"Failed to update config: {e}")

    def update_config_selections(self):
        if self.config:
            self.bodyparts = self.config.get('bodyparts', [])
            animal_count = self.config.get('num_classes', 1)

            self.region_selector.clear()
            self.region_selector.addItems(self.bodyparts)

            self.animal_selector.clear()
            for i in range(1, animal_count + 1):
                self.animal_selector.addItem(str(i))

            QMessageBox.information(self, "Info", "Selections updated after saving config.")

   

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


    def edit_predict_config(self):
        if self.predict_config is None:
            QMessageBox.warning(self, "Warning", "Please load a config first.")
            return

        self.config_editor = QTextEdit()
        self.config_editor.setPlainText(yaml.dump(self.predict_config))

        self.config_dialog = QDialog(self)
        self.config_dialog.setWindowTitle("Edit Predict Config")
        self.config_dialog.setGeometry(200, 100, 800, 600)

        dialog_layout = QVBoxLayout()
        dialog_layout.addWidget(self.config_editor)

        save_button = QPushButton("Save Config")
        save_button.clicked.connect(self.save_predict_config)
        dialog_layout.addWidget(save_button)

        self.config_dialog.setLayout(dialog_layout)
        self.config_dialog.exec_()
        
    def save_predict_config(self):
        try:
            self.predict_config = yaml.safe_load(self.config_editor.toPlainText())
            QMessageBox.information(self, "Info", "Config updated successfully.")
            self.update_config_selections()
            self.config_dialog.accept()
        except yaml.YAMLError as e:
            QMessageBox.critical(self, "Error", f"Failed to update config: {e}")

    def predict_video(self):
        if self.predict_config is None:
            QMessageBox.warning(self, "Warning", "Please load a prediction config first")
            return
        try:
            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.yaml') as temp_predict_file:
                yaml.dump(self.predict_config, temp_predict_file)
                temp_predict_file_path = temp_predict_file.name
            
            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.yaml') as temp_config_file:
                yaml.dump(self.config, temp_config_file)
                temp_config_file_path = temp_config_file.name
                
            subprocess.run(['python', 'predict.py', '--config_predict', temp_predict_file_path, '--config', temp_config_file_path], check=True)
            os.remove(temp_predict_file_path)
            QMessageBox.information(self, "Info", "Video analysis completed")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Video analysis failed: {e}")


    def _zoom_in_img(self):
        self.annotation_view.enable_zoom_select_mode()

    def _reset_zoom(self):
        self.annotation_view.reset_view()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = ADPTApp()
    window.show()

    sys.exit(app.exec_())
