from flask import Flask, render_template, request, send_file
from datetime import datetime
import base64
import fitz  # PyMuPDF
import os

app = Flask(__name__)

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

    os.makedirs("termos_assinados", exist_ok=True)

    pdf_saida = os.path.join(
        "termos_assinados",
        arquivo_pdf
    )

    doc = fitz.open(pdf_original)

    # Primeira página
    pagina = doc[2]

    # Posição fixa da assinatura
    area_assinatura = fitz.Rect(
        200, 80,   # canto superior esquerdo
        350, 700    # canto inferior direito
    )

    pagina.insert_image(
        area_assinatura,
        filename=assinatura_png
    )

    doc.save(pdf_saida)
    doc.close()

    print("PDF ASSINADO GERADO:", pdf_saida)

@app.route("/salvar_assinatura/<arquivo>", methods=["POST"])
def salvar_assinatura(arquivo):

    try:

        dados = request.get_json()

        assinatura = dados["assinatura"]

        assinatura = assinatura.replace(
            "data:image/png;base64,",
            ""
        )

        imagem = base64.b64decode(assinatura)

        os.makedirs("assinaturas", exist_ok=True)

        caminho_png = os.path.join(
            "assinaturas",
            "assinatura.png"
        )

        with open(caminho_png, "wb") as f:
            f.write(imagem)

        inserir_assinatura_pdf(
            arquivo,
            caminho_png
        )

        return "Documento assinado com sucesso!"

    except Exception as e:
        print("ERRO:", e)
        return str(e), 500

    

#if __name__ == "__main__":
    #app.run(debug=True)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)