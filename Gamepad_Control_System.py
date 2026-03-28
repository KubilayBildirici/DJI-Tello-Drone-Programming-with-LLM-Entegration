import pygame

class GamepadController:
    def __init__(self, drone):
        self.drone = drone
        pygame.init()
        pygame.joystick.init()
        
        if pygame.joystick.get_count() == 0:
            raise Exception("Gamepad not found")

        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        
        print(f"Gamepad e baglandi:{self.joystick.get_name()}")
        
        self.FLYING = False
    
    def deadzone(self, value, threshold = 0.1):
        return 0 if abs(value) < threshold else value
    
    
    def update(self):
        pygame.event.pump()
        
        #print("Axis count:", self.joystick.get_numaxes())
        
        lr = self.deadzone(self.joystick.get_axis(0))
        fb = self.deadzone(self.joystick.get_axis(1))
        
        ud = 0        
        yaw = 0
        
        # yaw (L1/R1)
        if self.joystick.get_button(9): # L1 -> oldugun yerde sola don
            yaw = -50
        if self.joystick.get_button(10): # R1 -> oldugun yerde saga don
            yaw = 50
        
        # Yukseklik (L2/R2)
        l2 = self.joystick.get_axis(4)
        r2 = self.joystick.get_axis(5)

        l2 = (l2 + 1) / 2
        r2 = (r2 + 1) / 2
        
        if r2 > 0.3:
            ud = int(r2 * 70)
        elif l2 > 0.3:
            ud = -int(l2 * 70)
        
        
        if abs(ud) < 10:
            ud = 0
        
        # scale
        lr = int(lr * 70)
        fb = int(-fb * 70)
        
        self.drone.set_movement(lr, fb, ud, yaw)
        
        # X -> Takeoff
        if self.joystick.get_button(0): # X -> TAKEOFF
            if not self.FLYING:
                self.drone.takeoff()
                self.FLYING = True
        
        if self.joystick.get_button(1): # O -> LAND
            if self.FLYING:
                self.drone.land()
                self.FLYING = False
                    
        

    
