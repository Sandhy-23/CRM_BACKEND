from flask import Blueprint, request, jsonify
from extensions import db, bcrypt, mail
from flask_jwt_extended import create_access_token
from flask_mail import Message
from models.team_user import TeamUser, Permission, UserPermission

team_user_bp = Blueprint('team_user', __name__)

def send_login_email(email, password, web_address):
    """Sends login details to a new user."""
    try:
        msg = Message(
            "Your CRM Login Details",
            sender="yourmail@gmail.com",
            recipients=[email]
        )

        msg.body = f"""
Welcome!

Here are your Login details:

Web Address: {web_address}
Username: {email}
Password: {password}

Thank you for joining!
"""
        mail.send(msg)
        print(f"Login email sent to {email}")
    except Exception as e:
        print(f"Email sending failed for {email}: {e}")

@team_user_bp.route('/add-user', methods=['POST'])
def add_user():
    data = request.json

    name = data['name']
    email = data['email']
    password = data['password']
    role = data['role']
    web_address = data['web_address']
    permissions = data.get('permissions', [])

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = TeamUser(
        name=name,
        email=email,
        password=hashed_password,
        role=role,
        web_address=web_address
    )

    db.session.add(new_user)
    db.session.commit()

    for perm_id in permissions:
        user_perm = UserPermission(
            user_id=new_user.id,
            permission_id=perm_id
        )
        db.session.add(user_perm)

    db.session.commit()
    send_login_email(email, password, web_address)

    return jsonify({"message":"User created successfully"}), 201

@team_user_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data['email']
    password = data['password']

    user = TeamUser.query.filter_by(email=email).first()

    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"message":"Invalid email or password"}), 401

    token = create_access_token(identity=user.id)
    return jsonify({"message":"Login successful", "token":token})

@team_user_bp.route('/user-permissions/<int:user_id>')
def get_permissions(user_id):
    perms = db.session.query(Permission.permission_name)\
        .join(UserPermission, Permission.id == UserPermission.permission_id)\
        .filter(UserPermission.user_id == user_id).all()

    permission_list = [p[0] for p in perms]
    return jsonify(permission_list)