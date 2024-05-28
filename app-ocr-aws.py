
import streamlit as st
import boto3
import io
from PIL import Image
import docx
import time
from dotenv import load_dotenv
import os
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.exceptions import HttpResponseError
import pinyin
import re
import typing

# Load environment variables from .env file
load_dotenv()

# Read AWS credentials from environment variables
# aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
# aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
# region_name = os.getenv('AWS_REGION')
aws_access_key_id = st.secrets["AWS_ACCESS_KEY_ID"]
aws_secret_access_key = st.secrets["AWS_SECRET_ACCESS_KEY"]
region_name = st.secrets["AWS_REGION"]

# Set the values of your computer vision endpoint and computer vision key
# as environment variables:
try:
    endpoint = "https://test-viseo-ai-services.cognitiveservices.azure.com/" #Paste your AI services endpoint here
    key = "d0095ddc07bf4b01a73355dceabe041b" #Paste your AI services resource key here
except KeyError:
    print("Missing ENDPOINT' or 'KEY'")
    print("Set them before running this sample.")
    exit()

title = '<p style="font-size: 40px;font-weight: 550;"> AWS Textract - Extract Text via Images</p>'
st.markdown(title, unsafe_allow_html=True)

st.image("./assets/textract.png")

# Provide AWS credentials directly
aws_management_console = boto3.session.Session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=region_name  # Replace with your desired region
)

client = aws_management_console.client(service_name='textract', region_name='ap-southeast-1')

# Create S3 client
s3_client = aws_management_console.client('s3')


# Define a function to extract text from an image
def extract_text_from_image(image):
    response = client.detect_document_text(Document={"Bytes": image})

    # Extract the text from the response
    text = ""

    for item in response["Blocks"]:
        if item["BlockType"] == "LINE":
            text += item["Text"] + "\n"

    # Display the extracted text
    st.subheader("Extracted Text")
    st.write(text)
    download_text(text)


def download_text(text):
    doc = docx.Document()
    doc.add_paragraph(text)

    output_file = io.BytesIO()
    doc.save(output_file)
    output_file.seek(0)
    st.download_button(
        label="Download Doc File",
        data=output_file,
        file_name="extracted_text.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

def has_unicode_group(text):
    for char in text:
        for name in ('CJK','CHINESE','KATAKANA','HANGUL',):
            if name in unicodedata.name(char):
                return name
    return ''

def extract_text_from_pdf(pdf_bytes, pdf_filename):
    
    # Create a file-like object from the bytes
    pdf_fileobj = io.BytesIO(pdf_bytes)

    # Upload PDF file to S3 bucket
    bucket_name = 'pdf-stuff'  # Replace with your S3 bucket name
    s3_key = 'uploads/' + pdf_filename
    s3_client.upload_fileobj(pdf_fileobj, bucket_name, s3_key)

    # Start text detection job with S3 object
    response = client.start_document_text_detection(
        DocumentLocation={
            'S3Object': {
                'Bucket': bucket_name,
                'Name': s3_key
            }
        }
    )

    # Wait for the job to complete
    job_id = response['JobId']
    st.write("Text extraction job started. Job ID:", job_id)
    st.write("Waiting for the job to complete... (This might take a while)")

    # Poll until the job is complete
    while True:
        job_status = client.get_document_text_detection(JobId=job_id)
        if job_status['JobStatus'] in ['SUCCEEDED', 'FAILED']:
            break
        time.sleep(5)  # Wait for 5 seconds before checking again

    if job_status['JobStatus'] == 'SUCCEEDED':
        text_blocks = [item['Text'] for item in job_status['Blocks'] if item['BlockType'] == "LINE"]
        if len(text_blocks) > 0:
            text = "\n".join(text_blocks)
            st.success("Text extracted from PDF:")
            st.write(text)
            download_text(text)
        else:
            st.warning("No text found in the PDF.")
    else:
        st.error("Text extraction failed. Please try again later.")


# Define the main function that will be called when the "Extract Text" button is clicked
def extract_text(file, file_type):
    if file_type == "Image":
        extracted_text = extract_text_from_image(file.read())
        img = Image.open(file)
        st.image(img, caption="Uploaded Image")
    elif file_type == "PDF":
        extracted_text = extract_text_from_pdf(file.read(), file.name)
        st.write(extracted_text)


# Create an option menu for selecting the file type
file_type = st.selectbox("Select file type", options=["Image"])

# Create a file uploader
file = st.file_uploader("Upload file", type=["jpg", "jpeg", "png"])

# Create a button to extract text from the uploaded file
if st.button("Extract Text with Textract"):
    if file is not None:
        extract_text(file, file_type)
    else:
        st.write("Please upload a file.")
        
        
# Create an Image Analysis client
image_analysis_client = ImageAnalysisClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(key)
)

