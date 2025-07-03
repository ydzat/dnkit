# 基础工具配置模板和示例

## 1. 完整配置文件模板

### 1.1 主配置文件 (config/modules/tools.yaml)
```yaml
# MCP工具集基础工具配置
tools:
  # 全局设置
  global:
    # 执行控制
    max_concurrent_executions: 50
    default_timeout_seconds: 30
    max_execution_time_seconds: 3600  # 1小时

    # 缓存设置
    cache:
      enabled: true
      max_size_mb: 256
      default_ttl_seconds: 300  # 5分钟
      cleanup_interval_seconds: 600  # 10分钟

    # 性能监控
    monitoring:
      enabled: true
      metrics_collection_interval: 10
      health_check_interval: 60

    # 错误处理
    error_handling:
      max_retry_attempts: 3
      retry_base_delay: 1.0
      retry_max_delay: 30.0
      log_all_errors: true

  # 分类特定配置
  categories:
    # 文件操作工具
    file_operations:
      enabled: true
      settings:
        # 安全限制
        max_file_size_bytes: 104857600  # 100MB
        max_files_per_operation: 1000

        # 路径控制
        allowed_paths:
          - "/workspace"
          - "/tmp/mcp-toolkit"
          - "/home/${USER}/projects"
          - "./data"

        forbidden_paths:
          - "/etc"
          - "/bin"
          - "/usr/bin"
          - "/sys"
          - "/proc"
          - "/root"

        # 文件类型限制
        allowed_extensions:
          - ".txt"
          - ".md"
          - ".json"
          - ".yaml"
          - ".yml"
          - ".py"
          - ".js"
          - ".ts"
          - ".html"
          - ".css"
          - ".sql"
          - ".sh"
          - ".log"

        forbidden_extensions:
          - ".exe"
          - ".dll"
          - ".so"
          - ".dylib"

        # 备份设置
        backup:
          enabled: true
          backup_directory: "/tmp/mcp-toolkit/backups"
          max_backup_age_days: 7

        # 性能优化
        buffer_size_bytes: 65536  # 64KB
        use_memory_mapping: true

    # 终端操作工具
    terminal:
      enabled: true
      settings:
        # 安全设置
        enable_shell: false
        log_all_commands: true
        sandbox_enabled: true

        # 命令白名单
        allowed_commands:
          - "ls"
          - "cat"
          - "grep"
          - "find"
          - "head"
          - "tail"
          - "wc"
          - "sort"
          - "uniq"
          - "cut"
          - "awk"
          - "sed"
          - "git"
          - "npm"
          - "pip"
          - "python"
          - "node"
          - "docker"
          - "kubectl"

        # 禁止的命令
        forbidden_commands:
          - "rm"
          - "rmdir"
          - "mv"
          - "cp"
          - "chmod"
          - "chown"
          - "sudo"
          - "su"
          - "passwd"
          - "systemctl"
          - "service"

        # 执行限制
        max_execution_time_seconds: 300  # 5分钟
        max_output_size_bytes: 10485760  # 10MB
        kill_on_timeout: true

        # 环境控制
        inherit_environment: false
        default_environment:
          PATH: "/usr/local/bin:/usr/bin:/bin"
          HOME: "/tmp/mcp-toolkit/sandbox"
          TMPDIR: "/tmp/mcp-toolkit/tmp"

        # 工作目录限制
        allowed_working_directories:
          - "/workspace"
          - "/tmp/mcp-toolkit"
          - "/home/${USER}/projects"

    # 网络操作工具
    network:
      enabled: true
      settings:
        # 访问控制
        allowed_domains:
          - "*.github.com"
          - "*.githubusercontent.com"
          - "api.openai.com"
          - "localhost"
          - "127.0.0.1"
          - "::1"

        blocked_domains:
          - "*.ads.com"
          - "*.tracker.com"

        # 请求限制
        max_request_size_bytes: 10485760  # 10MB
        max_response_size_bytes: 52428800  # 50MB
        default_timeout_seconds: 30
        max_redirects: 5

        # 安全设置
        verify_ssl: true
        allow_private_ips: false
        allow_local_files: false

        # 代理设置
        proxy:
          enabled: false
          http_proxy: ""
          https_proxy: ""
          no_proxy: "localhost,127.0.0.1"

        # 用户代理
        user_agent: "MCP-Toolkit/1.0"

    # 代码分析工具
    code_analysis:
      enabled: true
      settings:
        # 支持的语言
        supported_languages:
          - "python"
          - "javascript"
          - "typescript"
          - "java"
          - "cpp"
          - "c"
          - "go"
          - "rust"
          - "php"
          - "ruby"
          - "shell"

        # 分析限制
        max_file_size_bytes: 5242880  # 5MB
        max_files_per_analysis: 100
        analysis_timeout_seconds: 120

        # 外部工具配置
        external_tools:
          pylint:
            enabled: true
            command: "pylint"
            timeout: 60
          eslint:
            enabled: true
            command: "eslint"
            timeout: 60

        # 缓存设置
        cache_analysis_results: true
        cache_ttl_seconds: 1800  # 30分钟

    # 版本控制工具
    version_control:
      enabled: true
      settings:
        # 支持的VCS
        supported_vcs:
          - "git"
          - "svn"

        # Git设置
        git:
          max_log_entries: 1000
          default_remote: "origin"
          safe_commands:
            - "status"
            - "log"
            - "show"
            - "diff"
            - "branch"
            - "tag"
            - "remote"

        # 仓库限制
        max_repository_size_mb: 1000
        scan_timeout_seconds: 60

    # 搜索工具
    search:
      enabled: true
      settings:
        # 搜索限制
        max_search_depth: 10
        max_results_per_search: 10000
        search_timeout_seconds: 60

        # 文件搜索
        file_search:
          max_files_scanned: 100000
          excluded_directories:
            - ".git"
            - ".svn"
            - "node_modules"
            - "__pycache__"
            - ".pytest_cache"
            - "venv"
            - "env"
            - "build"
            - "dist"
            - "target"

        # 内容搜索
        content_search:
          max_file_size_bytes: 10485760  # 10MB
          excluded_file_types:
            - ".jpg"
            - ".png"
            - ".gif"
            - ".pdf"
            - ".zip"
            - ".tar"
            - ".gz"
            - ".exe"
            - ".dll"
          context_lines_max: 10

        # 索引设置
        indexing:
          enabled: false
          index_directory: "/tmp/mcp-toolkit/search_index"
          update_interval_seconds: 3600

  # 具体工具配置
  specific_tools:
    # 文件读取工具
    read_file:
      cache:
        enabled: true
        ttl_seconds: 300
        max_cached_size_bytes: 1048576  # 1MB
      performance:
        buffer_size: 65536
        use_mmap_for_large_files: true
        large_file_threshold: 10485760  # 10MB

    # 文件写入工具
    write_file:
      backup:
        enabled: true
        max_backups: 5
      validation:
        check_disk_space: true
        min_free_space_bytes: 104857600  # 100MB

    # 命令执行工具
    run_command:
      security:
        use_sandbox: true
        restricted_mode: true
      logging:
        log_command: true
        log_output: false  # 避免敏感信息
        log_errors: true

    # HTTP请求工具
    http_request:
      connection:
        pool_connections: 10
        pool_maxsize: 20
        max_retries: 3
      security:
        verify_certificates: true
        follow_redirects: true
        max_redirects: 5

    # Git状态工具
    git_status:
      cache:
        enabled: true
        ttl_seconds: 30  # 短缓存时间
      performance:
        use_porcelain: true
        include_ignored: false

    # 文件搜索工具
    file_search:
      performance:
        use_parallel_search: true
        max_parallel_threads: 4
      cache:
        enabled: true
        ttl_seconds: 60

# 环境特定配置覆盖
environments:
  development:
    tools:
      global:
        cache:
          enabled: false  # 开发时禁用缓存
      categories:
        terminal:
          settings:
            log_all_commands: true

  production:
    tools:
      global:
        max_concurrent_executions: 100
      categories:
        terminal:
          settings:
            log_all_commands: false
            sandbox_enabled: true
        network:
          settings:
            verify_ssl: true
            allow_private_ips: false

  testing:
    tools:
      global:
        default_timeout_seconds: 5
        cache:
          enabled: false
      categories:
        network:
          enabled: false  # 测试时禁用网络
```

