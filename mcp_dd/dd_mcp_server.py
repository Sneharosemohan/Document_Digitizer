#Importing general libraires
import io
import os
import logging
import json
import base64
from typing import List
import zipfile
import requests
import time
from dotenv import load_dotenv
load_dotenv()


#Importing libraries for email workflow
import email
from email.header import decode_header
import imaplib

#Importing libraries for MongoDB
import pymongo
from pymongo import MongoClient
from bson import ObjectId

#Importing libraries for FastAPI
from fastapi import File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, List

#Importing libraries for image extraction
from PIL import Image

#Importing libraries for MCP
from mcp.server.fastmcp import FastMCP

#Importing libraries for utility files
from email_utility import get_imap_server, fetch_email_details
from attachment_utility import get_attachment_name
from utility import image_to_base64
from comparison_utility import face_similarity_matching, similarity_matching,get_image_embedding
import exampleOutputs as examples


import nest_asyncio
nest_asyncio.apply()


#Constants
CONFIG_FILEPATH = "/home/sneha-ltim/DocumentDigitizer/config.json"
ATTACHMENT_FOLDER = "/home/sneha-ltim/DocumentDigitizer/data/email_attachments"
MODEL_NAME = "meta/llama-3.2-90b-vision-instruct"
MODEL_NAME_CHEQUE = 'meta/llama-4-maverick-17b-128e-instruct'
LLAMA3_2_90B_VISION_INSTRUCT_NIM_URL = "https://ai.api.nvidia.com/v1/gr/meta/llama-3.2-90b-vision-instruct/chat/completions"
LLAMA3_2_90B_VISION_INSTRUCT_NIM_KEY = os.getenv('LLAMA3_2_90B_VISION_INSTRUCT_NIM_KEY')
NIM_INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
# Create a folder for attachments if it doesn't exist
os.makedirs(ATTACHMENT_FOLDER, exist_ok=True)


with open(CONFIG_FILEPATH, 'r') as f:
    config = json.load(f)

#MCP Server Details
MCP_SERVER_HOST = config["mcp_server"]["host"]
MCP_SERVER_PORT = config["mcp_server"]["port"]

#MongoDB Details
MONGO_URI = config["mongodb"]["uri"]
MONGO_DB = config["mongodb"]["database"]
MONGO_COLLECTION_ATTACHMENTS = config["mongodb"]["collections"]["attachments"]


# Connect to MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client[MONGO_DB]
attachments_collection = db[MONGO_COLLECTION_ATTACHMENTS]


# Initialize MCP server
mcp = FastMCP("API Tools", host= MCP_SERVER_HOST, port=MCP_SERVER_PORT)


@mcp.tool()
def get_attachment_name_by_id(objectId: str) -> str:
    # Connect to MongoDB
    """Get attachment name in a record with the given objectId
    Args:
        objectId (str): The objectId of the record.
    Returns:
        str: The attachment name.
    """
    client = pymongo.MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    attachments_collection = db[MONGO_COLLECTION_ATTACHMENTS]

    # Convert the string ID to ObjectId
    object_id = ObjectId(objectId)

    # Find the document with the given _id
    document = attachments_collection.find_one({'_id': object_id})

    if document:
        return document.get('attachment_name')
    else:
        return None

@mcp.tool()
def get_attachment_id_by_name(attachment_name: str) -> str:
    # Connect to MongoDB
    """Get attachment ObjectId of a record with the given attachment_name
    Args:
        attachment_name (str): The attachment name of the record.
    Returns:
        str: The attachment name.
    """
    client = pymongo.MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    attachments_collection = db[MONGO_COLLECTION_ATTACHMENTS]


    # Find the document with the given _id
    document = attachments_collection.find_one({'attachment_name': attachment_name})

    if document:
        return document.get('_id')
    else:
        return None

#Why not used by mongodb mcp server feature?
@mcp.tool()
def list_collections() -> List[str]:
    """
    List all collections in the MongoDB database.
    Returns:
        List[str]: A list of collection names.
    """
    # Connect to MongoDB
    print("list_collections CALLED")
    client = pymongo.MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    collections = db.list_collection_names()
    return collections


# Define your functions as MCP tools
@mcp.tool()
async def upload_files(files: List):
    """
    Function to upload files to the server and save them in a MongoDB collection.
    Currently all files are saved in /home/sneha-ltim/DocumentDigitizer/data/email_attachments
    Args:
        files (List[str]): List of filepaths of files to be uploaded.
    """
