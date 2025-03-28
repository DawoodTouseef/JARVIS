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
import logging
from contextlib import contextmanager
from vision_agent.tools import load_image,save_image
from config import  JARVIS_DIR
from vision_agent.configs.openai_config import OpenAILMM
from vision_agent.agent.vision_agent_planner_v2 import VisionAgentPlannerV2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        prompt:str=None,
        images:List[str]=None
) -> Optional[str]:
    """
    Process images using vision agent with contextual model configuration

    Args:
        prompt: Optional custom prompt for image analysis
        image: List of image paths/URLs to process

    Returns:
        Formatted string containing generated code and tests, or None on failure
    """
    try:
        with (vision_model_context() as model):
            if not model:
                return None

            if not prompt:
                logger.error("No images provided for processing")
                return None

            final_prompt = prompt or DEFAULT_PROMPT
            logger.info(f"Processing {len(images)} images with prompt: {final_prompt[:50]}...")
            bin_image=[]
            for image in images:
                import uuid
                if image.startswith(("http", "https")):
                    np_image=load_image(image)
                    image_dir=os.path.join(JARVIS_DIR,"data","images")
                    image_path=os.path.join(image_dir,f"image-{str(uuid.uuid4())}.jpg")
                    save_image(np_image,image_path)
                    resize_image(image_path)
                    bin_image.append(image_path)
                else:
                    bin_image.append(image)
            coder=OpenAILMM(model_name=model.name,timeout=6000)
            tester=OpenAILMM(model_name=model.name,timeout=6000)
            debugger=OpenAILMM(model_name=model.name,timeout=6000)
            planner=OpenAILMM(model_name=model.name,timeout=6000)
            summarizer=OpenAILMM(model_name=model.name,timeout=6000)
            critic=OpenAILMM(model_name=model.name,timeout=6000)
            planner=VisionAgentPlannerV2(
                planner, summarizer, critic
            )
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
        logger.error(f"Error in vision agent processing: {str(e)}", exc_info=True)
        return None


if __name__ == "__main__":
    # Example test with sample image
    test_image = ["https://t4.ftcdn.net/jpg/03/07/33/25/360_F_307332586_iH4fO87qkGRKYvEmp5UxzhCQn3OjEQ4n.jpg"]  # Replace with actual image path
    result = vision_agent(
        prompt="Analyze this image and explain the scenario of this image.",
        images=test_image
    )
    if result:
        print("Analysis Result:")
        print(result)
    else:
        print("Failed to process image")