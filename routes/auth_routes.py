from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from config import config
from extensions import mongo

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")
        ok, papel = False, "admin"

        if mongo.disponivel:
            doc = mongo.buscar_usuario(usuario)
            if doc and check_password_hash(doc["senha_hash"], senha):
                ok, papel = True, doc.get("papel", "admin")
        else:
            # Modo degradado (sem MongoDB): credenciais do ambiente, só para demonstração local.
            ok = usuario == config.ADMIN_USER and senha == config.ADMIN_PASSWORD

        if ok:
            session["usuario"] = usuario
            session["papel"] = papel
            proximo = request.args.get("proximo") or url_for("dashboard.index")
            return redirect(proximo)
        flash("Usuário ou senha inválidos.", "erro")

    return render_template("login.html", mongo_ok=mongo.disponivel)


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Sessão encerrada.", "ok")
    return redirect(url_for("auth.login"))
