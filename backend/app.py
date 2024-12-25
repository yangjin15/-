from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import time
import os
from urllib.parse import urljoin, urlparse
import json
import io

app = Flask(__name__)
CORS(app)

@app.route('/proxy_image')
def proxy_image():
    url = request.args.get('url')
    referer = request.args.get('referer')
    
    if not url:
        return 'No URL provided', 400
        
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer
        }
        
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        return send_file(
            io.BytesIO(response.content),
            mimetype=response.headers['Content-Type'] if 'Content-Type' in response.headers else 'image/jpeg'
        )
        
    except Exception as e:
        return str(e), 500

# 设置请求头，模拟浏览器访问
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
}

def get_page_size(content):
    return len(content)

def is_valid_image_url(url):
    """检查URL是否是有效的图片URL"""
    # 检查是否是完整的URL
    if not url.startswith(('http://', 'https://')):
        return False
    
    # 检查是否以常见的图片扩展名结尾
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.ico')
    # B站特殊的图片URL格式
    bilibili_patterns = ('@', '.hdslb.com', '/bfs/')
    
    # 如果是B站的图片链接，特殊处理
    if any(pattern in url for pattern in bilibili_patterns):
        return True
    
    # 其他情况，检查是否以图片扩展名结尾
    return url.lower().endswith(image_extensions)

def extract_images(soup, base_url):
    images = []
    # 查找所有img标签
    for img in soup.find_all('img'):
        # 获取图片URL
        src = img.get('src') or img.get('data-src')
        if src:
            # 处理相对路��
            if not src.startswith(('http://', 'https://')):
                src = urljoin(base_url, src)
            if is_valid_image_url(src):
                images.append(src)
    
    # 特别处理B站视频封面图
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        content = og_image['content']
        if is_valid_image_url(content):
            images.append(content)
    
    # 处理视频缩略图
    for meta in soup.find_all('meta', {'itemprop': 'thumbnailUrl'}):
        if meta.get('content'):
            content = meta['content']
            if is_valid_image_url(content):
                images.append(content)
    
    # 从script标签中提取JSON数据
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict):
                # 提取缩略图URL
                thumbnail = data.get('thumbnailUrl')
                if thumbnail:
                    if isinstance(thumbnail, list):
                        images.extend([url for url in thumbnail if is_valid_image_url(url)])
                    elif is_valid_image_url(thumbnail):
                        images.append(thumbnail)
                # 提取图片URL
                image = data.get('image')
                if image:
                    if isinstance(image, list):
                        images.extend([url for url in image if is_valid_image_url(url)])
                    elif is_valid_image_url(image):
                        images.append(image)
        except:
            continue

    # 去重并过滤掉无效的URL
    images = list(dict.fromkeys([img for img in images if is_valid_image_url(img)]))
    return images

def extract_text(soup):
    # 移除script和style标签
    for script in soup(['script', 'style']):
        script.decompose()
    # 获取文本并清理
    text = ' '.join(soup.stripped_strings)
    return text

def crawl_url(url, max_size=None, content_type='all'):
    try:
        start_time = time.time()
        performance_metrics = {
            'dns_time': 0,
            'connect_time': 0,
            'response_time': 0,
            'download_time': 0,
            'parse_time': 0,
            'total_time': 0,
            'image_count': 0,
            'text_length': 0,
            'html_size': 0,
            'status_code': 0
        }
        
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Referer': 'https://www.bilibili.com',
            'Cookie': "buvid3=2B4AEB11-5E03-4F41-B288-D037739B4F6833232infoc"
        }
        
        # 记录DNS解析和连接时间
        dns_start = time.time()
        session = requests.Session()
        session.headers.update(headers)
        performance_metrics['dns_time'] = time.time() - dns_start
        
        # 记录响应时间
        response_start = time.time()
        response = session.get(url, timeout=10, verify=False)
        performance_metrics['response_time'] = time.time() - response_start
        performance_metrics['status_code'] = response.status_code
        response.raise_for_status()
        
        # 记录下载时间
        download_start = time.time()
        content = response.content
        performance_metrics['download_time'] = time.time() - download_start
        performance_metrics['html_size'] = len(content)
        
        if max_size and len(content) > max_size * 1024:
            return {
                'url': url,
                'size': len(content),
                'performance': performance_metrics,
                'status': f'页面超过最大大小限制 ({max_size}KB)'
            }

        # 记录解析时间
        parse_start = time.time()
        soup = BeautifulSoup(content, 'html.parser', from_encoding=response.apparent_encoding)
        performance_metrics['parse_time'] = time.time() - parse_start
        
        result = {
            'url': url,
            'size': len(content),
            'time': time.time() - start_time,
            'status': '成功',
            'performance': performance_metrics,
            'domain': urlparse(url).netloc,
            'content_type': response.headers.get('Content-Type', ''),
            'status_code': response.status_code,
            'headers': dict(response.headers)
        }

        if content_type == 'images':
            images = extract_images(soup, url)
            result['images'] = images
            result['image_count'] = len(images)
            performance_metrics['image_count'] = len(images)
        elif content_type == 'text':
            text = extract_text(soup)
            result['text'] = text
            result['text_length'] = len(text)
            performance_metrics['text_length'] = len(text)
        else:
            # 同时获取图片和文本
            images = extract_images(soup, url)
            text = extract_text(soup)
            result['images'] = images
            result['text'] = text
            result['image_count'] = len(images)
            result['text_length'] = len(text)
            performance_metrics['image_count'] = len(images)
            performance_metrics['text_length'] = len(text)

        performance_metrics['total_time'] = time.time() - start_time
        
        # 保存结果到文件
        save_result(result)
        
        return result

    except requests.exceptions.RequestException as e:
        error_result = {
            'url': url,
            'size': 0,
            'time': time.time() - start_time,
            'status': f'请求失败: {str(e)}',
            'error_type': type(e).__name__,
            'error_details': str(e),
            'domain': urlparse(url).netloc
        }
        return error_result
    except Exception as e:
        error_result = {
            'url': url,
            'size': 0,
            'time': time.time() - start_time,
            'status': f'失败: {str(e)}',
            'error_type': type(e).__name__,
            'error_details': str(e),
            'domain': urlparse(url).netloc
        }
        return error_result

