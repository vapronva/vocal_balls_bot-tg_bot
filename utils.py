from typing import List, Optional
from VoskAPI import VoskAPI
from models import (
    SpeechRecognitionVoskPartialResult,
    RecasepuncRequestBodyModel,
)
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
                    resText = Utils.get_formatted_stt_result(results, digitsAfterDot)
                    if len(resText) >= 4096:
                        resText = resText[:4000] + "..."
                        resText += (
                            "\n\n__⏳ Full message will be sent after processing...__"
                        )
                    message.edit_text(text=resText)
                except MessageNotModified:
                    logging.warning("Message not modified for #%s", message.id)
            lastResult = vosk.get_result()
            if vosk.get_finished_status():
                logging.info("Finished processing audio file for #%s", message.id)
                break
            time.sleep(checkEvery)

    @staticmethod
    def send_stt_result_with_respecting_max_message_length(
        message: PyrogramTypeMessage,
        initialMessage: PyrogramTypeMessage,
        vosk: VoskAPI,
        rcpapi: Optional[RecasepuncAPI] = None,
        digitsAfterDot: int = 1,
        language: AvailableLanguages = AvailableLanguages.RU,
    ) -> None:
        results = vosk.get_results()
        resultingText = Utils.get_formatted_stt_result(
            results, rcpapi=rcpapi, language=language, digitsAfterDot=digitsAfterDot
        )
        textToSend: List[str] = []
        if len(resultingText) >= 4096:
            currentPart = ""
            for line in resultingText.splitlines():
                if len(currentPart) + len(line) >= 4096:
                    textToSend.append(currentPart)
                    currentPart = ""
                currentPart += line + "\n"
            textToSend.append(currentPart)
        else:
            textToSend.append(resultingText)
        for text in textToSend:
            if text == textToSend[0]:
                try:
                    initialMessage.edit_text(text=text)
                except MessageNotModified:
                    logging.warning("Message not modified for #%s", message.id)
            else:
                message.reply_text(text=text, quote=True)
                time.sleep(0.5)
