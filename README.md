
# Anti-Drift Pose Tracker (ADPT): A transformer-based network for robust animal pose estimation cross-species

[![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

## Overview

This application provides a graphical user interface (GUI) for animal pose detection, video frame extraction, manual annotation, and model training using the ADPT (Anti-Drift Pose Tracker) system. It is designed for ease of use in multi-animal behavior tracking tasks and allows users to handle videos, annotate key points, and train models for pose tracking.

## ADPT Usage Tutorial Videos

We have created tutorial videos for using ADPT. You can find the video on YouTube and Bilibili to quickly learn how to use ADPT for animal pose estimation:

- [YouTube Tutorial Video](https://youtu.be/evtoOAChXeU)
- [Bilibili Tutorial Video](https://www.bilibili.com/video/BV1wbCHY1EYx/?share_source=copy_web&vd_source=46c72ebafcd31f08bf970187e3f7440e)

The mouse video of the demonstration can be found at the following link:

- [Demo Mouse Video](https://zenodo.org/records/14566416?token=eyJhbGciOiJIUzUxMiJ9.eyJpZCI6ImMzMjE0MWUzLTkxNjUtNGJmMy05MzllLTY5MmU2MjJmNGUzOSIsImRhdGEiOnt9LCJyYW5kb20iOiJiMjI2MTJjZWVkYzdjYjk5MmEyMTNjOTAyYTRjOTZjMiJ9.gN6eP6tgAxeb8f3fbWynCVYYFjKdq1JFYqTkBhF37d5ALmYXM7odRNe3_UyNC0x8K4PgW3zPKuCniHEIvdEPcQ)

These videos will help you efficiently master both the basic operations and advanced features of ADPT, enabling you to apply the tool effectively in your research and experiments.


## Features

- **Video Loading and Frame Extraction**: Load videos and extract frames for further processing.
- **Manual Annotation**: Annotate body parts on extracted frames with color-coded key points.
- **Model Training**: Train a model based on manually annotated frames for pose tracking.
- **Prediction/Analysis**: Analyze new videos with trained models for pose estimation.
- **Configurable Parameters**: Load and edit configuration files for training and prediction tasks.
- **Multi-Animal Tracking Support**: Supports multiple animals and different body parts for pose tracking.

## Installation

### Prerequisites

You can install these dependencies using the following commands (please be sure to install each package step by step, and confirm the installation at each step by "y".):

```bash
conda create -n ADPT python==3.9
conda activate ADPT
pip install numpy==1.26.3
pip install scikit-image==0.19.3
pip install tensorflow==2.9.1
pip install tensorflow-addons==0.17.1
conda install cudnn==8.2.1
pip install imgaug
pip install pandas
pip install pyyaml
pip install tqdm
pip install PyQt5
```

### Preparation

1. Clone or download this repository.
2. Modify config.yaml. You may need to modify the image size information, image path ('IMG_DIR', the same as where the GUI_v4.py is located), number of animals ('num_classes'), center of body ('centre'), NUM_KEYPOINT, bodyparts and skeleton to correspond to your project. Model information allows you to control model training details.
3. Modify config_predict.yaml. You may need to modify the Video_type, videos directory (Video_path), model_path. Please ensure that the videos to be processed have the same size as the original images during model training. Save_predicted_video allows you to control whether save predicted video (True or False).

### Run the Application

4. Open a terminal and enter the folder where the GUI_v4.py is located. Please make sure that config.yaml and config_predict.yaml is under the same folder of GUI_v4.py because script would read training configuration from them.
5. Run the GUI_v4.py script using Python:

```bash
python GUI_v4.py
```

The main window of the ADPT application will open.

## Usage

### Load Videos

1. Click on the "Load Video" button.
2. Select a video file from your system (.mp4, .avi, etc.).
3. Once loaded, the video details (length, frame count) will be displayed.

### Extracting Frames

1. After loading a video, click "Extract Frames" to extract frames from the video.
2. Frames will be stored in the `output_frames` directory for annotation and model training.

### Annotate Frames

1. Navigate to the "Annotate Frames" section in the menu.
2. Use the annotation view to manually label key points on each frame.
3. Choose different body parts to annotate by selecting from the dropdown menu.
4. Use the "Previous Frame" and "Next Frame" buttons to navigate through frames.
5. You can erase the last added point if needed.
6. After annoation, you should click "Save Annotations"

### Train a Model
1. Navigate to the "Train Model" section in the menu.
2. Ensure that the `config.yaml` file is properly configured with body parts and other parameters.
3. Click the "Start Training" button to begin training the model using the annotated frames.

### Predict New Videos

1. Navigate to the "Analyze Video" section in the menu.
2. Load a prediction configuration file (`config_predict.yaml`).
3. Click the "Start Analysis" button to predict animal poses in new videos using the trained model.


## File Structure

- `GUI.py`: The main application script that runs the ADPT GUI.
- `output_frames/`: The directory where extracted frames and annotations are saved.
- `config.yaml`: The configuration file used for model training.
- `config_predict.yaml`: The configuration file used for model predictions.
- `train.py`: Script to handle model training.
- `predict.py`: Script to handle predictions on new videos.
  
## Citation

If you use this project in your research, please cite our paper:

[Anti-drift pose tracker (ADPT): A transformer-based network for robust animal pose estimation cross-species](https://doi.org/10.7554/eLife.95709.1)  
Authors: Tang Guoling, Yaning HanYaning, HanQuanying, LiuPengfei Wei  
Published: May 2024  
DOI: [10.7554/eLife.95709.1
        
        ](https://doi.org/10.7554/eLife.95709.1)

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE.txt) file for details.

