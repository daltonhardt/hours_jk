#################################################
# Daily Work Report system using Streamlit
# Developed for : Jair Construction, LLC
# Author        : Dalton Hardt
# Date          : April 2025
# Last revision : April 2025
VERSION = '1.25.5'
#################################################
import google.generativeai as genai
import streamlit as st
from streamlit_js_eval import get_geolocation

from geopy.geocoders import Nominatim
import os
from pathlib import Path

from datetime import datetime
from tempfile import NamedTemporaryFile
from pydub import AudioSegment

import json
from json2html import *
import re

import logging  # library for not showing LOG messages on screen

# don't show LOG messages on screen
for name, l in logging.root.manager.loggerDict.items():
    if "streamlit" in name:
        l.disabled = True

# function to get geolocation using java connection
def get_location():
    try:
        local = get_geolocation()
        if local:
            lat = local['coords']['latitude']
            lon = local['coords']['longitude']
            # st.text(f"Lat.: {lat}   Lon.: {lon}")
            geolocator = Nominatim(user_agent="geo_localization")
            location = geolocator.reverse((lat, lon), exactly_one=True)
            return location.address if location else "Oops, address not found."
        else:
            return "Oops, location not found."
    except "ReadTimeoutError":
        return "Oops, could not get your location."

# function to define the html table pattern
def html_table_format():
    out = f'''
        <body>
            <hr> <!-- Horizontal line before the table -->
            <table style="width:100%; border-collapse: collapse;">
                <tr style="background-color:#99ff99;">
                    <th colspan="3" align="center">WORKING HOURS</th>
                </tr>
                <tr>
                    <th colspan="3" align="center">Date: date when the work was done</th>
                </tr>
                <tr>
                    <th colspan="3" style="padding: 0.5em 0 0.5em 0; text-align: center; border: none;">Local: </th>
                </tr>
                <tr style="background-color: #99ff99; border: none;">
                    <td style="text-align: center; padding: 0.05em; border: none;">Name</th>
                    <td style="text-align: center; padding: 0.05em; border: none;">Task</th>
                    <td style="text-align: center; padding: 0.05em; border: none;">Hours</th>
                </tr>
                <!-- table example -->
                <tr>
                    <td style="padding: 0.25em; border: none;">John</td>
                    <td style="padding: 0.25em; border: none; text-align: center;">Cutting</td>
                    <td style="padding: 0.25em; border: none;">4.0</td>
                </tr>
            </table>
        </body>
        '''
    return out

# function to extract complete JSON blocks
def extract_json_blocks(text):
    json_blocks = []
    stack = []
    json_start = None

    for i, char in enumerate(text):
        if char == '{':
            stack.append(char)
            if len(stack) == 1:  # First '{' the beginning of JSON
                json_start = i
        elif char == '}':
            stack.pop()
            if len(stack) == 0 and json_start is not None:  # Last '}' the end of JSON
                json_blocks.append(text[json_start:i + 1])
                json_start = None

    return json_blocks


# function to extract complete JSON blocks
def extract_html_blocks(text):
    html_blocks = []
    pattern = re.compile(r'<body[\s\S]*?</body>', re.IGNORECASE)
    matches = pattern.findall(text)
    return matches


# function to define the JSON pattern
def json_format():
    out = '''
            { "date": "date when the work was done",
              "weekday": "day of the week"
              "location": "place where the work was done",
              "name": "worker's name",
              "task": "Description of the task",
              "hours": "hours as decimal number'
            }
            '''
    return out

# function to process the audio file
def process_audio(value, name_of_model, system_instruction, description):
    # define Gemini Generative AI model
    model = genai.GenerativeModel(model_name=name_of_model, system_instruction=system_instruction)
    if value:
        with st.spinner("Working..."):
            # audio_file = st.audio(audio_value, format='audio/wav')
            with NamedTemporaryFile(dir='./', suffix='.wav', delete=True) as f:  #delete=False keep the file
                f.write(value.getbuffer())
                file_name = f.name
                # print('\n ==================')
                # print('Temp file_name:', file_name)
                audio = AudioSegment.from_file(file_name)
                new_file = os.path.splitext(f.name)[0] +'.mp3'
                audio.export(new_file, bitrate='128k', format='mp3')
                # print(f'===== mp3 file exported (new_file): \n {new_file}')

            # load mp3 audio file
            audio_file = genai.upload_file(new_file)

            # get result from AI model
            result = model.generate_content([audio_file, description])
            # print("=====  Total output  =====")
            # print(result.text)

            # Extract JSONs from the text
            json_text = result.text
            json_matches = extract_json_blocks(json_text)

            # Converts each JSON into a Python dictionary
            json_objects = []
            for match in json_matches:
                try:
                    json_objects.append(json.loads(match))
                except json.JSONDecodeError as e:
                    print(f"Error to decode JSON: {e}")

            # display the result
            # i=0
            # for obj in json_objects:
            #     i += 1
            #     print(f'=== Dump JSON nr. {i}')
            #     print(json.dumps(obj, indent=2, ensure_ascii=False))

            # Extract HTMLs from the text
            html_text = result.text
            html_matches = extract_html_blocks(html_text)

            # Converts each HTML into a Python dictionary
            html_objects = []
            try:
                for i, html in enumerate(html_matches, 1):
                    # print(f"\n=== Dump HTML nr.{i} ===\n")
                    # print(html)
                    st.html(html)
            except:
                st.html("HTML not found...")

        action1, _, _, action2 = st.columns(4)
        with action1:  # download audio file in .mp3 format
            with open(new_file, "rb") as f:
                data = f.read()
                st.download_button(
                    label='Save audio',
                    data=data,
                    file_name= "audio-hours.mp3",
                    mime="audio/mpeg",
                    icon=":material/download:"
                )
        with action2:  # download JSON file
            json_string = json.dumps(json_objects, ensure_ascii=False)  #ensure_Ascii=False for UTF-8 characters
            # display string in JSON format
            # st.json(json_string, expanded=True)

            # Save Data button to save JSON file locally
            st.download_button(
                label='Save data',
                data=json_string,
                file_name="work_hours.json",
                mime="application/json",
                icon=":material/download:"
            )
            # Convert string to a list of dictionary
            # json_data = json.loads(json_string)
            # for row in json_data:
            #     print(list(row.values()))


