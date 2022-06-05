"""
Module for REST based API
"""

import logging
import uuid
from typing import List, Optional

from requests import Response, Session

from mintapi.constants import MINT_ROOT_URL
from mintapi.endpoints import MintEndpoints

LOGGER = logging.getLogger(__name__)


class RESTClient(MintEndpoints):
    """
    Parallel API class to the selenium based one

    Motivated by fickleness of selenium to find the appropriate css selectors.
    Through introspection, the mint API can be accessed via REST with
    a header based auth pattern (cookie, api key, and transaction ID of which
    it seems only cookie is a necessary real value. mocked others with random
    values and seemed to work as long as they are present in the request)

    Auth values can be extracted using selenium flow or manually passed from browser
    inspection
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cookie: Optional[str] = None,
        **kwargs,
    ):
        self.session = Session()

        if api_key and cookie:
            self.authorize(api_key=api_key, cookie=cookie)

    def authorize(self, cookie: str, api_key: str):
        """
        _summary_

        Parameters
        ----------
        cookie : str
            _description_
        api_key : str
            _description_
        """
        self.session.headers.update({"authorization": api_key, "cookie": cookie})

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
