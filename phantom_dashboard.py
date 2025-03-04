from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet
import json
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rmm.db'
app.config['SECRET_KEY'] = 'your-secret-key'
db = SQLAlchemy(app)

# Encryption setup
ENCRYPTION_KEY = b'your-encryption-key-here'
cipher = Fernet(ENCRYPTION_KEY)

class Client(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    last_seen = db.Column(db.DateTime)
    system_info = db.Column(db.Text)
    commands = db.relationship('Command', backref='client')

class Command(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(50), db.ForeignKey('client.id'))
    command = db.Column(db.Text)
    status = db.Column(db.String(20))
    results = db.Column(db.Text)

@app.route('/api/checkin', methods=['POST'])
def checkin():
    agent_id = request.headers.get('X-Agent-ID')
    encrypted_data = request.data
    
    try:
        # Decrypt data
        decrypted_data = cipher.decrypt(encrypted_data)
        system_info = json.loads(decrypted_data)
        
        # Update client record
        client = Client.query.get(agent_id)
        if not client:
            client = Client(id=agent_id)
            db.session.add(client)
        
        client.system_info = json.dumps(system_info)
        client.last_seen = datetime.utcnow()
        
        # Get pending commands
        pending_commands = Command.query.filter_by(
            client_id=agent_id,
            status='pending'
        ).all()
        
        db.session.commit()
        
        return jsonify([cmd.serialize() for cmd in pending_commands])
    
    except Exception as e:
        return str(e), 400

@app.route('/api/command', methods=['POST'])
def create_command():
    data = request.json
    new_cmd = Command(
        client_id=data['client_id'],
        command=data['command'],
        status='pending'
    )
    db.session.add(new_cmd)
    db.session.commit()
    return jsonify({"message": "Command queued"})

@app.route('/api/updates/check', methods=['GET'])
def check_update():
    agent_id = request.headers.get('X-Agent-ID')
    client = Client.query.get(agent_id)
    
    latest_version = "1.0.1"  # Get from DB
    update_package = {
        "version": latest_version,
        "download_url": "https://your-dashboard.com/updates/agent.exe",
        "checksum": "sha256-hash-of-file"
    }
    
    return cipher.encrypt(json.dumps(update_package))

if __name__ == '__main__':
    db.create_all()
    app.run(ssl_context='adhoc')