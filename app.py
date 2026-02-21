import json
import os
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, redirect, url_for,
    send_file, jsonify, abort, request
)

from config import Config
from models import db, Proposal
from storage import proposal_pdf_path
from cleanup import cleanup_expired, cleanup_tmp_contracts
from proposal_service import gerar_proposta_pdf
from contract_service import gerar_contrato_pdf
from promissoria_service import gerar_promissoria_pdf
from utils import data_curta_para_extenso


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config["STORAGE_DIR"], exist_ok=True)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    @app.before_request
    def _auto_cleanup():
        # limpa propostas vencidas (10 dias)
        try:
            cleanup_expired(app.config["RETENTION_DAYS"])
        except Exception:
            pass

        # limpa contratos temporários (24h)
        try:
            tmp_contracts = os.path.join(app.config["STORAGE_DIR"], "_contratos_tmp")
            cleanup_tmp_contracts(tmp_contracts, max_age_hours=24)
        except Exception:
            pass

        # limpa promissórias temporárias (24h)
        try:
            tmp_prom = os.path.join(app.config["STORAGE_DIR"], "_promissorias_tmp")
            cleanup_tmp_contracts(tmp_prom, max_age_hours=24)
        except Exception:
            pass

    @app.get("/")
    def home():
        return render_template("home.html")

    # ---------------- PROPOSTA ----------------
    @app.route("/proposta", methods=["GET", "POST"])
    def proposta():
        if request.method == "GET":
            return render_template("proposta.html", erro=None)

        try:
            cliente = request.form.get("cliente", "").strip()
            cpf = request.form.get("cpf", "").strip()
            modelo = request.form.get("modelo", "").strip()
            franquia = request.form.get("franquia", "").strip()
            valor = request.form.get("valor", "").strip()

            img = request.files.get("imagem")
            if not img or img.filename == "":
                return render_template("proposta.html", erro="Envie a imagem do equipamento.")

            created_at = datetime.now()
            expires_at = created_at + timedelta(days=app.config["RETENTION_DAYS"])

            payload = {
                "CLIENTE": cliente,
                "CPF": cpf,
                "MODELO": modelo,
                "FRANQUIA": franquia,
                "VALOR": valor,
            }

            p = Proposal(
                client_name=cliente,
                created_at=created_at,
                expires_at=expires_at,
                payload_json=json.dumps(payload, ensure_ascii=False),
                pdf_path=None
            )
            db.session.add(p)
            db.session.commit()

            tmp_dir = os.path.join(app.config["STORAGE_DIR"], "_tmp")
            os.makedirs(tmp_dir, exist_ok=True)
            img_path = os.path.join(tmp_dir, f"img_{p.id}.png")
            img.save(img_path)

            template_path = os.path.abspath("./assets/template_proposta.docx")
            pdf_final = proposal_pdf_path(app.config["STORAGE_DIR"], cliente, created_at, p.id)

            gerar_proposta_pdf(
                template_docx_path=template_path,
                output_pdf_path=pdf_final,
                dados=payload,
                imagem_upload_path=img_path
            )

            p.pdf_path = pdf_final
            db.session.commit()

            try:
                os.remove(img_path)
            except Exception:
                pass

            return redirect(url_for("recentes"))

        except Exception as e:
            return render_template("proposta.html", erro=str(e))

    @app.get("/recentes")
    def recentes():
        items = Proposal.query.order_by(Proposal.created_at.desc()).limit(200).all()
        return render_template("recentes.html", items=items)

    @app.get("/api/proposta/<int:proposal_id>")
    def api_proposta(proposal_id: int):
        p = Proposal.query.get_or_404(proposal_id)
        payload = json.loads(p.payload_json or "{}")

        def dt_br(dt):
            return dt.strftime("%d/%m/%Y %H:%M")

        return jsonify({
            "id": p.id,
            "client_name": p.client_name,
            "criada": dt_br(p.created_at),
            "expira": dt_br(p.expires_at),
            "cpf": payload.get("CPF", ""),
            "modelo": payload.get("MODELO", ""),
            "franquia": payload.get("FRANQUIA", ""),
            "valor": payload.get("VALOR", ""),
        })

    @app.get("/proposta/<int:proposal_id>/baixar")
    def baixar_proposta(proposal_id: int):
        p = Proposal.query.get_or_404(proposal_id)
        if not p.pdf_path or not os.path.exists(p.pdf_path):
            abort(404, "PDF não encontrado.")
        return send_file(p.pdf_path, as_attachment=True)

    @app.post("/proposta/<int:proposal_id>/excluir")
    def excluir_proposta(proposal_id: int):
        p = Proposal.query.get_or_404(proposal_id)
        if p.pdf_path and os.path.exists(p.pdf_path):
            try:
                os.remove(p.pdf_path)
            except Exception:
                pass
        db.session.delete(p)
        db.session.commit()
        return redirect(url_for("recentes"))

    # ---------------- CONTRATO (MANUAL) ----------------
    @app.route("/contrato", methods=["GET", "POST"])
    def contrato_manual():
        pre = {"denom": "", "cpf": "", "modelo": "", "franquia": "", "valor": ""}

        if request.method == "GET":
            return render_template("contrato.html", pre=pre, erro=None, back_url=url_for("home"))

        try:
            denominacao = request.form.get("denominacao", "").strip()
            cpf_cnpj = request.form.get("cpf_cnpj", "").strip()
            endereco = request.form.get("endereco", "").strip()
            telefone = request.form.get("telefone", "").strip()
            email = request.form.get("email", "").strip()
            equipamento = request.form.get("equipamento", "").strip()
            franquia = request.form.get("franquia", "").strip()
            valor_mensal = request.form.get("valor_mensal", "").strip()

            data_inicio = data_curta_para_extenso(request.form.get("data_inicio", "").strip())
            data_termino = data_curta_para_extenso(request.form.get("data_termino", "").strip())

            acc_list = request.form.getlist("acc")
            acc_outros = request.form.get("acc_outros", "").strip()
            if acc_outros:
                acc_list.append(acc_outros)
            acessorios = " / ".join([a for a in acc_list if a])

            dados_contrato = {
                "DENOMINACAO": denominacao,
                "CPF_CNPJ": cpf_cnpj,
                "ENDERECO": endereco,
                "TELEFONE": telefone,
                "EMAIL": email,
                "EQUIPAMENTO": equipamento,
                "ACESSORIOS": acessorios,
                "DATA_INICIO": data_inicio,
                "DATA_TERMINO": data_termino,
                "FRANQUIA": franquia,
                "VALOR_MENSAL": valor_mensal,
            }

            template_path = os.path.abspath("./assets/template_contrato.docx")
            out_dir = os.path.join(app.config["STORAGE_DIR"], "_contratos_tmp")
            os.makedirs(out_dir, exist_ok=True)

            pdf_path = os.path.join(out_dir, f"CONTRATO - {denominacao} - {datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf")

            gerar_contrato_pdf(template_docx_path=template_path, output_pdf_path=pdf_path, dados=dados_contrato)
            return send_file(pdf_path, as_attachment=True)

        except Exception as e:
            return render_template("contrato.html", pre=pre, erro=str(e), back_url=url_for("home"))

    # ---------------- CONTRATO (DA PROPOSTA) ----------------
    @app.route("/contrato/<int:proposal_id>", methods=["GET", "POST"])
    def contrato(proposal_id: int):
        p = Proposal.query.get_or_404(proposal_id)
        payload = json.loads(p.payload_json or "{}")

        pre = {
            "denom": payload.get("CLIENTE", ""),
            "cpf": payload.get("CPF", ""),
            "modelo": payload.get("MODELO", ""),
            "franquia": payload.get("FRANQUIA", ""),
            "valor": payload.get("VALOR", ""),
        }

        if request.method == "GET":
            return render_template("contrato.html", pre=pre, erro=None, back_url=url_for("recentes"))

        try:
            denominacao = request.form.get("denominacao", "").strip()
            cpf_cnpj = request.form.get("cpf_cnpj", "").strip()
            endereco = request.form.get("endereco", "").strip()
            telefone = request.form.get("telefone", "").strip()
            email = request.form.get("email", "").strip()
            equipamento = request.form.get("equipamento", "").strip()
            franquia = request.form.get("franquia", "").strip()
            valor_mensal = request.form.get("valor_mensal", "").strip()

            data_inicio = data_curta_para_extenso(request.form.get("data_inicio", "").strip())
            data_termino = data_curta_para_extenso(request.form.get("data_termino", "").strip())

            acc_list = request.form.getlist("acc")
            acc_outros = request.form.get("acc_outros", "").strip()
            if acc_outros:
                acc_list.append(acc_outros)
            acessorios = " / ".join([a for a in acc_list if a])

            dados_contrato = {
                "DENOMINACAO": denominacao,
                "CPF_CNPJ": cpf_cnpj,
                "ENDERECO": endereco,
                "TELEFONE": telefone,
                "EMAIL": email,
                "EQUIPAMENTO": equipamento,
                "ACESSORIOS": acessorios,
                "DATA_INICIO": data_inicio,
                "DATA_TERMINO": data_termino,
                "FRANQUIA": franquia,
                "VALOR_MENSAL": valor_mensal,
            }

            template_path = os.path.abspath("./assets/template_contrato.docx")
            out_dir = os.path.join(app.config["STORAGE_DIR"], "_contratos_tmp")
            os.makedirs(out_dir, exist_ok=True)

            pdf_path = os.path.join(out_dir, f"CONTRATO - {p.client_name} - #{p.id}.pdf")

            gerar_contrato_pdf(template_docx_path=template_path, output_pdf_path=pdf_path, dados=dados_contrato)
            return send_file(pdf_path, as_attachment=True)

        except Exception as e:
            return render_template("contrato.html", pre=pre, erro=str(e), back_url=url_for("recentes"))

    # ---------------- PROMISSÓRIA (MANUAL) ----------------
    @app.route("/promissoria", methods=["GET", "POST"])
    def promissoria():
        if request.method == "GET":
            return render_template("promissoria.html", erro=None)

        try:
            nome = request.form.get("nome", "").strip()
            cpf = request.form.get("cpf", "").strip()
            endereco = request.form.get("endereco", "").strip()

            venc = data_curta_para_extenso(request.form.get("data_venc", "").strip())

            img = request.files.get("imagem_rg")
            if not img or img.filename == "":
                return render_template("promissoria.html", erro="Envie a foto do documento (RG/CNH).")

            tmp_dir = os.path.join(app.config["STORAGE_DIR"], "_promissorias_tmp")
            os.makedirs(tmp_dir, exist_ok=True)

            img_path = os.path.join(tmp_dir, f"rg_{int(datetime.utcnow().timestamp())}.png")
            img.save(img_path)

            template_path = os.path.abspath("./assets/template_promissoria.docx")
            pdf_path = os.path.join(tmp_dir, f"PROMISSORIA - {nome} - {datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf")

            dados = {"DATA": venc, "NOME": nome, "CPF": cpf, "ENDERECO": endereco}

            gerar_promissoria_pdf(
                template_docx_path=template_path,
                output_pdf_path=pdf_path,
                dados=dados,
                imagem_rg_path=img_path
            )

            try:
                os.remove(img_path)
            except Exception:
                pass

            return send_file(pdf_path, as_attachment=True)

        except Exception as e:
            return render_template("promissoria.html", erro=str(e))

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)