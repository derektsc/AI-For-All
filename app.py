#pip install pytesseract
from flask import Flask, request, render_template, jsonify, session
import PyPDF2
import base64
import google.generativeai as genai
import io
import pytesseract
import requests
import secrets #gerar chave aleatoria para secret_key do app
from PIL import Image # Importe a biblioteca PIL para lidar com imagens


#Para processar imagens e extrair texto delas. Uma biblioteca popular e de código aberto é o Tesseract OCR voce deve baixar em:
#https://github.com/UB-Mannheim/tesseract/wiki

# Configure o caminho para o executável do Tesseract (ajuste para o seu sistema)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

GOOGLE_API_KEY="AIzaSyCv-j5gPD45OX9MMql1aefQO6Jtsf8CuUU"
genai.configure(api_key=GOOGLE_API_KEY)

generation_config = {
    "candidate_count":1,
    "temperature": 0.4,
}
safety_settings = {
    "HARASSMENT": "BLOCK_NONE",
    "HATE": "BLOCK_NONE",
    "SEXUAL": "BLOCK_NONE",
    "DANGEROUS": "BLOCK_NONE",
}
model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                              generation_config=generation_config,
                              safety_settings=safety_settings)

############### MODELOS DE CHAT #############################

doctor_model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                                      generation_config=generation_config,
                                      safety_settings=safety_settings)
doctor_chat = doctor_model.start_chat(history=[])

teacher_model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                                      generation_config=generation_config,
                                      safety_settings=safety_settings)
teacher_chat = teacher_model.start_chat(history=[])

nature_model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                                     generation_config=generation_config,
                                     safety_settings=safety_settings)
nature_chat = nature_model.start_chat(history=[])

analise_model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                                        generation_config=generation_config,
                                        safety_settings=safety_settings)
analise_chat = analise_model.start_chat(history=[])


################################################
#cria instancia da aplicação flask
app = Flask(__name__)

# Gera uma chave secreta aleatória
app.secret_key = secrets.token_urlsafe(32)


############# Rotas para as paginas dos robos
@app.route('/index.html')
def home():
    return render_template('index.html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/teacher_robot.html')
def teacher():
    return render_template('teacher_robot.html')

@app.route('/nature_robot.html')
def nature():
    return render_template('nature_robot.html')

@app.route('/excel_robot.html')
def excel():
    return render_template('excel_robot.html')

@app.route('/chef_robot.html')
def chef():
    return render_template('chef_robot.html')



#############

@app.route("/doctor_robot.html", methods=["GET", "POST"])
def upload_file():
    text_content = None 
    num_pages = None
    erro_msg = ""
    generated_text = ""
    filename = ""

    if request.method == "POST":
        if "pdf_file" not in request.files:
            erro_msg = "Nenhum arquivo PDF anexado!"
            return render_template("doctor_robot.html", erro_msg=erro_msg)
        
        file = request.files["pdf_file"]
        
        if file.filename == "":
            erro_msg = "Nenhum arquivo selecionado! Por favor selecione um arquivo em formato PDF"
            return render_template("doctor_robot.html", erro_msg=erro_msg)

        if file and file.filename.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            filename = file.filename
            text_content = ""
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text_content += page.extract_text()
            
            #Usar a API Gemini para gerar uma descrição do PDF
            #prompt = f"Este é o texto extraído do PDF:\n{text_content}\n\nFaça um resumo gerando uma descrição concisa do conteúdo do PDF:"
            prompt = f"Aja como um médico não utilize '*', este é o texto extraído do PDF:\n{text_content}\n\nCaso identifique que é um pedido de exames liste cada um dos exames e verifique se o CRM do médico é valido, gere também uma descrição concisa do conteúdo do PDF, censure nomes e os 2 ultimos digitos do CRM \n.Caso não seja um pedido médico diga 'não é um pedido médico' e não acrescente mais nada."
            response = doctor_chat.send_message(prompt)
            generated_text = response.text

         #   return jsonify({
         #       'status': 'sucesso',
         #       'arquivo': filename,
         #       'resposta': response.text
         #   })

        else:
            erro_msg = "Tipo de arquivo inválido. Apenas arquivos PDF são permitidos."
            return render_template("doctor_robot.html", erro_msg=erro_msg)
    
    return render_template("doctor_robot.html", text_content=text_content, num_pages=num_pages, generated_text=generated_text)

