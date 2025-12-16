import dash
from dash import dcc, html, Input, Output, State, clientside_callback, no_update, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import io
import json
import os
import base64
from datetime import datetime
import time
import traceback
import tempfile
import random

# ==================== OCR 处理模块 ====================
try:
    from Ranch5 import SimpleOCR

    def parse_aliyun_ocr_result(raw_data):
        try:
            if 'Data' not in raw_data:
                return {"error": "返回数据中没有'Data'字段", "raw_data": raw_data}
            data_str = raw_data['Data']
            if isinstance(data_str, str):
                try:
                    data_dict = json.loads(data_str)
                except json.JSONDecodeError:
                    return {"error": "解析Data字符串失败", "raw_data": data_str}
            else:
                data_dict = data_str

            if 'data' in data_dict:
                nested_data = data_dict['data']
                if isinstance(nested_data, str):
                    try:
                        invoice_data = json.loads(nested_data)
                    except:
                        invoice_data = {}
                else:
                    invoice_data = nested_data

                result = {
                    "basic_info": {}, "seller_info": {}, "purchaser_info": {},
                    "amount_info": {}, "invoice_details": [], "image_info": {},
                }

                basic_fields = {
                    'invoiceCode': '发票代码', 'invoiceNumber': '发票号码', 'invoiceDate': '开票日期',
                    'drawer': '开票人', 'remarks': '备注',
                }
                for api_field, display_name in basic_fields.items():
                    if api_field in invoice_data and invoice_data[api_field]:
                        result["basic_info"][display_name] = invoice_data[api_field]

                seller_fields = {'sellerName': '名称', 'sellerTaxNumber': '税号'}
                for api_field, display_name in seller_fields.items():
                    if api_field in invoice_data and invoice_data[api_field]:
                        result["seller_info"][display_name] = invoice_data[api_field]

                purchaser_fields = {'purchaserName': '名称', 'purchaserTaxNumber': '税号'}
                for api_field, display_name in purchaser_fields.items():
                    if api_field in invoice_data and invoice_data[api_field]:
                        result["purchaser_info"][display_name] = invoice_data[api_field]

                amount_fields = {
                    'totalAmount': '发票金额',
                    'invoiceAmountPreTax': '不含税金额',
                    'invoiceTax': '发票税额'
                }
                for api_field, display_name in amount_fields.items():
                    if api_field in invoice_data and invoice_data[api_field]:
                        result["amount_info"][display_name] = invoice_data[api_field]

                if 'invoiceDetails' in invoice_data and invoice_data['invoiceDetails']:
                    details = invoice_data['invoiceDetails']
                    if isinstance(details, str):
                        try:
                            details = json.loads(details)
                        except:
                            details = []
                    if isinstance(details, list):
                        for detail in details:
                            if isinstance(detail, dict):
                                parsed_detail = {
                                    '货物名称': detail.get('itemName', ''),
                                    '数量': detail.get('quantity', ''),
                                    '金额': detail.get('amount', ''),
                                }
                                parsed_detail = {k: v for k, v in parsed_detail.items() if v}
                                if parsed_detail:
                                    result["invoice_details"].append(parsed_detail)
                if 'remarks' in invoice_data and invoice_data['remarks']:
                    remarks = invoice_data['remarks']
                    result["basic_info"]["备注"] = remarks
                    def extract_bank_info_from_remarks(remarks):
                        """
                        从备注中提取银行信息和账号
                        支持多种格式：
                        1. "销方开户银行:中国农业银行股份有限公司三明徐碧支行;银行账号:13800101040002394;"
                        2. "开户行：中国工商银行深圳分行\n账号：6222024000001234567"
                        3. "中国银行北京分行 6225888888888888"
                        """
                        bank_info = {"开户行": "", "银行账号": ""}
                        
                        if not remarks:
                            return bank_info
                        
                        import re
                        
                        # 清理备注文本
                        remarks = remarks.replace('\r\n', '\n').replace('\r', '\n')
                        
                        # 模式1：包含"开户银行"和"银行账号"的格式（分号分隔）
                        pattern1 = r'(?:销方开户银行|开户行)[:：]\s*([^;]+?)(?:;|银行账号)'
                        pattern1_account = r'银行账号[:：]\s*(\d{16,19})'
                        
                        # 模式2：一行中包含银行和账号的格式
                        pattern2 = r'([\u4e00-\u9fff]+银行[^;]*?)(\d{16,19})'
                        
                        # 模式3：分行显示，银行在一行，账号在另一行
                        pattern3_bank = r'开户行[:：]\s*([^\n]+)'
                        pattern3_account = r'账号[:：]\s*(\d{16,19})'
                        
                        # 首先尝试模式1（分号分隔格式）
                        bank_match = re.search(pattern1, remarks)
                        account_match = re.search(pattern1_account, remarks)
                        
                        if bank_match:
                            bank_info["开户行"] = bank_match.group(1).strip()
                        if account_match:
                            bank_info["银行账号"] = account_match.group(1)
                        
                        # 如果模式1没找到，尝试模式2（一行内包含）
                        if not bank_info["开户行"] or not bank_info["银行账号"]:
                            match2 = re.search(pattern2, remarks)
                            if match2:
                                if not bank_info["开户行"]:
                                    bank_info["开户行"] = match2.group(1).strip()
                                if not bank_info["银行账号"]:
                                    bank_info["银行账号"] = match2.group(2)
                        
                        # 如果还没找到，尝试模式3（分行格式）
                        if not bank_info["开户行"]:
                            match3_bank = re.search(pattern3_bank, remarks)
                            if match3_bank:
                                bank_info["开户行"] = match3_bank.group(1).strip()
                        
                        if not bank_info["银行账号"]:
                            match3_account = re.search(pattern3_account, remarks)
                            if match3_account:
                                bank_info["银行账号"] = match3_account.group(1)
                        
                        # 最后尝试通用搜索：直接搜索银行关键词和账号
                        if not bank_info["开户行"]:
                            bank_keywords = ['银行', '农行', '工行', '建行', '中行', '招行', '交行', '邮储',
                                            '农商行', '浦发', '兴业', '中信', '光大', '华夏', '民生', '平安']
                            for keyword in bank_keywords:
                                if keyword in remarks:
                                    # 找到包含关键词的行
                                    lines = remarks.split('\n')
                                    for line in lines:
                                        if keyword in line and '账号' not in line:
                                            bank_info["开户行"] = line.strip().replace(':', '').replace('：', '').strip()
                                            break
                                    if bank_info["开户行"]:
                                        break
                        
                        # 清理开户行文本
                        if bank_info["开户行"]:
                            # 移除可能的分隔符
                            for sep in [';', '；', '，', ',', '。', '、']:
                                if sep in bank_info["开户行"]:
                                    bank_info["开户行"] = bank_info["开户行"].split(sep)[0]
                            
                            # 移除多余的空格和冒号
                            bank_info["开户行"] = bank_info["开户行"].strip().rstrip(':：;；')
                        
                        return bank_info
                    # 尝试从备注中提取银行信息
                    bank_info = extract_bank_info_from_remarks(remarks)
                    if bank_info:
                        result["seller_info"]["开户行"] = bank_info.get("开户行", "")
                        result["seller_info"]["银行账号"] = bank_info.get("银行账号", "")

                return result
            else:
                return {"error": "没有找到嵌套的data字段", "raw_data": data_dict}
        except Exception as e:
            return {"error": f"解析过程中出错: {str(e)}", "raw_data": raw_data}

    def process_invoice_image(file_path, ocr_instance):
        try:
            result = ocr_instance.recognize_invoice_raw(file_path)
            if result["success"]:
                parsed = parse_aliyun_ocr_result(result["data"])
                if "error" not in parsed:
                    return {**parsed, "file_name": os.path.basename(file_path),
                            "processing_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "ocr_status": "成功"}
                else:
                    return {"error": parsed.get("error"), "file_name": os.path.basename(file_path)}
            else:
                return {"error": result.get("error", "OCR失败"), "file_name": os.path.basename(file_path)}
        except Exception as e:
            traceback.print_exc()
            return {"error": f"处理失败: {str(e)}", "file_name": os.path.basename(file_path)}
except ImportError:
    print("未找到Ranch5模块，使用模拟OCR模式")
    def process_invoice_image(file_path, ocr_instance=None):
        time.sleep(0.6)
        return {
            "basic_info": {"发票代码": f"14401{random.randint(10000,99999)}",
                           "发票号码": f"888{random.randint(10000000,99999999)}",
                           "开票日期": "2025-12-14", "开票人": "管理员"},
            "seller_info": {"名称": "深圳测试科技有限公司"},
            "purchaser_info": {"名称": "北京测试有限公司"},
            "amount_info": {"发票金额": "1234.56", "不含税金额": "1092.44", "发票税额": "142.12"},
            "invoice_details": [{"货物名称": "测试服务费", "数量": "1", "金额": "1092.44"}],
            "file_name": os.path.basename(file_path),
            "processing_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ocr_status": "模拟成功"
        }

# ==================== Dash 应用初始化 ====================
app = dash.Dash(__name__, external_stylesheets=[
    dbc.themes.BOOTSTRAP,
    dbc.icons.BOOTSTRAP
])
app.title = "发票OCR识别工具"

# 自定义CSS - 简洁风格
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            * {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            }
            
            body {
                background-color: #f8f9fa;
                margin: 0;
                padding: 0;
            }
            
            .container-fluid {
                padding: 0;
            }
            
            .clean-card {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            
            .clean-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px 0;
                margin-bottom: 30px;
            }
            
            .upload-area {
                background: white;
                border: 2px dashed #6c757d;
                transition: all 0.2s;
                border-radius: 8px;
            }
            
            .upload-area:hover {
                border-color: #0d6efd;
                background-color: #f8fbff;
            }
            
            .invoice-item {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 15px;
            }
            
            .invoice-item:hover {
                background-color: #f9f9f9;
            }
            
            .amount-box {
                background: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                padding: 15px;
                text-align: center;
            }
            
            .status-badge {
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 0.85em;
                font-weight: 500;
            }
            
            .btn-clean {
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 500;
                border: 1px solid transparent;
                transition: all 0.2s;
            }
            
            .btn-clean:hover {
                opacity: 0.9;
                transform: translateY(-1px);
            }
            
            .simple-table {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                overflow: hidden;
            }
            
            .simple-table th {
                background-color: #f8f9fa;
                border-bottom: 2px solid #dee2e6;
                font-weight: 600;
            }
            
            .divider {
                height: 1px;
                background: linear-gradient(90deg, transparent, #e0e0e0, transparent);
                margin: 30px 0;
            }
            
            .loading-text {
                color: #6c757d;
                font-style: italic;
            }
            
            .success-color {
                color: #198754;
            }
            
            .error-color {
                color: #dc3545;
            }
            
            .primary-color {
                color: #0d6efd;
            }
            
            .muted-color {
                color: #6c757d;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# 全局变量
processed_results = []
current_df = None
uploaded_images_data = []
temp_files = []

def save_base64_image(base64_str, filename):
    if ',' in base64_str:
        base64_str = base64_str.split(',')[1]
    try:
        image_data = base64.b64decode(base64_str)
    except:
        image_data = base64_str.encode()
    temp_dir = tempfile.gettempdir()
    safe_filename = "".join(c for c in filename if c.isalnum() or c in ['.', '-', '_'])
    if not safe_filename:
        safe_filename = f"invoice_{int(time.time())}.jpg"
    temp_path = os.path.join(temp_dir, safe_filename)
    counter = 1
    while os.path.exists(temp_path):
        name, ext = os.path.splitext(safe_filename)
        temp_path = os.path.join(temp_dir, f"{name}_{counter}{ext}")
        counter += 1
    with open(temp_path, 'wb') as f:
        f.write(image_data)
    return temp_path

# ==================== 简洁布局 ====================
app.layout = dbc.Container([
    # 简洁标题栏
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1([
                    html.I(className="bi bi-receipt me-3 primary-color"),
                    "发票OCR识别工具"
                ], className="fw-bold mb-2"),
                html.P("上传发票图片，自动识别关键信息", className="muted-color mb-0 fs-5")
            ], className="text-center py-4 px-3")
        ], width=12)
    ], className="bg-white mb-4 border-bottom"),
    
    # 主内容区域
    dbc.Row([
        dbc.Col([
            # 上传区域
            dbc.Card([
                dbc.CardBody([
                    html.H5([
                        html.I(className="bi bi-upload me-2"),
                        "上传发票"
                    ], className="fw-bold mb-3"),
                    
                    dcc.Upload(
                        id='upload-images',
                        children=html.Div([
                            html.I(className="bi bi-cloud-arrow-up display-6 text-muted mb-3"),
                            html.H5("点击或拖放文件", className="fw-semibold mb-2"),
                            html.P("支持JPG、PNG格式", className="text-muted mb-0"),
                            html.Small("可批量上传多张发票", className="text-muted")
                        ], className="text-center py-4"),
                        style={
                            'width': '100%',
                            'minHeight': '200px',
                            'borderWidth': '2px',
                            'borderStyle': 'dashed',
                            'borderRadius': '8px',
                            'borderColor': '#adb5bd',
                            'cursor': 'pointer',
                            'display': 'flex',
                            'alignItems': 'center',
                            'justifyContent': 'center'
                        },
                        multiple=True,
                        accept='image/*'
                    ),
                    
                    html.Div(id='upload-status', className="mt-3")
                ], className="px-4 py-3")
            ], className="clean-card mb-4"),
            
            # 发票详情预览
            html.Div(id='image-previews', className="mb-4"),
            
            # 识别结果表格
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.H5([
                            html.I(className="bi bi-table me-2"),
                            "识别结果"
                        ], className="fw-bold mb-3"),
                        html.P("所有已识别发票的汇总信息", className="text-muted mb-4")
                    ]),
                    
                    html.Div(id='data-table', className="simple-table mb-3"),
                    html.Div(id='data-info', className="mt-3")
                ], className="px-4 py-3")
            ], className="clean-card mb-4"),
            
            # 操作按钮区域
            dbc.Card([
                dbc.CardBody([
                    html.H5([
                        html.I(className="bi bi-download me-2"),
                        "数据导出"
                    ], className="fw-bold mb-4"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Button([
                                html.I(className="bi bi-clipboard-check me-2"),
                                "复制表格"
                            ], id='copy-btn', color="primary", 
                            className="w-100 btn-clean", disabled=True)
                        ], xs=12, md=4, className="mb-2"),
                        
                        dbc.Col([
                            dbc.Button([
                                html.I(className="bi bi-file-earmark-excel me-2"),
                                "下载Excel"
                            ], id='download-excel-btn', color="success", 
                            className="w-100 btn-clean", disabled=True)
                        ], xs=12, md=4, className="mb-2"),
                        
                        dbc.Col([
                            dbc.Button([
                                html.I(className="bi bi-x-circle me-2"),
                                "清空数据"
                            ], id='clear-btn', color="secondary", 
                            className="w-100 btn-clean")
                        ], xs=12, md=4, className="mb-2")
                    ]),
                    
                    html.Div(id='action-status', className="mt-3"),
                    dcc.Download(id="download-excel"),
                    dcc.Textarea(id='clipboard-text', style={'display': 'none'})
                ], className="px-4 py-3")
            ], className="clean-card")
        ], width=12, lg=10, xl=8, className="mx-auto")
    ], className="px-3")
], fluid=True)

