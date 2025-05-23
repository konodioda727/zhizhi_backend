from sqlalchemy import create_engine, Column, String, Integer, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

USERNAME = 'root'
PASSWORD = '123456'
PORT = '3306'
DB_NAME = 'zhizhi'




DATABASE_URL = f"mysql+pymysql://{USERNAME}:{PASSWORD}@localhost:{PORT}/{DB_NAME}" 

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
