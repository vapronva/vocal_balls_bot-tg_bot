from config import Config, AvailableLanguages
from VoskAPI import VoskAPI
import threading
import asyncio
from pathlib import Path
import logging
from pyrogram import Client as BotClient  # type: ignore
from pyrogram import filters as PyrogramFilters
from appwrite.client import Client as AppWriteClient
from appwrite.services.users import Users as AppWriteUsers
from appwrite.exception import AppwriteException
from models import UserModel
import audioread
import uuid
import sys
from utils import Utils
from ReCasePuncAPI import RecasepuncAPI


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


@bot.on_message(PyrogramFilters.voice & PyrogramFilters.private)
def on_voice_message_private(_, message):
    INTERNAL_ID = f"tlgrm-vocalballsbot-{message.from_user.id}"
    try:
        USER: UserModel = UserModel(**APPWRITEUSERS.get(user_id=INTERNAL_ID))
    except AppwriteException:
        USER: UserModel = UserModel(**APPWRITEUSERS.create(user_id=INTERNAL_ID))
    USER.prefs.statistics.messagesReceived += 1
    initialLanguage: AvailableLanguages = USER.prefs.language
    logging.info("Received voice message from user: %s", message.from_user.id)
    botRepliedMessage = message.reply_text(
        "__💬 Received your voice message...__", quote=True
    )
    vosk = VoskAPI(
        apiKey=CONFIG.get_vosk_api_key(),
        language=initialLanguage,
    )
    outputFile = Path(f"files_download/{uuid.uuid4().__str__().replace('-', '')}.ogg")
    message.download(file_name=outputFile.__str__())
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
    botRepliedMessage.edit_text(text="__🔁 Processing your voice message...__")
    threadProcessor.join()
    threadTelegramMessageEditor.join()
    results = vosk.get_results()
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
    outputFile.unlink()
    USER.name = (
        f"{message.from_user.first_name} {message.from_user.last_name} (@{message.from_user.username})"
        if message.from_user.username is not None
        else f"{message.from_user.first_name} {message.from_user.last_name} (null)"
    )
    USER.prefs.recasepunc = False
    APPWRITEUSERS.update_name(user_id=INTERNAL_ID, name=USER.name)
    APPWRITEUSERS.update_prefs(user_id=INTERNAL_ID, prefs=USER.prefs.dict())
    logging.info("User information: %s", USER.dict())
    if results is None or len(results) == 0:
        botRepliedMessage.edit_text(text="__⚠️ No words recognized!__")
        return
    Utils.send_stt_result_with_respecting_max_message_length(
        message,
        botRepliedMessage,
        vosk,
        RCPAPI if USER.prefs.recasepunc else None,
        USER.prefs.howManyDigitsAfterDot,
        initialLanguage,
    )


if __name__ == "__main__":
    try:
        bot.run()
    except KeyboardInterrupt:
        logging.info("Exiting the program due to KeyboardInterrupt")
        sys.exit(0)
