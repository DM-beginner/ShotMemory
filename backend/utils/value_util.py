class ValueUtil:
    @classmethod
    def coalesce(cls, *vals):
        """
        返回参数列表中**第一个不为 None 的值**；如果全部为 None，则返回 None。

        语义类似 SQL 的 `COALESCE`，常用于“取第一个可用值/默认值兜底”。
        """
        for val in vals:
            if val is not None:
                # 找到第一个有效值就立即返回
                return val
        # 都是 None：没有可用值
        return None
