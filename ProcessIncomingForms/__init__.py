import os
import logging

import azure.functions as func
from azure.identity import AzureCliCredential, ChainedTokenCredential, ManagedIdentityCredential
from azure.ai.formrecognizer import FormRecognizerClient
from azure.core.credentials import AzureKeyCredential


def main(myblob: func.InputStream):

    logging.info(f"Python blob trigger function processed blob {myblob.uri}")
    
    endpoint = os.getenv("FORM_RECOGNIZER_ENDPOINT")
    credential = ChainedTokenCredential(ManagedIdentityCredential(), AzureCliCredential())
    
    form_recognizer_client = FormRecognizerClient(
        endpoint=endpoint,
        credential=credential)
    
    poller = form_recognizer_client.begin_recognize_invoices_from_url(invoice_url=myblob.uri)
    invoices = poller.result()
    
    minimum_confidences = {
        "VendorName": 0.85,
        "VendorAddress": 0.85,
        "InvoiceDate": 0.85,
        "InvoiceTotal": 0.85        
    }
    
    for idx, invoice in enumerate(invoices):
        print("--------Recognizing invoice #-------")
        for field_name, min_confidence in minimum_confidences.items():
            field = invoice.fields.get(field_name)
            if field and field.confidence >= min_confidence:
                print(f"Success: {field_name}={field.value} found ({field.confidence}>={min_confidence})")
            else:
                print(f"Error: {field_name} not found or confidence too low ({field.confidence}<{min_confidence})")