from flask import Blueprint, render_template, request

from auth import login_obrigatorio
from extensions import mongo
from pipeline import limiares_atuais

alunos_bp = Blueprint("alunos", __name__, url_prefix="/alunos")

POR_PAGINA = 20


@alunos_bp.route("/")
@login_obrigatorio
def lista():
    busca = (request.args.get("q") or "").strip() or None
    situacao = request.args.get("situacao") or None
    try:
        pagina = max(int(request.args.get("pagina", 1)), 1)
    except ValueError:
        pagina = 1

    if not mongo.disponivel:
        return render_template("alunos_lista.html", itens=[], total=0, pagina=1, paginas=1,
                                busca=busca, situacao=situacao, mongo_ok=False)

    itens, total = mongo.listar_alunos(busca, situacao, pagina, POR_PAGINA)
    paginas = max((total - 1) // POR_PAGINA + 1, 1)
    return render_template("alunos_lista.html", itens=itens, total=total, pagina=pagina,
                            paginas=paginas, busca=busca, situacao=situacao, mongo_ok=True)


@alunos_bp.route("/<matricula>")
@login_obrigatorio
def detalhe(matricula):
    if not mongo.disponivel:
        return render_template("aluno_detalhe.html", aluno=None, mongo_ok=False)

    aluno = mongo.buscar_aluno(matricula)
    parcelas, predicoes = [], []
    if aluno:
        parcelas = mongo.parcelas_aluno(aluno["id_aluno"])
        predicoes = mongo.predicoes_aluno(aluno["id_aluno"])
    alto, medio = limiares_atuais()
    return render_template("aluno_detalhe.html", aluno=aluno, parcelas=parcelas, predicoes=predicoes,
                            mongo_ok=True, limiar_alto=alto, limiar_medio=medio)
