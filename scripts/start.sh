#!/bin/bash
# J.A.Y. Startup Script

set -e
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   J.A.Y. — Just Assists You v0.1.0  ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}✗ Python 3 not found. Install Python 3.10+${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python: $(python3 --version)${NC}"

# Check .env
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}⚠ backend/.env not found, copying from .env.example${NC}"
    cp backend/.env.example backend/.env
    echo -e "${YELLOW}  Edit backend/.env to configure API keys${NC}"
fi

# Install Python deps if needed
if [ ! -d "backend/.venv" ]; then
    echo -e "${CYAN}Creating virtual environment...${NC}"
    python3 -m venv backend/.venv
fi

echo -e "${CYAN}Activating virtual environment...${NC}"
source backend/.venv/bin/activate

# Install/update deps
echo -e "${CYAN}Installing Python dependencies...${NC}"
pip install -r backend/requirements.txt -q --disable-pip-version-check

# Start backend
echo -e "${GREEN}✓ Starting J.A.Y. backend on http://localhost:8000${NC}"
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..
echo -e "${GREEN}✓ Backend PID: $BACKEND_PID${NC}"

# Wait for backend to start
echo -e "${CYAN}Waiting for backend...${NC}"
for i in {1..20}; do
    if curl -s http://localhost:8000/health &>/dev/null; then
        echo -e "${GREEN}✓ Backend is ready${NC}"
        break
    fi
    sleep 1
done

# Check Node.js
if ! command -v node &>/dev/null; then
    echo -e "${YELLOW}⚠ Node.js not found. Frontend won't start.${NC}"
    echo -e "${YELLOW}  Backend is running at http://localhost:8000${NC}"
    echo -e "${YELLOW}  API docs: http://localhost:8000/docs${NC}"
    wait $BACKEND_PID
    exit 0
fi
echo -e "${GREEN}✓ Node: $(node --version)${NC}"

# Install frontend deps
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${CYAN}Installing frontend dependencies...${NC}"
    cd frontend && npm install -q && cd ..
fi

# Start frontend
echo -e "${GREEN}✓ Starting J.A.Y. frontend on http://localhost:3000${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         J.A.Y. IS ONLINE             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "  Frontend:  ${CYAN}http://localhost:3000${NC}"
echo -e "  Backend:   ${CYAN}http://localhost:8000${NC}"
echo -e "  API Docs:  ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down J.A.Y...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}Goodbye.${NC}"
}
trap cleanup EXIT

wait
