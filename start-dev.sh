#!/bin/bash

PROJECT_DIR="/opt/projects/ChaseTheZones"
VENV="source $PROJECT_DIR/.venv/bin/activate"

tmux new-session -d -s devstack -c "$PROJECT_DIR"

# Pane 1 - Django
tmux send-keys -t devstack "$VENV && python manage.py runserver 10.0.0.152:6993" C-m

# Split right → Flower
tmux split-window -h -t devstack -c "$PROJECT_DIR"
tmux send-keys -t devstack "$VENV && python -m celery -A config.celery flower --port=5555" C-m

# Split bottom → Worker
tmux split-window -v -t devstack:0.1 -c "$PROJECT_DIR"
tmux send-keys -t devstack "$VENV && python -m celery -A config.celery worker -l debug -P solo -E" C-m

# Focus main pane
tmux select-pane -t 0

tmux attach -t devstack
