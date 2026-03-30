import cv2
import mediapipe as mp
import time
import os
import random
import numpy as np
import pygame

# ====================== MEDIA PIPE ======================
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

model_path = "hand_landmarker.task"
if not os.path.exists(model_path):
    print("❌ hand_landmarker.task not found! Download and place in folder.")
    exit()

options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.IMAGE,
    num_hands=1
)

# ====================== SOUND (optional) ======================
pygame.mixer.init()
sounds = {}
if os.path.exists("sounds"):
    for name in ["rasengan", "chidori", "shadow_clone", "fireball"]:
        path = f"sounds/{name}.mp3"
        if os.path.exists(path):
            sounds[name] = pygame.mixer.Sound(path)

# ====================== PARTICLES ======================
class Particle:
    def __init__(self, x, y, color, jutsu_type="normal"):
        self.x = x + random.uniform(-25, 25)
        self.y = y + random.uniform(-25, 25)
        self.vx = random.uniform(-8, 8)
        self.vy = random.uniform(-8, 8)
        self.life = random.randint(35, 70)
        self.color = color
        self.size = random.randint(5, 11)
        self.jutsu_type = jutsu_type

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.jutsu_type == "rasengan":
            self.vx *= 0.95
            self.vy *= 0.95
        else:
            self.vy += 0.14
        self.life -= 1
        self.size = max(3, int(self.life / 10))

    def draw(self, frame):
        if self.life > 0:
            cv2.circle(frame, (int(self.x), int(self.y)), self.size, self.color, -1)

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, count, base_color, jutsu_type="normal"):
        for _ in range(count):
            if jutsu_type == "rasengan":
                c = (random.randint(160, 255), random.randint(220, 255), 255)
            elif jutsu_type == "chidori":
                c = (255, random.randint(180, 255), random.randint(200, 255))
            elif jutsu_type == "fire":
                c = (0, random.randint(90, 255), random.randint(170, 255))
            else:  # shadow
                c = (random.randint(210, 255), random.randint(230, 255), 100)
            self.particles.append(Particle(x, y, c, jutsu_type))

    def update_and_draw(self, frame):
        for p in self.particles[:]:
            p.update()
            p.draw(frame)
            if p.life <= 0:
                self.particles.remove(p)

# ====================== VISUAL EFFECTS ======================
def draw_chidori_lightning(frame, cx, cy, intensity=15):
    for _ in range(intensity):
        x, y = cx, cy
        pts = [(int(x), int(y))]
        for _ in range(11):
            x += random.uniform(-30, 30)
            y += random.uniform(-40, 15)
            pts.append((int(x), int(y)))
        cv2.polylines(frame, [np.array(pts, dtype=np.int32)], False, (200, 230, 255), 7)
        cv2.polylines(frame, [np.array(pts, dtype=np.int32)], False, (255, 255, 255), 2)

def draw_shadow_clones(frame, cx, cy):
    for i in range(4):
        ox = (i-1.5)*85 + random.randint(-20,20)
        oy = random.randint(-40,40)
        cv2.circle(frame, (int(cx+ox), int(cy+oy)), 35, (160, 255, 140), 9)
        cv2.circle(frame, (int(cx+ox), int(cy+oy)), 18, (240, 255, 200), 5)

# ====================== GESTURE DETECTION ======================
def get_gesture(landmarks):
    if not landmarks:
        return "none"
    
    tips = [8, 12, 16, 20]
    finger_count = 0
    for tip in tips:
        if landmarks[tip].y < landmarks[tip-2].y:
            finger_count += 1
    
    # Thumb
    if abs(landmarks[4].x - landmarks[3].x) > 0.04:
        finger_count += 1

    # Special gestures
    if finger_count >= 5:
        return "open"
    if finger_count <= 1:
        return "fist"
    if finger_count == 1:           # pointing
        return "point"
    if finger_count == 2:
        # Check if index + middle are close (Ram/Tiger like)
        if abs(landmarks[8].x - landmarks[12].x) < 0.08 and abs(landmarks[8].y - landmarks[12].y) < 0.1:
            return "ram"          # better for Shadow Clone
        return "two"
    
    return "none"

# ====================== COMBOS (No repeated same gesture) ======================
JUTSU_COMBOS = {
    "shadow": {
        "seq": ["open", "ram"],
        "name": "SHADOW CLONE JUTSU!!!",
        "color": (0, 255, 255),
        "type": "shadow"
    },
    "rasengan": {
        "seq": ["fist", "open"],
        "name": "RASENGAN!!!",
        "color": (80, 200, 255),
        "type": "rasengan"
    },
    "fire": {
        "seq": ["point", "ram"],
        "name": "FIRE STYLE: FIREBALL JUTSU!!!",
        "color": (0, 80, 255),
        "type": "fire"
    },
    "chidori": {
        "seq": ["open", "fist", "two"],
        "name": "CHIDORI!!!",
        "color": (180, 80, 255),
        "type": "chidori"
    }
}

