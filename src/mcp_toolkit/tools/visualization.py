"""
可视化工具集

基于 Mermaid 的图表生成工具，支持流程图、时序图、类图等多种图表类型，
以及基础的数据可视化功能。
"""

import json
import time
from typing import Any, Dict, List, Optional

from ..core.interfaces import ToolDefinition
from ..core.types import ConfigDict
from .base import (
    BaseTool,
    ExecutionMetadata,
    ResourceUsage,
    ToolExecutionRequest,
    ToolExecutionResult,
)


class MermaidVisualizationTools(BaseTool):
    """Mermaid 可视化工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.supported_diagrams = {
            "flowchart": "流程图",
            "sequence": "时序图",
            "class": "类图",
            "state": "状态图",
            "entity_relationship": "实体关系图",
            "user_journey": "用户旅程图",
            "gantt": "甘特图",
            "pie": "饼图",
            "gitgraph": "Git 图",
            "mindmap": "思维导图",
            "timeline": "时间线图",
        }

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="generate_diagram",
            description="生成 Mermaid 图表 - 支持流程图、时序图、类图等多种图表类型",
            parameters={
                "type": "object",
                "properties": {
                    "diagram_type": {
                        "type": "string",
                        "enum": list(self.supported_diagrams.keys()),
                        "description": "图表类型",
                    },
                    "title": {
                        "type": "string",
                        "description": "图表标题",
                    },
                    "content": {
                        "type": "string",
                        "description": "图表内容描述或数据（JSON格式或文本描述）",
                    },
                    "theme": {
                        "type": "string",
                        "enum": ["default", "dark", "forest", "neutral"],
                        "default": "default",
                        "description": "图表主题",
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["TD", "TB", "BT", "RL", "LR"],
                        "default": "TD",
                        "description": "图表方向（仅适用于流程图）",
                    },
                    "auto_generate": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否根据内容描述自动生成图表代码",
                    },
                },
                "required": ["diagram_type", "content"],
            },
        )

    def create_tools(self) -> List["BaseTool"]:
        """创建工具实例列表"""
        return [self]

    async def cleanup(self) -> None:
        """清理资源"""
        # 可视化工具不需要特殊的清理操作
        pass

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行图表生成操作"""
        start_time = time.time()
        params = request.parameters

        try:
            diagram_type = params["diagram_type"]
            content = params["content"]
            title = params.get("title", "")
            theme = params.get("theme", "default")
            direction = params.get("direction", "TD")
            auto_generate = params.get("auto_generate", False)

            if auto_generate:
                # 根据内容描述自动生成图表代码
                mermaid_code = await self._auto_generate_diagram(
                    diagram_type, content, title, direction
                )
            else:
                # 使用提供的内容生成图表
                mermaid_code = await self._generate_diagram(
                    diagram_type, content, title, direction
                )

            # 直接返回 Mermaid 代码，让 Agent 能够在聊天界面中渲染
            result = {
                "type": "mermaid",
                "content": mermaid_code,
                "title": title,
                "diagram_type": diagram_type,
                "message": f"成功生成 {self.supported_diagrams[diagram_type]}",
            }

            execution_time = (time.time() - start_time) * 1000

            metadata = ExecutionMetadata(
                execution_time=execution_time,
                memory_used=len(mermaid_code) / 1024,  # KB
                cpu_time=execution_time * 0.1,
                io_operations=1,
            )

            resources = ResourceUsage(
                memory_mb=len(mermaid_code) / 1024 / 1024,  # MB
                cpu_time_ms=execution_time * 0.1,
                io_operations=1,
            )

            return self._create_success_result(result, metadata, resources)

        except Exception as e:
            self._logger.exception("图表生成时发生异常")
            return self._create_error_result(
                "DIAGRAM_GENERATION_ERROR", f"图表生成失败: {str(e)}"
            )

    async def _generate_diagram(
        self, diagram_type: str, content: str, title: str, direction: str
    ) -> str:
        """生成 Mermaid 图表代码"""
        if diagram_type == "flowchart":
            return self._generate_flowchart(content, title, direction)
        elif diagram_type == "sequence":
            return self._generate_sequence_diagram(content, title)
        elif diagram_type == "class":
            return self._generate_class_diagram(content, title)
        elif diagram_type == "state":
            return self._generate_state_diagram(content, title)
        elif diagram_type == "entity_relationship":
            return self._generate_er_diagram(content, title)
        elif diagram_type == "gantt":
            return self._generate_gantt_chart(content, title)
        elif diagram_type == "pie":
            return self._generate_pie_chart(content, title)
        elif diagram_type == "mindmap":
            return self._generate_mindmap(content, title)
        elif diagram_type == "timeline":
            return self._generate_timeline(content, title)
        else:
            raise ValueError(f"不支持的图表类型: {diagram_type}")

    def _generate_flowchart(self, content: str, title: str, direction: str) -> str:
        """生成流程图"""
        lines = [f"flowchart {direction}"]

        if title:
            lines.append(f"    title[{title}]")

        # 尝试解析 JSON 格式的内容
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "nodes" in data:
                # 结构化数据格式
                for node in data.get("nodes", []):
                    node_id = node.get("id", "")
                    node_label = node.get("label", "")
                    node_shape = node.get("shape", "rect")

                    if node_shape == "circle":
                        lines.append(f"    {node_id}(({node_label}))")
                    elif node_shape == "diamond":
                        lines.append(f"    {node_id}{{{node_label}}}")
                    elif node_shape == "rect":
                        lines.append(f"    {node_id}[{node_label}]")

                for edge in data.get("edges", []):
                    from_node = edge.get("from", "")
                    to_node = edge.get("to", "")
                    label = edge.get("label", "")

                    if label:
                        lines.append(f"    {from_node} -->|{label}| {to_node}")
                    else:
                        lines.append(f"    {from_node} --> {to_node}")
            else:
                # 简单的步骤列表
                steps = data if isinstance(data, list) else [data]
                for i, step in enumerate(steps):
                    step_id = f"step{i+1}"
                    lines.append(f"    {step_id}[{step}]")
                    if i > 0:
                        lines.append(f"    step{i} --> {step_id}")
        except json.JSONDecodeError:
            # 文本格式，按行处理
            steps = [line.strip() for line in content.split("\n") if line.strip()]
            for i, step in enumerate(steps):
                step_id = f"step{i+1}"
                lines.append(f"    {step_id}[{step}]")
                if i > 0:
                    lines.append(f"    step{i} --> {step_id}")

        return "\n".join(lines)

    def _generate_sequence_diagram(self, content: str, title: str) -> str:
        """生成时序图"""
        lines = ["sequenceDiagram"]

        if title:
            lines.append(f"    title {title}")

        try:
            data = json.loads(content)
            participants = data.get("participants", [])
            messages = data.get("messages", [])

            # 添加参与者
            for participant in participants:
                lines.append(f"    participant {participant}")

            # 添加消息
            for msg in messages:
                from_p = msg.get("from", "")
                to_p = msg.get("to", "")
                message = msg.get("message", "")
                msg_type = msg.get("type", "->")

                lines.append(f"    {from_p}{msg_type}{to_p}: {message}")

        except json.JSONDecodeError:
            # 简单文本格式
            lines.append("    participant A")
            lines.append("    participant B")
            steps = [line.strip() for line in content.split("\n") if line.strip()]
            for step in steps:
                lines.append(f"    A->>B: {step}")

        return "\n".join(lines)

    def _generate_class_diagram(self, content: str, title: str) -> str:
        """生成类图"""
        lines = ["classDiagram"]

        if title:
            lines.append(f"    title {title}")

        try:
            data = json.loads(content)
            classes = data.get("classes", [])
            relationships = data.get("relationships", [])

            # 添加类定义
            for cls in classes:
                class_name = cls.get("name", "")
                attributes = cls.get("attributes", [])
                methods = cls.get("methods", [])

                lines.append(f"    class {class_name} {{")
                for attr in attributes:
                    lines.append(f"        {attr}")
                for method in methods:
                    lines.append(f"        {method}")
                lines.append("    }")

            # 添加关系
            for rel in relationships:
                from_cls = rel.get("from", "")
                to_cls = rel.get("to", "")
                rel_type = rel.get("type", "-->")

                lines.append(f"    {from_cls} {rel_type} {to_cls}")

        except json.JSONDecodeError:
            # 简单文本格式
            lines.append("    class Example {")
            lines.append("        +String name")
            lines.append("        +int id")
            lines.append("        +getName()")
            lines.append("        +setName(String)")
            lines.append("    }")

        return "\n".join(lines)

    def _generate_state_diagram(self, content: str, title: str) -> str:
        """生成状态图"""
        lines = ["stateDiagram-v2"]

        if title:
            lines.append(f"    title {title}")

        try:
            data = json.loads(content)
            states = data.get("states", [])
            transitions = data.get("transitions", [])

            # 添加状态
            for state in states:
                state_id = state.get("id", "")
                state_label = state.get("label", state_id)
                lines.append(f"    {state_id} : {state_label}")

            # 添加转换
            for trans in transitions:
                from_state = trans.get("from", "")
                to_state = trans.get("to", "")
                trigger = trans.get("trigger", "")

                lines.append(f"    {from_state} --> {to_state} : {trigger}")

        except json.JSONDecodeError:
            # 简单文本格式
            lines.append("    [*] --> State1")
            lines.append("    State1 --> State2")
            lines.append("    State2 --> [*]")

        return "\n".join(lines)

    def _generate_er_diagram(self, content: str, title: str) -> str:
        """生成实体关系图"""
        lines = ["erDiagram"]

        if title:
            lines.append(f"    title {title}")

        try:
            data = json.loads(content)
            entities = data.get("entities", [])
            relationships = data.get("relationships", [])

            # 添加实体
            for entity in entities:
                entity_name = entity.get("name", "")
                attributes = entity.get("attributes", [])

                lines.append(f"    {entity_name} {{")
                for attr in attributes:
                    attr_name = attr.get("name", "")
                    attr_type = attr.get("type", "string")
                    lines.append(f"        {attr_type} {attr_name}")
                lines.append("    }")

            # 添加关系
            for rel in relationships:
                entity1 = rel.get("entity1", "")
                entity2 = rel.get("entity2", "")
                relationship = rel.get("relationship", "||--o{")

                lines.append(f"    {entity1} {relationship} {entity2} : has")

        except json.JSONDecodeError:
            # 简单文本格式
            lines.append("    CUSTOMER {")
            lines.append("        string name")
            lines.append("        string email")
            lines.append("    }")
            lines.append("    ORDER {")
            lines.append("        int id")
            lines.append("        date order_date")
            lines.append("    }")
            lines.append("    CUSTOMER ||--o{ ORDER : places")

        return "\n".join(lines)

    def _generate_gantt_chart(self, content: str, title: str) -> str:
        """生成甘特图"""
        lines = ["gantt"]

        if title:
            lines.append(f"    title {title}")

        lines.append("    dateFormat  YYYY-MM-DD")
        lines.append("    axisFormat  %m/%d")

        try:
            data = json.loads(content)
            sections = data.get("sections", [])

            for section in sections:
                section_name = section.get("name", "")
                tasks = section.get("tasks", [])

                lines.append(f"    section {section_name}")
                for task in tasks:
                    task_name = task.get("name", "")
                    start_date = task.get("start", "")
                    duration = task.get("duration", "1d")
                    status = task.get("status", "")

                    task_line = f"    {task_name} :"
                    if status:
                        task_line += f" {status},"
                    task_line += f" {start_date}, {duration}"
                    lines.append(task_line)

        except json.JSONDecodeError:
            # 简单文本格式
            lines.append("    section 项目阶段")
            lines.append("    需求分析 : done, des1, 2024-01-01, 2024-01-05")
            lines.append("    设计开发 : active, des2, 2024-01-06, 3d")
            lines.append("    测试部署 : des3, after des2, 5d")

        return "\n".join(lines)

    def _generate_pie_chart(self, content: str, title: str) -> str:
        """生成饼图"""
        lines = ["pie"]

        if title:
            lines.append(f"    title {title}")

        try:
            data = json.loads(content)
            if isinstance(data, dict):
                for label, value in data.items():
                    lines.append(f'    "{label}" : {value}')
            elif isinstance(data, list):
                for item in data:
                    label = item.get("label", "")
                    value = item.get("value", 0)
                    lines.append(f'    "{label}" : {value}')

        except json.JSONDecodeError:
            # 简单文本格式，假设是 label:value 格式
            for line in content.split("\n"):
                if ":" in line:
                    label, value = line.split(":", 1)
                    lines.append(f'    "{label.strip()}" : {value.strip()}')

        return "\n".join(lines)

    def _generate_mindmap(self, content: str, title: str) -> str:
        """生成思维导图"""
        lines = ["mindmap"]

        if title:
            lines.append(f"  root(({title}))")
        else:
            lines.append("  root((思维导图))")

        try:
            data = json.loads(content)
            if isinstance(data, dict) and "nodes" in data:
                self._add_mindmap_nodes(lines, data["nodes"], "    ")
            elif isinstance(data, list):
                for item in data:
                    lines.append(f"    {item}")

        except json.JSONDecodeError:
            # 简单文本格式
            for line in content.split("\n"):
                if line.strip():
                    lines.append(f"    {line.strip()}")

        return "\n".join(lines)

    def _add_mindmap_nodes(
        self, lines: List[str], nodes: List[Dict], indent: str
    ) -> None:
        """递归添加思维导图节点"""
        for node in nodes:
            label = node.get("label", "")
            children = node.get("children", [])

            lines.append(f"{indent}{label}")
            if children:
                self._add_mindmap_nodes(lines, children, indent + "  ")

    def _generate_timeline(self, content: str, title: str) -> str:
        """生成时间线图"""
        lines = ["timeline"]

        if title:
            lines.append(f"    title {title}")

        try:
            data = json.loads(content)
            events = data.get("events", [])

            for event in events:
                date = event.get("date", "")
                event_title = event.get("title", "")
                description = event.get("description", "")

                lines.append(f"    {date} : {event_title}")
                if description:
                    lines.append(f"             : {description}")

        except json.JSONDecodeError:
            # 简单文本格式
            for line in content.split("\n"):
                if line.strip():
                    lines.append(f"    {line.strip()}")

        return "\n".join(lines)

    async def _auto_generate_diagram(
        self, diagram_type: str, description: str, title: str, direction: str
    ) -> str:
        """根据描述自动生成图表代码"""
        # 这里可以集成 AI 模型来根据描述生成图表
        # 目前使用简单的模板生成

        if diagram_type == "flowchart":
            return self._auto_generate_flowchart(description, title, direction)
        elif diagram_type == "sequence":
            return self._auto_generate_sequence(description, title)
        else:
            # 对于其他类型，使用基本模板
            return await self._generate_diagram(
                diagram_type, description, title, direction
            )

    def _auto_generate_flowchart(
        self, description: str, title: str, direction: str
    ) -> str:
        """自动生成流程图"""
        lines = [f"flowchart {direction}"]

        if title:
            lines.append(f"    title[{title}]")

        # 智能识别流程步骤
        steps = []

        # 首先尝试按箭头分割（支持 -> 和 → 符号）
        if "->" in description or "→" in description:
            # 按箭头分割流程
            text = description.replace("→", "->")
            parts = [part.strip() for part in text.split("->")]
            steps = [part for part in parts if part]
        else:
            # 按行分割
            for line in description.split("\n"):
                line = line.strip()
                if line:
                    steps.append(line)

        # 生成节点定义
        node_ids = []
        for i, step in enumerate(steps):
            step_id = f"step{i+1}"
            node_ids.append(step_id)

            if "判断" in step or "?" in step or "决策" in step:
                lines.append(f"    {step_id}{{{step}}}")
            elif "开始" in step or "start" in step.lower():
                lines.append(f"    {step_id}(({step}))")
            elif "结束" in step or "end" in step.lower():
                lines.append(f"    {step_id}(({step}))")
            else:
                lines.append(f"    {step_id}[{step}]")

        # 生成连接
        for i in range(len(node_ids) - 1):
            lines.append(f"    {node_ids[i]} --> {node_ids[i+1]}")

        return "\n".join(lines)

    def _auto_generate_sequence(self, description: str, title: str) -> str:
        """自动生成时序图"""
        lines = ["sequenceDiagram"]

        if title:
            lines.append(f"    title {title}")

        # 简单的参与者识别
        participants = set()
        interactions = []

        for line in description.split("\n"):
            line = line.strip()
            if line and "->" in line:
                parts = line.split("->")
                if len(parts) == 2:
                    from_p = parts[0].strip()
                    to_and_msg = parts[1].strip()
                    participants.add(from_p)

                    if ":" in to_and_msg:
                        to_p, message = to_and_msg.split(":", 1)
                        to_p = to_p.strip()
                        message = message.strip()
                    else:
                        to_p = to_and_msg
                        message = "消息"

                    participants.add(to_p)
                    interactions.append((from_p, to_p, message))

        # 如果没有找到交互，创建默认的
        if not interactions:
            participants = {"用户", "系统"}
            interactions = [("用户", "系统", description)]

        # 添加参与者
        for participant in sorted(participants):
            lines.append(f"    participant {participant}")

        # 添加交互
        for from_p, to_p, message in interactions:
            lines.append(f"    {from_p}->>+{to_p}: {message}")

        return "\n".join(lines)

    def _encode_mermaid(self, mermaid_code: str) -> str:
        """编码 Mermaid 代码用于预览 URL"""
        import base64
        import urllib.parse

        try:
            # 将代码编码为 base64
            encoded = base64.b64encode(mermaid_code.encode("utf-8")).decode("ascii")
            # URL 编码
            return urllib.parse.quote(encoded)
        except Exception:
            # 如果编码失败，返回空字符串
            return ""


