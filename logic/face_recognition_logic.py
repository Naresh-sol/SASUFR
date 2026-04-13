"""
Face Recognition Module using FaceNet (facenet-pytorch)

This module provides face detection and recognition capabilities using:
- MTCNN for face detection
- InceptionResnetV1 (FaceNet) for generating 512-dimensional face embeddings

Used during attendance taking to recognize students against stored embeddings.
"""

import torch
import numpy as np
from PIL import Image
from facenet_pytorch import MTCNN, InceptionResnetV1


# ── Configuration ──
FACE_RECOGNITION_THRESHOLD = 0.6   # Euclidean distance threshold for matching
FACE_ENCODING_SIZE = 512           # InceptionResnetV1 embedding dimension


class FaceRecognizer:
    """
    Face Recognition class using FaceNet architecture.
    
    Key Features:
    - Uses MTCNN for accurate face detection
    - Uses InceptionResnetV1 pretrained on VGGFace2 dataset
    - Generates 512-dimensional embeddings (digital biometric signatures)
    - Enables one-shot learning (recognize from single reference image)
    """
    
    _instance = None
    
    def __new__(cls):
        """Implement singleton pattern to avoid loading models multiple times."""
        if cls._instance is None:
            cls._instance = super(FaceRecognizer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize face detector and encoder (only once)"""
        if self._initialized:
            return
            
        # Select device (GPU if available, else CPU)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"FaceRecognizer using device: {self.device}")
        
        # Initialize MTCNN face detector
        self.mtcnn = MTCNN(
            image_size=160,
            margin=20,
            min_face_size=40,
            thresholds=[0.6, 0.7, 0.7],
            factor=0.709,
            post_process=True,
            keep_all=True,          # Detect multiple faces for attendance
            device=self.device
        )
        
        # Initialize FaceNet (InceptionResnetV1) for face embedding
        self.facenet = InceptionResnetV1(
            pretrained='vggface2',
            classify=False,
            num_classes=None
        ).eval().to(self.device)
        
        # Recognition threshold (Euclidean distance)
        self.threshold = FACE_RECOGNITION_THRESHOLD
        self._initialized = True
    
    def detect_faces(self, frame):
        """
        Detect faces in a frame using MTCNN.
        
        Args:
            frame: numpy array (BGR from OpenCV) or PIL Image
        
        Returns:
            boxes: List of bounding boxes [x1, y1, x2, y2]
            probs: Detection probabilities
            faces: Cropped and aligned face tensors
            landmarks: List of facial landmarks
        """
        # Convert BGR to RGB if numpy array
        if isinstance(frame, np.ndarray):
            frame = Image.fromarray(frame[:, :, ::-1])  # BGR to RGB
        
        # Detect faces with landmarks
        boxes, probs, landmarks = self.mtcnn.detect(frame, landmarks=True)
        
        if boxes is None:
            return [], [], [], []
        
        # Get aligned face tensors
        faces = self.mtcnn(frame)
        
        if faces is None:
            return [], [], [], []
        
        return boxes, probs, faces, landmarks
    
    def encode_face(self, face_tensor):
        """
        Generate 512-dimensional embedding for a face.
        
        Args:
            face_tensor: Preprocessed face tensor from MTCNN
        
        Returns:
            512-dimensional numpy array (face embedding)
        """
        with torch.no_grad():
            if face_tensor.dim() == 3:
                face_tensor = face_tensor.unsqueeze(0)
            
            face_tensor = face_tensor.to(self.device)
            embedding = self.facenet(face_tensor)
            embedding = embedding.cpu().numpy().flatten()
            
        return embedding
    
    def encode_faces(self, faces):
        """
        Generate embeddings for multiple faces.
        
        Args:
            faces: Tensor of aligned faces from MTCNN
        
        Returns:
            List of 512-dimensional embeddings
        """
        encodings = []
        
        if faces is None:
            return encodings
        
        with torch.no_grad():
            faces = faces.to(self.device)
            
            if faces.dim() == 3:
                faces = faces.unsqueeze(0)
            
            embeddings = self.facenet(faces)
            
            for emb in embeddings:
                encodings.append(emb.cpu().numpy().flatten())
        
        return encodings
    
    def calculate_distance(self, encoding1, encoding2):
        """
        Calculate Euclidean distance between two face embeddings.
        
        In FaceNet's embedding space:
        - Same person: distance < 0.6 (typically)
        - Different people: distance > 0.6
        """
        encoding1 = np.array(encoding1)
        encoding2 = np.array(encoding2)
        return np.linalg.norm(encoding1 - encoding2)
    
    def compare_faces(self, encoding1, encoding2):
        """
        Compare two face encodings and determine if they match.
        
        Returns:
            tuple: (is_match: bool, distance: float)
        """
        distance = self.calculate_distance(encoding1, encoding2)
        is_match = distance < self.threshold
        return is_match, distance
    
    def recognize_face(self, face_encoding, stored_encodings):
        """
        Recognize a face against a database of stored encodings.
        
        Args:
            face_encoding: Encoding of face to recognize (512-D)
            stored_encodings: List of dicts with 'encoding' and 'student_id'
        
        Returns:
            dict: Matched student info or None if no match
        """
        min_distance = float('inf')
        best_match = None
        
        for stored in stored_encodings:
            stored_encoding = stored['encoding']
            distance = self.calculate_distance(face_encoding, stored_encoding)
            
            if distance < min_distance and distance < self.threshold:
                min_distance = distance
                best_match = {
                    'student_id': stored['student_id'],
                    'student_name': stored.get('student_name', ''),
                    'distance': distance,
                    'confidence': 1 - (distance / self.threshold)
                }
        
        return best_match
    
    def encoding_to_bytes(self, encoding):
        """Convert numpy encoding to bytes for database storage"""
        return encoding.tobytes()
    
    def bytes_to_encoding(self, encoding_bytes):
        """Convert bytes from database to numpy encoding"""
        return np.frombuffer(encoding_bytes, dtype=np.float32)
    
    def get_embedding_size(self):
        """Return the embedding dimension (512 for InceptionResnetV1)"""
        return FACE_ENCODING_SIZE


if __name__ == "__main__":
    print("Initializing FaceRecognizer...")
    recognizer = FaceRecognizer()
    print(f"✓ FaceRecognizer initialized!")
    print(f"  - Embedding size: {recognizer.get_embedding_size()}")
    print(f"  - Threshold: {recognizer.threshold}")
