import os
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.exceptions import HttpResponseError

# Set the values of your computer vision endpoint and computer vision key
# as environment variables:
try:
    endpoint = "https://test-viseo-ai-services.cognitiveservices.azure.com/" #Paste your AI services endpoint here
    key = "d0095ddc07bf4b01a73355dceabe041b" #Paste your AI services resource key here
except KeyError:
    print("Missing ENDPOINT' or 'KEY'")
    print("Set them before running this sample.")
    exit()

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
def pii_recognition_example(client):

    #Get text from the image using Image Analysis OCR
    ocr_result = image_analysis_client.analyze_from_url(
    #image_url="https://resources.ssnsimple.com/wp-content/uploads/2019/11/social-security-number.jpg",
    
    # image_url="https://www.redprinting.sg/data/item/1573023186/top1_700x700.png",
    
    image_url="https://www.asianbusinesscards.com/wp-content/uploads/2019/03/chinese-business-card-translation-samples-stanford-445-sch.jpg",
    visual_features=[VisualFeatures.READ],
)
   
    documents = [' '.join([line['text'] for line in ocr_result.read.blocks[0].lines])]
  
    print(documents)

    #Detect sensitive information in OCR output
    response = text_analytics_client.recognize_pii_entities(documents, language="en")
    result = [doc for doc in response if not doc.is_error]
    
    for doc in result:
        print("Redacted Text: {}".format(doc.redacted_text))
        for entity in doc.entities:
            print("Entity: {}".format(entity.text))
            print("\tCategory: {}".format(entity.category))
            print("\tConfidence Score: {}".format(entity.confidence_score))
            print("\tOffset: {}".format(entity.offset))
            print("\tLength: {}".format(entity.length))
            
pii_recognition_example(text_analytics_client) 