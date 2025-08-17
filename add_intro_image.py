



import os
import datetime
import subprocess
from PIL import Image
from dotenv import load_dotenv
try:
    from .utils import ffprobe_get, ensure_dir
except ImportError:
    from utils import ffprobe_get, ensure_dir

load_dotenv()


class TransitionStrategy:
    def __init__(self, style: str, props: dict, duration: int = 1, zoom_max: float = 2.0):
        self.style = style
        self.props = props
        self.duration = duration
        self.fps = int(props['fps'])
        self.zoom_max = zoom_max
        self.vf_fit_pad = f"scale=w={props['width']}:h={props['height']}:force_original_aspect_ratio=decrease,pad={props['width']}:{props['height']}:(ow-iw)/2:(oh-ih)/2:color=white"

    def get_filter(self) -> str:
        """
        Returns the ffmpeg video filter string for the selected animation style.
        """
        d = self.duration
        w, h = self.props['width'], self.props['height']
        if self.style == "zoom":
            # Animate zoom from 1 to zoom_max over the duration
            total_frames = self.fps * d
            zoom_expr = f"1+(on/{int(total_frames)-1 if total_frames>1 else 1})*({self.zoom_max}-1)"
            return self.vf_fit_pad + f",zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(total_frames)}:s={w}x{h}"
        elif self.style == "fade":
            return self.vf_fit_pad + f",fade=t=in:st=0:d={d}"
        elif self.style == "slide_left":
            return self.vf_fit_pad + f",crop=w='iw':h='ih':x='(1-t/{d})*iw':y=0"
        elif self.style == "slide_right":
            return self.vf_fit_pad + f",crop=w='iw':h='ih':x='t/{d}*iw':y=0"
        elif self.style == "slide_up":
            return self.vf_fit_pad + f",crop=w='iw':h='ih':x=0:y='(1-t/{d})*ih'"
        elif self.style == "slide_down":
            return self.vf_fit_pad + f",crop=w='iw':h='ih':x=0:y='t/{d}*ih'"
        elif self.style == "blur_in":
            return self.vf_fit_pad + f",gblur=sigma='max(20*(1-t/{d}),0.1)'"
        elif self.style == "rotate":
            return self.vf_fit_pad + f",rotate='-(1-t/{d})*PI/4:c=white'"
        elif self.style == "scale_in":
            return self.vf_fit_pad + f",scale=iw*(0.5+t/{d}*0.5):ih*(0.5+t/{d}*0.5)"
        elif self.style == "grayscale_in":
            return self.vf_fit_pad + f",colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3:0:0:0:0:1,fade=t=out:st=0:d={d}:alpha=1"
        elif self.style == "color_in":
            return self.vf_fit_pad + f",fade=t=in:st=0:d={d}:alpha=1,colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3:0:0:0:0:1"
        elif self.style == "none":
            return self.vf_fit_pad
        else:
            return self.vf_fit_pad



class AddIntroImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_path": ("STRING", {"label": "Video file path", "multiline": False, "default": "/home/goat.mp4"}),
                "image_path": ("STRING", {"label": "Image file path", "multiline": False, "default": "/home/goat.png"}),
                "duration": ("FLOAT", {"default": 0.5, "min": 0.01, "max": 10.0, "step": 0.01}),
                "animation_style": ([
                    "zoom", "fade", "slide_left", "slide_right", "slide_up", "slide_down", "blur_in", "rotate", "scale_in", "grayscale_in", "color_in", "none"
                ], {"default": "zoom"}),
                "zoom_max": ("FLOAT", {"label": "Zoom Max (for zoom transition)", "default": 1.35, "min": 1.0, "max": 5.0, "step": 0.01}),
                "padding_color": ([
                    "black", "white", "red", "green", "blue", "yellow", "magenta", "cyan"
                ], {"label": "Padding Color", "default": "black"}),
            }
        }


    RETURN_TYPES = ("STRING", "file")
    RETURN_NAMES = ("output_video_path", "output_video_file")
    FUNCTION = "add_intro"
    CATEGORY = "hoangyell/video"

    def add_intro(
        self,
        video_path: str,
        image_path: str,
        duration: float,
        animation_style: str,
        zoom_max: float = 2.0,
        padding_color: str = "black"
    ) -> tuple[str, str]:
        """
        Adds an image (scaled and padded to video resolution) as an intro before the main video, with a transition.
        All video properties are matched for seamless concat.
        Returns a tuple: (output_video_path, output_video_file)
        """
        self._validate_inputs(video_path, image_path, duration)
        props = self._extract_video_properties(video_path)
        frame_w, frame_h = int(props['width']), int(props['height'])
        # Always pad the image first, and use only the padded image for both intro and transition
        padded_image_path = self._create_padded_image(image_path, frame_w, frame_h, padding_color)
        try:
            tmp_image_video = self._create_intro_video(padded_image_path, props, duration, already_padded=True)
            tmp_transition_video = self._create_transition(padded_image_path, props, animation_style, already_padded=True, zoom_max=zoom_max)
            output_path = self._concat_videos([tmp_image_video, tmp_transition_video, video_path], props)
        finally:
            self._cleanup(["image_temp.mp4", "transition_temp.mp4", "concat_list.txt", "padded_intro_image.png"])
        return (output_path, output_path)

    def _validate_inputs(self, video_path: str, image_path: str, duration: float) -> None:
        """
        Validates input file paths and duration.
        Raises FileNotFoundError or ValueError if invalid.
        """
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        if duration <= 0:
            raise ValueError("Duration must be positive.")
    def _create_padded_image(self, image_path: str, target_w: int, target_h: int, padding_color: str = "black") -> str:
        """
        Loads the input image, scales it to fit inside (target_w, target_h) maintaining aspect ratio,
        and pads with the selected background color. Returns the path to the new image.
        """
        color_map = {
            "black": (0, 0, 0, 255),
            "white": (255, 255, 255, 255),
            "red": (255, 0, 0, 255),
            "green": (0, 255, 0, 255),
            "blue": (0, 0, 255, 255),
            "yellow": (255, 255, 0, 255),
            "magenta": (255, 0, 255, 255),
            "cyan": (0, 255, 255, 255),
        }
        bg_color = color_map.get(padding_color, (0, 0, 0, 255))
        with Image.open(image_path) as im:
            im = im.convert("RGBA")
            orig_w, orig_h = im.size
            scale = min(target_w / orig_w, target_h / orig_h)
            new_w, new_h = int(orig_w * scale), int(orig_h * scale)
            im_resized = im.resize((new_w, new_h), Image.LANCZOS)
            # Create background with selected color
            bg = Image.new("RGBA", (target_w, target_h), bg_color)
            offset = ((target_w - new_w) // 2, (target_h - new_h) // 2)
            bg.paste(im_resized, offset, im_resized if im_resized.mode == "RGBA" else None)
            out_path = "padded_intro_image.png"
            bg.convert("RGB").save(out_path, "PNG")
        return out_path

    def _extract_video_properties(self, video_path: str) -> dict:
        """
        Extracts resolution, fps, pixel format, codec, and bitrate from the video.
        Returns a dict with all properties needed for ffmpeg.
        """
        res = ffprobe_get([
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", video_path
        ])
        if not res or "x" not in res:
            raise RuntimeError(f"Could not get resolution from video: {res}")
        width, height = res.split("x")

        fps_str = ffprobe_get([
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ], "30")
        if "/" in fps_str:
            num, denom = fps_str.split("/")
            try:
                fps = float(num) / float(denom) if float(denom) != 0 else 30.0
            except Exception:
                fps = 30.0
        else:
            try:
                fps = float(fps_str) if fps_str else 30.0
            except Exception:
                fps = 30.0

        pix_fmt = ffprobe_get([
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt", "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ], "yuv420p")

        codec_name = ffprobe_get([
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ], "h264")
        if codec_name == "h264":
            codec_ffmpeg = "libx264"
        elif codec_name == "hevc":
            codec_ffmpeg = "libx265"
        else:
            codec_ffmpeg = "libx264"

        bitrate = ffprobe_get([
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=bit_rate", "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ])
        bitrate_args = ["-b:v", bitrate] if bitrate and bitrate.isdigit() else []

        return {
            "width": width,
            "height": height,
            "fps": fps,
            "pix_fmt": pix_fmt,
            "codec_ffmpeg": codec_ffmpeg,
            "bitrate_args": bitrate_args,
        }

    def _create_intro_video(self, image_path, props, duration, already_padded=False):
        """
        Creates a video from the intro image, scaled and padded to match the main video.
        If already_padded is True, skip the ffmpeg scale/pad filter.
        Returns the path to the temporary video file.
        """
        tmp_image_video = "image_temp.mp4"
        if already_padded:
            vf = None
        else:
            vf = f"scale=w={props['width']}:h={props['height']}:force_original_aspect_ratio=decrease,pad={props['width']}:{props['height']}:(ow-iw)/2:(oh-ih)/2:color=black"
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-t", str(float(duration))
        ]
        if vf:
            cmd += ["-vf", vf]
        cmd += [
            "-c:v", props['codec_ffmpeg'], "-pix_fmt", props['pix_fmt'], "-r", str(props['fps']), *props['bitrate_args'], tmp_image_video
        ]
        self._run_ffmpeg(cmd, "Failed to create intro video from image.")
        return tmp_image_video

    def _create_transition(self, image_path, props, animation_style, already_padded=False, zoom_max=2.0):
        """
        Creates a transition video from the intro image using the selected animation style.
        If already_padded is True, skip the initial scale/pad in the filter.
        Returns the path to the temporary transition video file.
        """
        tmp_transition_video = "transition_temp.mp4"
        duration = 1
        # If already_padded, remove the scale/pad part from the filter
        if already_padded:
            class NoPadTransitionStrategy(TransitionStrategy):
                def __init__(self, style, props, duration=1, zoom_max=2.0):
                    super().__init__(style, props, duration, zoom_max=zoom_max)
                    self.vf_fit_pad = ""
                def get_filter(self):
                    base = super().get_filter()
                    return base.lstrip(",")
            strategy = NoPadTransitionStrategy(animation_style, props, duration, zoom_max=zoom_max)
        else:
            strategy = TransitionStrategy(animation_style, props, duration, zoom_max=zoom_max)
        vf = strategy.get_filter()
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-vf", vf, "-c:v", props['codec_ffmpeg'],
            "-t", str(duration), "-r", str(int(props['fps'])), "-pix_fmt", props['pix_fmt'], *props['bitrate_args'], tmp_transition_video
        ]
        self._run_ffmpeg(cmd, f"Failed to create transition video with style '{animation_style}'.")
        return tmp_transition_video

    def _concat_videos(self, video_paths, props):
        """
        Concatenates the intro, transition, and main video into the final output.
        Output file is prefixed with input file name and timestamp.
        Returns the output file path.
        """
        output_dir = "output"
        ensure_dir(output_dir)
        input_base = os.path.splitext(os.path.basename(video_paths[-1]))[0]
        now = datetime.datetime.now()
        # Format: day-hourminsec (e.g., 17-153045 for 17th day, 15:30:45)
        timestamp = now.strftime("%H:%M:%S")
        output_filename = f"{input_base}_{timestamp}.mp4"
        output_path = os.path.join(output_dir, output_filename)
        concat_list = "concat_list.txt"
        with open(concat_list, "w") as f:
            for path in video_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c:v", props['codec_ffmpeg'],
            "-pix_fmt", props['pix_fmt'], *props['bitrate_args'], output_path
        ]
        self._run_ffmpeg(cmd, "Failed to concatenate videos.")
        return output_path

    def _cleanup(self, files):
        """
        Removes temporary files used in the process.
        Ignores errors if files do not exist.
        """
        for f in files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass

    def _run_ffmpeg(self, cmd, error_message):
        """
        Runs an ffmpeg command and raises a RuntimeError if it fails.
        """
        try:
            completed = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if completed.returncode != 0:
                print(completed.stderr)
                raise RuntimeError(error_message + f"\nffmpeg stderr: {completed.stderr}")
        except subprocess.CalledProcessError as e:
            print(e.stderr)
            raise RuntimeError(error_message + f"\nffmpeg stderr: {e.stderr}")

