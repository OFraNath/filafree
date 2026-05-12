# ====================================================================
# CRÍTICO: O monkey_patch() DEVE SER A PRIMEIRA COISA A SER FEITA.
# Isso resolve o "RuntimeError: Working outside of application context"
# e o aviso do eventlet.
# ====================================================================
try:
    import eventlet
    # CRÍTICO: Faz o patch das bibliotecas padrão para assíncrono
    eventlet.monkey_patch() 
except ImportError:
    print("AVISO CRÍTICO: Eventlet não encontrado. Instale-o com 'pip install eventlet'. O servidor terá o AssertionError ou alta contagem de requests.")
# ====================================================================

import json
import os
import uuid
import re 
import random 
from datetime import datetime, timedelta
# Agora é seguro importar Flask/Werkzeug, pois o patch foi aplicado
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit

# --- [INTEGRAÇÃO DO ANTIGO UTILS.PY] ---
# Configurações de Persistência e Constantes
USERS_FILE = 'users.json'
MESSAGES_FILE = 'messages.json'
DEFAULT_USER_COLOR = '#00FFFF' # Ciano Neon, cor padrão para novos usuários

def load_data(file_path, default_data):
    """Carrega dados do arquivo JSON ou cria um novo se não existir."""
    if not os.path.exists(file_path):
        save_data(file_path, default_data)
        return default_data
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Garante que dados vazios retornem o default
            content = f.read()
            if not content:
                 return default_data
            return json.loads(content)
    except json.JSONDecodeError:
        # Se o JSON estiver corrompido, inicia com o default
        print(f"Erro ao decodificar {file_path}. Iniciando com dados padrão.")
        return default_data

