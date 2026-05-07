#!/usr/bin/env python3
"""
Скрипт для генерации иконок PWA разных размеров
"""
import os
from PIL import Image, ImageDraw, ImageFont
import math

# Размеры иконок для PWA
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

# Цвета темы
COLORS = {
    'primary': '#3b82f6',
    'secondary': '#1e40af',
    'background': '#0a0e17',
    'text': '#ffffff',
    'accent': '#10b981'
}

def hex_to_rgb(hex_color):
    """Convert hex color to RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_icon(size, output_dir):
    """Create an icon of specified size"""
    # Create image with gradient background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw circular background
    margin = size // 20
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=hex_to_rgb(COLORS['background']),
        outline=hex_to_rgb(COLORS['primary']),
        width=max(1, size // 40)
    )
    
    # Draw currency symbol (₽) or $ depending on size
    if size >= 96:
        # Draw $ symbol
        center_x, center_y = size // 2, size // 2
        radius = size // 4
        
        # Draw S shape
        points = []
        for i in range(100):
            t = i / 100 * 2 * math.pi * 1.5
            x = center_x + radius * math.cos(t) * 0.8
            y = center_y + radius * math.sin(t) * 0.5
            points.append((x, y))
        
        if len(points) > 1:
            draw.line(points, fill=hex_to_rgb(COLORS['primary']), width=max(2, size // 20))
        
        # Draw vertical line
        draw.line(
            [(center_x, center_y - radius),
             (center_x, center_y + radius)],
            fill=hex_to_rgb(COLORS['accent']),
            width=max(2, size // 20)
        )
    
    # Save icon
    icon_path = os.path.join(output_dir, f'icon-{size}x{size}.png')
    img.save(icon_path, 'PNG', optimize=True)
    print(f'Created icon: {icon_path}')
    return icon_path

def main():
    """Generate all PWA icons"""
    output_dir = os.path.join(os.path.dirname(__file__), 'web', 'static', 'icons')
    os.makedirs(output_dir, exist_ok=True)
    
    print(f'Generating PWA icons in {output_dir}...')
    
    for size in ICON_SIZES:
        create_icon(size, output_dir)
    
    print(f'Generated {len(ICON_SIZES)} icons')
    
    # Create favicon
    favicon_path = os.path.join(os.path.dirname(__file__), 'web', 'static', 'favicon.ico')
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw simple favicon
    draw.ellipse([4, 4, 60, 60], fill=hex_to_rgb(COLORS['background']))
    draw.ellipse([8, 8, 56, 56], fill=hex_to_rgb(COLORS['primary']))
    
    # Save as ICO
    img.save(favicon_path, format='ICO', sizes=[(64, 64)])
    print(f'Created favicon: {favicon_path}')

if __name__ == '__main__':
    main()