# 🚀 ChaseTheZones Development Launcher Guide

This project includes a **tmux-based development launcher** that allows
you to run:

-   Django Development Server
-   Celery Worker
-   Flower Monitoring Dashboard

All at the same time in one terminal session, with the ability to switch
between them and restart individual services.

------------------------------------------------------------------------

# 📦 Prerequisites

## Install tmux

``` bash
sudo apt install tmux
```

------------------------------------------------------------------------

## Ensure Virtual Environment Exists

The launcher expects the venv to be located at:

    /opt/projects/ChaseTheZones/.venv

------------------------------------------------------------------------

# ▶️ Running The Development Environment

## Start Everything

``` bash
./dev up
```

This will:

-   Create a tmux session
-   Activate the Python virtual environment
-   Start Django server
-   Start Celery worker
-   Start Flower monitoring dashboard
-   Attach you to the session

------------------------------------------------------------------------

# 🔁 Navigating Between Services

Inside tmux:

    Ctrl + B → Arrow Keys

------------------------------------------------------------------------

# 🌐 Service URLs

  Service   URL
  --------- ------------------------
  Django    http://10.0.0.152:6993
  Flower    http://10.0.0.152:5555

------------------------------------------------------------------------

# ⏸ Leaving The Dev Environment Running

Detach tmux but keep services running:

    Ctrl + B then D

------------------------------------------------------------------------

# 🔗 Reattach Later

``` bash
./dev attach
```

------------------------------------------------------------------------

# 🔄 Restart Individual Services

## Restart Django

``` bash
./dev restart django
```

## Restart Celery Worker

``` bash
./dev restart worker
```

## Restart Flower

``` bash
./dev restart flower
```

------------------------------------------------------------------------

# 📜 View Logs / Jump To Service Pane

## Django

``` bash
./dev logs django
```

## Worker

``` bash
./dev logs worker
```

## Flower

``` bash
./dev logs flower
```

------------------------------------------------------------------------

# 📊 Check Session Status

``` bash
./dev status
```

------------------------------------------------------------------------

# 🛑 Stop Development Environment

This stops all services and kills the tmux session.

``` bash
./dev down
```

------------------------------------------------------------------------

# 🧨 Emergency Kill Options (tmux Manual Controls)

## Kill ALL tmux sessions

``` bash
tmux kill-server
```

------------------------------------------------------------------------

## List Running Sessions

``` bash
tmux ls
```

------------------------------------------------------------------------

## Kill Specific Session

``` bash
tmux kill-session -t ctz-dev
```

------------------------------------------------------------------------

# ✂️ Kill Individual Panes (Inside tmux)

    Ctrl + B then X

------------------------------------------------------------------------

# 🪟 Kill Current Window (Inside tmux)

    Ctrl + B then &

------------------------------------------------------------------------

# 🧠 Tips

-   Closing your terminal does NOT stop tmux sessions.
-   Always use `./dev down` for clean shutdowns.
-   Use `./dev attach` to reconnect to running services.

------------------------------------------------------------------------

# ⚙️ Development Commands Summary

  Command                     Purpose
  --------------------------- ----------------------------
  `./dev up`                  Start full dev environment
  `./dev attach`              Reconnect to session
  `./dev down`                Stop everything
  `./dev restart <service>`   Restart one service
  `./dev logs <service>`      Jump to service pane
  `./dev status`              Show session info

------------------------------------------------------------------------

# 🧪 Troubleshooting

## If tmux session already exists

``` bash
./dev attach
```

------------------------------------------------------------------------

## If services fail to start

Check:

-   Virtual environment exists
-   Redis is running
-   Dependencies installed

------------------------------------------------------------------------

# ❤️ Developer Quality Of Life

Enable mouse support in tmux:

``` bash
nano ~/.tmux.conf
```

Add:

    set -g mouse on

Reload:

``` bash
tmux source-file ~/.tmux.conf
```

------------------------------------------------------------------------

# 🎯 Future Expansion Ideas

-   Add Celery Beat scheduler
-   Add Redis monitoring
-   Add production launcher
-   Add log file streaming
-   Add Docker orchestration
