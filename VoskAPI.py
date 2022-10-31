from pathlib import Path
from typing import List, Optional
import websockets
from config import AvailableLanguages, Config
from models import SpeechRecognitionVoskPartialResult
import asyncio
import json
import time
import logging


class VoskAPI:
    def __init__(self, apiKey: str, language: AvailableLanguages) -> None:
        self.__ENDPOINT = Config.get_vosk_endpoint(language)
        self.__APIKEY = apiKey
        self.__LANGUAGE = language
        self.__RESULTS: List[SpeechRecognitionVoskPartialResult] = []
        self.__FINISHED_STATUS: bool = False
        logging.debug("Initialized VoskAPI with endpoint: %s", self.__ENDPOINT)

    def __get_headers(self) -> list:
        return [["X-API-Key", self.__APIKEY]]

    @staticmethod
    def __get_vosk_server_config_message(
        maxAlternatives: int = 20,
        sampleRate: int = 16000,
        altFormat: bool = False,
    ) -> dict:
        return (
            {"config": {"sample_rate": 16000}}
            if not altFormat
            else {
                "config": {
                    "max_alternatives": maxAlternatives,
                    "sample_rate": sampleRate,
                }
            }
        )

    @staticmethod  # skipcq: PTC-W0038
    def __get_vosk_server_eof_message() -> dict:
        return {"eof": 1}

    def __get_language(self) -> AvailableLanguages:  # skipcq: PTC-W0038
        return self.__LANGUAGE

    @staticmethod
    def __get_vosk_server_message(data: bytes) -> bytes:
        return data

    @staticmethod
    def __get_ffmpeg_arguments(audioFile: Path) -> list:
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

    @staticmethod
    def __parse_response(response: str) -> Optional[SpeechRecognitionVoskPartialResult]:
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

    async def process_audio_file(
        self, audioFile: Path, bytesToReadEveryTime: int = 8000
    ) -> None:
        logging.debug("Processing audio file: %s", audioFile.__str__())
        startTime = time.time()
        async with websockets.connect(  # type: ignore
            self.__ENDPOINT, extra_headers=self.__get_headers()
        ) as websocket:
            logging.info("Using ffmpeg to convert audio file real-time")
            proc = await asyncio.create_subprocess_exec(
                *self.__get_ffmpeg_arguments(audioFile),
                stdout=asyncio.subprocess.PIPE,
            )
            await websocket.send(json.dumps(self.__get_vosk_server_config_message()))
            while True:
                data = (
                    await proc.stdout.read(bytesToReadEveryTime)
                    if proc.stdout
                    else None
                )
                if data is None:
                    logging.warning("No data read from ffmpeg subprocess")
                    break
                if len(data) == 0:
                    break
                await websocket.send(self.__get_vosk_server_message(data))
                self.__add_result(self.__parse_response(await websocket.recv()))
            await websocket.send('{"eof" : 1}')
            self.__add_result(self.__parse_response(await websocket.recv()))
            await proc.wait()
            self.__set_finished_status(True)
            logging.info(
                "Took %s seconds to process audio file with %d bytes sent every time",
                time.time() - startTime,
                bytesToReadEveryTime,
            )
            # logging.info("Using native audio file format")
            # waveFile = wave.open(audioFile.__str__(), "rb")
            # await websocket.send(
            #     json.dumps(
            #         self.__get_vosk_server_config_message(
            #             sampleRate=waveFile.getframerate(),
            #             altFormat=True,
            #         )
            #     ).__str__()
            # )
            # buffer_size = int(waveFile.getframerate() * 0.2)
            # while True:
            #     data = waveFile.readframes(buffer_size)
            #     if len(data) == 0:
            #         break
            #     await websocket.send(self.__get_vosk_server_message(data))
            #     self.__add_result(self.__parse_response(await websocket.recv()))
            # await websocket.send('{"eof" : 1}')
            # self.__add_result(self.__parse_response(await websocket.recv()))
            # self.__set_finished_status(True)
