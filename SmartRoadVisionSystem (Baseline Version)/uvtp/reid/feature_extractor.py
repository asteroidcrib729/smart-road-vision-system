"""FastReID-based feature extractor for vehicle re-identification.

This module provides a production-oriented wrapper around FastReID with:
- strict startup validation
- deterministic preprocessing
- normalized embeddings
- cosine-distance matching utilities
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

import numpy as np

from ..config import UVTPConfig


@dataclass
class FastReIDVehicleExtractor:
    """Vehicle ReID embedding extractor using FastReID.

    Notes
    -----
    - The model expects a FastReID YAML config and model weights path.
    - Inference is performed in eval/no-grad mode.
    - Output embeddings are L2-normalized.
    """

    config_file: str
    weights_path: str
    device: str = "cuda"
    config: UVTPConfig = field(default_factory=UVTPConfig)

    # Lazily initialized runtime handles
    _torch: Optional[object] = field(init=False, default=None, repr=False)
    _predictor: Optional[object] = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        try:
            import torch
            from fastreid.config import get_cfg
            from fastreid.engine import DefaultPredictor
        except Exception as exc:  # pragma: no cover - env dependent
            raise RuntimeError(
                "FastReID dependencies are missing. Install torch and fastreid first."
            ) from exc

        if not self.config_file:
            raise ValueError("config_file is required for FastReID initialization")
        if not Path(self.config_file).exists():
            raise FileNotFoundError(f"FastReID config file not found: {self.config_file}")
        if not self.weights_path:
            raise ValueError("weights_path is required for FastReID initialization")
        if not Path(self.weights_path).exists():
            raise FileNotFoundError(f"FastReID weights not found: {self.weights_path}")

        self._torch = torch
        cfg = get_cfg()
        cfg.merge_from_file(self.config_file)
        cfg.MODEL.WEIGHTS = self.weights_path
        cfg.MODEL.DEVICE = self.device
        cfg.freeze()

        self._predictor = DefaultPredictor(cfg)
        self._predictor.model.eval()

    def _preprocess(self, image_bgr: np.ndarray) -> object:
        import cv2

        if image_bgr is None or image_bgr.size == 0:
            raise ValueError("image_bgr must be a non-empty numpy array")

        image = cv2.resize(image_bgr, self.config.feature_input_size)
        image = image[:, :, ::-1].astype(np.float32) / 255.0  # BGR -> RGB
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        image = (image - mean) / std
        image = np.transpose(image, (2, 0, 1))
        tensor = self._torch.from_numpy(image).unsqueeze(0)
        return tensor.to(self.device)

    def extract_embedding(self, image_bgr: np.ndarray) -> np.ndarray:
        tensor = self._preprocess(image_bgr)
        with self._torch.no_grad():
            output = self._predictor.model(tensor)

        # FastReID outputs may be tensor or dict depending on config/head.
        if isinstance(output, dict):
            embedding_tensor = output.get("features")
            if embedding_tensor is None:
                raise RuntimeError("FastReID output dict missing 'features' key")
        else:
            embedding_tensor = output

        embedding = embedding_tensor.detach().cpu().numpy().reshape(-1).astype(np.float32)
        return self.normalize_embedding(embedding)

    @staticmethod
    def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(embedding)
        if norm <= 1e-12:
            return embedding
        return embedding / norm

    @staticmethod
    def cosine_distance(v1: np.ndarray, v2: np.ndarray) -> float:
        v1n = FastReIDVehicleExtractor.normalize_embedding(v1)
        v2n = FastReIDVehicleExtractor.normalize_embedding(v2)
        return float(1.0 - np.dot(v1n, v2n))

    def is_same_vehicle(self, prev_embedding: np.ndarray, next_embedding: np.ndarray) -> bool:
        dist = self.cosine_distance(prev_embedding, next_embedding)
        return dist < self.config.reid_cosine_match_threshold

    def batch_is_same_vehicle(self, pairs: Iterable[tuple[np.ndarray, np.ndarray]]) -> list[bool]:
        return [self.is_same_vehicle(a, b) for a, b in pairs]