import re
with open("SmartRoadVisionSystem/pipeline.py", "r") as f:
    content = f.read()

imports_to_add = """from models.transreid import TransReIDExtractor
from core.tracker import DeepOCSORT
from core.uvtp import UVTPGate, EvidenceBuffer, OutputDispatcher
from subtasks.anpr import ANPRProcessor
from subtasks.helmet import HelmetDetector"""

content = content.replace("from config import Config", f"from config import Config\n{imports_to_add}")

with open("SmartRoadVisionSystem/pipeline.py", "w") as f:
    f.write(content)
