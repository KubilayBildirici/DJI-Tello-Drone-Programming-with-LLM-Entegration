import sys
import cv2

from PySide6.QtCore import QTimer, QObject, QThread, Signal
from PySide6.QtGui import QImage, QPixmap, QMovie
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QFrame, QVBoxLayout, QHBoxLayout, QFileDialog
)
from drone_control_system import DroneControlSystem
from Gamepad_Control_System import GamepadController
from llm import analyze_frame, encode_frame
import time
from PySide6.QtCore import Qt

class ConnectWorker(QObject):
    finished = Signal(object, object) # drone, gamepad
    error = Signal(str)
    
    def run(self):
        try:
            drone = DroneControlSystem()
            gamepad = GamepadController(drone)
            self.finished.emit(drone, gamepad)
        except Exception as e:
            self.error.emit(str(e))


class LLMWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, target_b64, frame_b64):
        super().__init__()
        self.target_b64 = target_b64
        self.frame_b64 = frame_b64

    def run(self):
        try:
            result = analyze_frame(self.target_b64, self.frame_b64)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class DroneUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setStyleSheet("""
        QWidget {
            background-color: #000000;  /* 🔥 saf siyah */
            color: #e0e0e0;
            font-family: Segoe UI;
            font-size: 13px;
        }

        /* LABEL */
        QLabel {
            font-size: 14px;
        }

        /* PANEL */
        QFrame {
            background-color: #1a1a1a;  /* siyah üstünde hafif ayrım */
            border-radius: 12px;
            border: 1px solid #333;
        }

        /* BUTTON */
        QPushButton {
            background-color: #111;
            border-radius: 8px;
            padding: 8px;
            font-weight: bold;
            border: 1px solid #333;
        }

        QPushButton:hover {
            background-color: #1f1f1f;
            border: 1px solid #00ffaa;
            color: #00ffaa;
        }

        QPushButton:pressed {
            background-color: #050505;
        }

        /* WARNING */
        QLabel#warning {
            color: white;
            background-color: #c0392b;
            padding: 6px;
            border-radius: 6px;
            font-weight: bold;
        }

        /* TARGET STATES */
        QLabel#target_ok {
            color: #00ff88;
        }

        QLabel#target_fail {
            color: #ff4444;
        }
        
        QFrame#right_panel {
            background-color: #000000;
            border-radius: 12px;
            border: 1px solid #333;
        }
        
        QFrame#right_panel * {
            background-color: transparent;
        }
        
        """)
        
        self.setWindowTitle("Drone Control System")
        self.setGeometry(100, 100, 800, 600)
        
        # Drone
        self.drone = None
        self.gamepad = None
        
        self.last_gamepad_update = 0
        self.llm_busy = False
        self.connect_busy = False
        self.last_result = False
        self.interval = 5
        self.last_capture = 0
        
        self.connect_thread = None
        self.connect_worker = None
        self.llm_thread = None
        self.llm_worker = None
        
        
    
        # Left Panel (State)
        
        label_style = """
        padding: 6px;
        background-color: #3a3a3a;
        border-radius: 6px;
        """
                
        ## Test icin yazildi
        self.target_label = QLabel("target: -")
        ## Test icin yazildi
        self.battery_label = QLabel("Battery: -")
        self.height_label = QLabel("Height: -")
        self.speed_label = QLabel("Speed: -")
        self.temp_label = QLabel("Temp: -")
        self.image_label = QLabel("Henuz resim secilmedi")
        self.image_label.setFixedSize(200, 150)
        self.image_label.setStyleSheet("""
            border: 2px dashed #666;
            border-radius: 8px;
            padding: 5px;
        """)      
        self.image_label.setAlignment(Qt.AlignCenter)
        
        self.target_label.setStyleSheet(label_style)
        self.battery_label.setStyleSheet(label_style)
        self.height_label.setStyleSheet(label_style)
        self.speed_label.setStyleSheet(label_style)
        self.temp_label.setStyleSheet(label_style)
        
        self.warning_label = QLabel("Not Connected")
        self.warning_label.setObjectName("warning")
        
        self.btn_connect = QPushButton("Connect")

        #self.warning_label = QLabel("")
        self.warning_label.setObjectName("warning")
        
        self.image_button = QPushButton("resim sec")
        self.btn_connect = QPushButton("Connect")
        self.btn_takeoff = QPushButton("Takeoff")
        self.btn_land = QPushButton("Land")
        
        self.btn_takeoff.setEnabled(False)
        self.btn_land.setEnabled(False)
        
        left_panel = QFrame()
        left_panel_layout = QVBoxLayout()
        
        left_panel_layout.setSpacing(10)
        left_panel_layout.setContentsMargins(10,10,10,10)
        
        left_panel_layout.addWidget(self.target_label)
        left_panel_layout.addWidget(self.battery_label)
        left_panel_layout.addWidget(self.height_label)
        left_panel_layout.addWidget(self.speed_label)
        left_panel_layout.addWidget(self.temp_label)
        left_panel_layout.addWidget(self.warning_label)
        left_panel_layout.addWidget(self.image_label)
        left_panel_layout.addStretch()
        
        ## Buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_connect)
        button_layout.addWidget(self.btn_takeoff)
        button_layout.addWidget(self.btn_land)
        button_layout.addWidget(self.image_button)
        
        left_panel_layout.addLayout(button_layout)
        left_panel.setLayout(left_panel_layout)
        
        # RIGHT PANEL
        right_panel = QFrame()
        right_layout = QVBoxLayout()
        right_panel.setObjectName("right_panel")
        
        right_layout.setSpacing(12)
        right_layout.setContentsMargins(10,10,10,10)
        right_layout.setAlignment(Qt.AlignCenter)
        
        self.gif_label = QLabel()
        self.gif_label.setFixedSize(620, 360)
        self.gif_label.setAlignment(Qt.AlignCenter)

        self.gif_label.setStyleSheet("""
            background-color: black;
            border-radius: 12px;
            order: 1px solid #00c8aa;
        """)
        
        self.ai_title = QLabel("Drone Control System DJI-Tello")
        self.ai_title.setAlignment(Qt.AlignCenter)
        self.ai_title.setStyleSheet("""
            color: #00ffaa;
            font-weight: bold;
            font-size: 16px;
            padding: 6px;
            border: 1px solid #222;
            border-radius: 10px;
            background-color: #050505;
        """)
                
        from PySide6.QtGui import QMovie
        from PySide6.QtCore import QSize

        self.movie = QMovie("C:\\Users\\kubilay\\Desktop\\Tello_Drone\\2.gif")
        self.movie.setScaledSize(QSize(620, 360))

        self.gif_label.setMovie(self.movie)
        self.movie.start()
        
        right_layout.addWidget(self.ai_title)
        right_layout.addWidget(self.gif_label)
        right_panel.setLayout(right_layout)
        right_layout.addStretch()        
        
        # VIDEO PANEL
        self.video_label = QLabel()
        self.video_label.setStyleSheet("""
            border-radius: 12px;
            background-color: black;
            border: 2px solid #444;
        """)
        
        self.video_label.setFixedSize(640, 480)
        self.video_label.setScaledContents(True)
                
        video_frame = QFrame()
        video_layout = QVBoxLayout()


        video_layout.addWidget(self.video_label)
        video_frame.setLayout(video_layout)
        
        
        ## MAIN LAYOUT
        main_layout = QHBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15,15,15,15)
        
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(video_frame, 2)
        main_layout.addWidget(right_panel, 1)
        
        self.setLayout(main_layout)
        
        # connection to buttons
        self.btn_connect.clicked.connect(self.connect_drone)
        self.btn_takeoff.clicked.connect(self.takeoff)
        self.btn_land.clicked.connect(self.land)
        self.image_button.clicked.connect(self.load_image)
        
        # video timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_all)
        self.timer.start(30)
    
    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Bir resim sec",
            "",
            "Images (*.jpg *.png *.jpeg)"
        )
        
        if not file_path:
            return

        pixmap = QPixmap(file_path)

        if pixmap.isNull():
            self.image_label.setText("Resim yuklenemedi")
            return

        scaled_pixmap = pixmap.scaled(
            200, 150,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.image_label.setPixmap(scaled_pixmap)

        # 🔥 LLM target update
        self.target_image = cv2.imread(file_path)
        self.target_b64 = encode_frame(self.target_image)

        print("Target updated")
    
    def takeoff(self):
        if self.drone is None:
            self.warning_label.setText("❌ Drone not connected")
            return
        
        try:
            self.drone.takeoff()
        except:
            self.warning_label.setText("❌ Takeoff error")
        
    def land(self):
        if self.drone is None:
            self.warning_label.setText("❌ Drone not connected")
            return
        
        try:
            self.drone.land()
        except:
            self.warning_label.setText("❌ land error")

    
    def connect_drone(self):
        if self.connect_busy:
            return

        self.connect_busy = True
        self.warning_label.setText("Connecting..")
        self.btn_connect.setEnabled(False)

        self.connect_thread = QThread()
        self.connect_worker = ConnectWorker()
        self.connect_worker.moveToThread(self.connect_thread)

        self.connect_thread.started.connect(self.connect_worker.run)
        self.connect_worker.finished.connect(self.on_connect_success)
        self.connect_worker.error.connect(self.on_connect_error)

        self.connect_worker.finished.connect(self.connect_thread.quit)
        self.connect_worker.error.connect(self.connect_thread.quit)

        self.connect_thread.finished.connect(self.cleanup_connect_thread)
        self.connect_thread.finished.connect(self.connect_worker.deleteLater)
        self.connect_thread.finished.connect(self.connect_thread.deleteLater)

        self.connect_thread.start()
    
    def on_connect_success(self, drone, gamepad):
        self.drone = drone
        self.gamepad = gamepad
        self.connect_busy = False
        
        self.warning_label.setText("Connected")
        self.btn_connect.setEnabled(True)
        self.btn_takeoff.setEnabled(True)
        self.btn_land.setEnabled(True)
    
    
    def on_connect_error(self, message):
        print("Connect error", message)
        self.connect_busy = False
        self.warning_label.setText("Connection Failed")
        self.btn_connect.setEnabled(True)
    
    def start_llm_worker(self, frame_b64):
        if self.target_b64 is None:
            return

        if self.llm_thread is not None:
            try:
                if self.llm_thread.isRunning():
                    return
            except RuntimeError:
                self.llm_thread = None
                self.llm_worker = None

        self.llm_thread = QThread()
        self.llm_worker = LLMWorker(self.target_b64, frame_b64)
        self.llm_worker.moveToThread(self.llm_thread)

        self.llm_thread.started.connect(self.llm_worker.run)
        self.llm_worker.finished.connect(self.on_llm_result)
        self.llm_worker.error.connect(self.on_llm_error)

        self.llm_worker.finished.connect(self.llm_thread.quit)
        self.llm_worker.error.connect(self.llm_thread.quit)

        self.llm_thread.finished.connect(self.cleanup_llm_thread)
        self.llm_thread.finished.connect(self.llm_worker.deleteLater)
        self.llm_thread.finished.connect(self.llm_thread.deleteLater)

        self.llm_thread.start()
    
    def cleanup_llm_thread(self):
        self.llm_thread = None
        self.llm_worker = None
    
    def cleanup_connect_thread(self):
        self.connect_thread = None
        self.connect_worker = None
    
    
    def on_llm_result(self, result):
        self.llm_busy = False
        
        if result != self.last_result:
            self.last_result = result
            print("SONUC:", result)
            self.target_label.setText(result)
            
            base_style = """
                padding: 6px;
                background-color: #3a3a3a;
                border-radius: 6px;
            """

            if result == "HEDEF BULUNDU":
                self.target_label.setStyleSheet(base_style + "color: green;")
            else:
                self.target_label.setStyleSheet(base_style + "color: red;")
    
    def on_llm_error(self, message):
        print("LLM ERROR", message)
        self.llm_busy = False
                
    def update_warning(self):
        
        if self.drone is None:
            return
        
        try:
            battery = self.drone.tello.get_battery()
            temp = self.drone.tello.get_temperature()
                
            warning_text = ""
                
            if battery < 20:
                warning_text = "⚠️ LOW BATTERY"
                
            elif temp > 80:
                warning_text = "🔥 HIGH TEMPERATURE"
                
            self.warning_label.setText(warning_text)
            
        except:
            self.warning_label.setText("⚠️ CONNECTION ERROR")
    
    
    def update_all(self):
        
        if self.drone is None:
            return
        
        
        # Gamepad input
        try:
            if self.gamepad is not None and time.time() - self.last_gamepad_update > 0.1:
                self.gamepad.update()
                self.last_gamepad_update = time.time()
        except Exception as e:
            print("GAMEPAD ERROR:", e)
        
        
        # Video
        try:
            frame = self.drone.get_frame()
            
            if frame is not None:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                
                qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
                self.video_label.setPixmap(QPixmap.fromImage(qt_image))
                
                current_time = time.time()
                
                if current_time - self.last_capture > self.interval and not self.llm_busy:
                    frame_small = cv2.resize(frame, (320, 320))
                    frame_b64 = encode_frame(frame_small)
                    
                    self.last_capture = current_time
                    self.start_llm_worker(frame_b64)
                    
        except Exception as e:
            print("VIDEO ERROR", e)
        
                
        # STATES
        try:
            self.battery_label.setText(f"🔋 Battery: {self.drone.tello.get_battery()}%")
            self.height_label.setText(f"📏 Height: {self.drone.tello.get_height()} cm")
            self.speed_label.setText(f"🚀 Speed: {self.drone.tello.get_speed_x()} cm/s")
            self.temp_label.setText(f"🌡 Temp: {self.drone.tello.get_temperature()}°C")
        except Exception as e:
            print("STATE ERROR", e)
            
        # WARNING
        self.update_warning()
        

    
    def closeEvent(self,event):
        self.timer.stop()
        
        if self.llm_thread is not None and self.llm_thread.isRunning():
            self.llm_thread.quit()
            self.llm_thread.wait()
        
        if self.connect_thread is not None and self.connect_thread.isRunning():
            self.connect_thread.quit()
            self.connect_thread.wait()
        if self.drone:
            try:
                self.drone.shutdown()
            except Exception as e:
                print("SHUTDOWN ERROR", e)
        
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DroneUI()
    window.show()
    sys.exit(app.exec())

        