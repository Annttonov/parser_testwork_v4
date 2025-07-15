import requests
import json
import os

from dotenv import load_dotenv

load_dotenv()
input_path = 'input.pdf'


def ai_convert_pdf_to_md(pdf_file: str):
    url_pdf = 'https://api.mathpix.com/v3/pdf/'

    APP_ID = os.getenv('APP_ID')
    APP_KEY = os.getenv('APP_KEY')

    options = {
        "conversion_formats": {"docx": True, "tex.zip": True},
        "math_inline_delimiters": ["$", "$"],
        "rm_spaces": True
    }
    r = requests.post(url_pdf,
                      headers={
                          'app_id': APP_ID,
                          'app_key': APP_KEY,
                          },
                      data={"options_json": json.dumps(options)},
                      files={"file": open(pdf_file, "rb")})

    value = r.text.encode("utf-8")
    decoded_value = value.decode('utf-8').split(':')
    pdf_id = decoded_value[1].strip('"}')

    ans = ''
    while ans != '"completed"':
        rez = requests.get('https://api.mathpix.com/v3/pdf/' + pdf_id,
                           headers={
                               'app_id': APP_ID,
                               'app_key': APP_KEY,
                               })
        ans = rez.text.split(',')[0].split(':')[1]
        print(ans)

    url = url_pdf + pdf_id + ".md"
    response = requests.get(url,
                            headers={
                                'app_id': APP_ID,
                                'app_key': APP_KEY,
                                })
    with open(pdf_file.strip(".pdf") + ".md", "w", encoding="utf-8") as f:
        f.write(response.text)
    return f


ai_convert_pdf_to_md(input_path)