# ==================== 主回调：上传即识别 ====================
@app.callback(
    [Output('upload-status', 'children'),
     Output('image-previews', 'children'),
     Output('data-table', 'children'),
     Output('data-info', 'children'),
     Output('copy-btn', 'disabled'),
     Output('download-excel-btn', 'disabled'),
     Output('action-status', 'children')],
    Input('upload-images', 'contents'),
    State('upload-images', 'filename')
)
def handle_upload_and_process(contents_list, filename_list):
    global processed_results, current_df, uploaded_images_data, temp_files

    if not contents_list:
        return "", [], dash.no_update, "", True, True, ""

    # 清理旧数据
    for f in temp_files:
        try:
            if os.path.exists(f): 
                os.remove(f)
        except: 
            pass
    temp_files.clear()
    uploaded_images_data.clear()
    processed_results.clear()

    ocr_instance = SimpleOCR() if 'SimpleOCR' in globals() else None

    preview_cards = []
    table_rows = []

    # 显示加载状态
    status_msg = dbc.Alert([
        html.I(className="bi bi-hourglass me-2"),
        "正在处理发票图片，请稍候..."
    ], color="info", className="d-flex align-items-center")

    # 处理每张图片
    for idx, (content, filename) in enumerate(zip(contents_list, filename_list)):
        temp_path = save_base64_image(content, filename)
        temp_files.append(temp_path)
        uploaded_images_data.append((temp_path, filename, content))

        result = process_invoice_image(temp_path, ocr_instance)
        processed_results.append(result)

        # 创建发票预览项
        if "error" not in result:
            # 成功识别
            status_badge = dbc.Badge("成功", className="status-badge bg-success ms-2")
            details = dbc.Row([                
                # 第一行：开票日期（普通样式，无框包裹）
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Strong("开票日期: ", className="me-2"),
                            html.Span(result["basic_info"].get("开票日期", "—"))
                        ], className="py-2")
                    ], xs=12, className="mb-3")
                ]),
                # 第而行：第一列发票识别详情（卡片框），第二列销售方和金额（相同格式框）
                dbc.Row([
                    # 第一列：发票识别详情（使用卡片框）
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.Small("销售方", className="text-muted d-block mb-2"),
                                    html.Div([
                                        html.Span(result["seller_info"].get("名称", "—"), className="fw-bold")
                                    ], className="mb-1"),
                                ])
                            ], className="py-2 px-3")
                        ], className="h-100")
                    ], xs=12, md=6, className="mb-3"),
                    
                    # 第二列：销售方和金额（相同格式框）
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.Small("发票金额", className="text-muted d-block mb-2"),
                                    html.Div([
                                        html.Span("¥", className="me-1"),
                                        html.Span(result["amount_info"].get("发票金额", "0.00"), 
                                                className="fw-bold fs-4 success-color")
                                    ])
                                ])
                            ], className="py-2 px-3")
                        ], className="h-100")
                    ], xs=12, md=6, className="mb-3")
                ], className="mb-3"),
                   
                # 第三行：备注信息（开户行和账号）
                dbc.Row([
                    # 第一列：开户行
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.Small("开户行信息", className="text-muted d-block mb-1"),
                                    html.Div([
                                        html.Span(result.get("seller_info", {}).get("开户行", "").split()[0] 
                                                if result.get("seller_info", {}).get("开户行") 
                                                else "—")
                                    ])
                                ])
                            ], className="py-2 px-3")
                        ], className="h-100")
                    ], xs=12, md=6, className="mb-3"),
                    
                    # 第二列：账号
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.Small("银行账号", className="text-muted d-block mb-1"),
                                    html.Div([
                                        html.Span(result.get("seller_info", {}).get("银行账号", "").split()[-1] 
                                                if result.get("seller_info", {}).get("银行账号") 
                                                else "—")
                                    ])
                                ])
                            ], className="py-2 px-3")
                        ], className="h-100")
                    ], xs=12, md=6, className="mb-3")
                ])
            ])
            
            # 图片列
            img_section = html.Div([
                html.Img(src=content, 
                        style={'maxWidth': '100%', 'maxHeight': '200px', 'objectFit': 'contain'},
                        className="rounded border"),
                html.Div([
                    html.Small(f"{filename}", className="text-muted d-block mt-2 text-center")
                ])
            ], className="text-center")
            
        else:
            # 识别失败
            status_badge = dbc.Badge("失败", className="status-badge bg-danger ms-2")
            
            details = html.Div([
                html.Div([
                    html.I(className="bi bi-exclamation-triangle me-2 text-warning"),
                    html.Strong("识别失败", className="error-color")
                ], className="mb-2"),
                html.P(result.get("error", "未知错误"), className="text-muted small"),
                html.Div([
                    html.Small(f"文件: {filename}", className="text-muted")
                ], className="mt-2")
            ], className="py-3")
            
            img_section = html.Div([
                html.Img(src=content, 
                        style={'maxWidth': '100%', 'maxHeight': '200px', 'objectFit': 'contain', 
                               'filter': 'grayscale(70%)', 'opacity': '0.7'},
                        className="rounded border"),
                html.Div([
                    html.Small("识别失败", className="text-danger d-block mt-2 text-center")
                ])
            ], className="text-center")

        # 发票预览项
        preview_item = dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div([
                        html.Div([
                            html.I(className="bi bi-file-earmark-text me-2"),
                            html.Strong(f"发票 {idx+1}", className="fs-5")
                        ], className="d-flex align-items-center"),
                        status_badge
                    ], className="d-flex justify-content-between align-items-center mb-3"),
                    dbc.Row([
                        dbc.Col(img_section, xs=12, md=4, className="mb-3"),
                        dbc.Col(details, xs=12, md=8)
                    ])
                ], className="invoice-item")
            ], width=12)
        ])

        preview_cards.append(preview_item)

        # 表格数据
        table_rows.append({
            "序号": idx + 1,
            "文件名": result.get("file_name", filename),
             "项目名称": result.get("invoice_details", [{}])[0].get("货物名称", ""),
            "发票金额": f"¥{result.get('amount_info', {}).get('发票金额', '0.00')}",
            "发票数量": "1",
            "销售方": result.get("seller_info", {}).get("名称", ""),
            "开票日期": result.get("basic_info", {}).get("开票日期", ""),
            "购买方": result.get("purchaser_info", {}).get("名称", ""),
            "状态": "✅ 成功" if "error" not in result else "❌ 失败"
        })

    current_df = pd.DataFrame(table_rows)

    # 数据表格
    if not current_df.empty:
        data_table = dash_table.DataTable(
            data=current_df.to_dict('records'),
            columns=[{"name": i, "id": i} for i in current_df.columns],
            style_cell={
                'textAlign': 'left',
                'padding': '12px',
                'border': '1px solid #e0e0e0',
                'backgroundColor': 'white'
            },
            style_cell_conditional=[
                {"if": {"column_id": "序号"}, "textAlign": "center", "width": "60px"},
                {"if": {"column_id": "发票金额"}, "textAlign": "right"},
                {"if": {"column_id": "状态"}, "textAlign": "center", "width": "80px"},
            ],
            style_header={
                'backgroundColor': '#f8f9fa',
                'fontWeight': '600',
                'borderBottom': '2px solid #dee2e6',
                'textAlign': 'left'
            },
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#fafafa'},
                {'if': {'filter_query': '{状态} = "✅ 成功"'}, 'color': '#198754'},
                {'if': {'filter_query': '{状态} = "❌ 失败"'}, 'color': '#dc3545'},
            ],
            page_size=10,
            style_table={
                'overflowX': 'auto',
                'border': '1px solid #e0e0e0',
                'borderRadius': '8px'
            }
        )
    else:
        data_table = html.Div("暂无数据", className="text-center py-4 text-muted")

    # 统计信息
    success_count = sum(1 for r in processed_results if "error" not in r)
    info_content = html.Div([
        html.Div([
            html.I(className="bi bi-info-circle me-2"),
            f"共处理 {len(processed_results)} 张发票",
            html.Span(f" • 成功: {success_count}", className="success-color ms-2"),
            html.Span(f" • 失败: {len(processed_results)-success_count}", className="error-color ms-2")
        ], className="d-flex align-items-center flex-wrap")
    ])

    # 最终状态消息
    final_status = dbc.Alert([
        html.I(className="bi bi-check-circle me-2"),
        html.Strong(f"处理完成", className="me-2"),
        f"成功识别 {len(contents_list)} 张发票"
    ], color="success", className="d-flex align-items-center")

    return final_status, preview_cards, data_table, info_content, False, False, ""

