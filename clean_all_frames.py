import cv2
import numpy as np
import os

def clean_frames():
    frames_dir = 'public/frames'
    webp_params = [cv2.IMWRITE_WEBP_QUALITY, 95]
    
    files_to_clean = []
    for i in range(64):
        files_to_clean.append((f"{i}.webp", os.path.join(frames_dir, f"{i}.webp")))
    files_to_clean.append(("center.webp", os.path.join(frames_dir, "center.webp")))
    
    total_cleaned_components = 0
    cleaned_frames_count = 0

    for name, path in files_to_clean:
        if not os.path.exists(path):
            continue
        
        img = cv2.imread(path)
        if img is None:
            continue
        
        # Corner background sample (pure background)
        clean_bg = img[10, 10].copy()
        
        # Distance to background color
        diff = np.sqrt(np.sum((img.astype(float) - clean_bg.astype(float))**2, axis=2))
        fg_mask = (diff > 28).astype(np.uint8)
        
        # Connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(fg_mask)
        
        if num_labels <= 1:
            continue
            
        # Find main character (largest component)
        areas = [stats[l, cv2.CC_STAT_AREA] for l in range(1, num_labels)]
        main_label = np.argmax(areas) + 1
        
        artifact_mask = np.zeros(img.shape[:2], dtype=np.uint8)
        frame_artifacts = 0
        
        for l in range(1, num_labels):
            if l == main_label:
                continue
            area = stats[l, cv2.CC_STAT_AREA]
            cx, cy = centroids[l]
            
            # Any non-main component with area < 10000 is an artifact (stray cursor, pointer, noise)
            if area < 10000:
                artifact_mask[labels == l] = 255
                frame_artifacts += 1
                total_cleaned_components += 1
        
        if frame_artifacts > 0:
            cleaned_frames_count += 1
            # Dilate mask slightly by 2 pixels to catch anti-aliased cursor edges
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            dilated_mask = cv2.dilate(artifact_mask, kernel, iterations=1)
            
            # Inpaint / fill with clean background
            cleaned = img.copy()
            cleaned[dilated_mask > 0] = clean_bg
            
            # Save cleaned frame
            cv2.imwrite(path, cleaned, webp_params)
            
            # Also sync frame_{i}.webp if it exists
            if name != "center.webp":
                alt_path = os.path.join(frames_dir, f"frame_{name}")
                cv2.imwrite(alt_path, cleaned, webp_params)
            else:
                # Sync center.webp in public and root
                cv2.imwrite('public/center.webp', cleaned, webp_params)
                if os.path.exists('center.webp'):
                    cv2.imwrite('center.webp', cleaned, webp_params)

    print(f"Cleanup Complete!")
    print(f"Cleaned {total_cleaned_components} artifacts across {cleaned_frames_count} frames.")

if __name__ == "__main__":
    clean_frames()
