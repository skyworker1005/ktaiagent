#!/usr/bin/env bash
# kt_env 통합 가상환경 설치 (Python 3.12)
# requirements.txt

set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

ENV_NAME="kt_env"
REQUIREMENTS="requirements.txt"

eval "$(conda shell.bash hook)"

echo y | conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main 2>/dev/null || true
echo y | conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r 2>/dev/null || true

conda env list | grep -q "^${ENV_NAME} " || conda create -n $ENV_NAME python=3.12 -y

conda activate $ENV_NAME
pip install --upgrade pip setuptools wheel
pip install -r "$REQUIREMENTS"

# MCP 서버(npx) 실행을 위한 Node.js 설치
conda install -c conda-forge nodejs -y

python -m ipykernel install --user --name=$ENV_NAME --display-name="$ENV_NAME (Python 3.12)"

echo "설치 완료. 활성화: conda activate $ENV_NAME"
