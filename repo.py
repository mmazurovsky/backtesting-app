import os
from typing import List, Dict, Any, Optional
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv
from datetime import datetime
from bson import ObjectId
from data import OhlcEntity, OhlcRequest
from datetime import datetime, timedelta


def _document_to_entity(document: Dict[str, Any]) -> OhlcEntity:
    return OhlcEntity(
        _id=str(document.get('_id')) if document.get('_id') else None,
        volume=document.get('volume'),
        takerBuyBaseAssetVolume=document.get('takerBuyBaseAssetVolume'),
        numberOfTrades=document.get('numberOfTrades'),
        symbol=document['symbol'],
        base=document['base'],
        market=document['market'],
        exchange=document['exchange'],
        interval=document['interval'],
        dateTime=document['dateTime'],
        open=document['open'],
        high=document['high'],
        low=document['low'],
        close=document['close'],
    )


def compose_collection_name(request: OhlcRequest) -> str:
    return f"ohlc_{request.asset.lower()}_{request.quote.lower()}_{request.market.lower()}_{request.interval.lower()}_{request.exchange.lower()}"


class MongoConnector:
    def __init__(self):
        load_dotenv(dotenv_path=".env")
        self.__mongo_host: str = os.getenv('MONGO_HOST')
        self.__mongo_user: str = os.getenv('MONGO_USER')
        self.__mongo_pass: str = os.getenv('MONGO_PASSWORD')
        self.client: MongoClient = self._connect_to_mongo()
        self.db = self.client['tradingapp']

    def _connect_to_mongo(self) -> MongoClient:
        try:
            mongo_uri: str = f"mongodb+srv://{self.__mongo_user}:{self.__mongo_pass}@{self.__mongo_host}"
            client: MongoClient = MongoClient(mongo_uri)
            client.admin.command('ping')
            print("Connected to MongoDB")
            return client
        except ConnectionFailure as e:
            print(f"Could not connect to MongoDB: {e}")
            raise

    def find_all_ohlc_data(self, request: OhlcRequest) -> List[OhlcEntity]:
        collection_name = compose_collection_name(request)
        collection: Collection = self.db[collection_name]

        # Find all documents sorted by dateTime in ascending order
        documents = collection.find().sort("dateTime", ASCENDING)

        # Convert each document to an OhlcEntity
        result = [_document_to_entity(doc) for doc in documents]

        return result

    def find_ohlc_data(self, request: OhlcRequest) -> List[OhlcEntity]:
        collection_name = compose_collection_name(request)
        collection: Collection = self.db[collection_name]

        batch_size = 40000  # Adjust batch size as needed
        result = []
        start_time_for_new_batch = request.start_time - timedelta(seconds=1)

        while True:
            query = {
                "dateTime": {"$gte": start_time_for_new_batch + timedelta(seconds=1)}
            }
            if request.end_time:
                query["dateTime"]["$lt"] = request.end_time

            documents = collection.find(query).sort("dateTime", ASCENDING).limit(batch_size)
            batch = [_document_to_entity(doc) for doc in documents]

            if not batch:
                break
            result.extend(batch)
            if len(batch) < batch_size:
                break
            start_time_for_new_batch = batch[-1].dateTime

        return result
