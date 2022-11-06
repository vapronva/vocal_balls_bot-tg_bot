from os import environ as env
from pydantic import AnyUrl, HttpUrl, parse_obj_as, PositiveInt
from enum import Enum


class AvailableLanguages(str, Enum):
    EN = "en"
    RU = "ru"


class Config:
    def __init__(self) -> None:
        __REQUIRED = [
            "VOSK_API_KEY",
            "VOSK_ENDPOINT_RUSSIAN",
            "VOSK_ENDPOINT_ENGLISH",
            "TELEGRAM_API_ID",
            "TELEGRAM_API_HASH",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_BOT_WORKERS",
            "VPRW_RCPAPI_ENDPOINT",
            "VPRW_RCPAPI_KEY",
            "APPWRITE_API_ENDPOINT",
            "APPWRITE_PROJECT_ID",
            "APPWRITE_API_KEY",
            "APPWRITE_STORAGE_BOTAVATAR",
        ]
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
    def get_telegram_api_id() -> int:
        return int(env["TELEGRAM_API_ID"])

    @staticmethod
    def get_telegram_api_hash() -> str:
        return env["TELEGRAM_API_HASH"]

    @staticmethod
    def get_telegram_bot_token() -> str:
        return env["TELEGRAM_BOT_TOKEN"]

    @staticmethod
    def get_telegram_bot_workers() -> PositiveInt:
        return int(env["TELEGRAM_BOT_WORKERS"])

    @staticmethod
    def get_vprw_rcpapi_endpoint() -> HttpUrl:
        return parse_obj_as(HttpUrl, env["VPRW_RCPAPI_ENDPOINT"])

    @staticmethod
    def get_vprw_rcpapi_key() -> str:
        return env["VPRW_RCPAPI_KEY"]

    @staticmethod
    def get_vosk_endpoint(language: AvailableLanguages) -> AnyUrl:
        if language == AvailableLanguages.RU:
            return Config.get_vosk_endpoint_russian()
        elif language == AvailableLanguages.EN:
            return Config.get_vosk_endpoint_english()
        else:
            raise Exception(f"Unsupported language: {language}")

    @staticmethod
    def get_appwrite_api_endpoint() -> HttpUrl:
        return parse_obj_as(HttpUrl, env["APPWRITE_API_ENDPOINT"])

    @staticmethod
    def get_appwrite_project_id() -> str:
        return env["APPWRITE_PROJECT_ID"]

    @staticmethod
    def get_appwrite_api_key() -> str:
        return env["APPWRITE_API_KEY"]

    @staticmethod
    def get_appwrite_storage_botavatar() -> HttpUrl:
        return parse_obj_as(HttpUrl, env["APPWRITE_STORAGE_BOTAVATAR"])
