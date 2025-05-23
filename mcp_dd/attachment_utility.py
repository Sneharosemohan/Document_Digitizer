#Importing libraries for MongoDB
import pymongo
from pymongo import MongoClient
from bson import ObjectId
import json


CONFIG_FILEPATH = "./config.json"

with open(CONFIG_FILEPATH, 'r') as f:
    config = json.load(f)

#MongoDB Details
MONGO_URI = config["mongodb"]["uri"]
MONGO_DB = config["mongodb"]["database"]
MONGO_COLLECTION_ATTACHMENTS = config["mongodb"]["collections"]["attachments"]


# Connect to MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client[MONGO_DB]
attachments_collection = db[MONGO_COLLECTION_ATTACHMENTS]


def get_attachment_name(object_id):
    try:
        # Convert the string object_id to an ObjectId
        obj_id = ObjectId(object_id)
        
        # Find the document with the given object_id
        attachment = attachments_collection.find_one({"_id": obj_id})
        
        if attachment:
            return attachment.get("attachment_name", "Attachment name not found")
        else:
            return "Attachment not found"
    except Exception as e:
        return f"An error occurred: {e}"