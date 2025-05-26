import requests
import json
import os
from PIL import Image
from io import BytesIO
from datetime import datetime
from pydantic import Field
from typing import Callable, List, Dict, Optional
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import BaseTool, FileWriterTool
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import torch

from config import JARVIS_DIR, SessionManager
from core.Agent_models import  get_model_from_database
from core.tools.standard_tools import NextCloudTool
from jarvis_integration.models.users import Users
from jarvis_integration.models.preferences import Preferences


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
        Classify the task based on user input:
        - object_detection
        - image_to_text
        - facial_analysis
        - video_motion
        - video_scene
        - question_answering
        - all

        Prioritize question_answering if the input contains a question (e.g., starts with 'What', 'How', 'Why', or ends with '?').
        User input: "{user_input}"
        Output only the category.
        """
        llm_info = get_model_from_database()
        llm = LLM(model=f"openai/{llm_info.name}", base_url=llm_info.url, api_key=llm_info.api_key)
        response = llm.call([{"role": "user", "content": prompt}])
        task_type = response.strip()
        valid_tasks = ["object_detection", "image_to_text", "facial_analysis",
                       "video_motion", "video_scene", "question_answering", "all"]
        return task_type if task_type in valid_tasks else "all"


# ---------------------------- Media Preprocessing ----------------------------
def load_image(source) -> Optional[Image.Image]:
    try:
        if isinstance(source, str) and source.startswith(("http", "https")):
            response = requests.get(source, timeout=10)
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert("RGB")
        elif isinstance(source, bytes):
            return Image.open(BytesIO(source)).convert("RGB")
        elif isinstance(source, str) and os.path.exists(source):
            return Image.open(source).convert("RGB")
        elif isinstance(source, np.ndarray):
            return Image.fromarray(cv2.cvtColor(source, cv2.COLOR_BGR2RGB))
    except Exception as e:
        print(f"Error loading image: {str(e)}")
        return None
    return None


def extract_video_frames(video_path: str, max_frames: int = 100, frame_interval: int = 30) -> List[np.ndarray]:
    frames = []
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return frames

        frame_count = 0
        while cap.isOpened() and frame_count < max_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count * frame_interval)
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
            frame_count += 1
        cap.release()
    except Exception as e:
        print(f"Error extracting video frames: {str(e)}")
    return frames


def save_temp_image(image: Image.Image) -> str:
    os.makedirs(os.path.join(JARVIS_DIR, "data", "images"), exist_ok=True)
    path = os.path.join(JARVIS_DIR, "data", "images", f"temp_{os.urandom(8).hex()}.png")
    image.save(path, format="PNG")
    return path


# ---------------------------- Vision Models ----------------------------
class ObjectDetector:
    def __init__(self):
        from transformers import DetrImageProcessor, DetrForObjectDetection
        self.processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50", cache_dir="../../.cache")
        self.model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50", cache_dir="../../.cache")
        self.model.eval()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def detect(self, image: Image.Image) -> List[Dict]:
        try:
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.model(**inputs)
            target_sizes = torch.tensor([image.size[::-1]]).to(self.device)
            results = self.processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.9)[0]
            return [
                {
                    "label": self.model.config.id2label[label.item()],
                    "confidence": float(score),
                    "box": [float(x) for x in box]
                }
                for score, label, box in zip(results["scores"], results["labels"], results["boxes"])
            ]
        except Exception as e:
            return [{"error": f"Object detection failed: {str(e)}"}]
        finally:
            torch.cuda.empty_cache() if torch.cuda.is_available() else None


class ImageToText:
    def __init__(self):
        from transformers import BlipProcessor, BlipForConditionalGeneration
        self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", cache_dir="../../.cache")
        self.model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base",
                                                                  cache_dir="../../.cache")
        self.model.eval()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def generate(self, image: Image.Image) -> str:
        try:
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.model.generate(**inputs)
            return self.processor.decode(outputs[0], skip_special_tokens=True)
        except Exception as e:
            return f"Caption generation failed: {str(e)}"
        finally:
            torch.cuda.empty_cache() if torch.cuda.is_available() else None


class FaceAnalyzer:
    def analyze(self, image_path: str) -> Dict:
        from deepface import DeepFace
        try:
            return DeepFace.analyze(img_path=image_path,
                                    actions=["age", "gender", "emotion", "race"],
                                    enforce_detection=False,
                                    align=True,
                                    detector_backend='mtcnn')
        except Exception as e:
            return {"error": f"Face detection failed: {str(e)}"}


class VideoAnalyzer:
    def detect_motion(self, frames: List[np.ndarray]) -> List[Dict]:
        results = []
        try:
            prev_gray = None
            for i, frame in enumerate(frames):
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if prev_gray is not None:
                    diff = cv2.absdiff(prev_gray, gray)
                    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
                    motion_score = np.mean(thresh) / 255
                    if motion_score > 0.1:
                        results.append({
                            "frame": i,
                            "motion_score": float(motion_score),
                            "timestamp": i * 0.033
                        })
                prev_gray = gray
            return results
        except Exception as e:
            return [{"error": f"Motion detection failed: {str(e)}"}]

    def detect_scene_changes(self, frames: List[np.ndarray]) -> List[Dict]:
        results = []
        try:
            prev_hist = None
            for i, frame in enumerate(frames):
                hist = cv2.calcHist([frame], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                hist = cv2.normalize(hist, hist).flatten()
                if prev_hist is not None:
                    diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CHISQR)
                    if diff > 100:
                        results.append({
                            "frame": i,
                            "change_score": float(diff),
                            "timestamp": i * 0.033
                        })
                prev_hist = hist
            return results
        except Exception as e:
            return [{"error": f"Scene detection failed: {str(e)}"}]


class VisualQuestionAnswering:
    def __init__(self):
        from transformers import BlipProcessor, BlipForQuestionAnswering
        self.processor = BlipProcessor.from_pretrained("Salesforce/blip-vqa-base", cache_dir="../../.cache")
        self.model = BlipForQuestionAnswering.from_pretrained("Salesforce/blip-vqa-base", cache_dir="../../.cache")
        self.model.eval()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def answer(self, image: Image.Image, questions: List[str]) -> List[Dict]:
        results = []
        try:
            for question in questions:
                inputs = self.processor(images=image, text=question, return_tensors="pt").to(self.device)
                with torch.no_grad():
                    outputs = self.model.generate(**inputs)
                answer = self.processor.decode(outputs[0], skip_special_tokens=True)
                results.append({"question": question, "answer": answer})
        except Exception as e:
            results.append({"error": f"Question answering failed: {str(e)}"})
        finally:
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
        return results


# ---------------------------- Vision Analysis Tool ----------------------------
class VisionAnalysisTool(BaseTool):
    name: str = "Vision Analysis Tool"
    description: str = "Analyzes images and videos for faces, objects, captions, motion, and answers questions."
    media_inputs: List = Field(default_factory=list)

    def __init__(self, media_inputs: List):
        super().__init__(media_inputs=media_inputs)

    def _extract_questions(self, user_input: str) -> List[str]:
        # Split input into potential questions based on common separators
        questions = [q.strip() for q in user_input.split('?') if q.strip()]
        if not questions:
            questions = [user_input.strip()] if user_input.strip() else []
        return questions

    def _process_single_media(self, media_input, task_type: str, user_input: str = None) -> Dict:
        detector = ObjectDetector()
        captioner = ImageToText()
        analyzer = FaceAnalyzer()
        video_analyzer = VideoAnalyzer()
        vqa = VisualQuestionAnswering()

        result = {"input": "media" if isinstance(media_input, bytes) else str(media_input)}
        questions = self._extract_questions(user_input) if user_input else []

        try:
            if isinstance(media_input, str) and media_input.lower().endswith(('.mp4', '.avi', '.mov')):
                frames = extract_video_frames(media_input)
                if not frames:
                    return {"error": "Failed to extract video frames"}

                result["type"] = "video"
                result["frame_count"] = len(frames)

                if task_type in ("video_motion", "all"):
                    result["motion"] = video_analyzer.detect_motion(frames)
                if task_type in ("video_scene", "all"):
                    result["scene_changes"] = video_analyzer.detect_scene_changes(frames)

                key_frames = frames[::max(1, len(frames) // 5)]
                frame_results = []
                for frame in key_frames:
                    image = load_image(frame)
                    if image is None:
                        continue
                    temp_path = save_temp_image(image)
                    frame_result = {}
                    if task_type in ("object_detection", "all"):
                        frame_result["objects"] = detector.detect(image)
                    if task_type in ("image_to_text", "all"):
                        frame_result["caption"] = captioner.generate(image)
                    if task_type in ("facial_analysis", "all"):
                        frame_result["faces"] = analyzer.analyze(temp_path)
                    if task_type in ("question_answering", "all") and questions:
                        frame_result["answers"] = vqa.answer(image, questions)
                    frame_results.append(frame_result)
                    os.remove(temp_path)
                result["frame_analyses"] = frame_results

            else:
                image = load_image(media_input)
                if image is None:
                    return {"error": "Failed to load image"}

                result["type"] = "image"
                temp_path = save_temp_image(image)

                if task_type in ("object_detection", "all"):
                    result["objects"] = detector.detect(image)
                if task_type in ("image_to_text", "all"):
                    result["caption"] = captioner.generate(image)
                if task_type in ("facial_analysis", "all"):
                    result["faces"] = analyzer.analyze(temp_path)
                if task_type in ("question_answering", "all") and questions:
                    result["answers"] = vqa.answer(image, questions)

                os.remove(temp_path)

        except Exception as e:
            result["error"] = str(e)

        return result

    def _run(self, user_input: str) -> str:
        task_detector = TaskTypeDetector()
        task_type = task_detector.detect_task(user_input)

        all_results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_media = {
                executor.submit(self._process_single_media, media_input, task_type, user_input): media_input
                for media_input in self.media_inputs}
            for future in future_to_media:
                all_results.append(future.result())

        return json.dumps(all_results, indent=2)


# ---------------------------- Vision Agent Pipeline ----------------------------
def vision_agent(media_inputs, user_input: str):
    model_info = get_model_from_database()
    llm = LLM(model=f"openai/{model_info.name}", base_url=model_info.url, api_key=model_info.api_key)

    vision_agent = Agent(
        role="Vision Analyzer",
        goal="Analyze images/videos and answer questions about visual content.",
        backstory="You are an expert in processing visual media and providing accurate answers.",
        tools=[VisionAnalysisTool(media_inputs)],
        verbose=True,
        llm=llm
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"vision_report_{timestamp}.json"
    report_path = os.path.join(JARVIS_DIR, "data", "reports", report_filename)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    reporter_tools = [FileWriterTool(), HumanInputRun()]
    session = SessionManager()
    session.load_session()
    email = session.get_email()
    user_id = None
    if email:
        user_id = Users.get_user_by_email(email).id
    if user_id is not None:
        nextcloud_prefs = Preferences.get_preferences_by_user_id(user_id)
        nextcloud_config = next((pref for pref in nextcloud_prefs if pref.setting_key == "nextcloud"), None)
        if nextcloud_config is not None:
            reporter_tools.append(NextCloudTool())

    reporter = Agent(
        role="Report Generator",
        goal="Summarize visual analysis and question-answering results.",
        backstory="You create clear, concise summaries of visual data and answers.",
        tools=reporter_tools,
        verbose=True,
        llm=llm
    )

    analysis_task = Task(
        description=f"Analyze the media for: {user_input}. Answer questions if provided. Return JSON.",
        agent=vision_agent,
        expected_output="Media analysis and question answers in JSON"
    )

    report_task = Task(
        description=f"""
        Generate a concise summary of the analysis results in 100-500 words.
        - Highlight key findings: objects detected, faces (if any), scene descriptions, motion (for videos).
        - For question_answering tasks, emphasize questions and answers, including confidence where applicable.
        - For videos, summarize across key frames.
        - Save the full JSON to '{report_path}' or upload to '/VisionReports/{report_filename}'.
        - If unsure, ask the user using the human tool.
        """,
        agent=reporter,
        expected_output="Concise summary of analysis and question-answering results (100-500 words)"
    )

    crew = Crew(
        agents=[vision_agent, reporter],
        tasks=[analysis_task, report_task],
        process=Process.sequential,
        verbose=True,
        max_rpm=12
    )

    return crew.kickoff({"user_input": user_input})


# ---------------------------- CLI Testing Entry ----------------------------
if __name__ == "__main__":
    s = SessionManager()
    s.create_session("tdawood140@gmail.com")


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


    input_query = "What is the main object in the image? How many people are present?"
    media_inputs = capture_image_from_cam()
    result = vision_agent(media_inputs, input_query)
    print(result)