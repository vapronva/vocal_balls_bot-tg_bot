from config import Config, AvailableLanguages
from VoskAPI import VoskAPI
import threading
import asyncio
from pathlib import Path
import logging
from pyrogram import Client as BotClient  # type: ignore
from pyrogram import filters as PyrogramFilters
from pyrogram.errors import MessageNotModified
from appwrite.client import Client as AppWriteClient
from appwrite.services.users import Users as AppWriteUsers
from appwrite.exception import AppwriteException
from models import (
    UserModel,
    CallbackQueryActionTypes,
    CallbackQueryActionsObjects,
    CallbackQueryActionsValues,
)
import audioread
import time
import uuid
import sys
from utils import Utils
from ReCasePuncAPI import RecasepuncAPI
from Locale import LOCALE


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

CONFIG = Config()

bot = BotClient(
    name="vocal_balls_bot-testing_1",
    api_id=CONFIG.get_telegram_api_id(),
    api_hash=CONFIG.get_telegram_api_hash(),
    bot_token=CONFIG.get_telegram_bot_token(),
    workers=CONFIG.get_telegram_bot_workers(),
)

RCPAPI = RecasepuncAPI(
    endpointBase=CONFIG.get_vprw_rcpapi_endpoint(), apiKey=CONFIG.get_vprw_rcpapi_key()
)

APPWRITECLIENT = AppWriteClient()
(
    APPWRITECLIENT.set_endpoint(CONFIG.get_appwrite_api_endpoint())
    .set_project(CONFIG.get_appwrite_project_id())
    .set_key(CONFIG.get_appwrite_api_key())
)
APPWRITEUSERS = AppWriteUsers(APPWRITECLIENT)


def get_user(user_id: int) -> UserModel:
    INTERNAL_ID = f"tlgrm-vocalballsbot-{user_id}"
    try:
        USER: UserModel = UserModel(**APPWRITEUSERS.get(user_id=INTERNAL_ID))
    except AppwriteException:
        USER: UserModel = UserModel(**APPWRITEUSERS.create(user_id=INTERNAL_ID))
        APPWRITEUSERS.update_prefs(
            user_id=f"tlgrm-vocalballsbot-{user_id}",
            prefs=USER.prefs.dict(),
        )
    return USER


@bot.on_message(PyrogramFilters.command("settings") & PyrogramFilters.private)
def on_settings_command(_, message) -> None:
    USER = get_user(message.from_user.id)
    message.reply_text(
        f"<b>{LOCALE.get(USER.prefs.language, 'settings')}</b> <i>(ID: <code>{USER.id}</code>)</i>",
        quote=True,
        reply_markup=Utils.generate_settings_keyboard(USER, message.from_user.id),
    )
    return


@bot.on_message(PyrogramFilters.command("stats") & PyrogramFilters.private)
def on_stats_command(_, message) -> None:
    USER = get_user(message.from_user.id)
    message.reply_text(
        Utils.generate_statistics_text(USER), quote=True, disable_web_page_preview=True
    )
    return


@bot.on_message(PyrogramFilters.voice & PyrogramFilters.private)
def on_voice_message_private(_, message) -> None:
    USER = get_user(message.from_user.id)
    USER.prefs.statistics.messagesReceived += 1
    APPWRITEUSERS.update_prefs(
        user_id=f"tlgrm-vocalballsbot-{message.from_user.id}", prefs=USER.prefs.dict()
    )
    initialLanguage: AvailableLanguages = USER.prefs.language
    logging.info(
        "Received voice message from user #%s for message ID #%s",
        message.from_user.id,
        message.id,
    )
    botRepliedMessage = message.reply_text(
        f"__💬 {LOCALE.get(USER.prefs.language, 'voiceMessageReceived')}...__",
        quote=True,
    )
    vosk = VoskAPI(
        apiKey=CONFIG.get_vosk_api_key(),
        language=initialLanguage,
    )
    outputFile = Path(f"files_download/{uuid.uuid4().__str__().replace('-', '')}.ogg")
    try:
        message.download(file_name=outputFile.__str__())
    except Exception as e:
        logging.error(
            "Error while downloading file for user #%s for message #%s: %s",
            message.from_user.id,
            message.id,
            e,
        )
        botRepliedMessage.edit_text(
            f"__❌ {LOCALE.get(USER.prefs.language, 'errorWhileDownloading')}__\n\n```{e}```"
        )
        return
    threadProcessor = threading.Thread(
        target=asyncio.run,
        args=(
            vosk.process_audio_file(
                audioFile=outputFile,
                bytesToReadEveryTime=64000,
            ),
        ),
    )
    threadTelegramMessageEditor = threading.Thread(
        target=Utils.update_stt_result_as_everything_comes_in,
        args=(
            botRepliedMessage,
            vosk,
            USER.prefs.howManyDigitsAfterDot,
        ),
    )
    threadProcessor.start()
    threadTelegramMessageEditor.start()
    botRepliedMessage.edit_text(
        text=f"__🔁 {LOCALE.get(USER.prefs.language, 'voiceMessageProcessing')}...__"
    )
    threadProcessor.join()
    threadTelegramMessageEditor.join()
    results = vosk.get_results()
    if results is None or len(results) == 0:
        botRepliedMessage.edit_text(
            text=f"__⚠️ {LOCALE.get(USER.prefs.language, 'noWordsFound')}!__"
        )
        return
    Utils.send_stt_result_with_respecting_max_message_length(
        message=message,
        initialMessage=botRepliedMessage,
        vosk=vosk,
        user=USER,
        rcpapi=RCPAPI if USER.prefs.recasepunc else None,
        language=initialLanguage,
    )
    startTimeAnalytics = time.time()
    USER = get_user(message.from_user.id)
    if USER.prefs.participateInStatistics:
        USER.prefs.statistics.processedWithLanguage[initialLanguage.value] += 1
        USER.prefs.statistics.messagesProcessed += 1
        USER.prefs.statistics.charactersProcessed += sum(
            len(resultResult.text) for resultResult in results
        )
        fileOggType = audioread.audio_open(outputFile.__str__())
        USER.prefs.statistics.secondsOfAudioProcessed += (
            int(fileOggType.duration) if fileOggType.duration else 0
        )
    APPWRITEUSERS.update_prefs(
        user_id=f"tlgrm-vocalballsbot-{message.from_user.id}", prefs=USER.prefs.dict()
    )
    USER.name = (
        f"{message.from_user.first_name} {message.from_user.last_name} (@{message.from_user.username})"
        if message.from_user.username is not None
        else f"{message.from_user.first_name} {message.from_user.last_name} (null)"
    )
    APPWRITEUSERS.update_name(
        user_id=f"tlgrm-vocalballsbot-{message.from_user.id}", name=USER.name
    )
    outputFile.unlink()
    logging.info(
        "Processed voice message analytics and cleaned up for user #%s for message ID #%s in %s seconds",
        message.from_user.id,
        message.id,
        time.time() - startTimeAnalytics,
    )
    return


