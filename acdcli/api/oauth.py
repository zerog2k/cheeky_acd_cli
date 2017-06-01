import os
import json
import requests
import time
import logging
import webbrowser
import datetime
import random
import string
import uuid
from requests.auth import AuthBase
from urllib.parse import urlparse, parse_qs
from threading import Lock

logger = logging.getLogger(__name__)

TOKEN_INFO_URL = 'https://api.amazon.com/auth/o2/tokeninfo'

# Fuck you Amazon you massive twats.
APP_ID = "YW16bjEuYXBwbGljYXRpb24tb2EyLWNsaWVudC40YTY0NzZkODljYTA0NDQ3OGY3MTI3MDZiN2VjYzYwNA"
APP_NAME = "Amazon Drive"
APP_VERSION = "4.0.13.d2a5aec4"

def create_handler(path: str):
    return CheekyOAuthHandler(path)

class CheekyOAuthHandler(AuthBase):
    """An OAuth handler that does some cheeky bullshit to make acd_cli work again."""
    OAUTH_DATA_FILE = 'oauth.json'
    AMAZON_OA_TOKEN_URL = 'https://api.amazon.com/auth/token'

    class KEYS(object):
        EXP_IN = 'expires_in'
        ACC_TOKEN = 'access_token'
        REFR_TOKEN = 'refresh_token'
        EXP_TIME = 'exp_time'  # manually added

    def __init__(self, path):
        self.path = path
        self.oauth_data = {}
        self.oauth_data_path = os.path.join(path, self.OAUTH_DATA_FILE)
        self.init_time = time.time()
        self.lock = Lock()

        self.load_oauth_data()
        logger.info('%s initialized.' % self.__class__.__name__)

    def __call__(self, r: requests.Request):
        with self.lock:
            r.headers.update(
                {
                    "Accept": "application/json",
                    "x-amz-access-token": self.get_auth_token(),
                    "x-amz-clouddrive-appid": APP_ID,
                    "x-amzn-RequestId": str(uuid.uuid4()),
                }
            )
        return r

    @property
    def exp_time(self):
        return self.oauth_data[self.KEYS.EXP_TIME]

    @classmethod
    def validate(cls, oauth: str) -> dict:
        """Deserialize and validate an OAuth string

        :raises: RequestError"""

        from .common import RequestError

        try:
            o = json.loads(oauth)
            o[cls.KEYS.ACC_TOKEN]
            o[cls.KEYS.EXP_IN]
            o[cls.KEYS.REFR_TOKEN]
            return o
        except (ValueError, KeyError) as e:
            logger.critical('Invalid authentication token: Invalid JSON or missing key.'
                            'Token:\n%s' % oauth)
            raise RequestError(RequestError.CODE.INVALID_TOKEN, e.__str__())

    def treat_auth_token(self, time_: float):
        """Adds expiration time to member OAuth dict using specified begin time."""
        exp_time = time_ + self.oauth_data[self.KEYS.EXP_IN] - 120
        self.oauth_data[self.KEYS.EXP_TIME] = exp_time
        logger.info('New token expires at %s.'
                    % datetime.datetime.fromtimestamp(exp_time).isoformat(' '))

    def load_oauth_data(self):
        """Loads oauth data file, validate and add expiration time if necessary"""
        self.check_oauth_file_exists()

        with open(self.oauth_data_path) as oa:
            o = oa.read()
        try:
            self.oauth_data = self.validate(o)
        except:
            logger.critical('Local OAuth data file "%s" is invalid. '
                            'Please fix or delete it.' % self.oauth_data_path)
            raise
        if self.KEYS.EXP_TIME not in self.oauth_data:
            self.treat_auth_token(self.init_time)
            self.write_oauth_data()
        else:
            self.get_auth_token(reload=False)

    def get_auth_token(self, reload=True) -> str:
        """Gets current access token, refreshes if necessary.

        :param reload: whether the oauth token file should be reloaded (external update)"""

        if time.time() > self.exp_time:
            logger.info('Token expired at %s.'
                        % datetime.datetime.fromtimestamp(self.exp_time).isoformat(' '))

            # if multiple instances are running, check for updated file
            if reload:
                with open(self.oauth_data_path) as oa:
                    o = oa.read()
                self.oauth_data = self.validate(o)

            if time.time() > self.exp_time:
                self.refresh_auth_token()
            else:
                logger.info('Externally updated token found in oauth file.')
        return self.oauth_data[self.KEYS.ACC_TOKEN]

    def write_oauth_data(self):
        """Dumps (treated) OAuth dict to file as JSON."""

        new_nm = self.oauth_data_path + ''.join(random.choice(string.hexdigits) for _ in range(8))
        rm_nm = self.oauth_data_path + ''.join(random.choice(string.hexdigits) for _ in range(8))

        f = open(new_nm, 'w')
        json.dump(self.oauth_data, f, indent=4, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
        f.close()

        if os.path.isfile(self.oauth_data_path):
            os.rename(self.oauth_data_path, rm_nm)
        os.rename(new_nm, self.oauth_data_path)
        try:
            os.remove(rm_nm)
        except OSError:
            pass

    def refresh_auth_token(self):
        """Fetches a new access token using a refresh token."""
        logger.info('Refreshing authentication token.')

        data = {
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
            "requested_token_type": "access_token",
            "source_token": self.oauth_data[self.KEYS.REFR_TOKEN],
            "source_token_type": "refresh_token",
        }

        from .common import RequestError

        t = time.time()
        try:
            response = requests.post(self.AMAZON_OA_TOKEN_URL, data=data)
        except ConnectionError as e:
            logger.critical('Error refreshing authentication token.')
            raise RequestError(RequestError.CODE.CONN_EXCEPTION, e.__str__())

        if response.status_code != requests.codes.ok:
            raise RequestError(RequestError.CODE.REFRESH_FAILED,
                               'Error refreshing authentication token: %s' % response.text)

        response_json = response.json()
        response_json[self.KEYS.REFR_TOKEN] = self.oauth_data[self.KEYS.REFR_TOKEN]
        self.oauth_data = self.validate(json.dumps(response_json))
        self.treat_auth_token(t)
        self.write_oauth_data()

    def check_oauth_file_exists(self):
        """Checks for OAuth file existence and one-time initialize if necessary. Throws on error."""
        if not os.path.isfile(self.oauth_data_path):
            raise RuntimeError("The OAuth configuration does not exist. You must create it first.")

    def get_access_token_info(self) -> dict:
        """
        :returns:
        int exp: expiration time in sec,
        str aud: client id
        user_id, app_id, iat (exp time)"""

        r = requests.get(TOKEN_INFO_URL,
                         params={'access_token': self.oauth_data['access_token']})
        return r.json()
