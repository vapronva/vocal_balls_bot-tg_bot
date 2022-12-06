from enum import Enum
from pyrogram.types import Message as PyrogramMessage
from models import UserModel
from config import Config, AvailableLanguages
import logging
import uuid
import time
import threading
from pathlib import Path
from VoskAPI import VoskAPI
from Locale import LOCALE
import asyncio
from utils import Utils
import audioread
from ReCasePuncAPI import RecasepuncAPI
from models import SpeechRecognitionVoskPartialResult


class MESSAGE_TYPES_FILTRED(Enum):
    VOICE = "voice"
    AUDIO = "audio"


class STTPipeline:
    def __init__(
        self,
        messageType: MESSAGE_TYPES_FILTRED,
        message: PyrogramMessage,
        user: UserModel,
        config: Config,
    ) -> None:
        self.messageType = messageType
        self.message = message
        self.user = user
        self.config = config
        self.__post_init__()

    def __post_init__(self) -> None:
        self.user.prefs.statistics.messagesReceived += 1
        self.initialLanguage: AvailableLanguages = self.user.prefs.language
        logging.info(
            "Received %s message from user #%s for message ID #%s",
            self.messageType.value,
            self.message.from_user.id,
            self.message.id,
        )
        self.botRepliedMessage: PyrogramMessage = self.message.reply_text(
            f"__💬 {LOCALE.get(self.user.prefs.language, 'voiceMessageReceived') if self.messageType == MESSAGE_TYPES_FILTRED.VOICE else LOCALE.get(self.user.prefs.language, 'fileMessageReceived')}...__",
            quote=True,
        )  # type: ignore
        self.vosk = VoskAPI(
            apiKey=self.config.get_vosk_api_key(),
            language=self.initialLanguage,
        )
        self.outputFile = (
            Path(f"files_download/{uuid.uuid4().__str__().replace('-', '')}.ogg")
            if self.messageType == MESSAGE_TYPES_FILTRED.VOICE
            else Path(
                f"files_download/{uuid.uuid4().__str__().replace('-', '')[:16]}-{self.message.audio.file_name.replace(' ', '_').replace('/', '_').replace('-', '_')}"
            )
        )
        self.results: list[SpeechRecognitionVoskPartialResult] = []

    def get_user(self) -> UserModel:
        return self.user

    def run(self) -> int:
        if self.__download_message() != 0:
            return 1
        self.__start_threads()
        RCPAPI = RecasepuncAPI(
            apiKey=self.config.get_vprw_rcpapi_key(),
            endpointBase=self.config.get_vprw_rcpapi_endpoint(),
        )
        self.__get_and_process_results(RCPAPI)
        return 0

    def __download_message(self) -> int:
        try:
            _ = self.message.download(file_name=self.outputFile.__str__())
            return 0
        except Exception as e:
            logging.error(
                "Error while downloading message from user #%s for message ID #%s: %s",
                self.message.from_user.id,
                self.message.id,
                e,
            )
            _ = self.botRepliedMessage.edit_text(
                f"__❌ {LOCALE.get(self.user.prefs.language, 'errorWhileDownloading')}__\n\n```{e}```"
            )
            return 1

    def __start_threads(self) -> None:
        threadProcessor = threading.Thread(
            target=asyncio.run,
            args=(
                self.vosk.process_audio_file(
                    audioFile=self.outputFile,
                    bytesToReadEveryTime=64000,
                ),
            ),
        )
        threadTelegramMessageEditor = threading.Thread(
            target=Utils.update_stt_result_as_everything_comes_in,
            args=(
                self.botRepliedMessage,
                self.vosk,
                self.user.prefs.howManyDigitsAfterDot,
            ),
        )
        threadProcessor.start()
        threadTelegramMessageEditor.start()
        _ = self.botRepliedMessage.edit_text(
            text=f"__🔁 {LOCALE.get(self.user.prefs.language, 'voiceMessageProcessing') if self.messageType == MESSAGE_TYPES_FILTRED.VOICE else LOCALE.get(self.user.prefs.language, 'fileMessageProcessing')}...__"
        )
        threadProcessor.join()
        threadTelegramMessageEditor.join()

    def __get_and_process_results(self, RCPAPI: RecasepuncAPI) -> None:
        self.results = self.vosk.get_results()
        if self.results is None or len(self.results) == 0:
            _ = self.botRepliedMessage.edit_text(
                text=f"__⚠️ {LOCALE.get(self.user.prefs.language, 'noWordsFound')}!__"
            )
            return
        Utils.send_stt_result_with_respecting_max_message_length(
            message=self.message,
            initialMessage=self.botRepliedMessage,
            vosk=self.vosk,
            user=self.user,
            rcpapi=RCPAPI if self.user.prefs.recasepunc else None,
            language=self.initialLanguage,
        )

    def analytics(self, newUser: UserModel) -> None:
        startTimeAnalytics = time.time()
        self.user = newUser
        if self.user.prefs.participateInStatistics:
            self.user.prefs.statistics.processedWithLanguage[
                self.initialLanguage.value
            ] += 1
            self.user.prefs.statistics.messagesProcessed += 1
            self.user.prefs.statistics.charactersProcessed += sum(
                len(resultResult.text) for resultResult in self.results
            )
            fileOggType = audioread.audio_open(self.outputFile.__str__())
            self.user.prefs.statistics.secondsOfAudioProcessed += (
                int(fileOggType.duration) if fileOggType.duration else 0
            )
        self.user.name = (
            f"{self.message.from_user.first_name} {self.message.from_user.last_name} (@{self.message.from_user.username})"
            if self.message.from_user.username is not None
            else f"{self.message.from_user.first_name} {self.message.from_user.last_name} (null)"
        )
        self.outputFile.unlink()
        logging.info(
            "Processed %s message analytics and cleaned up for user #%s for message ID #%s in %s seconds",
            self.messageType.value,
            self.message.from_user.id,
            self.message.id,
            time.time() - startTimeAnalytics,
        )
