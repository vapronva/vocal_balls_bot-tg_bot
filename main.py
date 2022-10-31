from config import Config, AvailableLanguages
from VoskAPI import VoskAPI
import threading
import asyncio
from pathlib import Path
import time
import logging
from pyrogram import Client as BotClient  # type: ignore
from pyrogram import filters as PyrogramFilters
import uuid
from utils import Utils


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


def show_results_as_they_come(voskAPI: VoskAPI) -> None:
    lastResult = None
    while True:
        logging.info(
            voskAPI.get_result()
        ) if voskAPI.get_result() != lastResult else None
        lastResult = voskAPI.get_result()
        if voskAPI.get_finished_status():
            break
        time.sleep(0.5)


@bot.on_message(PyrogramFilters.voice & PyrogramFilters.private)
def on_voice_message_private(client, message):
    logging.info("Received voice message from user: %s", message.from_user.id)
    vosk = VoskAPI(
        apiKey=CONFIG.get_vosk_api_key(),
        language=AvailableLanguages.RU,
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
    threadProcessor.start()
    threadProcessor.join()
    results = vosk.get_results()
    if results is None or len(results) == 0:
        message.reply_text("No results", quote=True)
    message.reply_text(text=Utils.get_formatted_stt_result(results), quote=True)


if __name__ == "__main__":
    try:
        bot.run()
    except KeyboardInterrupt:
        logging.info("Exiting the program due to KeyboardInterrupt")
        exit(0)