@app.route('/chatbot', methods=['POST'])
def chatbot():
    mensagem = request.json['mensagem']
    resposta_gemini = ""
    
    if mensagem.startswith("upload:"):  # Verifica se a mensagem é um upload de arquivo
        # Extraia o conteúdo do PDF (texto) da mensagem
        text_content = mensagem.split(":", 1)[1] 

        # Use a API do Gemini para gerar a resposta com base no texto do PDF
        prompt = f"Este é o texto extraído do PDF:\n{text_content}\n\nFaça um resumo gerando uma descrição concisa do conteúdo do PDF:"
        response = doctor_chat.send_message(prompt)
        resposta_gemini = response.text
    else:
        response = doctor_chat.send_message(mensagem)
        resposta_gemini = response.text
        
    return jsonify({'resposta': resposta_gemini})

#######################################################################
#Teacher bot:

@app.route('/teacher_chatbot', methods=['POST'])
def teacher_chatbot():
    global teacher_chat # Acesse a variável global chat
    mensagem = request.json['mensagem']
    resposta_gemini = ""

    if mensagem.startswith("upload_pdf:"):
        pdf_data = mensagem.split("upload_pdf:", 1)[1]
        pdf_bytes = base64.b64decode(pdf_data.split(",", 1)[1])

        try:
            text_content = ""
            pdf_file_object = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file_object)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content += page.extract_text()

            prompt = f"Aja como um professor inteligente, este é o texto extraído do PDF:\n{text_content}\n\n Você só esta permitido fazer um resumo caso o texto se trate de um conteudo voltado para aprendizagem e estudos, caso seja de outra area realacionada retorne 'Não identificado como conteúdo educativo'"
            response = teacher_chat.send_message(prompt)
            resposta_gemini = response.text

        except Exception as e:
            resposta_gemini = f"Erro ao processar o PDF: {str(e)}"

    elif mensagem.startswith("upload_imagem:"):
        imagem_data = mensagem.split("upload_imagem:", 1)[1]
        imagem_bytes = base64.b64decode(imagem_data.split(",", 1)[1])

        try:
            # Abra a imagem com a biblioteca PIL
            imagem = Image.open(io.BytesIO(imagem_bytes))

            # Extrair o texto da imagem usando o Tesseract OCR
            texto_extraido = pytesseract.image_to_string(imagem)

            prompt = f"Aja como um professor inteligente, este é o texto extraído da imagem:\n{texto_extraido}\n\n caso identifique que é uma questão de a resposta correta, pergunte ao usuario se ele prefere a resposta em forma de texto ou em JSON, caso seja em JSON retorne somente [pergunta: ], [resposta correta: ] e [explicação resumida: ] não precisa da pergunta completa no formato JSON. Não cometa erros de calculo. Não utilize emojis."
            response = teacher_chat.send_message(prompt)
            resposta_gemini = response.text
        except Exception as e:
            resposta_gemini = f"Erro ao processar a imagem: {str(e)}"

    elif mensagem == "/limpar": # Nova condição para limpar o chat
        teacher_chat = model.start_chat(history=[]) # Reinicia o chat
        resposta_gemini = "Histórico da conversa limpo!"
    else:
        # Verifique se a mensagem é texto, caso contrário, trate como um erro
        if isinstance(mensagem, str):
            response = teacher_chat.send_message(mensagem)
            resposta_gemini = response.text
        else:
            resposta_gemini = "Erro: Tipo de mensagem inválido. Envie texto, PDF ou imagem."

    return jsonify({'resposta': resposta_gemini})




####################NATURE BOT:

# Função obter dados clima:

def obter_dados_clima(localizacao):
    api_key = "017bf4e06aec85a114988450ca982f3a" # SUBSTITUA PELA SUA CHAVE API_KEY
    base_url = "http://api.openweathermap.org/data/2.5/weather?"

    url = f"{base_url}appid={api_key}&q={localizacao}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        main = data['main']
        wind = data['wind']
        weather_description = data['weather'][0]['description'] # Descrição do clima
        rain = data.get('rain', {}).get('3h', 0) # Precipitação em mm
        alerts = data.get('alerts', []) # Alertas climáticos

        temperatura = round(main['temp'] - 273.15, 2) 
        umidade = main['humidity']
        vento = wind['speed']

        return {
            "temperatura": f"{temperatura}°C",
            "umidade": f"{umidade}%",
            "vento": f"{vento} m/s",
            "descricao": weather_description,
            "precipitacao": f"{rain} mm",
            "alertas": alerts
        }
    else:
        return None