class Test:
    @classmethod
    def get_kwargs(cls):
        kwargs = {
            "video_path": os.getenv("VIDEO_PATH", "/home/hoangyell/com/goat.mp4"),
            "image_path": os.getenv("IMAGE_PATH", "/home/hoangyell/com/goat_main.png"),
            "duration": float(os.getenv("DURATION", 0.5)),
            "animation_style": os.getenv("ANIMATION_STYLE", "zoom"),
            "zoom_max": float(os.getenv("ZOOM_MAX", 1.35)),
            "padding_color": os.getenv("PADDING_COLOR", "black"),
        }
        return kwargs

    @classmethod
    def test(cls):
        kwargs = cls.get_kwargs()
        AddIntroImage().add_intro(**kwargs)

    @classmethod
    def bulk_test(cls):
        """
        Bulk test method to ensure the node can be instantiated and run with custom parameters.
        """
        kwargs = cls.get_kwargs()
        characters = ["hoangyell", "mouse", "buff", "tiger", "cat", "dragon", "kingcobra", "horse", "goat", "monkey", "chicken", "dog", "pig"]
        results = []
        directory = os.getenv("DIRECTORY", "/home/hoangyell/com/")
        for character in characters:
            data = {
                "video_path": f"{directory}/{character}.mp4",
                "image_path": f"{directory}/{character}_main.png",
            }
            result = cls().add_intro(**{**kwargs, **data})
            results.append(result)
        print("[Test] Bulk test completed.", results)

