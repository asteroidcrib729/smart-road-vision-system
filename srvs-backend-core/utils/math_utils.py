import cv2
import numpy as np

def calculate_laplacian_variance(image):
    """
    Returns a measure of focus (sharpness) for an image.
    Higher values indicate less motion blur.
    """
    if image is None or image.size == 0:
        return 0.0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def calculate_bbox_area(bbox):
    """
    bbox format: [x1, y1, x2, y2]
    """
    return max(0, bbox[2] - bbox[0]) * max(0, bbox[3] - bbox[1])

class SpeedEstimator:
    def __init__(self, src_pts, dst_pts, fps=30.0):
        # Calculate Homography Matrix
        self.H, _ = cv2.findHomography(np.array(src_pts), np.array(dst_pts))
        self.fps = fps
        self.track_history = {} # track_id: [(time, (x, y))]

    def update_and_estimate(self, track_id, bbox, frame_idx):
        """
        Calculates speed based on perspective displacement.
        """
        # Bottom-center of the bounding box
        x_center = (bbox[0] + bbox[2]) / 2.0
        y_bottom = bbox[3]

        pts = np.array([[[x_center, y_bottom]]], dtype="float32")
        real_world_pts = cv2.perspectiveTransform(pts, self.H)[0][0]

        current_time = frame_idx / self.fps

        if track_id not in self.track_history:
            self.track_history[track_id] = []

        self.track_history[track_id].append((current_time, real_world_pts))

        # Keep history short (e.g., last 15 frames)
        if len(self.track_history[track_id]) > 15:
            self.track_history[track_id].pop(0)

        # Calculate speed if we have enough points
        if len(self.track_history[track_id]) >= 5:
            old_time, old_pt = self.track_history[track_id][0]
            new_time, new_pt = self.track_history[track_id][-1]

            dt = new_time - old_time
            if dt > 0:
                dist = np.linalg.norm(new_pt - old_pt)
                # m/s to km/h
                speed_kmh = (dist / dt) * 3.6
                return speed_kmh

        return 0.0

    def clear(self, track_id):
        if track_id in self.track_history:
            del self.track_history[track_id]