@app.route('/nature_chatbot', methods=['POST'])
def nature_chatbot():
    global nature_chat
    mensagem = request.json['mensagem']
    resposta_gemini = ""

    if mensagem == "/limpar":
        nature_chat = nature_model.start_chat(history=[])
        resposta_gemini = "Histórico da conversa limpo!"
    else:
        try:
            localizacao = mensagem 
            dados_clima = obter_dados_clima(localizacao)

            if dados_clima:
                temperatura = dados_clima.get("temperatura", "N/A")
                umidade = dados_clima.get("umidade", "N/A")
                vento = dados_clima.get("vento", "N/A")
                descricao = dados_clima.get("descricao", "N/A")
                precipitacao = dados_clima.get("precipitacao", "N/A")
                alertas = dados_clima.get("alertas", [])

                # Formatar alertas climáticos (se houver)
                alertas_formatados = ""
                if alertas:
                    for alerta in alertas:
                        alertas_formatados += f"- {alerta['event']}: {alerta['description']}\n"

                prompt = f"""
                'Usuário deseja saber sobre o clima em {localizacao}.

                Dados do clima:
                Temperatura: {temperatura}
                Umidade: {umidade}
                Vento: {vento}
                Descrição: {descricao}
                Precipitação (últimas 3h): {precipitacao}
                Alertas climáticos: 
                {alertas_formatados if alertas_formatados else "Sem alertas no momento."}

                Forneça um resumo conciso sobre o clima em {localizacao}, 
                incluindo alertas e riscos, se houver. 
                """

                response = nature_chat.send_message(prompt)
                resposta_gemini = response.text

                # Armazena a resposta do primeiro chatbot para usar no segundo
                session['resposta_clima'] = resposta_gemini

                # Armazenar dados em um arquivo de texto (opcional)
                with open("historico_clima.txt", "a", encoding='utf-8') as f:
                    f.write(f"Localização: {localizacao}\n")
                    f.write(f"Temperatura: {temperatura}\n")
                    f.write(f"Umidade: {umidade}\n")
                    f.write(f"Vento: {vento}\n")
                    f.write(f"Descrição: {descricao}\n")
                    f.write(f"Precipitação: {precipitacao}\n")
                    f.write(f"Alertas: {alertas_formatados if alertas_formatados else 'Sem alertas.'}\n")
                    f.write("-" * 20 + "\n")

            else:
                resposta_gemini = "Não foi possível encontrar informações sobre o clima para essa localização."
        except Exception as e:
            resposta_gemini = f"Erro ao processar a solicitação: {str(e)}"
    return jsonify({'resposta': resposta_gemini})


@app.route('/analise_chatbot', methods=['POST'])
def analise_chatbot():
    global analise_chat
    mensagem = request.json['mensagem']
    resposta_gemini = ""

    if mensagem == "/limpar":
        analise_chat = analise_model.start_chat(history=[])
        resposta_gemini = "Histórico da conversa limpo!"
    else:
        try:
            # Recupera a resposta do primeiro chatbot da sessão
            resposta_do_primeiro_chatbot = session.get('resposta_clima', '')
            # O prompt para o segundo chatbot inclui a mensagem do usuário
            # e a resposta do primeiro chatbot
            prompt = f"""
            Você é um meteorologista experiente. 

            **Etapa 1: Boletim Meteorológico**

            O usuário solicitou informações meteorológicas e disse: {mensagem}
            Aqui estão os dados coletados:
            {resposta_do_primeiro_chatbot}

            Crie um boletim meteorológico conciso e informativo sobre a localidade mencionada pelo usuário, utilizando os dados fornecidos. 

            Siga este formato:

            ## Boletim Meteorológico - [Data e Hora] - [Localização]

            **Condições:** [Descrição do clima - Ex: Céu limpo, Parcialmente nublado]
            **Temperatura:** [Temperatura] 
            **Sensação térmica:** [Sensação térmica, se disponível nos dados]
            **Umidade:** [Umidade]
            **Vento:** [Velocidade do vento] 
            **Precipitação:** [Informação sobre precipitação, se disponível]
            **Alertas:** [Alertas meteorológicos, se houver]

            **Etapa 2: Responda à Pergunta**

            Após fornecer o boletim, aguarde uma nova pergunta do usuário sobre as condições meteorológicas na localidade. 
            Responda à pergunta de forma clara e concisa, utilizando seus conhecimentos de meteorologia e os dados fornecidos.

            Exemplo:
            **Usuário:** Qual a previsão de chuva para amanhã?
            **Bot:** A previsão indica baixa probabilidade de chuva para amanhã.

            Lembre-se de:
            * Manter a linguagem clara e acessível.
            * Basear suas respostas nos dados fornecidos.
            * Se não souber a resposta, diga que não há informações suficientes."""
            response = analise_chat.send_message(prompt)
            resposta_gemini = response.text
        except Exception as e:
            resposta_gemini = f"Erro ao processar a solicitação: {str(e)}"
    return jsonify({'resposta': resposta_gemini})

if __name__ == "__main__":
    app.run(debug=True)
