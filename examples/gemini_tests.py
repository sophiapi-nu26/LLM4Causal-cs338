from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

load_dotenv()  # This loads the variables from .env
api_key = os.getenv('GEMINI_API_KEY')  # This gets a specific variable

client = genai.Client()

# image_list = os.listdir("../figures")
image_list = ['sciadv.abo6043-figure-5.png']

prompt_file = open('figure_extractor_gemini_prompt.txt', 'r')
prompt = prompt_file.read()
prompt_file.close()

for i in range(len(image_list)):
    with open('./temp/figures/' + image_list[i], 'rb') as f:
        image_bytes = f.read()

    response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[
        types.Part.from_bytes(
        data=image_bytes,
        mime_type='image/png',
        ),
        prompt
    ]
    )

    print(response.text)

    # save the response text to a file
    with open('./temp/' + image_list[i].split('.png')[0] + '_caption.txt', 'w') as f:
        f.write(response.text)