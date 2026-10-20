#!/usr/bin/env python3
"""Desktop animation preview; never starts Plymouth or takes over a console."""
import argparse
import math
import os
from pathlib import Path
import random
import sys
from PySide6.QtCore import QElapsedTimer, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

ROOT = Path(__file__).resolve().parent


class Scene:
    def __init__(self):
        self.images = {path.stem: QImage(str(path)) for path in (ROOT / 'theme/assets').glob('*.png')}
        if any(image.isNull() for image in self.images.values()):
            raise ValueError('Invalid preview asset')
        rng = random.Random(7)
        self.particles = [(rng.random(), rng.random()-.5, .05+rng.random()*.1, 8+rng.random()*17) for _ in range(18)]

    def draw(self, painter, width, height, mode, time):
        painter.fillRect(0, 0, width, height, QColor('#090C12'))
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        scale = min(height/1080, width/1600, 1)
        cx, cy = width/2, height*.40
        color = 'orange'
        fade = min(1, time/.8)
        painter.save(); painter.setOpacity((.65+math.sin(time*2.2)*.15)*fade)
        painter.translate(cx, cy); painter.rotate(time*.12*180/math.pi)
        size = 520*scale
        painter.drawImage(QRectF(-size/2,-size/2,size,size), self.images['aura-'+color]); painter.restore()
        for phase, x, speed, size in self.particles:
            fraction = (phase+time*speed)%1
            painter.setOpacity(math.sin(fraction*math.pi)*.5*fade)
            painter.drawImage(QRectF(cx+x*740*scale+math.sin(time+x)*9*scale,cy+(.5-fraction)*600*scale,2*scale,size*scale),self.images['spark-'+color])
        size = 620*scale
        painter.setOpacity(fade)
        painter.drawImage(QRectF(cx-size/2,cy-size/2+math.sin(time*1.3)*4*scale,size,size),self.images['silhouette'])
        painter.setOpacity(1)
        painter.setPen(QColor('#F4F1E8')); painter.setFont(QFont('Sans Serif',24,QFont.Bold))
        painter.drawText(QRectF(0,height*.745,width,42),Qt.AlignHCenter,'B A N K A I')
        painter.setPen(QColor('#8190A6')); painter.setFont(QFont('Sans Serif',11))
        painter.drawText(QRectF(0,height*.80,width,26),Qt.AlignHCenter,'SOUL SOCIETY  /  REIATSU ONLINE')
        track_width = 360*scale
        painter.drawImage(QRectF(cx-track_width/2,height*.84,track_width,3*scale),self.images['bar-track'])
        x = cx-track_width/2+track_width*.82*(math.sin(time*1.5)+1)/2
        painter.drawImage(QRectF(x,height*.84,track_width*.18,3*scale),self.images['bar-'+color])

    def frame(self, mode, time, width=1280, height=720):
        image=QImage(width,height,QImage.Format_RGBA8888);image.fill(QColor('#090C12'))
        painter=QPainter(image);self.draw(painter,width,height,mode,time);painter.end();return image


class Canvas(QWidget):
    def __init__(self):
        super().__init__();self.scene=Scene();self.mode='silhouette'
        self.setMinimumSize(800,450);self.clock=QElapsedTimer();self.clock.start()
        self.timer=QTimer(self);self.timer.timeout.connect(self.update);self.timer.start(33)
    def paintEvent(self,event):
        painter=QPainter(self);self.scene.draw(painter,self.width(),self.height(),self.mode,self.clock.elapsed()/1000);painter.end()
    def choose(self,mode):
        self.mode='silhouette'
        self.clock.restart();self.update()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--export',action='store_true');args=parser.parse_args()
    app=QApplication(sys.argv[:1])
    if args.export:
        from PIL import Image
        scene=Scene();out=ROOT/'previews';out.mkdir(exist_ok=True)
        for mode in ['silhouette']:
            scene.frame(mode,2).save(str(out/(mode+'.png')))
            frames=[]
            for i in range(48):
                image=scene.frame(mode,1+i/15,960,540)
                frames.append(Image.frombytes('RGBA',(image.width(),image.height()),image.bits().tobytes()).convert('RGB'))
            frames[0].save(out/(mode+'.gif'),save_all=True,append_images=frames[1:],duration=67,loop=0)
        print('Exported previews:',out);return
    window=QWidget();window.setWindowTitle('Bankai boot splash — desktop preview');layout=QVBoxLayout(window)
    row=QHBoxLayout();picker=QComboBox();picker.addItem('Ichigo silhouette','silhouette');picker.setCurrentIndex(0)
    canvas=Canvas();picker.currentIndexChanged.connect(lambda:canvas.choose(picker.currentData()))
    button=QPushButton('Replay');button.clicked.connect(lambda:canvas.choose(picker.currentData()))
    row.addWidget(picker);row.addWidget(button);row.addStretch();layout.addLayout(row);layout.addWidget(canvas)
    window.resize(1280,780);window.show();app.exec()


if __name__=='__main__':
    main()
