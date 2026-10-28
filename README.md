# VALENTIN MOREAU — Luxury Portfolio & Zero-Ghosting Head-Tracking Engine

An award-winning, luxury portfolio hero section featuring an ultra-smooth, zero-lag, zero-ghosting cursor-tracking character animation.

---

## 💎 Key Architecture & Technical Execution

### 1. Zero CSS 3D Transforms (Rock-Solid Motionless Body)
- **Constraint Compliance**: Absolutely **NO** `perspective`, `rotateX`, or `rotateY` transforms are applied to the canvas, page, or container.
- The character's shoulders and torso remain **100% rock-solid motionless**.
- Only the character's head and gaze rotate via precise 2D canvas frame sequencing.

### 2. Zero Runtime MP4 Seeking
- Video seeking in browsers causes severe stutter, decoding stalls, and uncontrolled background playback on single-keyframe AI/CGI MP4s.
- **100% of runtime rendering is performed using pre-extracted WebP slices** drawn directly onto an HTML5 2D Canvas context.

### 3. OpenCV Inspection & Frame Extraction
Using Python and OpenCV (`cv2`), the 240-frame timeline in `character.mp4` was analyzed to isolate the 8 cardinal/intercardinal compass directions and the neutral eye-contact frame:

| Compass Direction | Angle | Video Frame Number | Description |
|:---|:---:|:---:|:---|
| **RIGHT** | 0° | **Frame 168** | Head & gaze turned toward viewer's right |
| **DOWN-RIGHT** | 45° | **Frame 158** | Head & gaze tilted downward to the right |
| **DOWN** | 90° | **Frame 142** | Head & gaze looking straight down |
| **DOWN-LEFT** | 135° | **Frame 122** | Head & gaze tilted downward to the left |
| **LEFT** | 180° | **Frame 104** | Head & gaze turned toward viewer's left |
| **UP-LEFT** | 225° (-135°) | **Frame 88** | Head & gaze tilted upward to the left |
| **UP** | 270° (-90°) | **Frame 180** | Head & gaze tilted straight upward |
| **UP-RIGHT** | 315° (-45°) | **Frame 172** | Head & gaze tilted upward to the right |
| **CENTER (Neutral)** | — | **Frame 20** | Direct, confident eye-contact looking straight into camera |

- **64 WebP frames** (each ~5.625° apart) were extracted into `public/frames/` (`0.webp` through `63.webp`).
- `center.webp` was extracted for direct eye contact.

### 4. Zero-Ghosting 60 FPS Canvas Renderer
- **Preloading**: All 64 circular trajectory frames + `center.webp` preload asynchronously into memory on page load.
- **Shortest-Path Circular Angular Lerp**:
  ```javascript
  function lerpAngle(current, target, factor = 0.26) {
    let diff = (target - current) % (Math.PI * 2);
    diff = ((diff + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
    return current + diff * factor;
  }
  ```
- **~35ms Response Latency**: The response factor `0.26` tracks the cursor with zero perceived lag.
- **Strict Single-Frame Drawing**: The canvas clears and paints **EXACTLY ONE frame at 100% opacity (`globalAlpha = 1.0`)**. No alpha-blending is used, eliminating double-face ghosting.

### 5. Center Eye Contact (12% Screen Radius Deadzone)
- When the cursor enters within **12% of the screen dimension** relative to the face center, the engine instantly transitions to `center.webp`.
- The character locks eyes with the user, creating an intimate, lifelike connection.
- A toggleable luxury visual deadzone ring is available in the control bar.

### 6. Seamless Background Parity
- OpenCV detected the median studio background color: **`RGB(236, 14, 9)` / `#eb0e09`**.
- The page, body, and canvas clear operations use `#eb0e09`, resulting in an invisible boundary with zero visible seams.

---

## 🚀 Running the Project

### Option A: Local Python Server (Recommended)
```bash
python server.py
```
Open [http://localhost:3000](http://localhost:3000) or [http://localhost:3000/public/index.html](http://localhost:3000/public/index.html) in your browser.

### Option B: Direct File Opening
You can open `public/index.html` or `index.html` directly in any modern browser.

---

## 📁 Project Structure

```
portfolio/
├── character.mp4              # Original source video (240 frames, 1280x720)
├── extract_frames.py          # Python/OpenCV script for frame extraction
├── server.py                  # High-performance local development server
├── index.html                 # Root portfolio application
├── README.md                  # Technical documentation
└── public/
    ├── index.html             # Luxury portfolio hero application
    ├── center.webp            # Direct eye-contact frame (Frame 20)
    ├── frames_metadata.json   # Extracted compass & frame metadata
    ├── frames/
    │   ├── 0.webp ... 63.webp # 64 circular rotation frames (~5.6° apart)
    │   ├── center.webp        # Neutral eye contact frame
    │   └── metadata.json      # Extraction metadata & color telemetry
    └── vendor/
        ├── react.production.min.js
        ├── react-dom.production.min.js
        └── babel.min.js
```
"# imp_projects" 
