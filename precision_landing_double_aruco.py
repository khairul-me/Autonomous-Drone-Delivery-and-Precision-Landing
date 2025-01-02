# =================================================================
# Precision Landing System Using Double ArUco Markers
# =================================================================
# Author: Md Khairul Islam
# Institution: Hobart and William Smith Colleges, Geneva, NY
# Major: Robotics and Computer Science
# Contact: khairul.islam@hws.edu
# =================================================================
"""
This program implements an advanced precision landing system using two ArUco markers
of different sizes. The system switches between markers based on altitude to maintain
optimal tracking throughout the landing sequence.

Key Features:
- Dual ArUco marker detection
- Automatic marker switching based on altitude
- Dynamic marker size adjustment
- Enhanced landing accuracy through marker fusion
- Real-time performance monitoring
"""

import time
import math
import argparse
from typing import Tuple, Optional, List, Dict

import cv2
import cv2.aruco as aruco
import numpy as np
from imutils.video import WebcamVideoStream
import imutils

from dronekit import connect, VehicleMode, LocationGlobalRelative, APIException
from pymavlink import mavutil

class DualMarkerLandingSystem:
    def __init__(self):
        """Initialize the dual marker precision landing system"""
        # Marker configurations
        self.marker_configs = {
            'high_altitude': {
                'id': 129,
                'size': 40,  # cm
                'height_threshold': 7  # meters
            },
            'low_altitude': {
                'id': 72,
                'size': 19,  # cm
                'height_threshold': 4  # meters
            }
        }
        
        self.takeoff_height = 10  # meters
        self.velocity = 0.5      # m/s

        # Camera configuration
        self.camera_config = {
            'resolution': (640, 480),
            'horizontal_fov': 62.2 * (math.pi / 180),  # Pi cam V2
            'vertical_fov': 48.8 * (math.pi / 180)     # Pi cam V2
        }

        # Initialize ArUco detection
        self.aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_ARUCO_ORIGINAL)
        self.parameters = aruco.DetectorParameters_create()

        # Initialize camera
        self.cap = WebcamVideoStream(
            src=0,
            width=self.camera_config['resolution'][0],
            height=self.camera_config['resolution'][1]
        ).start()

        # Load camera calibration
        self._load_camera_calibration()

        # Performance metrics
        self.metrics = {
            'found_count': 0,
            'notfound_count': 0,
            'first_run': True,
            'start_time': 0
        }

        # Connect to drone
        self.vehicle = self._connect_vehicle()
        self._configure_precision_landing()

    def _load_camera_calibration(self):
        """Load camera calibration parameters from files"""
        try:
            calib_path = "/home/pi/video2calibration/calibrationFiles/"
            self.camera_matrix = np.loadtxt(calib_path + 'cameraMatrix.txt', delimiter=',')
            self.camera_distortion = np.loadtxt(calib_path + 'cameraDistortion.txt', delimiter=',')
        except Exception as e:
            raise Exception(f"Failed to load camera calibration files: {str(e)}")

    def _connect_vehicle(self):
        """Establish connection with the drone"""
        parser = argparse.ArgumentParser(description='Dual Marker Precision Landing')
        parser.add_argument('--connect', 
                          default='127.0.0.1:14550',
                          help='Vehicle connection target string')
        args = parser.parse_args()
        
        return connect(args.connect, wait_ready=True)

    def _configure_precision_landing(self):
        """Configure drone parameters for precision landing"""
        self.vehicle.parameters['PLND_ENABLED'] = 1
        self.vehicle.parameters['PLND_TYPE'] = 1
        self.vehicle.parameters['PLND_EST_TYPE'] = 0
        self.vehicle.parameters['LAND_SPEED'] = 20

    def get_active_marker_config(self) -> Dict:
        """
        Determine which marker to track based on current altitude
        
        Returns:
            dict: Active marker configuration
        """
        altitude = self.vehicle.location.global_relative_frame.alt
        
        if altitude > self.marker_configs['low_altitude']['height_threshold']:
            return self.marker_configs['high_altitude']
        return self.marker_configs['low_altitude']

    def detect_marker(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Detect the appropriate ArUco marker based on current altitude
        
        Returns:
            tuple: (x_angle, y_angle, distance) or (None, None, None) if not detected
        """
        frame = self.cap.read()
        frame = cv2.resize(frame, self.camera_config['resolution'])
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        corners, ids, _ = aruco
