import cv2
import numpy as np
import os
import json

def extract_webp_frames():
    video_path = 'character.mp4'
    if not os.path.exists(video_path):
        video_path = 'character.mp4.mp4'
    
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"Video Info: {total_frames} frames, {fps} FPS, {width}x{height}")
    
    all_frames = []
    for _ in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break
        all_frames.append(frame)
    cap.release()
    
    # 8 Compass Direction Frame Identifications:
    # 0 deg: RIGHT (Head turned toward viewer's right)
    # 45 deg: DOWN-RIGHT (Head turned toward viewer's bottom-right)
    # 90 deg: DOWN (Head turned straight down)
    # 135 deg: DOWN-LEFT (Head turned toward viewer's bottom-left)
    # 180 deg: LEFT (Head turned straight left)
    # 225 deg: UP-LEFT (Head turned toward viewer's top-left)
    # 270 deg: UP (Head tilted straight up)
    # 315 deg: UP-RIGHT (Head turned toward viewer's top-right)
    # CENTER: Neutral direct eye-contact looking into camera
    
    compass_directions = {
        "RIGHT": 168,
        "DOWN_RIGHT": 158,
        "DOWN": 142,
        "DOWN_LEFT": 122,
        "LEFT": 104,
        "UP_LEFT": 88,
        "UP": 180,
        "UP_RIGHT": 172,
        "CENTER": 20
    }
    
    print("Exact Frame Identifications for Compass Directions:")
    for direction, fnum in compass_directions.items():
        print(f"  - {direction:12s}: Frame {fnum}")
        
    # Detect exact background color from corner pixels across selected frames
    corner_samples = []
    for fnum in compass_directions.values():
        f = all_frames[fnum]
        corner_samples.append(f[5:15, 5:15])
        corner_samples.append(f[5:15, -15:-5])
        corner_samples.append(f[-15:-5, 5:15])
        corner_samples.append(f[-15:-5, -15:-5])
    
    bg_bgr = np.median(corner_samples, axis=(0, 1, 2))
    bg_rgb = bg_bgr[::-1].astype(int)
    hex_color = f"#{bg_rgb[0]:02x}{bg_rgb[1]:02x}{bg_rgb[2]:02x}"
    print(f"Seamless Background Color: RGB({bg_rgb[0]}, {bg_rgb[1]}, {bg_rgb[2]}) => {hex_color}")
    
    # Generate 64 frames along 360 degree circular head rotation trajectory:
    # 0..8 (0 to 45 deg): RIGHT -> DOWN_RIGHT
    # 8..16 (45 to 90 deg): DOWN_RIGHT -> DOWN
    # 16..24 (90 to 135 deg): DOWN -> DOWN_LEFT
    # 24..32 (135 to 180 deg): DOWN_LEFT -> LEFT
    # 32..40 (180 to 225 deg): LEFT -> UP_LEFT
    # 40..48 (225 to 270 deg): UP_LEFT -> UP
    # 48..56 (270 to 315 deg): UP -> UP_RIGHT
    # 56..64 (315 to 360/0 deg): UP_RIGHT -> RIGHT
    
    seq = []
    seq.extend(np.linspace(168, 158, 8, endpoint=False, dtype=int))
    seq.extend(np.linspace(158, 142, 8, endpoint=False, dtype=int))
    seq.extend(np.linspace(142, 122, 8, endpoint=False, dtype=int))
    seq.extend(np.linspace(122, 104, 8, endpoint=False, dtype=int))
    seq.extend(np.linspace(104, 88, 8, endpoint=False, dtype=int))
    seq.extend(np.linspace(88, 72, 8, endpoint=False, dtype=int))
    seq.extend(np.linspace(180, 172, 8, endpoint=False, dtype=int))
    seq.extend(np.linspace(172, 168, 8, endpoint=False, dtype=int))
    
    seq = [int(x) for x in seq]
    print(f"Generated 64 frame indices: {seq}")
    
    # Output directories
    frames_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    # WebP encoding parameters: high quality 92
    webp_params = [cv2.IMWRITE_WEBP_QUALITY, 92]
    
    # Save 64 circular frames
    saved_files = []
    for i, fidx in enumerate(seq):
        frame = all_frames[fidx]
        
        # Save both as {i}.webp and frame_{i}.webp for flexibility
        p1 = os.path.join(frames_dir, f"{i}.webp")
        p2 = os.path.join(frames_dir, f"frame_{i}.webp")
        cv2.imwrite(p1, frame, webp_params)
        cv2.imwrite(p2, frame, webp_params)
        saved_files.append(f"{i}.webp")
    
    # Save center neutral frame (Frame 20)
    center_frame = all_frames[20]
    p_center1 = os.path.join(frames_dir, "center.webp")
    p_center2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "center.webp")
    cv2.imwrite(p_center1, center_frame, webp_params)
    cv2.imwrite(p_center2, center_frame, webp_params)
    
    # Write metadata JSON
    metadata = {
        "frameCount": 64,
        "compassDirections": compass_directions,
        "backgroundColor": {
            "hex": hex_color,
            "rgb": [int(bg_rgb[0]), int(bg_rgb[1]), int(bg_rgb[2])]
        },
        "videoInfo": {
            "width": width,
            "height": height,
            "fps": fps,
            "totalFrames": total_frames
        },
        "frameIndices": seq
    }
    
    with open(os.path.join(frames_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
        
    print(f"Successfully pre-extracted 64 WebP frames + center.webp to {frames_dir}")
    print(f"Sample file size: {os.path.getsize(p1) / 1024:.1f} KB")

if __name__ == "__main__":
    extract_webp_frames()
