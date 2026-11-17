"""Pinned-release API transport. Local origin only; no redirects or mutation retry."""
import json
import re
import urllib.error
import urllib.request


class Rejected(RuntimeError): pass
class Uncertain(RuntimeError): pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args): return None


class API:
    def __init__(self, credentials):
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.token = None
        result = self.request('POST', '/api/accounts/token/', credentials)
        self.token = result['access']
        if not isinstance(self.token, str) or not 1 <= len(self.token) <= 8192:
            raise Rejected('invalid_authentication_response')

    def request(self, method, path, body=None):
        allowed = re.fullmatch(r'/api/(?:accounts/token/|core/(?:streamprofiles|settings)/(?:[0-9]+/)?|channels/(?:streams|channels|groups)/(?:[0-9]+/)?)(?:\?page=[0-9]+)?', path)
        if not allowed or method not in {'GET', 'POST', 'PATCH', 'DELETE'}:
            raise Rejected('API_scope_refused')
        if method != 'GET' and path != '/api/accounts/token/' and not re.fullmatch(r'/api/channels/(streams|channels)/(?:[0-9]+/)?', path):
            raise Rejected('API_write_scope_refused')
        headers = {'Content-Type': 'application/json'}
        if self.token: headers['Authorization'] = 'Bearer ' + self.token
        data = None if body is None else json.dumps(body, allow_nan=False).encode()
        request = urllib.request.Request('http://127.0.0.1:9191' + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=8) as response:
                raw = response.read(2097153)
                if len(raw) > 2097152: raise Uncertain('API_response_limit')
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            if 400 <= exc.code < 500: raise Rejected('API_rejected') from None
            raise Uncertain('API_outcome_uncertain') from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise Uncertain('API_outcome_uncertain') from None

    def rows(self, collection):
        rows = []
        for page in range(1, 65):
            result = self.request('GET', collection + '?page=' + str(page))
            if isinstance(result, list):
                if len(result)>10000: raise Rejected('inventory_limit')
                return result
            if not isinstance(result, dict) or not isinstance(result.get('results'), list):
                raise Rejected('pagination_schema_changed')
            rows.extend(result['results'])
            if len(rows) > 10000: raise Rejected('inventory_limit')
            if not result.get('next'): return rows
        raise Rejected('pagination_limit')
