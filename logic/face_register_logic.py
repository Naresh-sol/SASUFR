import cv2
import numpy as np
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
from db_config import verify_student_exists, authenticate_student, save_face_embedding


class FaceRegisterLogic:

    def __init__(self):
        # ── Initialize face detection and embedding models ──
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # MTCNN: detects faces in images and crops them to 160×160
        self.mtcnn = MTCNN(
            image_size=160,       # Output face size (FaceNet expects 160×160)
            keep_all=False,       # Only return the most prominent face
            device=self.device
        )

        # InceptionResnetV1: converts a face image into a 512-d embedding vector
        self.facenet = InceptionResnetV1(
            pretrained='vggface2'  # Pre-trained on VGGFace2 dataset
        ).eval().to(self.device)
        # .eval() = inference mode (no training)
        # .to(device) = run on GPU if available, else CPU

        # Camera state
        self.camera = None  # Will hold cv2.VideoCapture object

    # STUDENT VERIFICATION
    def verify_student(self, student_id):
        
        return verify_student_exists(student_id)

    # STUDENT AUTHENTICATION (ID + PASSWORD)
    def authenticate_student(self, student_id, password):
        """Authenticate student with ID and password."""
        return authenticate_student(student_id, password)


    # CAMERA OPERATIONS

    def start_camera(self, camera_index=0):
        
        if self.camera is None or not self.camera.isOpened():
            self.camera = cv2.VideoCapture(camera_index)
        return self.camera.isOpened()

    def read_frame(self):
        
        if self.camera is None or not self.camera.isOpened():
            return False, None
        return self.camera.read()

    def stop_camera(self):
        """Release the webcam resource."""
        if self.camera is not None and self.camera.isOpened():
            self.camera.release()
            self.camera = None


    # FACE DETECTION & EMBEDDING

    def detect_faces(self, frame_bgr):
       
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        boxes, _ = self.mtcnn.detect(frame_rgb)

        if boxes is None:
            return []

        # Convert float coords to int for drawing
        return [list(map(int, box)) for box in boxes]

    def detect_and_embed(self, frame_bgr):
        
        # Step 1: Convert BGR → RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # Step 2: Detect face using MTCNN
        # Returns a tensor of shape (3, 160, 160) or None
        face_tensor = self.mtcnn(frame_rgb)

        if face_tensor is None:
            return None  # No face detected

        # Step 3: Generate embedding using FaceNet
        # Add batch dimension: (3, 160, 160) → (1, 3, 160, 160)
        face_tensor = face_tensor.unsqueeze(0).to(self.device)

        with torch.no_grad():
            embedding = self.facenet(face_tensor)
        # embedding shape: (1, 512)

        # Step 4: Convert to bytes
        embedding_numpy = embedding.cpu().numpy()
        embedding_bytes = embedding_numpy.tobytes()

        return embedding_bytes

    def register_face(self, student_id, frame_bgr):
        
        # Detect face and generate embedding
        embedding_bytes = self.detect_and_embed(frame_bgr)

        if embedding_bytes is None:
            return False, (
                "Could not detect a face in the frame.\n"
                "Please ensure your face is clearly visible and try again."
            )

        # Save to database
        success = save_face_embedding(student_id, embedding_bytes)

        if success:
            return True, f"Face registered/updated successfully for Student ID: {student_id}!"
        else:
            return False, "Failed to save face embedding to database."
