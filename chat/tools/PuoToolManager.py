from typing import Literal, List, Optional

import requests
from langchain_core.tools import tool
from pydantic import Field

from requests import RequestException


class PuoToolManager:
    @staticmethod
    def _send_post_request_with_retry(url, payload, headers=None, max_retries=5):
       return "已查询到数据,这里是模拟场景，你可以随机编数据"



    # ==============================================
    # 2. 定义工具（对外提供的参数化接口）
    # ==============================================
    # --- 基础查询（查询 1-11）---
    @staticmethod
    @tool
    def menu_hert_node_on_rn(ver: str = Field(description="版本号 (如 24a)"),):
        """【意图1】rb上hert节点查询"""
        url = "http://cid-service.huawei.com/service-puo/continuous_delivery/read_file_rn"
        payload = {
            "int_ver": ver
        }
        response = PuoToolManager._send_post_request_with_retry(url, payload)
        return response

    @staticmethod
    @tool
    def query_trunk_mirror_info(ver: str = Field(description="版本号 (如 24a)"),):
        """【意图2】查询主干镜像的镜像信息"""
        url = "http://cid-service.huawei.com/service-puo/continuous_delivery/read_file_img"
        payload = {
            "int_ver": ver
        }
        response = PuoToolManager._send_post_request_with_retry(url, payload)
        return response

    @staticmethod
    @tool
    def query_bugfix_branch_info(
            ver: str = Field(description="版本号 (如 24a)"),
            branch_name: str = Field(description="Bugfix分支名 (必须包含 'hert_bugfix' 前缀)")
    ):
        """【意图3】查询 Bugfix 分支的镜像信息"""
        url = "http://cid-service.huawei.com/service-puo/continuous_delivery/read_bugfix_info"
        payload = {
            "int_ver": ver,
            "branch": branch_name
        }
        response = PuoToolManager._send_post_request_with_retry(url, payload)
        return response

    @staticmethod
    @tool
    def query_version_push_status(ver: str = Field(description="版本号 (如 24a)")):
        """【意图4】版本推送情况查询"""
        url = "http://cid-service.huawei.com/service-puo/continuous_delivery/inquire_ver_push"
        payload = {
            "int_ver": ver,
        }
        response = PuoToolManager._send_post_request_with_retry(url, payload)
        return response

    @staticmethod
    @tool
    def query_component_merge_status(
            search: str = Field(description="三方组件名称 (从列表选择)"),
            ver: str = Field(description="大版本号 (如 24a)")
    ):
        """【意图5】查询指定三方组件在该版本下的合入状态"""
        url = "http://cid-service.huawei.com/service-puo/continuous_delivery/inquire_components"
        payload = {
            "int_ver": ver,
            "search": search
        }
        response = PuoToolManager._send_post_request_with_retry(url, payload)
        return response

    @staticmethod
    @tool
    def query_version_basic_info(
            ver: str = Field(description="大版本号 (如 24a)"),
            search: str = Field(description="查询关键字。支持以下任意一种格式："
                                            "1. SPC版本号 (SPC开头)"
                                            "2. 备份工程名 (V开头)"
                                            "3. CM版本 (V开头)"
                                            "4. HERT BBU版本"
                                            "5.  数字和英文40位构建节点编号")
    ):
        """【意图6】查询每日构建版本的详细基本信息 (支持多种版本号格式)"""
        url = "http://cid-service.huawei.com/service-puo/continuous_delivery/inquire_daily_ver"
        payload = {
            "int_ver": ver,
            "search": search
        }
        response = PuoToolManager._send_post_request_with_retry(url, payload)
        return response

    @staticmethod
    @tool
    def query_version_by_multimode(search: str = Field(description="多模版本号 (必须以 BTS3900 开头)")):
        """【意图7】根据多模版本号查询版本基本信息"""
        url = "http://cid-service.huawei.com/service-puo/continuous_delivery/inquire_mode_ver"
        payload = {
            "search": search
        }
        response = PuoToolManager._send_post_request_with_retry(url, payload)
        return response

    @staticmethod
    @tool
    def query_spc_commercial_status(
            ver: str = Field(description="版本号 (如 24a)"),
            spc_ver: str = Field(description="SPC版本号 (以 SPC 开头)")
    ):
        """【意图8】查询SPC版本的商用状态"""
        url = "http://cid-service.huawei.com/service-puo/continuous_delivery/inquire_spc_ver"
        payload = {
            "int_ver": ver,
            "spc_ver": spc_ver
        }
        response = PuoToolManager._send_post_request_with_retry(url, payload)
        return response

    @staticmethod
    @tool
    def query_merge_info_between_versions(
            ver: str = Field(description="版本号 (如 24a)"),
            start_version: str = Field(description="起始版本 (V版本号 或 节点号)"),
            end_version: str = Field(description="终止版本 (V版本号 或 节点号)")
    ):
        """【意图9】查询两个版本之间的合入/差异信息"""
        url = "http://cid-service.huawei.com/service-puo/continuous_delivery/inquire_ver_merge"
        payload = {
            "int_ver": ver,
            "parameter_one": start_version,
            "parameter_two": end_version
        }
        response = PuoToolManager._send_post_request_with_retry(url, payload)
        return response

    @staticmethod
    @tool
    def query_mr_info(mr_url: str = Field(description="完整的 MR 链接 URL")):
        """【意图10】查询 Merge Request (MR) 详细信息"""
        url = "http://cid-service.huawei.com/service-puo/continuous_delivery/inquire_mr_info"
        payload = {
            "mr": mr_url
        }
        response = PuoToolManager._send_post_request_with_retry(url, payload)
        return response

    @staticmethod
    @tool
    def check_trunk_build_status(ver: str = Field(description="版本号 (如 24a)")):
        """【意图11】查询主干构建状态 (SmartCI)"""
        url = "http://cid-service.huawei.com/service-puo/continuous_delivery/inquire_smartci_info"
        payload = {
            "int_ver": ver
        }
        response = PuoToolManager._send_post_request_with_retry(url, payload)
        return response

    # --- 通过节点号查询三方组件配套信息 ---
    @staticmethod
    @tool
    def query_component_details(
            ver: str = Field(description="大版本号 (如 24a)"),
            search_key: str = Field(description="查询依据：支持 构建节点号、分支名 或 HERT版本号"),
            component_name: str = Field(None, description="三方组件名称")
    ):
        """【意图12】查询**三方组件**的版本配套信息。支持通过节点、分支或HERT版本进行查找。"""
        url = "http://cid-service.huawei.com/service-puo/continuous_delivery/read_file_components"
        payload = {
            "int_ver": ver,
            "search": search_key,
            "components": component_name
        }
        response = PuoToolManager._send_post_request_with_retry(url, payload)
        return response

    @staticmethod
    @tool
    def query_product_details(
            ver: str = Field(description="大版本号 (如 24a)"),
            search_key: str = Field(description="查询凭证：支持 构建节点号、分支名 或 HERT版本号"),
            product: str = Field(None, description="产品名称")
    ):
        """【意图13】查询**产品**配套版本信息。支持通过节点、分支或HERT版本进行查找。"""
        url = "http://cid-service.huawei.com/service-puo/continuous_delivery/read_file_matching"
        payload = {
            "int_ver": ver,
            "search": search_key,
            "mode_ver": product
        }
        response = PuoToolManager._send_post_request_with_retry(url, payload)
        return response


    @classmethod
    def get_tools_list(cls):
        """获取所有工具的列表"""
        return [
            cls.menu_hert_node_on_rn,
            cls.query_trunk_mirror_info,
            cls.query_bugfix_branch_info,
            cls.query_version_push_status,
            cls.query_component_merge_status,
            cls.query_version_basic_info,
            cls.query_version_by_multimode,
            cls.query_spc_commercial_status,
            cls.query_merge_info_between_versions,
            cls.query_mr_info,
            cls.check_trunk_build_status,
            cls.query_component_details,
            cls.query_product_details,

        ]