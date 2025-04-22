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
# vision_module.py

import requests
import json
import os
from PIL import Image
from io import BytesIO
from datetime import datetime
from pydantic import Field
from typing import Callable,  List
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import BaseTool, FileWriterTool

from config import JARVIS_DIR
from core.Agent_models import get_vision_model_from_database
from core.tools.standard_tools import NextCloudTool

# ---------------------------- Human Input Tool ----------------------------
class HumanInputRun(BaseTool):
    name: str = "human"
    description: str = "Ask user for guidance when unsure."
    prompt_func: Callable[[str], None] = Field(default_factory=lambda: lambda x: print("\n" + x))
    input_func: Callable = Field(default_factory=lambda: input)

    def _run(self, query: str) -> str:
        self.prompt_func(query)
        return self.input_func()

# ---------------------------- Task Type Detection ----------------------------
class TaskTypeDetector:
    def detect_task(self, user_input: str) -> str:
        prompt = f"""
        Classify the task:
        - object_detection
        - image_to_text
        - facial_analysis
        - all

        User input: "{user_input}"
        Output only the category.
        """
        llm_info = get_vision_model_from_database()
        llm = LLM(model=f"openai/{llm_info.name}", base_url=llm_info.url, api_key=llm_info.api_key)
        response = llm.call([{"role": "user", "content": prompt}])
        task_type = response.strip()
        return task_type if task_type in ["object_detection", "image_to_text", "facial_analysis", "all"] else "all"

# ---------------------------- Image Preprocessing ----------------------------
def load_image(source) -> Image.Image:
    if isinstance(source, str) and source.startswith(("http", "https")):
        response = requests.get(source)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGB")
    elif isinstance(source, bytes):
        return Image.open(BytesIO(source)).convert("RGB")
    elif isinstance(source, str) and os.path.exists(source):
        return Image.open(source).convert("RGB")
    raise ValueError("Unsupported image format or path.")

def save_temp_image(image: Image.Image) -> str:
    os.makedirs(os.path.join(JARVIS_DIR, "data", "images"), exist_ok=True)
    path = os.path.join(JARVIS_DIR, "data", "images", f"temp_{os.urandom(8).hex()}.png")
    image.save(path, format="PNG")
    return path

# ---------------------------- Vision Models ----------------------------
class ObjectDetector:
    def __init__(self):
        super().__init__()

    def detect(self, image: Image.Image):
        from transformers import DetrImageProcessor,DetrForObjectDetection
        import torch
        self.processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50", cache_dir=".cache")
        self.model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50", cache_dir=".cache")
        self.model.eval()
        inputs = self.processor(images=image, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model(**inputs)
        target_sizes = torch.tensor([image.size[::-1]])
        results = self.processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.9)[0]
        return [
            {
                "label": self.model.config.id2label[label.item()],
                "confidence": float(score),
                "box": [float(x) for x in box]
            }
            for score, label, box in zip(results["scores"], results["labels"], results["boxes"])
        ]

class ImageToText:
    def __init__(self):
        super().__init__()

    def generate(self, image: Image.Image):
        from transformers import (
            BlipProcessor, BlipForConditionalGeneration
        )
        import torch
        self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", cache_dir=".cache")
        self.model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base",
                                                                  cache_dir=".cache")
        self.model.eval()
        inputs = self.processor(images=image, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model.generate(**inputs)
        return self.processor.decode(outputs[0], skip_special_tokens=True)

class FaceAnalyzer:
    def analyze(self, image_path: str):
        from deepface import DeepFace
        try:
            return DeepFace.analyze(img_path=image_path, actions=["age", "gender", "emotion", "race"], enforce_detection=False)
        except Exception as e:
            return {"error": f"Face detection failed: {str(e)}"}

# ---------------------------- Vision Analysis Tool ----------------------------
class VisionAnalysisTool(BaseTool):
    name: str = "Vision Analysis Tool"
    description: str = "Detects faces, objects, and generates captions based on intent."
    image_inputs: List = Field(default_factory=list)

    def __init__(self, image_inputs: List):
        super().__init__(image_inputs=image_inputs)

    def _run(self, user_input: str) -> str:
        task_detector = TaskTypeDetector()
        task_type = task_detector.detect_task(user_input)

        detector = ObjectDetector()
        captioner = ImageToText()
        analyzer = FaceAnalyzer()

        all_results = []

        for img_input in self.image_inputs:
            try:
                image = load_image(img_input)
                temp_path = save_temp_image(image)

                result = {"input": "image" if isinstance(img_input, bytes) else str(img_input)}
                if task_type in ("object_detection", "all"):
                    result["objects"] = detector.detect(image)
                if task_type in ("image_to_text", "all"):
                    result["caption"] = captioner.generate(image)
                if task_type in ("facial_analysis", "all"):
                    result["faces"] = analyzer.analyze(temp_path)

                all_results.append(result)
                os.remove(temp_path)

            except Exception as e:
                all_results.append({"error": str(e)})

        return json.dumps(all_results, indent=2)

# ---------------------------- Vision Agent Pipeline ----------------------------
def vision_agent(image_inputs, user_input: str):
    model_info = get_vision_model_from_database()
    llm = LLM(model=f"openai/{model_info.name}", base_url=model_info.url, api_key=model_info.api_key)

    vision_agent = Agent(
        role="Vision Analyzer",
        goal="Analyze visual input for faces, objects, and descriptions.",
        backstory="You are a vision expert assistant.",
        tools=[VisionAnalysisTool(image_inputs)],
        verbose=True,
        llm=llm
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"vision_report_{timestamp}.json"
    report_path = os.path.join(JARVIS_DIR, "data", "reports", report_filename)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    reporter = Agent(
        role="Report Generator",
        goal="Summarize and store visual analysis reports.",
        backstory="You format vision data and upload or save them.",
        tools=[FileWriterTool(), NextCloudTool(), HumanInputRun()],
        verbose=True,
        llm=llm
    )

    analysis_task = Task(
        description=f"Analyze the image(s) for: {user_input}. Return JSON.",
        agent=vision_agent,
        expected_output="Vision analysis in JSON"
    )

    report_task = Task(
        description=f"""
        Create a summary from the analysis results.
        - Include objects, faces, and scene.
        - Save locally to '{report_path}' or upload to '/VisionReports/{report_filename}'.
        - If unsure, ask the user using the human tool.
        Return confirmation.
        """,
        agent=reporter,
        expected_output="Formatted report summary with save/upload status."
    )

    crew = Crew(
        agents=[vision_agent, reporter],
        tasks=[analysis_task, report_task],
        process=Process.sequential,
        verbose=True,
        max_rpm=3
    )

    return crew.kickoff({"user_input": user_input})

# ---------------------------- CLI Testing Entry ----------------------------
if __name__ == "__main__":
    import cv2

    def capture_image_from_cam():
        cam = cv2.VideoCapture(0)
        ret, frame = cam.read()
        cam.release()
        if ret:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            return [buffer.getvalue()]
        return []

    input_query = "Analyze objects and faces in this photo."
    captured = capture_image_from_cam()
    output = vision_agent(captured, input_query)
    print(output)