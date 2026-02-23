import os
import subprocess
import tempfile
from pathlib import Path

from docxtpl import DocxTemplate


LIBREOFFICE_PATH = os.getenv("LIBREOFFICE_PATH", r"C:\Program Files\LibreOffice\program\soffice.exe")


def _convert_docx_to_pdf(docx_path: str, out_dir: str) -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    cmd = [
        LIBREOFFICE_PATH,
        "--headless",
        "--norestore",
        "--invisible",
        "--convert-to", "pdf",
        "--outdir", out_dir,
        docx_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Falha ao converter para PDF.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}\n"
        )

    pdf_name = Path(docx_path).with_suffix(".pdf").name
    pdf_path = str(Path(out_dir) / pdf_name)

    if not os.path.exists(pdf_path):
        raise RuntimeError("PDF não foi encontrado após conversão.")

    return pdf_path


def gerar_termo_pdf(template_docx_path: str, output_pdf_path: str, dados: dict) -> None:
    tpl = DocxTemplate(template_docx_path)
    tpl.render(dados)

    with tempfile.TemporaryDirectory() as tmp:
        docx_out = str(Path(tmp) / "termo_preenchido.docx")
        tpl.save(docx_out)

        pdf_tmp = _convert_docx_to_pdf(docx_out, tmp)

        Path(output_pdf_path).parent.mkdir(parents=True, exist_ok=True)
        with open(pdf_tmp, "rb") as src, open(output_pdf_path, "wb") as dst:
            dst.write(src.read())