from flask import Flask, render_template, request, send_file, redirect, session
from datetime import datetime
from urllib.parse import urlencode
from dotenv import load_dotenv
import base64
import fitz  # PyMuPDF
import os
import requests


load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")

PASTA_TERMOS = "termos"

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
            for nome_arquivo in os.listdir(PASTA_TERMOS):

                if (
                    nome_arquivo.lower().endswith(".pdf")
                    and nome_arquivo.startswith(numero)
                ):
                    arquivo = nome_arquivo
                    break

            if not arquivo:
                mensagem = "Arquivo não encontrado."

    return render_template(
        "index.html",
        arquivo=arquivo,
        mensagem=mensagem
    )
@app.route("/login")
def login():
    auth_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize"

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": "https://graph.microsoft.com/Files.ReadWrite.All offline_access",
    }

    return redirect(auth_url + "?" + urlencode(params))

@app.route("/auth/callback")
def callback():
    code = request.args.get("code")

    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "scope": "https://graph.microsoft.com/Files.ReadWrite.All offline_access",
    }

    r = requests.post(token_url, data=data)
    token_data = r.json()

    session["access_token"] = token_data.get("access_token")

    return "Login Microsoft OK!"


@app.route("/upload-test")
def upload_test():
    token = session.get("access_token")

    if not token:
        return redirect("/login")

    file_content = b"Arquivo de teste"

    url = "https://graph.microsoft.com/v1.0/drive/root:/teste.txt:/content"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "text/plain"
    }

    r = requests.put(url, headers=headers, data=file_content)

    return r.json()

@app.route("/pdf/<path:arquivo>")
def pdf(arquivo):

    caminho = os.path.join(PASTA_TERMOS, arquivo)

    return send_file(
        caminho,
        mimetype="application/pdf",
        as_attachment=False
    )

@app.route("/assinar/<arquivo>")
def pagina_assinar(arquivo):
    return render_template("assinar.html", arquivo=arquivo)



def inserir_assinatura_pdf(arquivo_pdf, assinatura_png):
    
    pdf_original = os.path.join("termos", arquivo_pdf)

    if not os.path.exists(pdf_original):
        return "PDF não encontrado", 404

    os.makedirs("termos_assinados", exist_ok=True)

    pdf_saida = os.path.join("termos_assinados", arquivo_pdf)

    doc = fitz.open(pdf_original)

    pagina = doc[2]  # FIX

    area_assinatura = fitz.Rect(200, 80, 350, 700)

    pagina.insert_image(area_assinatura, filename=assinatura_png)

    doc.save(pdf_saida)
    doc.close()

    print("PDF ASSINADO GERADO:", pdf_saida)


@app.route("/salvar_assinatura/<arquivo>", methods=["POST"])
def salvar_assinatura(arquivo):

    try:
        dados = request.get_json()
        assinatura = dados["assinatura"]

        assinatura = assinatura.replace("data:image/png;base64,", "")
        imagem = base64.b64decode(assinatura)

        os.makedirs("assinaturas", exist_ok=True)

        caminho_png = os.path.join("assinaturas", "assinatura.png")

        with open(caminho_png, "wb") as f:
            f.write(imagem)

        # gera PDF assinado
        inserir_assinatura_pdf(arquivo, caminho_png)

        caminho_pdf = os.path.join("termos_assinados", arquivo)

        # 🔥 UPLOAD PARA ONEDRIVE
        token = session.get("access_token")

        if token:
            upload_onedrive(token, caminho_pdf, arquivo)

        return {
            "sucesso": True,
            "arquivo": arquivo,
            "onedrive": "enviado"
        }

    except Exception as e:
        print("ERRO:", e)
        return str(e), 500
    
    
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

def upload_onedrive(token, caminho_arquivo, nome_arquivo):
    url = f"https://graph.microsoft.com/v1.0/drive/root:/assinaturas/{nome_arquivo}:/content"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/pdf"
    }

    with open(caminho_arquivo, "rb") as f:
        response = requests.put(url, headers=headers, data=f)

    return response.json()
    

#if __name__ == "__main__":
    #app.run(debug=True)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
