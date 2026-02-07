#!/bin/bash

PROJECT_DIR="/opt/projects/ChaseTheZones"
VENV="source $PROJECT_DIR/.venv/bin/activate"

# Load environment variables if .env exists
if [ -f "$PROJECT_DIR/.env" ]; then
	# shellcheck disable=SC1090
	source "$PROJECT_DIR/.env"
fi

# Determine a sensible user for running Celery (prefer SUDO_USER when available)
CELERY_UID=${CELERY_UID:-${SUDO_USER:-$(whoami)}}

tmux new-session -d -s devstack -c "$PROJECT_DIR"

# Pane 1 - Django
tmux send-keys -t devstack "$VENV && python manage.py runserver 10.0.0.152:6993" C-m

# Split right → Flower
tmux split-window -h -t devstack -c "$PROJECT_DIR"
tmux send-keys -t devstack "$VENV && python -m celery -A config.celery flower --port=5555" C-m

# Split bottom → Worker
tmux split-window -v -t devstack:0.1 -c "$PROJECT_DIR"
# Run Celery worker with events enabled and set --uid to avoid running as root when possible
tmux send-keys -t devstack "$VENV && python -m celery -A config.celery worker -l debug -P solo -E --uid $CELERY_UID" C-m

# Focus main pane
tmux select-pane -t 0

tmux attach -t devstack
