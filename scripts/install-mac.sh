#!/bin/bash
# Postavi automatski scrape na Macu: 08:15, 12:15, 17:15 i 21:15.
# Ako je Mac ugašen ili spava u tom trenutku, launchd pokrene propušteni termin kad se probudi.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="hr.bruno.sushi-split"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Library/Logs/sushi-split.log"

case "$REPO" in
  "$HOME/Desktop"*|"$HOME/Documents"*|"$HOME/Downloads"*)
    echo "Repo je u $REPO. macOS ne da pozadinskim zadacima pristup Desktopu, Documents ni Downloads."
    echo "Premjesti ga, npr: mv \"$REPO\" ~/sushi-split-gh, pa pokreni ovu skriptu odande."
    exit 1;;
esac

chmod +x "$REPO/scripts/update.sh"
mkdir -p "$HOME/Library/LaunchAgents"

slots=""
for h in 8 12 17 21; do
  slots+="<dict><key>Hour</key><integer>$h</integer><key>Minute</key><integer>15</integer></dict>"
done

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$REPO/scripts/update.sh</string></array>
  <key>StartCalendarInterval</key><array>$slots</array>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
PLISTEOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Instalirano. Termini: 08:15, 12:15, 17:15, 21:15."
echo "Log:            tail -f $LOG"
echo "Pokreni odmah:  launchctl kickstart gui/$(id -u)/$LABEL"
echo "Ukloni:         launchctl bootout gui/$(id -u)/$LABEL && rm $PLIST"
