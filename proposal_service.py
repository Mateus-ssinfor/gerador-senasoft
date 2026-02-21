import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm

from utils import data_pt_br, moeda_pt_br

import os
LIBREOFFICE_PATH = os.getenv("LIBREOFFICE_PATH", r"C:\Program Files\LibreOffice\program\soffice.exe")


def _convert_docx_to_pdf(docx_path: str, out_dir: str) -> str:
    """
    Converte DOCX -> PDF usando LibreOffice headless.
    Retorna o caminho do PDF gerado.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    cmd = [
        LIBREOFFICE_PATH,
        "--headless",
        "--convert-to", "pdf",
        "--outdir", out_dir,
        docx_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Falha ao converter para PDF.\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}\n"
        )

    pdf_name = Path(docx_path).with_suffix(".pdf").name
    pdf_path = str(Path(out_dir) / pdf_name)

    if not os.path.exists(pdf_path):
        raise RuntimeError("PDF não foi encontrado após conversão.")

    return pdf_path


def gerar_proposta_pdf(
    template_docx_path: str,
    output_pdf_path: str,
    dados: dict,
    imagem_upload_path: str,
) -> None:
    """
    Preenche template_proposta.docx com variáveis e imagem e gera PDF final.
    """
    tpl = DocxTemplate(template_docx_path)

    hoje = datetime.now()

    # Formata o valor para: R$ 200,00 (duzentos)
    moeda, ext = moeda_pt_br(dados["VALOR"])
    valor_formatado = f"{moeda} ({ext})"

    context = {
        "DATA": data_pt_br(hoje),
        "CLIENTE": dados["CLIENTE"],
        "CPF": dados["CPF"],
        "MODELO": dados["MODELO"],
        "FRANQUIA": dados["FRANQUIA"],
        "VALOR": valor_formatado,
        "IMAGEM": InlineImage(tpl, imagem_upload_path, width=Mm(70)),
    }

    tpl.render(context)

    with tempfile.TemporaryDirectory() as tmp:
        docx_out = str(Path(tmp) / "proposta_preenchida.docx")
        tpl.save(docx_out)

        pdf_tmp = _convert_docx_to_pdf(docx_out, tmp)

        Path(output_pdf_path).parent.mkdir(parents=True, exist_ok=True)
        with open(pdf_tmp, "rb") as src, open(output_pdf_path, "wb") as dst:
            dst.write(src.read())