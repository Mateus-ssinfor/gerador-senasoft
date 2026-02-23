import json
import os
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, redirect, url_for,
    send_file, jsonify, abort, request, session
)

from config import Config
from models import db, Proposal
from storage import proposal_pdf_path
from cleanup import cleanup_expired, cleanup_tmp_contracts

from proposal_service import gerar_proposta_pdf
from contract_service import gerar_contrato_pdf
from promissoria_service import gerar_promissoria_pdf
from termo_service import gerar_termo_pdf

from utils import data_curta_para_extenso


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # versão profissional (Railway Variables ou .env)
    app.config["APP_VERSION"] = os.getenv("APP_VERSION", "1.0.0")
    app.config["ADMIN_USER"] = os.getenv("ADMIN_USER", "admin")
    app.config["ADMIN_PASS"] = os.getenv("ADMIN_PASS", "admin")

    os.makedirs(app.config["STORAGE_DIR"], exist_ok=True)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    # --------- Proteção (login) ----------
    PUBLIC_PATHS = {"/", "/login", "/hub", "/health"}
    @app.before_request
    def _guard_and_cleanup():
        path = request.path

        # libera static e rotas públicas
        if path.startswith("/static/") or path in PUBLIC_PATHS:
            return None

        # exige login para o resto
        if not session.get("logged_in"):
            return redirect(url_for("access"))

        # limpeza (somente quando logado, pra não gastar)
        try:
            cleanup_expired(app.config["RETENTION_DAYS"])
        except Exception:
            pass

        try:
            cleanup_tmp_contracts(os.path.join(app.config["STORAGE_DIR"], "_contratos_tmp"), max_age_hours=24)
        except Exception:
            pass

        try:
            cleanup_tmp_contracts(os.path.join(app.config["STORAGE_DIR"], "_promissorias_tmp"), max_age_hours=24)
        except Exception:
            pass

        try:
            cleanup_tmp_contracts(os.path.join(app.config["STORAGE_DIR"], "_termos_tmp"), max_age_hours=24)
        except Exception:
            pass

        return None

    # --------- Telas públicas ----------
    @app.get("/")
    def access():
        return render_template("access.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template("login.html", erro=None, version=app.config["APP_VERSION"])

        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()

        if u == app.config["ADMIN_USER"] and p == app.config["ADMIN_PASS"]:
            session["logged_in"] = True
            return redirect(url_for("hub"))

        return render_template("login.html", erro="Usuário ou senha inválidos.", version=app.config["APP_VERSION"])

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("access"))

    @app.get("/hub")
    def hub():
        if not session.get("logged_in"):
            return redirect(url_for("access"))
        return render_template("hub.html")

    # --------- HUB: Sistema (placeholder) ----------
    @app.get("/sistema")
    def sistema():
        # depois a gente cria as telas Venda/OS aqui
        return "<h2>Sistema (Venda/OS) em construção</h2><p><a href='/hub'>Voltar</a></p>"

    # --------- GERADOR (o que já existe hoje) ----------
    @app.get("/gerador")
    def gerador():
        return render_template("gerador_home.html")

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

    # ---------------- CONTRATO ----------------
    @app.route("/contrato", methods=["GET", "POST"])
    def contrato_manual():
        pre = {"denom": "", "cpf": "", "modelo": "", "franquia": "", "valor": ""}

        if request.method == "GET":
            return render_template("contrato.html", pre=pre, erro=None, back_url=url_for("gerador"))

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
            pdf_path = os.path.join(out_dir, f"CONTRATO - {denominacao}.pdf")

            gerar_contrato_pdf(template_docx_path=template_path, output_pdf_path=pdf_path, dados=dados_contrato)
            return send_file(pdf_path, as_attachment=True)

        except Exception as e:
            return render_template("contrato.html", pre=pre, erro=str(e), back_url=url_for("gerador"))

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
            pdf_path = os.path.join(out_dir, f"CONTRATO - {p.client_name}.pdf")

            gerar_contrato_pdf(template_docx_path=template_path, output_pdf_path=pdf_path, dados=dados_contrato)
            return send_file(pdf_path, as_attachment=True)

        except Exception as e:
            return render_template("contrato.html", pre=pre, erro=str(e), back_url=url_for("recentes"))

    # ---------------- PROMISSÓRIA ----------------
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
            pdf_path = os.path.join(tmp_dir, f"PROMISSORIA - {nome}.pdf")

            dados = {"DATA": venc, "NOME": nome, "CPF": cpf, "ENDERECO": endereco}

            gerar_promissoria_pdf(template_docx_path=template_path, output_pdf_path=pdf_path, dados=dados, imagem_rg_path=img_path)

            try:
                os.remove(img_path)
            except Exception:
                pass

            return send_file(pdf_path, as_attachment=True)

        except Exception as e:
            return render_template("promissoria.html", erro=str(e))

    # ---------------- TERMO RETIRADA ----------------
    @app.route("/termo", methods=["GET", "POST"])
    def termo():
        if request.method == "GET":
            return render_template("termo.html", erro=None)

        try:
            eq = set(request.form.getlist("eq"))  # pode marcar mais de 1

ck = "☑"
un = "☐"

dados = {
    "DATA_RET": request.form.get("data_ret", "").strip(),
    "HORA_RET": request.form.get("hora_ret", "").strip(),
    "DATA_DEV": request.form.get("data_dev", "").strip(),
    "HORA_DEV": request.form.get("hora_dev", "").strip(),

    "NOME": request.form.get("nome", "").strip(),
    "TELEFONE": request.form.get("telefone", "").strip(),
    "ENDEREÇO": request.form.get("endereco", "").strip(),

    # CHECKS do template
    "CK_CPU": ck if "CPU" in eq else un,
    "CK_NOT": ck if "NOT" in eq else un,
    "CK_MON": ck if "MON" in eq else un,
    "CK_IMP": ck if "IMP" in eq else un,

    "MARCA": request.form.get("marca", "").strip(),
    "MODELO": request.form.get("modelo", "").strip(),
    "SERIE": request.form.get("serie", "").strip(),
    "ACESSORIO": request.form.get("acessorio", "").strip(),
    "OBSERVAÇÃO": request.form.get("observacao", "").strip(),
}

            template_path = os.path.abspath("./assets/template_termo_retirada.docx")
            tmp_dir = os.path.join(app.config["STORAGE_DIR"], "_termos_tmp")
            os.makedirs(tmp_dir, exist_ok=True)

            nome = dados["NOME"] or "Cliente"
            pdf_path = os.path.join(tmp_dir, f"TERMO RETIRADA - {nome}.pdf")

            gerar_termo_pdf(template_docx_path=template_path, output_pdf_path=pdf_path, dados=dados)
            return send_file(pdf_path, as_attachment=True)

        except Exception as e:
            return render_template("termo.html", erro=str(e))

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)