"""
Module for REST based API
"""

import logging
from typing import Dict, List, Optional, Union

from requests import Session

from mintapi.endpoints import MintEndpoints

LOGGER = logging.getLogger(__name__)


class RESTClient(MintEndpoints):
    """
    Parallel API class to the selenium based one

    Motivated by fickleness of selenium to find the appropriate css selectors.
    Through introspection, the mint API can be accessed via REST with
    a header and/or cookie based auth pattern

    Auth values can be extracted using selenium flow or manually passed from browser
    inspection
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cookies: Optional[Union[str, List[Dict]]] = None,
        **kwargs,
    ):
        self.session = Session()

        if api_key or cookies:
            self.authorize(api_key=api_key, cookies=cookies)

    def authorize(self, cookies: Union[str, List[Dict]] = None, api_key: str = None):
        """
        Auth can be configured via an api key + cookie string in the headers
        or just the api key and cookies as cookies in the session

        Parameters
        ----------
        cookie : str
            _description_
        api_key : str
            _description_
        """
        if isinstance(cookies, list):
            self.update_cookies(cookies)
            cookies = None

        self.session.headers.update(
            {
                k: v
                for k, v in {"authorization": api_key, "cookie": cookies}.items()
                if v is not None
            }
        )

    def update_cookies(self, cookies: List[Dict]):
        """
        _summary_

        Parameters
        ----------
        cookies : List[Dict]
            _description_

        Returns
        -------
        _type_
            _description_
        """
        for cookie in cookies:
            self.session.cookies.set(cookie["name"], str(cookie["value"]))

    """
    Accessor Methods
    """

    def request(
        self,
        *,
        method: str,
        api_url: str,
        api_section: str,
        uri_path: str,
        data_key: str,
        metadata_key: str,
        paginate=True,
        **kwargs,
    ):
        """
        _summary_

        Parameters
        ----------
        method : str
            _description_
        api_url : str
            _description_
        api_section : str
            _description_
        uri_path : str
            _description_
        data_key : str
            _description_
        paginate : bool, optional
            _description_, by default True

        Returns
        -------
        _type_
            _description_
        """
        url = f"{api_url}{api_section}{uri_path}"

        response = self.session.request(method=method, url=url, **kwargs)
        response.raise_for_status()

        if paginate:
            return self._paginate(
                api_url=api_url,
                api_section=api_section,
                method=method,
                data_key=data_key,
                metadata_key=metadata_key,
                response=response,
                **kwargs,
            )
        else:
            return response
