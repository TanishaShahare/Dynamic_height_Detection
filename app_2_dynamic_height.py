import cv2
import tkinter as tk
from tkinter import Scale, HORIZONTAL, ttk, messagebox
from PIL import Image, ImageTk
import numpy as np
import json
import os


class LiveImageProcessor:
    CHECKERBOARD = (9, 6)
    SQUARE_SIZE_MM = 5.0
    DEFAULT_MM_PER_PIXEL = 0.1549

    def __init__(self, window, title):
        self.window = window
        self.window.title(title)
        self.window.geometry("1150x780")
        self.window.resizable(True, True)
        self.window.configure(bg="#f5f5f7")

        # Camera Configuration
        self.camera_index = 1
        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        self.canvas_width = 800
        self.canvas_height = 450
        self.camera_error_count = 0
        self.max_frame_failures = 30
        self.reconnect_check_interval = 15
        self.camera_retrying = False

        if not self.cap.isOpened():
            messagebox.showerror("Camera Error", "Cannot open camera")
            self.window.destroy()
            return

        # Styles
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TLabelframe", background="#f5f5f7", borderwidth=1, relief="solid")
        self.style.configure("TLabelframe.Label", font=("Arial", 11, "bold"), background="#f5f5f7", foreground="#333333")

        # ==================== UPPER VIDEO CANVAS ====================
        self.canvas = tk.Canvas(
            window,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="#1e1e1e",
            highlightthickness=0,
        )
        self.canvas.pack(pady=15)

        # ==================== MAIN CONTROLS CONTAINER ====================
        main_ctrl_frame = ttk.Frame(window, padding=10)
        main_ctrl_frame.pack(fill="both", expand=True, padx=15, pady=5)

        main_ctrl_frame.columnconfigure(0, weight=1, uniform="group1")
        main_ctrl_frame.columnconfigure(1, weight=1, uniform="group1")
        main_ctrl_frame.rowconfigure(0, weight=1)

        # ====================== LEFT SIDE - IMAGE CONTROLS ======================
        left_frame = ttk.LabelFrame(main_ctrl_frame, text=" IMAGE CONTROLS ")
        left_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        left_frame.columnconfigure(1, weight=1)

        row = 0
        tk.Label(left_frame, text="Brightness", font=("Arial", 10), bg="#f5f5f7").grid(
            row=row, column=0, padx=10, pady=6, sticky="e"
        )
        self.brightness = Scale(left_frame, from_=-100, to=100, orient=HORIZONTAL, bg="#f5f5f7", highlightthickness=0)
        self.brightness.set(0)
        self.brightness.grid(row=row, column=1, padx=10, pady=6, sticky="ew")
        row += 1

        tk.Label(left_frame, text="Contrast", font=("Arial", 10), bg="#f5f5f7").grid(
            row=row, column=0, padx=10, pady=6, sticky="e"
        )
        self.contrast = Scale(left_frame, from_=1, to=300, orient=HORIZONTAL, bg="#f5f5f7", highlightthickness=0)
        self.contrast.set(100)
        self.contrast.grid(row=row, column=1, padx=10, pady=6, sticky="ew")
        row += 1

        tk.Label(left_frame, text="Threshold", font=("Arial", 10), bg="#f5f5f7").grid(
            row=row, column=0, padx=10, pady=6, sticky="e"
        )
        self.threshold = Scale(left_frame, from_=0, to=255, orient=HORIZONTAL, bg="#f5f5f7", highlightthickness=0)
        self.threshold.set(127)
        self.threshold.grid(row=row, column=1, padx=10, pady=6, sticky="ew")
        row += 1

        modes_frame = tk.Frame(left_frame, bg="#f5f5f7")
        modes_frame.grid(row=row, column=0, columnspan=2, pady=8, padx=10, sticky="w")

        self.mode = tk.StringVar(value="normal")
        tk.Radiobutton(modes_frame, text="Normal View", variable=self.mode, value="normal", bg="#f5f5f7").pack(
            side="left", padx=10
        )
        tk.Radiobutton(modes_frame, text="Threshold View", variable=self.mode, value="threshold", bg="#f5f5f7").pack(
            side="left", padx=10
        )
        tk.Radiobutton(modes_frame, text="Edge Detection", variable=self.mode, value="edges", bg="#f5f5f7").pack(
            side="left", padx=10
        )
        row += 1

        self.measure_mode = tk.BooleanVar(value=True)
        tk.Checkbutton(
            left_frame,
            text="Enable Target Tracking & Measurement",
            variable=self.measure_mode,
            font=("Arial", 10, "bold"),
            bg="#f5f5f7",
            fg="#1b5e20",
        ).grid(row=row, column=0, columnspan=2, pady=10, padx=10, sticky="w")
        row += 1

        self.dynamic_scale_mode = tk.BooleanVar(value=True)
        tk.Checkbutton(
            left_frame,
            text="Use Checkerboard Dynamic Scale",
            variable=self.dynamic_scale_mode,
            font=("Arial", 10, "bold"),
            bg="#f5f5f7",
            fg="#1565c0",
        ).grid(row=row, column=0, columnspan=2, pady=6, padx=10, sticky="w")

        # ====================== RIGHT SIDE - CALIBRATION & METRICS ======================
        right_frame = ttk.LabelFrame(main_ctrl_frame, text=" CALIBRATION & DATA ")
        right_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        right_frame.columnconfigure(1, weight=1)

        tk.Label(right_frame, text="Square Size (mm):", font=("Arial", 10), bg="#f5f5f7").grid(
            row=0, column=0, padx=10, pady=8, sticky="e"
        )
        self.square_size_var = tk.DoubleVar(value=self.SQUARE_SIZE_MM)
        self.square_entry = ttk.Entry(right_frame, textvariable=self.square_size_var, width=15)
        self.square_entry.grid(row=0, column=1, padx=10, pady=8, sticky="w")

        btn_frame = tk.Frame(right_frame, bg="#f5f5f7")
        btn_frame.grid(row=1, column=0, columnspan=2, pady=8, padx=10, sticky="ew")

        tk.Button(
            btn_frame,
            text="Save Config",
            bg="#2196F3",
            fg="white",
            font=("Arial", 9, "bold"),
            width=11,
            relief="flat",
            command=self.save_calibration,
        ).pack(side="left", padx=3)
        tk.Button(
            btn_frame,
            text="Load Config",
            bg="#FF9800",
            fg="white",
            font=("Arial", 9, "bold"),
            width=11,
            relief="flat",
            command=self.load_calibration,
        ).pack(side="left", padx=3)
        tk.Button(
            btn_frame,
            text="Reset Default",
            bg="#f44336",
            fg="white",
            font=("Arial", 9, "bold"),
            width=12,
            relief="flat",
            command=self.reset_calibration,
        ).pack(side="left", padx=3)

        self.mm_per_pixel = self.DEFAULT_MM_PER_PIXEL
        self.pixels_per_mm = 1.0 / self.mm_per_pixel
        self.calibration_file = "calibration_dynamic.json"

        self.calib_label = tk.Label(
            right_frame,
            text=f"Waiting for checkerboard | Default {self.mm_per_pixel:.4f} mm/px",
            fg="#1565c0",
            font=("Arial", 10, "bold"),
            bg="#f5f5f7",
        )
        self.calib_label.grid(row=2, column=0, columnspan=2, pady=2)

        self.status_label = tk.Label(
            right_frame,
            text="Camera status: OK",
            fg="#2e7d32",
            font=("Arial", 10, "bold"),
            bg="#f5f5f7",
        )
        self.status_label.grid(row=3, column=0, columnspan=2, pady=2)

        table_frame = ttk.Frame(right_frame)
        table_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        right_frame.rowconfigure(4, weight=1)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("Dimension", "Pixels", "Millimeters", "Centimeters"),
            show="headings",
            height=3,
        )
        self.tree.pack(fill="both", expand=True)

        self.tree.heading("Dimension", text="Dimension")
        self.tree.heading("Pixels", text="Pixels (px)")
        self.tree.heading("Millimeters", text="Metric (mm)")
        self.tree.heading("Centimeters", text="Metric (cm)")

        self.tree.column("Dimension", width=100, anchor="center")
        self.tree.column("Pixels", width=90, anchor="center")
        self.tree.column("Millimeters", width=90, anchor="center")
        self.tree.column("Centimeters", width=90, anchor="center")

        self.tree.insert("", "end", iid="dimA", values=("Width", "0.00", "0.00", "0.00"))
        self.tree.insert("", "end", iid="dimB", values=("Height", "0.00", "0.00", "0.00"))

        self.roi_start = None
        self.roi_end = None
        self.selecting_roi = False

        self.criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            30,
            0.001,
        )

        self.load_calibration(auto=True)

        self.canvas.bind("<ButtonPress-1>", self.start_roi)
        self.canvas.bind("<B1-Motion>", self.update_roi)
        self.canvas.bind("<ButtonRelease-1>", self.end_roi)

        self.update_frame()
        self.window.protocol("WM_DELETE_WINDOW", self.close)

    # ====================== ROI MANAGERS ======================
    def start_roi(self, event):
        self.roi_start = (event.x, event.y)
        self.roi_end = (event.x, event.y)
        self.selecting_roi = True

    def update_roi(self, event):
        if self.selecting_roi:
            self.roi_end = (event.x, event.y)

    def end_roi(self, event):
        self.roi_end = (event.x, event.y)
        self.selecting_roi = False

    # ====================== IMAGE PROCESSING pipeline ======================
    def process_frame(self, frame):
        brightness = self.brightness.get()
        contrast = self.contrast.get() / 100.0
        frame = cv2.convertScaleAbs(frame, alpha=contrast, beta=brightness)

        mode = self.mode.get()
        if mode == "threshold":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, frame = cv2.threshold(gray, self.threshold.get(), 255, cv2.THRESH_BINARY)
        elif mode == "edges":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = cv2.Canny(gray, self.threshold.get(), self.threshold.get() * 2)
        return frame

    # ====================== DYNAMIC CHECKERBOARD SCALE ======================
    def update_dynamic_scale(self, frame, display):
        if not self.dynamic_scale_mode.get():
            return display

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found, corners = cv2.findChessboardCornersSB(
            gray,
            self.CHECKERBOARD,
            flags=cv2.CALIB_CB_EXHAUSTIVE + cv2.CALIB_CB_ACCURACY,
        )

        if not found:
            cv2.putText(
                display,
                "Checkerboard NOT detected",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )
            return display

        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), self.criteria)
        cv2.drawChessboardCorners(display, self.CHECKERBOARD, corners, found)

        corners = corners.reshape(-1, 2)
        cols, rows = self.CHECKERBOARD
        distances = []

        for r in range(rows):
            for c in range(cols - 1):
                idx1 = r * cols + c
                idx2 = r * cols + (c + 1)
                distances.append(np.linalg.norm(corners[idx1] - corners[idx2]))

        for r in range(rows - 1):
            for c in range(cols):
                idx1 = r * cols + c
                idx2 = (r + 1) * cols + c
                distances.append(np.linalg.norm(corners[idx1] - corners[idx2]))

        try:
            square_size_mm = float(self.square_size_var.get())
            if square_size_mm <= 0:
                raise ValueError
        except ValueError:
            square_size_mm = self.SQUARE_SIZE_MM
            self.square_size_var.set(square_size_mm)

        avg_square_px = np.mean(distances)
        self.pixels_per_mm = avg_square_px / square_size_mm
        self.mm_per_pixel = 1.0 / self.pixels_per_mm

        self.calib_label.config(
            text=f"Live Scale: {self.pixels_per_mm:.3f} px/mm | {self.mm_per_pixel:.4f} mm/px",
            fg="#2e7d32",
        )

        cv2.putText(
            display,
            f"Scale: {self.pixels_per_mm:.3f} px/mm",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        return display

    # ====================== CALIBRATION CONTROLS ======================
    def save_calibration(self):
        try:
            data = {
                "mm_per_pixel": self.mm_per_pixel,
                "pixels_per_mm": self.pixels_per_mm,
                "square_size_mm": float(self.square_size_var.get()),
            }
            with open(self.calibration_file, "w") as f:
                json.dump(data, f, indent=4)
            self.calib_label.config(text="Configuration Saved Perfectly", fg="#2e7d32")
        except Exception as e:
            messagebox.showerror("Error", f"Disk I/O Write Exception: {e}")

    def load_calibration(self, auto=False):
        if not os.path.exists(self.calibration_file):
            if not auto:
                messagebox.showinfo("Info", "No profile discovered. Reverting to system defaults.")
            self.reset_calibration()
            return
        try:
            with open(self.calibration_file, "r") as f:
                data = json.load(f)
            self.mm_per_pixel = data.get("mm_per_pixel", self.DEFAULT_MM_PER_PIXEL)
            self.pixels_per_mm = data.get("pixels_per_mm", 1.0 / self.mm_per_pixel)
            self.square_size_var.set(data.get("square_size_mm", self.SQUARE_SIZE_MM))
            self.calib_label.config(text=f"Loaded | {self.mm_per_pixel:.4f} mm/px", fg="#2e7d32")
        except Exception:
            if not auto:
                messagebox.showerror("Error", "Corrupt data block formatting parsed on read.")

    def reset_calibration(self):
        self.mm_per_pixel = self.DEFAULT_MM_PER_PIXEL
        self.pixels_per_mm = 1.0 / self.mm_per_pixel
        self.square_size_var.set(self.SQUARE_SIZE_MM)
        self.calib_label.config(text=f"Default Scale: {self.mm_per_pixel:.4f} mm/px", fg="#1565c0")
        self.tree.item("dimA", values=("Width", "0.00", "0.00", "0.00"))
        self.tree.item("dimB", values=("Height", "0.00", "0.00", "0.00"))

    def set_status(self, text, color="#1565c0"):
        if hasattr(self, "status_label"):
            self.status_label.config(text=text, fg=color)

    def open_camera(self):
        if hasattr(self, "cap") and self.cap is not None and self.cap.isOpened():
            self.cap.release()
        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.camera_retrying = False
        return self.cap.isOpened()

    def attempt_reconnect(self):
        self.set_status("Camera disconnected. Attempting reconnect...", "#d32f2f")
        success = self.open_camera()
        if success:
            self.camera_error_count = 0
            self.set_status("Camera reconnected", "#2e7d32")
            self.camera_retrying = False
        else:
            self.camera_retrying = True
        return success

    def make_error_display(self, width, height):
        display = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.putText(
            display,
            "Camera error: no frame",
            (20, height // 2 - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
        )
        cv2.putText(
            display,
            "Reconnect in progress...",
            (20, height // 2 + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            1,
        )
        return display

    # ====================== MACHINE VISION INTERFACE ======================
    def measure_objects(self, frame, display):
        if not (self.roi_start and self.roi_end):
            return display

        x1, y1 = self.roi_start
        x2, y2 = self.roi_end
        x_min, x_max = min(x1, x2), max(x1, x2)
        y_min, y_max = min(y1, y2), max(y1, y2)

        x_min = max(0, min(self.canvas_width - 1, x_min))
        x_max = max(0, min(self.canvas_width, x_max))
        y_min = max(0, min(self.canvas_height - 1, y_min))
        y_max = max(0, min(self.canvas_height, y_max))

        roi = frame[y_min:y_max, x_min:x_max]
        if roi.size == 0:
            return display

        roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(roi_gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thresh = 255 - thresh

        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return display

        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) <= 500:
            return display

        rect = cv2.minAreaRect(largest)
        box = cv2.boxPoints(rect)
        box = np.int32(box)
        box[:, 0] += x_min
        box[:, 1] += y_min

        cv2.drawContours(display, [box], 0, (0, 255, 0), 2)

        width_px = rect[1][0]
        height_px = rect[1][1]
        width_mm = width_px * self.mm_per_pixel
        height_mm = height_px * self.mm_per_pixel
        width_cm = width_mm / 10.0
        height_cm = height_mm / 10.0

        self.tree.item("dimA", values=("Width", f"{width_px:.2f}", f"{width_mm:.1f}", f"{width_cm:.2f}"))
        self.tree.item("dimB", values=("Height", f"{height_px:.2f}", f"{height_mm:.1f}", f"{height_cm:.2f}"))

        center_x = int(rect[0][0]) + x_min
        center_y = int(rect[0][1]) + y_min
        text = f"{width_mm:.1f} mm x {height_mm:.1f} mm"

        cv2.putText(
            display,
            text,
            (center_x - 80, center_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 255),
            2,
        )

        return display

    # ====================== FRAME LOOP ======================
    def update_frame(self):
        if not hasattr(self, "cap") or self.cap is None:
            display = self.make_error_display(self.canvas_width, self.canvas_height)
            self.set_status("Camera not initialized", "#d32f2f")
        else:
            ret, frame = self.cap.read()
            if ret:
                self.camera_error_count = 0
                if self.camera_retrying:
                    self.set_status("Camera reconnected", "#2e7d32")
                    self.camera_retrying = False

                frame = cv2.resize(frame, (self.canvas_width, self.canvas_height))
                adjusted_frame = cv2.convertScaleAbs(
                    frame,
                    alpha=self.contrast.get() / 100.0,
                    beta=self.brightness.get(),
                )
                processed = self.process_frame(frame.copy())
                display = processed.copy()

                if len(display.shape) == 2:
                    display = cv2.cvtColor(display, cv2.COLOR_GRAY2BGR)

                display = self.update_dynamic_scale(adjusted_frame, display)

                if self.measure_mode.get():
                    display = self.measure_objects(adjusted_frame, display)

                if self.roi_start and self.roi_end:
                    cv2.rectangle(display, self.roi_start, self.roi_end, (255, 235, 59), 2)

                cv2.putText(
                    display,
                    "Drag Mouse = ROI",
                    (20, display.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2,
                )
            else:
                self.camera_error_count += 1
                if self.camera_error_count >= self.max_frame_failures:
                    if self.camera_error_count % self.reconnect_check_interval == 0:
                        self.attempt_reconnect()
                    else:
                        self.set_status(
                            f"Camera disconnected. Retrying... ({self.camera_error_count})",
                            "#d32f2f",
                        )
                else:
                    self.set_status(
                        f"Frame read failure {self.camera_error_count}/{self.max_frame_failures}",
                        "#ff9800",
                    )
                display = self.make_error_display(self.canvas_width, self.canvas_height)

        display = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(display)
        imgtk = ImageTk.PhotoImage(image=img)
        self.canvas.imgtk = imgtk
        self.canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)

        self.window.after(10, self.update_frame)

    def close(self):
        if self.cap.isOpened():
            self.cap.release()
        self.window.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = LiveImageProcessor(root, "Real-Time Dynamic Measurement Workspace")
    root.mainloop()
