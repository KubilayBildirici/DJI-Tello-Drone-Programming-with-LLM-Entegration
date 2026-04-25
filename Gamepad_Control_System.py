import pygame
from config import Config
from loggingSystem import Logger


class GamepadController:
    """
    PlayStation/Xbox gamepad → Tello RC komut eşleştirmesi.

    Eksen / Buton Eşleştirmesi (PS4 DualShock düzenine göre):
        Axis 0  — Sol stick X    : sol/sağ (lr)
        Axis 1  — Sol stick Y    : ileri/geri (fb)
        Axis 4  — L2             : aşağı iniş (ud–)
        Axis 5  — R2             : yukarı çıkış (ud+)
        Button 0 — X             : kalkış (takeoff)
        Button 1 — O             : iniş (land)
        Button 9 — L1            : sola dönüş (yaw–)
        Button 10 — R1           : sağa dönüş (yaw+)
    """

    YAW_SPEED = 50  # yaw dönüş hızı (sabit)

    def __init__(self, drone) -> None:
        self.drone = drone
        self.logger = Logger("GAMEPAD", Logger.BLUE)

        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            raise RuntimeError("Gamepad not found. Please connect a controller.")

        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        self.logger.log(f"Connected: {self.joystick.get_name()}")

        self._flying = False

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _deadzone(self, value: float) -> float:
        return 0.0 if abs(value) < Config.GAMEPAD_DEADZONE else value

    # ── Main update ───────────────────────────────────────────────────────────

    def update(self) -> None:
        """Gamepad durumunu oku ve drone'a RC komutu gönder. Her ~100ms çağrılır."""
        pygame.event.pump()

        # ── Yatay hareket ────────────────────────────────────────────────────
        lr = int(self._deadzone(self.joystick.get_axis(0)) * Config.DRONE_SPEED)
        fb = int(-self._deadzone(self.joystick.get_axis(1)) * Config.DRONE_SPEED)

        # ── Yaw (L1/R1) ──────────────────────────────────────────────────────
        yaw = 0
        if self.joystick.get_button(9):   # L1
            yaw = -self.YAW_SPEED
        elif self.joystick.get_button(10): # R1
            yaw = self.YAW_SPEED

        # ── Yükseklik (L2/R2 analog) ─────────────────────────────────────────
        l2 = (self.joystick.get_axis(4) + 1) / 2  # [–1,1] → [0,1]
        r2 = (self.joystick.get_axis(5) + 1) / 2

        ud = 0
        if r2 > Config.GAMEPAD_TRIGGER_THRESHOLD:
            ud = int(r2 * Config.DRONE_SPEED)
        elif l2 > Config.GAMEPAD_TRIGGER_THRESHOLD:
            ud = -int(l2 * Config.DRONE_SPEED)

        if abs(ud) < Config.GAMEPAD_UD_MIN:
            ud = 0

        self.drone.set_movement(lr, fb, ud, yaw)

        # ── Takeoff / Land ───────────────────────────────────────────────────
        if self.joystick.get_button(0) and not self._flying:  # X
            self.drone.takeoff()
            self._flying = True

        if self.joystick.get_button(1) and self._flying:      # O
            self.drone.land()
            self._flying = False
