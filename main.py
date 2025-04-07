import google.generativeai as genai
import sys
import streamlit as st
from streamlit_option_menu import option_menu
import locale
import os
from pathlib import Path

from datetime import datetime
from tempfile import NamedTemporaryFile
from pydub import AudioSegment

import json
import re

import logging  # biblioteca para não mostrar log de mensagens na tela

# para não mostrar log de mensagens na tela
for name, l in logging.root.manager.loggerDict.items():
    if "streamlit" in name:
        l.disabled = True

def html_table_format():
    # Get current datetime
    current_datetime = datetime.now()
    # Convert to string and format
    datetime_string = current_datetime.strftime('%d-%m-%Y')
    # Define the html table format
    out = f"""
        <body>
            <table style="width:100%; border-collapse: collapse;">
                <tr style="background-color:#99ff99;">
                    <th colspan="3" align="center">WORKING HOURS</th>
                </tr>
                <tr>
                    <th colspan="3" align="center">Date: {datetime_string}</th>
                </tr>
                <tr>
                    <th colspan="3" style="padding: 0.5em 0 0.5em 0; text-align: center; border: none;">Local: </th>
                </tr>
                <tr style="background-color: #99ff99; border: none;">
                    <td style="text-align: center; border: none;">Name</th>
                    <td style="text-align: center; border: none;">Activity</th>
                    <td style="text-align: center; border: none;">Hours</th>
                </tr>
            </table>
        </body>
        """
    return out

def json_format():
    out = '''
            {
              "location": "place where the work was done",
              "date": "date when the work was done",
              "entries":
              [
                {"name": "worker's name", "activity": "Description of the task", "hours": X},
                {"name": "worker's name", "activity": "Description of the task", "hours": X}
              ],
              "total_hours": X
            }
        '''
    return out

# @st.cache_data
def process_audio(value, name_of_model, system_instruction, description, type):

    model = genai.GenerativeModel(model_name=name_of_model, system_instruction=system_instruction)

    if value:
        with st.spinner("Working..."):
            # audio_file = st.audio(audio_value, format='audio/wav')
            with NamedTemporaryFile(dir='./tempDir', suffix='.wav', delete=True) as f:  #delete=False mantém o arquivo
                f.write(value.getbuffer())
                # file_name = os.path.splitext(f.name)[0]
                file_name = f.name
                # print('\n ==================')
                # print('Temp file_name:', file_name)
                audio = AudioSegment.from_file(file_name)
                new_file = os.path.splitext(f.name)[0] +'.mp3'
                audio.export(new_file, bitrate='128k', format='mp3')
                # print(f'===== mp3 file (new_file): \n {new_file}')

            # st.audio(new_file, format="audio/mpeg")  # mostrar o audio player
            audio_file = genai.upload_file(new_file)

            # get result from AI model
            # print(f'===== Giving the response using Google Generative AI model: {name_of_model}')
            result = model.generate_content([audio_file, description])

            # print("=====  Saida Total  =====")
            # print(result.text)

            start_idx = result.text.find('```html')  # Primeira chave
            end_idx = result.text.rfind('```\n')  # Segunda chave

            if start_idx != -1 and end_idx != -1:
                html_text = result.text[start_idx:end_idx + 1]  # Extrai o HTML somente
                st.html(html_text.strip("```html").strip("```"))

            # st.html(result.text.strip("```html").strip("```"))
            # for chunk in result:
            #     st.markdown(chunk.text, unsafe_allow_html=True)

            # Encontra a primeira e última ocorrência de '{' e '}'
            start_idx = result.text.find('{')  # Primeira chave '{'
            end_idx = result.text.rfind('}')  # Última chave '}'

            if start_idx != -1 and end_idx != -1:
                json_text = result.text[start_idx:end_idx + 1]  # Extrai o JSON puro
                try:
                    json_data = json.loads(json_text)  # Converte string para dicionário Python
                    # print("JSON Extraído com Sucesso:", json_data)

                    try:
                        # Convert JSON string to a Python dictionary
                        # json_data = json_text.strip("```json").strip("```")
                        # data_dict = json.loads(json_data)

                        # Extract relevant data
                        location = json_data["location"]
                        data = [[entry["name"], entry["activity"], entry["hours"]] for entry in json_data["entries"]]
                        total_hours = json_data["total_hours"]

                        print("=== Location:", location)
                        print("=== Data:", data)
                        print("=== Total Horas:", total_hours)

                    except json.JSONDecodeError as e:
                        print("Error parsing JSON:", e)

                except json.JSONDecodeError as e:
                    print("Erro ao decodificar JSON:", e)

            else:
                print("JSON não encontrado")


        if type == 'audio':
            action1, action2 = st.columns(2)
            with action1:  # download arquivo em MP3
                with open(new_file, "rb") as f:
                    data = f.read()
                    st.download_button(
                        label='Save data',
                        data=data,
                        file_name= "audio-hours.mp3",
                        mime="audio/mpeg"
                    )

