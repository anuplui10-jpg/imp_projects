import cv2
import os

os.makedirs('temp_inspect', exist_ok=True)
cap = cv2.VideoCapture('character.mp4')
frame_idx = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    if frame_idx % 4 == 0 or frame_idx == 239:
        thumb = cv2.resize(frame, (320, 180))
        cv2.putText(thumb, f'F{frame_idx}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.imwrite(os.path.join('temp_inspect', f'frame_{frame_idx:03d}.jpg'), thumb)
    frame_idx += 1

cap.release()
print('Extraction complete. Total frames inspected:', frame_idx)