class DataVisualizationTools(BaseTool):
    """数据可视化工具集"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.supported_charts = {
            "bar": "柱状图",
            "line": "折线图",
            "pie": "饼图",
            "scatter": "散点图",
            "histogram": "直方图",
            "box": "箱线图",
        }

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="create_data_chart",
            description="创建数据图表 - 支持柱状图、折线图、饼图等多种数据可视化图表",
            parameters={
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": list(self.supported_charts.keys()),
                        "description": "图表类型",
                    },
                    "title": {
                        "type": "string",
                        "description": "图表标题",
                    },
                    "data": {
                        "type": "string",
                        "description": "图表数据（JSON格式）",
                    },
                    "x_label": {
                        "type": "string",
                        "default": "X轴",
                        "description": "X轴标签",
                    },
                    "y_label": {
                        "type": "string",
                        "default": "Y轴",
                        "description": "Y轴标签",
                    },
                    "width": {
                        "type": "integer",
                        "default": 800,
                        "description": "图表宽度（像素）",
                    },
                    "height": {
                        "type": "integer",
                        "default": 600,
                        "description": "图表高度（像素）",
                    },
                },
                "required": ["chart_type", "data"],
            },
        )

    def create_tools(self) -> List["BaseTool"]:
        """创建工具实例列表"""
        return [self]

    async def cleanup(self) -> None:
        """清理资源"""
        # 数据可视化工具不需要特殊的清理操作
        pass

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行数据图表创建操作"""
        start_time = time.time()
        params = request.parameters

        try:
            chart_type = params["chart_type"]
            data = params["data"]
            title = params.get("title", "")
            x_label = params.get("x_label", "X轴")
            y_label = params.get("y_label", "Y轴")
            width = params.get("width", 800)
            height = params.get("height", 600)

            # 解析数据
            chart_data = json.loads(data)

            # 生成图表配置
            chart_config = await self._generate_chart_config(
                chart_type, chart_data, title, x_label, y_label, width, height
            )

            # 生成可直接渲染的图表代码
            chart_code = self._generate_chart_code(chart_config)

            result = {
                "type": "chart",
                "content": chart_code,
                "chart_type": chart_type,
                "title": title,
                "data_points": (
                    len(chart_data)
                    if isinstance(chart_data, list)
                    else len(chart_data.get("values", []))
                ),
                "message": f"成功生成 {self.supported_charts[chart_type]}",
            }

            return ToolExecutionResult(success=True, content=result)

        except json.JSONDecodeError as e:
            from .base import ToolError

            return ToolExecutionResult(
                success=False,
                error=ToolError("DATA_FORMAT_ERROR", f"数据格式错误: {str(e)}"),
            )
        except Exception as e:
            from .base import ToolError

            return ToolExecutionResult(
                success=False,
                error=ToolError("CHART_CREATION_ERROR", f"图表创建失败: {str(e)}"),
            )

    async def _generate_chart_config(
        self,
        chart_type: str,
        data: Any,
        title: str,
        x_label: str,
        y_label: str,
        width: int,
        height: int,
    ) -> Dict[str, Any]:
        """生成图表配置"""
        base_config = {
            "type": chart_type,
            "title": title,
            "width": width,
            "height": height,
            "x_label": x_label,
            "y_label": y_label,
        }

        if chart_type == "bar":
            return self._generate_bar_chart_config(data, base_config)
        elif chart_type == "line":
            return self._generate_line_chart_config(data, base_config)
        elif chart_type == "pie":
            return self._generate_pie_chart_config(data, base_config)
        elif chart_type == "scatter":
            return self._generate_scatter_chart_config(data, base_config)
        elif chart_type == "histogram":
            return self._generate_histogram_config(data, base_config)
        elif chart_type == "box":
            return self._generate_box_chart_config(data, base_config)
        else:
            raise ValueError(f"不支持的图表类型: {chart_type}")

    def _generate_bar_chart_config(
        self, data: Any, base_config: Dict
    ) -> Dict[str, Any]:
        """生成柱状图配置"""
        config = base_config.copy()

        if isinstance(data, dict):
            config["categories"] = list(data.keys())
            config["values"] = list(data.values())
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            config["categories"] = [
                item.get("label", f"Item {i+1}") for i, item in enumerate(data)
            ]
            config["values"] = [item.get("value", 0) for item in data]
        else:
            raise ValueError("柱状图数据格式应为字典或包含label/value的对象列表")

        config["chart_specific"] = {
            "bar_width": 0.8,
            "color_scheme": "default",
            "show_values": True,
        }

        return config

    def _generate_line_chart_config(
        self, data: Any, base_config: Dict
    ) -> Dict[str, Any]:
        """生成折线图配置"""
        config = base_config.copy()

        if isinstance(data, dict) and "x" in data and "y" in data:
            config["x_values"] = data["x"]
            config["y_values"] = data["y"]
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            config["x_values"] = [item.get("x", i) for i, item in enumerate(data)]
            config["y_values"] = [item.get("y", 0) for item in data]
        else:
            raise ValueError("折线图数据格式应包含x和y坐标数组")

        config["chart_specific"] = {
            "line_width": 2,
            "marker_size": 4,
            "color": "#1f77b4",
            "show_grid": True,
        }

        return config

    def _generate_pie_chart_config(
        self, data: Any, base_config: Dict
    ) -> Dict[str, Any]:
        """生成饼图配置"""
        config = base_config.copy()

        if isinstance(data, dict):
            config["labels"] = list(data.keys())
            config["values"] = list(data.values())
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            config["labels"] = [
                item.get("label", f"Slice {i+1}") for i, item in enumerate(data)
            ]
            config["values"] = [item.get("value", 0) for item in data]
        else:
            raise ValueError("饼图数据格式应为字典或包含label/value的对象列表")

        config["chart_specific"] = {
            "start_angle": 90,
            "show_percentages": True,
            "explode": None,  # 可以设置为列表来突出显示某些扇形
        }

        return config

    def _generate_scatter_chart_config(
        self, data: Any, base_config: Dict
    ) -> Dict[str, Any]:
        """生成散点图配置"""
        config = base_config.copy()

        if isinstance(data, dict) and "x" in data and "y" in data:
            config["x_values"] = data["x"]
            config["y_values"] = data["y"]
            config["sizes"] = data.get("sizes", [20] * len(data["x"]))
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            config["x_values"] = [item.get("x", 0) for item in data]
            config["y_values"] = [item.get("y", 0) for item in data]
            config["sizes"] = [item.get("size", 20) for item in data]
        else:
            raise ValueError("散点图数据格式应包含x和y坐标数组")

        config["chart_specific"] = {
            "marker_style": "circle",
            "alpha": 0.7,
            "color": "#ff7f0e",
        }

        return config

    def _generate_histogram_config(
        self, data: Any, base_config: Dict
    ) -> Dict[str, Any]:
        """生成直方图配置"""
        config = base_config.copy()

        if isinstance(data, list):
            config["values"] = data
        elif isinstance(data, dict) and "values" in data:
            config["values"] = data["values"]
        else:
            raise ValueError("直方图数据格式应为数值列表")

        config["chart_specific"] = {
            "bins": data.get("bins", 10) if isinstance(data, dict) else 10,
            "color": "#2ca02c",
            "alpha": 0.7,
            "edge_color": "black",
        }

        return config

    def _generate_box_chart_config(
        self, data: Any, base_config: Dict
    ) -> Dict[str, Any]:
        """生成箱线图配置"""
        config = base_config.copy()

        if isinstance(data, list):
            config["datasets"] = [{"label": "数据", "values": data}]
        elif isinstance(data, dict):
            if "datasets" in data:
                config["datasets"] = data["datasets"]
            else:
                config["datasets"] = [
                    {"label": key, "values": values} for key, values in data.items()
                ]
        else:
            raise ValueError("箱线图数据格式应为数值列表或包含多个数据集的字典")

        config["chart_specific"] = {
            "show_outliers": True,
            "box_width": 0.6,
            "whisker_style": "default",
        }

        return config

    def _generate_chart_code(self, config: Dict[str, Any]) -> str:
        """生成可直接渲染的图表代码（Chart.js格式）"""
        chart_type = config["type"]
        title = config.get("title", "")

        if chart_type == "bar":
            return self._generate_bar_chart_code(config)
        elif chart_type == "line":
            return self._generate_line_chart_code(config)
        elif chart_type == "pie":
            return self._generate_pie_chart_code(config)
        elif chart_type == "scatter":
            return self._generate_scatter_chart_code(config)
        elif chart_type in ["histogram", "box"]:
            return self._generate_advanced_chart_code(config)
        else:
            return f"// 不支持的图表类型: {chart_type}"

    def _generate_bar_chart_code(self, config: Dict[str, Any]) -> str:
        """生成柱状图代码"""
        categories = config.get("categories", [])
        values = config.get("values", [])
        title = config.get("title", "")

        chart_config = {
            "type": "bar",
            "data": {
                "labels": categories,
                "datasets": [
                    {
                        "label": title,
                        "data": values,
                        "backgroundColor": "rgba(54, 162, 235, 0.6)",
                        "borderColor": "rgba(54, 162, 235, 1)",
                        "borderWidth": 1,
                    }
                ],
            },
            "options": {
                "responsive": True,
                "plugins": {"title": {"display": True, "text": title}},
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "title": {"display": True, "text": config.get("y_label", "值")},
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": config.get("x_label", "类别"),
                        }
                    },
                },
            },
        }

        return json.dumps(chart_config, indent=2, ensure_ascii=False)

    def _generate_line_chart_code(self, config: Dict[str, Any]) -> str:
        """生成折线图代码"""
        x_values = config.get("x_values", [])
        y_values = config.get("y_values", [])
        title = config.get("title", "")

        # 将 x, y 值组合成 Chart.js 需要的格式
        data_points = [{"x": x, "y": y} for x, y in zip(x_values, y_values)]

        chart_config = {
            "type": "line",
            "data": {
                "datasets": [
                    {
                        "label": title,
                        "data": data_points,
                        "borderColor": "rgba(75, 192, 192, 1)",
                        "backgroundColor": "rgba(75, 192, 192, 0.2)",
                        "tension": 0.1,
                    }
                ]
            },
            "options": {
                "responsive": True,
                "plugins": {"title": {"display": True, "text": title}},
                "scales": {
                    "x": {
                        "type": "linear",
                        "title": {
                            "display": True,
                            "text": config.get("x_label", "X轴"),
                        },
                    },
                    "y": {
                        "title": {"display": True, "text": config.get("y_label", "Y轴")}
                    },
                },
            },
        }

        return json.dumps(chart_config, indent=2, ensure_ascii=False)

    def _generate_pie_chart_code(self, config: Dict[str, Any]) -> str:
        """生成饼图代码"""
        labels = config.get("labels", [])
        values = config.get("values", [])
        title = config.get("title", "")

        chart_config = {
            "type": "pie",
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "data": values,
                        "backgroundColor": [
                            "rgba(255, 99, 132, 0.6)",
                            "rgba(54, 162, 235, 0.6)",
                            "rgba(255, 205, 86, 0.6)",
                            "rgba(75, 192, 192, 0.6)",
                            "rgba(153, 102, 255, 0.6)",
                            "rgba(255, 159, 64, 0.6)",
                        ],
                    }
                ],
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {"display": True, "text": title},
                    "legend": {"position": "right"},
                },
            },
        }

        return json.dumps(chart_config, indent=2, ensure_ascii=False)

    def _generate_scatter_chart_code(self, config: Dict[str, Any]) -> str:
        """生成散点图代码"""
        x_values = config.get("x_values", [])
        y_values = config.get("y_values", [])
        title = config.get("title", "")

        data_points = [{"x": x, "y": y} for x, y in zip(x_values, y_values)]

        chart_config = {
            "type": "scatter",
            "data": {
                "datasets": [
                    {
                        "label": title,
                        "data": data_points,
                        "backgroundColor": "rgba(255, 99, 132, 0.6)",
                    }
                ]
            },
            "options": {
                "responsive": True,
                "plugins": {"title": {"display": True, "text": title}},
                "scales": {
                    "x": {
                        "type": "linear",
                        "title": {
                            "display": True,
                            "text": config.get("x_label", "X轴"),
                        },
                    },
                    "y": {
                        "title": {"display": True, "text": config.get("y_label", "Y轴")}
                    },
                },
            },
        }

        return json.dumps(chart_config, indent=2, ensure_ascii=False)

    def _generate_advanced_chart_code(self, config: Dict[str, Any]) -> str:
        """生成高级图表代码（直方图、箱线图等）"""
        chart_type = config["type"]
        title = config.get("title", "")

        # 对于复杂图表，返回配置说明
        return f"""{{
  "type": "{chart_type}",
  "title": "{title}",
  "note": "此图表类型需要专门的渲染库支持",
  "config": {json.dumps(config, indent=2, ensure_ascii=False)}
}}"""


