import humanize
import time
import re
from typing import List, Optional
from typing import Any

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine
from google.protobuf.json_format import MessageToJson
import pandas as pd
import csv
import json

# developer to-dos - set these values
project_id = "sanchezac-genai-demos"
location = "global"  # Options: "global", "us", "eu"
datastore_id = "ucmo_1692813045971"

#[begin helper scripts]
def _call_list_documents(
    project_id: str, location: str, datastore_id: str, page_token: Optional[str] = None
) -> discoveryengine.ListDocumentsResponse:
    # Build the List Docs Request payload.
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )
    client = discoveryengine.DocumentServiceClient(client_options=client_options)

    request = discoveryengine.ListDocumentsRequest(
        parent=client.branch_path(project_id, location, datastore_id, "default_branch"),
        page_size=1000,
        page_token=page_token,
        
    )

    return client.list_documents(request=request)


def list_documents(
    project_id: str, location: str, datastore_id: str, rate_limit: int = 1
) -> List[discoveryengine.Document]:
    # Gets a list of docs in a datastore.

    res = _call_list_documents(project_id, location, datastore_id)

    # setup the list with the first batch of docs
    docs = res.documents

    while res.next_page_token:
        # implement a rate_limit to prevent quota exhaustion
        # input time in seconds will be divided by 2
        time.sleep(rate_limit/2)

        res = _call_list_documents(
            project_id, location, datastore_id, res.next_page_token
        )
        docs.extend(res.documents)

    return docs


def list_indexed_urls(
    docs: Optional[List[discoveryengine.Document]] = None,
    project_id: str = None,
    location: str = None,
    datastore_id: str = None,
) -> List[str]:
    #Get the list of docs in data store, then parse to only urls.
    if not docs:
        docs = list_documents(project_id, location, datastore_id)
    urls = [doc.content.uri for doc in docs]

    return urls


def search_url(urls: List[str], url: str) -> None:
    """Searches a url in a list of urls."""
    for item in urls:
        if url in item:
            print(item)


def search_doc_id(
    doc_id: str,
    docs: Optional[List[discoveryengine.Document]] = None,
    project_id: str = None,
    location: str = None,
    datastore_id: str = None,
) -> None:
    #Searches a doc_id in a list of docs.
    if not docs:
        docs = list_documents(project_id, location, datastore_id)

    doc_found = False
    for doc in docs:
        if doc.parent_document_id == doc_id:
            doc_found = True
            print(doc)

    if not doc_found:
        print(f"Document not found for provided Doc ID: `{doc_id}`")


def estimate_data_store_size(
    urls: Optional[List[str]] = None,
    docs: Optional[List[discoveryengine.Document]] = None,
    project_id: str = None,
    location: str = None,
    datastore_id: str = None,
) -> None:
    #For Advanced Website Indexing data stores only.
    if not urls:
        if not docs:
            docs = list_documents(project_id, location, datastore_id)
        urls = list_indexed_urls(docs=docs)

    # Filter to only include website urls.
    urls = list(filter(lambda x: re.search(r"https?://", x), urls))

    if not urls:
        print(
            "No urls found. Make sure this data store is for websites with advanced indexing."
        )
        return

    # For website indexing, each page is calculated as 500KB.
    size = len(urls) * 500_000
    print(f"Estimated data store size: {humanize.naturalsize(size)}")


PENDING_MESSAGE = """
No docs found.\n\nIt\'s likely one of the following issues: \n  [1] Your data store is not finished indexing. \n  [2] Your data store failed indexing. \n  [3] Your data store is for website data without advanced indexing.\n\n
If you just added your data store, it can take up to 4 hours before it will become available.
"""
#[end helper scripts]

#[start data store index to csv]

# Get entire datastore into a list
# returns protobuf
docs = list_documents(project_id, location, datastore_id)

#determine length of list, so we can treat the last record different than the first
docs_length = len(docs)

# write all records to json document
with open('/tmp/all-datastore-documents.txt', 'w') as writefile:
    writefile.write("[")
    for i, doc in enumerate(docs):
        if docs_length - i == 1:
            # last record, don't print trailing comma
            writefile.write(f"{MessageToJson(doc._pb)}")
        else :
            # not last record, print trailing comma and newline char
            writefile.write(f"{MessageToJson(doc._pb)}" + ',\n')
    writefile.write("]")

# parse a valid JSON document and convert it into a Python Dictionary.
with open ("/tmp/all-datastore-documents.txt","r") as f:
  data = json.loads(f.read()) 

# create pandas dataframe of json data, normalized/flattened
df = pd.json_normalize(data,sep="_")

# convert json pandas dataframe to csv
df.to_csv(f"/tmp/datastore-{project_id}-{location}-{datastore_id}.csv",index=False,quoting=1)

#[end data store index to csv]
        