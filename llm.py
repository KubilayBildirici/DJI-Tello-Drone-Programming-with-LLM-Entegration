from openai import OpenAI
from dotenv import load_dotenv
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
import cv2

load_dotenv(override=True)

openai = OpenAI()
#executor = ThreadPoolExecutor(max_workers=2)

PROMPT = """
You are a strict vision system.

TASK:
Find if the object in Image A exists in Image B.

RULES:
- Only answer EXACTLY one of:
  HEDEF BULUNDU
  HEDEF BULUNAMADI
- No explanation
- No extra text
"""

def encode_frame(frame):
    _, buffer = cv2.imencode(".jpg", frame)
    return base64.b64encode(buffer).decode("UTF-8")

    
    
def analyze_frame(target_b64, frame_b64):
    
    response = openai.responses.create(
        model = "gpt-4o-mini",
        input=[
            {
                "role":"user",
                "content": [
                    {"type": "input_text", "text": PROMPT},
                    {"type": "input_text", "text": "Image A:"},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{target_b64}",
                    },
                    
                    {"type": "input_text", "text": "Image B:"},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{frame_b64}"
                    }
                ]
                    
            }
        ],
        max_output_tokens=50
    )
    return response.output_text.strip()
