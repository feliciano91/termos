from flask import Flask, render_template, request, send_file, redirect, session
from datetime import datetime
from urllib.parse import urlencode
from dotenv import load_dotenv
from flask import Response
from flask import jsonify
import base64
import fitz
import os
import requests


load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")





@app.route("/", methods=["GET", "POST"])
def index():

    arquivo = None
    mensagem = None

    if request.method == "POST":

        numero = request.form["numero"].strip()

        # Validar 6 dígitos
        if len(numero) != 6 or not numero.isdigit():
            mensagem = "Digite exatamente 6 números."
        else:

            # Procurar arquivo que comece com os 6 dígitos
            arquivo = None
            for item in listar_documentos():
                if item["name"].startswith(numero):
                    arquivo = item
                    break

            if not arquivo:
                mensagem = "Arquivo não encontrado."


    return render_template(
        "index.html",
        arquivo=arquivo,
        mensagem=mensagem
    )


@app.route("/descobrir_site")
def descobrir_site():

    token = obter_token_graph()

    headers = {
        "Authorization": f"Bearer {token}"
    }

    url = (
        "https://graph.microsoft.com/v1.0/"
        "sites/rlconstrucoes.sharepoint.com:/sites/RLConstrues"
    )

    r = requests.get(url, headers=headers)

    return r.json()

@app.route("/descobrir_drive")
def descobrir_drive():

    token = obter_token_graph()

    headers = {
        "Authorization": f"Bearer {token}"
    }

    site_id = "rlconstrucoes.sharepoint.com,f208e3bf-de95-4ec6-9bea-f79c617a1dfc,6d73ca91-ee0b-4145-ad21-787602630398"

    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"

    r = requests.get(url, headers=headers)

    return r.json()

@app.route("/listar_assinaturas")
def listar_assinaturas():

    token = obter_token_graph()

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Descobre o drive automaticamente
    site_id = "rlconstrucoes.sharepoint.com,f208e3bf-de95-4ec6-9bea-f79c617a1dfc,6d73ca91-ee0b-4145-ad21-787602630398"

    r = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive",
        headers=headers
    )

    drive = r.json()

    drive_id = drive["id"]

    # Lista a pasta Assinaturas1
    r = requests.get(
        f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/Assinaturas1:/children",
        headers=headers
    )

    return r.json()



def listar_documentos():
    
    token = obter_token_graph()

    headers = {
        "Authorization": f"Bearer {token}"
    }

    drive_id = "b!v-MI8pXexk6b6vecYXod_JHKc20L7kVBrSF4dgJjA5j6HX8lOL6OR4jJrnXvXG4H"

    url = (
        f"https://graph.microsoft.com/v1.0/"
        f"drives/{drive_id}/root:/Assinaturas1/Documentos:/children"
    )

    r = requests.get(url, headers=headers)

    r.raise_for_status()

    return r.json()["value"]

def obter_item(item_id):
    
    token = obter_token_graph()

    headers = {
        "Authorization": f"Bearer {token}"
    }

    drive_id = "b!v-MI8pXexk6b6vecYXod_JHKc20L7kVBrSF4dgJjA5j6HX8lOL6OR4jJrnXvXG4H"

    r = requests.get(
        f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}",
        headers=headers
    )

    r.raise_for_status()

    return r.json()


def baixar_pdf(item_id):
    
    token = obter_token_graph()

    headers = {
        "Authorization": f"Bearer {token}"
    }

    drive_id = "b!v-MI8pXexk6b6vecYXod_JHKc20L7kVBrSF4dgJjA5j6HX8lOL6OR4jJrnXvXG4H"

    url = (
        f"https://graph.microsoft.com/v1.0/"
        f"drives/{drive_id}/items/{item_id}/content"
    )

    r = requests.get(url, headers=headers)

    r.raise_for_status()

    return r.content


@app.route("/pdf/<item_id>")
def pdf(item_id):

    pdf = baixar_pdf(item_id)

    return Response(
        pdf,
        mimetype="application/pdf"
    )


@app.route("/assinar/<item_id>")
def pagina_assinar(item_id):
    return render_template(
        "assinar.html",
        item_id=item_id
    )


def inserir_assinatura_pdf(pdf_bytes, assinatura_png):
    
    doc = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    pagina = doc[2]

    area = fitz.Rect(200,340,400,440)

    pagina.insert_image(area, filename=assinatura_png)

    pdf_assinado = doc.tobytes()

    doc.close()

    return pdf_assinado



def enviar_pdf(nome, pdf):
    
    token = obter_token_graph()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":"application/pdf"
    }

    drive_id = "b!v-MI8pXexk6b6vecYXod_JHKc20L7kVBrSF4dgJjA5j6HX8lOL6OR4jJrnXvXG4H"

    url = (
        f"https://graph.microsoft.com/v1.0/"
        f"drives/{drive_id}"
        f"/root:/Assinaturas1/Assinados/{nome}:/content"
    )

    r = requests.put(
        url,
        headers=headers,
        data=pdf
    )

    r.raise_for_status()


def obter_token_graph():
    
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "https://graph.microsoft.com/.default"
    }

    r = requests.post(url, data=data)

    print("STATUS:", r.status_code)
    print("RESPOSTA:", r.text)

    r.raise_for_status()

    return r.json()["access_token"]


@app.route("/salvar_assinatura/<item_id>", methods=["POST"])
def salvar_assinatura(item_id):

    dados = request.get_json()

    assinatura = dados["assinatura"]

    assinatura = assinatura.replace(
        "data:image/png;base64,", ""
    )

    imagem = base64.b64decode(assinatura)

    nome_png = "assinatura.png"

    with open(nome_png,"wb") as f:
        f.write(imagem)

    pdf = baixar_pdf(item_id)

    pdf_assinado = inserir_assinatura_pdf(
        pdf,
        nome_png
    )

    item = obter_item(item_id)

    enviar_pdf(
        item["name"],
        pdf_assinado
    )

    return jsonify({
        "mensagem": "Documento assinado com sucesso!"
    })

 
@app.route("/baixar_assinado/<arquivo>")
def baixar_assinado(arquivo):

    caminho = os.path.join(
        "termos_assinados",
        arquivo
    )

    return send_file(
        caminho,
        as_attachment=True
    )

def criar_pasta_onedrive(token):
    url = "https://graph.microsoft.com/v1.0/drive/root/children"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    data = {
        "name": "assinaturas",
        "folder": {},
        "@microsoft.graph.conflictBehavior": "fail"
    }

    requests.post(url, headers=headers, json=data)

def upload_onedrive(token, caminho_arquivo, nome_arquivo):
    
    url = (
        f"https://graph.microsoft.com/v1.0/"
        f"drive/root:/assinaturas/{nome_arquivo}:/content"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/pdf"
    }

    with open(caminho_arquivo, "rb") as f:
        r = requests.put(
            url,
            headers=headers,
            data=f
        )

    print(r.status_code)
    print(r.text)

    r.raise_for_status()

    return r.json()

    resultado = upload_onedrive(
        token,
        caminho_pdf,
        arquivo
    )

    print("UPLOAD OK")
    print(resultado)

#if __name__ == "__main__":
    #app.run(debug=True)

print("CLIENT_ID:", CLIENT_ID)
print("TENANT_ID:", TENANT_ID)
print("CLIENT_SECRET:", "OK" if CLIENT_SECRET else "NÃO ENCONTRADO")


if __name__ == "__main__":
    print(app.url_map)
    app.run(host="0.0.0.0", port=5000)
