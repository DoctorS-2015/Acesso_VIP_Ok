from app import app, db, User
from werkzeug.security import generate_password_hash

# Defina a senha que você quer para o admin
NOVA_SENHA_ADMIN = "Senha123"

with app.app_context():
    # Tenta localizar o usuário admin existente
    admin = User.query.filter_by(username='admin').first()

    if admin:
        print(f"Usuário admin encontrado. Alterando a senha...")
        admin.password_hash = generate_password_hash(NOVA_SENHA_ADMIN)
    else:
        print(f"Usuário admin não encontrado. Criando novo usuário admin...")
        admin = User(
            username='admin',
            password_hash=generate_password_hash(NOVA_SENHA_ADMIN),
            is_admin=1
        )
        db.session.add(admin)

    db.session.commit()
    print(f"Senha do admin agora é: {NOVA_SENHA_ADMIN}")