# 专门的子图生成工具
class SubgraphDiagramTool(BaseTool):
    """生成带子图的 Mermaid 图表工具"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)

    async def cleanup(self) -> None:
        """清理资源"""
        pass

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="generate_subgraph_diagram",
            description="生成带子图的 Mermaid 图表 - 专门用于创建包含多个模块或组件的复杂图表",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "图表标题"},
                    "direction": {
                        "type": "string",
                        "enum": ["TD", "TB", "BT", "RL", "LR"],
                        "default": "TD",
                        "description": "图表方向",
                    },
                    "subgraphs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "子图ID"},
                                "title": {"type": "string", "description": "子图标题"},
                                "nodes": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "子图内的节点列表",
                                },
                            },
                            "required": ["id", "title", "nodes"],
                        },
                        "description": "子图定义列表",
                    },
                    "connections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from": {"type": "string", "description": "起始节点"},
                                "to": {"type": "string", "description": "目标节点"},
                                "label": {
                                    "type": "string",
                                    "description": "连接标签（可选）",
                                },
                            },
                            "required": ["from", "to"],
                        },
                        "description": "节点间的连接定义",
                    },
                },
                "required": ["title", "subgraphs"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行子图生成"""
        try:
            params = request.parameters
            title = params.get("title", "")
            direction = params.get("direction", "TD")
            subgraphs = params.get("subgraphs", [])
            connections = params.get("connections", [])

            # 生成 Mermaid 代码
            lines = [f"flowchart {direction}"]

            if title:
                lines.append(f"    title[{title}]")

            # 生成子图
            for subgraph in subgraphs:
                subgraph_id = subgraph["id"]
                subgraph_title = subgraph["title"]
                nodes = subgraph["nodes"]

                lines.append(f'    subgraph {subgraph_id}["{subgraph_title}"]')

                # 生成子图内的节点
                for i, node in enumerate(nodes):
                    node_id = f"{subgraph_id}_node{i+1}"
                    lines.append(f"        {node_id}[{node}]")

                # 生成子图内的连接（顺序连接）
                for i in range(len(nodes) - 1):
                    from_node = f"{subgraph_id}_node{i+1}"
                    to_node = f"{subgraph_id}_node{i+2}"
                    lines.append(f"        {from_node} --> {to_node}")

                lines.append("    end")

            # 生成子图间的连接
            for conn in connections:
                from_node = conn["from"]
                to_node = conn["to"]
                label = conn.get("label", "")

                if label:
                    lines.append(f"    {from_node} -->|{label}| {to_node}")
                else:
                    lines.append(f"    {from_node} --> {to_node}")

            mermaid_code = "\n".join(lines)

            return ToolExecutionResult(
                success=True,
                content={
                    "type": "mermaid",
                    "content": mermaid_code,
                    "title": title,
                    "diagram_type": "subgraph_flowchart",
                    "message": "成功生成子图流程图",
                },
            )

        except Exception as e:
            from .base import ToolError

            return ToolExecutionResult(
                success=False,
                error=ToolError("SUBGRAPH_GENERATION_ERROR", f"子图生成失败: {str(e)}"),
            )