### 1.2 安全配置文件 (config/modules/tool_security.yaml)
```yaml
# 工具安全配置
security:
  # 全局安全设置
  global:
    audit_enabled: true
    audit_log_path: "/var/log/mcp-toolkit/security.log"
    fail_safe_mode: true  # 遇到安全问题时默认拒绝

  # 权限管理
  permissions:
    # 基于角色的权限
    roles:
      readonly:
        allowed_categories: ["search", "code_analysis", "version_control"]
        allowed_tools:
          - "read_file"
          - "list_files"
          - "file_search"
          - "content_search"
          - "git_status"
          - "git_log"

      developer:
        allowed_categories: ["file_operations", "terminal", "code_analysis", "version_control", "search"]
        forbidden_tools:
          - "run_command"  # 需要特殊权限
        allowed_tools:
          - "*"  # 其他所有工具

      admin:
        allowed_categories: ["*"]
        allowed_tools: ["*"]

    # 工具特定权限
    tool_permissions:
      read_file:
        required_permissions: ["file:read"]
        path_restrictions: true

      write_file:
        required_permissions: ["file:write"]
        backup_required: true
        size_limit_check: true

      run_command:
        required_permissions: ["system:execute"]
        command_whitelist_required: true
        sandbox_required: true

      http_request:
        required_permissions: ["network:http"]
        domain_whitelist_required: true

  # 访问控制
  access_control:
    # 用户限制
    per_user_limits:
      max_concurrent_requests: 10
      max_requests_per_minute: 100
      max_requests_per_hour: 1000

    # 工具限制
    per_tool_limits:
      file_operations:
        max_requests_per_minute: 50
      terminal:
        max_requests_per_minute: 20
      network:
        max_requests_per_minute: 30

  # 监控和告警
  monitoring:
    alert_thresholds:
      failed_authentications: 5
      permission_denials: 10
      suspicious_commands: 3

    alert_actions:
      - type: "log"
        level: "warning"
      - type: "email"
        recipients: ["admin@example.com"]
      - type: "webhook"
        url: "https://monitoring.example.com/webhook"

  # 沙箱配置
  sandbox:
    enabled: true
    type: "docker"  # docker, chroot, none

    docker_config:
      image: "mcp-toolkit-sandbox:latest"
      memory_limit: "512m"
      cpu_limit: "1.0"
      network_mode: "none"
      readonly_root: true
      tmpfs_mounts:
        - "/tmp:size=100m"
        - "/var/tmp:size=100m"

    resource_limits:
      max_processes: 50
      max_file_descriptors: 1000
      max_memory_mb: 512
      max_cpu_percent: 50
```

