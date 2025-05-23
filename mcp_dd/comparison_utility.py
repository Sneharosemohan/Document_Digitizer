from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.preprocessing import image
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from PIL import Image
from deepface import DeepFace
from typing import List, Optional, Dict, List
import time
# ML FACE AND SIGNATURE COMPARISON

# Function to get image embedding
base_model = ResNet50(weights='imagenet', include_top=False, pooling='avg')
def get_image_embedding(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_data = image.img_to_array(img)
    img_data = np.expand_dims(img_data, axis=0)
    img_data = preprocess_input(img_data)
    embedding = base_model.predict(img_data)
    return embedding.flatten()
# Function to compare face images
def face_similarity_matching(img_path_1: str, img_path_2: str) -> Dict[str, str]:
    start_time = time.time()
    result = DeepFace.verify(img_path_1, img_path_2)
    similarity_score = round((1 - result['distance']), 4)
    end_time = time.time()
    time_taken = str(round((end_time - start_time), 4)) + " seconds"
    return {
        "similarity_score": str(similarity_score),
        "time_taken": time_taken
    }

# Function to compare signature images
def similarity_matching(img_path_1: str, img_path_2: str) -> float:
    embedding1 = get_image_embedding(img_path_1)
    embedding2 = get_image_embedding(img_path_2)
    similarity = cosine_similarity([embedding1], [embedding2])
    return float(similarity)  # Convert numpy.float64 to float before returning
