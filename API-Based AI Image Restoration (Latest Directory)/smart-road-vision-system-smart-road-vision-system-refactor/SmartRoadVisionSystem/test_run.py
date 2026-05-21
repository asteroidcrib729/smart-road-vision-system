import cv2
import numpy as np
from pipeline import VideoPipeline

# Create a dummy video file
height, width = 720, 1280
out = cv2.VideoWriter('dummy.avi', cv2.VideoWriter_fourcc(*'DIVX'), 15, (width, height))

for i in range(30):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # Draw a moving rectangle
    x = int(300 + i * 20)
    cv2.rectangle(img, (x, 300), (x+200, 500), (0, 255, 0), -1)
    out.write(img)
out.release()

pipeline = VideoPipeline(video_source='dummy.avi')
pipeline.run()
