# from google import genai
# from google.genai import types
# from pydantic import BaseModel
# import json
# import os


# class Prompt(BaseModel):
#     claims:list[str]
#     questions:list[str]

# class GeminiChat:
#     def __init__(
#             self, api_key, model_name="gemini-2.0-flash-lite",
#             temperature=1, top_p=0.95, top_k=40, max_output_tokens=1024,
#             system_prompt="Reply:No system prompt given"
#             ):
#         self.model_name = model_name
#         self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
#         self.chat = self.client.chats.create(model=self.model_name)
#         self.config =types.GenerateContentConfig(
#             temperature=temperature,
#             top_p=top_p,top_k=top_k,
#             max_output_tokens=max_output_tokens,
#             system_instruction=[types.Part.from_text(text=system_prompt)],
#             response_mime_type= 'application/json',
#             response_schema= list[Prompt],
#         )
#     def send_message(self, message_text):
#         # chat.send_message is inbuilt function of genai
#         response = self.chat.send_message(message_text, config=self.config)
#         try:
#             return json.loads(response.text) 
#         except json.JSONDecodeError:
#             print("Could not convert to json, returning string")
#             return response.text 
        
#     def get_history(self):
#         # chat.get_history is inbuilt function of genai
#         history = []
#         for message in self.chat.get_history():
#             history.append(f'role - {message.role}: {message.parts[0].text}')
#         return history



import json
import os
from groq import Groq
from pydantic import BaseModel, ValidationError


# ==========================
# Output schema
# ==========================
class Prompt(BaseModel):
    claims: list[str]
    questions: list[str]


# ==========================
# Chat wrapper
# ==========================
class GroqChat:
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "meta-llama/llama-4-scout-17b-16e-instruct",
        temperature: float = 1.0,
        top_p: float = 0.95,
        max_output_tokens: int = 1024,
        system_prompt: str = "Reply: No system prompt given"
    ):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model_name = model_name
        self.temperature = temperature
        self.top_p = top_p
        self.max_output_tokens = max_output_tokens
        self.system_prompt = system_prompt

    def send_message(self, message_text: str):
        prompt = f"""
        Return ONLY valid JSON.

        Expected format:
        A JSON array where each item matches this schema:
        {Prompt.model_json_schema()}

        User message:
        {message_text}

        Rules:
        - No markdown
        - No explanations
        - No extra text outside JSON
        """

        completion = self.client.chat.completions.create(
            model=self.model_name,
            temperature=self.temperature,
            top_p=self.top_p,
            max_completion_tokens=self.max_output_tokens,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
        )

        raw_output = completion.choices[0].message.content.strip()

        try:
        #     parsed = json.loads(raw_output)
        #     validated = [Prompt(**item) for item in parsed]
        #     return [v.model_dump() for v in validated]
                parsed = json.loads(raw_output)

                # ---- NORMALIZE OUTPUT ----
                if isinstance(parsed, dict):
                    parsed = [parsed]

                if not isinstance(parsed, list):
                    raise ValueError("Expected list or dict JSON output")

                validated = []
                for item in parsed:
                    if isinstance(item, dict):
                        validated.append(Prompt(**item))
                    else:
                        print("⚠️ Skipping invalid item:", item)

                return [v.model_dump() for v in validated]


        except (json.JSONDecodeError, ValidationError) as e:
            print("❌ JSON validation failed")
            print("Raw output:")
            print(raw_output)
            raise e
           

            
            


    def get_history(self):
        # Groq is stateless — kept for compatibility
        return []
