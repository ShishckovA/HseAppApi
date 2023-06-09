import logging
import requests
from typing import Optional

from urllib.parse import urlparse, parse_qs, urlencode

logger = logging.Logger(__name__)


def combine_base_url_with_params(url: str, params: Optional[dict]) -> str:
    if params is None:
        return url
    combined_url = url + "?" + urlencode(params)
    return combined_url


class HseAppApi:
    # Auth
    REDIRECT_URI = "ru.hse.pf://auth.hse.ru/adfs/oauth2/android/ru.hse.pf/callback/"
    BASE_URL_AUTHORIZE = "https://auth.hse.ru/adfs/oauth2/authorize/"
    BASE_URL_TOKEN = "https://auth.hse.ru/adfs/oauth2/token/"

    # Fuzzy search
    BASE_URL_SEARCH = "https://api.hseapp.ru/v2/dump/search/"

    SEARCH_SCOPES = [
        "student",
        "staff",
        "external_staff",
        "auditorium",
        "group",
        "course",
        "service",
    ]

    DEFAULT_SEARCH_SCOPE: str = "all"
    DEFAULT_SEARCH_COUNT: int = 5

    # Email search
    BASE_URL_EMAIL_SEARCH = "https://api.hseapp.ru/v2/dump/email/{email}"

    def __init__(self, username: str, password: str, client_id: str):
        self.username: str = username
        self.password: str = password
        self.client_id: str = client_id
        self.token: Optional[str] = None
        self.session: Optional[requests.Session] = None

    @staticmethod
    def get_bearer_token(
        username: str,
        password: str,
        client_id: str,
        session: Optional[requests.Session] = None,
    ) -> Optional[str]:
        """
        Getting Bearer token for using HSE auth.
        May be can be simplified using https:// schema in redirect_uri.
        """

        # 1. Base authorization
        # If allow_redirects=True, auth redirects to ru.hse.pf://auth.hse.ru/adfs...,
        # which falls with an error (Unknown schema: ru.hse.pf://)
        # So we can follow redirections manually using allow_redirects=False
        if session is None:
            session = requests.Session()

        # Setting query params
        query_params_authorize_pos = {
            "client_id": client_id,
            "redirect_uri": HseAppApi.REDIRECT_URI,
            "response_type": "code",
        }

        # Constructing URL and querying
        url_auth_post = combine_base_url_with_params(
            HseAppApi.BASE_URL_AUTHORIZE, query_params_authorize_pos
        )
        res_auth_post = session.post(
            url_auth_post,
            data={
                "UserName": username,
                "Password": password,
                "AuthMethod": "FormsAuthentication",
            },
            allow_redirects=False,
        )

        # Awaiting redirect, falling if not
        if res_auth_post.status_code != 302:
            raise ValueError(
                "Bad status code for post on auth url: {}. "
                "May be your credentials or client_id is incorrect?".format(
                    res_auth_post.status_code
                )
            )

        cookies = res_auth_post.cookies

        # 2. Getting code
        # This request edirects to https://auth.hse.ru:443/adfs/oauth2/authorize,
        # but now includes client-request-id (ac708a1c-ab98-4ec3...) in query params
        url_auth_get = res_auth_post.headers["Location"]
        res_auth_get = session.get(url_auth_get, cookies=cookies, allow_redirects=False)

        # Also awaiting redirect, now on redirect_uri. But now we have
        # code=KwMmAUI6c0... in url query params
        assert res_auth_get.status_code == 302

        # Stopping next redirections, because next redirect falls with
        # "Unknown schema: ru.hse.pf://". May be can be simplifyed if
        # appropriate REDIRECT_URI (with https://) can be found

        # Getting code from query params
        parsed_url = urlparse(res_auth_get.headers["Location"])
        code = parse_qs(parsed_url.query)["code"]

        # 3. Getting Bearer token
        # With this code we can get Bearer token for querying
        # https://api.hseapp.ru/v2
        res_token_post = session.post(
            HseAppApi.BASE_URL_TOKEN,
            data={
                "code": code,
                "client_id": client_id,
                "redirect_uri": HseAppApi.REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        token = res_token_post.json()["access_token"]
        return token

    def auth(self) -> None:
        if self.session is not None:
            self.session.close()
        self.session = requests.Session()
        self.token = HseAppApi.get_bearer_token(
            username=self.username,
            password=self.password,
            client_id=self.client_id,
            session=self.session,
        )
        logger.debug("Auth success!")

    def has_session(self) -> bool:
        return self.session is not None

    def get_api_headers(self) -> dict[str, str]:
        token_header = "Bearer {token}".format(token=self.token)
        return {
            "accept-encoding": "gzip",
            "accept-language": "ru-RU",
            "authorization": token_header,
            "user-agent": "HSE App X/1.18.1; release (SM-A515F; Android/11; ru_RU; 1080x2400)",
        }

    def get_request(self, base_url: str, params: Optional[dict] = None):
        if not self.has_session():
            raise ValueError("No opened session found! Use HseAppApi.auth() first.")
        logger.debug("Querying {url} with params {params}".format(
            url=base_url,
            params=params
        ))
        url = combine_base_url_with_params(base_url, params)
        headers = self.get_api_headers()
        result = self.session.get(url, headers=headers)
        if result.status_code != 200:
            raise ValueError(
                "Error: expected code 200, got {}".format(result.status_code)
            )
        json_result = result.json()
        return json_result

    def search(
        self,
        query: str,
        type_: Optional[str] = None,
        count: int = DEFAULT_SEARCH_COUNT,
    ) -> list[dict]:
        if type_ is None:
            type_ = ",".join(HseAppApi.SEARCH_SCOPES)
        else:
            if type_ not in HseAppApi.SEARCH_SCOPES:
                raise ValueError(
                    'type must be one of {search_scopes}, got "{type_}"'.format(
                        search_scopes=HseAppApi.SEARCH_SCOPES, type_=type_
                    )
                )
        params = {"q": query, "type": type_, "count": count}
        result = self.get_request(HseAppApi.BASE_URL_SEARCH, params)
        return result

    def search_by_email(
        self,
        email: str,
    ) -> dict:
        url = HseAppApi.BASE_URL_EMAIL_SEARCH.format(email=email)
        result = self.get_request(url)
        return result
