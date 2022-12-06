from config import Config, AvailableLanguages
import logging
from pyrogram import Client as BotClient  # type: ignore
from pyrogram import filters as PyrogramFilters
from pyrogram.types import Message as PyrogramMessage
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
import sys
from utils import Utils
from Locale import LOCALE
from SpeechToTextPipeline import STTPipeline, MESSAGE_TYPES_FILTRED


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
        USER: UserModel = UserModel(
            **APPWRITEUSERS.get(user_id=INTERNAL_ID)  # type: ignore
        )
    except AppwriteException:
        USER: UserModel = UserModel(
            **APPWRITEUSERS.create(user_id=INTERNAL_ID)  # type: ignore
        )
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
def on_voice_message_private(_, message: PyrogramMessage) -> None:
    STTP = STTPipeline(
        messageType=MESSAGE_TYPES_FILTRED.VOICE,
        message=message,
        user=get_user(message.from_user.id),
        config=CONFIG,
    )
    APPWRITEUSERS.update_prefs(
        user_id=f"tlgrm-vocalballsbot-{message.from_user.id}",
        prefs=STTP.get_user().prefs.dict(),
    )
    STTP.run()
    STTP.analytics(get_user(message.from_user.id))
    APPWRITEUSERS.update_prefs(
        user_id=f"tlgrm-vocalballsbot-{message.from_user.id}",
        prefs=STTP.get_user().prefs.dict(),
    )
    APPWRITEUSERS.update_name(
        user_id=f"tlgrm-vocalballsbot-{message.from_user.id}", name=STTP.get_user().name
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
        elif (
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
        elif (
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
        elif (
            callback.actionType == CallbackQueryActionTypes.ACTION
            and callback.actionObject == CallbackQueryActionsObjects.SENDSUBTITLES
            and callback.actionValue == CallbackQueryActionsValues.TOGGLE
            and not callback.actionValue == CallbackQueryActionsValues.NOTHING
        ):
            USER.prefs.sendSubtitles = bool(USER.prefs.sendSubtitles ^ True)
            logging.debug(
                "SendSubtitles changed to `%s` for user #%s",
                USER.prefs.sendSubtitles,
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
    except Exception as e:
        logging.error("Error while processing the whole callback: %s", e)
        return


if __name__ == "__main__":
    try:
        bot.run()
    except KeyboardInterrupt:
        logging.debug("Exiting the program due to KeyboardInterrupt")
        sys.exit(0)