## 2. 部署配置示例

### 2.1 Systemd服务配置
```ini
# /etc/systemd/system/mcp-toolkit.service
[Unit]
Description=MCP Toolkit Server
After=network.target
Wants=network.target

[Service]
Type=notify
User=mcp-toolkit
Group=mcp-toolkit
WorkingDirectory=/opt/mcp-toolkit
ExecStart=/opt/mcp-toolkit/bin/mcp-server --config /etc/mcp-toolkit/server.yaml
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5

# 安全设置
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/mcp-toolkit/data /tmp/mcp-toolkit /var/log/mcp-toolkit

# 资源限制
LimitNOFILE=65536
LimitNPROC=4096
MemoryLimit=2G
CPUQuota=200%

# 环境变量
Environment=MCP_CONFIG_DIR=/etc/mcp-toolkit
Environment=MCP_LOG_DIR=/var/log/mcp-toolkit
Environment=MCP_DATA_DIR=/opt/mcp-toolkit/data

[Install]
WantedBy=multi-user.target
```

### 2.2 Docker Compose配置
```yaml
# docker-compose.yml
version: '3.8'

services:
  mcp-toolkit:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    volumes:
      - ./config:/app/config:ro
      - ./data:/app/data
      - ./logs:/app/logs
      - /tmp/mcp-toolkit:/tmp/mcp-toolkit
    environment:
      - MCP_ENV=production
      - MCP_LOG_LEVEL=INFO
      - MCP_CONFIG_DIR=/app/config
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp:size=1G
    ulimits:
      nproc: 4096
      nofile: 65536

  # 可选：Redis缓存
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 256mb
    restart: unless-stopped

  # 可选：Prometheus监控
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

volumes:
  redis_data:
  prometheus_data:
```

