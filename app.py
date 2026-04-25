import os
from flask import Flask, jsonify, send_from_directory
from flask_login import LoginManager
from flask_cors import CORS
from dotenv import load_dotenv
from models import db, Usuario

load_dotenv()

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')

    # ── Configurações ──────────────────────────────
    app.config['SECRET_KEY']                  = os.getenv('SECRET_KEY', 'vigilantex-secret-2026')
    app.config['SQLALCHEMY_DATABASE_URI']     = os.getenv('DATABASE_URL', 'sqlite:///vigilantex.db').replace('postgres://', 'postgresql://')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH']          = 16 * 1024 * 1024  # 16MB upload

    # ── Extensões ──────────────────────────────────
    db.init_app(app)
    CORS(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # ── Blueprints ─────────────────────────────────
    from routes.auth      import auth_bp
    from routes.plantao   import plantao_bp
    from routes.panico    import panico_bp
    from routes.relatorio import relatorio_bp
    from routes.admin     import admin_bp

    app.register_blueprint(auth_bp,      url_prefix='/api/auth')
    app.register_blueprint(plantao_bp,   url_prefix='/api/plantao')
    app.register_blueprint(panico_bp,    url_prefix='/api/panico')
    app.register_blueprint(relatorio_bp, url_prefix='/api/relatorio')
    app.register_blueprint(admin_bp,     url_prefix='/api/admin')

    # ── Frontend (SPA) ─────────────────────────────
    @app.route('/')
    @app.route('/<path:path>')
    def index(path=''):
        return send_from_directory('templates', 'index.html')

    # ── Health check ───────────────────────────────
    @app.route('/health')
    def health():
        return jsonify({'status': 'ok', 'sistema': 'VIGILANTEX PRO', 'versao': '2026'})

    # ── Criar tabelas ──────────────────────────────
    with app.app_context():
        db.create_all()
        _criar_admin_padrao()

    return app

def _criar_admin_padrao():
    """Cria empresa e admin padrão se não existir."""
    from models import Empresa, Usuario
    if not Empresa.query.first():
        emp = Empresa(
            nome  = 'SPYNET Tecnologia Forense',
            cnpj  = '64.000.808/0001-51',
            plano = 'empresarial',
        )
        db.session.add(emp)
        db.session.flush()

        admin = Usuario(
            empresa_id = emp.id,
            nome       = 'Administrador',
            email      = 'admin@vigilantex.com',
            role       = 'admin',
            matricula  = '0001',
        )
        admin.set_senha('admin123')
        db.session.add(admin)
        db.session.commit()
        print('✅ Admin padrão criado — email: admin@vigilantex.com / senha: admin123')

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