def save_data(file_path, data):
    """Salva dados no arquivo JSON."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
# --- [FIM DA INTEGRAÇÃO] ---

# --- FUNÇÕES DE PARSING DE MENSAGEM ---
URL_REGEX = re.compile(r'(https?:\/\/[^\s]+)')

def is_image_url(url):
    """Verifica se a URL termina com uma extensão de imagem comum."""
    image_extensions = ('.jpeg', '.jpg', '.gif', '.png', '.webp', '.bmp', '.tiff', '.svg')
    return url.lower().endswith(image_extensions)

def parse_message_content(content):
    """
    Processa o conteúdo da mensagem:
    - Transforma links de imagem em tags <img>.
    - Transforma links comuns em tags <a> neon.
    """
    images_html = ''
    cleaned_content = content
    urls = URL_REGEX.findall(content)
    
    for url in urls:
        if is_image_url(url):
            images_html += f'<a href="{url}" target="_blank"><img src="{url}" class="message-image" alt="Imagem do Chat" /></a>'
            cleaned_content = cleaned_content.replace(url, ' ', 1).strip()
        else:
            link_html = f'<a href="{url}" target="_blank" class="message-link">{url}</a>'
            cleaned_content = cleaned_content.replace(url, link_html, 1)

    return {'text': cleaned_content, 'images_html': images_html}

# --- LISTAS DE MENSAGENS TEMÁTICAS (ESPAÇO) ---
MESSAGES_ENTRADA = [
    "se conectou ao intercomunicador.", "emergiu do hiperespaço. Boas-vindas!",
    "está online.", "entrou na frequência.", "acoplou-se à estação.",
    "teve sua transmissão recebida e estabilizada.", "cruzou a barreira cósmica e está aqui.",
    "iniciou o log de bordo.", ", seu planeta natal te saúda!", "entrou na órbita de chat.",
    "entrou para a conversa.", "está ajustando os propulsores. Preparado(a) para a conversa.",
    "ligou o sistema de suporte vital.", "entrou em comunicação de longo alcance.",
    "desembarcou no planeta da discussão.", "fez um pouso suave. Que a Força esteja com você!",
    "interceptou a frequência, transmitindo dados...", "está a bordo.", "entrou na conversa!",
    "encontrou o canal de transmissão.", "passou no teste interestelar e está dentro.",
    "injetou-se no mainframe da conversa.", "recuperou-se de um 'crash' no buraco de minhoca.",
    "finalizou o download de dados e está presente.", "trouxe cookies de meteorito para a viagem!",
    "reiniciou o sistema e aterrissou com sucesso.", "teve o login aprovado por J.A.R.V.I.S.!.",
    "localizou a Terra e se conectou.", ", relaxe e aproveite a viagem!", "acabou de chegar. Seja bem-vindo!"
]

MESSAGES_SAIDA = [
    "desligou o comunicador.", "saltou para outra dimensão.", "desapareceu do radar.",
    "esgotou o combustível e saiu.", "desacoplou-se.", "perdeu a conexão com a base.",
    "está voltando para casa.", "encerrou o log de bordo.", "está seguindo para a escuridão...",
    "deixou a órbita de chat.", "partiu em sua próxima missão.", "desligou os sistemas de navegação.",
    "foi abduzido(a) pela inatividade.", "saiu da atmosfera do chat. Adeus!",
    "decolou do hangar da estação.", ", seu sinal ficou fraco... Tchau!",
    "entrou em modo de hibernação prolongada.", ", seu combustível acabou. Desligando...",
    "navegou para fora do alcance do radar.", ", o portal estelar se fechou.",
    "? o servidor central o(a) ejetou!", "voltou para a gravidade da Terra.",
    ", seu sinal foi perdido no ruído cósmico.", ", seu escudo defletor falhou...",
    "precisa recarregar os capacitores de fluxo.", "caiu em um buraco negro.",
    "desconectou o cabo de rede.", ", a bateria do traje espacial acabou.",
    ", o programa de teletransporte falhou... bye!", "está fora da frequência. Falaremos depois."
]

# --- Configurações de Limites ---
MAX_MESSAGE_LENGTH = 350
FLOOD_CONTROL_COUNT = 3
FLOOD_CONTROL_TIME_SECONDS = 10

# --- Inicialização ---
app = Flask(__name__)
socketio = SocketIO(app, ping_interval=30, ping_timeout=60, transports=['websocket', 'polling'])

secret_key = os.urandom(24).hex()
app.config['SECRET_KEY'] = secret_key
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400 

@app.after_request
def add_header(response):
    if request.method in ['GET', 'HEAD']:
        if request.path.startswith('/static/'): 
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif not request.path.startswith('/socket.io'):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
    return response

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Estruturas em Memória ---
user_sid_map = {} 
sid_user_map = {} 
typing_users = {}  
message_history = {} 

def get_active_online_usernames():
    users_data = load_data(USERS_FILE, {})
    active_user_ids = [uid for uid, sids in user_sid_map.items() if sids]
    online_usernames = []
    for uid in active_user_ids:
        user_info = users_data.get(uid)
        if user_info:
            online_usernames.append(user_info['username'])
    return online_usernames

# --- Classe de Usuário ---
class User(UserMixin):
    def __init__(self, id, username, password_hash, permission='user', color=DEFAULT_USER_COLOR, is_banned=False):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.permission = permission
        self.color = color
        self.is_banned = is_banned

    def get_id(self):
        return self.id

    @staticmethod
    def get(user_id):
        users_data = load_data(USERS_FILE, {})
        data = users_data.get(user_id)
        if data:
            return User(
                id=user_id,
                username=data['username'],
                password_hash=data['password_hash'],
                permission=data.get('permission', 'user'),
                color=data.get('color', DEFAULT_USER_COLOR),
                is_banned=data.get('is_banned', False)
            )
        return None
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# --- Forms ---
class LoginForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class RegistrationForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repetir Senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')])
    submit = SubmitField('Registrar')

class ColorForm(FlaskForm):
    color = StringField('Cor (Hex)', validators=[DataRequired()])
    submit = SubmitField('Salvar Cor')

# --- Rotas Padrão ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        users_data = load_data(USERS_FILE, {})
        user_match, user_id = None, None
        for uid, data in users_data.items():
            if data['username'].lower() == form.username.data.lower():
                user_match, user_id = data, uid
                break
        if user_match and check_password_hash(user_match['password_hash'], form.password.data):
            if user_match.get('is_banned', False):
                flash('Foi mal, mas... você está banido(a)!.', 'danger')
                return render_template('login.html', form=form)
            login_user(User.get(user_id))
            return redirect(url_for('chat'))
        flash('Tem algo errado aí, explorador(a). Revise suas credenciais!', 'danger')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        users_data = load_data(USERS_FILE, {})
        for data in users_data.values():
            if data['username'].lower() == form.username.data.lower():
                flash('Já existe alguém com esse nome...', 'danger')
                return render_template('register.html', form=form)
        new_id = str(uuid.uuid4())
        users_data[new_id] = {
            'username': form.username.data,
            'password_hash': generate_password_hash(form.password.data),
            'permission': 'admin' if not users_data else 'user',
            'color': DEFAULT_USER_COLOR,
            'is_banned': False
        }
        save_data(USERS_FILE, users_data)
        flash('Conta criada! Faça login para viajar!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@app.route('/chat')
@login_required
def chat():
    user = User.get(current_user.id)
    if user.is_banned:
        logout_user()
        flash('O quê você fez...? Você já era!', 'danger')
        return redirect(url_for('login'))

    messages_data = load_data(MESSAGES_FILE, [])
    users_data = load_data(USERS_FILE, {})
    display_messages = []
    
    for msg in messages_data:
        u_info = users_data.get(str(msg['user_id']), {})
        parsed = parse_message_content(msg['content'])
        display_messages.append({
            'id': msg['id'],
            'username': u_info.get('username', '...'),
            'user_id': str(msg['user_id']),
            'content': parsed['text'],
            'images_html': parsed['images_html'],
            'timestamp': msg['timestamp'],
            'can_delete': current_user.permission == 'admin' or str(msg['user_id']) == current_user.id,
            'color': u_info.get('color', DEFAULT_USER_COLOR)
        })
    
    return render_template('chat.html', messages=display_messages, current_user_id=current_user.id, 
                           online_users=get_active_online_usernames(), color_form=ColorForm(),
                           max_message_length=MAX_MESSAGE_LENGTH, current_user_permission=current_user.permission,
                           current_user_color=current_user.color)

@app.route('/set_color', methods=['POST'])
@login_required
def set_user_color():
    data = request.get_json()
    new_color = data.get('color')
    if not re.match(r'^#[0-9a-fA-F]{6}$', new_color):
        return jsonify(success=False), 400
    users_data = load_data(USERS_FILE, {})
    if current_user.id in users_data:
        users_data[current_user.id]['color'] = new_color
        save_data(USERS_FILE, users_data)
        socketio.emit('user_color_updated', {'user_id': current_user.id, 'new_color': new_color})
        return jsonify(success=True), 200
    return jsonify(success=False), 404

@app.route('/clear_messages', methods=['POST'])
@login_required
def clear_all_messages():
    if current_user.permission != 'admin':
        return jsonify(success=False), 403
    data = request.get_json()
    if not current_user.check_password(data.get('password')):
        return jsonify(success=False, message='Senha incorreta.'), 401
    save_data(MESSAGES_FILE, [])
    socketio.emit('clear_chat', {'message': 'O histórico foi apagado pelo admin.'})
    return jsonify(success=True), 200

@app.route('/delete_message/<string:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    messages_data = load_data(MESSAGES_FILE, [])
    msg_to_del = next((msg for msg in messages_data if msg['id'] == message_id), None)
    if not msg_to_del: return jsonify(success=False), 404
    if current_user.permission != 'admin' and str(msg_to_del['user_id']) != current_user.id:
        return jsonify(success=False), 403
    messages_data = [m for m in messages_data if m['id'] != message_id]
    save_data(MESSAGES_FILE, messages_data)
    socketio.emit('delete_message', {'id': message_id})
    return jsonify(success=True), 200

# --- SocketIO Handlers ---
@socketio.on('connect')
@login_required
def handle_connect():
    sid_user_map[request.sid] = current_user.id
    if current_user.id not in user_sid_map: user_sid_map[current_user.id] = set()
    is_first = not user_sid_map[current_user.id]
    user_sid_map[current_user.id].add(request.sid)
    
    if is_first:
        msg = random.choice(MESSAGES_ENTRADA)
        content = f"{current_user.username}{msg}" if msg.startswith(",") else f"{current_user.username} {msg}"
        emit('system_message', {'content': content}, broadcast=True)
    
    emit('update_online_users', {'users': get_active_online_usernames()}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    uid = sid_user_map.pop(request.sid, None)
    if uid and uid in user_sid_map:
        user_sid_map[uid].discard(request.sid)
        if not user_sid_map[uid]:
            del user_sid_map[uid]
            u_data = load_data(USERS_FILE, {}).get(uid, {})
            name = u_data.get('username', '...')
            if name in typing_users: del typing_users[name]
            msg = random.choice(MESSAGES_SAIDA)
            emit('system_message', {'content': f"{name} {msg}"}, broadcast=True)
            emit('update_online_users', {'users': get_active_online_usernames()}, broadcast=True)

@socketio.on('send_message')
@login_required
def handle_send_message(data):
    if User.get(current_user.id).is_banned:
        emit('ban_detected', {'message': 'VOCÊ JÁ ERA...'}, to=request.sid)
        return
    content = data['message'].strip()
    if not content or len(content) > MAX_MESSAGE_LENGTH: return
    
    # Flood Control
    now = datetime.now()
    if current_user.id not in message_history: message_history[current_user.id] = []
    message_history[current_user.id] = [t for t in message_history[current_user.id] if now - t < timedelta(seconds=FLOOD_CONTROL_TIME_SECONDS)]
    if len(message_history[current_user.id]) >= FLOOD_CONTROL_COUNT:
        emit('message_error', {'message': 'Calma aí, viajante! Flood detectado.'})
        return
    message_history[current_user.id].append(now)

    parsed = parse_message_content(content)
    m_id = str(uuid.uuid4())
    m_data = {'id': m_id, 'user_id': current_user.id, 'content': content, 'timestamp': now.strftime('%d/%m/%Y %H:%M:%S')}
    
    db_msgs = load_data(MESSAGES_FILE, [])
    db_msgs.append(m_data)
    save_data(MESSAGES_FILE, db_msgs)
    
    emit('receive_message', {'id': m_id, 'username': current_user.username, 'user_id': current_user.id, 
                             'content': parsed['text'], 'images_html': parsed['images_html'], 
                             'timestamp': m_data['timestamp'], 'color': current_user.color}, broadcast=True)

@socketio.on('typing')
@login_required
def handle_typing_event(data):
    if data['is_typing']:
        typing_users[current_user.username] = datetime.now()
        emit('typing_status', {'username': current_user.username, 'is_typing': True}, broadcast=True, include_self=False)
    elif current_user.username in typing_users:
        del typing_users[current_user.username]
        emit('typing_status', {'username': current_user.username, 'is_typing': False}, broadcast=True)

# --- Registro do Admin Panel ---
try:
    from admin_panel import admin_bp 
    app.register_blueprint(admin_bp) 
except ImportError:
    pass

if __name__ == '__main__':
    print("Iniciando servidor unificado com Eventlet...")
    socketio.run(app, port=8000, debug=False, allow_unsafe_werkzeug=True)
