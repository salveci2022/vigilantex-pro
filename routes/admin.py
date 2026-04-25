from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Usuario, Empresa, Posto, Plantao
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)

def _require_admin():
    return current_user.role in ('admin', 'gestor')

# ── DASHBOARD GERAL ──────────────────────────────
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if not _require_admin():
        return jsonify({'erro': 'Sem permissão'}), 403

    emp_id = current_user.empresa_id
    hoje   = datetime.utcnow().date()
    mes    = datetime.utcnow().replace(day=1)

    total_vigs    = Usuario.query.filter_by(empresa_id=emp_id, role='vigilante', ativo=True).count()
    ativos_hoje   = Plantao.query.filter(
        Plantao.empresa_id==emp_id,
        Plantao.encerrado==False
    ).count()
    plantoes_mes  = Plantao.query.filter(
        Plantao.empresa_id==emp_id,
        Plantao.inicio >= mes
    ).count()

    from models import Ocorrencia, Panico
    ocorr_mes = (Ocorrencia.query
                 .join(Plantao)
                 .filter(Plantao.empresa_id==emp_id,
                         Ocorrencia.data_hora >= mes)
                 .count())
    panicos_mes = (Panico.query
                   .join(Plantao)
                   .filter(Plantao.empresa_id==emp_id,
                           Panico.data_hora >= mes)
                   .count())

    return jsonify({
        'total_vigilantes': total_vigs,
        'plantoes_ativos' : ativos_hoje,
        'plantoes_mes'    : plantoes_mes,
        'ocorrencias_mes' : ocorr_mes,
        'panicos_mes'     : panicos_mes,
    })

# ── CONFIGURAR Z-API ─────────────────────────────
@admin_bp.route('/zapi', methods=['POST'])
@login_required
def config_zapi():
    if not _require_admin():
        return jsonify({'erro': 'Sem permissão'}), 403
    data = request.get_json()
    emp = Empresa.query.get(current_user.empresa_id)
    emp.zapi_instance = data.get('instance', '')
    emp.zapi_token    = data.get('token', '')
    db.session.commit()
    return jsonify({'ok': True})

# ── LISTAR POSTOS ────────────────────────────────
@admin_bp.route('/postos')
@login_required
def listar_postos():
    postos = Posto.query.filter_by(empresa_id=current_user.empresa_id).all()
    return jsonify([{
        'id': p.id, 'nome': p.nome,
        'endereco': p.endereco, 'ativo': p.ativo,
    } for p in postos])

# ── CRIAR/EDITAR POSTO ───────────────────────────
@admin_bp.route('/postos', methods=['POST'])
@login_required
def criar_posto():
    if not _require_admin():
        return jsonify({'erro': 'Sem permissão'}), 403
    data = request.get_json()
    p = Posto(
        empresa_id = current_user.empresa_id,
        nome       = data['nome'],
        endereco   = data.get('endereco', ''),
        descricao  = data.get('descricao', ''),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({'ok': True, 'id': p.id})

# ── ALTERAR SENHA DE USUÁRIO (admin) ─────────────
@admin_bp.route('/reset-senha', methods=['POST'])
@login_required
def reset_senha():
    if not _require_admin():
        return jsonify({'erro': 'Sem permissão'}), 403
    data = request.get_json()
    u = Usuario.query.get(data.get('user_id'))
    if not u or u.empresa_id != current_user.empresa_id:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    u.set_senha(data.get('nova_senha', '123456'))
    db.session.commit()
    return jsonify({'ok': True})

# ── DESATIVAR USUÁRIO ────────────────────────────
@admin_bp.route('/usuarios/<int:uid>/desativar', methods=['POST'])
@login_required
def desativar(uid):
    if not _require_admin():
        return jsonify({'erro': 'Sem permissão'}), 403
    u = Usuario.query.get_or_404(uid)
    if u.empresa_id != current_user.empresa_id:
        return jsonify({'erro': 'Sem permissão'}), 403
    u.ativo = False
    db.session.commit()
    return jsonify({'ok': True})
