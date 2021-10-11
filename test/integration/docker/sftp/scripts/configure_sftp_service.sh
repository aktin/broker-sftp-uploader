#! /bin/bash

if [[ $EUID -ne 0 ]]; then
  echo "script must be run as root" && exit 1
fi

# user sftp must exist
id -u sftpuser >/dev/null

# file sshd_config must exist
[ ! -f /etc/ssh/sshd_config ] && echo "/etc/ssh/sshd_config does not exist" && exit 1

# configure sftp service for user sftpuser with some security restrictions
cat <<EOF >>"/etc/ssh/sshd_config"
Port 22
Match User sftpuser
ForceCommand internal-sftp
PasswordAuthentication yes
ChrootDirectory /var/sftp
PermitTunnel no
AllowAgentForwarding no
AllowTcpForwarding no
X11Forwarding no
EOF
