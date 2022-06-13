import os
import json
import logging
from urllib.parse import urlparse

import azure.functions as func
from azure.identity import AzureCliCredential, ChainedTokenCredential, ManagedIdentityCredential
from azure.ai.formrecognizer import FormRecognizerClient
from azure.storage.blob import BlobServiceClient
from azure.storage.blob import ContentSettings


def main(inputblob: func.InputStream):

    logging.info(f"Python blob trigger function processed blob {inputblob.uri}")
    
    container_review = "forms-review"
    container_success = "forms-success"
    
    endpoint = os.getenv("FORM_RECOGNIZER_ENDPOINT")
    credential = ChainedTokenCredential(ManagedIdentityCredential(), AzureCliCredential())
    
    source_blob = inputblob.uri
    
    form_recognizer_client = FormRecognizerClient(
        endpoint=endpoint,
        credential=credential)
    
    poller = form_recognizer_client.begin_recognize_invoices_from_url(invoice_url=source_blob)
    invoices = poller.result()
    
    minimum_confidences = {
        "VendorName": 0.85,
        "VendorAddress": 0.85,
        "InvoiceDate": 0.85,
        "InvoiceTotal": 0.85        
    }
    
    source_filename = os.path.basename(urlparse(source_blob).path)
    
    results = {"filename": source_filename}
    invoice_okay = True
    for idx, invoice in enumerate(invoices):
        print(invoices)
        print("--------Recognizing invoice #-------")
        for field_name, min_confidence in minimum_confidences.items():
            field = invoice.fields.get(field_name)
            if field and field.confidence >= min_confidence:
                print(f"Success: {field_name}={field.value} found ({field.confidence}>={min_confidence})")
            else:
                print(f"Error: {field_name} not found or confidence too low ({field.confidence}<{min_confidence})")
                invoice_okay = False
            results[field_name] = field.value
            results[field_name + '_confidence'] = field.confidence

                
   
    # TODO: error handling
    blob_service_client = BlobServiceClient(account_url="https://formprocessingexample42.blob.core.windows.net/", credential=credential)
    if invoice_okay:
        target_container = container_success
    else:
        target_container = container_review
        
    copied_blob = blob_service_client.get_blob_client(container=target_container, blob=source_filename)
    copied_blob.start_copy_from_url(source_blob)

    # write Form Recognizer results to Blob
    blob_client = blob_service_client.get_blob_client(container=target_container, blob=source_filename + '.json')
    blob_client.upload_blob(data=json.dumps(results, indent=2, sort_keys=True, default=str),
                            content_settings=ContentSettings(content_type='application/json'),
                            overwrite=True)