# ====================== INSTRUCTION TAB ======================
def draw_instruction_tab(frame, combo_sequence):
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (540, 320), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.68, frame, 0.32, 0, frame)

    cv2.putText(frame, "NARUTO JUTSU COMBO GUIDE", (25, 40), 
                cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 255, 255), 2)

    inst = [
        "Shadow Clone   : Open Hand → Ram Seal (Index+Middle together)",
        "Rasengan       : Fist → Open Palm",
        "Fireball       : Pointing → Ram Seal",
        "Chidori        : Open → Fist → Two Fingers"
    ]

    for i, line in enumerate(inst):
        color = (0, 255, 200) if "Chidori" in line else (210, 210, 210)
        cv2.putText(frame, line, (25, 78 + i*33), cv2.FONT_HERSHEY_SIMPLEX, 0.73, color, 2)

    if combo_sequence:
        cv2.putText(frame, f"Current: {' → '.join(combo_sequence)}", (25, 290), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 100), 2)

# ====================== MAIN ======================
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

particle_system = ParticleSystem()

print("✅ Improved Combo System Started (No repeated gestures)!")
print("Perform the exact sequence shown in the top-left box.")
print("Press 'q' to quit\n")

with HandLandmarker.create_from_options(options) as landmarker:
    jutsu_text = ""
    jutsu_color = (255, 255, 255)
    display_until = 0
    shake = 0

    combo_sequence = []
    last_gesture = "none"
    last_time = 0
    combo_timeout = 0

    prev_time = time.time()
    hand_cx = hand_cy = 640, 360

    while True:
        ret, frame = cap.read()
        if not ret: break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = landmarker.detect(mp_image)
        now = time.time()

        if now > combo_timeout and combo_sequence:
            combo_sequence = []

        if result.hand_landmarks:
            for landmarks in result.hand_landmarks:
                h, w = frame.shape[:2]
                hand_cx = int(sum(lm.x for lm in landmarks) / len(landmarks) * w)
                hand_cy = int(sum(lm.y for lm in landmarks) / len(landmarks) * h)

                # Draw landmarks
                for lm in landmarks:
                    cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 6, (0, 255, 255), -1)

                current_gesture = get_gesture(landmarks)

                # Add to combo only when gesture changes
                if current_gesture != "none" and current_gesture != last_gesture and now - last_time > 0.4:
                    combo_sequence.append(current_gesture)
                    last_gesture = current_gesture
                    last_time = now
                    combo_timeout = now + 3.5

                    if len(combo_sequence) > 4:
                        combo_sequence.pop(0)

                    # Check combos
                    for key, data in JUTSU_COMBOS.items():
                        req = data["seq"]
                        if len(combo_sequence) >= len(req) and combo_sequence[-len(req):] == req:
                            jutsu_text = data["name"]
                            jutsu_color = data["color"]
                            display_until = now + 3.6
                            shake = 25 if key == "chidori" else 16

                            particle_system.emit(hand_cx, hand_cy, 95 if key=="chidori" else 78, jutsu_color, data["type"])

                            if key == "chidori":
                                draw_chidori_lightning(frame, hand_cx, hand_cy, 18)
                            elif key == "shadow":
                                draw_shadow_clones(frame, hand_cx, hand_cy)
                            # Rasengan big ball drawn below

                            if sounds.get(key if key != "shadow" else "shadow_clone"):
                                sounds.get(key if key != "shadow" else "shadow_clone").play()

                            combo_sequence = []
                            break

        # Update particles
        particle_system.update_and_draw(frame)

        # Rasengan Big Blue Ball
        if jutsu_text == "RASENGAN!!!" and now < display_until:
            r = 45 + int(15 * np.sin(now * 16))
            cv2.circle(frame, (hand_cx, hand_cy), r+20, (100, 220, 255), 18)
            cv2.circle(frame, (hand_cx, hand_cy), r, (70, 190, 255), 24)
            cv2.circle(frame, (hand_cx, hand_cy), r-18, (220, 255, 255), -1)

        # Shadow Clone aura
        if jutsu_text == "SHADOW CLONE JUTSU!!!" and now < display_until:
            draw_shadow_clones(frame, hand_cx, hand_cy)

        # Chidori lightning
        if jutsu_text == "CHIDORI!!!" and now < display_until:
            draw_chidori_lightning(frame, hand_cx, hand_cy, 16)

        # Screen shake
        sx = sy = 0
        if shake > 0:
            sx = random.randint(-shake, shake)
            sy = random.randint(-shake, shake)
            shake -= 1

        # Big Text
        if jutsu_text and now < display_until:
            tx = 50 + sx
            ty = 150 + sy
            cv2.putText(frame, jutsu_text, (tx, ty), cv2.FONT_HERSHEY_TRIPLEX, 2.6, (0,0,0), 16)
            cv2.putText(frame, jutsu_text, (tx, ty), cv2.FONT_HERSHEY_TRIPLEX, 2.6, jutsu_color, 7)

        draw_instruction_tab(frame, combo_sequence)

        fps = int(1 / (now - prev_time + 1e-6))
        prev_time = now
        cv2.putText(frame, f"FPS: {fps}", (1080, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("Naruto Jutsu - Improved Combos", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
pygame.mixer.quit()