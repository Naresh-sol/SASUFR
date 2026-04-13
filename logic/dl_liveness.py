import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
import os

# ── MiniFASNet Architecture Definition (MiniFASNetV2) ──

CHANNEL_CONFIGS = {
    "v2": {
        "stem": 32,
        "transition1": {"expand": 103, "out": 64},
        "stage2": [(13, 64), (13, 64), (13, 64), (13, 64)],
        "transition2": {"expand": 231, "out": 128},
        "stage3": [(231, 128), (52, 128), (26, 128), (77, 128), (26, 128), (26, 128)],
        "transition3": {"expand": 308, "out": 128},
        "stage4": [(26, 128), (26, 128)],
        "final": 512,
    },
}

class ConvBNPReLU(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=1, stride=1, padding=0, groups=1, activation=True):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, groups=groups, bias=False)
        self.bn = nn.BatchNorm2d(out_channels)
        self.prelu = nn.PReLU(out_channels) if activation else nn.Identity()

    def forward(self, x):
        return self.prelu(self.bn(self.conv(x)))

class InvertedResidual(nn.Module):
    def __init__(self, in_channels, expand_channels, out_channels, stride=1):
        super().__init__()
        self.use_residual = (in_channels == out_channels) and (stride == 1)
        self.conv = ConvBNPReLU(in_channels, expand_channels, kernel_size=1)
        self.conv_dw = ConvBNPReLU(expand_channels, expand_channels, 3, stride, 1, groups=expand_channels)
        self.project = ConvBNPReLU(expand_channels, out_channels, kernel_size=1, activation=False)

    def forward(self, x):
        out = self.project(self.conv_dw(self.conv(x)))
        if self.use_residual:
            out = out + x
        return out

class ResidualStack(nn.Module):
    def __init__(self, in_channels, block_configs):
        super().__init__()
        layers = []
        current_ch = in_channels
        for expand_ch, out_ch in block_configs:
            layers.append(InvertedResidual(current_ch, expand_ch, out_ch, stride=1))
            current_ch = out_ch
        self.model = nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)

class MiniFASNetV2(nn.Module):
    def __init__(self, num_classes=3):
        super().__init__()
        config = CHANNEL_CONFIGS["v2"]
        stem_ch = config["stem"]
        t1, t2, t3 = config["transition1"], config["transition2"], config["transition3"]
        final_ch = config["final"]

        self.stem = ConvBNPReLU(3, stem_ch, kernel_size=3, stride=2, padding=1)
        self.stem_dw = ConvBNPReLU(stem_ch, stem_ch, kernel_size=3, stride=1, padding=1, groups=stem_ch)
        self.transition1 = InvertedResidual(stem_ch, t1["expand"], t1["out"], stride=2)
        self.stage2 = ResidualStack(t1["out"], config["stage2"])
        self.transition2 = InvertedResidual(config["stage2"][-1][1], t2["expand"], t2["out"], stride=2)
        self.stage3 = ResidualStack(t2["out"], config["stage3"])
        self.transition3 = InvertedResidual(config["stage3"][-1][1], t3["expand"], t3["out"], stride=2)
        self.stage4 = ResidualStack(t3["out"], config["stage4"])
        
        self.final_expand = ConvBNPReLU(config["stage4"][-1][1], final_ch, kernel_size=1)
        self.final_dw = ConvBNPReLU(final_ch, final_ch, kernel_size=5, groups=final_ch, activation=False)

        self.flatten = nn.Flatten()
        self.linear = nn.Linear(final_ch, 128, bias=False)
        self.bn = nn.BatchNorm1d(128)
        self.drop = nn.Dropout(p=0.2)
        self.classifier = nn.Linear(128, num_classes, bias=False)

    def forward(self, x):
        x = self.stem_dw(self.stem(x))
        x = self.stage2(self.transition1(x))
        x = self.stage3(self.transition2(x))
        x = self.stage4(self.transition3(x))
        x = self.final_dw(self.final_expand(x))
        x = self.flatten(x)
        out = self.classifier(self.drop(self.bn(self.linear(x))))
        return out