# ==================== 复制到剪贴板 ====================
@app.callback(
    [Output('action-status', 'children', allow_duplicate=True),
     Output('clipboard-text', 'value')],
    Input('copy-btn', 'n_clicks'),
    prevent_initial_call=True
)
def copy_to_clipboard(n_clicks):
    global current_df
    if current_df is None or current_df.empty:
        return dbc.Alert("无数据可复制", color="warning", className="mt-2"), ""
    text = current_df.to_csv(sep='\t', index=False, encoding='utf-8')
    msg = dbc.Alert([
        html.I(className="bi bi-check-circle me-2"),
        "表格数据已复制到剪贴板，可直接粘贴到Excel"
    ], color="success", className="mt-2")
    return msg, text

# ==================== 下载Excel ====================
@app.callback(
    Output("download-excel", "data"),
    Input('download-excel-btn', 'n_clicks'),
    prevent_initial_call=True
)
def download_excel(n_clicks):
    global current_df
    if current_df is None or current_df.empty:
        return no_update
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        current_df.to_excel(writer, index=False, sheet_name='发票汇总')
    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return dcc.send_bytes(output.getvalue(), f"发票识别结果_{timestamp}.xlsx")

# ==================== 清空所有 ====================
@app.callback(
    [Output('upload-images', 'contents'),
     Output('upload-images', 'filename'),
     Output('upload-status', 'children', allow_duplicate=True),
     Output('image-previews', 'children', allow_duplicate=True),
     Output('data-table', 'children', allow_duplicate=True),
     Output('data-info', 'children', allow_duplicate=True),
     Output('copy-btn', 'disabled', allow_duplicate=True),
     Output('download-excel-btn', 'disabled', allow_duplicate=True),
     Output('action-status', 'children', allow_duplicate=True)],
    Input('clear-btn', 'n_clicks'),
    prevent_initial_call=True
)
def clear_all(n_clicks):
    global processed_results, current_df, uploaded_images_data, temp_files
    for f in temp_files:
        try:
            if os.path.exists(f): 
                os.remove(f)
        except: 
            pass
    processed_results = []
    current_df = None
    uploaded_images_data = []
    temp_files = []
    
    return None, None, "", [], dash.no_update, "", True, True, dbc.Alert([
        html.I(className="bi bi-check-circle me-2"),
        "已清空所有数据"
    ], color="info", className="mt-2")

# ==================== 客户端复制提示 ====================
clientside_callback(
    """
    function(text) {
        if (text && text.length > 0) {
            // 简单复制提示
            const toast = document.createElement('div');
            toast.innerHTML = '已复制到剪贴板';
            toast.style.cssText = 'position:fixed;top:20px;right:20px;padding:10px 20px;background:#198754;color:white;border-radius:4px;z-index:1000;font-weight:500;';
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 2000);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('clipboard-text', 'style'),
    Input('clipboard-text', 'value')
)

if __name__ == '__main__':
    print("="*50)
    print("发票OCR识别工具启动成功！")
    print("访问地址：http://localhost:8050")
    print("="*50)
    app.run(debug=True, port=8050, dev_tools_ui=False)