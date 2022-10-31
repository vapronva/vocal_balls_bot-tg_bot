from typing import List
from VoskAPI import VoskAPI
from models import SpeechRecognitionVoskPartialResult
from pyrogram.types import Message as PyrogramTypeMessage
from pyrogram.errors.exceptions.bad_request_400 import MessageNotModified
import time
import logging


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

    @staticmethod
    def update_stt_result_as_everything_comes_in(
        message: PyrogramTypeMessage,
        vosk: VoskAPI,
        digitsAfterDot: int = 1,
    ) -> None:
        lastResult = None
        while True:
            results = vosk.get_results()
            if results is not None and len(results) > 0 and lastResult != results[-1]:
                try:
                    message.edit_text(
                        text=Utils.get_formatted_stt_result(results, digitsAfterDot)
                    )
                except MessageNotModified:
                    logging.warning("Message not modified for #%s", message.id)
            lastResult = vosk.get_result()
            if vosk.get_finished_status():
                logging.info("Finished processing audio file for #%s", message.id)
                break
            time.sleep(3)