# 专门的状态机生成工具
class StateMachineDiagramTool(BaseTool):
    """生成状态机 Mermaid 图表工具"""

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)

    async def cleanup(self) -> None:
        """清理资源"""
        pass

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="generate_state_machine",
            description="生成状态机图表 - 专门用于创建自动机、状态转换图等",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "状态机标题"},
                    "states": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "状态ID"},
                                "name": {"type": "string", "description": "状态名称"},
                                "type": {
                                    "type": "string",
                                    "enum": ["start", "end", "normal"],
                                    "default": "normal",
                                    "description": "状态类型",
                                },
                            },
                            "required": ["id", "name"],
                        },
                        "description": "状态列表",
                    },
                    "transitions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from": {"type": "string", "description": "起始状态"},
                                "to": {"type": "string", "description": "目标状态"},
                                "condition": {
                                    "type": "string",
                                    "description": "转换条件",
                                },
                            },
                            "required": ["from", "to", "condition"],
                        },
                        "description": "状态转换列表",
                    },
                },
                "required": ["title", "states", "transitions"],
            },
        )

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行状态机生成"""
        try:
            params = request.parameters
            title = params.get("title", "")
            states = params.get("states", [])
            transitions = params.get("transitions", [])

            # 生成 Mermaid 状态图代码
            lines = ["stateDiagram-v2"]

            if title:
                lines.append(f"    title: {title}")

            # 生成状态定义
            for state in states:
                state_id = state["id"]
                state_name = state["name"]
                state_type = state.get("type", "normal")

                if state_type == "start":
                    lines.append(f"    [*] --> {state_id}")
                elif state_type == "end":
                    lines.append(f"    {state_id} --> [*]")

                if state_name != state_id:
                    lines.append(f"    {state_id} : {state_name}")

            # 生成状态转换
            for transition in transitions:
                from_state = transition["from"]
                to_state = transition["to"]
                condition = transition["condition"]

                lines.append(f"    {from_state} --> {to_state} : {condition}")

            mermaid_code = "\n".join(lines)

            return ToolExecutionResult(
                success=True,
                content={
                    "type": "mermaid",
                    "content": mermaid_code,
                    "title": title,
                    "diagram_type": "state_machine",
                    "message": "成功生成状态机图表",
                },
            )

        except Exception as e:
            from .base import ToolError

            return ToolExecutionResult(
                success=False,
                error=ToolError(
                    "STATE_MACHINE_GENERATION_ERROR", f"状态机生成失败: {str(e)}"
                ),
            )


def create_visualization_tools() -> List[BaseTool]:
    """创建所有可视化工具"""
    tools = []

    # 原有的工具
    mermaid_tools = MermaidVisualizationTools()
    tools.extend(mermaid_tools.create_tools())

    data_viz_tools = DataVisualizationTools()
    tools.extend(data_viz_tools.create_tools())

    # 新的专门工具
    tools.append(SubgraphDiagramTool())
    tools.append(StateMachineDiagramTool())

    return tools
