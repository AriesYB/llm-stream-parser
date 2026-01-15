# 贡献指南

感谢你对 `llm-stream-parser` 的关注！我们欢迎任何形式的贡献。

## 🤝 如何贡献

### 报告问题

如果你发现了 bug 或有功能建议，请：

1. 检查 [Issues](https://github.com/yourusername/llm-stream-parser/issues) 确认问题是否已被报告
2. 如果没有，创建一个新的 Issue，包含：
   - 清晰的标题
   - 详细的问题描述
   - 复现步骤（如果是 bug）
   - 预期行为
   - 实际行为
   - 环境信息（Python 版本、操作系统等）

### 提交代码

1. **Fork 本仓库**

   ```bash
   # 在 GitHub 上点击 Fork 按钮
   git clone https://github.com/yourusername/llm-stream-parser.git
   cd llm-stream-parser
   ```

2. **创建特性分支**

   ```bash
   git checkout -b feature/amazing-feature
   # 或
   git checkout -b fix/bug-description
   ```

3. **进行更改**

   - 遵循代码风格规范
   - 添加或更新测试
   - 更新文档（如需要）

4. **提交更改**

   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   # 或
   git commit -m "fix: resolve bug description"
   ```

5. **推送到分支**

   ```bash
   git push origin feature/amazing-feature
   ```

6. **创建 Pull Request**
   - 在 GitHub 上创建 PR
   - 填写 PR 模板
   - 等待代码审查

## 📋 开发规范

### 代码风格

我们使用以下工具来保持代码质量：

- **Black**: 代码格式化
- **Ruff**: Linting
- **MyPy**: 类型检查

在提交代码前，请运行：

```bash
# 格式化代码
black llm_stream_parser tests

# 检查代码
ruff check llm_stream_parser tests

# 类型检查
mypy llm_stream_parser
```

### 测试要求

- 新功能必须包含测试
- 测试覆盖率不低于 80%
- 所有测试必须通过

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_parser.py

# 查看覆盖率
pytest --cov=llm_stream_parser --cov-report=html
```

### 提交信息规范

使用约定式提交（Conventional Commits）格式：

- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档更新
- `test:` 测试相关
- `refactor:` 重构
- `style:` 代码风格（不影响功能）
- `chore:` 构建/工具相关

示例：

```
feat: add support for nested tags
fix: handle incomplete tags correctly
docs: update API documentation
test: add tests for streaming mode
```

## 🏗️ 项目结构

```
llm-stream-parser/
├── llm_stream_parser/      # 核心代码
│   ├── __init__.py
│   ├── models.py           # 数据模型
│   └── parser.py          # 解析器实现
├── tests/                 # 测试代码
│   ├── __init__.py
│   ├── conftest.py        # pytest fixtures
│   ├── test_parser.py     # 单元测试
│   └── test_async.py      # 异步测试
├── examples/              # 示例代码
├── docs/                  # 文档
├── .github/              # GitHub 配置
│   └── workflows/        # CI/CD 工作流
├── pyproject.toml        # 项目配置
├── README.md             # 项目说明
├── LICENSE               # 许可证
└── CONTRIBUTING.md       # 贡献指南
```

## 🧪 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/yourusername/llm-stream-parser.git
cd llm-stream-parser

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest
```

## 📝 文档贡献

如果你发现文档有错误或可以改进：

1. Fork 仓库
2. 修改文档
3. 提交 PR

文档位置：

- `README.md` - 主要文档
- `docs/` - 详细文档

## 🎯 功能开发建议

在开发新功能前，建议：

1. 先创建 Issue 讨论功能设计
2. 等待维护者反馈
3. 开始开发

这样可以避免重复工作和方向偏差。

## 📧 联系方式

如有问题，可以通过以下方式联系：

- GitHub Issues: [提交问题](https://github.com/yourusername/llm-stream-parser/issues)
- Email: your.email@example.com

## 🙏 致谢

感谢所有贡献者！

---

再次感谢你的贡献！
