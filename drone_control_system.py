from djitellopy import Tello
from loggingSystem import Logger
import threading
import time


class DroneControlSystem:
    """
    Drone Kontrol Sistemi
    Manuel Kontrol
    """
    def __init__(self):
        self.logger = Logger("DRONE", Logger.RED)
        self.tello = Tello()
        self.tello.connect()
        
        self.tello.streamon()
        self.frame_read = self.tello.get_frame_read()

        # RC
        self.lr = 0
        self.fb = 0
        self.ud = 0
        self.yaw = 0
        
        self.running = True
        
        # Thread
        self.thread = threading.Thread(target=self._rc_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def _rc_loop(self):
        while self.running:
            try:
                self.tello.send_rc_control(self.lr, self.fb, self.ud, self.yaw)
            except Exception as e:
                self.logger.log(f"RC ERROR {e}")
                
            time.sleep(0.05)
    
    def get_frame(self):
        return self.frame_read.frame
    
    def takeoff(self):
        if self.tello is None:
            return
        try:
            self.tello.takeoff()
        except:
            print("Hata")
    
    def land(self):
        if self.tello is None:
            return
        
        try:
            self.tello.land()
        except:
            print("hata")
    
    def set_movement(self, lr=0, fb=0, ud=0, yaw=0):
        self.lr = lr
        self.fb = fb
        self.ud = ud
        self.yaw = yaw
        
    def shutdown(self):
        self.logger.log("Shutting down...")
        
        self.running = False
        self.thread.join(timeout=1)
        
        try:
            self.tello.send_rc_control(0, 0, 0, 0)
        except:
            pass
        
        self.tello.streamoff()
        self.tello.end()
        
        self.logger.log("Drone Disconnected")
        
        

        
        
        
        
        
    
        