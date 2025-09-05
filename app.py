from flask import Flask, jsonify
import subprocess
import os
import shutil
import random
import string
import datetime
from jinja2 import Template

app = Flask(__name__)

# Path where your playbooks are stored
PLAYBOOK_DIR = "/home/sanjib/Ansible/Windows_Desktop_Automation/playbooks"

# Jinja2 template for inventory
INVENTORY_TEMPLATE_FILE = os.path.join(PLAYBOOK_DIR, "inventory.yml.j2")


def random_suffix(length=6):
    """Generate random alphanumeric string."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


@app.route("/run-playbook/<playbook_name>/<target_ip>", methods=["POST"])
def run_playbook(playbook_name, target_ip):
    playbook_src_path = os.path.join(PLAYBOOK_DIR, playbook_name)

    # Step 1: Check if playbook exists
    if not os.path.exists(playbook_src_path):
        return jsonify({
            "status": "error",
            "message": f"Playbook {playbook_name} not found in {PLAYBOOK_DIR}"
        }), 404

    try:
        # Step 2: Create temporary folder
        suffix = random_suffix()
        tmp_dir = f"/tmp/{playbook_name}_{suffix}"
        os.makedirs(tmp_dir, exist_ok=True)

        # Step 3: Copy playbook into temp folder
        tmp_playbook_path = os.path.join(tmp_dir, playbook_name)
        shutil.copy(playbook_src_path, tmp_playbook_path)

        # Step 4: Generate inventory.yml from Jinja2 template
        with open(INVENTORY_TEMPLATE_FILE, "r") as f:
            template = Template(f.read())
        inventory_content = template.render(target_ip=target_ip)

        inventory_file_path = os.path.join(tmp_dir, "inventory.yml")
        with open(inventory_file_path, "w") as f:
            f.write(inventory_content)

        # Step 5: Prepare log files
        start_time = datetime.datetime.now()
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        ansible_log_file = os.path.join(tmp_dir, f"ansible_log_{timestamp}.log")
        api_log_file = os.path.join(tmp_dir, f"api_log_{timestamp}.log")

        # Step 6: Run ansible-playbook
        cmd = ["ansible-playbook", "-i", inventory_file_path, tmp_playbook_path]
        with open(ansible_log_file, "w") as logfile:
            result = subprocess.run(cmd, cwd=tmp_dir, stdout=logfile, stderr=subprocess.STDOUT, text=True)

        end_time = datetime.datetime.now()

        # Step 7: Delete playbook and inventory copy 
        if os.path.exists(tmp_playbook_path):
            os.remove(tmp_playbook_path)

        if os.path.exists(inventory_file_path):
            os.remove(inventory_file_path)

        # Step 8: Write API log
        api_log_entry = (
            f"[API LOG]\n"
            f"Playbook: {playbook_name}\n"
            f"Source Path: {playbook_src_path}\n"
            f"Execution Folder: {tmp_dir}\n"
            f"Target IP: {target_ip}\n"
            f"Start Time: {start_time}\n"
            f"End Time: {end_time}\n"
            f"Status: {'SUCCESS' if result.returncode == 0 else 'FAILED'}\n"
            "------------------------------------------------------------\n"
        )
        with open(api_log_file, "a") as api_log:
            api_log.write(api_log_entry)

        # Step 9: Return API response
        return jsonify({
            "status": "success" if result.returncode == 0 else "failed",
            "playbook": playbook_name,
            "target_ip": target_ip,
            "execution_folder": tmp_dir,
            "ansible_log": ansible_log_file,
            "api_log": api_log_file,
            "start_time": str(start_time),
            "end_time": str(end_time)
        }), (200 if result.returncode == 0 else 500)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

