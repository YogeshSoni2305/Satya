from groq import Groq
from system_prompts import *
import json
import os
import re
from preprocessor import Description

from dotenv import load_dotenv

load_dotenv()


def extract_json_object(text: str) -> dict:
    """
    Extract the first valid JSON object from a string.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in formatter output.")

    json_str = match.group(0)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON extracted:\n{json_str}") from e


def format_preprocessed_with_groq(preprocessed_dict):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    prompt = FORMATTER_PROMPT + "\n\nDATA:\n" + json.dumps(preprocessed_dict, ensure_ascii=False)

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,          # IMPORTANT: reduce creativity
        max_completion_tokens=800,
        top_p=1,
        stream=True,
    )

    full_response = ""
    for chunk in completion:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="")
            full_response += delta

    print("\n\n---- PARSED JSON ----")

    try:
        return extract_json_object(full_response)
    except Exception as e:
        print("❌ Formatter JSON extraction failed.")
        print("RAW OUTPUT:\n", full_response)
        raise e

def normalize_for_formatter(preprocessed: dict) -> dict:
    return {
        "user_text": preprocessed.get("text", ""),
        "image_description": preprocessed.get("image", ""),
        "video_summary": preprocessed.get("video", ""),
        "audio_transcript": preprocessed.get("audio", ""),
        "url_article_text": preprocessed.get("url", "")
    }



def run_full_pipeline(input_dict):
    desc = Description()
    extracted = desc.process(input_dict)
    normalized = normalize_for_formatter(extracted)
    formatted_output = format_preprocessed_with_groq(normalized)
    return formatted_output

    


if __name__ == "__main__":
    sample_input = {
        "text": "Explain what this media is about.",
        "image": "test.jpg",
        "audio": None,
        "video": None,
        "url": None
    }

    print("\n🚀 Running full Groq pipeline...\n")
    result = run_full_pipeline(sample_input)

    print("\n\n===== FINAL OUTPUT =====")
    print(result)
