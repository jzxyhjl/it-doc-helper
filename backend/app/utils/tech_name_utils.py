"""
技术名词工具函数
- 清理技术名词中的中文翻译
- 标准化技术名称用于去重
- 使用AI判断技术名称是否等价
- 统一处理逻辑
"""
import re
from typing import Optional


def normalize_tech_name(tech_name: str) -> str:
    """
    标准化技术名称，用于去重比较
    
    移除组织前缀和标准化格式，使得：
    - "Apache RocketMQ" 和 "RocketMQ" 被认为是同一个
    - "Spring Boot" 和 "SpringBoot" 被认为是同一个
    - "Spring Cloud Stream" 和 "spring-cloud-stream" 被认为是同一个
    
    注意：Spring 本身是一种技术，不是前缀，所以不会被移除。
    
    Args:
        tech_name: 原始技术名称
        
    Returns:
        标准化后的技术名称（用于比较）
    """
    if not tech_name:
        return ""
    
    # 先清理翻译
    cleaned = clean_tech_name(tech_name)
    
    # 转换为小写
    normalized = cleaned.lower().strip()
    
    # 只移除真正的组织前缀（不包括技术名称本身）
    # 按长度从长到短排序，优先匹配更长的前缀
    org_prefixes = [
        "apache ",
        "google ",
        "microsoft ",
        "oracle ",
        "ibm ",
        "netflix ",
        "facebook ",
        "twitter ",
        "alibaba ",
        "amazon ",
        "red hat ",
        "redhat ",
    ]
    
    for prefix in org_prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
            break
    
    # 统一格式：移除空格、连字符和下划线
    # 这样 "Spring Boot" 和 "SpringBoot" 和 "spring-boot" 都会变成 "springboot"
    normalized = re.sub(r'[\s\-_]+', '', normalized)
    
    return normalized


def clean_tech_name(tech_name: str) -> str:
    """
    清理技术名词，移除括号中的中文翻译
    
    Args:
        tech_name: 原始技术名词（可能包含中文翻译）
        
    Returns:
        清理后的技术名词（只保留英文）
    
    Examples:
        >>> clean_tech_name("Spring Boot（春波特）")
        "Spring Boot"
        >>> clean_tech_name("RocketMQ - 消息队列")
        "RocketMQ"
        >>> clean_tech_name("Spring Boot（春波特")
        "Spring Boot"
        >>> clean_tech_name("Spring Boot — 春波特")
        "Spring Boot"
    """
    if not tech_name:
        return ""
    
    cleaned = tech_name.strip()
    
    # 移除各种括号及其内部的中文内容（包括未闭合的括号）
    # 匹配：中文括号、英文括号、全角括号，以及它们内部的中文、字母、数字、空格
    cleaned = re.sub(r'[\uff08(（][\u4e00-\u9fa5\w\s]*[\uff09)]?', '', cleaned)
    
    # 移除破折号后的中文翻译（包括短破折号、长破折号、全角破折号）
    # 只移除包含中文的部分，不移除纯英文技术名称
    # 匹配：破折号 + 空格 + 中文内容（可能包含一些英文单词）
    cleaned = re.sub(r'\s*[-–—]\s*[\u4e00-\u9fa5]+[\u4e00-\u9fa5\w\s]*$', '', cleaned)
    
    # 移除末尾可能残留的括号
    cleaned = re.sub(r'[\uff08(（][\u4e00-\u9fa5\w\s]*$', '', cleaned)
    
    return cleaned.strip()


async def are_tech_names_equivalent(name1: str, name2: str) -> bool:
    """
    使用AI判断两个技术名称是否指向同一个技术
    
    当标准化名称无法确定时，可以使用AI来判断。
    例如：
    - "Apache RocketMQ" 和 "RocketMQ" -> True
    - "Spring Boot" 和 "SpringBoot" -> True
    - "MySQL" 和 "PostgreSQL" -> False
    
    Args:
        name1: 第一个技术名称
        name2: 第二个技术名称
        
    Returns:
        True 如果两个名称指向同一个技术，False 否则
    """
    if not name1 or not name2:
        return False
    
    # 先尝试标准化比较（快速路径）
    norm1 = normalize_tech_name(name1)
    norm2 = normalize_tech_name(name2)
    if norm1 == norm2:
        return True
    
    # 如果标准化后相同，直接返回True
    if norm1 and norm2 and norm1 == norm2:
        return True
    
    # 如果标准化后差异很大，可能不是同一个技术
    # 计算相似度（简单的字符重叠度）
    if norm1 and norm2:
        # 如果标准化后的名称长度差异很大，可能不是同一个
        len_diff = abs(len(norm1) - len(norm2)) / max(len(norm1), len(norm2))
        if len_diff > 0.5:  # 长度差异超过50%，可能不是同一个
            return False
    
    # 使用AI判断（异步调用）
    try:
        from app.services.ai_service import get_ai_service
        
        ai_service = get_ai_service()
        
        prompt = f"""请判断以下两个技术名称是否指向同一个技术或框架。

技术名称1: {name1}
技术名称2: {name2}

请只返回 JSON 格式：
{{"is_same": true/false, "reason": "简短原因"}}

注意：
- 如果两个名称是同一个技术的不同写法（如 "Apache RocketMQ" 和 "RocketMQ"），返回 true
- 如果两个名称是同一个技术的不同格式（如 "Spring Boot" 和 "SpringBoot"），返回 true
- 如果两个名称是完全不同的技术，返回 false
- 如果两个名称是相关但不同的技术（如 "Spring" 和 "Spring Boot"），返回 false"""
        
        result = await ai_service.generate_json(
            prompt=prompt,
            system_prompt="你是一个技术专家，擅长识别技术名称的等价关系。只返回JSON格式的答案。",
            temperature=0.1  # 低温度，更确定性
        )
        
        if isinstance(result, dict):
            return result.get("is_same", False)
        else:
            return False
            
    except Exception as e:
        # AI调用失败，回退到标准化比较
        import structlog
        logger = structlog.get_logger()
        logger.warning("AI判断技术名称等价性失败，使用标准化比较", 
                      name1=name1, name2=name2, error=str(e))
        return norm1 == norm2 if norm1 and norm2 else False

