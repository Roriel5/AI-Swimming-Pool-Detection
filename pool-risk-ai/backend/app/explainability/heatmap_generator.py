"""
Explainability — Grad-CAM heatmaps for YOLOv11 predictions.

GradCAM
-------
Registers forward/backward hooks on the last convolutional layer of the
YOLO backbone to capture feature-map activations and their gradients.
Computes the global-average-pooled weighted sum to produce a saliency map,
then resizes and overlays it on the input image (COLORMAP_JET).

HeatmapGenerator
----------------
High-level interface used by the rest of the codebase.  Wraps GradCAM and
also provides mask-overlay and bounding-box visualisation helpers.
"""

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level Grad-CAM
# ---------------------------------------------------------------------------

class GradCAM:
    """
    Gradient-weighted Class Activation Map for a PyTorch model.

    Works with any CNN that has at least one Conv2d layer (auto-detects the
    last such layer).  For YOLOv11 the backbone's last convolutional output
    is used, giving a spatial attention map over the input image.
    """

    def __init__(self, model, target_layer_name: Optional[str] = None) -> None:
        """
        Args:
            model:             ultralytics YOLO model or bare nn.Module.
            target_layer_name: Named module to hook into.  When None, the
                               last Conv2d in the model is selected.
        """
        # Unwrap ultralytics YOLO wrapper if needed
        self.nn_model: torch.nn.Module = getattr(model, "model", model)
        self.gradients: Optional[torch.Tensor] = None
        self.activations: Optional[torch.Tensor] = None
        self._hooks: list = []

        self.target_layer = self._resolve_layer(target_layer_name)
        if self.target_layer is not None:
            self._register_hooks()
        else:
            logger.warning("GradCAM: could not find a target Conv2d layer.")

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _resolve_layer(self, name: Optional[str]) -> Optional[torch.nn.Module]:
        """Return the named module, or auto-select the last Conv2d."""
        if name is not None:
            for mod_name, mod in self.nn_model.named_modules():
                if mod_name == name:
                    return mod
            logger.warning("GradCAM: layer '%s' not found — auto-selecting.", name)

        last_conv: Optional[torch.nn.Module] = None
        for _, mod in self.nn_model.named_modules():
            if isinstance(mod, torch.nn.Conv2d):
                last_conv = mod
        return last_conv

    def _register_hooks(self) -> None:
        def _fwd(module, inp, out):
            self.activations = out.detach().clone()

        def _bwd(module, grad_in, grad_out):
            self.gradients = grad_out[0].detach().clone()

        self._hooks.append(self.target_layer.register_forward_hook(_fwd))
        self._hooks.append(self.target_layer.register_full_backward_hook(_bwd))

    def remove_hooks(self) -> None:
        """Deregister all hooks (call when done to avoid memory leaks)."""
        for h in self._hooks:
            h.remove()
        self._hooks.clear()

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    def generate(
        self,
        image: np.ndarray,
        target_size: Optional[Tuple[int, int]] = None,
    ) -> np.ndarray:
        """
        Generate a Grad-CAM saliency heatmap for *image*.

        Args:
            image:       BGR uint8 numpy array.
            target_size: Output (width, height).  Defaults to input image size.

        Returns:
            uint8 greyscale heatmap of the same spatial size as target_size.
        """
        if self.target_layer is None:
            logger.error("GradCAM: no target layer — returning blank heatmap.")
            return np.zeros(image.shape[:2], dtype=np.uint8)

        h, w = image.shape[:2]
        target_size = target_size or (w, h)

        device = next(self.nn_model.parameters()).device
        tensor = self._to_tensor(image).to(device)

        self.nn_model.eval()
        self.gradients = None
        self.activations = None

        try:
            out = self.nn_model(tensor)
            # Aggregate all scalar outputs as the "class score"
            if isinstance(out, (list, tuple)):
                score = sum(
                    o.sum() for o in out if isinstance(o, torch.Tensor)
                )
            else:
                score = out.sum()

            self.nn_model.zero_grad()
            score.backward(retain_graph=False)

        except Exception as exc:
            logger.error("GradCAM forward/backward failed: %s", exc, exc_info=True)
            return np.zeros((h, w), dtype=np.uint8)

        if self.gradients is None or self.activations is None:
            logger.error("GradCAM hooks returned no data.")
            return np.zeros((h, w), dtype=np.uint8)

        # Global-average-pool gradients → channel importance weights
        weights = self.gradients.mean(dim=[2, 3], keepdim=True)  # [1, C, 1, 1]
        cam = (weights * self.activations).sum(dim=1, keepdim=True)  # [1, 1, H', W']
        cam = F.relu(cam).squeeze().cpu().numpy()

        # Normalise to [0, 1]
        cam_min, cam_max = cam.min(), cam.max()
        if cam_max > cam_min:
            cam = (cam - cam_min) / (cam_max - cam_min)
        else:
            cam = np.zeros_like(cam)

        cam_resized = cv2.resize(cam, target_size)
        return (cam_resized * 255).astype(np.uint8)

    # ------------------------------------------------------------------
    # Overlay
    # ------------------------------------------------------------------

    def overlay(
        self,
        image: np.ndarray,
        heatmap: np.ndarray,
        alpha: float = 0.4,
        colormap: int = cv2.COLORMAP_JET,
    ) -> np.ndarray:
        """
        Blend a Grad-CAM heatmap with the original image.

        Args:
            image:    Original BGR image.
            heatmap:  Greyscale heatmap (uint8) from generate().
            alpha:    Weight of heatmap in the blend (0 = image only, 1 = heatmap only).
            colormap: OpenCV colourmap identifier.

        Returns:
            BGR uint8 blended image.
        """
        coloured = cv2.applyColorMap(heatmap, colormap)
        if coloured.shape[:2] != image.shape[:2]:
            coloured = cv2.resize(coloured, (image.shape[1], image.shape[0]))
        return cv2.addWeighted(image, 1.0 - alpha, coloured, alpha, 0)

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------

    @staticmethod
    def _to_tensor(image: np.ndarray) -> torch.Tensor:
        """Convert a BGR uint8 image to a normalised RGB float tensor [1, 3, H, W]."""
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        t = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
        return t.unsqueeze(0)


