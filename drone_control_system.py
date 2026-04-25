from djitellopy import Tello
from loggingSystem import Logger
from config import Config
import threading
import time


class DroneControlSystem:
    """
    Tello drone için thread-safe RC kontrol sistemi.
    RC komutları sabit frekansta ayrı bir thread'den gönderilir.
    """

    def __init__(self) -> None:
        self.logger = Logger("DRONE", Logger.RED)
        self.tello = Tello()
        self.tello.connect()

        self.tello.streamon()
        self.frame_read = self.tello.get_frame_read()

        # Paylaşılan RC değerleri — lock ile korunur
        self._lock = threading.Lock()
        self._lr: int = 0
        self._fb: int = 0
        self._ud: int = 0
        self._yaw: int = 0

        self._running = True

        self._thread = threading.Thread(target=self._rc_loop, daemon=True)
        self._thread.start()
        self.logger.log("Drone connected and stream started.")

    # ── RC loop ──────────────────────────────────────────────────────────────

    def _rc_loop(self) -> None:
        while self._running:
            with self._lock:
                lr, fb, ud, yaw = self._lr, self._fb, self._ud, self._yaw
            try:
                self.tello.send_rc_control(lr, fb, ud, yaw)
            except Exception as e:
                self.logger.error(f"RC send failed: {e}")
            time.sleep(Config.RC_LOOP_INTERVAL)

    # ── Public API ───────────────────────────────────────────────────────────

    def get_frame(self):
        return self.frame_read.frame

    def set_movement(self, lr: int = 0, fb: int = 0, ud: int = 0, yaw: int = 0) -> None:
        """Thread-safe RC değer güncellemesi."""
        with self._lock:
            self._lr = lr
            self._fb = fb
            self._ud = ud
            self._yaw = yaw

    def takeoff(self) -> None:
        try:
            self.tello.takeoff()
            self.logger.log("Takeoff command sent.")
        except Exception as e:
            self.logger.error(f"Takeoff failed: {e}")

    def land(self) -> None:
        try:
            self.tello.land()
            self.logger.log("Land command sent.")
        except Exception as e:
            self.logger.error(f"Land failed: {e}")

    def shutdown(self) -> None:
        self.logger.log("Shutting down...")
        self._running = False
        self._thread.join(timeout=2)

        try:
            self.tello.send_rc_control(0, 0, 0, 0)
        except Exception:
            pass

        try:
            self.tello.streamoff()
            self.tello.end()
        except Exception as e:
            self.logger.error(f"Shutdown error: {e}")

        self.logger.log("Drone disconnected.")


        
        
        
        
        
    
        