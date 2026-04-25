import os
import requests
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Plantao, Panico, Empresa
from datetime import datetime

panico_bp = Blueprint('panico', __name__)

# ── ACIONAR PÂNICO ───────────────────────────────
@panico_bp.route('/acionar', methods=['POST'])
@login_required
def acionar():
    data = request.get_json()
    plantao = Plantao.query.filter_by(
        vigilante_id=current_user.id, encerrado=False
    ).order_by(Plantao.inicio.desc()).first()

    if not plantao:
        return jsonify({'erro': 'Nenhum plantão ativo'}), 400

    pan = Panico(
        plantao_id    = plantao.id,
        tipo          = data.get('tipo', 'Emergência'),
        vigilante_nome= current_user.nome,
        posto_nome    = plantao.posto_nome,
    )
    db.session.add(pan)
    db.session.commit()

    # Envia WhatsApp para supervisores e gestores
    msg = (
        f"🆘🆘 *ALERTA DE PÂNICO* 🆘🆘\n\n"
        f"*Tipo:* {pan.tipo}\n"
        f"*Vigilante:* {current_user.nome} (Mat. {current_user.matricula or '—'})\n"
        f"*Posto:* {plantao.posto_nome}\n"
        f"*Hora:* {datetime.now().strftime('%H:%M:%S')} — {datetime.now().strftime('%d/%m/%Y')}\n\n"
        f"⚠️ _Acesse o painel VIGILANTEX PRO para confirmar o atendimento._"
    )
    enviado = _enviar_whatsapp(current_user.empresa_id, msg)
    pan.whatsapp_enviado = enviado
    db.session.commit()

    return jsonify({'ok': True, 'panico_id': pan.id, 'whatsapp': enviado})

# ── CANCELAR PÂNICO ──────────────────────────────
@panico_bp.route('/cancelar', methods=['POST'])
@login_required
def cancelar():
    data = request.get_json()
    pan = Panico.query.get(data.get('panico_id'))
    if not pan:
        return jsonify({'erro': 'Pânico não encontrado'}), 404
    pan.cancelado = True
    db.session.commit()

    msg = (
        f"✅ *PÂNICO CANCELADO — FALSO ALARME*\n"
        f"Vigilante: {current_user.nome}\n"
        f"Posto: {pan.posto_nome}\n"
        f"Hora: {datetime.now().strftime('%H:%M:%S')}"
    )
    _enviar_whatsapp(current_user.empresa_id, msg)
    return jsonify({'ok': True})

# ── ATENDER PÂNICO (supervisor) ──────────────────
@panico_bp.route('/atender', methods=['POST'])
@login_required
def atender():
    if current_user.role not in ('supervisor', 'gestor', 'admin'):
        return jsonify({'erro': 'Sem permissão'}), 403
    data = request.get_json()
    pan = Panico.query.get(data.get('panico_id'))
    if not pan:
        return jsonify({'erro': 'Pânico não encontrado'}), 404
    pan.atendido    = True
    pan.atendido_em = datetime.utcnow()
    db.session.commit()

    msg = (
        f"✅ *PÂNICO ATENDIDO*\n"
        f"Supervisor: {current_user.nome}\n"
        f"Vigilante: {pan.vigilante_nome}\n"
        f"Posto: {pan.posto_nome}\n"
        f"Hora: {datetime.now().strftime('%H:%M:%S')}"
    )
    _enviar_whatsapp(current_user.empresa_id, msg)
    return jsonify({'ok': True})

# ── LISTAR PÂNICOS ATIVOS ────────────────────────
@panico_bp.route('/ativos')
@login_required
def ativos():
    if current_user.role not in ('supervisor', 'gestor', 'admin'):
        return jsonify({'erro': 'Sem permissão'}), 403
    panicos = (Panico.query
               .join(Plantao)
               .filter(
                   Plantao.empresa_id == current_user.empresa_id,
                   Panico.atendido == False,
                   Panico.cancelado == False,
               ).all())
    return jsonify([{
        'id'           : p.id,
        'tipo'         : p.tipo,
        'vigilante'    : p.vigilante_nome,
        'posto'        : p.posto_nome,
        'hora'         : p.data_hora.strftime('%H:%M:%S'),
        'data'         : p.data_hora.strftime('%d/%m/%Y'),
        'whatsapp_ok'  : p.whatsapp_enviado,
    } for p in panicos])

# ════════════════════════════════════════════════
# WHATSAPP Z-API
# ════════════════════════════════════════════════

def _enviar_whatsapp(empresa_id, mensagem):
    """
    Envia mensagem WhatsApp via Z-API para todos os supervisores/gestores
    que têm telefone cadastrado.
    """
    try:
        empresa = Empresa.query.get(empresa_id)
        if not empresa or not empresa.zapi_instance or not empresa.zapi_token:
            print('Z-API não configurada para esta empresa')
            return False

        from models import Usuario
        destinatarios = Usuario.query.filter(
            Usuario.empresa_id == empresa_id,
            Usuario.role.in_(['supervisor', 'gestor', 'admin']),
            Usuario.telefone != None,
            Usuario.telefone != '',
            Usuario.ativo == True,
        ).all()

        if not destinatarios:
            print('Nenhum supervisor com telefone cadastrado')
            return False

        url = f"https://api.z-api.io/instances/{empresa.zapi_instance}/token/{empresa.zapi_token}/send-text"
        enviado = False

        for sup in destinatarios:
            telefone = sup.telefone.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
            if not telefone.startswith('55'):
                telefone = '55' + telefone

            payload = {'phone': telefone, 'message': mensagem}
            r = requests.post(url, json=payload, timeout=10)
            if r.status_code == 200:
                enviado = True
                print(f'WhatsApp enviado para {sup.nome} ({telefone})')
            else:
                print(f'Erro WhatsApp para {sup.nome}: {r.text}')

        return enviado

    except Exception as e:
        print(f'Erro ao enviar WhatsApp: {e}')
        return False
