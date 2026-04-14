# MediaPipe model management for hand mouse

import os
import socket
import tempfile
import time
import urllib.request
import logging
from config import HAND_MODEL_URL
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import (
    VisionTaskRunningMode,
)
from mediapipe.tasks.python.vision.hand_landmarker import (
    HandLandmarker,
    HandLandmarkerOptions,
)

logger = logging.getLogger(__name__)

def ensure_hand_model(model_path):
    """Ensure the hand landmarker model exists locally.

    Downloads with retries, a socket timeout, and a temporary file so partial
    downloads do not leave behind a broken model file.
    """
    if os.path.exists(model_path) and os.path.getsize(model_path) > 0:
        return

    model_dir = os.path.dirname(model_path) or "."
    os.makedirs(model_dir, exist_ok=True)

    max_attempts = 3
    chunk_size = 1024 * 1024

    for attempt in range(1, max_attempts + 1):
        temp_fd, temp_path = tempfile.mkstemp(
            prefix="hand_landmarker_", suffix=".task", dir=model_dir
        )
        os.close(temp_fd)

        try:
            logger.info(
                f"Downloading hand landmarker model... "
                f"(attempt {attempt}/{max_attempts})"
            )
            with urllib.request.urlopen(HAND_MODEL_URL, timeout=30) as response, open(
                temp_path, "wb"
            ) as output_file:
                total_size = response.headers.get("Content-Length")
                total_size = int(total_size) if total_size else None
                downloaded = 0
                last_reported_mb = -1

                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break

                    output_file.write(chunk)
                    downloaded += len(chunk)

                    downloaded_mb = downloaded // (1024 * 1024)
                    if downloaded_mb != last_reported_mb:
                        last_reported_mb = downloaded_mb
                        if total_size:
                            percent = downloaded * 100 / total_size
                            logger.info(
                                f"  Downloaded {downloaded_mb} MB / "
                                f"{total_size / (1024 * 1024):.1f} MB "
                                f"({percent:.1f}%)"
                            )
                        else:
                            logger.info(f"  Downloaded {downloaded_mb} MB")

            if os.path.getsize(temp_path) == 0:
                raise RuntimeError("Downloaded model file is empty.")

            os.replace(temp_path, model_path)
            logger.info(f"Model downloaded: {model_path}")
            return

        except KeyboardInterrupt:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise RuntimeError(
                "Model download was interrupted. Re-run the script and let the "
                "download finish, or manually download the file from "
                f"{HAND_MODEL_URL} and save it as "
                f"'{os.path.basename(model_path)}' beside the script."
            ) from None
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            if os.path.exists(temp_path):
                os.remove(temp_path)

            if attempt == max_attempts:
                raise RuntimeError(
                    "Failed to download the MediaPipe hand model after multiple "
                    "attempts. Check your internet connection or manually place "
                    f"'{os.path.basename(model_path)}' beside the script."
                ) from exc

            logger.error(f"Download failed: {exc}. Retrying in 2 seconds...")
            time.sleep(2)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

def create_hand_landmarker(model_path):
    """Create and return HandLandmarker instance."""
    base_options = BaseOptions(model_asset_path=model_path)
    options = HandLandmarkerOptions(
	    base_options=base_options,
	    running_mode=VisionTaskRunningMode.VIDEO,
	    num_hands=2,
	    min_hand_detection_confidence=0.7,
	    min_hand_presence_confidence=0.6,
	    min_tracking_confidence=0.6,
    )
    return HandLandmarker.create_from_options(options)