@bot.on_callback_query()
def on_callback(_, callbackQuery) -> None:
    callback = Utils.check_callback_query(callbackQuery)
    if callback is None:
        return
    if callback.telegramUserId != callbackQuery.from_user.id:
        return
    USER = get_user(callbackQuery.from_user.id)
    try:
        if (
            callback.actionType == CallbackQueryActionTypes.ACTION
            and callback.actionObject == CallbackQueryActionsObjects.LANGUAGE
            and not callback.actionValue == CallbackQueryActionsValues.NOTHING
        ):
            USER.prefs.language = AvailableLanguages(callback.actionValue.value)
            logging.debug(
                "Language changed to `%s` for user #%s", USER.prefs.language, USER.id
            )
            APPWRITEUSERS.update_prefs(
                user_id=f"tlgrm-vocalballsbot-{callbackQuery.from_user.id}",
                prefs=USER.prefs.dict(),
            )
            try:
                callbackQuery.edit_message_text(
                    text=f"<b>{LOCALE.get(USER.prefs.language, 'settings')}</b> <i>(ID: <code>{USER.id}</code>)</i>",
                    reply_markup=Utils.generate_settings_keyboard(
                        USER, callbackQuery.from_user.id
                    ),
                )
            except MessageNotModified:
                pass
            return
        if (
            callback.actionType == CallbackQueryActionTypes.ACTION
            and callback.actionObject == CallbackQueryActionsObjects.PUNCTUATION
            and callback.actionValue == CallbackQueryActionsValues.TOGGLE
            and not callback.actionValue == CallbackQueryActionsValues.NOTHING
        ):
            USER.prefs.recasepunc = bool(USER.prefs.recasepunc ^ True)
            logging.debug(
                "Punctuation changed to `%s` for user #%s",
                USER.prefs.recasepunc,
                USER.id,
            )
            APPWRITEUSERS.update_prefs(
                user_id=f"tlgrm-vocalballsbot-{callbackQuery.from_user.id}",
                prefs=USER.prefs.dict(),
            )
            try:
                callbackQuery.edit_message_text(
                    text=f"<b>{LOCALE.get(USER.prefs.language, 'settings')}</b> <i>(ID: <code>{USER.id}</code>)</i>",
                    reply_markup=Utils.generate_settings_keyboard(
                        USER, callbackQuery.from_user.id
                    ),
                )
            except MessageNotModified:
                pass
            return
        if (
            callback.actionType == CallbackQueryActionTypes.ACTION
            and callback.actionObject == CallbackQueryActionsObjects.SENDBIGTEXTASFILE
            and callback.actionValue == CallbackQueryActionsValues.TOGGLE
            and not callback.actionValue == CallbackQueryActionsValues.NOTHING
        ):
            USER.prefs.sendBigTextAsFile = bool(USER.prefs.sendBigTextAsFile ^ True)
            logging.debug(
                "SendBigTextFile changed to `%s` for user #%s",
                USER.prefs.sendBigTextAsFile,
                USER.id,
            )
            APPWRITEUSERS.update_prefs(
                user_id=f"tlgrm-vocalballsbot-{callbackQuery.from_user.id}",
                prefs=USER.prefs.dict(),
            )
            try:
                callbackQuery.edit_message_text(
                    text=f"<b>{LOCALE.get(USER.prefs.language, 'settings')}</b> <i>(ID: <code>{USER.id}</code>)</i>",
                    reply_markup=Utils.generate_settings_keyboard(
                        USER, callbackQuery.from_user.id
                    ),
                )
            except MessageNotModified:
                pass
            return
        return
    except Exception as e:
        logging.error("Error while processing the whole callback: %s", e)
        return


if __name__ == "__main__":
    try:
        bot.run()
    except KeyboardInterrupt:
        logging.debug("Exiting the program due to KeyboardInterrupt")
        sys.exit(0)
