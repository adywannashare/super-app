from __future__ import division
import os
import cv2
import dlib
import sys
from .eye import Eye
from .calibration import Calibration


class GazeTracking(object):
    """
    This class tracks the user's gaze.
    It provides useful information like the position of the eyes
    and pupils and allows to know if the eyes are open or closed
    """

    def __init__(self):
        self.frame = None
        self.eye_left = None
        self.eye_right = None
        self.calibration = Calibration()

        # _face_detector is used to detect faces
        self._face_detector = dlib.get_frontal_face_detector()

        # _predictor is used to get facial landmarks of a given face
        self._load_predictor()

    def _load_predictor(self):
        """Load the facial landmark predictor model with comprehensive error handling"""
        cwd = os.path.abspath(os.path.dirname(__file__))
        model_dir = os.path.join(cwd, "trained_models")
        model_path = os.path.join(model_dir, "shape_predictor_68_face_landmarks.dat")
        
        # Check if model file exists
        if not os.path.exists(model_path):
            print(f"❌ Model file not found at: {model_path}")
            self._print_download_instructions(model_dir)
            sys.exit(1)
        
        # Check file size (should be around 95MB)
        file_size = os.path.getsize(model_path)
        expected_min_size = 90 * 1024 * 1024  # 90MB minimum
        
        if file_size < expected_min_size:
            print(f"❌ Model file seems corrupted (size: {file_size // 1024 // 1024}MB)")
            print("Expected size: ~95MB")
            print("Please re-download the model file.")
            self._print_download_instructions(model_dir)
            sys.exit(1)
        
        # Try to load the predictor
        try:
            print("Loading facial landmark predictor...")
            self._predictor = dlib.shape_predictor(model_path)
            print("✓ Facial landmark predictor loaded successfully!")
            
        except RuntimeError as e:
            error_msg = str(e).lower()
            print(f"❌ Error loading predictor model: {e}")
            
            if "deserializing" in error_msg or "corrupt" in error_msg:
                print("\nThis error usually means the model file is corrupted.")
                print("Please delete the existing file and re-download it.")
                print(f"Delete: {model_path}")
            elif "unable to open" in error_msg:
                print("\nThe model file path is incorrect or file doesn't exist.")
            
            self._print_download_instructions(model_dir)
            sys.exit(1)
            
        except Exception as e:
            print(f"❌ Unexpected error loading predictor: {e}")
            sys.exit(1)

    def _print_download_instructions(self, model_dir):
        """Print instructions for downloading the model file"""
        print("\n" + "="*60)
        print("DOWNLOAD INSTRUCTIONS:")
        print("="*60)
        print("1. Download the model file from:")
        print("   http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2")
        print()
        print("2. Extract the .bz2 file to get the .dat file")
        print()
        print("3. Place the .dat file in:")
        print(f"   {os.path.abspath(model_dir)}")
        print()
        print("4. The final file path should be:")
        print(f"   {os.path.abspath(os.path.join(model_dir, 'shape_predictor_68_face_landmarks.dat'))}")
        print()
        print("Alternative: Run the robust downloader script provided earlier.")
        print("="*60)

    @property
    def pupils_located(self):
        """Check that the pupils have been located"""
        try:
            int(self.eye_left.pupil.x)
            int(self.eye_left.pupil.y)
            int(self.eye_right.pupil.x)
            int(self.eye_right.pupil.y)
            return True
        except Exception:
            return False

    def _analyze(self):
        """Detects the face and initialize Eye objects"""
        frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        faces = self._face_detector(frame)

        try:
            landmarks = self._predictor(frame, faces[0])
            self.eye_left = Eye(frame, landmarks, 0, self.calibration)
            self.eye_right = Eye(frame, landmarks, 1, self.calibration)

        except IndexError:
            self.eye_left = None
            self.eye_right = None

    def refresh(self, frame):
        """Refreshes the frame and analyzes it.

        Arguments:
            frame (numpy.ndarray): The frame to analyze
        """
        self.frame = frame
        self._analyze()

    def pupil_left_coords(self):
        """Returns the coordinates of the left pupil"""
        if self.pupils_located:
            x = self.eye_left.origin[0] + self.eye_left.pupil.x
            y = self.eye_left.origin[1] + self.eye_left.pupil.y
            return (x, y)

    def pupil_right_coords(self):
        """Returns the coordinates of the right pupil"""
        if self.pupils_located:
            x = self.eye_right.origin[0] + self.eye_right.pupil.x
            y = self.eye_right.origin[1] + self.eye_right.pupil.y
            return (x, y)

    def horizontal_ratio(self):
        """Returns a number between 0.0 and 1.0 that indicates the
        horizontal direction of the gaze. The extreme right is 0.0,
        the center is 0.5 and the extreme left is 1.0
        """
        if self.pupils_located:
            pupil_left = self.eye_left.pupil.x / (self.eye_left.center[0] * 2 - 10)
            pupil_right = self.eye_right.pupil.x / (self.eye_right.center[0] * 2 - 10)
            return (pupil_left + pupil_right) / 2

    def vertical_ratio(self):
        """Returns a number between 0.0 and 1.0 that indicates the
        vertical direction of the gaze. The extreme top is 0.0,
        the center is 0.5 and the extreme bottom is 1.0
        """
        if self.pupils_located:
            pupil_left = self.eye_left.pupil.y / (self.eye_left.center[1] * 2 - 10)
            pupil_right = self.eye_right.pupil.y / (self.eye_right.center[1] * 2 - 10)
            return (pupil_left + pupil_right) / 2

    def is_right(self):
        """Returns true if the user is looking to the right"""
        if self.pupils_located:
            return self.horizontal_ratio() <= 0.35

    def is_left(self):
        """Returns true if the user is looking to the left"""
        if self.pupils_located:
            return self.horizontal_ratio() >= 0.65

    def is_center(self):
        """Returns true if the user is looking to the center"""
        if self.pupils_located:
            return self.is_right() is not True and self.is_left() is not True

    def is_blinking(self):
        """Returns true if the user closes his eyes"""
        if self.pupils_located:
            blinking_ratio = (self.eye_left.blinking + self.eye_right.blinking) / 2
            return blinking_ratio > 3.8

    def annotated_frame(self):
        """Returns the main frame with pupils highlighted"""
        frame = self.frame.copy()

        if self.pupils_located:
            color = (0, 255, 0)
            x_left, y_left = self.pupil_left_coords()
            x_right, y_right = self.pupil_right_coords()
            cv2.line(frame, (x_left - 5, y_left), (x_left + 5, y_left), color)
            cv2.line(frame, (x_left, y_left - 5), (x_left, y_left + 5), color)
            cv2.line(frame, (x_right - 5, y_right), (x_right + 5, y_right), color)
            cv2.line(frame, (x_right, y_right - 5), (x_right, y_right + 5), color)

        return frame