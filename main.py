# This file is intended to parse customer support chats for product information to be used in traing a GPT-3 Model to answer questions about the product supported in the chats
# It uses OpenAI's text-davinci-003 to pull structured data about the product from the unstructured chats
# It uses support chats from Intercom's API, but any support chat platform could be used

# Import necessary libraries
import requests
# import json
import openai
import os
from datetime import datetime
import time
import checkedConvos

conversation_ids_checked = checkedConvos.ids

# Set the OpenAI API key
openai.api_key = os.environ['OPENAI_KEY']

# Set the Intercom access token
access_token = os.environ['INTERCOM_KEY']

# Set the URL for the Intercom API endpoint
api_url = "https://api.intercom.io/conversations"

# Set the request headers
headers = {
  "Accept": "application/json",
  "Authorization": "Bearer " + access_token
}

# Set the request parameters
params = {
  "sort": "desc"  # Set the sort order to descending by conversation ID
}


# Function to retrieve and process the conversations
def get_conversations():
  # Initialize empty lists to store the prompts and responses
  prompts = []

  # settings
  starting_date = 1641013200  # setting earliest date to analyze
  prompt_limit = 4000  # setting character limit on customer prompts
  pages_to_analyze = 500  # setting limit on pages of chats to analyze
  last_page_analyzed = 58  # setting the last page of chats analyzed
  new_conversation_ids_checked = []
  cm_prompt = "Starchup sells a software product. Determine whether you can summary the following support chat with Starchup users into a help page article or FAQ. If yes, return the the article in the following format: TITLE: Title of the article, BODY: Body of the article in html format. If no, simply answer 'no'. Customer Chat: "

  # Set the initial page number to the last page analyzed
  page_number = last_page_analyzed or 1
  starting_after = "WzE2NTQ5NTYyMjcwMDAsNDU5MzIzMDAwMTUxOTMsNTld"
  tokens_used = 0

  # Continue retrieving and processing pages of conversations
  # until there are no more conversations to retrieve
  while page_number < pages_to_analyze:
    # Set the request parameters for the current page
    if len(starting_after) > 1:
      params["starting_after"] = starting_after
      params["per_page"] = 100
      print("starting_after: ", starting_after)
    # Send the GET request to the Intercom API
    response = requests.get(api_url, headers=headers, params=params)
    # Check the response status code
    if response.status_code == 200:
      # Load the response data as a JSON object
      data = response.json()
      starting_after = data["pages"]["next"]["starting_after"]
      if data["pages"]["next"]["page"] < page_number:
        continue
      page_number = data["pages"]["next"]["page"]
      # Loop through the conversations in the response
      for conversation in data["conversations"]:
        conversation_id = conversation["id"]
        # Check if conversation already analyzed
        if conversation_id in conversation_ids_checked:
          continue
        if conversation_id in new_conversation_ids_checked:
          continue
        # Check if conversation is older than set "Starting Data"
        if conversation["created_at"] < starting_date:
          continue
        # Get full conversation from Intercom API
        full_conversation_url = api_url + "/" + conversation_id
        full_conversation_params = {"display_as": "plaintext"}
        fc_response = requests.get(full_conversation_url,
                                   headers=headers,
                                   params=full_conversation_params)
        full_conversation = fc_response.json()
        # Extract conversation parts
        parts = full_conversation["conversation_parts"]["conversation_parts"]
        # Initialize empty strings to store the conversation messages
        formatted_conversation = ""
        if full_conversation["source"]["delivered_as"] == "customer_initiated":
          if "Image" not in full_conversation["source"][
              "body"] if full_conversation["source"]["body"] else "":
            formatted_conversation += "CUSTOMER: " + full_conversation[
              "source"]["body"] + "\n "

        # Loop through the parts in the conversation
        for part in parts:
          # Check if the part is a message
          if part["part_type"] == "comment" or part["part_type"] == "note":
            # Ignore images
            if "Image" not in part["body"] if part["body"] else "":
              if "assets.bratinreegateway.com" not in part["body"] if part[
                  "body"] else "":
                # Concatenate the message text to the customer message string
                formatted_conversation += part["author"]["type"] + ": " + part[
                  "body"] + "\n "
        # Send prompt to GPT-3 for analysis
        new_prompt = cm_prompt + formatted_conversation[:prompt_limit]
        time.sleep(5)
        potential_article = openai.Completion.create(engine="text-davinci-002",
                                                     prompt=new_prompt,
                                                     max_tokens=200,
                                                     temperature=0.5,
                                                     top_p=1,
                                                     frequency_penalty=0,
                                                     presence_penalty=0)
        #  Create JSON record with output
        new_output = potential_article.choices[0].text
        tokens_used += potential_article.usage.total_tokens
        prompt_is_article = new_output.find('TITLE') or new_output.find(
          'Title')
        if prompt_is_article > -1:
          # Create Article on Intercom
          output_array = new_output.split('BODY:')
          if not len(output_array) > 1:
            continue
          title_string = output_array[0].replace("\n", "")
          title_string = title_string.replace("TITLE: ", "")
          title_string = title_string.replace("Title: ", "")
          body_string = output_array[1] + "\n<p>ID: " + conversation_id + "</p>"
          article_data = {
            "title": title_string,
            "body": body_string,
            "author_id": 465942,
            "state": "draft"
          }
          post_response = requests.post("https://api.intercom.io/articles",
                                        data=article_data,
                                        headers=headers)
        new_conversation_ids_checked.append(conversation_id)
        print("NEW conversation_ids_checked:", new_conversation_ids_checked)
        total_conversation_ids_checked = len(
          new_conversation_ids_checked) + len(conversation_ids_checked)
        print("TOTAL conversation_ids_checked: ",
              total_conversation_ids_checked)
        print("page_number: ", page_number)
        print("starting_after: ", starting_after)
        print("TOKENS USED: ", tokens_used)

      # Increment the page number
      page_number += 1
      print("new page_number: ", page_number)
    # If the response status code is not 200, there are no more conversations to retrieve
    else:
      break
  # Return the prompts
  return prompts


# Call the get_conversations function
prompts = get_conversations()

# TODO: Refactor the OpenAI calls into a separate file to be imported into files for pulling chats from other chat platform APIs
# TODO: Add support for parsing chat structuring features such as "tags" so support agents can indicate quality training chats in real-time
# TODO: Add endpoints for receiving new chats from webhooks on the chat platforms
