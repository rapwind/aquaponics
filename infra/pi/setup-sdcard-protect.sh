#!/usr/bin/env bash
set -euo pipefail

# SD Card Write Protection Setup for Raspberry Pi
# Run once as root: sudo bash setup-sdcard-protect.sh

echo "=== 1. journald: volatile storage (RAM only) ==="
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/volatile.conf << 'CONF'
[Journal]
Storage=volatile
RuntimeMaxUse=30M
RuntimeMaxFileSize=5M
CONF
systemctl restart systemd-journald

echo "=== 2. fstab: noatime + tmpfs ==="
cp /etc/fstab "/etc/fstab.bak.$(date +%Y%m%d)"

if ! grep -q 'noatime' /etc/fstab; then
    sed -i 's|defaults|defaults,noatime|g' /etc/fstab
    echo "Added noatime to existing mounts"
fi

TMPFS_ENTRIES=(
    "tmpfs /tmp tmpfs defaults,noatime,nosuid,nodev,size=100M 0 0"
    "tmpfs /var/tmp tmpfs defaults,noatime,nosuid,nodev,size=50M 0 0"
    "tmpfs /var/log tmpfs defaults,noatime,nosuid,nodev,size=50M 0 0"
)
for entry in "${TMPFS_ENTRIES[@]}"; do
    mount_point=$(echo "$entry" | awk '{print $2}')
    if ! grep -q "tmpfs $mount_point " /etc/fstab; then
        echo "$entry" >> /etc/fstab
        echo "Added tmpfs for $mount_point"
    fi
done

echo "=== 3. Docker daemon: global log rotation ==="
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'JSON'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "5m",
    "max-file": "3"
  }
}
JSON

echo "=== 4. Disable apt daily timers ==="
systemctl disable --now apt-daily.timer apt-daily-upgrade.timer 2>/dev/null || true

echo "=== 5. Reduce swap and batch writes ==="
cat > /etc/sysctl.d/99-sdcard.conf << 'SYSCTL'
vm.swappiness=1
vm.dirty_writeback_centisecs=6000
SYSCTL
sysctl -p /etc/sysctl.d/99-sdcard.conf

echo ""
echo "=== Done. Reboot required. ==="
echo "After reboot, verify:"
echo "  mount | grep tmpfs"
echo "  journalctl --header | grep Storage"
echo "  cat /etc/docker/daemon.json"
