import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "mysql+pymysql://3vv7osWoLoY5zrD.root:ZT68huUjzEPEMMED@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/cater?ssl_verify_cert=true&ssl_verify_identity=true")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