def save_result(result):
    # 确保data目录存在
    if not os.path.exists('../data'):
        os.makedirs('../data')
    
    # 生成文件名
    domain = urlparse(result['url']).netloc
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    filename = f'../data/crawl_{domain}_{timestamp}.json'
    
    # 保存结果
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

@app.route('/crawl', methods=['POST'])
def crawl():
    data = request.get_json()
    urls = data.get('urls', '').strip().split('\n')
    max_size = data.get('maxSize', 1000)  # KB
    content_type = data.get('contentType', 'all')
    
    # 清理空行
    urls = [url.strip() for url in urls if url.strip()]
    
    if not urls:
        return jsonify({'error': '请输入要抓取的网址'}), 400
        
    results = []
    stats = {
        'total_urls': len(urls),
        'success_count': 0,
        'failed_count': 0,
        'total_size': 0,
        'total_time': 0,
        'avg_time_per_page': 0,
        'avg_size_per_page': 0,
        'domains': {},
        'error_types': {}
    }
    
    start_time = time.time()
    
    for url in urls:
        result = crawl_url(url, max_size, content_type)
        results.append(result)
        
        # 更新统计信息
        if result.get('status') == '成功':
            stats['success_count'] += 1
            stats['total_size'] += result.get('size', 0)
            
            # 按域名统计
            domain = urlparse(url).netloc
            if domain not in stats['domains']:
                stats['domains'][domain] = {
                    'count': 0,
                    'total_size': 0,
                    'total_time': 0,
                    'success_count': 0,
                    'failed_count': 0
                }
            stats['domains'][domain]['count'] += 1
            stats['domains'][domain]['total_size'] += result.get('size', 0)
            stats['domains'][domain]['total_time'] += result.get('time', 0)
            stats['domains'][domain]['success_count'] += 1
        else:
            stats['failed_count'] += 1
            error_type = result.get('error_type', 'Unknown')
            stats['error_types'][error_type] = stats['error_types'].get(error_type, 0) + 1
            
            domain = urlparse(url).netloc
            if domain not in stats['domains']:
                stats['domains'][domain] = {
                    'count': 0,
                    'total_size': 0,
                    'total_time': 0,
                    'success_count': 0,
                    'failed_count': 0
                }
            stats['domains'][domain]['count'] += 1
            stats['domains'][domain]['failed_count'] += 1
    
    stats['total_time'] = time.time() - start_time
    
    if stats['success_count'] > 0:
        stats['avg_time_per_page'] = stats['total_time'] / stats['success_count']
        stats['avg_size_per_page'] = stats['total_size'] / stats['success_count']
    
    # 计算每个域名的平均值
    for domain in stats['domains']:
        domain_stats = stats['domains'][domain]
        if domain_stats['success_count'] > 0:
            domain_stats['avg_time'] = domain_stats['total_time'] / domain_stats['success_count']
            domain_stats['avg_size'] = domain_stats['total_size'] / domain_stats['success_count']
    
    return jsonify({
        'results': results,
        'stats': stats
    })

if __name__ == '__main__':
    app.run(debug=True) 