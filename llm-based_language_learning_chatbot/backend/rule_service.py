import re
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import models

# ==========================================
# 1. 内存中的规则缓存
# ==========================================
_RULES_CACHE = []

async def load_rules_from_db(db: AsyncSession):
    """
    【热更新】从数据库读取所有启用规则，编译正则，更新到内存缓存。
    此函数应在系统启动时调用，以及管理员修改规则后调用。
    """
    global _RULES_CACHE
    print("🔄 正在从数据库重新加载高频规则库...")
    
    try:
        result = await db.execute(select(models.Rule).filter(models.Rule.active == True))
        rules_db = result.scalars().all()
        
        new_cache = []
        for r in rules_db:
            try:
                # 数据库存的是 JSON 字符串 '["a", "b"]' -> 解析为 Python list
                pattern_strs = json.loads(r.patterns)
                if not isinstance(pattern_strs, list):
                    pattern_strs = [str(pattern_strs)]
                
                # 预编译正则，忽略大小写
                compiled_patterns = [re.compile(p, re.IGNORECASE) for p in pattern_strs]
                
                new_cache.append({
                    "patterns": compiled_patterns,
                    "answer": r.answer,
                    "source": r.source
                })
            except Exception as e:
                print(f"❌ 规则 ID {r.id} 加载失败: {e}")
                
        _RULES_CACHE = new_cache
        print(f"✅ 规则库加载完成，当前生效规则数: {len(_RULES_CACHE)}")
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")

# ==========================================
# 2. 种子规则（供数据库首次初始化使用）
# ==========================================
def get_default_seed_rules():
    """提供系统首次启动时的初始数据"""
    return [
        (
            [r"借款.*诉讼时效", r"欠钱.*多久.*起诉"], 
            "根据《民法典》第一百八十八条，向人民法院请求保护民事权利的诉讼时效期间为三年。诉讼时效期间自权利人知道或者应当知道权利受到损害以及义务人之日起计算。",
            "《民法典》第一百八十八条"
        ),
        (
            [r"利息.*上限", r"高利贷.*标准", r"年利率.*多少"],
            "根据最高人民法院规定，借贷双方约定的利率未超过合同成立时一年期贷款市场报价利率（LPR）四倍的，人民法院应予支持。超过部分不予保护。",
            "最高法《关于审理民间借贷案件适用法律若干问题的规定》"
        ),
        (
            [r"客服.*电话", r"联系.*管理员", r"人工.*服务"],
            "我们的法律援助热线是：400-888-8888。工作时间：周一至周五 9:00-18:00。",
            "平台服务指南"
        ),
        (
            [r"杀人.*判几年", r"故意杀人.*刑期"],
            "根据《刑法》第二百三十二条，故意杀人的，处死刑、无期徒刑或者十年以上有期徒刑；情节较轻的，处三年以上十年以下有期徒刑。",
            "《刑法》第二百三十二条"
        )
    ]

# ==========================================
# 3. 规则匹配引擎
# ==========================================
def check_rules(user_query: str):
    """
    规则匹配引擎：直接使用从数据库加载到内存的 _RULES_CACHE，实现毫秒级响应。
    """
    global _RULES_CACHE
    for rule in _RULES_CACHE:
        for pattern in rule["patterns"]:
            if pattern.search(user_query):
                return rule["answer"], rule["source"]
    return None, None