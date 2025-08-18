import os
import logging
from pymongo import MongoClient

logger = logging.getLogger(__name__)


class MongoService():
    def __init__(self):
        MONGO_URI = os.getenv("uri")
        if MONGO_URI is None:
            logger.error("Invalid Mongo URI")

        try:
            client = MongoClient(MONGO_URI)
            self.db = client["pfm-db"]
            logger.info("Successfully got Mongo client and connected to pfm-db.")
        except Exception as e:
            logger.exception(f"Failed to connect to MongoDB: {e}")
            raise

    def get_db(self):
        return self.db
