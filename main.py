from config import Config, AvailableLanguages
from VoskAPI import VoskAPI
import threading
import asyncio
from pathlib import Path
import logging
from pyrogram import Client as BotClient  # type: ignore
from pyrogram import filters as PyrogramFilters
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


@bot.on_message(PyrogramFilters.voice & PyrogramFilters.private)
def on_voice_message_private(_, message):
    initialLanguage: AvailableLanguages = AvailableLanguages.RU
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
        ),
    )
    threadProcessor.start()
    threadTelegramMessageEditor.start()
    botRepliedMessage.edit_text(text="__🔁 Processing your voice message...__")
    threadProcessor.join()
    threadTelegramMessageEditor.join()
    results = vosk.get_results()
    outputFile.unlink()
    if results is None or len(results) == 0:
        botRepliedMessage.edit_text(text="__⚠️ No words recognized!__")
        return
    Utils.send_stt_result_with_respecting_max_message_length(
        message, botRepliedMessage, vosk, RCPAPI, 1, initialLanguage
    )


if __name__ == "__main__":
    try:
        bot.run()
    except KeyboardInterrupt:
        logging.info("Exiting the program due to KeyboardInterrupt")
        sys.exit(0)
