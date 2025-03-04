import psutil
import requests
import json
import time
import subprocess
import os
import sys
import platform
import hashlib
import urllib.request
from cryptography.fernet import Fernet

class RMMAgent:
    def __init__(self):
        self.config = {
            "server_url": "https://your-dashboard.com/api",
            "agent_id": "UNIQUE_AGENT_ID",
            "check_in_interval": 60,
            "encryption_key": b'your-encryption-key-here'
        }
        
        self.cipher = Fernet(self.config['encryption_key'])

    def encrypt_data(self, data):
        return self.cipher.encrypt(json.dumps(data).encode())

    def get_system_info(self):
        return {
            "os": platform.system(),
            "hostname": platform.node(),
            "cpu_percent": psutil.cpu_percent(),
            "memory": psutil.virtual_memory()._asdict(),
            "disks": [disk._asdict() for disk in psutil.disk_partitions()],
            "network": psutil.net_io_counters()._asdict()
        }

    def check_in(self):
        last_update_check = time.time()
        while True:
            # Regular check-in
            self.send_system_info()
        # Check for updates periodically
            if time.time() - last_update_check > self.config['update_check_interval']:
                self.check_for_updates()
            last_update_check = time.time()
        
            # time.sleep(self.config['check_in_interval'])
            try:
                system_data = self.get_system_info()
                encrypted_data = self.encrypt_data(system_data)
                
                response = requests.post(
                    f"{self.config['server_url']}/checkin",
                    data=encrypted_data,
                    headers={"X-Agent-ID": self.config['agent_id']}
                )

                if response.status_code == 200:
                    commands = self.cipher.decrypt(response.content)
                    self.process_commands(json.loads(commands))

            except Exception as e:
                print(f"Error: {str(e)}")
            
            time.sleep(self.config['check_in_interval'])

    def process_commands(self, commands):
        for cmd in commands:
            if cmd['type'] == 'execute':
                result = subprocess.run(
                    cmd['command'], 
                    shell=True, 
                    capture_output=True
                )
                self.send_result(cmd['id'], result)

    def send_result(self, command_id, result):
        data = {
            "command_id": command_id,
            "output": result.stdout.decode(),
            "error": result.stderr.decode(),
            "return_code": result.returncode
        }
        encrypted_data = self.encrypt_data(data)
        
        requests.post(
            f"{self.config['server_url']}/result",
            data=encrypted_data,
            headers={"X-Agent-ID": self.config['agent_id']}
        )
        def check_for_updates(self):
            try:
                response = requests.get(
                f"{self.config['update_url']}/check",
                headers={"X-Agent-ID": self.config['agent_id']},
                timeout=10
                )
                
                if response.status_code == 200:
                    update_info = json.loads(self.cipher.decrypt(response.content))
                    if self.is_new_version(update_info['version']):
                        self.download_update(update_info)
                        
            except Exception as e:
                self.log_error(f"Update check failed: {str(e)}")

    def is_new_version(self, remote_version):
        current = [int(x) for x in self.config['current_version'].split('.')]
        remote = [int(x) for x in remote_version.split('.')]
        return remote > current

    def download_update(self, update_info):
        try:
            # Download update package
            temp_path = os.path.join(os.environ['TEMP'], 'rmm_update.pkg')
            
            with urllib.request.urlopen(update_info['download_url']) as response:
                with open(temp_path, 'wb') as f:
                    f.write(response.read())

            # Verify checksum
            if self.verify_update(temp_path, update_info['checksum']):
                self.install_update(temp_path)
                
        except Exception as e:
            self.log_error(f"Update failed: {str(e)}")

    def verify_update(self, file_path, expected_checksum):
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest() == expected_checksum

    def install_update(self, update_path):
        # Create update script
        script = f"""
        @echo off
        timeout /t 5 /nobreak
        move /Y "{sys.executable}" "{sys.executable}.old"
        move /Y "{update_path}" "{sys.executable}"
        del "%~f0"
        net start RMMAgent
        """
        
        # Save and execute batch file
        bat_path = os.path.join(os.environ['TEMP'], 'update_agent.bat')
        with open(bat_path, 'w') as f:
            f.write(script)
            
        subprocess.call(
            f'cmd /c "{bat_path}"',
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        sys.exit(0)

if __name__ == "__main__":
    agent = RMMAgent()
    agent.check_in()