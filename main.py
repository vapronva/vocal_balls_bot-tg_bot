from config import Config, AvailableLanguages
from VoskAPI import VoskAPI
import threading
import asyncio
from pathlib import Path
import time
import logging


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def show_results_as_they_come(voskAPI: VoskAPI) -> None:
    lastResult = None
    while True:
        logging.info(voskAPI.get_result()) if voskAPI.get_result() != lastResult else None
        lastResult = voskAPI.get_result()
        if voskAPI.get_finished_status():
            break
        time.sleep(0.5)


def main():
    config = Config()
    vosk = VoskAPI(
        apiKey=config.get_vosk_api_key(),
        language=AvailableLanguages.EN,
    )
    threadProcessor = threading.Thread(
        target=asyncio.run,
        args=(
            vosk.process_audio_file(
                audioFile=Path("eeddebaa-1197-4f89-a1f9-d81bdb9c6e77.mp3"),
                bytesToReadEveryTime=128000,
            ),
        ),
    )
    threadResultsPrinter = threading.Thread(
        target=show_results_as_they_come, args=(vosk,)
    )
    threadProcessor.start()
    threadResultsPrinter.start()
    threadProcessor.join()
    threadResultsPrinter.join()
    logging.info(vosk.get_results())


if __name__ == "__main__":
    main()
