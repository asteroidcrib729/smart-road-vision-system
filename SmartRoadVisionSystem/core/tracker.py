import numpy as np

# A highly simplified, robust object tracker placeholder to act as DeepOCSORT.
# DeepOCSORT normally uses OCSORT's spatial matching + TransReID appearance matching.
# I am implementing a clean scaffolding that performs basic assignment.

def iou(bbox1, bbox2):
    # bbox format [x1, y1, x2, y2]
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])

    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    if inter_area == 0:
        return 0

    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])

    return inter_area / float(area1 + area2 - inter_area)

class Track:
    def __init__(self, track_id, bbox, feature, cls_id):
        self.track_id = track_id
        self.bbox = bbox # [x1, y1, x2, y2]
        self.feature = feature
        self.cls_id = cls_id

        self.hits = 1
        self.time_since_update = 0
        self.is_active = False

    def update(self, bbox, feature):
        self.bbox = bbox
        if feature is not None:
            # Momentum update for appearance feature
            self.feature = 0.9 * self.feature + 0.1 * feature
            self.feature = self.feature / np.linalg.norm(self.feature)
        self.hits += 1
        self.time_since_update = 0
        self.is_active = True

class DeepOCSORT:
    def __init__(self, max_age=30, min_hits=3, iou_threshold=0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.tracks = []
        self.next_id = 1

    def update(self, detections, features):
        """
        detections: list of dicts: {'bbox': [x1,y1,x2,y2], 'conf': float, 'class': int}
        features: list of embeddings corresponding to detections.
        """
        # 1. Predict (increment age of tracks)
        for track in self.tracks:
            track.time_since_update += 1
            track.is_active = False  # Reset state until matched on current frame

        # 2. Match
        matched, unmatched_dets, unmatched_tracks = self._match(detections, features)

        # 3. Update Matched Tracks
        for track_idx, det_idx in matched:
            self.tracks[track_idx].update(detections[det_idx]['bbox'], features[det_idx])

        # 4. Create New Tracks for unmatched detections
        for det_idx in unmatched_dets:
            det = detections[det_idx]
            new_track = Track(self.next_id, det['bbox'], features[det_idx], det['class'])
            self.tracks.append(new_track)
            self.next_id += 1

        # 5. Remove Dead Tracks
        active_tracks = []
        removed_tracks = []
        for track in self.tracks:
            if track.time_since_update > self.max_age:
                removed_tracks.append(track)
            else:
                active_tracks.append(track)

        self.tracks = active_tracks

        # Return active tracks formatted
        output = []
        for track in self.tracks:
            # Return tracks that meet the minimum hit requirement
            if track.hits >= self.min_hits or track.time_since_update == 0:
                output.append({
                    'track_id': track.track_id,
                    'bbox': track.bbox,
                    'class': track.cls_id,
                    'active': track.is_active
                })

        return output, removed_tracks

    def _match(self, detections, features):
        # Extremely simplified greedy matching based primarily on IoU for scaffolding.
        # In actual DeepOCSORT, this is a linear assignment utilizing both IoU and ReID cosine distance.
        matched = []
        unmatched_dets = list(range(len(detections)))
        unmatched_tracks = list(range(len(self.tracks)))

        if len(detections) == 0 or len(self.tracks) == 0:
            return matched, unmatched_dets, unmatched_tracks

        iou_matrix = np.zeros((len(self.tracks), len(detections)))
        for t, track in enumerate(self.tracks):
            for d, det in enumerate(detections):
                iou_matrix[t, d] = iou(track.bbox, det['bbox'])

        # Greedy match sorting workaround
        for t in range(len(self.tracks)):
            if len(unmatched_dets) == 0: break
            best_dets = np.argsort(iou_matrix[t])[::-1]
            for best_det in best_dets:
                if iou_matrix[t, best_det] < self.iou_threshold:
                    break
                if best_det in unmatched_dets:
                    matched.append((t, best_det))
                    unmatched_dets.remove(best_det)
                    unmatched_tracks.remove(t)
                    break

        return matched, unmatched_dets, unmatched_tracks
