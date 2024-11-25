
# Anti-Drift Pose Tracker (ADPT): A transformer-based network for robust animal pose estimation cross-species

[![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

## Overview

This application provides a graphical user interface (GUI) for animal pose detection, video frame extraction, manual annotation, and model training using the ADPT (Anti-Drift Pose Tracker) system. It is designed for ease of use in multi-animal behavior tracking tasks and allows users to handle videos, annotate key points, and train models for pose tracking.

## Features

- **Video Loading and Frame Extraction**: Load videos and extract frames for further processing.
- **Manual Annotation**: Annotate body parts on extracted frames with color-coded key points.
- **Model Training**: Train a model based on manually annotated frames for pose tracking.
- **Prediction/Analysis**: Analyze new videos with trained models for pose estimation.
- **Configurable Parameters**: Load and edit configuration files for training and prediction tasks.
- **Multi-Animal Tracking Support**: Supports multiple animals and different body parts for pose tracking.

## Installation

### Prerequisites

You can install these dependencies using the following commands:

```bash
conda create -n ADPT python==3.9
conda activate ADPT
pip install tensorflow==2.9.1
pip install tensorflow-addons==0.17.1
conda install cudnn==8.2.1
pip install imgaug
pip install pandas
pip install pyyaml
pip install tqdm
pip install PyQt5
```

### Running the Application

1. Clone or download this repository.
2. Navigate to the project directory in your terminal.
3. Run the `GUI_v3.py` script using Python:

```bash
python GUI_v3.py
```

The main window of the ADPT application will open.

## Usage

### Loading Videos

1. Click on the "Load Video" button.
2. Select a video file from your system (.mp4, .avi, etc.).
3. Once loaded, the video details (length, frame count) will be displayed.

### Extracting Frames

1. After loading a video, click "Extract Frames" to extract frames from the video.
2. Frames will be stored in the `output_frames` directory for annotation and model training.

### Annotating Frames

1. Navigate to the "Annotate Frames" section in the menu.
2. Use the annotation view to manually label key points on each frame.
3. Choose different body parts to annotate by selecting from the dropdown menu.
4. Use the "Previous Frame" and "Next Frame" buttons to navigate through frames.
5. You can erase the last added point if needed.

### Training a Model

1. Navigate to the "Train Model" section in the menu.
2. Ensure that the `config.yaml` file is properly configured with body parts and other parameters.
3. Click the "Start Training" button to begin training the model using the annotated frames.

### Predicting on New Videos

1. Navigate to the "Analyze Video" section in the menu.
2. Load a prediction configuration file (`config_predict.yaml`).
3. Click the "Start Analysis" button to predict animal poses in new videos using the trained model.

### Configurations

The application requires configuration files (`.yaml`) for training and prediction tasks. You can load and edit these configurations directly from the GUI. Be sure to specify parameters such as body parts, skeleton structures, and model paths in the YAML files.

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
DOI: [10.7554/eLife.95709.1](https://doi.org/10.7554/eLife.95709.1)

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE.txt) file for details.

