#!/data/data/com.termux/files/usr/bin/bash

# Project directory (update this if your project path is different)
PROJECT_DIR="/data/data/com.termux/files/home/codespaces-blank/HMS"

# Port for Django to run on
PORT=5656

# Start a new tmux session in detached mode
tmux new-session -d -s django_session "cd $PROJECT_DIR && python manage.py runserver 127.0.0.1:$PORT"

# Wait for Django to initialize
sleep 5

# Split the tmux window and run ngrok in the new pane
tmux split-window -v -t django_session "ngrok http $PORT"

# Optional: Select the first pane (Django) by default
tmux select-pane -t django_session:.0

# Attach to the session so the user sees both panes
tmux attach-session -t django_session
