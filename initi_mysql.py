from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('sqlalchemy.engine')

logger.setLevel(logging.INFO)
# user, password, host, dbname
DATABASE_URI = 'mysql+pymysql://songkai:test@101.43.133.171:3307/embedded_system'

engine = create_engine(url=DATABASE_URI, pool_size=5, echo=True)

Session = sessionmaker(bind=engine)
session: Session = Session()
