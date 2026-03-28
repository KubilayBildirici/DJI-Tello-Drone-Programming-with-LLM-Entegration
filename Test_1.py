import pygame
import time

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("Gamepad bulunamadi!")
    exit()

joystick = pygame.joystick.Joystick(0)
joystick.init()

print("Gamepad:", joystick.get_name())
print("Axis sayisi:", joystick.get_numaxes())
print("Button sayisi:", joystick.get_numbuttons())

print("\n--- DEBUG BASLADI ---\n")

while True:
    pygame.event.pump()

    # 🎮 AXIS
    for i in range(joystick.get_numaxes()):
        val = joystick.get_axis(i)
        print(f"Axis {i}: {val:.2f}", end=" | ")

    print()

    # 🎮 BUTTON
    for i in range(joystick.get_numbuttons()):
        if joystick.get_button(i):
            print(f"Button pressed: {i}")

    time.sleep(0.2)
