from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from models import db, Usuario, Empresa, Posto

auth_bp = Blueprint('auth', __name__)

# ── LOGIN ────────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email    = data.get('email', '').strip().lower()
    senha    = data.get('senha', '')

    user = Usuario.query.filter_by(email=email, ativo=True).first()
    if not user or not user.check_senha(senha):
        return jsonify({'erro': 'Email ou senha incorretos'}), 401

    login_user(user, remember=True)
    return jsonify({
        'ok': True,
        'usuario': user.to_dict(),
        'empresa': user.empresa.nome,
        'plano': user.empresa.plano,
    })

# ── LOGOUT ───────────────────────────────────────
@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'ok': True})

# ── QUEM SOU ─────────────────────────────────────
@auth_bp.route('/me')
@login_required
def me():
    return jsonify(current_user.to_dict())

# ── LISTAR USUÁRIOS DA EMPRESA ───────────────────
@auth_bp.route('/usuarios')
@login_required
def listar_usuarios():
    if current_user.role not in ('admin', 'gestor', 'supervisor'):
        return jsonify({'erro': 'Sem permissão'}), 403
    users = Usuario.query.filter_by(
        empresa_id=current_user.empresa_id, ativo=True
    ).all()
    return jsonify([{
        'id': u.id, 'nome': u.nome, 'matricula': u.matricula,
        'role': u.role, 'email': u.email, 'telefone': u.telefone,
    } for u in users])

# ── CRIAR USUÁRIO ────────────────────────────────
@auth_bp.route('/usuarios', methods=['POST'])
@login_required
def criar_usuario():
    if current_user.role not in ('admin', 'gestor'):
        return jsonify({'erro': 'Sem permissão'}), 403
    data = request.get_json()
    if Usuario.query.filter_by(email=data.get('email')).first():
        return jsonify({'erro': 'Email já cadastrado'}), 400
    u = Usuario(
        empresa_id = current_user.empresa_id,
        nome       = data['nome'],
        matricula  = data.get('matricula', ''),
        email      = data['email'],
        role       = data.get('role', 'vigilante'),
        telefone   = data.get('telefone', ''),
    )
    u.set_senha(data.get('senha', '123456'))
    db.session.add(u)
    db.session.commit()
    return jsonify({'ok': True, 'id': u.id})

# ── ALTERAR SENHA ────────────────────────────────
@auth_bp.route('/senha', methods=['POST'])
@login_required
def alterar_senha():
    data = request.get_json()
    if not current_user.check_senha(data.get('senha_atual', '')):
        return jsonify({'erro': 'Senha atual incorreta'}), 400
    current_user.set_senha(data['nova_senha'])
    db.session.commit()
    return jsonify({'ok': True})

# ── LISTAR POSTOS DA EMPRESA ─────────────────────
@auth_bp.route('/postos')
@login_required
def listar_postos():
    postos = Posto.query.filter_by(
        empresa_id=current_user.empresa_id, ativo=True
    ).all()
    return jsonify([{'id': p.id, 'nome': p.nome, 'endereco': p.endereco} for p in postos])

# ── CRIAR POSTO ──────────────────────────────────
@auth_bp.route('/postos', methods=['POST'])
@login_required
def criar_posto():
    if current_user.role not in ('admin', 'gestor'):
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
