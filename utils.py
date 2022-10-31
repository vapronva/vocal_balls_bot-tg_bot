from typing import List, Optional
from VoskAPI import VoskAPI
from models import SpeechRecognitionVoskPartialResult, RecasepuncRequestBodyModel
from pyrogram.types import Message as PyrogramTypeMessage
from pyrogram.errors.exceptions.bad_request_400 import MessageNotModified
import time
import logging
from ReCasePuncAPI import RecasepuncAPI
from config import AvailableLanguages


class Utils:
    @staticmethod
    def get_formatted_stt_result(
        results: List[SpeechRecognitionVoskPartialResult],
        digitsAfterDot: int = 1,
        rcpapi: Optional[RecasepuncAPI] = None,
        language: AvailableLanguages = AvailableLanguages.RU,
    ) -> str:
        resultingString: str = ""
        for partialResult in results:
            try:
                formattedText = (
                    partialResult.text
                    if not rcpapi
                    else rcpapi.make_request(
                        RecasepuncRequestBodyModel(
                            text=partialResult.text, lang=language
                        )
                    ).fix_result_apostrophe()  # type: ignore
                )
            except AttributeError:
                formattedText = partialResult.text
            resultingString += f"""__{round(partialResult.startTime, digitsAfterDot) if int(partialResult.startTime) != 0 else int(partialResult.startTime)} → {round(partialResult.endTime, digitsAfterDot)}:__
{formattedText}
"""
        return resultingString

    @staticmethod
    def update_stt_result_as_everything_comes_in(
        message: PyrogramTypeMessage,
        vosk: VoskAPI,
        digitsAfterDot: int = 1,
        checkEvery: float = 2,
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
            time.sleep(checkEvery)
