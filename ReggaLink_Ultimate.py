# ============================================
# ReggaLink ULTIMATE V3 by Reggadi
# 100% Original Code - No scrcpy
# Motherboard Only Mode Supported
# ============================================

import subprocess
import cv2
import numpy as np
import threading
import queue
import time
import os
from datetime import datetime
from tkinter import Tk, filedialog

class ReggaLinkUltimate:
    def __init__(self):
        self.frame_queue = queue.Queue(maxsize=2)
        self.running = True
        self.recording = False
        self.video_writer = None
        self.phone_w, self.phone_h = 720, 1600
        
        try:
            out = subprocess.check_output(["adb", "shell", "wm", "size"], timeout=3).decode()
            size = out.split(":")[1].strip().split("x")
            self.phone_w, self.phone_h = int(size[0]), int(size[1])
        except:
            pass

        self.display_w, self.display_h = 360, 800

        print(f"""
╔════════════════════════════════════════╗
║  ReggaLink ULTIMATE V3 - by Reggadi    ║
║  Phone: {self.phone_w}x{self.phone_h} | PC: {self.display_w}x{self.display_h}    ║
║  MODE: Motherboard + Battery ONLY OK   ║
╠════════════════════════════════════════╣
║  CONTROLS:                             ║
║  Mouse Click/Drag = Touch phone        ║
║  Type = Write to phone                 ║
║  [R] = Start/Stop Recording            ║
║  [F] = Push File to phone              ║
║  [S] = Screenshot                      ║
║  [ESC] = Quit                          ║
╚════════════════════════════════════════╝
        """)

    # ========== VIDEO STREAM ==========
    def video_thread(self):
        print("[ReggaLink] Starting H264 stream...")
        cmd = ["adb", "exec-out", "screenrecord --output-format=h264 --size 720x1280 --bit-rate 4000000 --time-limit 179 -"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        # Try ffmpeg for 30FPS
        try:
            ffmpeg_cmd = ["ffmpeg", "-i", "pipe:0", "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1", "-loglevel", "quiet"]
            ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            
            while self.running:
                raw = ffmpeg_proc.stdout.read(720*1280*3)
                if not raw or len(raw) < 720*1280*3:
                    break
                frame = np.frombuffer(raw, dtype=np.uint8).reshape((1280, 720, 3))
                if self.frame_queue.full():
                    try: self.frame_queue.get_nowait()
                    except: pass
                self.frame_queue.put(frame)
                
        except FileNotFoundError:
            print("[ReggaLink] FFmpeg not found, using fast PNG mode (10-15 FPS)")
            print("-> For 30FPS, put ffmpeg.exe next to adb.exe")
            self.fallback_thread()

    def fallback_thread(self):
        while self.running:
            try:
                proc = subprocess.Popen(["adb", "exec-out", "screencap -p"], stdout=subprocess.PIPE)
                data, _ = proc.communicate(timeout=2)
                if data:
                    frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        if self.frame_queue.full(): self.frame_queue.get_nowait()
                        self.frame_queue.put(frame)
            except:
                time.sleep(0.05)

    # ========== CONTROLS ==========
    def send_tap(self, x, y):
        rx = int(x * self.phone_w / self.display_w)
        ry = int(y * self.phone_h / self.display_h)
        subprocess.Popen(["adb", "shell", f"input tap {rx} {ry}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def send_swipe(self, x1, y1, x2, y2):
        rx1, ry1 = int(x1*self.phone_w/self.display_w), int(y1*self.phone_h/self.display_h)
        rx2, ry2 = int(x2*self.phone_w/self.display_w), int(y2*self.phone_h/self.display_h)
        subprocess.Popen(["adb", "shell", f"input swipe {rx1} {ry1} {rx2} {ry2} 200"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def send_text(self, text):
        # كيحول النص باش ما يطراش مشكل مع المسافات
        safe = text.replace(" ", "%s").replace("'", "").replace('"', '')
        subprocess.Popen(["adb", "shell", f"input text {safe}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def send_keyevent(self, code):
        subprocess.Popen(["adb", "shell", f"input keyevent {code}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ========== FEATURES ==========
    def take_screenshot(self, frame):
        name = f"ReggaLink_Screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        cv2.imwrite(name, frame)
        print(f"[ReggaLink] Screenshot saved: {name}")

    def toggle_recording(self, frame):
        if not self.recording:
            name = f"ReggaLink_Record_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            self.video_writer = cv2.VideoWriter(name, cv2.VideoWriter_fourcc(*'mp4v'), 15, (self.display_w, self.display_h))
            self.recording = True
            print(f"[ReggaLink] RECORDING STARTED: {name}")
        else:
            self.recording = False
            if self.video_writer:
                self.video_writer.release()
            print("[ReggaLink] Recording stopped")

    def push_file(self):
        print("[ReggaLink] Select file to push...")
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_path = filedialog.askopenfilename()
        root.destroy()
        if file_path:
            filename = os.path.basename(file_path)
            print(f"[ReggaLink] Pushing {filename} to /sdcard/Download/")
            subprocess.run(["adb", "push", file_path, f"/sdcard/Download/{filename}"])
            print("[ReggaLink] File pushed!")

    # ========== MAIN LOOP ==========
    def run(self):
        threading.Thread(target=self.video_thread, daemon=True).start()

        window = "ReggaLink ULTIMATE V3 - by Reggadi | [R]Record [F]File [S]Shot [ESC]Exit"
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window, self.display_w, self.display_h)

        is_dragging = [False]
        start = [0,0]

        def mouse_cb(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                is_dragging[0] = True
                start[0], start[1] = x, y
            elif event == cv2.EVENT_LBUTTONUP:
                if is_dragging[0]:
                    dx = abs(x-start[0])
                    dy = abs(y-start[1])
                    if dx > 15 or dy > 15:
                        self.send_swipe(start[0], start[1], x, y)
                    else:
                        self.send_tap(x, y)
                is_dragging[0] = False

        cv2.setMouseCallback(window, mouse_cb)

        last_frame = np.zeros((1280, 720, 3), dtype=np.uint8)
        typed_buffer = ""

        while self.running:
            try:
                frame = self.frame_queue.get(timeout=1)
                last_frame = frame
            except:
                frame = last_frame

            if frame is None:
                continue

            display = cv2.resize(frame, (self.display_w, self.display_h))

            # Overlay status
            if self.recording:
                cv2.circle(display, (20, 20), 8, (0,0,255), -1)
                cv2.putText(display, "REC", (35,25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
                if self.video_writer:
                    self.video_writer.write(display)

            cv2.putText(display, "ReggaLink | Reggadi", (10, self.display_h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,136), 1)

            cv2.imshow(window, display)

            key = cv2.waitKey(1) & 0xFF
            
            if key == 27: # ESC
                break
            elif key == ord('r') or key == ord('R'):
                self.toggle_recording(frame)
            elif key == ord('s') or key == ord('S'):
                self.take_screenshot(frame)
            elif key == ord('f') or key == ord('F'):
                threading.Thread(target=self.push_file, daemon=True).start()
            elif key == 8: # Backspace
                self.send_keyevent(67)
            elif key == 13: # Enter
                self.send_keyevent(66)
            elif key != 255 and key > 31:
                # كتابة مباشرة
                try:
                    char = chr(key)
                    self.send_text(char)
                except:
                    pass

        self.running = False
        if self.video_writer:
            self.video_writer.release()
        cv2.destroyAllWindows()
        subprocess.run(["adb", "shell", "pkill screenrecord"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[ReggaLink ULTIMATE] Closed")

if __name__ == "__main__":
    app = ReggaLinkUltimate()
    app.run()