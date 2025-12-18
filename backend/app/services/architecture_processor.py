"""
架构/搭建文档处理服务
- 配置流程提取
- 组件识别
- 全景视图生成
- 白话串讲
- 配置检查清单
"""
from typing import Dict, List
import structlog
from app.utils.tech_name_utils import clean_tech_name, normalize_tech_name, are_tech_names_equivalent

from app.services.ai_service import get_ai_service
from app.services.source_segmenter import SourceSegmenter
from app.services.confidence_calculator import ConfidenceCalculator

logger = structlog.get_logger()


class ArchitectureProcessor:
    """架构文档处理器"""
    
    @staticmethod
    async def process(content: str, progress_callback=None) -> Dict:
        """
        处理架构/搭建文档
        
        Args:
            content: 文档内容
            progress_callback: 进度回调函数 (task_id, progress, stage)
        
        Returns:
            处理结果字典
        """
        logger.info("开始处理架构文档", content_length=len(content))
        
        # 0. 段落切分（带异常处理）
        try:
            segments = SourceSegmenter.segment_content(content, timeout=5.0)
            logger.info("段落切分完成", segments_count=len(segments), content_length=len(content))
            # 如果段落切分返回空列表，使用兜底策略
            if not segments:
                logger.warning("段落切分返回空列表，使用兜底策略")
                segments = SourceSegmenter._fallback_segment(content)
                logger.info("兜底策略完成", segments_count=len(segments))
        except Exception as e:
            logger.error("段落切分失败，使用兜底策略", error=str(e))
            segments = SourceSegmenter._fallback_segment(content)  # 使用兜底策略而不是空列表
        
        # 1. 配置流程提取（带异常处理）
        if progress_callback:
            await progress_callback(65, "处理架构文档（步骤1/5：提取配置流程）...")
        try:
            config_steps = await ArchitectureProcessor._extract_config_steps(content, segments)
        except Exception as e:
            logger.error("配置流程提取失败，使用默认值", error=str(e))
            config_steps = []
        
        # 2. 组件识别（带异常处理）
        if progress_callback:
            await progress_callback(70, "处理架构文档（步骤2/5：识别组件）...")
        try:
            components = await ArchitectureProcessor._identify_components(content, segments)
        except Exception as e:
            logger.error("组件识别失败，使用默认值", error=str(e))
            components = []
        
        # 3. 全景视图生成（带异常处理）
        if progress_callback:
            await progress_callback(75, "处理架构文档（步骤3/5：生成架构视图）...")
        try:
            architecture_view = await ArchitectureProcessor._generate_architecture_view(content, segments, components)
        except Exception as e:
            logger.error("全景视图生成失败，使用默认值", error=str(e))
            architecture_view = "系统架构视图生成失败，请查看原始文档。"
        
        # 4. 白话串讲（带异常处理）
        if progress_callback:
            await progress_callback(80, "处理架构文档（步骤4/5：生成白话解释）...")
        try:
            plain_explanation = await ArchitectureProcessor._generate_plain_explanation(content, segments)
        except Exception as e:
            logger.error("白话串讲生成失败，使用默认值", error=str(e))
            plain_explanation = "白话解释生成失败，请查看原始文档。"
        
        # 5. 配置检查清单（带异常处理）
        if progress_callback:
            await progress_callback(85, "处理架构文档（步骤5/5：生成检查清单）...")
        try:
            checklist = await ArchitectureProcessor._generate_checklist(content, segments, config_steps)
        except Exception as e:
            logger.error("检查清单生成失败，使用默认值", error=str(e))
            checklist = {
                "items": [],
                "confidence": None,
                "confidence_label": None,
                "sources": []
            }
        
        # 6. 提取相关技术栈（带异常处理）
        if progress_callback:
            await progress_callback(88, "处理架构文档（提取技术栈）...")
        try:
            related_technologies = await ArchitectureProcessor._extract_related_technologies(content, segments, components)
        except Exception as e:
            logger.error("技术栈提取失败，使用默认值", error=str(e))
            related_technologies = {
                "technologies": [],
                "confidence": None,
                "confidence_label": None,
                "sources": []
            }
        
        result = {
            "config_steps": config_steps,
            "components": components,
            "architecture_view": architecture_view,
            "plain_explanation": plain_explanation,
            "checklist": checklist,
            "related_technologies": related_technologies
        }
        
        logger.info("架构文档处理完成", 
                   steps=len(config_steps),
                   components=len(components),
                   technologies=len(related_technologies))
        
        return result
    
    @staticmethod
    async def _extract_config_steps(content: str, segments: List[Dict]) -> List[Dict]:
        """提取配置流程"""
        ai_service = get_ai_service()
        
        # 使用完整内容，不进行截断
        # 如果内容太长（超过20000字符），使用前15000字符 + 后5000字符（确保包含开头和结尾）
        if len(content) > 20000:
            content_preview = content[:15000] + "\n\n... [中间内容已省略] ...\n\n" + content[-5000:]
        else:
            content_preview = content
        
        prompt = f"""请从以下架构/搭建文档中提取**所有实际的配置步骤**。

文档内容：
{content_preview}

**重要要求：**
1. **必须提取或生成所有实际的配置步骤**，包括：
   - 依赖引入（Maven/Gradle依赖配置）
   - 配置文件设置（application.yml/properties）
   - 代码示例和注解使用
   - 启动和测试步骤
   - 如果文档提到多种方法，必须为每种方法提取相应步骤
   
2. **如果文档中没有详细的配置步骤，请基于文档中描述的架构和方法，生成合理的配置步骤**：
   - 根据文档提到的技术栈（如RocketMQ-Spring-Boot-Starter、Spring Cloud Stream等），生成标准的配置步骤
   - 使用这些技术的常见配置方式
   - 确保步骤是实际可操作的

2. **每个步骤必须包含**：
   - step：步骤序号（从1开始）
   - title：清晰的步骤标题（如"引入RocketMQ-Spring-Boot-Starter依赖"）
   - description：详细的配置说明，包括：
     * 具体的代码示例
     * 配置文件内容
     * 关键参数说明
     * 注意事项

3. **步骤要求**：
   - 必须按照实际操作顺序排列
   - 每个步骤都应该是可执行的、具体的操作
   - 不要只提取概念性描述或背景介绍
   - 如果文档提到多种集成方法（如RocketMQ-Spring-Boot-Starter、Spring Cloud Stream、Spring Cloud Bus），必须为每种方法提取完整的配置步骤

4. **完整性要求（非常重要）**：
   - **如果文档提到了3种方法，必须提取至少15-20个步骤（每种方法5-7个步骤）**
   - **如果文档提到了2种方法，必须提取至少10-12个步骤（每种方法5-6个步骤）**
   - **如果文档提到了1种方法，必须提取至少5-7个步骤**
   - 不要遗漏任何重要的配置环节
   - 确保步骤覆盖从依赖引入到实际使用的完整流程
   - **不要只提取背景介绍或概念性描述，必须提取可操作的配置步骤**

请以JSON格式返回，格式如下：
```json
[
    {{
        "step": 1,
        "title": "引入RocketMQ-Spring-Boot-Starter依赖",
        "description": "在pom.xml中添加以下依赖：\\n<dependency>\\n    <groupId>org.apache.rocketmq</groupId>\\n    <artifactId>rocketmq-spring-boot-starter</artifactId>\\n    <version>2.2.3</version>\\n</dependency>"
    }},
    {{
        "step": 2,
        "title": "配置RocketMQ NameServer地址",
        "description": "在application.yml中配置：\\nrocketmq:\\n  name-server: 127.0.0.1:9876\\n  producer:\\n    group: my-producer-group"
    }},
    ...
]
```

**注意**：只返回JSON数组，不要包含其他文字说明。确保提取的步骤是完整的、可操作的配置流程。"""
        
        system_prompt = "你是一个系统架构专家，擅长从文档中提取完整、可操作的配置流程。必须提取所有实际的配置步骤，不要遗漏任何方法或环节。"
        
        try:
            # 第一次尝试（弱展示：不强制要求source_ids和confidence）
            steps = await ai_service.generate_with_sources(
                prompt=prompt,
                segments=segments,
                system_prompt=system_prompt,
                temperature=0.3,
                require_confidence=False  # 弱展示，不强制要求
            )
            
            # 确保返回列表格式
            if isinstance(steps, dict):
                steps = [steps]
            elif not isinstance(steps, list):
                steps = []
            
            # 验证和格式化，添加可信度和来源（弱展示）
            validated_steps = []
            for step in steps[:30]:  # 最多30个步骤
                if isinstance(step, dict):
                    title = step.get("title", "").strip()
                    description = step.get("description", "").strip()
                    # 过滤掉背景介绍类步骤（但保留中文关键词检查）
                    title_lower = title.lower()
                    # 扩展过滤关键词，包括"选择"、"回顾"等非配置操作
                    filter_keywords = ["回顾", "背景", "介绍", "概述", "了解", "发展历程", "历史", "起源", "选择", "对比", "比较"]
                    if title and description and not any(keyword in title_lower for keyword in filter_keywords):
                        step_item = {
                            "step": len(validated_steps) + 1,  # 重新编号
                            "title": title,
                            "description": description
                        }
                        
                        # 弱展示：如果AI返回了可信度和来源，则添加
                        if "confidence" in step or "source_ids" in step:
                            base_confidence = ConfidenceCalculator.normalize_confidence(
                                step.get("confidence")
                            )
                            source_ids = step.get("source_ids", [])
                            
                            confidence_result = ConfidenceCalculator.calculate_confidence(
                                base_confidence=base_confidence,
                                source_ids=source_ids,
                                segments=segments,
                                content=content,
                                ai_response=str(step)
                            )
                            
                            step_item["confidence"] = confidence_result["score"]
                            step_item["confidence_label"] = confidence_result["label"]
                            
                            # 添加来源片段（弱展示，截断显示）
                            if source_ids:
                                source_segments = SourceSegmenter.get_segments_by_ids(segments, source_ids)
                                step_item["sources"] = [
                                    {
                                        "id": seg["id"],
                                        "text": seg["text"][:200] + "..." if len(seg["text"]) > 200 else seg["text"],
                                        "position": seg["position"]
                                    }
                                    for seg in source_segments
                                ]
                            else:
                                step_item["sources"] = []
                        
                        validated_steps.append(step_item)
            
            # 如果步骤太少（少于5个），尝试第二次提取
            logger.info("配置步骤验证完成", 
                       validated_count=len(validated_steps),
                       raw_count=len(steps) if isinstance(steps, list) else 0,
                       will_retry=len(validated_steps) < 5)
            
            if len(validated_steps) < 5:
                logger.warning("配置步骤提取不足，尝试二次提取", 
                             total_steps=len(validated_steps),
                             raw_steps_count=len(steps) if isinstance(steps, list) else 0)
                
                # 二次提取：使用完整内容和更明确的提示，要求生成配置步骤
                if len(content) > 20000:
                    retry_content = content[:15000] + "\n\n... [中间内容已省略] ...\n\n" + content[-5000:]
                else:
                    retry_content = content
                
                retry_prompt = f"""请从以下架构/搭建文档中提取或生成**所有实际的配置步骤**。**必须返回至少10个步骤**。

文档内容：
{retry_content}

**严格要求：**
1. **必须返回至少10个实际配置步骤**，包括依赖引入、配置文件、代码示例等
2. **如果文档中没有详细步骤，请基于文档描述的架构和方法生成标准配置步骤**：
   - 如果文档提到RocketMQ-Spring-Boot-Starter，生成：引入依赖、配置NameServer、创建生产者、创建消费者等步骤
   - 如果文档提到Spring Cloud Stream，生成：引入依赖、配置Binder、定义Input/Output通道、编写消息处理代码等步骤
   - 如果文档提到Spring Cloud Bus，生成：引入依赖、配置Bus、使用@RefreshScope等步骤
3. **不要提取背景介绍、概念说明等非配置步骤**
4. **每个步骤必须包含具体的操作，如：**
   - 在pom.xml中添加依赖（包含完整的groupId、artifactId、version）
   - 在application.yml中配置参数（包含完整的配置示例）
   - 创建Java类并添加注解（包含代码示例）
   - 编写测试代码
   - 启动和验证

请返回JSON数组，格式：
```json
[
    {{"step": 1, "title": "具体操作标题", "description": "详细操作说明和代码示例"}},
    ...
]
```

**必须返回至少10个步骤，不要只返回1-2个步骤。**"""
                
                try:
                    retry_steps = await ai_service.generate_with_sources(
                        prompt=retry_prompt,
                        segments=segments,
                        system_prompt="你是一个系统架构专家，必须提取至少10个实际配置步骤，不要只提取背景介绍。",
                        temperature=0.2,  # 降低温度，更确定性
                        require_confidence=False  # 弱展示
                    )
                    
                    # 验证二次提取结果
                    if isinstance(retry_steps, list):
                        retry_validated = []
                        for step in retry_steps[:30]:
                            if isinstance(step, dict):
                                title = step.get("title", "").strip()
                                description = step.get("description", "").strip()
                                title_lower = title.lower()
                                # 扩展过滤关键词
                                filter_keywords = ["回顾", "背景", "介绍", "概述", "了解", "发展历程", "历史", "起源", "选择", "对比", "比较"]
                                if title and description and not any(keyword in title_lower for keyword in filter_keywords):
                                    step_item = {
                                        "step": len(retry_validated) + 1,
                                        "title": title,
                                        "description": description
                                    }
                                    
                                    # 弱展示：如果AI返回了可信度和来源，则添加
                                    if "confidence" in step or "source_ids" in step:
                                        base_confidence = ConfidenceCalculator.normalize_confidence(
                                            step.get("confidence")
                                        )
                                        source_ids = step.get("source_ids", [])
                                        
                                        confidence_result = ConfidenceCalculator.calculate_confidence(
                                            base_confidence=base_confidence,
                                            source_ids=source_ids,
                                            segments=segments,
                                            content=content,
                                            ai_response=str(step)
                                        )
                                        
                                        step_item["confidence"] = confidence_result["score"]
                                        step_item["confidence_label"] = confidence_result["label"]
                                        
                                        if source_ids:
                                            source_segments = SourceSegmenter.get_segments_by_ids(segments, source_ids)
                                            step_item["sources"] = [
                                                {
                                                    "id": seg["id"],
                                                    "text": seg["text"][:200] + "..." if len(seg["text"]) > 200 else seg["text"],
                                                    "position": seg["position"]
                                                }
                                                for seg in source_segments
                                            ]
                                        else:
                                            step_item["sources"] = []
                                    
                                    retry_validated.append(step_item)
                        
                        # 如果二次提取的结果更好，使用它
                        if len(retry_validated) > len(validated_steps):
                            validated_steps = retry_validated
                            logger.info("二次提取成功", steps_count=len(validated_steps))
                        else:
                            logger.warning("二次提取结果不理想", 
                                         retry_count=len(retry_validated),
                                         original_count=len(validated_steps))
                except Exception as retry_error:
                    logger.error("二次提取失败", error=str(retry_error))
            
            # 最终验证
            if len(validated_steps) < 3:
                logger.error("配置步骤提取严重不足", 
                           total_steps=len(validated_steps),
                           content_length=len(content))
            
            return validated_steps
            
        except Exception as e:
            logger.error("配置流程提取失败", error=str(e))
            return []
    
    @staticmethod
    async def _identify_components(content: str, segments: List[Dict]) -> List[Dict]:
        """识别组件"""
        ai_service = get_ai_service()
        
        # 使用完整内容，不进行截断
        # 如果内容太长（超过20000字符），使用前15000字符 + 后5000字符（确保包含开头和结尾）
        if len(content) > 20000:
            content_preview = content[:15000] + "\n\n... [中间内容已省略] ...\n\n" + content[-5000:]
        else:
            content_preview = content
        
        prompt = f"""请从以下架构文档中识别**所有系统组件**。

文档内容：
{content_preview}

**重要要求：**
1. **必须识别文档中提到的所有组件，如果文档只提到部分组件，请基于架构描述推断其他相关组件**，包括：
   - 消息中间件（如 Apache RocketMQ）
   - Spring 框架组件（如 Spring Boot、Spring Cloud Stream、Spring Cloud Bus）
   - 集成组件（如 RocketMQ-Spring-Boot-Starter、RocketMQ Binder）
   - 抽象层组件（如 Spring Messaging）
   - 应用层组件（如业务微服务应用）
   - 任何在文档中被明确提及的技术组件、框架、库、工具

2. **每个组件必须包含**：
   - name：组件的标准名称（使用英文原名，不要翻译）
   - description：详细描述组件在系统中的作用、位置和职责
   - dependencies：该组件依赖的其他组件列表（如果文档中提到了依赖关系）

3. **完整性要求（非常重要）**：
   - **如果文档提到了3种集成方法，必须识别至少6-8个组件**
   - **如果文档提到了2种集成方法，必须识别至少4-5个组件**
   - **如果文档提到了1种集成方法，必须识别至少3个组件**
   - **如果文档只提到部分组件，请基于架构描述推断其他相关组件**：
     * 如果提到RocketMQ-Spring-Boot-Starter，必须识别：Spring Boot、Spring Messaging、Apache RocketMQ
     * 如果提到Spring Cloud Stream，必须识别：Spring Cloud Stream、Spring Messaging、对应的Binder（如spring-cloud-stream-binder-rocketmq）、Apache RocketMQ
     * 如果提到Spring Cloud Bus，必须识别：Spring Cloud Bus、Spring Cloud Stream、对应的Binder、Apache RocketMQ
   - 例如：RocketMQ-Spring-Boot-Starter、Spring Cloud Stream、spring-cloud-stream-binder-rocketmq、Spring Cloud Bus、Spring Messaging、Apache RocketMQ、Spring Boot 等
   - 不要遗漏任何在文档中被讨论的组件
   - 确保组件列表能够反映文档中描述的完整架构
   - **不要只识别基础设施组件，必须识别所有层次的组件（应用层、框架层、集成层、基础设施层）**

4. **准确性要求**：
   - 组件名称必须使用标准的英文技术名称
   - 不要翻译技术名词（如不要写成"Spring Boot（春波特）"）
   - 依赖关系必须准确反映文档中描述的关系

请以JSON格式返回，格式如下：
```json
[
    {{
        "name": "Apache RocketMQ",
        "description": "阿里开源的消息中间件，负责消息的持久化存储、主题管理、消息路由、高可靠投递以及流处理。位于架构最底层，是独立部署的基础设施。",
        "dependencies": []
    }},
    {{
        "name": "RocketMQ-Spring-Boot-Starter",
        "description": "RocketMQ官方为Spring Boot提供的集成组件，提供了RocketMQTemplate和@RocketMQMessageListener注解，让开发者能够以Spring风格的方式使用RocketMQ。位于Spring抽象集成层。",
        "dependencies": ["Spring Boot", "Spring Messaging", "Apache RocketMQ"]
    }},
    {{
        "name": "Spring Cloud Stream",
        "description": "Spring Cloud提供的声明式消息驱动微服务框架，引入了Binder抽象，将应用与消息中间件完全隔离。位于Spring抽象集成层，是比RocketMQ-Spring-Boot-Starter抽象程度更高的方案。",
        "dependencies": ["Spring Messaging"]
    }},
    {{
        "name": "spring-cloud-stream-binder-rocketmq",
        "description": "Spring Cloud Stream Binder的RocketMQ实现，是连接Spring Cloud Stream应用内核与Apache RocketMQ集群的桥梁。位于客户端适配层。",
        "dependencies": ["Spring Cloud Stream", "Apache RocketMQ"]
    }},
    {{
        "name": "Spring Cloud Bus",
        "description": "基于Spring Cloud Stream构建，用于广播配置变更或管理事件到分布式系统中的所有服务实例。位于应用层/业务层之上。",
        "dependencies": ["Spring Cloud Stream"]
    }},
    ...
]
```

**注意**：只返回JSON数组，不要包含其他文字说明。确保识别所有在文档中被提及的组件。"""
        
        system_prompt = """你是一个系统架构专家，擅长识别系统组件和依赖关系。

**重要**：
1. 必须识别文档中提到的所有组件，不要遗漏任何技术组件、框架或工具
2. 如果文档只提到部分组件，你必须基于架构描述推断其他相关组件
3. 如果文档提到多种集成方法，必须识别所有相关组件
4. 不要只识别基础设施组件，必须识别所有层次的组件（应用层、框架层、集成层、基础设施层）"""
        
        try:
            # 第一次尝试（弱展示：不强制要求source_ids和confidence）
            components = await ai_service.generate_with_sources(
                prompt=prompt,
                segments=segments,
                system_prompt=system_prompt,
                temperature=0.3,
                require_confidence=False  # 弱展示
            )
            
            # 确保返回列表格式
            if isinstance(components, dict):
                components = [components]
            elif not isinstance(components, list):
                components = []
            
            # 验证格式并清理技术名称
            validated_components = []
            seen_names = set()  # 避免重复（使用标准化名称）
            name_mapping = {}  # 标准化名称 -> 原始名称（保留更完整的名称）
            ai_checked_pairs = set()  # 缓存已用AI检查过的名称对，避免重复调用
            
            for comp in components[:30]:  # 最多30个组件
                if isinstance(comp, dict) and "name" in comp:
                    name = clean_tech_name(comp.get("name", "").strip())
                    description = comp.get("description", "").strip()
                    
                    # 确保名称不为空且不重复（使用标准化名称比较，失败时使用AI判断）
                    if name:
                        normalized = normalize_tech_name(name)
                        if normalized and normalized not in seen_names:
                            # 检查是否与已有组件等价（使用AI判断）
                            is_duplicate = False
                            equivalent_name = None
                            
                            for existing_norm, existing_name in name_mapping.items():
                                # 如果标准化名称不同，但可能等价，使用AI判断
                                if normalized != existing_norm:
                                    # 创建检查键（按字母顺序，避免重复检查）
                                    check_key = tuple(sorted([normalized, existing_norm]))
                                    if check_key not in ai_checked_pairs:
                                        try:
                                            is_equivalent = await are_tech_names_equivalent(name, existing_name)
                                            ai_checked_pairs.add(check_key)
                                            
                                            if is_equivalent:
                                                is_duplicate = True
                                                equivalent_name = existing_name
                                                logger.info("AI判断技术名称等价", 
                                                          name1=name, name2=existing_name, 
                                                          normalized1=normalized, normalized2=existing_norm)
                                                break
                                        except Exception as e:
                                            logger.warning("AI判断技术名称等价失败", 
                                                         name1=name, name2=existing_name, error=str(e))
                                            # AI调用失败，继续使用标准化比较
                            
                            if not is_duplicate:
                                seen_names.add(normalized)
                                name_mapping[normalized] = name
                                validated_components.append({
                                    "name": name,
                                    "description": description,
                                    "dependencies": [clean_tech_name(dep) for dep in comp.get("dependencies", [])] if isinstance(comp.get("dependencies"), list) else []
                                })
                            else:
                                # 是重复的，检查是否需要更新为更完整的名称
                                if equivalent_name:
                                    # 如果新名称更完整，更新已有组件
                                    if len(name) > len(equivalent_name) and name.lower().startswith(equivalent_name.lower()):
                                        for i, vc in enumerate(validated_components):
                                            if vc["name"] == equivalent_name:
                                                validated_components[i]["name"] = name
                                                # 更新映射
                                                existing_norm_for_equiv = normalize_tech_name(equivalent_name)
                                                if existing_norm_for_equiv in name_mapping:
                                                    name_mapping[existing_norm_for_equiv] = name
                                                break
                        elif normalized in seen_names:
                            # 如果标准化名称已存在，检查是否需要更新为更完整的名称
                            existing_name = name_mapping.get(normalized)
                            if existing_name and len(name) > len(existing_name) and name.lower().startswith(existing_name.lower()):
                                # 新名称更完整（如 "Apache RocketMQ" vs "RocketMQ"），更新
                                for i, vc in enumerate(validated_components):
                                    if normalize_tech_name(vc["name"]) == normalized:
                                        validated_components[i]["name"] = name
                                        name_mapping[normalized] = name
                                        break
            
            # 如果组件太少（少于3个），尝试第二次识别
            logger.info("组件识别验证完成", 
                       validated_count=len(validated_components),
                       raw_count=len(components) if isinstance(components, list) else 0,
                       will_retry=len(validated_components) < 3)
            
            if len(validated_components) < 3:
                logger.warning("组件识别不足，尝试二次识别", 
                             total_components=len(validated_components),
                             raw_components_count=len(components) if isinstance(components, list) else 0)
                
                # 二次识别：使用完整内容和更明确的提示，要求推断组件
                if len(content) > 20000:
                    retry_content = content[:15000] + "\n\n... [中间内容已省略] ...\n\n" + content[-5000:]
                else:
                    retry_content = content
                
                retry_prompt = f"""请从以下架构文档中识别**所有系统组件**。**必须返回至少5个组件**。

文档内容：
{retry_content}

**严格要求：**
1. **必须返回至少5个组件**，包括：
   - 消息中间件（如 Apache RocketMQ）
   - Spring 框架组件（如 Spring Boot、Spring Cloud Stream、Spring Cloud Bus）
   - 集成组件（如 RocketMQ-Spring-Boot-Starter、RocketMQ Binder）
   - 抽象层组件（如 Spring Messaging）
   - 应用层组件（如业务微服务应用）

2. **如果文档只提到部分组件，请基于架构描述推断其他相关组件**：
   - 如果提到RocketMQ-Spring-Boot-Starter，必须识别：Spring Boot、Spring Messaging、Apache RocketMQ
   - 如果提到Spring Cloud Stream，必须识别：Spring Cloud Stream、Spring Messaging、对应的Binder、Apache RocketMQ
   - 如果提到Spring Cloud Bus，必须识别：Spring Cloud Bus、Spring Cloud Stream、对应的Binder、Apache RocketMQ

3. **不要只识别基础设施组件，必须识别所有层次的组件（应用层、框架层、集成层、基础设施层）**

4. **如果文档提到了多种集成方法，必须识别所有相关组件**

请返回JSON数组，格式：
```json
[
    {{"name": "组件名称（英文）", "description": "组件描述", "dependencies": ["依赖组件"]}},
    ...
]
```

**必须返回至少5个组件，不要只返回1-2个组件。**"""
                
                try:
                    retry_components = await ai_service.generate_with_sources(
                        prompt=retry_prompt,
                        segments=segments,
                        system_prompt="你是一个系统架构专家，必须识别至少5个组件，不要只识别基础设施组件。",
                        temperature=0.2,  # 降低温度，更确定性
                        require_confidence=False  # 弱展示
                    )
                    
                    # 验证二次识别结果
                    if isinstance(retry_components, list):
                        retry_validated = []
                        retry_seen_names = set()  # 使用标准化名称
                        retry_name_mapping = {}  # 标准化名称 -> 原始名称
                        retry_ai_checked_pairs = set()  # 缓存已用AI检查过的名称对
                        
                        for comp in retry_components[:30]:
                            if isinstance(comp, dict) and "name" in comp:
                                name = clean_tech_name(comp.get("name", "").strip())
                                description = comp.get("description", "").strip()
                                if name:
                                    normalized = normalize_tech_name(name)
                                    if normalized and normalized not in retry_seen_names:
                                        # 检查是否与已有组件等价（使用AI判断）
                                        is_duplicate = False
                                        equivalent_name = None
                                        
                                        for existing_norm, existing_name in retry_name_mapping.items():
                                            # 如果标准化名称不同，但可能等价，使用AI判断
                                            if normalized != existing_norm:
                                                # 创建检查键（按字母顺序，避免重复检查）
                                                check_key = tuple(sorted([normalized, existing_norm]))
                                                if check_key not in retry_ai_checked_pairs:
                                                    try:
                                                        is_equivalent = await are_tech_names_equivalent(name, existing_name)
                                                        retry_ai_checked_pairs.add(check_key)
                                                        
                                                        if is_equivalent:
                                                            is_duplicate = True
                                                            equivalent_name = existing_name
                                                            logger.info("AI判断技术名称等价（二次识别）", 
                                                                      name1=name, name2=existing_name)
                                                            break
                                                    except Exception as e:
                                                        logger.warning("AI判断技术名称等价失败（二次识别）", 
                                                                     name1=name, name2=existing_name, error=str(e))
                                        
                                        if not is_duplicate:
                                            retry_seen_names.add(normalized)
                                            retry_name_mapping[normalized] = name
                                            retry_validated.append({
                                                "name": name,
                                                "description": description,
                                                "dependencies": [clean_tech_name(dep) for dep in comp.get("dependencies", [])] if isinstance(comp.get("dependencies"), list) else []
                                            })
                                        else:
                                            # 是重复的，检查是否需要更新为更完整的名称
                                            if equivalent_name:
                                                if len(name) > len(equivalent_name) and name.lower().startswith(equivalent_name.lower()):
                                                    for i, vc in enumerate(retry_validated):
                                                        if vc["name"] == equivalent_name:
                                                            retry_validated[i]["name"] = name
                                                            existing_norm_for_equiv = normalize_tech_name(equivalent_name)
                                                            if existing_norm_for_equiv in retry_name_mapping:
                                                                retry_name_mapping[existing_norm_for_equiv] = name
                                                            break
                                    elif normalized in retry_seen_names:
                                        # 如果标准化名称已存在，检查是否需要更新为更完整的名称
                                        existing_name = retry_name_mapping.get(normalized)
                                        if existing_name and len(name) > len(existing_name) and name.lower().startswith(existing_name.lower()):
                                            for i, vc in enumerate(retry_validated):
                                                if normalize_tech_name(vc["name"]) == normalized:
                                                    retry_validated[i]["name"] = name
                                                    retry_name_mapping[normalized] = name
                                                    break
                        
                        # 如果二次识别的结果更好，使用它
                        if len(retry_validated) > len(validated_components):
                            validated_components = retry_validated
                            logger.info("二次识别成功", components_count=len(validated_components))
                        else:
                            logger.warning("二次识别结果不理想", 
                                         retry_count=len(retry_validated),
                                         original_count=len(validated_components))
                    else:
                        logger.warning("二次识别返回格式错误", retry_type=type(retry_components))
                except Exception as retry_error:
                    logger.error("二次识别失败", error=str(retry_error))
            
            # 最终验证
            if len(validated_components) < 2:
                logger.error("组件识别严重不足", 
                           total_components=len(validated_components),
                           content_length=len(content))
            
            return validated_components
            
        except Exception as e:
            logger.error("组件识别失败", error=str(e))
            return []
    
    @staticmethod
    async def _generate_architecture_view(content: str, segments: List[Dict], components: List[Dict]) -> str:
        """生成组件全景视图"""
        ai_service = get_ai_service()
        
        content_preview = content[:3000] if len(content) > 3000 else content
        components_info = "\n".join([f"- {c['name']}: {c.get('description', '')}" for c in components[:10]])
        
        prompt = f"""基于以下架构文档和组件信息，生成组件在系统中的全景视图描述。

文档内容：
{content_preview}

已识别组件：
{components_info if components_info else "无"}

请用清晰的语言描述：
1. 系统整体架构
2. 各组件的职责和位置
3. 组件之间的关系和数据流

可以生成Mermaid图表代码（可选），格式：
```mermaid
graph TB
    A[组件A] --> B[组件B]
    ...
```

**Mermaid 代码要求（重要）：**
1. 所有节点必须有标签，格式：NodeName[标签文本]
2. 所有节点必须通过边（-->）连接，不能有孤立节点
3. 节点名称只能包含字母、数字、下划线，不能有空格或特殊字符
4. 如果节点名称包含空格或特殊字符，必须用引号包裹，如："Spring Boot"[Spring Boot应用]
5. 每行只能定义一个节点或一条边
6. 不能有重复的节点定义
7. 确保语法正确，所有括号、引号必须成对
8. 不要生成无效的节点（如只有节点名没有标签也没有连接的节点）"""
        
        system_prompt = "你是一个系统架构专家，擅长描述系统架构和组件关系。"
        
        try:
            view = await ai_service.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=3000  # 增加token限制，确保Mermaid代码完整生成
            )
            
            # 清理生成的 Mermaid 代码中的常见问题
            cleaned_view = ArchitectureProcessor._clean_mermaid_in_text(view)
            
            logger.info("全景视图生成完成", view_length=len(cleaned_view))
            return cleaned_view.strip()
            
        except Exception as e:
            logger.error("全景视图生成失败", error=str(e))
            return "系统架构视图生成失败，请查看原始文档。"
    
    @staticmethod
    def _clean_mermaid_in_text(text: str) -> str:
        """清理文本中的 Mermaid 代码块"""
        import re
        
        # 匹配 Mermaid 代码块（包括不完整的代码块）
        # 先尝试匹配完整的代码块
        mermaid_pattern = r'```mermaid\s*\n(.*?)```'
        
        def clean_mermaid_code(match):
            code = match.group(1)
            # 检查代码是否有效（至少包含graph声明和一些内容）
            code_stripped = code.strip()
            # 如果代码太短或明显被截断（只有单个字符或只有graph声明），可能是AI生成有问题
            if len(code_stripped) < 20 or (len(code_stripped) < 50 and 'graph' in code_stripped.lower() and '[' not in code_stripped and '-->' not in code_stripped):
                logger.warning("Mermaid代码可能被截断或无效", code_length=len(code_stripped), code_preview=code_stripped[:100])
                # 返回空的代码块，让前端显示错误而不是空白
                return '```mermaid\ngraph TB\n    A[无效的图表代码]\n```'
            
            # 移除节点名后面的数字（如 SCMsg1 -> SCMsg）
            code = re.sub(r'([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)(?=\s|$|\n|\[|-->|--|<-|==)', r'\1', code)
            # 移除标签后的数字（如 SCMsg[SCMsg]1 -> SCMsg[SCMsg]）
            code = re.sub(r'(\])([0-9]+)(?=\s|$|\n)', r'\1', code)
            # 移除无效的 direction 声明
            code = re.sub(r'^\s*direction\s+(TB|BT|LR|RL)\s*$', '', code, flags=re.MULTILINE)
            # 分离紧跟着的节点（如 ]SCMsg -> ]\nSCMsg）
            code = re.sub(r'(\])([A-Z][A-Za-z0-9_\-]+)(?![\[\]<>\-|:])', r'\1\n\2', code)
            # 为孤立节点添加标签
            lines = code.split('\n')
            fixed_lines = []
            for line in lines:
                trimmed = line.strip()
                if not trimmed or trimmed.startswith('%') or re.match(r'^graph\s+(TB|BT|LR|RL)', trimmed, re.I) or re.match(r'^subgraph', trimmed, re.I) or trimmed == 'end':
                    fixed_lines.append(line)
                    continue
                # 检查是否是孤立节点
                isolated_match = re.match(r'^([A-Za-z][A-Za-z0-9_\-]*?)\s*$', trimmed)
                if isolated_match and not any(c in trimmed for c in ['[', ']', '-->', '--', '<-', '==']):
                    node_name = isolated_match.group(1)
                    # 移除节点名中的数字（多次处理确保移除）
                    node_name = re.sub(r'([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)$', r'\1', node_name)
                    node_name = re.sub(r'([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)', r'\1', node_name)  # 再次移除
                    # 保持缩进
                    indent = line[:len(line) - len(line.lstrip())]
                    fixed_lines.append(f'{indent}{node_name}[{node_name}]')
                else:
                    fixed_lines.append(line)
            code = '\n'.join(fixed_lines)
            # 最后再次移除所有数字
            code = re.sub(r'(\])([0-9]+)(?=\s|$|\n)', r'\1', code)
            code = re.sub(r'([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)(\[)', r'\1\3', code)
            return f'```mermaid\n{code}\n```'
        
        # 替换所有完整的 Mermaid 代码块
        cleaned_text = re.sub(mermaid_pattern, clean_mermaid_code, text, flags=re.DOTALL)
        
        # 处理不完整的 Mermaid 代码块（只有开始标记，没有结束标记）
        # 检查是否有未闭合的mermaid代码块
        if '```mermaid' in cleaned_text:
            # 查找所有```mermaid的位置
            mermaid_starts = []
            for match in re.finditer(r'```mermaid', cleaned_text):
                mermaid_starts.append(match.start())
            
            # 从后往前处理，避免位置偏移问题
            for start_pos in reversed(mermaid_starts):
                # 从```mermaid之后查找下一个```或文本结束
                after_start = cleaned_text[start_pos + 9:]  # 跳过```mermaid
                # 查找下一个```的位置
                next_close = after_start.find('```')
                if next_close == -1:
                    # 没有找到结束标记，需要添加
                    # 提取代码部分（到文本结束或下一个段落，但保留代码内容）
                    # 使用更宽松的匹配，匹配到文本结束或明显的段落分隔
                    code_match = re.search(r'```mermaid\s*\n(.*?)(?=\n\n[^\s]|\n[#\*]|$)', cleaned_text[start_pos:], re.DOTALL)
                    if code_match:
                        code = code_match.group(1).strip()
                        if code:  # 确保有代码内容
                            # 应用相同的清理逻辑
                            code = re.sub(r'([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)(?=\s|$|\n|\[|-->|--|<-|==)', r'\1', code)
                            code = re.sub(r'(\])([0-9]+)(?=\s|$|\n)', r'\1', code)
                            code = re.sub(r'^\s*direction\s+(TB|BT|LR|RL)\s*$', '', code, flags=re.MULTILINE)
                            code = re.sub(r'(\])([A-Z][A-Za-z0-9_\-]+)(?![\[\]<>\-|:])', r'\1\n\2', code)
                            lines = code.split('\n')
                            fixed_lines = []
                            for line in lines:
                                trimmed = line.strip()
                                if not trimmed or trimmed.startswith('%') or re.match(r'^graph\s+(TB|BT|LR|RL)', trimmed, re.I) or re.match(r'^subgraph', trimmed, re.I) or trimmed == 'end':
                                    fixed_lines.append(line)
                                    continue
                                isolated_match = re.match(r'^([A-Za-z][A-Za-z0-9_\-]*?)\s*$', trimmed)
                                if isolated_match and not any(c in trimmed for c in ['[', ']', '-->', '--', '<-', '==']):
                                    node_name = isolated_match.group(1)
                                    node_name = re.sub(r'([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)$', r'\1', node_name)
                                    node_name = re.sub(r'([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)', r'\1', node_name)
                                    indent = line[:len(line) - len(line.lstrip())]
                                    fixed_lines.append(f'{indent}{node_name}[{node_name}]')
                                else:
                                    fixed_lines.append(line)
                            code = '\n'.join(fixed_lines)
                            code = re.sub(r'(\])([0-9]+)(?=\s|$|\n)', r'\1', code)
                            code = re.sub(r'([A-Za-z][A-Za-z0-9_\-]*?)([0-9]+)(\[)', r'\1\3', code)
                            # 替换不完整的代码块为完整的
                            incomplete_block = cleaned_text[start_pos:start_pos + 9 + len(code_match.group(0))]
                            complete_block = f'```mermaid\n{code}\n```'
                            cleaned_text = cleaned_text[:start_pos] + complete_block + cleaned_text[start_pos + 9 + len(code_match.group(0)):]
        
        return cleaned_text
    
    @staticmethod
    async def _generate_plain_explanation(content: str, segments: List[Dict]) -> str:
        """生成白话串讲"""
        ai_service = get_ai_service()
        
        content_preview = content[:3000] if len(content) > 3000 else content
        
        prompt = f"""请用通俗易懂的白话，解释以下架构/搭建文档中的技术内容。

文档内容：
{content_preview}

要求：
1. 用通俗易懂的语言，避免过于专业的术语
2. 用类比和例子帮助理解
3. 解释技术细节和配置步骤
4. 保持逻辑清晰，条理分明
5. 使用完整的括号对，不要使用不完整的括号（如只有右括号")"或"）"）
6. 如果需要在句子中添加说明，使用完整的括号对（如"（说明内容）"）
7. 确保所有括号都是成对出现的"""
        
        system_prompt = "你是一个技术讲师，擅长用通俗易懂的语言解释复杂的技术概念。请确保输出格式正确，所有括号都是成对出现的，不要使用不完整的括号。"
        
        try:
            explanation = await ai_service.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=2000
            )
            
            # 清理输出：移除单独的右括号
            cleaned_explanation = ArchitectureProcessor._clean_explanation_text(explanation.strip())
            
            return cleaned_explanation
            
        except Exception as e:
            logger.error("白话串讲生成失败", error=str(e))
            return "白话解释生成失败，请查看原始文档。"
    
    @staticmethod
    def _clean_explanation_text(text: str) -> str:
        """清理白话串讲文本，修复括号不匹配的问题"""
        import re
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            original_line = line
            
            # 统计括号数量（包括中文括号和英文括号）
            left_parens = len(re.findall(r'[\uff08(（]', line))  # 中文左括号、英文左括号、全角左括号
            right_parens = len(re.findall(r'[\uff09)]', line))   # 中文右括号、英文右括号、全角右括号
            
            # 如果右括号多于左括号，移除多余的右括号（从行尾开始移除）
            if right_parens > left_parens:
                excess = right_parens - left_parens
                # 从行尾开始移除多余的右括号
                for _ in range(excess):
                    line = re.sub(r'[\uff09)]', '', line, count=1)
            
            # 如果左括号多于右括号，在行尾添加缺失的右括号
            if left_parens > right_parens:
                missing = left_parens - right_parens
                # 添加缺失的右括号（使用中文右括号，因为中文文本中更常见）
                line = line + '）' * missing
            
            # 修复常见的括号不匹配模式
            # 1. 修复 "？ （内容" 这种模式（问号后缺少右括号）
            # 匹配：问号/感叹号 + 空格 + 左括号 + 内容（到行尾或标点前）
            line = re.sub(r'([？！。])\s*[\uff08(（]([^）)\uff09)]+?)(?=\s*$|\n|[\s，。、；：])', r'\1（\2）', line)
            
            # 2. 移除行首的单独右括号
            line = re.sub(r'^\s*[\uff09)]+', '', line)
            
            # 3. 移除行尾的单独左括号（没有内容）
            line = re.sub(r'[\uff08(（]+\s*$', '', line)
            
            # 4. 确保所有左括号都有对应的右括号（在行尾或段落结束前）
            # 重新统计（因为前面可能已经修复了一些）
            left_parens_final = len(re.findall(r'[\uff08(（]', line))
            right_parens_final = len(re.findall(r'[\uff09)]', line))
            unclosed_left = left_parens_final - right_parens_final
            if unclosed_left > 0:
                # 在行尾添加缺失的右括号
                line = line + '）' * unclosed_left
            
            if line.strip():
                cleaned_lines.append(line.strip())
        
        return '\n'.join(cleaned_lines)
    
    @staticmethod
    async def _generate_checklist(content: str, segments: List[Dict], config_steps: List[Dict]) -> List[Dict]:
        """生成配置检查清单"""
        ai_service = get_ai_service()
        
        content_preview = content[:2000] if len(content) > 2000 else content
        steps_info = "\n".join([f"{s['step']}. {s['title']}" for s in config_steps[:10]])
        
        prompt = f"""基于以下架构文档和配置步骤，生成配置检查清单。

文档内容：
{content_preview}

配置步骤：
{steps_info if steps_info else "无"}

请返回JSON格式的数组，包含配置验证步骤：
["检查项1", "检查项2", ...]

检查项应该：
1. 覆盖关键配置点
2. 便于验证配置是否正确
3. 包含必要的验证方法"""
        
        system_prompt = "你是一个系统运维专家，擅长制定配置检查清单。"
        
        try:
            result = await ai_service.generate_with_sources(
                prompt=prompt,
                segments=segments,
                system_prompt=system_prompt,
                temperature=0.4,
                require_confidence=False  # 弱展示
            )
            
            # 提取checklist列表
            if isinstance(result, dict) and "checklist" in result:
                checklist = result["checklist"]
            elif isinstance(result, list):
                checklist = result
            elif isinstance(result, dict):
                # 尝试从其他字段提取
                checklist = result.get("items", result.get("checks", []))
            else:
                checklist = []
            
            # 确保返回列表格式
            if isinstance(checklist, list):
                checklist_items = checklist[:20]  # 限制数量
            else:
                checklist_items = []
            
            # 弱展示：如果AI返回了可信度和来源，则添加
            if isinstance(result, dict) and ("confidence" in result or "source_ids" in result):
                base_confidence = ConfidenceCalculator.normalize_confidence(
                    result.get("confidence")
                )
                source_ids = result.get("source_ids", [])
                
                confidence_result = ConfidenceCalculator.calculate_confidence(
                    base_confidence=base_confidence,
                    source_ids=source_ids,
                    segments=segments,
                    content=content,
                    ai_response=str(checklist_items)
                )
                
                return {
                    "items": checklist_items,
                    "confidence": confidence_result["score"],
                    "confidence_label": confidence_result["label"],
                    "sources": [
                        {
                            "id": seg["id"],
                            "text": seg["text"][:200] + "..." if len(seg["text"]) > 200 else seg["text"],
                            "position": seg["position"]
                        }
                        for seg in SourceSegmenter.get_segments_by_ids(segments, source_ids)
                    ] if source_ids else []
                }
            else:
                # 兼容旧格式
                return {
                    "items": checklist_items,
                    "confidence": None,
                    "confidence_label": None,
                    "sources": []
                }
                
        except Exception as e:
            logger.error("检查清单生成失败", error=str(e))
            return {
                "items": [],
                "confidence": None,
                "confidence_label": None,
                "sources": []
            }
    
    @staticmethod
    async def _extract_related_technologies(content: str, segments: List[Dict], components: List[Dict]) -> List[Dict]:
        """提取相关技术栈"""
        ai_service = get_ai_service()
        
        content_preview = content[:3000] if len(content) > 3000 else content
        components_info = "\n".join([f"- {c['name']}: {c.get('description', '')}" for c in components[:10]])
        
        prompt = f"""请从以下架构文档和组件信息中，提取所有涉及到的IT技术栈（编程语言、框架、数据库、工具、平台、消息队列等）。

文档内容：
{content_preview}

已识别组件：
{components_info if components_info else "无"}

请返回JSON格式的数组，包含所有提到的技术名词：
["技术1", "技术2", ...]

要求：
1. 只提取IT相关的技术名词（如 Java, Spring Boot, RocketMQ, MySQL, Docker 等）
2. 使用标准的技术名称（如 "Spring Boot" 而不是 "springboot"）
3. 必须使用英文原名，不要翻译技术名词（如 "Spring Boot" 而不是 "Spring Boot（春波特）"）
4. 去除重复项
5. 如果没有技术名词，返回空数组 []

只返回JSON数组，不要其他内容。"""
        
        system_prompt = "你是一个技术架构专家，擅长识别技术栈和技术名词。"
        
        try:
            result = await ai_service.generate_with_sources(
                prompt=prompt,
                segments=segments,
                system_prompt=system_prompt,
                temperature=0.3,
                require_confidence=False  # 弱展示
            )
            
            # 提取technologies列表
            if isinstance(result, dict) and "technologies" in result:
                technologies = result["technologies"]
            elif isinstance(result, list):
                technologies = result
            else:
                technologies = []
            
            # 清理和验证技术名词
            validated_techs = []
            for tech in technologies:
                if isinstance(tech, str) and tech.strip():
                    tech_clean = clean_tech_name(tech)
                    # 过滤掉太短或太长的词
                    if 2 <= len(tech_clean) <= 50:
                        validated_techs.append(tech_clean)
            
            validated_techs = validated_techs[:20]  # 限制数量
            
            # 弱展示：如果AI返回了可信度和来源，则添加
            if isinstance(result, dict) and ("confidence" in result or "source_ids" in result):
                base_confidence = ConfidenceCalculator.normalize_confidence(
                    result.get("confidence")
                )
                source_ids = result.get("source_ids", [])
                
                confidence_result = ConfidenceCalculator.calculate_confidence(
                    base_confidence=base_confidence,
                    source_ids=source_ids,
                    segments=segments,
                    content=content,
                    ai_response=str(validated_techs)
                )
                
                return {
                    "technologies": validated_techs,
                    "confidence": confidence_result["score"],
                    "confidence_label": confidence_result["label"],
                    "sources": [
                        {
                            "id": seg["id"],
                            "text": seg["text"][:200] + "..." if len(seg["text"]) > 200 else seg["text"],
                            "position": seg["position"]
                        }
                        for seg in SourceSegmenter.get_segments_by_ids(segments, source_ids)
                    ] if source_ids else []
                }
            else:
                # 兼容旧格式
                return {
                    "technologies": validated_techs,
                    "confidence": None,
                    "confidence_label": None,
                    "sources": []
                }
                
        except Exception as e:
            logger.error("技术栈提取失败，尝试从组件中提取", error=str(e))
            # 如果AI提取失败，从组件中提取技术名词
            from app.services.entity_extractor import EntityExtractor
            techs = set()
            for comp in components:
                if isinstance(comp, dict):
                    # 从组件名称和描述中提取
                    if 'name' in comp:
                        techs.update(EntityExtractor._extract_tech_from_text(comp['name']))
                    if 'description' in comp:
                        techs.update(EntityExtractor._extract_tech_from_text(comp['description']))
                    if 'dependencies' in comp:
                        for dep in comp.get('dependencies', []):
                            if isinstance(dep, str):
                                techs.update(EntityExtractor._extract_tech_from_text(dep))
            return list(techs)[:20]

