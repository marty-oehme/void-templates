If you previously installed PIA with the official .run installer, run the old
uninstaller as root BEFORE installing this package:

    /opt/piavpn/bin/pia-uninstall.sh

otherwise the old /usr/local/bin/piactl symlink, service files and desktop
entry will linger next to the packaged ones.

The 'piavpn' service is installed but not enabled. To use it:

    sv up piavpn                       # start now
    ln -s /etc/sv/piavpn /var/service/ # start at boot

Settings live in /opt/piavpn/etc, cached data in /opt/piavpn/var.
piactl is symlinked to /usr/bin/piactl.

Notes:
- The wgpia.conf drop-in makes NetworkManager ignore the wgpia* tunnel
  interfaces. Delete /etc/NetworkManager/conf.d/wgpia.conf if unwanted.
- OpenVPN mode switches DNS via resolvconf (openresolv) or systemd-resolved;
  install openresolv if DNS does not follow the tunnel.
- A terminal emulator (xterm, ...) is needed for run-in-terminal.sh.
