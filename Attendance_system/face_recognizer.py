import cv2
import numpy as np
import os
import pickle
import face_recognition as fr
from PIL import Image
import time

class FaceRecognizer:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_ids = []
        self.known_face_names = []
        self.model_path = "trained_model.pkl"
        self.encoding_quality_threshold = 0.6  # Threshold for face matching
        
    def train_from_dataset(self, dataset_path="dataset"):
        """
        Train the face recognition model from images in dataset folder
        Args:
            dataset_path: Path to folder containing student folders with images
        Returns:
            Number of faces successfully encoded
        """
        print("=" * 50)
        print("Starting face recognition training...")
        print("=" * 50)
        
        # Clear previous data
        self.known_face_encodings = []
        self.known_face_ids = []
        self.known_face_names = []
        
        # Check if dataset exists
        if not os.path.exists(dataset_path):
            print(f"ERROR: Dataset path '{dataset_path}' does not exist!")
            return 0
        
        # Get all student folders
        student_folders = [f for f in os.listdir(dataset_path) 
                          if os.path.isdir(os.path.join(dataset_path, f))]
        
        if not student_folders:
            print("No student folders found in dataset!")
            return 0
        
        print(f"Found {len(student_folders)} students in dataset")
        
        total_encodings = 0
        students_with_faces = 0
        
        # Process each student folder
        for student_id in student_folders:
            student_path = os.path.join(dataset_path, student_id)
            student_name = f"Student_{student_id}"  # Default name, can be updated from DB
            
            # Get all images in student folder
            image_files = [f for f in os.listdir(student_path) 
                          if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            
            if not image_files:
                print(f"  ⚠️  Student {student_id}: No images found")
                continue
            
            print(f"\n  Processing Student ID: {student_id}")
            print(f"  Found {len(image_files)} images")
            
            student_encodings = 0
            
            # Process each image
            for i, img_file in enumerate(image_files, 1):
                img_path = os.path.join(student_path, img_file)
                
                try:
                    # Load image using face_recognition library
                    image = fr.load_image_file(img_path)
                    
                    # Detect faces in the image
                    face_locations = fr.face_locations(image)
                    
                    if len(face_locations) == 0:
                        print(f"    ❌ Image {i}: No face detected")
                        continue
                    
                    # Get face encodings
                    face_encodings = fr.face_encodings(image, face_locations)
                    
                    if len(face_encodings) > 0:
                        # Take the first face (should be the only one)
                        face_encoding = face_encodings[0]
                        
                        # Store encoding
                        self.known_face_encodings.append(face_encoding)
                        self.known_face_ids.append(int(student_id))
                        self.known_face_names.append(student_name)
                        
                        student_encodings += 1
                        print(f"    ✅ Image {i}: Face encoded successfully")
                    else:
                        print(f"    ❌ Image {i}: Could not encode face")
                        
                except Exception as e:
                    print(f"    ❌ Image {i}: Error - {str(e)}")
            
            if student_encodings > 0:
                students_with_faces += 1
                total_encodings += student_encodings
                print(f"  ✅ Student {student_id}: {student_encodings} faces encoded")
            else:
                print(f"  ❌ Student {student_id}: No faces could be encoded")
        
        print("\n" + "=" * 50)
        print(f"TRAINING COMPLETE:")
        print(f"  • Students processed: {students_with_faces}/{len(student_folders)}")
        print(f"  • Total face encodings: {total_encodings}")
        print(f"  • Average per student: {total_encodings/max(students_with_faces, 1):.1f}")
        print("=" * 50)
        
        return total_encodings
    
    def recognize_faces(self, frame):
        """
        Recognize faces in a video frame
        Args:
            frame: BGR image from OpenCV
        Returns:
            List of student IDs that were recognized
        """
        if len(self.known_face_encodings) == 0:
            print("WARNING: No trained faces to recognize!")
            return []
        
        # Convert BGR to RGB (face_recognition uses RGB)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Find all faces in the frame
        face_locations = fr.face_locations(rgb_frame)
        
        if len(face_locations) == 0:
            return []  # No faces found
        
        # Get face encodings for all detected faces
        face_encodings = fr.face_encodings(rgb_frame, face_locations)
        
        recognized_students = []
        
        for face_encoding in face_encodings:
            # Compare with known faces
            matches = fr.compare_faces(self.known_face_encodings, face_encoding, 
                                      tolerance=self.encoding_quality_threshold)
            
            # Calculate face distances
            face_distances = fr.face_distance(self.known_face_encodings, face_encoding)
            
            if True in matches:
                # Find the best match (lowest distance)
                best_match_index = np.argmin(face_distances)
                
                # Check if the match is good enough
                if face_distances[best_match_index] <= self.encoding_quality_threshold:
                    student_id = self.known_face_ids[best_match_index]
                    recognized_students.append(student_id)
                    
                    # Optional: Draw on frame for debugging
                    # top, right, bottom, left = face_locations[0]
                    # cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        
        # Remove duplicates (same student might be recognized in multiple faces)
        return list(set(recognized_students))
    
    def recognize_from_image_file(self, image_path):
        """
        Recognize faces in an image file
        Args:
            image_path: Path to image file
        Returns:
            List of student IDs recognized
        """
        try:
            image = fr.load_image_file(image_path)
            face_locations = fr.face_locations(image)
            face_encodings = fr.face_encodings(image, face_locations)
            
            recognized = []
            for face_encoding in face_encodings:
                matches = fr.compare_faces(self.known_face_encodings, face_encoding)
                if True in matches:
                    face_distances = fr.face_distance(self.known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    recognized.append(self.known_face_ids[best_match_index])
            
            return list(set(recognized))
        except Exception as e:
            print(f"Error recognizing from file: {e}")
            return []
    
    def save_model(self, filepath=None):
        """
        Save the trained model to a file
        Args:
            filepath: Path to save the model (optional)
        """
        if filepath:
            self.model_path = filepath
            
        data = {
            'encodings': self.known_face_encodings,
            'ids': self.known_face_ids,
            'names': self.known_face_names,
            'timestamp': time.time()
        }
        
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump(data, f)
            print(f"Model saved successfully to {self.model_path}")
            print(f"  • Encodings: {len(self.known_face_encodings)}")
            print(f"  • Unique students: {len(set(self.known_face_ids))}")
            return True
        except Exception as e:
            print(f"Error saving model: {e}")
            return False
    
    def load_model(self, filepath=None):
        """
        Load a trained model from file
        Args:
            filepath: Path to load the model from (optional)
        Returns:
            Boolean indicating success
        """
        if filepath:
            self.model_path = filepath
            
        if not os.path.exists(self.model_path):
            print(f"Model file {self.model_path} not found!")
            return False
        
        try:
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)
                
            self.known_face_encodings = data['encodings']
            self.known_face_ids = data['ids']
            self.known_face_names = data.get('names', [f"Student_{id}" for id in self.known_face_ids])
            
            print(f"Model loaded successfully from {self.model_path}")
            print(f"  • Encodings: {len(self.known_face_encodings)}")
            print(f"  • Unique students: {len(set(self.known_face_ids))}")
            print(f"  • Model timestamp: {time.ctime(data.get('timestamp', 0))}")
            return True
            
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def get_model_stats(self):
        """
        Get statistics about the trained model
        Returns:
            Dictionary with model statistics
        """
        unique_students = len(set(self.known_face_ids))
        encodings_per_student = {}
        
        for student_id in self.known_face_ids:
            encodings_per_student[student_id] = encodings_per_student.get(student_id, 0) + 1
        
        return {
            'total_encodings': len(self.known_face_encodings),
            'unique_students': unique_students,
            'encodings_per_student': encodings_per_student,
            'avg_encodings_per_student': len(self.known_face_encodings) / max(unique_students, 1)
        }
    
    def add_face_from_image(self, image_path, student_id, student_name=None):
        """
        Add a single face to the model from an image file
        Args:
            image_path: Path to image file
            student_id: Student ID
            student_name: Student name (optional)
        Returns:
            Boolean indicating success
        """
        try:
            image = fr.load_image_file(image_path)
            face_locations = fr.face_locations(image)
            
            if len(face_locations) == 0:
                print(f"No face detected in {image_path}")
                return False
            
            face_encodings = fr.face_encodings(image, face_locations)
            
            if len(face_encodings) > 0:
                self.known_face_encodings.append(face_encodings[0])
                self.known_face_ids.append(student_id)
                self.known_face_names.append(student_name or f"Student_{student_id}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error adding face: {e}")
            return False
    
    def verify_face_quality(self, image_path):
        """
        Verify if an image contains a good quality face for training
        Args:
            image_path: Path to image file
        Returns:
            Dictionary with quality metrics
        """
        try:
            image = fr.load_image_file(image_path)
            face_locations = fr.face_locations(image)
            
            if len(face_locations) == 0:
                return {'valid': False, 'reason': 'No face detected'}
            
            if len(face_locations) > 1:
                return {'valid': False, 'reason': 'Multiple faces detected'}
            
            face_encodings = fr.face_encodings(image, face_locations)
            
            if len(face_encodings) == 0:
                return {'valid': False, 'reason': 'Could not encode face'}
            
            # Calculate face size (approximate quality metric)
            top, right, bottom, left = face_locations[0]
            face_width = right - left
            face_height = bottom - top
            face_size = min(face_width, face_height)
            
            quality = 'good' if face_size > 100 else 'acceptable' if face_size > 50 else 'poor'
            
            return {
                'valid': True,
                'face_size': face_size,
                'quality': quality,
                'encoding_quality': 'good'  # Could add more metrics
            }
            
        except Exception as e:
            return {'valid': False, 'reason': str(e)}


# Optional: Test the module if run directly
if __name__ == "__main__":
    print("Testing Face Recognition Module...")
    
    # Create recognizer instance
    recognizer = FaceRecognizer()
    
    # Check if dataset exists
    if os.path.exists("dataset"):
        # Train on dataset
        num_faces = recognizer.train_from_dataset("dataset")
        
        if num_faces > 0:
            # Save model
            recognizer.save_model()
            
            # Show stats
            stats = recognizer.get_model_stats()
            print("\nModel Statistics:")
            print(f"  Total encodings: {stats['total_encodings']}")
            print(f"  Unique students: {stats['unique_students']}")
            print(f"  Average per student: {stats['avg_encodings_per_student']:.1f}")
    else:
        print("No dataset folder found. Please create 'dataset' folder with student images.")