#!/usr/bin/env bash
# BookSmart — stop everything started by start-booksmart.sh
cd "$(dirname "$0")"

echo "  Stopping BookSmart..."

if [[ -f .booksmart.pids ]]; then
  while read -r pid; do
    kill "$pid" 2>/dev/null && echo "  [✔] stopped process $pid"
  done < .booksmart.pids
  rm -f .booksmart.pids
fi

# belt & suspenders: catch any strays
pkill -f "backend.main" 2>/dev/null && echo "  [✔] app server stopped"
pkill -f llamafile     2>/dev/null && echo "  [✔] llamafile stopped"

echo "  Done — everything stopped. 👋"
