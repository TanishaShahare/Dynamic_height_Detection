# Dynamic Height Detection

## Overview
`app_2_dynamic_height.py` is a real-time object measurement application built with Python, OpenCV, and Tkinter. It captures camera frames, allows the user to select a region of interest (ROI), and computes object dimensions in pixels and metric units.

## Architecture
- `Tkinter` builds the GUI and manages the application window.
- `cv2.VideoCapture` reads frames from the camera.
- A main update loop (`update_frame`) processes each frame and refreshes the UI.
- The canvas displays the live camera feed, ROI overlay, measurement box, and status text.
- The application supports three display modes: Normal, Threshold, and Edge Detection.

## Measurement Methodology
1. The user draws an ROI by dragging the mouse on the preview canvas.
2. The selected ROI is extracted from the current camera frame.
3. The ROI is converted to grayscale, blurred, and thresholded using Otsu's method.
4. Morphological opening and closing remove noise and fill gaps.
5. Contours are found, and the largest contour is selected as the object.
6. `cv2.minAreaRect` computes the minimum bounding rotated rectangle around the object.
7. The width and height of that rotated rectangle are converted from pixels to millimeters using the current scale.
8. Dimensions are shown in pixels, millimeters, and centimeters in the UI.

## Calibration Approach
- The app supports dynamic calibration using a checkerboard pattern.
- When checkerboard detection is enabled, the app detects the board and computes the average pixel distance between adjacent corners.
- The user enters the real-world square size in millimeters.
- The app computes `pixels_per_mm = avg_square_px / square_size_mm` and `mm_per_pixel = 1 / pixels_per_mm`.
- This live scale updates automatically and is displayed in the UI.
- Calibration can also be saved and loaded from `calibration_dynamic.json`.
- If no saved calibration exists, the app falls back to a default scale value.

## Robustness
- The app checks for camera availability at startup.
- Frame read failures are detected during runtime and shown in the UI.
- The app attempts to reconnect if the camera disconnects.

## Usage
- Run `python app_2_dynamic_height.py`.
- Drag the mouse over the object to set the ROI.
- Enable measurement and checkerboard calibration as needed.
- Adjust brightness, contrast, and threshold settings to improve detection.
