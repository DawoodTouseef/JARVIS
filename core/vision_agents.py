# Copyright 2025 Dawood Thouseef
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from vision_agent.agent import VisionAgentCoderV2
from vision_agent.models import AgentMessage
from core.Agent_models import get_vision_model_from_database
from typing import List, Optional
import os
import numpy as np
import logging
from contextlib import contextmanager
from vision_agent.tools import load_image,save_image
from config import  JARVIS_DIR,loggers
from vision_agent.configs.openai_config import OpenAILMM
from vision_agent.agent.vision_agent_planner_v2 import VisionAgentPlannerV2

# Configure logging
logger = loggers['VISION']

DEFAULT_PROMPT = """Provide detailed description of the image(s) focusing on:
- Text content (OCR information)
- Distinct objects and their spatial relationships
- Color schemes and visual style
- Actions or activities depicted
- Contextual information and subtle details
- Specific terminologies for semantic document retrieval"""

def resize_image(image_path:str):
    import cv2

    # Read the image
    image = cv2.imread(image_path)

    # Reduce size by half
    height, width = image.shape[:2]
    new_size = (width // 2, height // 2)
    resized_image = cv2.resize(image, new_size)

    # Save the resized image
    cv2.imwrite(image_path, resized_image)

@contextmanager
def vision_model_context():
    """Context manager for handling vision model configuration"""
    model = get_vision_model_from_database()
    if model:
        original_openai_url = os.environ.get("OPENAI_BASE_URL")
        original_openai_key = os.environ.get("OPENAI_API_KEY")

        os.environ["OPENAI_BASE_URL"] = model.url
        os.environ["OPENAI_API_KEY"] = model.api_key
        
        try:
            yield model
        finally:
            # Restore original environment variables
            if original_openai_url:
                os.environ["OPENAI_BASE_URL"] = original_openai_url
            else:
                del os.environ["OPENAI_BASE_URL"]

            if original_openai_key:
                os.environ["OPENAI_API_KEY"] = original_openai_key
            else:
                del os.environ["OPENAI_API_KEY"]
    else:
        logger.error("No vision model configured in database")
        yield None


def vision_agent(
    prompt: str = None,
    images: List = None  # Changed from List[str] to List to accept bytes or str
) -> Optional[str]:
    try:
        with vision_model_context() as model:
            if not model:
                return None

            if not images:  # Check if images list is empty
                logger.error("No images provided for processing")
                return None

            final_prompt = prompt or DEFAULT_PROMPT
            logger.info(f"Processing {len(images)} images with prompt: {final_prompt[:50]}...")
            bin_image = []
            for image in images:
                import uuid
                if isinstance(image, str) and image.startswith(("http", "https")):
                    # Handle URL strings
                    np_image = load_image(image)
                    image_dir = os.path.join(JARVIS_DIR, "data", "images")
                    image_path = os.path.join(image_dir, f"image-{str(uuid.uuid4())}.jpg")
                    save_image(np_image, image_path)
                    resize_image(image_path)
                    bin_image.append(image_path)
                elif isinstance(image, bytes):
                    # Handle bytes input from camera feed
                    from PIL import Image
                    import io
                    image_dir = os.path.join(JARVIS_DIR, "data", "images")
                    image_path = os.path.join(image_dir, f"image-{str(uuid.uuid4())}.jpg")
                    img = Image.open(io.BytesIO(image))
                    np_image = np.array(img)
                    save_image(np_image, image_path)
                    resize_image(image_path)
                    bin_image.append(image_path)
                else:
                    # Handle local file paths or other string inputs
                    bin_image.append(image)

            planner = OpenAILMM(model_name=model.name, timeout=6000)
            summarizer = OpenAILMM(model_name=model.name, timeout=6000)
            critic = OpenAILMM(model_name=model.name, timeout=6000)
            planner = VisionAgentPlannerV2(planner, summarizer, critic)
            agent = VisionAgentCoderV2(
                verbose=True,
                planner=planner,
            )
            code_context = agent.generate_code([
                AgentMessage(
                    role="user",
                    content=final_prompt,
                    media=bin_image
                )
            ])

            if not code_context or not code_context.code:
                logger.warning("No code generated by the vision agent")
                return None

            return f"{code_context.code}\n\n{code_context.test or 'No tests generated'}"

    except Exception as e:
        return f"Error in vision agent processing: {str(e.message)}"


if __name__ == "__main__":
    import cv2
    from PIL import Image
    import io
    camera = cv2.VideoCapture(0)
    def capture_camera_feed():
        if camera.isOpened():
            ret, frame = camera.read()
            if ret:
                # Convert to PIL Image and save temporarily
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                return [buffer.getvalue()]  # Return as a list for vision_agent compatibility
        return None
    # Example test with sample image
    test_image = capture_camera_feed()
    result = vision_agent(
        prompt="Analyze this image and explain the scenario of this image.",
        images=test_image
    )
    if result:
        print("Analysis Result:")
        print(result)
    else:
        print("Failed to process image")