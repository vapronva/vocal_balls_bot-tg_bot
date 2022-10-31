from pathlib import Path
from typing import List, Optional
import websockets
from config import AvailableLanguages, Config
from models import SpeechRecognitionVoskPartialResult
import asyncio
import websockets
import json
import threading
import time


class VoskAPI:
    def __init__(self, apiKey: str, language: AvailableLanguages) -> None:
        self.__ENDPOINT = Config.get_vosk_endpoint(language)
        self.__APIKEY = apiKey
        self.__LANGUAGE = language
        self.__RESULTS: List[SpeechRecognitionVoskPartialResult] = []
        self.__FINISHED_STATUS: bool = False

    def __get_headers(self) -> list:
        return [["X-API-Key", self.__APIKEY]]

    def __get_vosk_server_config_message(self) -> dict:
        return {"config": {"sample_rate": 16000}}

    def __get_vosk_server_eof_message(self) -> dict:
        return {"eof": 1}

    def __get_vosk_server_message(self, data: bytes) -> bytes:
        return data

    def __get_ffmpeg_arguments(self, audioFile: Path) -> list:
        return [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "quiet",
            "-i",
            audioFile.__str__(),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-f",
            "s16le",
            "-",
        ]

    def __parse_response(
        self, response: str
    ) -> Optional[SpeechRecognitionVoskPartialResult]:
        try:
            data = json.loads(response)
            if "result" in data:
                confidence = sum([word["conf"] for word in data["result"]]) / len(
                    data["result"]
                )
                startTime = data["result"][0]["start"]
                endTime = data["result"][-1]["end"]
                text = data["text"]
                return SpeechRecognitionVoskPartialResult(
                    overallConfidence=confidence,
                    startTime=startTime,
                    endTime=endTime,
                    text=text,
                )
            return None
        except json.JSONDecodeError:
            return None
        except KeyError:
            return None

    def __add_result(
        self, result: Optional[SpeechRecognitionVoskPartialResult]
    ) -> None:
        if result is not None:
            self.__RESULTS.append(result)

    def get_results(self) -> List[SpeechRecognitionVoskPartialResult]:
        return self.__RESULTS

    def get_result(
        self, index: int = -1
    ) -> Optional[SpeechRecognitionVoskPartialResult]:
        try:
            return self.__RESULTS[index]
        except IndexError:
            return None

    def get_finished_status(self) -> bool:
        return self.__FINISHED_STATUS

    def __set_finished_status(self, status: bool) -> None:
        self.__FINISHED_STATUS = status

    async def process_audio_file(self, audioFile: Path) -> None:
        async with websockets.connect(
            self.__ENDPOINT, extra_headers=self.__get_headers()
        ) as websocket:
            proc = await asyncio.create_subprocess_exec(
                *self.__get_ffmpeg_arguments(audioFile),
                stdout=asyncio.subprocess.PIPE,
            )
            await websocket.send(json.dumps(self.__get_vosk_server_config_message()))
            while True:
                data = await proc.stdout.read(8000)
                if len(data) == 0:
                    break
                await websocket.send(self.__get_vosk_server_message(data))
                self.__add_result(self.__parse_response(await websocket.recv()))
            await websocket.send('{"eof" : 1}')
            self.__add_result(self.__parse_response(await websocket.recv()))
            await proc.wait()
            self.__set_finished_status(True)


def show_results_as_they_come(voskAPI: VoskAPI) -> None:
    while True:
        print(voskAPI.get_result())
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
            vosk.process_audio_file(Path("eeddebaa-1197-4f89-a1f9-d81bdb9c6e77.mp3")),
        ),
    )
    threadResultsPrinter = threading.Thread(
        target=show_results_as_they_come, args=(vosk,)
    )
    threadProcessor.start()
    threadResultsPrinter.start()
    threadProcessor.join()
    threadResultsPrinter.join()
    print(vosk.get_results())


if __name__ == "__main__":
    main()
