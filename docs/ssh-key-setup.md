# SSH Key Setup — Passwordless SCP from Windows

## Goal
Allow SCP file transfers from your Windows machine to the server
without typing a password every time.

---

## Step 1 — Generate SSH key on Windows (run once)

Open PowerShell and run:

```powershell
ssh-keygen -t rsa -b 4096
```

- Press Enter to accept the default location (`C:\Users\YourName\.ssh\id_rsa`)
- Press Enter twice to skip the passphrase (or set one for extra security)

This creates two files:
- `~\.ssh\id_rsa`       ← private key (keep this secret, never share)
- `~\.ssh\id_rsa.pub`   ← public key (this goes on the server)

---

## Step 2 — View your public key

```powershell
type $env:USERPROFILE\.ssh\id_rsa.pub
```

Copy the entire output — it looks like:
```
ssh-rsa AAAAB3NzaC1yc2EAAA... your-pc-name
```

---

## Step 3 — Add public key to the server

### For root user:
```bash
cat >> /root/.ssh/authorized_keys << 'EOF'
PASTE-YOUR-PUBLIC-KEY-HERE
EOF
```

### For integra user (create .ssh folder first if missing):
```bash
mkdir -p /home/integra/.ssh
chmod 700 /home/integra/.ssh
touch /home/integra/.ssh/authorized_keys
chmod 600 /home/integra/.ssh/authorized_keys
chown -R integra:integra /home/integra/.ssh

cat >> /home/integra/.ssh/authorized_keys << 'EOF'
PASTE-YOUR-PUBLIC-KEY-HERE
EOF
```

> Same public key can be added to as many users as needed.
> The private key stays only on your Windows machine.

---

## Step 4 — Test the connection (no password prompt)

```powershell
ssh root@your-server-ip
```

If it connects without asking for a password — done!

---

## Step 5 — SCP commands (no password needed)

```powershell
# Download machine-data.json from server
scp root@your-server-ip:/var/www/integra-royce/dashboard/data/machine-data.json C:\Downloads\machine-data.json

# Upload a new RoyceData.csv to server
scp C:\path\to\RoyceData.csv root@your-server-ip:/home/integra/RoyceData.csv
```

---

## Troubleshooting

### "Permission denied (publickey)"
- Make sure the public key was pasted correctly (one line, no line breaks)
- Check permissions on the server:
  ```bash
  chmod 700 ~/.ssh
  chmod 600 ~/.ssh/authorized_keys
  ```

### "No such file or directory" for authorized_keys
Run the mkdir/touch/chmod commands from Step 3 first.

### Still being asked for a password
Check that `PubkeyAuthentication yes` is set in `/etc/ssh/sshd_config`:
```bash
grep PubkeyAuthentication /etc/ssh/sshd_config
# If missing or set to no, edit it and restart:
systemctl restart sshd
```
