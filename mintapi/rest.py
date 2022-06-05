"""
Module for REST based API
"""

import logging
from typing import Dict, List, Optional, Union

from requests import Response, Session

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

    def _paginate(self, data_key: str, metadata_key: str, response: Response, **kwargs):
        """
        Mint API appears to use a limit-offset pagination mechanism with
        href links embedded in responses. Can iterate through sequentially
        and append results together

        Data schema:
        {DataType: [], metaData: {}} where DataType is a dynamic key mapping to the endpoint
        metaData follows a consistent format:

        {
            'asOf': 'TIMESTAMP',
            'totalSize': INT,
            'pageSize': 20,
            'currentPage': 1,
            'offset': 0,
            'limit': 20,
            'link': [
                {'otherAttributes': {'method': 'GET'}, 'href': '/v1/accounts', 'rel': 'self'},
                {'otherAttributes': {}, 'href': '/v1/accounts?offset=20&limit=20', 'rel': 'next'}
            ]
        }

        Parameters
        ----------
        data_key : str
            _description_
        response : Response
            _description_

        Returns
        -------
        _type_
            _description_
        """
        data = []

        json_data = response.json()
        data.extend(json_data[data_key])
        metadata = _ResponseMetadata(json_data[metadata_key])

        # drop url params from propagating (href includes the full uri path already)
        kwargs.pop("params", None)

        while metadata.has_next:
            response = self.request(
                uri_path=metadata.next_uri_path,
                data_key=data_key,
                metadata_key=metadata_key,
                paginate=False,
                **kwargs,
            )
            json_data = response.json()
            data.extend(json_data[data_key])
            metadata = _ResponseMetadata(json_data[metadata_key])

        return data

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

    def get(self, **kwargs):
        return self.request(method="GET", **kwargs)

    def post(self, **kwargs):
        return self.request(method="POST", **kwargs)


class _ResponseMetadata(object):
    """
    Convenience wrapper for pagination
    """

    def __init__(self, metadata):
        self.metadata = metadata

    @property
    def has_next(self):
        return "link" in self.metadata and any(
            [i["rel"] == "next" for i in self.metadata["link"]]
        )

    @property
    def next_uri_path(self):
        link = [i for i in self.metadata["link"] if i["rel"] == "next"][0]
        return link["href"]
