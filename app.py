# app.py
from flask import Flask, request, send_file, jsonify, make_response
from flask_cors import CORS
import yt_dlp
import io
import os

# 导入 ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT

app = Flask(__name__)

# 极其关键：显式且彻底地配置 CORS 允许源
CORS(app, resources={r"/api/*": {"origins": ["https://www.rui-palace.com", "http://localhost:5000"]}})

# 全局错误捕获，确保即使后端崩溃，也必须返回带有 CORS 的 JSON 响应，绝不给浏览器报 CORS 错误的机会
@app.errorhandler(Exception)
def handle_exception(e):
    response = jsonify({"error": f"Internal Server Error: {str(e)}"})
    response.status_code = 500
    # 强制手动追加 CORS 头部防止前端假拦截
    response.headers.add('Access-Control-Allow-Origin', 'https://www.rui-palace.com')
    return response

@app.route('/api/generate-pdf', methods=['POST', 'OPTIONS'])
def generate_pdf():
    # 处理 CORS 预检请求（Preflight Request）
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "https://www.rui-palace.com")
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response

    data = request.json
    if not data:
        return jsonify({"error": "No JSON data received"}), 400
        
    playlist_url = data.get('url')
    lang = data.get('lang', 'zh')
    
    if not playlist_url:
        return jsonify({"error": "No URL provided"}), 400

    # 1. 使用 yt-dlp 解析数据（加入了抗封锁和轻量化配置）
    ydl_opts = {
        'extract_flat': True,
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 15, # 限制超时，防止 Render 请求被挂起
        # 模拟浏览器行为，降低被 YouTube 限制的概率
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5'
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
            if 'entries' not in playlist_info or not playlist_info['entries']:
                return jsonify({"error": "No videos found in this playlist"}), 404
            
            playlist_title = playlist_info.get('title', 'Untitled Playlist')
            video_data = []
            for index, entry in enumerate(playlist_info['entries'], start=1):
                video_id = entry.get('id')
                title = entry.get('title', 'Unknown Video')
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                video_data.append((index, title, video_url))
    except Exception as e:
        # 如果解析失败，返回带有 CORS 的 500 错误
        response = jsonify({"error": f"YouTube extraction failed: {str(e)}"})
        response.status_code = 500
        response.headers.add('Access-Control-Allow-Origin', 'https://www.rui-palace.com')
        return response

    # 2. 在内存中生成 PDF
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )

    # 注册字体
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    
    local_font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'SourceHanSans-Regular.ttf')
    
    if os.path.exists(local_font_path):
        pdfmetrics.registerFont(TTFont('SourceHanSans', local_font_path))
        font_name = 'SourceHanSans'
    else:
        win_msyh = "C:\\Windows\\Fonts\\msyh.ttc"
        if os.path.exists(win_msyh):
            pdfmetrics.registerFont(TTFont('msyh', win_msyh))
            font_name = 'msyh'
        else:
            font_name = 'Helvetica'

    # 双语转换配置
    texts = {
        "zh": {
            "pdf_report_title": "YouTube 播放列表视频链接导出报告",
            "pdf_meta_type": "报告类型",
            "pdf_meta_type_val": "YouTube 视频链接集合 (交互式 PDF)",
            "pdf_meta_security": "安全机制",
            "pdf_meta_security_val": "Web API 安全渲染",
            "pdf_meta_tool": "生成工具",
            "pdf_meta_tool_val": "蕊宫专属定制工具 · 杏花微雨版",
            "pdf_playlist_label": "播放列表",
        },
        "en": {
            "pdf_report_title": "YouTube Playlist Export Report",
            "pdf_meta_type": "Report Type",
            "pdf_meta_type_val": "YouTube Playlist Links (Interactive PDF)",
            "pdf_meta_security": "Security",
            "pdf_meta_security_val": "Web API Secure Rendering",
            "pdf_meta_tool": "Generated via",
            "pdf_meta_tool_val": "Rui Palace Custom Tool · Apricot Blossom Edition",
            "pdf_playlist_label": "Playlist",
        }
    }[lang]

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'ReportTitle', parent=styles['Normal'], fontName=font_name, fontSize=20,
        textColor=colors.HexColor('#4A3E3D'), alignment=TA_LEFT, spaceAfter=15
    )
    meta_style = ParagraphStyle(
        'MetaInfo', parent=styles['Normal'], fontName=font_name, fontSize=9,
        textColor=colors.HexColor('#8C7A78'), leading=14, spaceAfter=20
    )
    playlist_style = ParagraphStyle(
        'PlaylistTitle', parent=styles['Normal'], fontName=font_name, fontSize=12,
        textColor=colors.HexColor('#4A3E3D'), leading=16, backColor=colors.HexColor('#FDF6F0'),
        borderColor=colors.HexColor('#F4D1C6'), borderWidth=1, borderPadding=12, spaceAfter=20, borderRadius=4
    )
    card_index_style = ParagraphStyle(
        'CardIndex', parent=styles['Normal'], fontName=font_name, fontSize=8,
        textColor=colors.HexColor('#4A3E3D'), backColor=colors.HexColor('#F4D1C6'), borderPadding=3, spaceAfter=6, borderRadius=3
    )
    card_title_style = ParagraphStyle(
        'CardTitle', parent=styles['Normal'], fontName=font_name, fontSize=11, leading=15, textColor=colors.HexColor('#202124'), spaceAfter=4
    )
    card_link_style = ParagraphStyle(
        'CardLink', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#D38A73'), leading=12
    )

    story = []
    story.append(Paragraph(texts["pdf_report_title"], title_style))
    story.append(Paragraph(
        f"<b>{texts['pdf_meta_type']}：</b>{texts['pdf_meta_type_val']}<br/>"
        f"<b>{texts['pdf_meta_security']}：</b>{texts['pdf_meta_security_val']}<br/>"
        f"<b>{texts['pdf_meta_tool']}：</b>{texts['pdf_meta_tool_val']}", 
        meta_style
    ))
    story.append(Paragraph(f"<b>{texts['pdf_playlist_label']}：</b>{playlist_title}", playlist_style))
    
    for index, title, url in video_data:
        hyperlink = f'<a href="{url}" color="#D38A73"><u>{url}</u></a>'
        card_flow = [
            Paragraph(f"VIDEO #{index:02d}", card_index_style),
            Paragraph(f"<b>{title}</b>", card_title_style),
            Paragraph(hyperlink, card_link_style),
            Spacer(1, 15)
        ]
        story.append(KeepTogether(card_flow))
        
    try:
        doc.build(story)
    except Exception as e:
        response = jsonify({"error": f"PDF Generation failed: {str(e)}"})
        response.status_code = 500
        response.headers.add('Access-Control-Allow-Origin', 'https://www.rui-palace.com')
        return response
    
    pdf_buffer.seek(0)
    
    # 3. 构造成功的返回响应，强制带上下载流和 CORS 头部
    response = make_response(send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Youtube_Playlist_Export.pdf"
    ))
    response.headers.add('Access-Control-Allow-Origin', 'https://www.rui-palace.com')
    return response

if __name__ == '__main__':
    app.run(port=5000, debug=True)
