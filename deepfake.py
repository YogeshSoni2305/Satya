# import torch
# from transformers import AutoModelForImageClassification, AutoImageProcessor
# from PIL import Image
# from pathlib import Path
# import sys
# import time

# class FakeImageDetector:
#     def __init__(self, model_name="umm-maybe/ai-image-detector", fast=True):
#         """
#         A fast and robust AI-generated image detector using a Hugging Face model.
#         """
#         self.device = "cuda" if (fast and torch.cuda.is_available()) else "cpu"
#         self.processor = AutoImageProcessor.from_pretrained(model_name)
#         self.model = AutoModelForImageClassification.from_pretrained(model_name).to(self.device)
#         self.model.eval()

#         # Optional optimization for inference speed
#         if fast:
#             self.model = torch.compile(self.model) if hasattr(torch, "compile") else self.model

#     def _load_image(self, image_path: str):
#         """Load and validate image."""
#         path = Path(image_path)
#         if not path.exists():
#             raise FileNotFoundError(f"Image not found: {path}")
#         return Image.open(path).convert("RGB")

#     @torch.inference_mode()
#     def predict(self, image_path: str):
#         """
#         Predict fake probability for a single image or a folder of images.
#         Returns dict: {image_name: fake_prob}
#         """
#         start = time.time()

#         # Handle single image or folder
#         paths = [image_path] if Path(image_path).is_file() else list(Path(image_path).glob("*.*"))
#         results = {}

#         for p in paths:
#             img = self._load_image(p)
#             inputs = self.processor(images=img, return_tensors="pt").to(self.device)
#             logits = self.model(**inputs).logits
#             probs = torch.softmax(logits, dim=-1)[0]
#             fake_prob = probs[1].item()
#             results[Path(p).name] = round(fake_prob, 4)

#         elapsed = (time.time() - start)
#         print(f"✅ Processed {len(paths)} image(s) in {elapsed:.2f}s using {self.device.upper()}")
#         return results


# if __name__ == "__main__":
#     # Usage: python detect_fake_fast.py <image_or_folder>
#     image_path = sys.argv[1] if len(sys.argv) > 1 else "sample.jpg"

#     detector = FakeImageDetector(fast=True)
#     results = detector.predict(image_path)

#     for name, score in results.items():
#         print(f"🧠 {name}: Fake probability = {score*100:.2f}%")