## 3. 开发环境配置

### 3.3 开发配置覆盖 (config/environments/development.yaml)
```yaml
# 开发环境特定配置
extends: "../modules/tools.yaml"

# 开发环境覆盖
tools:
  global:
    # 开发时更详细的日志
    debug_mode: true

    # 禁用缓存以便测试
    cache:
      enabled: false

    # 更短的超时时间用于快速反馈
    default_timeout_seconds: 10

  categories:
    # 文件操作更宽松的限制
    file_operations:
      settings:
        allowed_paths:
          - "/workspace"
          - "/tmp"
          - "/home/${USER}"
          - "."
          - ".."

    # 终端允许更多命令
    terminal:
      settings:
        allowed_commands:
          - "*"  # 开发时允许所有命令
        forbidden_commands: []
        log_all_commands: true
        sandbox_enabled: false  # 开发时禁用沙箱

    # 网络允许所有域名
    network:
      settings:
        allowed_domains:
          - "*"
        blocked_domains: []
        verify_ssl: false  # 开发时可能使用自签名证书

# 开发工具集成
development:
  hot_reload: true
  auto_restart: true

  # 测试数据
  test_data_path: "./test_data"

  # 开发服务器设置
  dev_server:
    port: 8080
    host: "localhost"
    debug: true
    auto_reload: true
```

## 4. 性能调优配置

### 4.4 生产环境性能配置 (config/environments/production.yaml)
```yaml
# 生产环境性能优化配置
extends: "../modules/tools.yaml"

tools:
  global:
    # 高并发设置
    max_concurrent_executions: 200

    # 优化的缓存设置
    cache:
      enabled: true
      max_size_mb: 1024  # 1GB
      default_ttl_seconds: 1800  # 30分钟
      cleanup_interval_seconds: 300

    # 性能监控
    monitoring:
      enabled: true
      detailed_metrics: true
      export_prometheus: true

  # 性能优化的工具配置
  specific_tools:
    read_file:
      cache:
        ttl_seconds: 600  # 10分钟
        max_cached_size_bytes: 5242880  # 5MB
      performance:
        use_mmap_for_large_files: true
        concurrent_reads: true

    file_search:
      performance:
        use_parallel_search: true
        max_parallel_threads: 8
        use_filesystem_cache: true

    content_search:
      performance:
        use_indexing: true
        rebuild_index_interval: 3600

# 资源限制
resource_limits:
  memory:
    max_per_tool_mb: 256
    max_total_mb: 4096

  cpu:
    max_per_tool_percent: 25
    max_total_percent: 80

  disk:
    max_temp_space_mb: 1024
    cleanup_interval_seconds: 300
```

这个配置模板提供了：

1. **完整的工具配置结构**
2. **环境特定的配置覆盖**
3. **详细的安全配置**
4. **部署配置示例**
5. **性能调优指导**

这样的配置体系确保了MCP工具集在不同环境下的可靠运行和安全性。
