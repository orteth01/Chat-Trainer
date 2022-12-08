# Import necessary libraries
import requests
import json
from openai import api_key
import openai

# Set the OpenAI API key
openai.api_key = "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"

# Set the Intercom access token
access_token = "dG9rOjdmZjBmNzM0X2EzN2ZfNGYxOV84Y2EyXzAyNDYzYTdjODg3MzoxOjA="

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
  responses = []
  starting_date = '1641013200' # setting earliest date to analyze
  cm_slice = 500 # setting character limit on customer prompts
  am_slice = 500 # setting character limit on agent prompts
  
  conversation_ids_checked = ['45932300018484', '45932300018524', '45932300018541', '45932300018581', '4944027790', '4943974544', '4944023659', '4990802698', '5005713249', '5012594031', '4717888219', '5022450335', '5074329044', '5109849327', '45932300018583', '45932300018582', '5134776020', '5161200285', '5152286720', '5190964015', '45932300018584', '5213268222', '5189597143', '5212253269', '5244206235', '5260683268', '5225457648', '5260683423', '5257585446', '5269615527', '5324514597', '5274045995', '5281471780', '5270008660', '5390855153', '5398927606', '5409685008', '5409631032', '5432915636', '5433532509', '5433547138', '5444140571']
  
  # Set the initial page number to 1
  page_number = 1

  # Set the initial last conversation ID to 0
  last_conversation_id = 0

  # Continue retrieving and processing pages of conversations
  # until there are no more conversations to retrieve
  while page_number < 3:
    # Set the request parameters for the current page
    params["page"] = page_number
    print("params", params)
    # Send the GET request to the Intercom API
    response = requests.get(api_url, headers=headers, params=params)
    # Check the response status code
    if response.status_code == 200:
      # Load the response data as a JSON object
      data = response.json()
      print("ALL CONVOS:", data)

      # Loop through the conversations in the response
      for conversation in data["conversations"]:
        # Extract the conversation ID, retrieve the full conversation, extract conversation parts
        conversation_id = conversation["id"]
        print("conversation_id:", conversation_id)
        print("created_at", conversation["created_at"])
        if conversation_id in conversation_ids_checked:
          print("CONVERSATION SKIPPED")
          continue

        full_conversation_url = api_url + "/" + conversation_id
        full_conversation_params = {
          "display_as": "plaintext"
        }
        fc_response = requests.get(full_conversation_url, headers=headers, params=full_conversation_params)
        full_conversation = fc_response.json()
        
        parts = full_conversation["conversation_parts"]["conversation_parts"]

        # Initialize empty strings to store the conversation messages
        customer_message = ""
        agent_message = ""

        # Loop through the parts in the conversation
        for part in parts:
          # Check if the part is a message
          if part["part_type"] == "comment":
            # Check if the part is an image
            if "Image" not in part["body"] if part["body"] else "":
              print("Message Part " + part["author"]["type"] + " body:", part["body"])
              # Check if the part was sent by a customer
              if part["author"]["type"] == "user":
                # Concatenate the message text to the customer message string
                customer_message += part["body"] + " "
              # Check if the part was sent by an agent
              elif part["author"]["type"] == "admin":
                # Concatenate the message text to the agent message string
                agent_message += part["body"] + " "

        # Use ChatGPT to summarize the customer and agent messages
        cm_prompt = "Summarize this customer's support chat into a question: " + customer_message[:cm_slice]
        print("Concatented customer_message: ", customer_message[:cm_slice])
        print("Concatented agent_message: ", agent_message)
        GPT_prompt = openai.Completion.create(engine="text-davinci-003",
                                          prompt=cm_prompt,
                                          max_tokens=64,
                                          temperature=0.5,
                                          top_p=1,
                                          frequency_penalty=0,
                                          presence_penalty=0)
        print("OpenAI Prompt: ", GPT_prompt)
        new_output = {"prompt": GPT_prompt.choices[0].text}

        am_prompt = "Determine whether Agent answered the customer's question with product-related information. If yes, return that answer summarized. If no, return a summary of what the agent said. Customer:" + GPT_prompt.choices[0].text + ". Agent: " + agent_message[:am_slice]
        GPT_response = openai.Completion.create(engine="text-davinci-003",
                                            prompt=am_prompt,
                                            max_tokens=64,
                                            temperature=0.5,
                                            top_p=1,
                                            frequency_penalty=0,
                                            presence_penalty=0)

        print("OpenAI Response: ", GPT_response)
        new_output["response"] = GPT_response.choices[0].text
        prompts.append(new_output)

        # Update the last conversation ID
        last_conversation_id = conversation_id
        print("last_conversation_id: ", last_conversation_id)
        conversation_ids_checked.append(conversation_id)
        print("conversation_ids_checked:", conversation_ids_checked)

      # Increment the page number
      page_number += 1
      print("page_number: ", page_number)
    # If the response status code is not 200, there are no more conversations to retrieve
    else: 
      break
  print('prompts 1',prompts)
  # Return the prompts and responses as a tuple
  return prompts


# print("NLP prompts: ", prompts, "NLP responses: ", responses)
# Call the get_conversations function
prompts = get_conversations()
print('prompts 2',prompts)