"""
结果导出服务
将处理结果导出为Markdown格式
"""
from typing import Dict, Any, Optional
import structlog
from datetime import datetime

logger = structlog.get_logger()


class ResultExporter:
    """结果导出器"""
    
    @staticmethod
    def export_to_markdown(
        result_data: Dict[str, Any],
        view: str,
        document_name: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> str:
        """
        将处理结果导出为Markdown格式
        
        Args:
            result_data: 处理结果数据
            view: 视角名称（learning/qa/system）
            document_name: 文档名称（可选）
            document_id: 文档ID（可选）
        
        Returns:
            Markdown格式的字符串
        """
        lines = []
        
        # 标题
        lines.append("# 文档处理结果")
        lines.append("")
        
        # 元信息
        if document_name:
            lines.append(f"**文档名称**: {document_name}")
        if document_id:
            lines.append(f"**文档ID**: {document_id}")
        lines.append(f"**视角**: {ResultExporter._get_view_name(view)}")
        lines.append(f"**导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 根据视角类型导出内容
        if view == "learning":
            lines.extend(ResultExporter._export_learning_view(result_data))
        elif view == "qa":
            lines.extend(ResultExporter._export_qa_view(result_data))
        elif view == "system":
            lines.extend(ResultExporter._export_system_view(result_data))
        else:
            # 未知视角，导出为JSON
            import json
            lines.append("## 处理结果")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(result_data, ensure_ascii=False, indent=2))
            lines.append("```")
        
        return "\n".join(lines)
    
    @staticmethod
    def _get_view_name(view: str) -> str:
        """获取视角的中文名称"""
        view_names = {
            "learning": "学习视角",
            "qa": "问答视角",
            "system": "系统视角"
        }
        return view_names.get(view, view)
    
    @staticmethod
    def _export_learning_view(data: Dict[str, Any]) -> list:
        """导出学习视角"""
        lines = []
        
        # 前置条件
        if "prerequisites" in data:
            lines.append("## 前置条件")
            lines.append("")
            prereq = data["prerequisites"]
            
            if "required" in prereq and prereq["required"]:
                lines.append("### 必需条件")
                for item in prereq["required"]:
                    if isinstance(item, str):
                        lines.append(f"- {item}")
                    elif isinstance(item, dict):
                        lines.append(f"- {item.get('name', item.get('content', str(item)))}")
                lines.append("")
            
            if "recommended" in prereq and prereq["recommended"]:
                lines.append("### 推荐条件")
                for item in prereq["recommended"]:
                    if isinstance(item, str):
                        lines.append(f"- {item}")
                    elif isinstance(item, dict):
                        lines.append(f"- {item.get('name', item.get('content', str(item)))}")
                lines.append("")
            
            if "confidence" in prereq:
                lines.append(f"*可信度: {prereq.get('confidence_label', '未知')} ({prereq.get('confidence', 0)}%)*")
                lines.append("")
        
        # 学习路径
        if "learning_path" in data and data["learning_path"]:
            lines.append("## 学习路径")
            lines.append("")
            for stage in data["learning_path"]:
                if isinstance(stage, dict):
                    stage_num = stage.get("stage", "")
                    title = stage.get("title", "")
                    content = stage.get("content", "")
                    
                    lines.append(f"### 阶段 {stage_num}: {title}")
                    lines.append("")
                    if content:
                        lines.append(content)
                    lines.append("")
                    
                    if "confidence" in stage:
                        lines.append(f"*可信度: {stage.get('confidence_label', '未知')} ({stage.get('confidence', 0)}%)*")
                        lines.append("")
        
        # 学习方法建议
        if "learning_methods" in data:
            lines.append("## 学习方法建议")
            lines.append("")
            methods = data["learning_methods"]
            
            if "theory" in methods:
                lines.append("### 理论学习")
                lines.append("")
                lines.append(methods["theory"])
                lines.append("")
            
            if "practice" in methods:
                lines.append("### 实践建议")
                lines.append("")
                lines.append(methods["practice"])
                lines.append("")
            
            if "confidence" in methods:
                lines.append(f"*可信度: {methods.get('confidence_label', '未知')} ({methods.get('confidence', 0)}%)*")
                lines.append("")
        
        # 相关技术
        if "related_technologies" in data:
            tech = data["related_technologies"]
            if "technologies" in tech and tech["technologies"]:
                lines.append("## 相关技术")
                lines.append("")
                for tech_name in tech["technologies"]:
                    lines.append(f"- {tech_name}")
                lines.append("")
        
        return lines
    
    @staticmethod
    def _export_qa_view(data: Dict[str, Any]) -> list:
        """导出问答视角"""
        lines = []
        
        # 内容总结
        if "summary" in data:
            lines.append("## 内容总结")
            lines.append("")
            summary = data["summary"]
            
            if "key_points" in summary and summary["key_points"]:
                lines.append("### 关键知识点")
                for point in summary["key_points"]:
                    lines.append(f"- {point}")
                lines.append("")
            
            if "question_types" in summary and summary["question_types"]:
                lines.append("### 题型分布")
                for qtype, count in summary["question_types"].items():
                    lines.append(f"- {qtype}: {count} 题")
                lines.append("")
        
        # 生成的问题
        if "generated_questions" in data and data["generated_questions"]:
            lines.append("## 生成的问题")
            lines.append("")
            for i, question in enumerate(data["generated_questions"], 1):
                if isinstance(question, dict):
                    q_text = question.get("question", question.get("content", str(question)))
                    lines.append(f"### 问题 {i}")
                    lines.append("")
                    lines.append(q_text)
                    lines.append("")
                    
                    if "answer" in question:
                        lines.append(f"**答案**: {question['answer']}")
                        lines.append("")
                    
                    if "confidence" in question:
                        lines.append(f"*可信度: {question.get('confidence_label', '未知')} ({question.get('confidence', 0)}%)*")
                        lines.append("")
                elif isinstance(question, str):
                    lines.append(f"### 问题 {i}")
                    lines.append("")
                    lines.append(question)
                    lines.append("")
        
        # 提取的答案
        if "extracted_answers" in data:
            answers = data["extracted_answers"]
            if "answers" in answers and answers["answers"]:
                lines.append("## 提取的答案")
                lines.append("")
                for i, answer in enumerate(answers["answers"], 1):
                    if isinstance(answer, dict):
                        lines.append(f"### 答案 {i}")
                        lines.append("")
                        lines.append(answer.get("content", answer.get("answer", str(answer))))
                        lines.append("")
                    elif isinstance(answer, str):
                        lines.append(f"### 答案 {i}")
                        lines.append("")
                        lines.append(answer)
                        lines.append("")
        
        return lines
    
    @staticmethod
    def _export_system_view(data: Dict[str, Any]) -> list:
        """导出系统视角"""
        lines = []
        
        # 配置流程
        if "config_steps" in data and data["config_steps"]:
            lines.append("## 配置流程")
            lines.append("")
            for i, step in enumerate(data["config_steps"], 1):
                if isinstance(step, dict):
                    step_title = step.get("title", step.get("name", f"步骤 {i}"))
                    step_content = step.get("content", step.get("description", ""))
                    
                    lines.append(f"### {step_title}")
                    lines.append("")
                    if step_content:
                        lines.append(step_content)
                    lines.append("")
                elif isinstance(step, str):
                    lines.append(f"### 步骤 {i}")
                    lines.append("")
                    lines.append(step)
                    lines.append("")
        
        # 组件识别
        if "components" in data and data["components"]:
            lines.append("## 系统组件")
            lines.append("")
            for component in data["components"]:
                if isinstance(component, dict):
                    comp_name = component.get("name", component.get("title", str(component)))
                    comp_desc = component.get("description", component.get("content", ""))
                    
                    lines.append(f"### {comp_name}")
                    if comp_desc:
                        lines.append("")
                        lines.append(comp_desc)
                    lines.append("")
                elif isinstance(component, str):
                    lines.append(f"- {component}")
            lines.append("")
        
        # 架构视图
        if "architecture_view" in data:
            lines.append("## 架构视图")
            lines.append("")
            lines.append(data["architecture_view"])
            lines.append("")
        
        # 白话串讲
        if "plain_explanation" in data:
            lines.append("## 白话解释")
            lines.append("")
            lines.append(data["plain_explanation"])
            lines.append("")
        
        # 检查清单
        if "checklist" in data:
            checklist = data["checklist"]
            if "items" in checklist and checklist["items"]:
                lines.append("## 配置检查清单")
                lines.append("")
                for item in checklist["items"]:
                    if isinstance(item, str):
                        lines.append(f"- [ ] {item}")
                    elif isinstance(item, dict):
                        item_text = item.get("item", item.get("content", str(item)))
                        checked = item.get("checked", False)
                        checkbox = "[x]" if checked else "[ ]"
                        lines.append(f"- {checkbox} {item_text}")
                lines.append("")
        
        # 相关技术栈
        if "related_technologies" in data:
            tech = data["related_technologies"]
            if "technologies" in tech and tech["technologies"]:
                lines.append("## 相关技术栈")
                lines.append("")
                for tech_name in tech["technologies"]:
                    lines.append(f"- {tech_name}")
                lines.append("")
        
        return lines

