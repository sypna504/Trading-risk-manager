from ..config import settings
from .model_predictor import ModelPredictor


predictor = ModelPredictor(
    model_path=settings.MODEL_PATH,
    config_path=settings.MODEL_CONFIG_PATH,
    registry_path=settings.MODEL_REGISTRY_PATH,
    models_root=settings.MODELS_ROOT,
)
