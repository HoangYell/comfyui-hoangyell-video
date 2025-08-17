

# comfyui-hoangyell-video-edit

Professional ComfyUI custom nodes for video editing workflows.

---
**Author:** [hoangyell](http://hoangyell.com/)  
*Coding for fun! If you like this project, visit my site or say hi!*
---

## Features
- Select video and image files via ComfyUI file picker
- Image is scaled and padded to fit video resolution (no crop/stretch)
- Zoom transition animation between intro image and main video
- All video properties (resolution, fps, pixel format, codec, bitrate) are matched to the original video
- Output is auto-saved and selectable in ComfyUI
- Modular codebase, ready for future expansion (more nodes, helpers, and utilities)

## Usage
1. Place this folder in your `ComfyUI/custom_nodes/` directory.
2. Restart ComfyUI.
3. Use the `VideoIntroImage` node in your workflow.

## Requirements
- ffmpeg (system binary)
- ffprobe (system binary)
- ffmpeg-python (for future extensibility, see requirements.txt)

## Node: VideoIntroImage
**Inputs:**
- `video_path`: Path to the main video file
- `image_path`: Path to the intro image file
- `duration`: Duration (seconds) for the intro image

**Outputs:**
- `output_video_path`: Path to the output video file
- `output_video_file`: Output video file (for ComfyUI file output)

## Extensibility
- All helpers are in `utils.py` for easy reuse.
- Node code is modular and ready for future splitting into multiple files/classes.
- Follow the structure in `Bjornulf_custom_nodes` for large-scale node collections.

## License
MIT
