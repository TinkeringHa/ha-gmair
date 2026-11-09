DOMAIN = "gmair"
NAME = "GMAIR 果麦新风"

API_BASE = "https://microservice.gmair.net"
WEB_URL = "https://reception.gmair.net/"

TOKEN_PATH = "/oauth/consumer/token"
SMS_REQUEST_PATH = "/auth/consumer/authentication/request"
SMS_LOGIN_PATH = "/auth/consumer/login"
DEVICE_LIST_PATH = "/reception/machine/devicelist"
MACHINE_LIST_PATH = "/reception/machine/list"
STATUS_PATH = "/reception/machine/running/status"
OPERATE_PATH = "/reception/machine/operate/{key}/{value}"
SPEED_PATH = "/reception/machine/config/speed"
LIGHT_PATH = "/reception/machine/config/light"
AIR_QUALITY_PATH = "/reception/airquality/city"
DEVICE_CITY_PATH = "/reception/machine/probe/cityId/byqrcode"
LOCATION_OVERVIEW_URL = "https://microservice.gmair.net/location/overview"
FILTER_CLEAN_PATH = "/reception/machine/filter/clean"
FILTER_REPLACE_PATH = "/reception/machine/efficientFilter/replaceStatus"

DEFAULT_CITY_ID = "110101"
FILTER_STATUS_TO_NAME = {
    "NO_NEED": "正常",
    "NEED": "即将到期",
    "URGENT_NEED": "立即更换",
}

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_CODE = "code"
CONF_AUTH_METHOD = "auth_method"
CONF_TOKEN = "token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_CITY_ID = "city_id"

AUTH_PASSWORD = "password_auth"
AUTH_SMS = "sms"

CLIENT_ID = "client_2"
CLIENT_SECRET = "123456"

UPDATE_INTERVAL_SECONDS = 30

MIN_VOLUME = 60
MAX_VOLUME = 420
MAX_LIGHT = 8

MODE_TO_NAME = {0: "自动", 1: "睡眠", 2: "手动"}
NAME_TO_MODE = {"自动": "auto", "睡眠": "sleep", "手动": "manual"}

HEAT_TO_NAME = {0: "关闭", 1: "500W", 2: "1000W"}
NAME_TO_HEAT = {"关闭": "off", "500W": "cosy", "1000W": "warm"}

PLATFORMS = ["sensor", "fan", "select", "number", "switch"]
