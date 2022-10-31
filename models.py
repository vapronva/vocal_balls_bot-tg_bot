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

    def fix_result_apostrophe(self) -> Optional[str]:
        if self.result is not None:
            self.result = (
                self.result.replace(" ' ", "'")
                .replace(" ? ", "?")
                .replace(" ?", "?")
                .replace(" ! ", "!")
                .replace(" !", "!")
                .replace(" , ", ", ")
                .replace(" . ", ". ")
                .replace(" .", ".")
            )
        return self.result
