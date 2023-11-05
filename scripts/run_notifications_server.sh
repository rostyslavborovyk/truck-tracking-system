#!/usr/bin/env bash

set -ex

uvicorn --host 0.0.0.0 --port 80 --workers 1 --log-level info app.run_notifications_server:app
