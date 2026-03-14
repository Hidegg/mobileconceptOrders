#!/usr/bin/env bash
# Run once: sudo bash install-command.sh

cat > /usr/local/bin/gsmDashboard << 'SCRIPT'
#!/usr/bin/env bash
cd /home/billy/Desktop/serviceGSM/dashboard
source venv/bin/activate
python server.py
SCRIPT

chmod +x /usr/local/bin/gsmDashboard
echo "Done — run: gsmDashboard"
