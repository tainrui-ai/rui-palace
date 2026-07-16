# app.py
from flask import Flask, request, send_file, jsonify
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
CORS(app)  # 解决跨域限制

# 修复处：移除了不支持的 name="generate-pdf" 参数
@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    data = request.json
    playlist_url = data.get('url')
    lang = data.get('lang', 'zh')
    
    if not playlist_url:
        return jsonify({"error": "No URL provided"}), 400

    # 1. 使用 yt-dlp 解析数据
    ydl_opts = {
        'extract_flat': True,
        'skip_download': True,
        'quiet': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
            if 'entries' not in playlist_info or not playlist_info['entries']:
                return jsonify({"error": "No videos found"}), 404
            
            playlist_title = playlist_info.get('title', 'Untitled Playlist')
            video_data = []
            for index, entry in enumerate(playlist_info['entries'], start=1):
                video_id = entry.get('id')
                title = entry.get('title', 'Unknown Video')
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                video_data.append((index, title, video_url))
    except Exception as e:
        return jsonify({"error": f"Parsing failed: {str(e)}"}), 500

    # 2. 在内存中生成 PDF，直接返回给浏览器下载
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )

    # 注册系统自带字体（确保支持中文字符）
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    
    # 兼容 Windows 和 Linux 的字体路径
    font_path = "C:\\Windows\\Fonts\\msyh.ttc"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('msyh', font_path))
        font_name = 'msyh'
    else:
        font_name = 'Helvetica' # 备用字体

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
        
    doc.build(story)
    
    pdf_buffer.seek(0)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Youtube_Playlist_Export.pdf"
    )

if __name__ == '__main__':
    app.run(port=5000, debug=True)