from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

# 配置根日志记录器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('sqlalchemy.engine')

# 开启SQL语句打印
logger.setLevel(logging.INFO)
# 替换下面的连接字符串中的user, password, host, dbname
DATABASE_URI = 'mysql+pymysql://songkai:test@101.43.133.171:3307/embedded_system'

engine = create_engine(url=DATABASE_URI, pool_size=1, echo=True)

Session = sessionmaker(bind=engine)
session: Session = Session()
