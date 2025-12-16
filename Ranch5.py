# -*- coding: utf-8 -*-
"""
阿里云OCR发票识别模块 - 简化版
只负责接收文件和实现OCR功能，返回原始数据
Author: Your Name
Version: 2.0.1 - 修复错误处理
"""

import os
import sys
from typing import Dict, Optional, Tuple, Any

from alibabacloud_ocr_api20210707.client import Client as OcrClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_darabonba_stream.client import Client as StreamClient
from alibabacloud_ocr_api20210707 import models as ocr_api_20210707_models
from alibabacloud_tea_util import models as util_models


class SimpleOCR:
    """阿里云OCR简化类 - 只返回原始数据"""
    
    def __init__(self, access_key_id: str = None, access_key_secret: str = None, 
                 endpoint: str = 'ocr-api.cn-hangzhou.aliyuncs.com'):
        """
        初始化OCR客户端
        
        Args:
            access_key_id: AccessKey ID，如果为None则从环境变量获取
            access_key_secret: AccessKey Secret，如果为None则从环境变量获取
            endpoint: API端点，默认为发票OCR服务端点
        """
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.endpoint = endpoint
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化阿里云OCR客户端"""
        # 获取AccessKey
        ak_id, ak_secret = self._get_credentials()
        
        if not ak_id or not ak_secret:
            raise ValueError("未找到有效的AccessKey")
        
        # 创建配置
        config = open_api_models.Config(
            access_key_id=ak_id,
            access_key_secret=ak_secret
        )
        config.endpoint = self.endpoint
        
        # 创建客户端
        self.client = OcrClient(config)
    
    def _get_credentials(self) -> Tuple[str, str]:
        """
        获取AccessKey凭证
        
        Returns:
            Tuple[access_key_id, access_key_secret]
        """
        # 优先使用传入的参数
        if self.access_key_id and self.access_key_secret:
            return self.access_key_id, self.access_key_secret
        
        # 其次使用环境变量
        env_ak_id = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID')
        env_ak_secret = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
        
        if env_ak_id and env_ak_secret:
            return env_ak_id, env_ak_secret
        
        # 返回空值
        return None, None
    
    def validate_file(self, file_path: str, max_size_mb: int = 10) -> Dict[str, Any]:
        """
        验证文件是否有效，返回验证结果
        
        Args:
            file_path: 文件路径
            max_size_mb: 最大文件大小(MB)
            
        Returns:
            Dict: 验证结果，包含验证状态和消息
        """
        result = {
            "valid": False,
            "message": "",
            "file_size_mb": 0,
            "file_extension": ""
        }
        
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                result["message"] = f"文件不存在: {file_path}"
                return result
            
            # 检查文件是否可读
            if not os.access(file_path, os.R_OK):
                result["message"] = f"文件不可读: {file_path}"
                return result
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            result["file_size_mb"] = file_size / 1024 / 1024
            
            # 检查文件大小
            max_size_bytes = max_size_mb * 1024 * 1024
            if file_size > max_size_bytes:
                result["message"] = f"文件过大 ({result['file_size_mb']:.2f}MB)，请使用小于{max_size_mb}MB的文件"
                return result
            
            # 检查文件扩展名
            valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.pdf']
            file_ext = os.path.splitext(file_path)[1].lower()
            result["file_extension"] = file_ext
            
            if file_ext not in valid_extensions:
                result["message"] = f"不支持的文件格式: {file_ext}，支持的格式: {', '.join(valid_extensions)}"
                return result
            
            # 验证通过
            result["valid"] = True
            result["message"] = "文件验证通过"
            return result
            
        except Exception as e:
            result["message"] = f"文件验证过程中发生错误: {str(e)}"
            return result
    
    def recognize_invoice_raw(self, file_path: str, validate: bool = True) -> Dict[str, Any]:
        """
        识别发票图片，返回原始数据
        
        Args:
            file_path: 图片文件路径
            validate: 是否验证文件
            
        Returns:
            Dict: 包含识别结果或错误信息
                - 成功: {"success": True, "data": raw_data, "file_info": {...}}
                - 失败: {"success": False, "error": error_message, "file_info": {...}}
        """
        result = {
            "success": False,
            "file_info": {
                "path": file_path,
                "exists": os.path.exists(file_path) if os.path.exists(file_path) else False
            }
        }
        
        try:
            # 文件验证
            if validate:
                validation = self.validate_file(file_path)
                result["validation"] = validation
                
                if not validation["valid"]:
                    result["error"] = validation["message"]
                    return result
            
            # 读取文件
            body_stream = StreamClient.read_from_file_path(file_path)
            
            # 创建请求
            recognize_invoice_request = ocr_api_20210707_models.RecognizeInvoiceRequest(
                body=body_stream
            )
            
            runtime = util_models.RuntimeOptions()
            
            # 调用API
            response = self.client.recognize_invoice_with_options(
                recognize_invoice_request, runtime
            )
            
            # 转换为字典
            raw_data = response.body.to_map()
            
            # 成功返回
            result["success"] = True
            result["data"] = raw_data
            
            # 添加文件信息
            if os.path.exists(file_path):
                result["file_info"]["size_bytes"] = os.path.getsize(file_path)
                result["file_info"]["size_mb"] = os.path.getsize(file_path) / 1024 / 1024
                result["file_info"]["extension"] = os.path.splitext(file_path)[1].lower()
            
            return result
            
        except Exception as e:
            # 错误处理 - 确保error字段是字典
            error_info = {
                "type": type(e).__name__,
                "message": str(e)
            }
            
            # 添加阿里云API特定的错误信息
            try:
                if hasattr(e, 'message'):
                    error_info["api_message"] = str(e.message)
                
                if hasattr(e, 'code'):
                    error_info["api_code"] = str(e.code)
                
                if hasattr(e, 'data') and isinstance(e.data, dict):
                    error_info["api_data"] = e.data
            except:
                # 忽略提取错误信息的异常
                pass
            
            result["error"] = error_info
            return result
    
    def check_credentials(self) -> Dict[str, Any]:
        """
        检查凭证是否有效
        
        Returns:
            Dict: 检查结果
        """
        result = {
            "valid": False,
            "source": "unknown",
            "message": ""
        }
        
        try:
            # 尝试获取凭证
            ak_id, ak_secret = self._get_credentials()
            
            if not ak_id or not ak_secret:
                result["message"] = "未找到AccessKey凭证"
                return result
            
            # 判断凭证来源
            if self.access_key_id and self.access_key_secret:
                result["source"] = "parameter"
            elif os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID') and os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET'):
                result["source"] = "environment"
            else:
                result["source"] = "unknown"
            
            # 检查凭证格式（基本检查）
            if len(ak_id) < 10 or len(ak_secret) < 10:
                result["message"] = "AccessKey格式可能不正确"
                return result
            
            result["valid"] = True
            result["message"] = f"凭证有效（来源: {result['source']}）"
            result["access_key_id_length"] = len(ak_id)
            
            return result
            
        except Exception as e:
            result["message"] = f"检查凭证时出错: {str(e)}"
            return result
    
    @staticmethod
    def print_raw_result(result: Dict[str, Any], verbose: bool = False):
        """
        打印原始结果（简单格式化）
        
        Args:
            result: recognize_invoice_raw返回的结果
            verbose: 是否显示详细信息
        """
        print("\n" + "=" * 60)
        print("OCR识别结果")
        print("=" * 60)
        
        if result.get("success", False):
            print("✓ 识别成功")
            
            if verbose:
                print(f"\n文件信息:")
                for key, value in result.get("file_info", {}).items():
                    print(f"  {key}: {value}")
                
                if "validation" in result:
                    print(f"\n验证信息:")
                    for key, value in result["validation"].items():
                        print(f"  {key}: {value}")
            
            print(f"\n原始数据已返回")
            
            # 安全地获取data字段
            data = result.get("data")
            if data and isinstance(data, dict):
                data_keys = list(data.keys())
                print(f"数据字段: {data_keys}")
                
                # 简要显示data结构
                if 'Data' in data:
                    inner_data = data['Data']
                    if isinstance(inner_data, dict):
                        data_fields = list(inner_data.keys())
                        print(f"Data字段数量: {len(data_fields)}")
                        if data_fields:
                            display_fields = data_fields[:10]
                            print(f"主要字段: {', '.join(display_fields)}{'...' if len(data_fields) > 10 else ''}")
                    else:
                        print(f"Data字段类型: {type(inner_data).__name__}")
                else:
                    print("警告: 返回数据中没有'Data'字段")
            else:
                print(f"警告: 返回的data字段类型为 {type(data).__name__}")
            
        else:
            print("✗ 识别失败")
            
            if verbose:
                print(f"\n文件信息:")
                for key, value in result.get("file_info", {}).items():
                    print(f"  {key}: {value}")
            
            print(f"\n错误信息:")
            error_info = result.get("error", {})
            
            # 安全地处理错误信息
            if isinstance(error_info, str):
                print(f"  {error_info}")
            elif isinstance(error_info, dict):
                for key, value in error_info.items():
                    if key == "api_data" and isinstance(value, dict):
                        print(f"  API数据:")
                        for k, v in value.items():
                            print(f"    {k}: {v}")
                    else:
                        print(f"  {key}: {value}")
            else:
                print(f"  错误类型: {type(error_info).__name__}")
                print(f"  错误内容: {error_info}")
            
            # 显示阿里云特定的错误信息
            if isinstance(error_info, dict) and "api_data" in error_info:
                api_data = error_info["api_data"]
                if isinstance(api_data, dict):
                    if "Recommend" in api_data:
                        print(f"\n诊断地址: {api_data.get('Recommend')}")
                    if "Code" in api_data:
                        print(f"错误代码: {api_data.get('Code')}")
                    if "Message" in api_data:
                        print(f"错误消息: {api_data.get('Message')}")
        
        print("\n" + "=" * 60)


# 命令行接口 - 修复错误处理
def main():
    """命令行入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='阿里云OCR发票识别工具 - 简化版（返回原始数据）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s invoice.jpg            # 识别发票
  %(prog)s invoice.jpg --verbose  # 显示详细信息
  %(prog)s invoice.jpg --no-validate  # 跳过文件验证
  %(prog)s --check-cred           # 检查凭证
        """
    )
    
    parser.add_argument(
        'file_path',
        nargs='?',
        help='发票图片文件路径'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='显示详细信息'
    )
    
    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='跳过文件验证'
    )
    
    parser.add_argument(
        '--check-cred',
        action='store_true',
        help='检查凭证配置'
    )
    
    args = parser.parse_args()
    
    try:
        # 创建OCR实例
        ocr = SimpleOCR()
        
        # 检查凭证
        if args.check_cred:
            print("检查凭证配置...")
            cred_result = ocr.check_credentials()
            print(f"凭证状态: {'有效' if cred_result['valid'] else '无效'}")
            print(f"凭证来源: {cred_result['source']}")
            print(f"消息: {cred_result['message']}")
            
            if not cred_result['valid']:
                print("\n配置方法:")
                print("1. 设置环境变量:")
                print('   set ALIBABA_CLOUD_ACCESS_KEY_ID=your_id')
                print('   set ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_secret')
                print("\n2. 或在代码中传入:")
                print('   ocr = SimpleOCR(access_key_id="your_id", access_key_secret="your_secret")')
            
            return
        
        # 检查文件路径
        if not args.file_path:
            parser.print_help()
            print(f"\n错误: 必须指定文件路径")
            return
        
        print(f"阿里云OCR发票识别工具 - 简化版 v2.0.1")
        print(f"文件: {args.file_path}")
        
        # 识别发票
        result = ocr.recognize_invoice_raw(
            args.file_path, 
            validate=not args.no_validate
        )
        
        # 打印结果
        ocr.print_raw_result(result, verbose=args.verbose)
        
        # 如果成功，返回原始数据（可以用于进一步处理）
        if result.get("success", False):
            return result.get("data")
        
    except ValueError as e:
        print(f"配置错误: {e}")
        print("请设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        return None
    except Exception as e:
        print(f"程序错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    main()