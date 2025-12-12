"""
知识图谱构建服务
- 从架构师视角构建技术栈知识图谱
- 节点是IT技术名词（带架构层次信息），边表示上下游关系
"""
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict, Counter
import structlog

logger = structlog.get_logger()


class KnowledgeGraphBuilder:
    """知识图谱构建器"""
    
    @staticmethod
    async def build_graph(
        db,
        similarity_threshold: float = 0.3,
        max_nodes: int = 50,
        document_type: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> Dict:
        """
        构建知识图谱（从架构师视角）
        
        Args:
            db: 数据库会话
            similarity_threshold: 关联度阈值（默认0.3）
            max_nodes: 最大节点数（默认50）
            document_type: 文档类型过滤（可选）
            document_id: 文档ID（可选，如果提供则只显示该文档中的技术栈架构）
        
        Returns:
            知识图谱数据字典（包含nodes和edges，带架构层次和上下游关系）
        """
        from sqlalchemy import select
        from app.models.processing_result import ProcessingResult
        from app.models.system_learning_data import SystemLearningData
        from app.models.document import Document
        from app.services.entity_extractor import get_entity_extractor
        
        logger.info("开始构建知识图谱（基于技术名词）", 
                   threshold=similarity_threshold, 
                   max_nodes=max_nodes)
        
        try:
            from uuid import UUID
            
            # 1. 获取文档结果（如果指定了document_id，只获取该文档）
            if document_id:
                try:
                    doc_uuid = UUID(document_id) if isinstance(document_id, str) else document_id
                except ValueError:
                    logger.warning("无效的文档ID格式", document_id=document_id)
                    return {
                        "nodes": [],
                        "edges": [],
                        "total_nodes": 0,
                        "total_edges": 0,
                        "error": "无效的文档ID格式",
                        "generated_at": datetime.now().isoformat()
                    }
                
                query = select(
                    ProcessingResult.document_id,
                    ProcessingResult.document_type,
                    ProcessingResult.result_data
                ).join(
                    Document, ProcessingResult.document_id == Document.id
                ).where(
                    Document.id == doc_uuid,
                    Document.status == 'completed'
                )
                
                if document_type:
                    query = query.where(ProcessingResult.document_type == document_type)
                
                query_result = await db.execute(query)
                documents_data = query_result.fetchall()
            else:
                # 获取所有已处理的文档结果
                query = select(
                    ProcessingResult.document_id,
                    ProcessingResult.document_type,
                    ProcessingResult.result_data
                ).join(
                    Document, ProcessingResult.document_id == Document.id
                ).where(
                    Document.status == 'completed'
                )
                
                if document_type:
                    query = query.where(ProcessingResult.document_type == document_type)
                
                query_result = await db.execute(query)
                documents_data = query_result.fetchall()
            
            if len(documents_data) == 0:
                logger.warning("没有已处理的文档，无法构建知识图谱")
                return {
                    "nodes": [],
                    "edges": [],
                    "total_nodes": 0,
                    "total_edges": 0,
                    "generated_at": datetime.now().isoformat()
                }
            
            # 2. 如果是单文档模式，使用架构分析器生成架构视角的知识图谱
            if document_id and len(documents_data) == 1:
                return await KnowledgeGraphBuilder._build_architecture_graph(
                    db, documents_data[0], similarity_threshold, max_nodes
                )
            
            # 3. 多文档模式：从文档中提取技术名词
            extractor = get_entity_extractor()
            technology_docs_map = defaultdict(set)  # 技术 -> 包含该技术的文档集合
            doc_technologies_map = {}  # 文档ID -> 技术列表
            all_technologies = set()  # 所有提取到的技术名词集合（用于单文档模式）
            component_relationships = {}  # 组件关系（用于架构文档）
            
            for doc_data in documents_data:
                doc_id = str(doc_data.document_id)
                processing_result = doc_data.result_data if isinstance(doc_data.result_data, dict) else {}
                
                # 从处理结果中提取技术名词
                technologies = await extractor.extract_technologies_from_result(processing_result)
                
                # 如果是架构文档，从 components 中提取更多信息
                if doc_data.document_type == 'architecture' and 'components' in processing_result:
                    components = processing_result.get('components', [])
                    if isinstance(components, list):
                        # 提取组件依赖关系
                        for comp in components:
                            if isinstance(comp, dict) and 'name' in comp:
                                comp_name = comp.get('name', '').strip()
                                comp_deps = comp.get('dependencies', [])
                                if comp_name and comp_deps:
                                    # 从组件名称中提取技术名词
                                    from app.services.entity_extractor import EntityExtractor
                                    comp_techs = EntityExtractor._extract_tech_from_text(comp_name)
                                    technologies.extend(comp_techs)
                                    
                                    # 从依赖中提取技术名词
                                    for dep in comp_deps:
                                        if isinstance(dep, str):
                                            dep_techs = EntityExtractor._extract_tech_from_text(dep)
                                            technologies.extend(dep_techs)
                                            # 记录组件关系
                                            for comp_tech in comp_techs:
                                                for dep_tech in dep_techs:
                                                    if comp_tech != dep_tech:
                                                        if comp_tech not in component_relationships:
                                                            component_relationships[comp_tech] = set()
                                                        component_relationships[comp_tech].add(dep_tech)
                
                # 如果处理结果中没有，尝试从文档内容中提取
                if not technologies:
                    try:
                        doc_uuid = UUID(doc_id) if isinstance(doc_data.document_id, str) else doc_data.document_id
                        sld_query = await db.execute(
                            select(SystemLearningData.content_summary)
                            .where(SystemLearningData.document_id == doc_uuid)
                        )
                        sld_data = sld_query.scalar_one_or_none()
                        if sld_data and hasattr(sld_data, 'content_summary') and sld_data.content_summary:
                            technologies = await extractor.extract_technologies_from_content(sld_data.content_summary)
                    except Exception as e:
                        logger.warning("获取文档内容摘要失败", document_id=doc_id, error=str(e))
                
                # 去重并标准化技术名词
                technologies = list(set(technologies))
                # 标准化：将 "MQ" 扩展为 "RocketMQ"（如果文档中提到 RocketMQ）
                if 'MQ' in technologies:
                    # 检查是否有 RocketMQ 相关的技术
                    has_rocketmq = any('rocketmq' in tech.lower() or 'rocket' in tech.lower() for tech in technologies)
                    if has_rocketmq and 'RocketMQ' not in technologies:
                        technologies.append('RocketMQ')
                        technologies.remove('MQ')
                
                if technologies:
                    doc_technologies_map[doc_id] = technologies
                    for tech in technologies:
                        technology_docs_map[tech].add(doc_id)
                        all_technologies.add(tech)
            
            if len(technology_docs_map) == 0:
                logger.warning("未提取到技术名词，无法构建知识图谱")
                return {
                    "nodes": [],
                    "edges": [],
                    "total_nodes": 0,
                    "total_edges": 0,
                    "generated_at": datetime.now().isoformat()
                }
            
            # 3. 构建技术名词节点（优化：优先选择有强关联关系的技术）
            from app.services.tech_relationship_service import get_tech_relationship_service
            relationship_service = get_tech_relationship_service()
            
            if document_id:
                # 单文档模式：只显示该文档中的技术名词，但优先选择有强关联关系的
                tech_scores = {}
                for tech in all_technologies:
                    # 计算技术的重要性分数：基于与其他技术的关联强度
                    score = 0
                    related_count = 0
                    for other_tech in all_technologies:
                        if tech != other_tech:
                            strength = relationship_service.get_relationship_strength_sync(tech, other_tech)
                            if strength > 0:
                                score += strength
                                related_count += 1
                    # 重要性 = 平均关联强度 + 关联数量权重
                    avg_strength = score / related_count if related_count > 0 else 0
                    tech_scores[tech] = avg_strength * 0.7 + (related_count / len(all_technologies)) * 0.3 if len(all_technologies) > 1 else 1.0
                
                # 按重要性分数排序
                sorted_techs = sorted(tech_scores.items(), key=lambda x: x[1], reverse=True)
                selected_techs = [tech for tech, score in sorted_techs[:max_nodes]]
                tech_frequency = {tech: 1 for tech in selected_techs}
            else:
                # 多文档模式：按出现频率和关联关系综合排序
                tech_frequency = {tech: len(docs) for tech, docs in technology_docs_map.items()}
                tech_scores = {}
                for tech, freq in tech_frequency.items():
                    # 计算综合分数：频率 + 关联关系强度
                    related_strength_sum = 0
                    related_count = 0
                    for other_tech, other_freq in tech_frequency.items():
                        if tech != other_tech:
                            strength = relationship_service.get_relationship_strength_sync(tech, other_tech)
                            if strength > 0:
                                related_strength_sum += strength
                                related_count += 1
                    avg_related_strength = related_strength_sum / related_count if related_count > 0 else 0
                    # 综合分数 = 频率权重(0.4) + 关联强度权重(0.6)
                    tech_scores[tech] = (freq / max(tech_frequency.values()) if tech_frequency.values() else 0) * 0.4 + avg_related_strength * 0.6
                
                sorted_techs = sorted(tech_scores.items(), key=lambda x: x[1], reverse=True)
                selected_techs = [tech for tech, score in sorted_techs[:max_nodes]]
            
            # 4. 构建节点列表（优化：节点大小基于重要性和关联度）
            nodes = []
            # 计算每个节点的边数量（用于确定节点大小）
            node_edge_count = {}
            for tech in selected_techs:
                node_edge_count[tech] = 0
            
            # 临时计算边数量（在正式构建边之前）
            for i, tech1 in enumerate(selected_techs):
                for j, tech2 in enumerate(selected_techs):
                    if i >= j:
                        continue
                    strength = relationship_service.get_relationship_strength_sync(tech1, tech2)
                    if strength >= similarity_threshold:
                        node_edge_count[tech1] = node_edge_count.get(tech1, 0) + 1
                        node_edge_count[tech2] = node_edge_count.get(tech2, 0) + 1
            
            max_edge_count = max(node_edge_count.values()) if node_edge_count.values() else 1
            
            for tech in selected_techs:
                frequency = tech_frequency[tech]
                edge_count = node_edge_count.get(tech, 0)
                
                # 节点大小基于：频率(30%) + 关联度(70%)
                # 关联度 = 边的数量 / 最大边数量
                edge_ratio = edge_count / max_edge_count if max_edge_count > 0 else 0
                importance = (frequency / max(tech_frequency.values()) if tech_frequency.values() else 1) * 0.3 + edge_ratio * 0.7
                
                # 节点大小：最小30，最大60
                size = int(30 + importance * 30)
                
                nodes.append({
                    "id": tech,
                    "label": tech,
                    "type": "technology",
                    "frequency": frequency,
                    "color": KnowledgeGraphBuilder._get_tech_color(tech),
                    "size": size
                })
            
            # 5. 构建边列表（基于技术栈的实际关联关系，优化筛选逻辑）
            edges = []
            processed_pairs = set()
            
            # 先收集所有可能的边及其权重
            candidate_edges = []
            
            for i, tech1 in enumerate(selected_techs):
                for j, tech2 in enumerate(selected_techs):
                    if i >= j:
                        continue
                    
                    pair_key = tuple(sorted([tech1, tech2]))
                    if pair_key in processed_pairs:
                        continue
                    
                    processed_pairs.add(pair_key)
                    
                    # 获取技术栈的实际关联强度（基于架构师/开发者的视角）
                    relationship_strength = relationship_service.get_relationship_strength_sync(tech1, tech2)
                    
                    # 如果关联强度超过阈值，加入候选边
                    if relationship_strength >= similarity_threshold:
                        if document_id:
                            # 单文档模式：只使用技术栈关联强度
                            final_weight = relationship_strength
                            cooccurrence = 1.0
                            docs_count = 1
                        else:
                            # 多文档模式：使用技术栈关联强度 + 文档共现度
                            docs_with_tech1 = technology_docs_map.get(tech1, set())
                            docs_with_tech2 = technology_docs_map.get(tech2, set())
                            docs_with_both = docs_with_tech1 & docs_with_tech2
                            docs_with_either = docs_with_tech1 | docs_with_tech2
                            
                            cooccurrence = len(docs_with_both) / len(docs_with_either) if len(docs_with_either) > 0 else 0
                            
                            # 最终权重 = 技术栈关联强度 * 0.7 + 文档共现度 * 0.3
                            final_weight = relationship_strength * 0.7 + cooccurrence * 0.3
                            docs_count = len(docs_with_both)
                        
                        candidate_edges.append({
                            "source": tech1,
                            "target": tech2,
                            "cooccurrence": round(cooccurrence, 3),
                            "relationship_strength": round(relationship_strength, 3),
                            "weight": round(final_weight, 3),
                            "label": f"{relationship_strength:.2f}",
                            "documents_count": docs_count
                        })
            
            # 按最终权重排序
            candidate_edges.sort(key=lambda x: x["weight"], reverse=True)
            
            # 优化边筛选：确保每个节点至少有一条边（如果可能），但优先保留强关联边
            # 1. 先保留所有强关联边（权重 >= 0.5）
            strong_edges = [e for e in candidate_edges if e["relationship_strength"] >= 0.5]
            edges.extend(strong_edges)
            
            # 2. 确保每个节点至少有一条边（如果还没有）
            nodes_with_edges = set()
            for edge in edges:
                nodes_with_edges.add(edge["source"])
                nodes_with_edges.add(edge["target"])
            
            for tech in selected_techs:
                if tech not in nodes_with_edges:
                    # 为该节点找一条最强的边
                    for edge in candidate_edges:
                        if edge not in edges and (edge["source"] == tech or edge["target"] == tech):
                            edges.append(edge)
                            nodes_with_edges.add(tech)
                            break
            
            # 3. 补充其他边，但限制总数
            remaining_edges = [e for e in candidate_edges if e not in edges]
            # 限制边的数量：最多 max_nodes * 2（避免图过于复杂）
            max_edges = min(len(edges) + len(remaining_edges), max_nodes * 2)
            edges.extend(remaining_edges[:max_edges - len(edges)])
            
            # 最终排序
            edges.sort(key=lambda x: x["weight"], reverse=True)
            
            result = {
                "nodes": nodes,
                "edges": edges,
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "cooccurrence_threshold": similarity_threshold,
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info("知识图谱构建完成（基于技术名词）", 
                       nodes=len(nodes), 
                       edges=len(edges),
                       technologies=len(selected_techs))
            
            return result
            
        except Exception as e:
            logger.error("知识图谱构建失败", error=str(e))
            return {
                "nodes": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }
    
    @staticmethod
    async def _build_architecture_graph(
        db,
        doc_data,
        similarity_threshold: float,
        max_nodes: int
    ) -> Dict:
        """
        构建架构视角的知识图谱（单文档模式）
        
        Args:
            db: 数据库会话
            doc_data: 文档数据
            similarity_threshold: 关联度阈值
            max_nodes: 最大节点数
        
        Returns:
            知识图谱数据字典
        """
        from app.services.architecture_analyzer import get_architecture_analyzer
        from app.services.entity_extractor import get_entity_extractor
        from sqlalchemy import select
        from app.models.system_learning_data import SystemLearningData
        from uuid import UUID
        
        try:
            doc_id = str(doc_data.document_id)
            processing_result = doc_data.result_data if isinstance(doc_data.result_data, dict) else {}
            
            # 获取文档内容
            doc_uuid = UUID(doc_id) if isinstance(doc_data.document_id, str) else doc_data.document_id
            sld_query = await db.execute(
                select(SystemLearningData.content_summary)
                .where(SystemLearningData.document_id == doc_uuid)
            )
            sld_data = sld_query.scalar_one_or_none()
            content = ""
            if sld_data and hasattr(sld_data, 'content_summary') and sld_data.content_summary:
                content = sld_data.content_summary
            
            # 获取组件和相关技术
            components = processing_result.get('components', [])
            related_technologies = processing_result.get('related_technologies', [])
            
            # 如果没有相关技术，从文档中提取
            if not related_technologies:
                extractor = get_entity_extractor()
                related_technologies = await extractor.extract_technologies_from_result(processing_result)
                if not related_technologies and content:
                    related_technologies = await extractor.extract_technologies_from_content(content[:2000])
            
            # 使用架构分析器分析技术栈
            analyzer = get_architecture_analyzer()
            analysis_result = await analyzer.analyze_architecture(
                content=content,
                components=components if isinstance(components, list) else None,
                related_technologies=related_technologies if isinstance(related_technologies, list) else None
            )
            
            technologies = analysis_result.get('technologies', [])
            relationships = analysis_result.get('relationships', [])
            summary = analysis_result.get('summary', '')
            
            # 限制技术数量
            technologies = technologies[:max_nodes]
            
            # 构建节点
            nodes = []
            tech_name_to_layer = {}
            for tech in technologies:
                tech_name = tech.get('name', '').strip()
                if not tech_name:
                    continue
                
                layer = tech.get('layer', 'other')
                layer_info = analyzer.ARCHITECTURE_LAYERS.get(layer, analyzer.ARCHITECTURE_LAYERS['other'])
                
                tech_name_to_layer[tech_name] = layer
                
                nodes.append({
                    "id": tech_name,
                    "label": tech_name,
                    "type": "technology",
                    "layer": layer,
                    "layer_name": layer_info['name'],
                    "layer_order": layer_info['order'],
                    "description": tech.get('description', ''),
                    "position": tech.get('position', ''),
                    "color": layer_info['color'],
                    "size": 40
                })
            
            # 构建边（上下游关系）
            edges = []
            for rel in relationships:
                from_tech = rel.get('from', '').strip()
                to_tech = rel.get('to', '').strip()
                rel_type = rel.get('type', 'integration')
                strength = rel.get('strength', 0.5)
                
                # 只包含已选中的技术
                if from_tech in tech_name_to_layer and to_tech in tech_name_to_layer:
                    if strength >= similarity_threshold:
                        edges.append({
                            "source": from_tech,
                            "target": to_tech,
                            "type": rel_type,
                            "relationship_strength": round(strength, 3),
                            "weight": round(strength, 3),
                            "label": rel.get('description', rel_type),
                            "description": rel.get('description', '')
                        })
            
            # 按层次排序节点
            nodes.sort(key=lambda x: (x.get('layer_order', 99), x.get('label', '')))
            
            result = {
                "nodes": nodes,
                "edges": edges,
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "summary": summary,
                "architecture_layers": {k: v['name'] for k, v in analyzer.ARCHITECTURE_LAYERS.items()},
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info("架构视角知识图谱构建完成", 
                       nodes=len(nodes), 
                       edges=len(edges),
                       summary=summary[:50] if summary else "")
            
            return result
            
        except Exception as e:
            logger.error("架构视角知识图谱构建失败", error=str(e))
            return {
                "nodes": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }
    
    @staticmethod
    def _get_tech_color(tech: str, layer: Optional[str] = None) -> str:
        """根据技术类型获取节点颜色"""
        tech_lower = tech.lower()
        
        # 编程语言
        if tech_lower in ['python', 'java', 'javascript', 'typescript', 'go', 'rust', 'c++', 'c#', 'php', 'ruby', 'swift', 'kotlin']:
            return "#3B82F6"  # 蓝色
        
        # 框架
        elif tech_lower in ['react', 'vue', 'angular', 'django', 'flask', 'spring', 'express', 'fastapi', 'laravel']:
            return "#10B981"  # 绿色
        
        # 数据库
        elif tech_lower in ['mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'sqlite', 'oracle']:
            return "#F59E0B"  # 橙色
        
        # 工具和平台
        elif tech_lower in ['docker', 'kubernetes', 'git', 'jenkins', 'aws', 'azure', 'gcp', 'nginx', 'apache']:
            return "#8B5CF6"  # 紫色
        
        # 其他
        else:
            return "#6B7280"  # 灰色


def get_knowledge_graph_builder() -> KnowledgeGraphBuilder:
    """获取知识图谱构建器实例（单例模式）"""
    return KnowledgeGraphBuilder()
