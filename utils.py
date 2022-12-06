from typing import List, Optional
from VoskAPI import VoskAPI
from models import (
    SpeechRecognitionVoskPartialResult,
    RecasepuncRequestBodyModel,
    UserModel,
    CallbackQueryDataModel,
    CallbackQueryActionTypes,
    CallbackQueryActionsObjects,
    CallbackQueryActionsValues,
)
from pyrogram.types import Message as PyrogramMessage
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors.exceptions.bad_request_400 import MessageNotModified
import time
import logging
from pathlib import Path
import uuid
from ReCasePuncAPI import RecasepuncAPI
from config import AvailableLanguages
from Locale import LOCALE


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
        message: PyrogramMessage,
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
                        resText = resText[:4036] + "..."
                        resText += f"\n\n__⏳ {LOCALE.get(vosk.get_language(), 'fullMessageAfterProcessing')}...__"
                    _ = message.edit_text(text=resText)
                except MessageNotModified:
                    logging.warning("Message not modified for message #%s", message.id)
                    checkEvery = 10
            lastResult = vosk.get_result()
            if vosk.get_finished_status():
                logging.info(
                    "Finished processing audio file for message #%s", message.id
                )
                break
            time.sleep(checkEvery)

    @staticmethod
    def send_stt_result_with_respecting_max_message_length(
        message: PyrogramMessage,
        initialMessage: PyrogramMessage,
        vosk: VoskAPI,
        user: UserModel,
        rcpapi: Optional[RecasepuncAPI] = None,
        language: AvailableLanguages = AvailableLanguages.RU,
        textLimitPerMessage: int = 4096,
    ) -> None:
        results = vosk.get_results()
        resultingText = Utils.get_formatted_stt_result(
            results,
            rcpapi=rcpapi,
            language=language,
            digitsAfterDot=user.prefs.howManyDigitsAfterDot,
        )
        textToSend: List[str] = []
        if len(resultingText) >= textLimitPerMessage:
            currentPart = ""
            for line in resultingText.splitlines():
                if len(currentPart) + len(line) >= textLimitPerMessage:
                    textToSend.append(currentPart)
                    currentPart = ""
                currentPart += line + "\n"
            textToSend.append(currentPart)
        else:
            textToSend.append(resultingText)
        logging.debug(
            "Total resulting messages amount for user #%s and message #%s: %s",
            user.id,
            message.id,
            len(textToSend),
        )
        if user.prefs.sendBigTextAsFile and len(textToSend) > 1:
            outputFile: Path = (
                Path("files_download")
                / f"{user.id.replace('-', '')}-{uuid.uuid4().__str__().replace('-', '')}.txt"
            )
            with open(outputFile, "w") as f:
                f.write(resultingText)
            _ = message.reply_document(
                document=outputFile.__str__(),
                caption=f"📄 __{LOCALE.get(user.prefs.language, 'messageSentAsAFile')}__",
                file_name=outputFile.name,
                quote=True,
            )
            outputFile.unlink()
            _ = initialMessage.delete()
            logging.debug(
                "Sent STT'ed text as a file for user #%s and message #%s",
                user.id,
                message.id,
            )
            return
        for text in textToSend:
            if text == textToSend[0]:
                try:
                    _ = initialMessage.edit_text(text=text)
                except MessageNotModified:
                    logging.warning(
                        "Initial message not modified for message #%s", message.id
                    )
            else:
                _ = message.reply_text(
                    text=text,
                    quote=True,
                    disable_web_page_preview=True,
                    disable_notification=True,
                )
                time.sleep(0.5)
        return

    @staticmethod
    def generate_settings_keyboard(
        user: UserModel, telegramUserID: int
    ) -> InlineKeyboardMarkup:
        resultingKeyboard: List[List[InlineKeyboardButton]] = []
        resultingKeyboard.append(
            [
                InlineKeyboardButton(
                    f"🔊 {LOCALE.get(user.prefs.language, 'settingsLanguage')}",
                    callback_data=f"vclblls-sttc-lang-none-{telegramUserID}",
                )
            ]
        )
        secondRow: List[InlineKeyboardButton] = []
        for language in [AvailableLanguages.RU, AvailableLanguages.EN]:
            secondRow.append(
                InlineKeyboardButton(
                    f"{'✅ ' if user.prefs.language == language else ''}{LOCALE.get(user.prefs.language, 'settingsLanguageRussian') if language == AvailableLanguages.RU else LOCALE.get(user.prefs.language, 'settingsLanguageEnglish')}",
                    callback_data=f"vclblls-actn-lang-{language.value}-{telegramUserID}",
                )
            )
        resultingKeyboard.append(secondRow)
        resultingKeyboard.append(
            [
                InlineKeyboardButton(
                    f"📝 {LOCALE.get(user.prefs.language, 'settingsPunctuation')}",
                    callback_data=f"vclblls-sttc-punc-none-{telegramUserID}",
                )
            ]
        )
        resultingKeyboard.append(
            [
                InlineKeyboardButton(
                    f"{LOCALE.get(user.prefs.language, 'settingsPunctuationOn') if user.prefs.recasepunc else LOCALE.get(user.prefs.language, 'settingsPunctuationOff')} {'✅' if user.prefs.recasepunc else '❌'}",
                    callback_data=f"vclblls-actn-punc-toggle-{telegramUserID}",
                )
            ]
        )
        resultingKeyboard.append(
            [
                InlineKeyboardButton(
                    f"📑 {LOCALE.get(user.prefs.language, 'settingSendBigTextAsFile')}",
                    callback_data=f"vclblls-sttc-sbta-none-{telegramUserID}",
                )
            ]
        )
        resultingKeyboard.append(
            [
                InlineKeyboardButton(
                    f"{LOCALE.get(user.prefs.language, 'settingSendBigTextAsFileOn') if user.prefs.sendBigTextAsFile else LOCALE.get(user.prefs.language, 'settingSendBigTextAsFileOff')} {'✅' if user.prefs.sendBigTextAsFile else '❌'}",
                    callback_data=f"vclblls-actn-sbta-toggle-{telegramUserID}",
                )
            ]
        )
        resultingKeyboard.append(
            [
                InlineKeyboardButton(
                    f"💬 {LOCALE.get(user.prefs.language, 'settingSendSubtitles')}",
                    callback_data=f"vclblls-sttc-ssub-none-{telegramUserID}",
                )
            ]
        )
        resultingKeyboard.append(
            [
                InlineKeyboardButton(
                    f"{LOCALE.get(user.prefs.language, 'settingSendSubtitlesOn') if user.prefs.sendSubtitles else LOCALE.get(user.prefs.language, 'settingSendSubtitlesOff')} {'✅' if user.prefs.sendSubtitles else '❌'}",
                    callback_data=f"vclblls-actn-ssub-toggle-{telegramUserID}",
                )
            ]
        )
        return InlineKeyboardMarkup(resultingKeyboard)

    @staticmethod
    def generate_statistics_text(user: UserModel) -> str:
        return f"""<b>{LOCALE.get(user.prefs.language, 'settingsHowMany')}</b>
- <code>{user.prefs.statistics.messagesProcessed}</code> {LOCALE.get(user.prefs.language, 'settingsHowManyMessagesProcessed')}
- <code>{user.prefs.statistics.charactersProcessed}</code> {LOCALE.get(user.prefs.language, 'settingsHowManyCharactersProcessed')}
- <code>{user.prefs.statistics.secondsOfAudioProcessed}</code> {LOCALE.get(user.prefs.language, 'settingsHowManySecondsOfAudioProcessed')}"""

    @staticmethod
    def check_callback_query(
        callbackQuery: CallbackQuery,
    ) -> Optional[CallbackQueryDataModel]:
        try:
            (
                botName,
                actionType,
                actionObject,
                actionValue,
                telegramUserId,
            ) = callbackQuery.data.__str__().split("-")
        except ValueError:
            return None
        if botName != "vclblls":
            return None
        try:
            data = CallbackQueryDataModel(
                actionType=CallbackQueryActionTypes(actionType),
                actionObject=CallbackQueryActionsObjects(actionObject),
                actionValue=CallbackQueryActionsValues(actionValue),
                telegramUserId=int(telegramUserId),
            )
        except ValueError:
            return None
        except AttributeError:
            return None
        if (
            data.actionType == CallbackQueryActionTypes.ACTION
            and data.actionValue == CallbackQueryActionsValues.NOTHING
        ):
            return None
        if data.actionType == CallbackQueryActionTypes.STATIC:
            return None
        return data