# ── Utilities for specific texture-aware cropping ──

def crop_face(image, bbox, scale, out_w, out_h):
    """
    Specialized crop that captures context around the face for texture analysis.
    bbox: [x1, y1, x2, y2]
    """
    src_h, src_w = image.shape[:2]
    x1, y1, x2, y2 = bbox
    box_w = x2 - x1
    box_h = y2 - y1

    # Ensure the scale doesn't go out of bounds
    scale = min((src_h - 1) / box_h, (src_w - 1) / box_w, scale)
    new_w = box_w * scale
    new_h = box_h * scale

    center_x = x1 + box_w / 2
    center_y = y1 + box_h / 2

    nx1 = max(0, int(center_x - new_w / 2))
    ny1 = max(0, int(center_y - new_h / 2))
    nx2 = min(src_w - 1, int(center_x + new_w / 2))
    ny2 = min(src_h - 1, int(center_y + new_h / 2))

    cropped = image[ny1 : ny2 + 1, nx1 : nx2 + 1]
    return cv2.resize(cropped, (out_w, out_h))

# ── Liveness Detector Wrapper ──

class DeepTextureLiveness:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern to avoid loading models multiple times."""
        if cls._instance is None:
            cls._instance = super(DeepTextureLiveness, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_path=None):
        if self._initialized:
            return
            
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = MiniFASNetV2(num_classes=3).to(self.device)
        self.is_ready = False
        self.input_size = (80, 80)
        self.scale = 2.7  # Key for MiniFASNetV2
        
        if model_path and os.path.exists(model_path):
            try:
                state_dict = torch.load(model_path, map_location=self.device)
                # Cleanup state dict if needed
                new_state_dict = {}
                for k, v in state_dict.items():
                    name = k[7:] if k.startswith('module.') else k
                    new_state_dict[name] = v
                
                self.model.load_state_dict(new_state_dict)
                self.model.eval()
                self.is_ready = True
                print(f"[DL-Liveness] MiniFASNetV2 optimized loaded from {model_path}")
            except Exception as e:
                print(f"[DL-Liveness] Error loading model: {e}")
        else:
            print("[DL-Liveness] Simulation mode (no model weights).")
            self.model.eval()
        self._initialized = True

    def predict(self, frame, face_box):
        if face_box is None:
            return 0.0, "No face"

        try:
            # 1. Texture-Aware Crop (Scale = 2.7)
            face_crop = crop_face(frame, face_box, self.scale, self.input_size[0], self.input_size[1])
            
            # 2. Convert to Tensor (expects 0-255 float, CHW) 
            # Note: No normalization or 0-1 scaling as per original MiniFASNet utils
            tensor = torch.from_numpy(face_crop.transpose(2, 0, 1)).float()
            tensor = tensor.unsqueeze(0).to(self.device)

            with torch.no_grad():
                outputs = self.model(tensor)
                probabilities = torch.softmax(outputs, dim=1)
                
                # IMPORTANT: In MiniFASNetV2 (Yakhyo version), label_idx == 1 is REAL
                # Result structure: [Fake, Real, Fake] or similar
                # Based on source: "Real" if label_idx == 1 else "Fake"
                score = probabilities[0][1].item() 
                label_idx = torch.argmax(probabilities, dim=1).item()

            if not self.is_ready:
                return 0.85, "Simulation Mode"

            label = "Real" if label_idx == 1 else "Fake/Spoof"
            return score, f"{label} ({score:.2f})"

        except Exception as e:
            return 0.0, f"Error: {e}"

if __name__ == "__main__":
    detector = DeepTextureLiveness(model_path="models/liveness_model.pth")
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_box = [100, 100, 300, 300]
    score, msg = detector.predict(dummy_frame, dummy_box)
    print(f"Test Result: {msg}")
