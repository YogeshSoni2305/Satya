import cv2
from PIL import Image
import tldextract
from newspaper import Article
# from serpapi import GoogleSearch
# import google.generativeai as genai
from google import genai
from google.genai import types
from system_prompts import *
import os
from groq import Groq
from dotenv import load_dotenv
load_dotenv()



class Description:
    def __init__(self):
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
        self.API_KEY = os.getenv("API_KEY")

    # ============= IMAGE DESCRIPTION =============
    def _extract_image_description(self, image_path: str) -> str:
        if not os.path.exists(image_path):
            return ""

        # genai.configure(api_key=self.GEMINI_API_KEY)
        # model = genai.GenerativeModel("gemini-1.5-flash")
        client = genai.Client(api_key=GEMINI_API_KEY)

            
        image = Image.open(image_path)
        # response = model.generate_content(["Describe this image in detail.", image])
        response = client.models.generate_content(
                model="gemini-1.5-pro",
                contents=prompt
            )


        return response.text or ""

    # ============= VIDEO DESCRIPTION =============
    def _extract_video_description_vision(self, video_path: str, frame_count: int = 3) -> dict:
        if not os.path.exists(video_path):
            return {"summary": ""}

        genai.configure(api_key=self.GEMINI_API_KEY)
        vision_model = genai.GenerativeModel("gemini-1.5-pro")
        text_model = genai.GenerativeModel("gemini-1.5-pro")

        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        interval = max(total_frames // frame_count, 1)

        descriptions = []

        for i in range(frame_count):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i * interval)
            ret, frame = cap.read()
            if not ret:
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)

            response = vision_model.generate_content(
                ["Describe this frame in detail:", pil_image]
            )

            if response.text:
                descriptions.append(response.text.strip())

        cap.release()
        combined = "\n".join(descriptions)

        if not combined:
            return {"summary": ""}

        try:
            summary = text_model.generate_content(
                ["Summarize these frame descriptions clearly:", combined]
            ).text.strip()
        except:
            summary = combined[:300]

        return {"summary": summary}

    # ============= AUDIO DESCRIPTION =============
    def _extract_audio_description(self, audio_path: str) -> str:
        if not os.path.exists(audio_path):
            return ""

        client = Groq(api_key=self.GROQ_API_KEY)
        with open(audio_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=f
            )
        return response.text or ""

    # ============= URL CONTENT =============
    def _extract_content_from_url(self, url: str):
        try:
            article = Article(url)
            article.download()
            article.parse()

            return article.text or ""
        except:
            return ""

    # ============= MAIN PROCESSOR =============
    def process(self, input_dict: dict) -> dict:
        responses = {
            "text": "",
            "image": "",
            "video": "",
            "audio": "",
            "url": ""
        }

        for key, value in input_dict.items():
            if value in [None, "null", "None"]:
                continue

            try:
                match key:
                    case "text":
                        responses[key] = value

                    case "image":
                        responses[key] = self._extract_image_description(value)

                    case "video":
                        responses[key] = self._extract_video_description_vision(value)["summary"]

                    case "audio":
                        responses[key] = self._extract_audio_description(value)

                    case "url":
                        responses[key] = self._extract_content_from_url(value)

            except Exception as e:
                responses[key] = ""

        # print("🟢 Final responses:", responses)
        return responses
