from config import AvailableLanguages
from pydantic import BaseModel
import json


class SingleLocale(BaseModel):
    voiceMessageReceived: str
    fileMessageReceived: str
    voiceMessageProcessing: str
    fileMessageProcessing: str
    noWordsFound: str
    settings: str
    settingsLanguage: str
    settingsLanguageRussian: str
    settingsLanguageEnglish: str
    settingsPunctuation: str
    settingsPunctuationOn: str
    settingsPunctuationOff: str
    settingsParticipateInStatistics: str
    settingsHowMany: str
    settingsHowManyMessagesReceived: str
    settingsHowManyMessagesProcessed: str
    settingsHowManyCharactersProcessed: str
    settingsHowManySecondsOfAudioProcessed: str
    settingsDigitsAfterDot: str
    settingSendBigTextAsFile: str
    settingSendBigTextAsFileOn: str
    settingSendBigTextAsFileOff: str
    settingSendSubtitles: str
    settingSendSubtitlesOn: str
    settingSendSubtitlesOff: str
    messageSentAsAFile: str
    messageSentAsAFileWithSubtitles: str
    errorWhileDownloading: str
    fullMessageAfterProcessing: str


class Locale:
    @staticmethod
    def get_language_locale(lang: AvailableLanguages) -> SingleLocale:
        with open(f"locales/{lang.value}.json", "r") as f:
            return SingleLocale(**json.load(f))

    def __init__(self, languages: list[AvailableLanguages]) -> None:
        for lang in languages:
            setattr(self, lang.value.upper(), self.get_language_locale(lang))

    def get(self, lang: AvailableLanguages, key: str) -> str:
        return getattr(getattr(self, lang.value.upper()), key)


LOCALE = Locale([AvailableLanguages.EN, AvailableLanguages.RU])
