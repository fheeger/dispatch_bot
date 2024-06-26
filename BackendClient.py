import requests
import json

from BackendCallError import BackendCallError


class BackendClient:
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    def __init__(self, base_url):
        self.base_url = base_url

    def call(self, method, url_function, res_id=None, data=None, params=None):
        if method == "GET":
            return self.get_url(url_function, res_id, params)
        elif method == "PATCH":
            return self.patch_url(url_function, res_id, data, params)
        elif method == "POST":
            return self.post_url(url_function, data, params)
        else:
            raise ValueError("Unknown method: {}".format(method))

    def get_url(self, url_function, res_id=None, params=None):
        """ general function get to read"""
        this_url = self.base_url + url_function
        if res_id:
            this_url += '/' + str(res_id)
        response = requests.get(this_url, headers=self.headers, params=params)
        if is_error(response.status_code):
            raise BackendCallError(response)
        return response.json()

    def patch_url(self, url_function, res_id=None, data=None, params=None):
        """ general function put to update"""
        url = self.base_url + url_function
        if res_id:
            url += str(res_id)
        if data:
            data = json.dumps(data)
        response = requests.patch(url, data=data, headers=self.headers, params=params)
        if is_error(response.status_code):
            raise BackendCallError(response)
        return response.json()

    def post_url(self, url_function, data=None, params=None):
        """ general function post to create"""
        url = self.base_url + url_function
        response = requests.post(url, data=json.dumps(data), headers=self.headers, params=params)
        if is_error(response.status_code):
            raise BackendCallError(response)
        return response.json()


def is_error(http_status: int):
    return http_status >= 400