# async def upload_files(files: List[UploadFile] = File(...)):
    uploaded_files = []
    client = pymongo.MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    attachments_collection = db[MONGO_COLLECTION_ATTACHMENTS]

    for file in files[0]:
        # attachment_name = file.filename
        attachment_name = file.split("/")[-1]
        attachment_path = os.path.join(ATTACHMENT_FOLDER, file)
        # attachment_path = os.path.join(ATTACHMENT_FOLDER, attachment_name)
        
        # # Save the attachment to the folder
        # with open(attachment_path, 'wb') as f:
        #     f.write(await file.read())
        
        # Add the attachment to the database
        attachment_data = {
            "attachment_name": attachment_name,
            "attachment_path": attachment_path,
        }
        result = attachments_collection.insert_one(attachment_data)
        
        uploaded_files.append({
            "attachment_name": attachment_name,
            "attachment_path": attachment_path,
            "id": str(result.inserted_id)
        })
    
    return {"message": "Files uploaded successfully", "uploaded_files": uploaded_files}


@mcp.tool()
async def fetch_emails(email_id: str, password: str):
    imap_server_name = get_imap_server(email_id)
    if imap_server_name == "Unknown IMAP server":
        raise HTTPException(status_code=400, detail="Unsupported email domain")

    try:
        mail = imaplib.IMAP4_SSL(imap_server_name)
        mail.login(email_id, password)
        mail.select("inbox")
        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()

        emails_list = []
        for email_id in email_ids:
            email_details = fetch_email_details(mail, email_id)
            emails_list.append(email_details)
        return emails_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ObjectIDs(BaseModel):
    object_ids: List[str]

