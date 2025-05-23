import io
import base64
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
# attachments_collection = db[MONGO_COLLECTION_ATTACHMENTS]

# Function to convert image to base64
def image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