sys.path.append(str(Path(__file__).resolve().parents[1]))

# --- GOOGLE API initialization
# print('Configuring apikey...')
# os.environ['GEMINI_API_KEY'] = apikey
# Read Gemini API-Key credentials stored in secrets.toml file
apikey = st.secrets.google_api["apikey"]
genai.configure(api_key=apikey)

# --- LOCAL configurations
# set the locale to Spanish (Spain)
locale.setlocale(locale.LC_NUMERIC, 'es_ES.UTF-8')
# get today date
TODAY = datetime.strptime(datetime.now().strftime("%d-%m-%Y"), "%d-%m-%Y")
# LANG = ["Português-BR", "Español-ES"]
# SOURCE = ["Audio", "Audio file"]

output_format = html_table_format()
output_json = json_format()
DESC = (f"Show an html table using the output format {output_format}."
        f"Always sum the total worked hours and put it in the last row of the table in bold format."
        f"Below the table display return the data in JSON format with the following structure {output_json}")

# Define Gemini AI instructions according to selected language
instruction = (f"Based on what you understand from the audio, always give the answer in the same language. "
              f"The target user are mostly carpentry service firms in order to register their daily jobs. "
              f"It is important to keep track of the persons names, tasks and hours spent by each one. "
              f"The table must be populated exactly with the name of the person, "
              f"the task the person has done and the hours the person has spent on it. "
              f"Describe the activity in a complete form. "
              f"If you don't understand a name, write 'not clear', but keep the record of task and hours."
              f"Do the job with no verbosity, don't display your comments. "
              f"If the date is not mentioned in the audio use the date {TODAY} in the format '%b-%d-%Y'. ")

# Choosing the Gemini model
# model_name = "gemini-1.5-flash"
model_name = "gemini-2.0-flash"
# model_name = "gemini-2.0-flash-Lite"

# --- starting STREAMLIT
st.set_page_config(layout="wide")
st.header('JK Services Co.')
st.subheader('Daily Work Report')
st.text(f'- powered by Google AI model {model_name}')
st.divider()

# st.sidebar.markdown("# Menu")
# # Define language to be used
# lang = st.sidebar.selectbox("Seleccione el idioma:", LANG)

# Tabs
TAB_0 = 'Speak'
# TAB_1 = 'Subir archivo'

tab = option_menu(
    menu_title='',
    options=['Speak'],
    icons=['bi bi-mic-fill','bi-filetype-mp3'],
    menu_icon='cast',
    orientation='horizontal',
    default_index=0
)

if tab == TAB_0:
    # Enter the audio
    st.markdown("Speak normally and make sure you include the following terms:")
    st.markdown("- :blue-background[**the name of the local**]")
    st.markdown("- :red-background[**the names of the workers**]")
    st.markdown("- :blue-background[**the activities developed by each worker**]")
    st.markdown("- :red-background[**the hours spent on each activity by each worker**]")
    st.markdown("- if no :blue-background[**date**] is mentioned the system will assume the current date/time")
    st.markdown("Press the microphone icon bellow to start speaking and press again when finished.")
    audio_value = st.audio_input("")
    input_type = "audio"
    process_audio(audio_value, model_name, instruction, DESC, input_type)

# if tab == TAB_1:
#     # Select the audio file
#     audio_value = st.file_uploader(label='Seleccione el archivo:', type=['mp3', 'm4a', 'wav'])
#     input_type = "file"
#     process_audio(audio_value, model_name, DESC, input_type)