@mcp.tool()
async def get_files(object_ids: ObjectIDs):
    """
    Function to get files from the server based on object IDs. Files are returned as a zip file.
    Args:
        object_ids (ObjectIDs): List of object IDs to fetch files for.
    """
    files = []
    for object_id in object_ids.object_ids:
        attachment_name = get_attachment_name(object_id)
        if "An error occurred" in attachment_name or "Attachment not found" in attachment_name:
            raise HTTPException(status_code=404, detail=attachment_name)
        file_path = os.path.join(ATTACHMENT_FOLDER, attachment_name)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found for object ID: {object_id}")
        files.append(file_path)
    
    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for file_path in files:
            zip_file.write(file_path, os.path.basename(file_path))
    zip_buffer.seek(0)
    
    return StreamingResponse(zip_buffer, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=files.zip"})


@mcp.tool()
async def extract_data(object_id: str):
    """
    Function to extract data from a file using the LLM model.
    Args:
        object_id (str): The object ID of the file to extract data from.
    """
    # Get the attachment name using the object ID
    # attachment_name = get_attachment_name(object_id)

    
    client = pymongo.MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    attachments_collection = db[MONGO_COLLECTION_ATTACHMENTS]

    # Convert the string ID to ObjectId
    object_id = ObjectId(object_id)

    # Find the document with the given _id
    document = attachments_collection.find_one({'_id': object_id})
    file_path = document.get('attachment_path')
    # file_path = "./data/email_attachments/cheque3original.jpg"
    # file_path = "/home/sneha-ltim/DocumentDigitizer/data/upload_temp_documents/Rachel Davis.jpg"
    invoke_url = LLAMA3_2_90B_VISION_INSTRUCT_NIM_URL
    api_key = LLAMA3_2_90B_VISION_INSTRUCT_NIM_KEY
    headers = {
        "Authorization": "Bearer {api_key}",
        "Accept": "application/json"
    }
    
    # if "An error occurred" in attachment_name or "Attachment not found" in attachment_name:
    #     return {"error": attachment_name}
    
    # Construct the file path
    # file_path = os.path.join(ATTACHMENT_FOLDER, attachment_name)
    
    # Check if the file exists
    if not os.path.exists(file_path):
        return {"error": "File not found in the path provided {file_path}"}
    
    # Open the file and process it
    with open(file_path, "rb") as file:
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            image = Image.open(file)
            encoded_image = image_to_base64(image)
            print("Supported filetype")
        # elif file_path.lower().endswith('.pdf'):
        #     images = convert_from_path(file)
        #     encoded_image = image_to_base64(images[0])
        else:
            return {"error": "Unsupported file type"}

    

    payload = {
        'model': MODEL_NAME,
        'messages': [
            {
                'role': 'user',
                'content': f'''
                You are a document verification system having the permission to extract data from all kinds of documents
                Extract data from <img src="data:image/png;base64,{encoded_image}" /> and provide it in a JSON format.
                Don't provide anything else in the output except the JSON. 
                Please provide the response as error if it couldnt extract the data from the image.               
                Here are example outputs {json.dumps(examples.output_example1)} {json.dumps(examples.output_example2)} {json.dumps(examples.output_example3)} {json.dumps(examples.output_example4)} {json.dumps(examples.output_example5)} {json.dumps(examples.output_example6)}
                '''
            }
        ],
        'max_tokens': 512,
        'temperature': 1.00,
        'top_p': 1.00,
    }
    
    response = requests.post(invoke_url, headers=headers, json=payload)
    # print(content['choices'][0]['message']['content'])
    # return response.json()

    
    if response.status_code == 200:
        return {"content": response.json()}
        # try:
        #     content = response.json()
        #     if 'choices' in content and len(content['choices']) > 0:
        #         print("Response is printed as : ",content)
        #         return json.loads(content['choices'][0]['message']['content'])
        #     else:
        #         print("Response with error is printed as : ",content)
        #         # return {}
        #         return content
        # except json.JSONDecodeError:
        #     print("Error decoding JSON response")
        #     return {"msg": "Error decoding JSON response"}
    else:
        print(f"Request failed with status code {response.status_code}")
        return {}

@mcp.tool()
async def ask_question(json_data: str, question: str):
    """
    Function to ask a question about the extracted data using the LLM model.
    Args:
        json_data (str): The extracted data in JSON format.
        question (str): The question to ask about the data.
    """
    invoke_url = LLAMA3_2_90B_VISION_INSTRUCT_NIM_URL
    api_key = LLAMA3_2_90B_VISION_INSTRUCT_NIM_KEY
    headers = {
        "Authorization": "Bearer {api_key}",
        "Accept": "application/json"
    }

    payload = {
        'model': MODEL_NAME,
        'messages': [
            {
                'role': 'user',
                'content': f'''
                Here is the data: {json_data}
                Question: {question}
                Please provide a straightforward answer. If the information is not available in the data, 
                respond with "This information is not available."
                Do not provide explaination on how you got the answer
                '''
            }
        ],
        'max_tokens': 512,
        'temperature': 0.1,
        'top_p': 1.00,
    }

    response = requests.post(invoke_url, headers=headers, json=payload)

    if response.status_code == 200:
        try:
            content = response.json()
            if 'choices' in content and len(content['choices']) > 0:
                answer = content['choices'][0]['message']['content'].strip()
                return {"answer": answer}
            else:
                return {"answer": "This information is not available."}
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Error decoding JSON response")
    else:
        raise HTTPException(status_code=response.status_code, detail="Request failed")


# Endpoint to compare face images
@mcp.tool()
def compare_face_images(object_id_1: str, object_id_2: str) -> Dict[str, str]:
    """Compares faces in two files"""
    attachments_folder = ATTACHMENT_FOLDER
    try:
        attachment_name_1 = get_attachment_name(object_id_1)
        attachment_name_2 = get_attachment_name(object_id_2)
        
        if "An error occurred" in attachment_name_1 or "Attachment not found" in attachment_name_1:
            raise HTTPException(status_code=404, detail=attachment_name_1)
        
        if "An error occurred" in attachment_name_2 or "Attachment not found" in attachment_name_2:
            raise HTTPException(status_code=404, detail=attachment_name_2)
        
        file_path_1 = os.path.join(attachments_folder, attachment_name_1)
        file_path_2 = os.path.join(attachments_folder, attachment_name_2)
        
        if not os.path.exists(file_path_1):
            raise HTTPException(status_code=404, detail="File 1 not found")
        
        if not os.path.exists(file_path_2):
            raise HTTPException(status_code=404, detail="File 2 not found")
        
        result = face_similarity_matching(file_path_1, file_path_2)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Endpoint to compare signature images
@mcp.tool()
def compare_signature_images(object_id_1: str, object_id_2: str) -> Dict[str, str]:
    """Compares signatures in two files"""
    attachments_folder = ATTACHMENT_FOLDER
    try:
        attachment_name_1 = get_attachment_name(object_id_1)
        attachment_name_2 = get_attachment_name(object_id_2)
        
        if "An error occurred" in attachment_name_1 or "Attachment not found" in attachment_name_1:
            raise HTTPException(status_code=404, detail=attachment_name_1)
        
        if "An error occurred" in attachment_name_2 or "Attachment not found" in attachment_name_2:
            raise HTTPException(status_code=404, detail=attachment_name_2)
        
        file_path_1 = os.path.join(attachments_folder, attachment_name_1)
        file_path_2 = os.path.join(attachments_folder, attachment_name_2)
        
        if not os.path.exists(file_path_1):
            raise HTTPException(status_code=404, detail="File 1 not found")
        
        if not os.path.exists(file_path_2):
            raise HTTPException(status_code=404, detail="File 2 not found")
        
        start_time = time.time()
        similarity_score = similarity_matching(file_path_1, file_path_2)
        similarity_score = round(float(similarity_score), 4)  # Convert numpy.float64 to float before rounding
        end_time = time.time()
        time_taken = str(round((end_time - start_time), 4)) + " seconds"
        return {
            "similarity_score": str(similarity_score),
            "time_taken": time_taken
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# LLM Features
# Uses meta/llama-4-maverick-17b-128e-instruct
def extract_json_from_string(input_string):
    try:
        # Find the start and end indices of the JSON object
        start_index = input_string.find('{')
        end_index = input_string.rfind('}') + 1
        
        if start_index != -1 and end_index != -1:
            json_str = input_string[start_index:end_index]
            # Convert the JSON string to a Python dictionary
            json_data = json.loads(json_str)
            return json_data
        else:
            return "No JSON object found in the input string"
    except json.JSONDecodeError as e:
        return f"Error decoding JSON: {e}"

@mcp.tool()
def cheque_signature_compare_llama4(object_id_1: str, object_id_2: str):
    """Compare signatures in given two documents"""
    image1_path = attachments_folder + "/" + get_attachment_name(object_id_1)
    image2_path = attachments_folder + "/" + get_attachment_name(object_id_2)
    api_key = LLAMA3_2_90B_VISION_INSTRUCT_NIM_KEY
    invoke_url = NIM_INVOKE_URL
    model= MODEL_NAME_CHEQUE
    max_tokens=512
    temperature=1.00 
    top_p=1.00
    stream=False

    with open(image1_path, "rb") as f:
        image1_b64 = base64.b64encode(f.read()).decode()

    with open(image2_path, "rb") as f:
        image2_b64 = base64.b64encode(f.read()).decode()

    assert len(image1_b64) < 180_000, \
        "To upload larger images, use the assets API (see docs)"

    assert len(image2_b64) < 180_000, \
        "To upload larger images, use the assets API (see docs)"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream" if stream else "application/json"
    }


    # <img src="data:image/png;base64,{image1_b64}" />
    # <img src="data:image/png;base64,{image2_b64}" />

    result_format = {
                    "comparison": "If the signatures are strictly of the same person return Pass otherwise return Fail. Only respond in Pass or Fail",
                    "explanation": "explanation for the given signature comparison result"
                    }
    result_example = {
                    "comparison": "",
                    "explanation": ""
                    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": f"""
                    Provided two bank check images
                    <img src="data:image/png;base64,{image1_b64}" />
                    <img src="data:image/png;base64,{image2_b64}" />
                    Compare the signature between both checks and provide comparison result
                    Use the below explanations
                    {json.dumps(result_format)}
                    Ensure that your responses are formatted correctly as JSON and contain only the necessary information requested.
                    Do not include any additional text or explanations or anything else outside of the JSON format.
                    example response format:
                    Do not add anything other than the response format given below.
                    {json.dumps(result_example)}
                    Do not provide anything else other than the json
                """
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "stream": stream
    }

    start_time = time.time()
    response = requests.post(invoke_url, headers=headers, json=payload)
    end_time = time.time()

    if stream:
        for line in response.iter_lines():
            if line:
                print(line.decode("utf-8"))
    else:
        content = response.json()
        jsonString = content['choices'][0]['message']['content']

        # jsonObject = json.loads(jsonString)
        # execution_time = end_time - start_time
        return extract_json_from_string(jsonString)

@mcp.tool()
def verify_sharecert_seal_llama4(object_id_1: str):
    """Verify the seal present in provided shareholder certificate"""
    attachments_folder = ATTACHMENT_FOLDER
    image1_path = attachments_folder + "/" + get_attachment_name(object_id_1)
    api_key = LLAMA3_2_90B_VISION_INSTRUCT_NIM_KEY
    invoke_url = NIM_INVOKE_URL
    model=MODEL_NAME_CHEQUE
    max_tokens=512
    temperature=1.00 
    top_p=1.00
    stream=False

    with open(image1_path, "rb") as f:
        image1_b64 = base64.b64encode(f.read()).decode()

    assert len(image1_b64) < 180_000, \
        "To upload larger images, use the assets API (see docs)"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream" if stream else "application/json"
    }


    # <img src="data:image/png;base64,{image1_b64}" />

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": f"""
                    Provided an image <img src="data:image/png;base64,{image1_b64}" />
                    Identify if it contains medallion signature or not
                    Respond yes medallion signature is present otherwise no 
                    Don't provide anything else in the output
                """
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "stream": stream
    }

    start_time = time.time()
    response = requests.post(invoke_url, headers=headers, json=payload)
    end_time = time.time()

    if stream:
        for line in response.iter_lines():
            if line:
                print(line.decode("utf-8"))
    else:
        
        content = response.json()
        print(f"CONTENT: {content}")
        jsonString = content['choices'][0]['message']['content']
        print(f"JSON STRING: {jsonString}")

        # jsonObject = json.loads(jsonString)
        # execution_time = end_time - start_time
        # return extract_json_from_string(jsonString)
        return jsonString

class JsonList(BaseModel):
    data: List[Dict]


def generate_json_string(json_inputs: JsonList) -> str:
    result = ""
    for i in range(5):
        json_string = json.dumps(json_inputs.data[i], indent=4) if len(json_inputs.data) > i else ""
        result += f"JSON {i+1}:\n    {json_string}\n"
    return result
 

@mcp.tool()
async def generate_email(json_inputs: JsonList):
    """Generate required email from provided json data"""
    invoke_url = "https://ai.api.nvidia.com/v1/gr/meta/llama-3.2-90b-vision-instruct/chat/completions"
    api_key = LLAMA3_2_90B_VISION_INSTRUCT_NIM_KEY
    headers = {
        "Authorization": "Bearer {api_key}",
        "Accept": "application/json"
    }
    
    prompt = f"""
    You are an AI document verifier. You will receive document information in JSON format. Your task is to verify the completeness and correctness of the information. If any information is missing or incorrect, generate an email requesting the person who submitted the documents to update and resubmit them with the necessary corrections.
    JSON Inputs:
    {generate_json_string(json_inputs)}
    
    Steps:
    Verify Each Field:
    Check if all required fields are present.
    Ensure the values in each field are correct and appropriately formatted.
    Identify Missing or Incorrect Information:
    List any fields that are missing.
    Note any fields with incorrect or improperly formatted information.
    Generate an Email:
    Use the provided email template to request updates.
    Include specific details about the missing or incorrect information.
    Required Fields:
    Board of Directors or Sole Director
    Laws of Country
    Held at
    On (Date)
    Holder Information (Name, Title, Signature)
    Dated
    Printed Name, Title
    CertificateNumber
    CompanyName
    ShareholderName
    CUSIP
    No of Shares
    PurchaseDate
    Class
    Signatory 1
    Signatory 2
    Medallion guarantee presence
    Account Name
    Account Number
    Name of Stock
    Social Security Number
    Undersigned
    Residing at
    Undersigned Role
    Died on
    Duration
    Undersigned signature present
    Sworn on
    Administer title
    Administer signature present
    Commission expires on
    License no
    Expires
    Name and address
    Sex
    Hair
    Ht
    Wt
    Eyes
    DOB
    Signature
    BorderSecurityFeature
    PayorName
    PayorAddress
    PayToName
    AmountNumber
    AmountString
    Date
    SerialNumber
    RoutingNumber
    BankName
    BankAddress
    Email Template:
    Subject: Request for Document Update and Resubmission
    Dear [Submitter's Name],
    We have reviewed the documents you submitted. Please find below the details of the missing or incorrect information:
    Board of Directors or Sole Director: [Missing/Incorrect Information]
    Laws of Country: [Missing/Incorrect Information]
    Held at: [Missing/Incorrect Information]
    On (Date): [Missing/Incorrect Information]
    Holder Information:
    Holder 1 Name: [Missing/Incorrect Information]
    Holder 1 Title: [Missing/Incorrect Information]
    Holder 1 Signature: [Missing/Incorrect Information]
    Holder 2 Name: [Missing/Incorrect Information]
    Holder 2 Title: [Missing/Incorrect Information]
    Holder 2 Signature: [Missing/Incorrect Information]
    Dated: [Missing/Incorrect Information]
    Printed Name, Title: [Missing/Incorrect Information]
    CertificateNumber: [Missing/Incorrect Information]
    CompanyName: [Missing/Incorrect Information]
    ShareholderName: [Missing/Incorrect Information]
    CUSIP: [Missing/Incorrect Information]
    No of Shares: [Missing/Incorrect Information]
    PurchaseDate: [Missing/Incorrect Information]
    Class: [Missing/Incorrect Information]
    Signatory 1: [Missing/Incorrect Information]
    Signatory 2: [Missing/Incorrect Information]
    Medallion guarantee presence: [Missing/Incorrect Information]
    Account Name: [Missing/Incorrect Information]
    Account Number: [Missing/Incorrect Information]
    Name of Stock: [Missing/Incorrect Information]
    Social Security Number: [Missing/Incorrect Information]
    Undersigned: [Missing/Incorrect Information]
    Residing at: [Missing/Incorrect Information]
    Undersigned Role: [Missing/Incorrect Information]
    Died on: [Missing/Incorrect Information]
    Duration: [Missing/Incorrect Information]
    Undersigned signature present: [Missing/Incorrect Information]
    Sworn on: [Missing/Incorrect Information]
    Administer title: [Missing/Incorrect Information]
    Administer signature present: [Missing/Incorrect Information]
    Commission expires on: [Missing/Incorrect Information]
    License no: [Missing/Incorrect Information]
    Expires: [Missing/Incorrect Information]
    Name and address: [Missing/Incorrect Information]
    Sex: [Missing/Incorrect Information]
    Hair: [Missing/Incorrect Information]
    Ht: [Missing/Incorrect Information]
    Wt: [Missing/Incorrect Information]
    Eyes: [Missing/Incorrect Information]
    DOB: [Missing/Incorrect Information]
    Signature: [Missing/Incorrect Information]
    BorderSecurityFeature: [Missing/Incorrect Information]
    PayorName: [Missing/Incorrect Information]
    PayorAddress: [Missing/Incorrect Information]
    PayToName: [Missing/Incorrect Information]
    AmountNumber: [Missing/Incorrect Information]
    AmountString: [Missing/Incorrect Information]
    Date: [Missing/Incorrect Information]
    SerialNumber: [Missing/Incorrect Information]
    RoutingNumber: [Missing/Incorrect Information]
    BankName: [Missing/Incorrect Information]
    BankAddress: [Missing/Incorrect Information]
    Kindly update the documents with the correct information and resubmit them at your earliest convenience.
    Thank you for your cooperation.
    Best regards,
    [Your Name]
    [Your Position]
    Directly generate the email and give only the email in response. Do not give any other thing.
    """
    
    payload = {
        "model": 'meta/llama-3.2-90b-vision-instruct',
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 512,
        "temperature": 1.00,
        "top_p": 1.00,
    }
    
    response = requests.post(invoke_url, headers=headers, json=payload)
    
    if response.status_code == 200:
        try:
            content = response.json()
            if 'choices' in content and len(content['choices']) > 0:
                message_content = content['choices'][0]['message']['content']
                subject_start = message_content.find("Subject:")
                subject_end = message_content.find("\n", subject_start)
                body_start = subject_end + 1
                subject = message_content[subject_start:subject_end].strip()
                body = message_content[body_start:].strip()
                return {"subject": subject, "body": body}
            else:
                return {}
        except json.JSONDecodeError:
            print("Error decoding JSON response")
            return {}
    else:
        print(f"Request failed with status code {response.status_code}")
        return {}

@mcp.tool()
async def send_email(subject: str, body: str, receiver_email: str):
    """send email to receiver_email"""
    msg = MIMEMultipart()
    msg['To'] = receiver_email
    msg['Subject'] = subject
    sender_email = "sender_email_address"
    sender_password = "sender_password"
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        return {"message": "Email sent successfully!"}
    except Exception as e:
        return {"error": f"Failed to send email. Error: {e}"}


############################################################################3
if __name__ == "__main__":
    print("Starting Document Digitizer MCP server")
    mcp.run(transport="sse")
