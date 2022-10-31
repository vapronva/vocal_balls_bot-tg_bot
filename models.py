from typing import List, Optional
from pydantic import BaseModel, NonNegativeFloat
from config import AvailableLanguages


class SpeechRecognitionVoskPartialResult(BaseModel):
    text: str
    startTime: NonNegativeFloat
    endTime: NonNegativeFloat
    overallConfidence: float


class RecasepuncRequestBodyModel(BaseModel):
    text: str
    lang: AvailableLanguages


class RecasepuncResponseModel(BaseModel):
    error: Optional[dict]
    result: Optional[str]
