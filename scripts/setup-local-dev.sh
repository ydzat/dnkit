#!/bin/bash
# 本地开发环境安装脚本
# 用于在本地开发时安装本地版本的Logloom

set -e

echo "检查是否为本地开发环境..."

# 检查本地Logloom项目是否存在
if [ -d "../Logloom" ]; then
    echo "发现本地Logloom项目，使用本地版本进行开发..."
    
    # 确保Logloom依赖已安装
    echo "安装Logloom的系统依赖..."
    if command -v apt-get >/dev/null 2>&1; then
        # Ubuntu/Debian
        sudo apt-get update
        sudo apt-get install -y build-essential cmake libssl-dev zlib1g-dev
    elif command -v dnf >/dev/null 2>&1; then
        # Fedora
        sudo dnf install -y make gcc cmake openssl-devel zlib-devel
    else
        echo "警告：无法自动安装系统依赖，请手动安装：build-essential cmake libssl-dev zlib1g-dev"
    fi
    
    # 进入Logloom目录并安装
    echo "构建并安装本地Logloom..."
    cd ../Logloom
    
    # 如果有uv，使用uv安装
    if command -v uv >/dev/null 2>&1; then
        echo "使用uv安装Logloom..."
        uv sync
        
        # 将Logloom安装到当前项目的uv环境中
        cd ../dnkit
        uv pip install -e ../Logloom
    else
        echo "警告：未找到uv，请安装uv或手动安装Logloom"
        exit 1
    fi
    
    echo "本地Logloom安装完成！"
else
    echo "未发现本地Logloom项目，将使用远程版本..."
    echo "运行: uv sync 来安装远程依赖"
fi
