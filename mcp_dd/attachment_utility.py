#Importing libraries for MongoDB
import pymongo
from pymongo import MongoClient
from bson import ObjectId
import json
from dotenv import load_dotenv
load_dotenv()
import os
import sys
from PIL import Image
import requests
import nest_asyncio
nest_asyncio.apply()


from utility import image_to_base64
#Constants
# Get the directory of the current script
BASE_DIR = os.getcwd()

CONFIG_FILEPATH = os.path.join(BASE_DIR, "config.json")
ATTACHMENT_FOLDER = os.path.join(BASE_DIR, "data/upload_documents")


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


## CONSTANT
LLAMA3_2_90B_VISION_INSTRUCT_NIM_KEY = os.getenv('LLAMA3_2_90B_VISION_INSTRUCT_NIM_KEY')
LLAMA3_2_90B_VISION_INSTRUCT_NIM_URL = "https://ai.api.nvidia.com/v1/gr/meta/llama-3.2-90b-vision-instruct/chat/completions"


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


def get_document_type(attachment_name: str):
    # Get the attachment name using the object ID

    api_key = LLAMA3_2_90B_VISION_INSTRUCT_NIM_KEY
    invoke_url = LLAMA3_2_90B_VISION_INSTRUCT_NIM_URL
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    
    # if "An error occurred" in attachment_name or "Attachment not found" in attachment_name:
    #     return {"error": attachment_name}
    
    # Construct the file path
    file_path = os.path.join(ATTACHMENT_FOLDER, attachment_name)
    
    # Check if the file exists
    if not os.path.exists(file_path):
        return {"error": "File not found"}
    
    # Open the file and process it
    with open(file_path, "rb") as file:
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            image = Image.open(file)
            encoded_image = image_to_base64(image)
        elif file_path.lower().endswith('.pdf'):
            images = convert_from_path(file)
            encoded_image = image_to_base64(images)
        else:
            return {"error": "Unsupported file type"}

    payload = {
        'model': 'meta/llama-3.2-90b-vision-instruct',
        'messages': [
            {
                'role': 'user',
                'content': f'''
                You are a document verification system. Identify the type of document from the provided image.
                Respond in one word
                Choose word from ["passport", "driver's license", "cheque", "corporate resolution", "PAN card", "adhaar card", "shareholder's certificate", "affidavit"]
                Do not add any extra characters like "." in the output
                <img src="data:image/png;base64,{encoded_image}" />
                '''
            }
        ],
        'max_tokens': 512,
        'temperature': 1.00,
        'top_p': 1.00,
    }
    
    response = requests.post(invoke_url, headers=headers, json=payload)
    
    if response.status_code == 200:
        try:
            content = response.json()
            if 'choices' in content and len(content['choices']) > 0:
                return {"document_type": content['choices'][0]['message']['content']}
            else:
                return {"error": "No document type identified"}
        except json.JSONDecodeError:
            return {"error": "Error decoding JSON response"}
    else:
        return {"error": f"Request failed with status code {response.status_code}"}
