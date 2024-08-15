import discord
import os
import requests
import json
import random
import google.generativeai as palm
import io
from PyPDF2 import PdfReader
from docx import Document


token = os.environ['TOKEN']
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
Palm_API=os.environ['PalmAPI']
palm.configure(api_key=Palm_API) 

models=[m for m in palm.list_models() if 'generateText' in m.supported_generation_methods]
model=models[0].name

def get_quote():
  response=requests.get("https://zenquotes.io/api/random")
  json_data=json.loads(response.text)
  quote=json_data[0]['q'] + " -" + json_data[0]['a']
  return quote

def get_completion(prompt):
  Completion=palm.generate_text(
  model=model,
  prompt=prompt,
  temperature=0.3,
  max_output_tokens=1000
)
  return Completion.result

def summarize_text(text):
  prompt = f"""
  Your task is to summarize the following text. Keep the summary concise and capture the key points:
  
{text}

  """
  return get_completion(prompt)

# Extract text from a PDF file and split it into manageable chunks
def read_pdf_to_chunks(file, chunk_size=2000):
  text = ""
  pdf_document = fitz.open(stream=file.read(), filetype="pdf")
  for page in pdf_document:
      text += page.get_text()

  # Split the text into chunks of up to chunk_size characters
  return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]


@client.event
async def on_ready():
      print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
         return

    if message.content.lower().startswith('hello'):
      await message.channel.send("""\
      Hello! I am a bot. Where you can ask me anything such as:
      
      1. To explain Python code, just type "$code" followed by your code.
      2. To get an inspiring quote, just type "$inspire".
      3. To summarize a text, just type "$summarize" followed by your text.
      """)
      
    if message.content.lower().startswith('$inspire'):
      await message.channel.send(get_quote())
      
    if message.content.lower().startswith('$code'):
        code_snippet = message.content[len('$code'):].strip()
        await message.channel.send("Code has been successfully extracted.")
        #await message.channel.send(f"Extracted code: {code_snippet}")
        prompt=f"""
        Your task is to act as a Python code Explainer.
        I'll give you aa code snippet.
        your job is to explain the code Snippet Step-by-Step.
        Also, compute the final output of the code.
        code snippet is shared below, delimited with triple backticks:
         
{code_snippet}

        Finally, provide a summary that clearly states the main logic or purpose of the code.
        """
        result=get_completion(prompt)
       #await message.channel.send(result)
        if len(result) > 2000:
          with open("output.txt", "w") as file:
              file.write(result)
          await message.channel.send(file=discord.File("output.txt"))
        else:
          await message.channel.send(result)

    if message.content.lower().startswith('$summarize') and message.attachments:
         attachment = message.attachments[0]
         if attachment.filename.endswith(".pdf"):
             file = await attachment.read()
             text_chunks = read_pdf_to_chunks(io.BytesIO(file))
         elif attachment.filename.endswith(".docx"):
             file = await attachment.read()
             text = read_word(io.BytesIO(file))
             text_chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
         elif attachment.filename.endswith(".txt"):
             file = await attachment.read()
             text = file.decode('utf-8')
             text_chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
         else:
             await message.channel.send("Unsupported file type. Please upload a PDF, Word document, or text file.")
             return

         # Summarize each chunk
         await message.channel.send("File has been successfully processed. Summarizing the content now...")
         summarized_texts = [summarize_text(chunk) for chunk in text_chunks]

         # Combine the summaries and send as either a file or directly in the chat
         combined_summary = "\n\n".join(summarized_texts)
         if len(combined_summary) > 2000:
             with open("summary_output.txt", "w") as file:
                 file.write(combined_summary)
             await message.channel.send(file=discord.File("summary_output.txt"))
         else:
             await message.channel.send(combined_summary)
    # if message.content.startswith('$summarize'):
    #   text_to_summarize = message.content[len('$summarize'):].strip()
    #   await message.channel.send("Text has been successfully extracted for summarization.")
    #   prompt = f"""
    #   Your task is to summarize the following text. Keep the summary concise and capture the key points:
    #   
{text_to_summarize}

    #   """
    #   result = get_completion(prompt)
    #   if len(result) > 2000:
    #       with open("summary_output.txt", "w") as file:
    #           file.write(result)
    #       await message.channel.send(file=discord.File("summary_output.txt"))
    #   else:
    #       await message.channel.send(result)

   # Handle file uploads for summarization
   

client.run(token)
