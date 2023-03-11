
from pprint import pprint
from typing import List, Union
from urllib.parse import quote_plus

from pydantic import validate_arguments
from pymongo import MongoClient, cursor
from pymongo.errors import (CollectionInvalid, OperationFailure,
                            ServerSelectionTimeoutError)

from .config import settings


class MongoDB:
    client = None

    def __init__(self, db_name=None):
        self._db = None
        self._collection = None
        if db_name is not None:
            self._db = self.__create_db(db_name)

    @staticmethod
    def mongodb_connect(user, password, host, port):
        try:
            uri = f"mongodb://{host}:{port}"
            if user and password:
                user = quote_plus(user)
                password = quote_plus(password)
                uri = f"mongodb://{user}:{password}@{host}:{port}"
            client = MongoClient(uri)
            client.server_info()
            MongoDB.client = client
        except Exception as e:
            print('Invalid username or password')
            print(e)

    @staticmethod
    def mongodb_disconnect():
        if MongoDB.client:
            MongoDB.client.close()

    def has_database(self, db_name):
        dblist = MongoDB.client.list_database_names()
        if db_name in dblist:
            return True
        else:
            return False

    def __create_collections(self, collection_list=None):
        for each in settings.collections:
            try:
                if self.__check_collection(each):
                    continue
            except ValueError as e:
                self.create_node_type(each)
                continue

    def __create_db(self, db_name):
        if not self.has_database(db_name):
            self._db = MongoDB.client[db_name]
            self.__create_collections()
        return MongoDB.client[db_name]

    def delete_db(self, db_name):
        if not self.has_database(db_name):
            raise ValueError('Invalid db_name or database does not exists')
        else:
            try:
                MongoDB.client.drop_database(db_name)
            except Exception as e:
                print("Db could not be deleted ", e)

    def create_node_type(self, node_type):
        try:
            self._collection = self._db.create_collection(node_type)
        except CollectionInvalid as e:
            raise ValueError(
                f'Collection or node_type: {node_type} already exit')

    def create_node(self, node_type_name, properties):
        try:
            self.__check_collection(node_type_name)
            node_type = self._db[node_type_name]
            if isinstance(properties, dict):
                result = node_type.insert_one(properties).inserted_id
            else:
                result = node_type.insert_many(properties).inserted_ids
            return result
        except ValueError as e:
            print(e)
            return None

    def get_db(self, db_name):
        if not self.has_database(db_name):
            raise ValueError('Invalid db_name or database does not exists')
        else:
            return MongoDB.client[db_name]

    def __check_collection(self, node_type):
        try:
            collections = self._db.list_collection_names()
            if node_type in collections:
                return True
            else:
                raise ValueError(f'Invalid node_type_name: {node_type}')
        except:
             # DB is not yet created
             raise ValueError(f'Invalid node_type_name: {node_type}')

    def get_node_type(self, node_type_name):
        if self.__check_collection(node_type_name):
            return self._db[node_type_name]
        else:
            raise ValueError(f'Node {node_type_name} does not exists')

    def get_node(self, dict_, node_type_name):
        node = None
        try:
            node_type = self.get_node_type(node_type_name)
            node_cursor = node_type.find(dict_)
            node = node_cursor.next()
            return node
        except Exception:
            return node

    def has_node(self, dict_, node_type_name):
        node = self.get_node(dict_, node_type_name)
        if node is None:
            return False
        else:
            return True

    def update_node(self, dict_, node, node_type_name):
        status = False
        try:
            node_type = self.get_node_type(node_type_name)
            updated_data = node_type.find_one_and_update(
                node, {'$set': dict_}, upsert=False,)
            if updated_data:
                status = True
        except Exception as e:
            print(e)
            status = False
        return status

    def delete_node(self, node, node_type_name):
        status = False
        try:
            node_type = self.get_node_type(node_type_name)
            node_type.delete_one(node)
            status = True
        except Exception as e:
            status = False
        return status

    def get_all_nodes(self, node_type_name, filter_query=None):
        node_type = self.get_node_type(node_type_name)
        node_cursor = node_type.find({})
        if filter_query:
            node_cursor = node_type.find(filter_query)
        documents = []
        for doc in node_cursor:
            documents.append(doc)
        return documents


@validate_arguments
def validate_nonempty_str(db_name: str):
    if db_name.__len__() == 0:
        raise ValueError('db_name can not be empty')
