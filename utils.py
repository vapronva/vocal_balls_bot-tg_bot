from typing import List
from models import SpeechRecognitionVoskPartialResult


class Utils:
    @staticmethod
    def get_formatted_stt_result(
        results: List[SpeechRecognitionVoskPartialResult], digitsAfterDot: int = 1
    ) -> str:
        resultingString: str = ""
        for partialResult in results:
            resultingString += f"""__{round(partialResult.startTime, digitsAfterDot) if int(partialResult.startTime) != 0 else int(partialResult.startTime)} → {round(partialResult.endTime, digitsAfterDot)}:__
{partialResult.text}
"""
        return resultingString
