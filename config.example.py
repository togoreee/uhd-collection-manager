"""
UHD 片单系统配置文件
"""

# Emby 配置
EMBY_BASE_URL = "http://你的Emby地址:8096"
EMBY_SERVER_ID = "你的EmbyServerId"
EMBY_DB_PATH = "/volume3/docker/emby/config/data/library.db"

# TMDB API
TMDB_API_KEY = "你的TMDBAPIKey"

# 文件路径
CSV_FILE = "digiraw_movies_full_merged.csv"
LOCAL_MOVIE_CSV = "local_tmdb_path_from_emby.csv"
EMBY_MAP_CSV = "emby_tmdb_itemid_map.csv"

# 服务端口
API_PORT = 8081
WEB_PORT = 8080