#Create an Azure Text Analytics client
text_analytics_client = TextAnalyticsClient(
            endpoint=endpoint, 
            credential=AzureKeyCredential(key)
)

# Example method for detecting sensitive information (PII) from text in images 
def pii_recognition(file):

    #Get text from the image using Image Analysis OCR
    # ocr_result = image_analysis_client.analyze_from_url(
    # image_url="https://www.asianbusinesscards.com/wp-content/uploads/2019/03/chinese-business-card-translation-samples-stanford-445-sch.jpg",
    # visual_features=[VisualFeatures.READ])
   
    ocr_result = image_analysis_client.analyze(
    image_data = file,
    visual_features=[VisualFeatures.READ])
       
    documents = [' '.join([line['text'] for line in ocr_result.read.blocks[0].lines])]

    # print(documents)

    #Detect sensitive information in OCR output
    # response = text_analytics_client.recognize_entities(documents, language="en")
    # response = text_analytics_client.recognize_pii_entities(documents, language="en")
    # result = [doc for doc in response if not doc.is_error]
    
    
    result = text_analytics_client.recognize_entities(documents)
    result = [review for review in result if not review.is_error]
    organization_to_reviews: typing.Dict[str, typing.List[str]] = {}

    # # Display the extracted text
    st.subheader("Extracted Text by AZURE Document Intelligence")
    st.write(documents)
    text2 = ""
    for idx, review in enumerate(result):
        for entity in review.entities:
            print(f"Entity '{entity.text}' has category '{entity.category}'")
            if re.findall(r'[\u4e00-\u9fff]+',  entity.text):
                text2 = entity.text + " (" + pinyin.get(entity.text)+ ")" + " - is a " + entity.category + "\n"
            else:
                text2 = entity.text + " - is a " + entity.category + "\n"
                  
            
            st.write(text2)
            text2 = "" 
            if entity.category == 'Organization':
                organization_to_reviews.setdefault(entity.text, [])
                organization_to_reviews[entity.text].append(documents[idx])

    for organization, reviews in organization_to_reviews.items():
        print(
            "\n\nOrganization '{}' has left us the following review(s): {}".format(
                organization, "\n\n".join(reviews)
            )
        )
    

    
    # for doc in result:
    #     # print("Redacted Text: {}".format(doc.redacted_text))
    #     for entity in doc.entities:
    #         print("Entity: {}".format(entity.text))
    #         print("\tCategory: {}".format(entity.category))
    #         print("\tConfidence Score: {}".format(entity.confidence_score))
    #         print("\tOffset: {}".format(entity.offset))
    #         print("\tLength: {}".format(entity.length))
    #     for entity in doc.entities:
    #         if re.findall(r'[\u4e00-\u9fff]+',  entity.text):
    #             text2 += entity.text + "(" + pinyin.get(entity.text)+ ")" + "\n"
    #         else:
    #             text2 += entity.text + "\n"    
    

    
    # download_text(text2)
    st.image(file, caption="Uploaded Image")

title1 = '<p style="font-size: 40px;font-weight: 550;"> AZURE Document Intelligence - \nExtract Text via Images</p>'
st.markdown(title1, unsafe_allow_html=True)
st.image("./assets/azure-ai.png")

# Create a file uploader
file1 = st.file_uploader(key = "azure-uploader", label = "Upload file", type=["jpg", "jpeg", "png"])

if st.button("Extract Text with Document Intelligence"):
    if file1 is not None:
        pii_recognition(file1) 
    else:
        st.write("Please upload a file.")
            