# ---------------------------------------------------------------------------
# High-level interface
# ---------------------------------------------------------------------------

class HeatmapGenerator:
    """
    Convenient wrapper for generating explainability visualisations:
      - Grad-CAM overlays
      - Segmentation mask overlays
      - Bounding-box annotations
    """

    def __init__(self, yolo_model=None) -> None:
        """
        Args:
            yolo_model: Loaded ultralytics YOLO model.  When None, only
                        mask/bbox visualisation helpers are available.
        """
        self.yolo_model = yolo_model
        self._grad_cam: Optional[GradCAM] = None

        if yolo_model is not None:
            self._grad_cam = GradCAM(yolo_model)

    # ------------------------------------------------------------------
    # Grad-CAM
    # ------------------------------------------------------------------

    def generate_gradcam(self, image: np.ndarray) -> np.ndarray:
        """
        Generate a Grad-CAM overlay for *image*.

        Args:
            image: BGR uint8 array.

        Returns:
            BGR uint8 image with Grad-CAM heatmap blended in.
        """
        if self._grad_cam is None:
            logger.error("HeatmapGenerator: no model loaded — returning original image.")
            return image.copy()

        heatmap = self._grad_cam.generate(image)
        return self._grad_cam.overlay(image, heatmap)

    # ------------------------------------------------------------------
    # Mask overlay
    # ------------------------------------------------------------------

    def generate_mask_overlay(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        color: Tuple[int, int, int] = (0, 255, 0),
        alpha: float = 0.4,
    ) -> np.ndarray:
        """
        Blend a binary segmentation mask onto the image.

        Args:
            image:  BGR image.
            mask:   Binary mask (0 / non-zero).
            color:  BGR colour for the mask overlay.
            alpha:  Blend weight for the mask region.

        Returns:
            BGR image with coloured mask and contour outline.
        """
        overlay = image.copy()
        mask_bool = mask > 0

        overlay[mask_bool] = (
            (1.0 - alpha) * overlay[mask_bool].astype(np.float32)
            + alpha * np.array(color, dtype=np.float32)
        ).clip(0, 255).astype(np.uint8)

        # Draw contour for crisp boundary
        mask_u8 = mask_bool.astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, color, 2)

        return overlay

    # ------------------------------------------------------------------
    # Bounding-box annotation
    # ------------------------------------------------------------------

    def generate_bbox_visualization(
        self,
        image: np.ndarray,
        bbox: List[int],
        label: str = "pool",
        confidence: float = 1.0,
        color: Tuple[int, int, int] = (0, 255, 0),
    ) -> np.ndarray:
        """
        Draw a labelled bounding box on *image*.

        Args:
            image:       BGR image.
            bbox:        [x1, y1, x2, y2] pixel coordinates.
            label:       Class label string.
            confidence:  Confidence score (shown in label).
            color:       BGR box and label background colour.

        Returns:
            Annotated BGR image.
        """
        vis = image.copy()
        x1, y1, x2, y2 = bbox

        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)

        text = f"{label}: {confidence:.2f}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        (txt_w, txt_h), _ = cv2.getTextSize(text, font, font_scale, thickness)

        # Filled label background
        cv2.rectangle(vis, (x1, y1 - txt_h - 8), (x1 + txt_w + 4, y1), color, -1)
        cv2.putText(vis, text, (x1 + 2, y1 - 4), font, font_scale, (0, 0, 0), thickness)

        return vis

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    def save_visualization(self, image: np.ndarray, output_path: str) -> None:
        """Write a visualisation image to disk."""
        import pathlib

        pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(output_path, image)
        logger.info("Visualization saved to %s", output_path)
