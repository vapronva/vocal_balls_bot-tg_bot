from os import environ as env
from pydantic import AnyUrl, parse_obj_as
from enum import Enum


class AvailableLanguages(Enum):
    EN = "en"
    RU = "ru"


class Config:
    def __init__(self) -> None:
        __REQUIRED = ["VOSK_API_KEY", "VOSK_ENDPOINT_RUSSIAN", "VOSK_ENDPOINT_ENGLISH"]
        for key in __REQUIRED:
            if key not in env:
                raise Exception(f"Missing required environment variable: {key}")

    @staticmethod
    def get_vosk_api_key() -> str:
        return env["VOSK_API_KEY"]

    @staticmethod
    def get_vosk_endpoint_russian() -> AnyUrl:
        return parse_obj_as(AnyUrl, env["VOSK_ENDPOINT_RUSSIAN"])

    @staticmethod
    def get_vosk_endpoint_english() -> AnyUrl:
        return parse_obj_as(AnyUrl, env["VOSK_ENDPOINT_ENGLISH"])

    @staticmethod
    def get_vosk_endpoint(language: AvailableLanguages) -> AnyUrl:
        if language == AvailableLanguages.RU:
            return Config.get_vosk_endpoint_russian()
        elif language == AvailableLanguages.EN:
            return Config.get_vosk_endpoint_english()
        else:
            raise Exception(f"Unsupported language: {language}")