sys.path.append(str(Path(__file__).resolve().parents[1]))

# --- GOOGLE API initialization
# Read Gemini API-Key credentials stored in secrets.toml file
apikey = st.secrets.google_api["apikey"]
genai.configure(api_key=apikey)

# --- LOCAL configurations
# set the locale to Spanish (Spain)
# locale.setlocale(locale.LC_NUMERIC, 'es_ES.UTF-8')

# Get current datetime
current_datetime = datetime.now()
# Convert to string and format
TODAY = datetime.strptime(datetime.now().strftime("%d-%b-%Y"), "%d-%b-%Y")
# Get current location
address = get_location()
if 'Oops' not in address:
    add = address.split(', ')
    address = f'{add[0]}, {add[1]}, {add[3]}'

# Define Gemini AI table format, json format and description
output_html = html_table_format()
output_json = json_format()
DESC = (f"Save the result as JSON file using the format {output_json} and always sum the total worked hours per day."
        f"Create an html table using the format {output_html} and sum the total worked hours per day in bold format.")

# Define Gemini AI instructions
instruction = (f"Based on what you understand from the audio, always give the answer in the same language. For example,"
              f" if the user is speaking in Brazilian Portuguese, all responses must be in Brazilian Portuguese. "
              f"If the user is speaking in Spanish, all responses must be in Spanish, and the same happens for English."
              f"The target users are mostly carpentry service firms who want to register their daily jobs. "
              f"It is important to keep track of the persons names, tasks and hours spent by each one. "
              f"Return the information as a JSON list of dictionaries. Each dictionary in the list must have the "
              f"following keys: 'date', 'weekday', 'location', 'name', 'task' and 'hours'."
              f"Populate the 'name' field exactly with the person's name. "
              f"The 'task' field should contain a complete description of the activity performed. "
              f"The 'hours' field should contain the number of hours spent on the task as a decimal number (e.g.,'3.5')."
              f"If the name is not mentioned and the audio is in Portuguese, refer as 'Eu'. "
              f"If the name is not mentioned and the audio is in Spanish, refer as 'Yo'. "
              f"If the name is not mentioned and the audio is in English, refer as 'Myself'. "
              f"If you don't understand a name, write '_???_' (never create or invent a name). "
              f"Give your best to identify the name of the local where the job was done, e.g., 'building X', "
              f"'house of Y', 'my house', 'park X', 'hotel Y', 'company X', 'firm Z' and so on. "
              f"Only if the location is not clearly mentioned in the audio or you are not able to understand,"
              f"you are allowed to use the current geolocation '{address}' when available, otherwise write '_???_'. "
              f"If the date is not mentioned in the audio use the current date '{TODAY}' in the format '%d-%b-%Y'. "
              f"Identify the day in the week according to the current date so that if the user says 'this monday' or "
              f"'yesterday' or 'last wednesday' you may understand the correct date. "
              f"If the audio mentions multiple people and their tasks, create a separate dictionary for each "
              f"person-task-hours combination in the list. "
              f"Do the job with no verbosity, don't display your comments. "
              f"Always populate the HTML and JSON files in the same audio language. Don't translate anything.")

# Choosing the Gemini model
# model_name = "gemini-1.5-flash"
model_name = "gemini-2.0-flash"
# model_name = "gemini-2.0-flash-Lite"

# --- starting STREAMLIT
# st.set_page_config(layout="wide")
st.header('Jair Construction, LLC.')
st.subheader('Daily Work Report')
st.text(f'v{VERSION} - powered by Google generative AI model {model_name}')
st.divider()

# Enter the audio
st.markdown("Instructions: speak normally and make sure you include the following terms:")
st.markdown("- :blue-background[**the name of the local**], if not mentioned the system will assume your current geolocation")
st.markdown("- :red-background[**the date**], if not mentioned the system will assume the date as Today")
st.markdown("- :blue-background[**the names of the workers**]")
st.markdown("- :red-background[**the activities developed by each worker**]")
st.markdown("- :blue-background[**the hours spent on each activity by each worker**]")
st.markdown("Press the microphone icon bellow to start speaking and press it again when finished.")
audio_value = st.audio_input("")
process_audio(audio_value, model_name, instruction, DESC)
