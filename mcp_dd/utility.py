import io
import base64
#Importing libraries for MongoDB
import pymongo
from pymongo import MongoClient
from bson import ObjectId
import json
from PIL import Image
import os
import nest_asyncio
nest_asyncio.apply()

#Constants
# Get the directory of the current script
BASE_DIR = os.getcwd()

CONFIG_FILEPATH = os.path.join(BASE_DIR, "config.json")



with open(CONFIG_FILEPATH, 'r') as f:
    config = json.load(f)

#MongoDB Details
MONGO_URI = config["mongodb"]["uri"]
MONGO_DB = config["mongodb"]["database"]
MONGO_COLLECTION_ATTACHMENTS = config["mongodb"]["collections"]["attachments"]


# Connect to MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client[MONGO_DB]
# attachments_collection = db[MONGO_COLLECTION_ATTACHMENTS]

# Function to convert image to base64
def image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

