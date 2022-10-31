from pydantic import BaseModel, NonNegativeFloat


class SpeechRecognitionVoskPartialResult(BaseModel):
    text: str
    startTime: NonNegativeFloat
    endTime: NonNegativeFloat
    overallConfidence: float
