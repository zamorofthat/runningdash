#!/bin/bash
# Reload dashboard changes by restarting Grafana

echo "Reloading dashboard..."
docker-compose restart
echo "Done. View at: http://localhost:3000/d/running-debug"
