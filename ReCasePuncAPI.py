from typing import Optional
import requests
from pydantic import HttpUrl, parse_obj_as
from config import AvailableLanguages
from models import RecasepuncResponseModel, RecasepuncRequestBodyModel
import logging


class RecasepuncAPI:
    def __init__(self, endpointBase: HttpUrl, apiKey: str) -> None:
        self.__ENDPOINT = endpointBase
        self.__APIKEY = apiKey

    def __get_headers(self) -> dict:
        return {
            "X-API-Key": self.__APIKEY,
            "Content-Type": "application/json; charset=utf-8",
        }

    def __get_endpoint(self, language: AvailableLanguages) -> HttpUrl:
        return parse_obj_as(HttpUrl, self.__ENDPOINT + "/" + language.value)

    def make_request(
        self, request: RecasepuncRequestBodyModel
    ) -> Optional[RecasepuncResponseModel]:
        logging.info(
            "Making request to %s with text `%s`",
            self.__get_endpoint(request.lang),
            request.text.__str__(),
        )
        response = requests.post(
            url=self.__get_endpoint(request.lang),
            headers=self.__get_headers(),
            json={"text": request.text.__str__()},
        )
        if response.status_code == 200:
            logging.info(
                "RecasepuncAPI request successful: %s", response.text.__str__()
            )
            return RecasepuncResponseModel(**response.json())
        return None
