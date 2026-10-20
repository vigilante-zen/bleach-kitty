#!/usr/bin/env python3
"""Rasterize code-native Plymouth graphics; keep the AI character artwork unchanged."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from PySide6.QtCore import QByteArray, QRectF
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent
app = QGuiApplication.instance() or QGuiApplication([])


def raster(svg, name, width, height):
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    if not renderer.isValid():
        raise ValueError(name)
    image = QImage(width, height, QImage.Format_ARGB32_Premultiplied); image.fill(0)
    painter = QPainter(image); renderer.render(painter, QRectF(0, 0, width, height)); painter.end()
    if not image.save(str(ROOT / 'theme/assets' / name)):
        raise RuntimeError(name)


def main():
    for suffix, color in [('orange', '#FF9D52')]:
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512"><g fill="none" stroke="{color}"><circle cx="256" cy="256" r="225" stroke-width="1" opacity=".16"/><circle cx="256" cy="256" r="208" stroke-width="2" stroke-dasharray="110 45 12 45" opacity=".55"/><circle cx="256" cy="256" r="190" stroke-width="1" stroke-dasharray="2 18" opacity=".32"/></g></svg>'''
        (ROOT / f'theme/assets/aura-{suffix}.svg').write_text(svg+'\n')
        raster(svg, f'aura-{suffix}.png', 512, 512)
        raster(f'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="28"><defs><linearGradient id="g" x2="0" y2="1"><stop stop-color="{color}" stop-opacity="0"/><stop offset="1" stop-color="{color}"/></linearGradient></defs><rect width="4" height="28" rx="2" fill="url(#g)"/></svg>', f'spark-{suffix}.png',4,28)
        raster(f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="4"><rect width="400" height="4" rx="2" fill="{color}"/></svg>', f'bar-{suffix}.png',400,4)
    raster('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="4"><rect width="400" height="4" rx="2" fill="#202838"/></svg>','bar-track.png',400,4)
    print('Rasterized aura, particles and progress graphics.')


if __name__ == '__main__':
    main()
