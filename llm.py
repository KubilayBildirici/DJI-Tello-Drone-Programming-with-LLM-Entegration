from openai import OpenAI
from dotenv import load_dotenv
from config import Config
import base64
import cv2

load_dotenv(override=True)

_client = OpenAI(timeout=Config.OPENAI_TIMEOUT)

PROMPT = """You are a strict vision system.

TASK:
Find if the object in Image A exists in Image B.

RULES:
- Only answer EXACTLY one of:
  HEDEF BULUNDU
  HEDEF BULUNAMADI
- No explanation
- No extra text"""


def encode_frame(frame) -> str:
    """OpenCV BGR frame'i base64 JPEG string'e çevirir."""
    _, buffer = cv2.imencode(".jpg", frame)
    return base64.b64encode(buffer).decode("utf-8")


def analyze_frame(target_b64: str, frame_b64: str) -> str:
    """
    İki görüntüyü karşılaştırır ve hedefin bulunup bulunmadığını döner.

    Returns:
        "HEDEF BULUNDU" veya "HEDEF BULUNAMADI"
    """
    response = _client.chat.completions.create(
        model=Config.LLM_MODEL,
        max_tokens=Config.LLM_MAX_TOKENS,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "text", "text": "Image A (target):"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{target_b64}"},
                    },
                    {"type": "text", "text": "Image B (current frame):"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"},
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content.strip()

