#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小学语文课文通关游戏构建工具

功能：
1. 读取game_config.json和HTML模板
2. 将图片转换为Base64嵌入
3. 生成单文件HTML课文通关游戏网页

参考：互动教学游戏生成器的build_game.py
"""

import json
import os
import sys
import base64
from io import BytesIO


def find_matching_image(desired_path, json_dir, images_dir="images"):
    """
    智能查找图片文件，支持模糊匹配
    当精确匹配失败时，尝试查找同名的不同扩展名文件
    """
    exact_path = os.path.join(json_dir, desired_path)
    if os.path.exists(exact_path):
        return exact_path
    
    filename = os.path.basename(desired_path)
    name_without_ext = os.path.splitext(filename)[0]
    
    images_path = os.path.join(json_dir, images_dir)
    if not os.path.exists(images_path):
        return None
    
    supported_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
    for file in os.listdir(images_path):
        file_name_without_ext = os.path.splitext(file)[0]
        file_ext = os.path.splitext(file)[1].lower()
        
        if file_name_without_ext == name_without_ext and file_ext in supported_extensions:
            matched_path = os.path.join(images_path, file)
            print(f"    智能匹配: {desired_path} → {file}")
            return matched_path
    
    return None


def compress_image(image_data, max_width=1920, quality=85, format='JPEG'):
    """
    使用Pillow压缩图片，如未安装则返回原始数据
    """
    try:
        from PIL import Image
        img = Image.open(BytesIO(image_data))
        
        original_size_mb = len(image_data) / (1024 * 1024)
        original_width = img.width
        
        if original_width <= max_width and original_size_mb < 1:
            print(f"    图片已优化: {original_width}x{img.height}, {original_size_mb:.2f}MB (无需压缩)")
            return base64.b64encode(image_data).decode('utf-8')
        
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
            print(f"    图片已缩放: {original_width}x{img.height} → {max_width}x{new_height}")
        
        if format == 'JPEG' and img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        output = BytesIO()
        img.save(output, format=format, quality=quality, optimize=True)
        compressed_data = output.getvalue()
        
        compressed_size_mb = len(compressed_data) / (1024 * 1024)
        compression_ratio = (1 - len(compressed_data) / len(image_data)) * 100
        print(f"    压缩完成: {compressed_size_mb:.2f}MB (节省 {compression_ratio:.1f}%)")
        return base64.b64encode(compressed_data).decode('utf-8')
        
    except ImportError:
        print("    警告: 未安装 Pillow 库，跳过图片压缩")
        return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        print(f"    警告: 图片压缩失败: {e}")
        return base64.b64encode(image_data).decode('utf-8')


def resolve_image_path(image_path, json_dir):
    """
    解析图片路径，返回绝对路径或None
    """
    if not image_path:
        return None
    
    if image_path.startswith("data:") or image_path.startswith("http"):
        return image_path
    
    if os.path.isabs(image_path) and os.path.exists(image_path):
        return image_path
    
    relative_path = os.path.join(json_dir, image_path)
    if os.path.exists(relative_path):
        return relative_path
    
    matched_path = find_matching_image(image_path, json_dir)
    if matched_path and os.path.exists(matched_path):
        return matched_path
    
    if os.path.exists(image_path):
        return image_path
    
    return None


def load_image_as_base64(image_path, json_dir, max_size_mb=5):
    """
    加载图片并返回base64字符串
    """
    resolved_path = resolve_image_path(image_path, json_dir)
    
    if not resolved_path or not os.path.exists(resolved_path):
        images_dir = os.path.join(json_dir, "images")
        available_files = []
        if os.path.exists(images_dir):
            available_files = [f for f in os.listdir(images_dir) 
                             if os.path.splitext(f)[1].lower() in ['.jpg', '.jpeg', '.png', '.webp', '.gif']]
        
        error_msg = f"图片未找到: {image_path}\n"
        error_msg += f"已尝试的路径:\n"
        error_msg += f"  - 绝对路径: {os.path.abspath(image_path)}\n"
        error_msg += f"  - 相对JSON目录: {os.path.join(json_dir, image_path)}\n"
        error_msg += f"  - 智能匹配: 已尝试查找同名不同扩展名的文件\n"
        
        if available_files:
            error_msg += f"\n可用的图片文件 (在 images/ 目录下):\n"
            for f in available_files:
                error_msg += f"  - images/{f}\n"
        else:
            error_msg += f"\n警告: images/ 目录不存在或为空"
        
        error_msg += f"\n解决方法:\n"
        error_msg += f"  1. 确保图片保存在 user-data/images/ 目录下\n"
        error_msg += f"  2. 检查 game_config.json 中的路径格式应为 'images/xxx.jpg'\n"
        
        raise FileNotFoundError(error_msg)
    
    ext = os.path.splitext(resolved_path)[1].lower().replace('.', '')
    if ext == 'jpg': 
        ext = 'jpeg'
    elif ext not in ['png', 'jpeg', 'webp', 'gif']:
        raise ValueError(f"不支持的图片格式: {ext}。仅支持 png, jpg, jpeg, webp")
    
    try:
        with open(resolved_path, "rb") as image_file:
            image_data = image_file.read()
            file_size_mb = len(image_data) / (1024 * 1024)
            
            if file_size_mb > max_size_mb:
                print(f"    警告: 图片 {os.path.basename(image_path)} 较大 ({file_size_mb:.2f}MB)")
            
            compressed_base64 = compress_image(image_data, max_width=1920, quality=85, 
                                               format='JPEG' if ext in ['jpg', 'jpeg'] else 'PNG')
            return f"data:image/{ext};base64,{compressed_base64}"
            
    except Exception as e:
        raise IOError(f"图片读取失败 {resolved_path}: {e}")


def build_game(json_path, template_path, output_path):
    """
    构建课文通关游戏HTML文件
    
    Args:
        json_path: game_config.json路径
        template_path: HTML模板路径
        output_path: 输出HTML文件路径
    """
    json_dir = os.path.dirname(os.path.abspath(json_path))
    
    print("=" * 60)
    print("小学语文课文通关游戏构建工具")
    print("=" * 60)
    print(f"配置文件: {json_path}")
    print(f"模板文件: {template_path}")
    print(f"输出文件: {output_path}")
    print("=" * 60)
    
    # 1. 加载游戏配置
    print("\n[步骤 1/5] 加载游戏配置...")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
        print("✓ 配置文件加载成功")
    except FileNotFoundError:
        raise FileNotFoundError(f"配置文件未找到: {json_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"配置文件格式错误: {e}")
    except Exception as e:
        raise Exception(f"加载配置文件失败: {e}")

    # 2. 验证数据结构
    print("\n[步骤 2/5] 验证数据结构...")
    required_fields = ["title", "intro", "start_scene_id", "scenes", "review"]
    for field in required_fields:
        if field not in game_data:
            raise ValueError(f"配置文件缺少必要字段: {field}")
    
    # 验证每个场景
    scene_images = {}
    for idx, scene in enumerate(game_data.get("scenes", [])):
        scene_id = scene.get("id", f"场景{idx+1}")
        
        if "image" not in scene or not scene["image"]:
            raise ValueError(f"场景 [{scene_id}] 缺少 image 字段")
        
        img_path = scene["image"]
        if img_path in scene_images:
            raise ValueError(
                f"场景图片重复: 场景 [{scene_id}] 和场景 [{scene_images[img_path]}] 使用了相同的图片"
            )
        scene_images[img_path] = scene_id
        
        choices = scene.get("choices", [])
        if len(choices) != 3:
            raise ValueError(f"场景 [{scene_id}] 选项数量错误: 期望 3 个，实际 {len(choices)} 个")
        
        correct_count = sum(1 for c in choices if c.get("is_correct", False))
        if correct_count != 1:
            raise ValueError(f"场景 [{scene_id}] 正确选项数量错误: 期望 1 个，实际 {correct_count} 个")
    
    print("✓ 数据结构验证通过")

    # 3. 处理图片（转为Base64）
    print("\n[步骤 3/5] 处理图片并转换为 Base64...")
    images_processed = 0
    
    # 处理封面图
    if "cover_image" in game_data and game_data["cover_image"]:
        try:
            print(f"  处理封面图: {game_data['cover_image']}")
            base64_img = load_image_as_base64(game_data["cover_image"], json_dir)
            game_data["cover_image"] = base64_img
            images_processed += 1
            print(f"  ✓ 封面图处理成功")
        except Exception as e:
            raise e
    
    # 处理场景图
    if "scenes" in game_data:
        for idx, scene in enumerate(game_data["scenes"]):
            if "image" in scene and scene["image"]:
                scene_id = scene.get("id", f"场景{idx+1}")
                try:
                    print(f"  处理场景图 [{scene_id}]: {scene['image']}")
                    base64_img = load_image_as_base64(scene["image"], json_dir)
                    scene["image"] = base64_img
                    images_processed += 1
                    print(f"  ✓ 场景图 [{scene_id}] 处理成功")
                except Exception as e:
                    raise e
    
    print(f"\n✓ 图片处理完成，共处理 {images_processed} 张图片")

    # 4. 加载模板
    print("\n[步骤 4/5] 加载模板...")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        print("✓ 模板加载成功")
    except FileNotFoundError:
        raise FileNotFoundError(f"模板文件未找到: {template_path}")
    except Exception as e:
        raise Exception(f"加载模板失败: {e}")

    # 5. 注入数据并生成输出
    print("\n[步骤 5/5] 生成最终 HTML 文件...")
    json_str = json.dumps(game_data, ensure_ascii=False)
    title = game_data.get("title", "课文通关游戏")
    
    output_content = template_content.replace("{{ title }}", title)
    output_content = output_content.replace("{{ game_data }}", json_str)

    try:
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        file_size = os.path.getsize(output_path)
        file_size_mb = file_size / (1024 * 1024)
        print(f"✓ 游戏文件生成成功")
        print(f"  文件路径: {os.path.abspath(output_path)}")
        print(f"  文件大小: {file_size_mb:.2f} MB")
    except Exception as e:
        raise Exception(f"写入输出文件失败: {e}")
    
    print("\n" + "=" * 60)
    print("构建完成！")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python build_game.py <json_config_path> <template_path> <output_html_path>")
        print("\n示例:")
        print("  python build_game.py user-data/game_config.json assets/game_template.html user-data/output_game.html")
        sys.exit(1)
    
    json_path = sys.argv[1]
    template_path = sys.argv[2]
    output_path = sys.argv[3]
    
    try:
        build_game(json_path, template_path, output_path)
    except Exception as e:
        print("\n" + "=" * 60)
        print("错误: 构建失败")
        print("=" * 60)
        print(f"错误详情: {e}")
        print("\n请检查以下内容:")
        print("  1. game_config.json 是否存在且格式正确")
        print("  2. 图片文件是否保存在 user-data/images/ 目录下")
        print("  3. JSON 中的图片路径是否为 'images/xxx.jpg' 格式")
        print("  4. 模板文件 assets/game_template.html 是否存在")
        sys.exit(1)
