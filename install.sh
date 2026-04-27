#!/usr/bin/env bash
# One-shot installer for the Family Notification System.
# Works on Raspberry Pi OS, Debian, Ubuntu, and most systemd-based distros.
#
# Two ways to run:
#
#   1) Curl-pipe (clones the repo for you):
#        curl -fsSL https://raw.githubusercontent.com/vertex-ai-automations/family-notification-system/master/install.sh | bash
#        # or, with options:
#        curl -fsSL https://raw.githubusercontent.com/vertex-ai-automations/family-notification-system/master/install.sh \
#          | TARGET_DIR=/opt/family-notifier PORT=8080 bash
#
#   2) From inside an existing clone:
#        ./install.sh
#        ./install.sh --no-systemd
#        PORT=8080 ./install.sh
#
# Environment overrides:
#   REPO_URL    git URL to clone (default: https://github.com/vertex-ai-automations/family-notification-system.git)
#   BRANCH      branch / tag to check out (default: master)
#   TARGET_DIR  directory to clone into (default: ./family-notification-system)
#   PORT        TCP port for the dashboard (default: 8001)

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/vertex-ai-automations/family-notification-system.git}"
BRANCH="${BRANCH:-master}"
TARGET_DIR="${TARGET_DIR:-$(pwd)/family-notification-system}"
PORT="${PORT:-8001}"
INSTALL_SYSTEMD=1
for arg in "$@"; do
  case "$arg" in
    --no-systemd) INSTALL_SYSTEMD=0 ;;
    -h|--help)
      sed -n '2,22p' "$0"
      exit 0
      ;;
  esac
done

# ── 0. Locate or clone the repo ─────────────────────────────────────────────
# If the script lives inside an actual checkout (app/main.py present beside
# it), use that. Otherwise — typical for `curl … | bash` — clone REPO_URL
# into TARGET_DIR and continue from there.
SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo "")"
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/app/main.py" ] && [ -f "$SCRIPT_DIR/requirements.txt" ]; then
  APP_DIR="$SCRIPT_DIR"
  echo "==> Using existing checkout at $APP_DIR"
else
  if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git not found — install git first (sudo apt install -y git)" >&2
    exit 1
  fi
  if [ -d "$TARGET_DIR/.git" ]; then
    echo "==> Repo already present at $TARGET_DIR — pulling latest"
    git -C "$TARGET_DIR" fetch --tags origin "$BRANCH"
    git -C "$TARGET_DIR" checkout "$BRANCH"
    git -C "$TARGET_DIR" pull --ff-only origin "$BRANCH"
  elif [ -e "$TARGET_DIR" ]; then
    echo "ERROR: $TARGET_DIR exists and is not a git checkout. Move/rename it or set TARGET_DIR=…" >&2
    exit 1
  else
    echo "==> Cloning $REPO_URL → $TARGET_DIR (branch: $BRANCH)"
    git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$TARGET_DIR"
  fi
  APP_DIR="$TARGET_DIR"
fi

APP_USER="$(id -un)"

echo "==> Family Notification System installer"
echo "    repo:  $APP_DIR"
echo "    user:  $APP_USER"
echo "    port:  $PORT"
echo

# ── 1. Python ───────────────────────────────────────────────────────────────
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.11+ first." >&2
  exit 1
fi
PY_VER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
echo "==> Python $PY_VER detected"
case "$PY_VER" in
  3.11|3.12|3.13|3.14) ;;
  *) echo "WARNING: Python 3.11+ recommended; you have $PY_VER. Continuing anyway." ;;
esac

# ── 2. venv + deps ──────────────────────────────────────────────────────────
if [ ! -d "$APP_DIR/venv" ]; then
  echo "==> Creating virtualenv"
  python3 -m venv "$APP_DIR/venv"
fi
echo "==> Installing dependencies"
"$APP_DIR/venv/bin/pip" install --upgrade pip >/dev/null
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# ── 3. .env ─────────────────────────────────────────────────────────────────
if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo "==> Created .env from template — EDIT IT before starting the service:"
  echo "    $APP_DIR/.env"
fi

# ── 4. systemd unit ─────────────────────────────────────────────────────────
if [ "$INSTALL_SYSTEMD" = "1" ]; then
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "==> systemctl not found — skipping systemd setup"
  else
    UNIT_SRC="$APP_DIR/systemd/family-notifier.service"
    UNIT_DST="/etc/systemd/system/family-notifier.service"
    TMP="$(mktemp)"
    sed -e "s|__USER__|$APP_USER|g" \
        -e "s|__APP_DIR__|$APP_DIR|g" \
        -e "s|__PORT__|$PORT|g" \
        "$UNIT_SRC" > "$TMP"

    echo "==> Installing systemd unit at $UNIT_DST (requires sudo)"
    sudo install -m 0644 "$TMP" "$UNIT_DST"
    rm -f "$TMP"
    sudo systemctl daemon-reload
    sudo systemctl enable family-notifier.service
    echo
    echo "    Start it with:   sudo systemctl start family-notifier"
    echo "    Tail logs with:  journalctl -u family-notifier -f"
  fi
fi

echo
echo "==> Done. Dashboard will be available at http://<this-host>:$PORT once started."
echo "    (For local dev: cd $APP_DIR && source venv/bin/activate && uvicorn app.main:app --reload)"
