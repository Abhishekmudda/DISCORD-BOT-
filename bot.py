import discord
import os
import requests
import json
import google.generativeai as palm
import io
from PyPDF2 import PdfReader
from docx import Document
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Environment variables for API keys and token
token = os.environ['TOKEN']
Palm_API = os.environ['PalmAPI']

# Configure Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Configure Google PaLM API
palm.configure(api_key=Palm_API) 
models = [m for m in palm.list_models() if 'generateText' in m.supported_generation_methods]
model = models[0].name

# Function to get an inspiring quote
def get_quote():
    response = requests.get("https://zenquotes.io/api/random")
    json_data = json.loads(response.text)
    quote = json_data[0]['q'] + " -" + json_data[0]['a']
    return quote

# Function to get a text completion from Google PaLM API
def get_completion(prompt):
    completion = palm.generate_text(
        model=model,
        prompt=prompt,
        temperature=0.3,
        max_output_tokens=1000
    )
    return completion.result

# Summarize text using PaLM API
def summarize_text(text):
    prompt = f"""
    Your task is to summarize the following text. Keep the summary concise and capture the key points:
    ```{text}```
    """
    return get_completion(prompt)

# Extract text from a PDF file and split it into manageable chunks
def read_pdf_to_chunks(file, chunk_size=2000):
    text = ""
    reader = PdfReader(file)
    for page in reader.pages:
        text += page.extract_text()
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

# Extract text from a Word document
def read_word(file):
    doc = Document(file)
    return "\n".join([paragraph.text for paragraph in doc.paragraphs])

# Event: Bot is ready
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

# Event: On receiving a message
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.lower().startswith('hello'):
        await message.channel.send("""
        Hello! I am a bot. You can ask me anything such as:
        
        1. To explain Python code, just type "$code" followed by your code.
        2. To get an inspiring quote, just type "$inspire".
        3. To summarize a text, just type "$summarize" followed by your text.
        """)

    if message.content.startswith('$inspire'):
        await message.channel.send(get_quote())

    if message.content.startswith('$code'):
        code_snippet = message.content[len('$code'):].strip()
        await message.channel.send("Code has been successfully extracted.")
        prompt = f"""
        Your task is to act as a Python code explainer.
        I'll give you a code snippet.
        Your job is to explain the code step-by-step.
        Also, compute the final output of the code.
        The code snippet is shared below, delimited with triple backticks:
        ```{code_snippet}```
        Finally, provide a summary that clearly states the main logic or purpose of the code.
        """
        result = get_completion(prompt)
        if len(result) > 2000:
            with open("output.txt", "w") as file:
                file.write(result)
            await message.channel.send(file=discord.File("output.txt"))
        else:
            await message.channel.send(result)

    if message.content.startswith('$summarize') and message.attachments:
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

        await message.channel.send("File has been successfully processed. Summarizing the content now...")
        summarized_texts = [summarize_text(chunk) for chunk in text_chunks]
        combined_summary = "\n\n".join(summarized_texts)

        if len(combined_summary) > 2000:
            with open("summary_output.txt", "w") as file:
                file.write(combined_summary)
            await message.channel.send(file=discord.File("summary_output.txt"))
        else:
            await message.channel.send(combined_summary)

client.run(token)
