from typing import Optional
from pydantic import BaseModel, NonNegativeFloat
from config import AvailableLanguages
from enum import Enum


class SpeechRecognitionVoskPartialResult(BaseModel):
    text: str
    startTime: NonNegativeFloat
    endTime: NonNegativeFloat
    overallConfidence: float


class RecasepuncRequestBodyModel(BaseModel):
    text: str
    lang: AvailableLanguages


class RecasepuncResponseModel(BaseModel):
    error: Optional[dict]
    result: Optional[str]

    def fix_result_apostrophe(self) -> Optional[str]:
        if self.result is not None:
            self.result = (
                self.result.replace(" ' ", "'")
                .replace(" ? ", "? ")
                .replace(" ?", "?")
                .replace(" ! ", "! ")
                .replace(" !", "!")
                .replace(" , ", ", ")
                .replace(" . ", ". ")
                .replace(" .", ".")
                .replace(" - ", "-")
                .replace(" : ", ": ")
                .replace(" ; ", "; ")
            )
        return self.result


class UserStatisticsModel(BaseModel):
    messagesReceived: int = 0
    messagesProcessed: int = 0
    charactersProcessed: int = 0
    secondsOfAudioProcessed: int = 0
    processedWithLanguage: dict[AvailableLanguages, int] = {
        AvailableLanguages.RU: 0,
        AvailableLanguages.EN: 0,
    }


class UserPreferencesModel(BaseModel):
    howManyDigitsAfterDot: int = 1
    language: AvailableLanguages = AvailableLanguages.EN
    recasepunc: bool = True
    participateInStatistics: bool = True
    sendBigTextAsFile: bool = True
    sendSubtitles: bool = True
    statistics: UserStatisticsModel = UserStatisticsModel()


class UserModel(BaseModel):
    id: str
    name: Optional[str] = None
    status: bool
    prefs: UserPreferencesModel = UserPreferencesModel()

    def __init__(self, **data) -> None:
        super().__init__(id=data["$id"], **data)


class CallbackQueryActionTypes(Enum):
    STATIC = "sttc"
    ACTION = "actn"


class CallbackQueryActionsObjects(Enum):
    LANGUAGE = "lang"
    PUNCTUATION = "punc"
    SENDBIGTEXTASFILE = "sbta"
    SENDSUBTITLES = "ssub"


class CallbackQueryActionsValues(Enum):
    RUSSIAN = "ru"
    ENGLISH = "en"
    NOTHING = "none"
    TOGGLE = "toggle"


class CallbackQueryDataModel(BaseModel):
    actionType: CallbackQueryActionTypes
    actionObject: CallbackQueryActionsObjects
    actionValue: CallbackQueryActionsValues
    telegramUserId: int
