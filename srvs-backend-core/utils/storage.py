import cv2
import os

def save_snapshot(image, directory, filename):
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, filename)
    cv2.imwrite(filepath, image)
    return filepath
