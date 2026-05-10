import sys
import os
import math
import hashlib
import calendar
from datetime import datetime
import email_service as _email_service
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QFrame, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QGridLayout, QFileDialog, QDialog, QFormLayout, QMessageBox,
    QComboBox, QTextEdit, QDateEdit, QScrollArea, QSizePolicy,
    QGraphicsDropShadowEffect, QScrollBar, QProgressBar, QSpacerItem,
    QInputDialog
)
from PySide6.QtGui import (
    QPixmap, QColor, QCursor, QFont, QPainter, QPainterPath,
    QBrush, QPen, QLinearGradient, QRadialGradient, QPolygonF,
    QFontMetrics
)
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QDate, QSize,
    QRectF, QPointF, QTimer, Property
)

import qtawesome as qta
import database

# ─────────────────────────────────────────────
#  THEME
# ─────────────────────────────────────────────
class Theme:
    DARK = {
        "bg":          "#0D1117",
        "surface":     "#161B22",
        "surface2":    "#21262D",
        "border":      "#30363D",
        "text":        "#FFFFFF",
        "text_muted":  "#8B949E",
        "accent":      "#FFD700",
        "accent_dim":  "rgba(255,215,0,0.12)",
        "blue":        "#58A6FF",
        "green":       "#3FB950",
        "red":         "#FF6B6B",
        "orange":      "#F0883E",
        "purple":      "#D2A8FF",
        "teal":        "#79C0FF",
    }
    LIGHT = {
        "bg":          "#F6F8FA",
        "surface":     "#FFFFFF",
        "surface2":    "#EAEEF2",
        "border":      "#D0D7DE",
        "text":        "#1F2328",
        "text_muted":  "#636C76",
        "accent":      "#B8860B",
        "accent_dim":  "rgba(184,134,11,0.12)",
        "blue":        "#0969DA",
        "green":       "#1A7F37",
        "red":         "#CF222E",
        "orange":      "#BC4C00",
        "purple":      "#8250DF",
        "teal":        "#0969DA",
    }
    _current = "DARK"

    @classmethod
    def get(cls):
        return cls.DARK if cls._current == "DARK" else cls.LIGHT

    @classmethod
    def toggle(cls):
        cls._current = "LIGHT" if cls._current == "DARK" else "DARK"

    @classmethod
    def is_dark(cls):
        return cls._current == "DARK"


def T(key):
    return Theme.get()[key]


def table_style():
    t = Theme.get()
    return f"""
        QTableWidget {{ background-color: {t['surface']}; color: {t['text']}; gridline-color: {t['border']}; border: none; font-size: 13px; }}
        QHeaderView::section {{ background-color: {t['surface2']}; color: {t['text_muted']}; padding: 10px; border: 1px solid {t['border']}; font-weight: bold; }}
        QTableWidget::item {{ padding: 8px; border-bottom: 1px solid {t['surface2']}; }}
        QTableWidget::item:selected {{ background-color: {t['accent_dim']}; color: {t['accent']}; }}
        QScrollBar:vertical {{ background: {t['bg']}; width: 8px; border-radius: 4px; }}
        QScrollBar::handle:vertical {{ background: {t['border']}; border-radius: 4px; }}
    """


def input_style():
    t = Theme.get()
    return f"background-color: {t['bg']}; color: {t['text']}; border: 1px solid {t['border']}; border-radius: 8px; padding: 8px 12px; font-size: 13px;"


def dialog_style():
    t = Theme.get()
    return f"background-color: {t['surface']}; color: {t['text']};"


def label_style():
    return f"color: {T('text_muted')}; font-size: 13px;"


def make_btn(text, color=None, text_color="black", width=None, height=40, icon=None, icon_color=None):
    if color is None:
        color = T("accent")
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    if icon:
        btn.setIcon(qta.icon(icon, color=icon_color or text_color))
        btn.setIconSize(QSize(16, 16))
    w = f"min-width: {width}px;" if width else ""
    btn.setStyleSheet(f"""
        QPushButton {{ background-color: {color}; color: {text_color};
            border-radius: 8px; font-weight: bold; font-size: 13px;
            padding: 6px 18px; {w} min-height: {height}px; }}
        QPushButton:hover {{ border: 1px solid rgba(255,255,255,0.2); }}
    """)
    return btn


def resolve_photo_path(photo_path):
    """Resolve a stored photo_path (relative or absolute) to an absolute path."""
    if not photo_path:
        return ''
    if os.path.isabs(photo_path) and os.path.exists(photo_path):
        return photo_path
    # Try resolving relative to main.py directory
    resolved = os.path.join(os.path.dirname(__file__), photo_path)
    if os.path.exists(resolved):
        return resolved
    return ''


def page_header(title, btn_text=None, btn_callback=None, btn_icon=None):
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    lbl = QLabel(title)
    lbl.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
    h.addWidget(lbl)
    h.addStretch()
    if btn_text and btn_callback:
        btn = make_btn(btn_text, T("green"), "white", icon=btn_icon, icon_color="white")
        btn.clicked.connect(btn_callback)
        h.addWidget(btn)
    return w


# ─────────────────────────────────────────────
#  AVATAR
# ─────────────────────────────────────────────
class AvatarWidget(QLabel):
    COLORS = ["#FF6B6B","#FFD700","#58A6FF","#3FB950","#F0883E",
              "#D2A8FF","#79C0FF","#A8D8A8","#FFA07A","#87CEEB"]

    def __init__(self, name="?", size=48, image_path=None):
        super().__init__()
        self.avatar_size = size
        self.setFixedSize(size, size)
        self.set_avatar(name, image_path)

    def set_avatar(self, name="?", image_path=None):
        self.name = name
        self.image_path = image_path
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        s = self.avatar_size
        path = QPainterPath()
        path.addEllipse(QRectF(0, 0, s, s))
        painter.setClipPath(path)

        if self.image_path and os.path.exists(self.image_path):
            pix = QPixmap(self.image_path).scaled(s, s, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawPixmap(0, 0, pix)
        else:
            initial = self.name[0].upper() if self.name else "?"
            idx = sum(ord(c) for c in self.name) % len(self.COLORS)
            color = QColor(self.COLORS[idx])
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(0, 0, s, s))
            painter.setPen(QPen(QColor("white")))
            font = QFont("Segoe UI", int(s * 0.36), QFont.Bold)
            painter.setFont(font)
            painter.drawText(QRectF(0, 0, s, s), Qt.AlignCenter, initial)
        painter.end()


# ─────────────────────────────────────────────
#  CHARTS
# ─────────────────────────────────────────────
class BarChartWidget(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.title = title
        self.data = []
        self._anim_progress = 0.0
        self._hover_index = -1
        self._bar_rects = []
        self.setMinimumHeight(200)
        self.setMouseTracking(True)
        self._animation = QPropertyAnimation(self, b"animationProgress")
        self._animation.setDuration(900)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def animationProgress(self):
        return self._anim_progress

    def setAnimationProgress(self, value):
        self._anim_progress = value
        self.update()

    animationProgress = Property(float, animationProgress, setAnimationProgress)

    def set_data(self, data):
        self.data = data
        self._hover_index = -1
        self._animation.stop()
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.start()
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        t = Theme.get()
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 40, 10, 30, 40
        chart_w = w - pad_l - pad_r
        chart_h = h - pad_t - pad_b
        max_val = max((v for _, v, _ in self.data), default=1) or 1
        bar_count = len(self.data)
        bar_gap = 12
        bar_w = (chart_w - bar_gap * (bar_count + 1)) / bar_count
        painter.setPen(QPen(QColor(t['text'])))
        font = QFont("Segoe UI", 11, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(pad_l, 4, chart_w, 22), Qt.AlignLeft, self.title)
        self._bar_rects = []
        for i, (label, value, color) in enumerate(self.data):
            x = pad_l + bar_gap * (i + 1) + bar_w * i
            animated_value = value * self._anim_progress
            bar_h = (animated_value / max_val) * (chart_h - 20)
            y = pad_t + chart_h - bar_h
            c = QColor(color)
            if i == self._hover_index:
                painter.setBrush(QBrush(c.lighter(130)))
            else:
                grad = QLinearGradient(x, y, x, y + bar_h)
                grad.setColorAt(0, c.lighter(120))
                grad.setColorAt(1, c.darker(110))
                painter.setBrush(QBrush(grad))
            painter.setPen(Qt.NoPen)
            path = QPainterPath()
            rect = QRectF(x, y, bar_w, bar_h)
            path.addRoundedRect(rect, 4, 4)
            painter.drawPath(path)
            if i == self._hover_index:
                painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
                painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 6, 6)
            painter.setPen(QPen(QColor(t['text'])))
            font2 = QFont("Segoe UI", 9, QFont.Bold)
            painter.setFont(font2)
            painter.drawText(QRectF(x, y - 18, bar_w, 16), Qt.AlignCenter, str(int(animated_value)))
            font3 = QFont("Segoe UI", 8)
            painter.setFont(font3)
            painter.setPen(QPen(QColor(t['text_muted'])))
            painter.drawText(QRectF(x - 4, pad_t + chart_h + 4, bar_w + 8, 24), Qt.AlignCenter, label)
            self._bar_rects.append(rect)
        painter.end()

    def mouseMoveEvent(self, event):
        pos = event.position() if hasattr(event, 'position') else event.pos()
        hover_index = -1
        for i, rect in enumerate(self._bar_rects):
            if rect.contains(pos):
                hover_index = i
                break
        if hover_index != self._hover_index:
            self._hover_index = hover_index
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_index = -1
        self.update()
        super().leaveEvent(event)


class DonutChartWidget(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.title = title
        self.data = []
        self._anim_progress = 0.0
        self._hover_index = -1
        self._segment_angles = []
        self.setMinimumSize(200, 200)
        self.setMouseTracking(True)
        self._animation = QPropertyAnimation(self, b"animationProgress")
        self._animation.setDuration(900)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def animationProgress(self):
        return self._anim_progress

    def setAnimationProgress(self, value):
        self._anim_progress = value
        self.update()

    animationProgress = Property(float, animationProgress, setAnimationProgress)

    def set_data(self, data):
        self.data = data
        self._hover_index = -1
        self._animation.stop()
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.start()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        t = Theme.get()
        w, h = self.width(), self.height()
        side = min(w, h) - 40
        cx = w // 2
        cy = h // 2
        outer_r = side // 2
        inner_r = int(outer_r * 0.58)
        total = sum(v for _, v, _ in self.data) or 1
        start_angle = -90 * 16
        self._segment_angles = []
        current_start = start_angle
        for i, (label, value, color) in enumerate(self.data):
            span = int((value / total) * 360 * 16 * self._anim_progress)
            segment_rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(Qt.NoPen)
            painter.drawPie(segment_rect, current_start, span)
            norm_start = current_start % (360 * 16)
            norm_end = (current_start + span) % (360 * 16)
            self._segment_angles.append((norm_start, norm_end, outer_r, inner_r))
            if i == self._hover_index and span > 0:
                highlight_path = QPainterPath()
                rect = QRectF(cx - outer_r - 4, cy - outer_r - 4, (outer_r + 4) * 2, (outer_r + 4) * 2)
                highlight_path.addEllipse(rect)
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor(255, 255, 255, 120), 3))
                painter.drawPath(highlight_path)
            current_start += span
        painter.setBrush(QBrush(QColor(t['surface'])))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2))
        painter.setPen(QPen(QColor(t['text'])))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(QRectF(cx - inner_r, cy - 14, inner_r * 2, 28), Qt.AlignCenter, self.title)
        legend_y = cy + outer_r + 8
        legend_x = cx - (len(self.data) * 70) // 2
        for i, (label, value, color) in enumerate(self.data):
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(legend_x, legend_y, 10, 10), 2, 2)
            painter.setPen(QPen(QColor(t['text_muted'])))
            painter.setFont(QFont("Segoe UI", 8))
            text = f"{label} ({value})"
            if i == self._hover_index:
                painter.setPen(QPen(QColor(t['text']), 1))
                painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(QRectF(legend_x + 14, legend_y - 1, 56, 14), Qt.AlignLeft, text)
            legend_x += 80
        painter.end()

    def mouseMoveEvent(self, event):
        pos = event.position() if hasattr(event, 'position') else event.pos()
        rel_x = pos.x() - self.width() / 2
        rel_y = pos.y() - self.height() / 2
        dist = math.hypot(rel_x, rel_y)
        angle = int((90 - math.degrees(math.atan2(rel_y, rel_x))) * 16) % (360 * 16)
        hover_index = -1
        for i, (start, end, outer_r, inner_r) in enumerate(self._segment_angles):
            if inner_r < dist < outer_r:
                if start <= end:
                    if start <= angle <= end:
                        hover_index = i
                        break
                else:
                    if angle >= start or angle <= end:
                        hover_index = i
                        break
        if hover_index != self._hover_index:
            self._hover_index = hover_index
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_index = -1
        self.update()
        super().leaveEvent(event)


# ─────────────────────────────────────────────
#  LINE CHART WIDGET  (revenue trend)
# ─────────────────────────────────────────────
class LineChartWidget(QWidget):
    """Smooth animated line/area chart for revenue trends."""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.title = title
        self.datasets = []        # list of (label, [(x_label, value)], color)
        self._anim_progress = 0.0
        self._hover_x = -1
        self._point_positions = []  # list of list of (px, py, value, label)
        self.setMinimumHeight(220)
        self.setMouseTracking(True)

        self._animation = QPropertyAnimation(self, b"animProgress")
        self._animation.setDuration(1000)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def animProgress(self):
        return self._anim_progress

    def setAnimProgress(self, v):
        self._anim_progress = v
        self.update()

    animProgress = Property(float, animProgress, setAnimProgress)

    def set_data(self, datasets):
        """datasets: list of (label, [(x_label, value), ...], color)"""
        self.datasets = datasets
        self._hover_x = -1
        self._animation.stop()
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.start()

    def paintEvent(self, event):
        if not self.datasets:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        t = Theme.get()
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 56, 20, 36, 44

        chart_w = w - pad_l - pad_r
        chart_h = h - pad_t - pad_b

        # Collect all values to find global max
        all_values = [v for _, pts, _ in self.datasets for _, v in pts]
        max_val = max(all_values, default=1) or 1

        # Draw title
        painter.setPen(QPen(QColor(t['text'])))
        painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
        painter.drawText(QRectF(pad_l, 4, chart_w, 24), Qt.AlignLeft | Qt.AlignVCenter, self.title)

        # Y-axis gridlines + labels
        grid_steps = 4
        painter.setFont(QFont("Segoe UI", 8))
        for i in range(grid_steps + 1):
            y = pad_t + chart_h - (i / grid_steps) * chart_h
            val = (i / grid_steps) * max_val
            painter.setPen(QPen(QColor(t['border']), 1, Qt.DashLine))
            painter.drawLine(int(pad_l), int(y), int(w - pad_r), int(y))
            painter.setPen(QPen(QColor(t['text_muted'])))
            if val >= 1000:
                lbl = f"₱{val/1000:.0f}k"
            else:
                lbl = f"₱{val:.0f}"
            painter.drawText(QRectF(0, y - 8, pad_l - 4, 16), Qt.AlignRight | Qt.AlignVCenter, lbl)

        # Determine x positions from first dataset
        if not self.datasets[0][1]:
            painter.end()
            return
        x_labels = [lbl for lbl, _ in self.datasets[0][1]]
        n = len(x_labels)
        if n < 2:
            painter.end()
            return
        x_step = chart_w / (n - 1)

        # X-axis labels
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QPen(QColor(t['text_muted'])))
        for i, lbl in enumerate(x_labels):
            px = pad_l + i * x_step
            painter.drawText(QRectF(px - 30, pad_t + chart_h + 6, 60, 20),
                             Qt.AlignCenter, lbl)

        # Hover vertical line
        self._point_positions = []
        if 0 <= self._hover_x < n:
            hx = pad_l + self._hover_x * x_step
            painter.setPen(QPen(QColor(t['text_muted']), 1, Qt.DashLine))
            painter.drawLine(int(hx), pad_t, int(hx), pad_t + chart_h)

        # Draw each dataset as filled area + line
        for ds_idx, (ds_label, pts, color) in enumerate(self.datasets):
            if len(pts) < 2:
                continue
            pts_draw = []
            for i, (lbl, val) in enumerate(pts):
                px = pad_l + i * x_step
                animated = val * self._anim_progress
                py = pad_t + chart_h - (animated / max_val) * chart_h
                pts_draw.append((px, py, val, lbl))

            c = QColor(color)

            # Filled area under line
            area_path = QPainterPath()
            area_path.moveTo(pts_draw[0][0], pad_t + chart_h)
            for px, py, _, _ in pts_draw:
                area_path.lineTo(px, py)
            area_path.lineTo(pts_draw[-1][0], pad_t + chart_h)
            area_path.closeSubpath()
            fill_color = QColor(c)
            fill_color.setAlpha(40)
            painter.setBrush(QBrush(fill_color))
            painter.setPen(Qt.NoPen)
            painter.drawPath(area_path)

            # Line
            line_pen = QPen(c, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(line_pen)
            painter.setBrush(Qt.NoBrush)
            line_path = QPainterPath()
            line_path.moveTo(pts_draw[0][0], pts_draw[0][1])
            for px, py, _, _ in pts_draw[1:]:
                line_path.lineTo(px, py)
            painter.drawPath(line_path)

            # Data points
            self._point_positions.append(pts_draw)
            for i, (px, py, val, lbl) in enumerate(pts_draw):
                is_hover = (self._hover_x == i)
                r = 6 if is_hover else 4
                painter.setBrush(QBrush(c))
                painter.setPen(QPen(QColor(t['surface']), 2))
                painter.drawEllipse(QRectF(px - r, py - r, r * 2, r * 2))

                # Tooltip on hover
                if is_hover:
                    tooltip = f"₱{val:,.0f}"
                    fm = QFontMetrics(QFont("Segoe UI", 9, QFont.Bold))
                    tw = fm.horizontalAdvance(tooltip) + 16
                    th = 24
                    tx = min(px - tw / 2, w - pad_r - tw)
                    ty = py - th - 8
                    painter.setBrush(QBrush(QColor(t['surface2'])))
                    painter.setPen(QPen(QColor(c), 1))
                    painter.drawRoundedRect(QRectF(tx, ty, tw, th), 6, 6)
                    painter.setPen(QPen(c))
                    painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    painter.drawText(QRectF(tx, ty, tw, th), Qt.AlignCenter, tooltip)

        # Legend (multi-dataset)
        if len(self.datasets) > 1:
            lx = pad_l
            ly = pad_t + chart_h + 28
            for ds_label, _, color in self.datasets:
                c = QColor(color)
                painter.setBrush(QBrush(c))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(QRectF(lx, ly, 10, 10), 2, 2)
                painter.setPen(QPen(QColor(t['text_muted'])))
                painter.setFont(QFont("Segoe UI", 8))
                painter.drawText(QRectF(lx + 14, ly - 1, 80, 14), Qt.AlignLeft, ds_label)
                lx += 100

        painter.end()

    def mouseMoveEvent(self, event):
        pos = event.position() if hasattr(event, 'position') else event.pos()
        if self.datasets and self.datasets[0][1]:
            n = len(self.datasets[0][1])
            if n >= 2:
                pad_l, pad_r = 56, 20
                chart_w = self.width() - pad_l - pad_r
                x_step = chart_w / (n - 1)
                hover = round((pos.x() - pad_l) / x_step) if x_step > 0 else -1
                hover = max(0, min(n - 1, hover))
                if hover != self._hover_x:
                    self._hover_x = hover
                    self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_x = -1
        self.update()
        super().leaveEvent(event)


class ThemeToggleBtn(QWidget):
    def __init__(self, on_toggle):
        super().__init__()
        self.on_toggle = on_toggle
        self.setFixedSize(56, 28)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        Theme.toggle()
        self.update()
        self.on_toggle()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        is_dark = Theme.is_dark()
        track_color = QColor("#30363D") if is_dark else QColor("#D0D7DE")
        painter.setBrush(QBrush(track_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(0, 4, 56, 20), 10, 10)
        thumb_x = 32 if is_dark else 4
        thumb_color = QColor("#FFD700") if is_dark else QColor("#636C76")
        painter.setBrush(QBrush(thumb_color))
        painter.drawEllipse(QRectF(thumb_x, 2, 24, 24))
        icon_name = "fa5s.moon" if is_dark else "fa5s.sun"
        icon_color = "#FFD700" if is_dark else "white"
        pix = qta.icon(icon_name, color=icon_color).pixmap(QSize(14, 14))
        painter.drawPixmap(int(thumb_x + 5), 7, pix)
        painter.end()


# ─────────────────────────────────────────────
#  INTERACTIVE STAT CARD (clickable)
# ─────────────────────────────────────────────
class StatCard(QFrame):
    def __init__(self, title, value, color, icon_name=None, subtitle=None, on_click=None):
        super().__init__()
        self.on_click = on_click
        self.setMinimumSize(160, 120)
        self.setFrameShape(QFrame.NoFrame)
        self.setCursor(Qt.PointingHandCursor if on_click else Qt.ArrowCursor)
        self._color = color
        self._apply_style(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        top_row.addWidget(t_lbl)
        top_row.addStretch()
        if icon_name:
            icon_lbl = QLabel()
            pix = qta.icon(icon_name, color=color).pixmap(QSize(20, 20))
            icon_lbl.setPixmap(pix)
            icon_lbl.setStyleSheet("border: none; background: transparent;")
            top_row.addWidget(icon_lbl)
        layout.addLayout(top_row)

        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(f"color: {color}; font-size: 36px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(self.value_label)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 11px; border: none; background: transparent;")
            layout.addWidget(sub_lbl)

        if on_click:
            arrow = QLabel("View details")
            arrow.setStyleSheet(f"color: {color}; font-size: 11px; border: none; background: transparent; margin-top: 2px;")
            layout.addWidget(arrow)

    def _apply_style(self, hovered):
        t = Theme.get()
        border = self._color if hovered else t['border']
        bg = t['surface2'] if hovered else t['surface']
        self.setStyleSheet(f"background-color: {bg}; border-radius: 16px; border: 1px solid {border};")

    def set_value(self, v):
        self.value_label.setText(str(v))

    def enterEvent(self, event):
        if self.on_click:
            self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click()
        super().mousePressEvent(event)


# ─────────────────────────────────────────────
#  MAINTENANCE CARD (interactive inline card)
# ─────────────────────────────────────────────
class MaintenanceCardWidget(QFrame):
    def __init__(self, request, on_resolve, on_view, can_resolve=True):
        super().__init__()
        t = Theme.get()
        priority_colors = {"High": t['red'], "Medium": t['accent'], "Low": t['green']}
        p_color = priority_colors.get(request.get('priority', 'Low'), t['text_muted'])
        self.setStyleSheet(f"background: {t['surface2']}; border-radius: 12px; border-left: 4px solid {p_color};")
        self.setMinimumHeight(90)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(3)

        title_row = QHBoxLayout()
        room_lbl = QLabel(f"Room {request.get('room_number','?')}")
        room_lbl.setStyleSheet(f"color: {t['text']}; font-weight: bold; font-size: 13px; background: transparent; border: none;")
        priority_badge = QLabel(request.get('priority','?'))
        priority_badge.setStyleSheet(f"color: {p_color}; font-size: 11px; font-weight: bold; background: transparent; border: none; padding: 2px 8px;")
        title_row.addWidget(room_lbl)
        title_row.addWidget(priority_badge)
        title_row.addStretch()
        info.addLayout(title_row)

        issue_lbl = QLabel(str(request.get('description',''))[:80] + ('...' if len(str(request.get('description',''))) > 80 else ''))
        issue_lbl.setStyleSheet(f"color: {t['text_muted']}; font-size: 12px; background: transparent; border: none;")
        info.addWidget(issue_lbl)

        renter_lbl = QLabel(f"Reported by: {request.get('renter_name','?')}")
        renter_lbl.setStyleSheet(f"color: {t['text_muted']}; font-size: 11px; background: transparent; border: none;")
        info.addWidget(renter_lbl)

        row.addLayout(info, stretch=1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(6)
        if can_resolve:
            resolve_btn = QPushButton("Resolve")
            resolve_btn.setCursor(Qt.PointingHandCursor)
            resolve_btn.setStyleSheet(f"background: {t['green']}; color: white; border-radius: 6px; font-size: 11px; font-weight: bold; padding: 4px 12px; border: none;")
            resolve_btn.clicked.connect(on_resolve)
            btn_col.addWidget(resolve_btn)
        view_btn = QPushButton("View")
        view_btn.setCursor(Qt.PointingHandCursor)
        view_btn.setStyleSheet(f"background: transparent; color: {t['blue']}; border: 1px solid {t['blue']}; border-radius: 6px; font-size: 11px; padding: 4px 12px;")
        view_btn.clicked.connect(on_view)
        btn_col.addWidget(view_btn)
        row.addLayout(btn_col)


# ─────────────────────────────────────────────
#  ROOM CARD WIDGET
# ─────────────────────────────────────────────
class RoomCardWidget(QFrame):
    def __init__(self, room, on_click=None):
        super().__init__()
        t = Theme.get()
        status = room.get('status', 'Available')
        status_colors = {
            'Available': t['green'],
            'Full': t['red'],
            'Under Maintenance': t['orange'],
            'Reserved': t['blue'],
        }
        s_color = status_colors.get(status, t['text_muted'])

        self.setStyleSheet(f"""
            QFrame {{
                background: {t['surface']};
                border-radius: 14px;
                border: 1px solid {t['border']};
            }}
            QFrame:hover {{
                border: 1px solid {s_color};
            }}
        """)
        self.setFixedSize(200, 160)
        self.setCursor(Qt.PointingHandCursor if on_click else Qt.ArrowCursor)
        if on_click:
            self.mousePressEvent = lambda e: on_click(room)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(5)

        top = QHBoxLayout()
        room_no = QLabel(f"Room {room.get('room_number','?')}")
        room_no.setStyleSheet(f"color: {t['text']}; font-size: 15px; font-weight: bold; background: transparent; border: none;")
        status_dot = QLabel(f"{status}")
        status_dot.setStyleSheet(f"color: {s_color}; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        top.addWidget(room_no)
        top.addStretch()
        layout.addLayout(top)
        layout.addWidget(status_dot)

        floor_lbl = QLabel(f"Floor: {room.get('floor_level','?')}")
        floor_lbl.setStyleSheet(f"color: {t['text_muted']}; font-size: 11px; background: transparent; border: none;")
        layout.addWidget(floor_lbl)

        # Occupancy bar
        cap = room.get('capacity', 1) or 1
        occ = room.get('occupied', 0)
        pct = int((occ / cap) * 100)
        occ_lbl = QLabel(f"{occ}/{cap} occupied")
        occ_lbl.setStyleSheet(f"color: {t['text_muted']}; font-size: 11px; background: transparent; border: none;")
        layout.addWidget(occ_lbl)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(pct)
        bar.setFixedHeight(6)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ background: {t['border']}; border-radius: 3px; border: none; }}
            QProgressBar::chunk {{ background: {s_color}; border-radius: 3px; }}
        """)
        layout.addWidget(bar)

        rate_lbl = QLabel(f"₱{room.get('monthly_rate',0):,.0f}/mo")
        rate_lbl.setStyleSheet(f"color: {t['accent']}; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(rate_lbl)


# ─────────────────────────────────────────────
#  DIALOGS
# ─────────────────────────────────────────────
class PersonDetailDialog(QDialog):
    def __init__(self, parent, person_data, person_type="renter"):
        super().__init__(parent)
        self.person_data = person_data
        self.person_type = person_type
        self.setWindowTitle("Person Details")
        self.setFixedWidth(480)
        self.setStyleSheet(dialog_style())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)
        header = QHBoxLayout()
        name = f"{person_data.get('first_name','')} {person_data.get('last_name','')}".strip()
        profile_path = person_data.get('profile_path') or person_data.get('profile_pic_path')
        avatar = AvatarWidget(name, 80, profile_path)
        header.addWidget(avatar)
        info_col = QVBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color: {T('text')}; font-size: 20px; font-weight: bold;")
        info_col.addWidget(name_lbl)
        if person_type == "renter":
            status = person_data.get('renter_status', '-')
            status_colors = {"Active": T("green"), "Inactive": T("text_muted"), "Blacklisted": T("red")}
            s_color = status_colors.get(status, T("text_muted"))
        else:
            status = person_data.get('role', '-')
            s_color = T("blue")
        status_lbl = QLabel(f"{status}")
        status_lbl.setStyleSheet(f"color: {s_color}; font-size: 13px; font-weight: bold;")
        info_col.addWidget(status_lbl)
        header.addLayout(info_col)
        header.addStretch()
        layout.addLayout(header)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {T('border')}; max-height: 1px;")
        layout.addWidget(line)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        grid = QGridLayout(scroll_content)
        grid.setSpacing(10)
        if person_type == "renter":
            fields = [
                ("Gender",        person_data.get('gender')),
                ("Occupation",    person_data.get('occupation_type')),
                ("Institution",   person_data.get('institution_employer')),
                ("Contact",       person_data.get('contact_number')),
                ("Email",         person_data.get('email')),
                ("ID Type",       person_data.get('id_type')),
                ("ID Number",     person_data.get('id_number')),
                ("Address",       person_data.get('address')),
                ("Emerg. Name",   person_data.get('emergency_contact_name')),
                ("Emerg. Number", person_data.get('emergency_contact_number')),
            ]
        else:
            fields = [
                ("Username",   person_data.get('username')),
                ("Role",       person_data.get('role')),
                ("Email",      person_data.get('email')),
                ("Contact",    person_data.get('contact_number')),
                ("Joined",     str(person_data.get('created_at', '-'))),
            ]
        row = 0
        for label_text, value in fields:
            if value:
                lbl = QLabel(label_text + ":")
                lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px; font-weight: bold;")
                val = QLabel(str(value))
                val.setStyleSheet(f"color: {T('text')}; font-size: 13px;")
                val.setWordWrap(True)
                grid.addWidget(lbl, row, 0)
                grid.addWidget(val, row, 1)
                row += 1
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        close_btn = make_btn("Close", T("surface2"), T("text"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class MaintenanceDetailDialog(QDialog):
    def __init__(self, parent, request):
        super().__init__(parent)
        self.setWindowTitle("Maintenance Request Detail")
        self.setFixedWidth(440)
        self.setStyleSheet(dialog_style())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)
        t = Theme.get()
        priority_colors = {"High": t['red'], "Medium": t['accent'], "Low": t['green']}
        p_color = priority_colors.get(request.get('priority', ''), t['text'])
        title_lbl = QLabel(f"Room {request.get('room_number','?')} - Maintenance")
        title_lbl.setStyleSheet(f"color: {T('text')}; font-size: 18px; font-weight: bold;")
        layout.addWidget(title_lbl)
        fields = [
            ("Renter", request.get('renter_name', '-')),
            ("Issue", request.get('description', '-')),
            ("Priority", request.get('priority', '-')),
            ("Status", request.get('status', '-')),
            ("Date", str(request.get('request_date', '-'))),
        ]
        for lbl, val in fields:
            row = QHBoxLayout()
            l = QLabel(f"{lbl}:")
            l.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px; font-weight: bold; min-width: 80px;")
            v = QLabel(str(val))
            v.setStyleSheet(f"color: {T('text')}; font-size: 13px;")
            v.setWordWrap(True)
            row.addWidget(l)
            row.addWidget(v, stretch=1)
            layout.addLayout(row)
        close_btn = make_btn("Close", T("surface2"), T("text"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class RenterSelfProfileDialog(QDialog):
    def __init__(self, parent, name, person_id, person_type="renter"):
        super().__init__(parent)
        self.person_id = person_id
        self.person_type = person_type
        self.chosen_path = None
        self.setWindowTitle(f"Set Profile Picture - {name}")
        self.setFixedWidth(380)
        self.setStyleSheet(dialog_style())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignCenter)
        title = QLabel(f"Hello, {name}!")
        title.setStyleSheet(f"color: {T('text')}; font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        sub = QLabel("You can set your profile picture here.\nThis step is optional - you can skip it.")
        sub.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px;")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        layout.addWidget(sub)
        self.avatar_preview = AvatarWidget(name, 100)
        layout.addWidget(self.avatar_preview, alignment=Qt.AlignCenter)
        choose_btn = make_btn("  Choose Photo", T("blue"), "white", icon="fa5s.camera", icon_color="white")
        choose_btn.clicked.connect(self._choose_photo)
        layout.addWidget(choose_btn)
        self.path_label = QLabel("No photo selected")
        self.path_label.setStyleSheet(f"color: {T('text_muted')}; font-size: 11px;")
        self.path_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.path_label)
        btns = QHBoxLayout()
        skip_btn = make_btn("Skip", T("surface2"), T("text"))
        save_btn = make_btn("  Save", T("green"), "white", icon="fa5s.save", icon_color="white")
        skip_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self.accept)
        btns.addWidget(skip_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

    def _choose_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose Profile Picture", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            self.chosen_path = path
            self.path_label.setText(f"{os.path.basename(path)[:30]}")
            self.avatar_preview.set_avatar(self.avatar_preview.name, path)
            self.avatar_preview.update()


class StaffDialog(QDialog):
    def __init__(self, parent, staff=None):
        super().__init__(parent)
        self.setWindowTitle("Add Staff" if not staff else "Edit Staff")
        self.setFixedWidth(460)
        self.setStyleSheet(dialog_style())
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        def inp(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setStyleSheet(input_style())
            return e

        self.full_name = inp("Full Name")
        self.username  = inp("Username")
        self.password  = inp("Password (leave blank to keep)")
        self.password.setEchoMode(QLineEdit.Password)
        self.role = QComboBox()
        self.role.addItems(["Staff", "Maintenance", "Security"])
        self.role.setStyleSheet(input_style())
        self.email   = inp("email@example.com")
        self.contact = inp("09XXXXXXXXX")
        layout.addRow("Full Name*:", self.full_name)
        layout.addRow("Username*:",  self.username)
        layout.addRow("Password:",   self.password)
        layout.addRow("Role:",       self.role)
        layout.addRow("Email:",      self.email)
        layout.addRow("Contact:",    self.contact)
        if staff:
            self.full_name.setText(staff.get('full_name', ''))
            self.username.setText(staff.get('username', ''))
            self.role.setCurrentText(staff.get('role', 'Staff'))
            self.email.setText(staff.get('email', '') or '')
            self.contact.setText(staff.get('contact_number', '') or '')
        save_btn = make_btn("  Save", T("green"), "white", icon="fa5s.save", icon_color="white")
        save_btn.clicked.connect(self._validate_and_accept)
        layout.addRow(save_btn)

    def _validate_and_accept(self):
        if not self.full_name.text().strip() or not self.username.text().strip():
            QMessageBox.warning(self, "Missing", "Full name and username are required.")
            return
        self.accept()

    def get_data(self):
        d = dict(
            full_name=self.full_name.text().strip(),
            username=self.username.text().strip(),
            role=self.role.currentText(),
            email=self.email.text().strip() or None,
            contact_number=self.contact.text().strip() or None,
        )
        pw = self.password.text().strip()
        if pw:
            d['password'] = pw
        return d


class RoomDialog(QDialog):
    def __init__(self, parent, room=None):
        super().__init__(parent)
        self.setWindowTitle("Add Room" if not room else "Edit Room")
        self.setFixedWidth(460)
        self.setStyleSheet(dialog_style())
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        def inp(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setStyleSheet(input_style())
            return e

        self.room_number  = inp("e.g. 101")
        self.floor_level  = QComboBox()
        self.floor_level.addItems(["1st Floor", "2nd Floor"])
        self.floor_level.setStyleSheet(input_style())
        self.monthly_rate = inp("e.g. 3500")
        self.capacity     = inp("e.g. 4")
        self.status       = QComboBox()
        # 'Under Maintenance' is intentionally excluded - only Admin can set it
        # via the dedicated "Set Under Maintenance" action (with a reason).
        self.status.addItems(["Available", "Full", "Reserved"])
        self.status.setStyleSheet(input_style())
        self.description  = QTextEdit()
        self.description.setFixedHeight(70)
        self.description.setStyleSheet(input_style())

        layout.addRow("Room No.*:", self.room_number)
        layout.addRow("Floor:",     self.floor_level)
        layout.addRow("Rate (₱):",  self.monthly_rate)
        layout.addRow("Capacity:",  self.capacity)
        layout.addRow("Status:",    self.status)
        layout.addRow("Notes:",     self.description)

        if room:
            self.room_number.setText(str(room.get('room_number', '')))
            self.floor_level.setCurrentText(room.get('floor_level', ''))
            self.monthly_rate.setText(str(room.get('monthly_rate', '')))
            self.capacity.setText(str(room.get('capacity', '')))
            cur_status = room.get('status', 'Available')
            if cur_status == 'Under Maintenance':
                # Preserve maintenance state by adding it temporarily so the
                # combo can reflect it; admin must use the dedicated action
                # to clear or change maintenance reason.
                self.status.addItem("Under Maintenance")
            self.status.setCurrentText(cur_status)
            self.description.setPlainText(room.get('description', '') or '')

        save_btn = make_btn("  Save", T("green"), "white", icon="fa5s.save", icon_color="white")
        save_btn.clicked.connect(self.accept)
        layout.addRow(save_btn)

    def get_data(self):
        return dict(
            room_number=self.room_number.text().strip(),
            floor_level=self.floor_level.currentText(),
            monthly_rate=float(self.monthly_rate.text() or 0),
            capacity=int(self.capacity.text() or 0),
            status=self.status.currentText(),
            description=self.description.toPlainText().strip()
        )


class PaymentDialog(QDialog):
    def __init__(self, parent, renters):
        super().__init__(parent)
        self.setWindowTitle("Record Payment")
        self.setFixedWidth(480)
        self.setStyleSheet(dialog_style())
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        def inp(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setStyleSheet(input_style())
            return e

        self.invoice      = inp("e.g. INV-2026-001")
        self.renter_combo = QComboBox()
        self.renter_combo.setStyleSheet(input_style())
        self._renter_ids  = []
        for r in renters:
            self.renter_combo.addItem(f"{r['first_name']} {r['last_name']}")
            self._renter_ids.append(r['renter_id'])
        self.amount       = inp("e.g. 1800.00")
        self.balance      = inp("Remaining balance (0 if fully paid)")
        self.method       = QComboBox()
        self.method.addItems(["Cash", "GCash", "Bank Transfer", "Other"])
        self.method.setStyleSheet(input_style())
        self.reference    = inp("Reference # (optional)")
        # Billing month defaults to current month name + year
        from datetime import date as _d
        _now = _d.today()
        default_month = f"{calendar.month_name[_now.month]} {_now.year}"
        self.billing_month = inp("e.g. May 2026")
        self.billing_month.setText(default_month)
        self.pay_date     = QDateEdit(QDate.currentDate())
        self.pay_date.setCalendarPopup(True)
        self.pay_date.setStyleSheet(input_style())
        # Status is now READ-ONLY hint - auto-computed from amount/balance/date
        self.status       = QComboBox()
        self.status.addItems(["Paid", "Partial", "Pending", "Overdue", "Advanced"])
        self.status.setStyleSheet(input_style())
        self.remarks      = inp("Remarks (optional)")

        # Auto-status hint label
        t = Theme.get()
        self._status_hint = QLabel("Status will auto-update based on balance & due date")
        self._status_hint.setStyleSheet(f"color: {t['text_muted']}; font-size: 11px;")
        self._status_hint.setWordWrap(True)

        layout.addRow("Invoice No*:",   self.invoice)
        layout.addRow("Renter*:",       self.renter_combo)
        layout.addRow("Amount Paid*:",  self.amount)
        layout.addRow("Balance Left:",  self.balance)
        layout.addRow("Method:",        self.method)
        layout.addRow("Reference #:",   self.reference)
        layout.addRow("Billing Month:", self.billing_month)
        layout.addRow("Payment Date:",  self.pay_date)
        layout.addRow("Status:",        self.status)
        layout.addRow("",               self._status_hint)
        layout.addRow("Remarks:",       self.remarks)

        # Wire auto-status computation
        self.amount.textChanged.connect(self._auto_compute_status)
        self.balance.textChanged.connect(self._auto_compute_status)
        self.billing_month.textChanged.connect(self._auto_compute_status)
        self._auto_compute_status()

        save_btn = make_btn("  Save", T("green"), "white", icon="fa5s.save", icon_color="white")
        save_btn.clicked.connect(self.accept)
        layout.addRow(save_btn)

    def _auto_compute_status(self):
        """Automatically determine the correct status from amount, balance, and billing month."""
        from datetime import date as _d
        t = Theme.get()
        try:
            amt     = float(self.amount.text() or 0)
            balance = float(self.balance.text() or 0)
        except ValueError:
            return

        # Parse billing month to get the due date (5th of that month)
        month_text = self.billing_month.text().strip()
        today = _d.today()
        due_date = None
        try:
            parts = month_text.split()
            mo_num = list(calendar.month_name).index(parts[0])
            yr_num = int(parts[1])
            due_date = _d(yr_num, mo_num, 5)
        except Exception:
            pass

        # Logic:
        # balance == 0 and amt > 0           → Paid
        # balance > 0 and amt > 0            → Partial
        # amt == 0 and due_date past today   → Overdue
        # amt == 0 and due_date in future    → Pending
        # amt > monthly_rate (overpay)       → Advanced
        if amt > 0 and balance == 0:
            computed = "Paid"
            color = t['green']
            hint  = "Fully paid - balance is zero."
        elif amt > 0 and balance > 0:
            if due_date and today > due_date:
                computed = "Partial"
                color = t['orange']
                hint  = f"Partial payment with ₱{balance:,.2f} still owed (past due {due_date})."
            else:
                computed = "Partial"
                color = t['orange']
                hint  = f"Partial - ₱{balance:,.2f} remaining balance."
        elif amt == 0:
            if due_date and today > due_date:
                computed = "Overdue"
                color = t['red']
                hint  = f"No payment received and due date {due_date} has passed."
            else:
                computed = "Pending"
                color = t['accent']
                hint  = "No payment yet - not past due date."
        else:
            computed = "Pending"
            color = t['accent']
            hint  = ""

        idx = self.status.findText(computed)
        if idx >= 0:
            self.status.setCurrentIndex(idx)
        self._status_hint.setText(hint)
        self._status_hint.setStyleSheet(f"color: {color}; font-size: 11px;")

    def get_data(self):
        return dict(
            invoice_number=self.invoice.text().strip(),
            renter_id=self._renter_ids[self.renter_combo.currentIndex()] if self._renter_ids else None,
            amount=float(self.amount.text() or 0),
            balance_amount=float(self.balance.text() or 0),
            payment_method=self.method.currentText(),
            billing_month=self.billing_month.text().strip(),
            payment_date=self.pay_date.date().toString("yyyy-MM-dd"),
            status=self.status.currentText(),
            reference_number=self.reference.text().strip() or None,
            remarks=self.remarks.text().strip() or None,
            processed_by=None
        )


class MaintenanceDialog(QDialog):
    def __init__(self, parent, rooms, renters):
        super().__init__(parent)
        self.setWindowTitle("Add Maintenance Request")
        self.setFixedWidth(440)
        self.setStyleSheet(dialog_style())
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        self.room_combo = QComboBox()
        self.room_combo.setStyleSheet(input_style())
        self._room_ids = []
        for r in rooms:
            self.room_combo.addItem(f"Room {r['room_number']} ({r['floor_level']})")
            self._room_ids.append(r['room_id'])
        self.renter_combo = QComboBox()
        self.renter_combo.setStyleSheet(input_style())
        self._renter_ids = []
        for r in renters:
            self.renter_combo.addItem(f"{r['first_name']} {r['last_name']}")
            self._renter_ids.append(r['renter_id'])
        self.description = QTextEdit()
        self.description.setFixedHeight(80)
        self.description.setStyleSheet(input_style())
        self.priority = QComboBox()
        self.priority.addItems(["Low", "Medium", "High"])
        self.priority.setCurrentText("Medium")
        self.priority.setStyleSheet(input_style())
        layout.addRow("Room*:",    self.room_combo)
        layout.addRow("Renter*:",  self.renter_combo)
        layout.addRow("Issue*:",   self.description)
        layout.addRow("Priority:", self.priority)
        save_btn = make_btn("  Save", T("green"), "white", icon="fa5s.save", icon_color="white")
        save_btn.clicked.connect(self.accept)
        layout.addRow(save_btn)

    def get_data(self):
        return dict(
            room_id=self._room_ids[self.room_combo.currentIndex()] if self._room_ids else None,
            renter_id=self._renter_ids[self.renter_combo.currentIndex()] if self._renter_ids else None,
            description=self.description.toPlainText().strip(),
            priority=self.priority.currentText()
        )


class VisitorDialog(QDialog):
    def __init__(self, parent, renters):
        super().__init__(parent)
        self.setWindowTitle("Log Visitor In")
        self.setFixedWidth(400)
        self.setStyleSheet(dialog_style())
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        def inp(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setStyleSheet(input_style())
            return e

        self.visitor_name = inp("Visitor Full Name")
        self.relationship = inp("e.g. Parent, Sibling, Friend")
        self.renter_combo = QComboBox()
        self.renter_combo.setStyleSheet(input_style())
        self._renter_ids  = []
        for r in renters:
            self.renter_combo.addItem(f"{r['first_name']} {r['last_name']}")
            self._renter_ids.append(r['renter_id'])
        layout.addRow("Visitor Name*:", self.visitor_name)
        layout.addRow("Relationship:",  self.relationship)
        layout.addRow("Visiting*:",     self.renter_combo)
        save_btn = make_btn("  Log In", T("green"), "white", icon="fa5s.sign-in-alt", icon_color="white")
        save_btn.clicked.connect(self.accept)
        layout.addRow(save_btn)

    def get_data(self):
        return dict(
            renter_id=self._renter_ids[self.renter_combo.currentIndex()] if self._renter_ids else None,
            visitor_name=self.visitor_name.text().strip(),
            relationship=self.relationship.text().strip()
        )


class RenterDialog(QDialog):
    def __init__(self, parent, renter=None):
        super().__init__(parent)
        self._is_edit = renter is not None
        self.setWindowTitle("Register Renter" if not self._is_edit else "Edit Renter")
        self.setFixedWidth(520)
        self.setStyleSheet(dialog_style())

        # ── Wrap everything in a scroll area ──
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 16)
        main_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        form_widget = QWidget()
        form_widget.setStyleSheet(f"background: {T('surface')};")
        layout = QFormLayout(form_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 24, 24, 12)

        def inp(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setStyleSheet(input_style())
            return e

        def section_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"color: {T('accent')}; font-size: 12px; font-weight: bold; "
                f"background: transparent; padding-top: 8px;"
            )
            return lbl

        self.first_name  = inp("First Name")
        self.middle_name = inp("Middle Name (optional)")
        self.last_name   = inp("Last Name")
        self.gender      = QComboBox()
        self.gender.addItems(["Male", "Female", "Other"])
        self.gender.setStyleSheet(input_style())
        self.occ_type    = QComboBox()
        self.occ_type.addItems(["Student", "Professional", "Other"])
        self.occ_type.setStyleSheet(input_style())
        self.institution = inp("School / Company")
        self.contact     = inp("09XXXXXXXXX")
        self.email       = inp("email@example.com")
        self.id_type     = QComboBox()
        self.id_type.addItems(["School ID","National ID","Driver's License","Passport","Other"])
        self.id_type.setStyleSheet(input_style())
        self.id_number   = inp("ID Number")
        self.address     = inp("Home Address")
        self.emerg_name  = inp("Emergency Contact Name")
        self.emerg_num   = inp("Emergency Contact Number")
        self.status      = QComboBox()
        self.status.addItems(["Active", "Inactive", "Blacklisted"])
        self.status.setStyleSheet(input_style())

        layout.addRow(section_label("── Personal Information ──"))
        layout.addRow("First Name*:",      self.first_name)
        layout.addRow("Middle Name:",      self.middle_name)
        layout.addRow("Last Name*:",       self.last_name)
        layout.addRow("Gender:",           self.gender)
        layout.addRow("Occupation:",       self.occ_type)
        layout.addRow("Institution:",      self.institution)
        layout.addRow("Contact*:",         self.contact)
        layout.addRow("Email:",            self.email)
        layout.addRow("ID Type:",          self.id_type)
        layout.addRow("ID Number:",        self.id_number)
        layout.addRow("Address:",          self.address)
        layout.addRow("Emergency Name:",   self.emerg_name)
        layout.addRow("Emergency Number:", self.emerg_num)
        layout.addRow("Status:",           self.status)

        # ── Room Assignment section (new renter only) ──
        self.preferred_room = None
        self.preferred_bed  = None
        self.check_in_date  = None
        self.agreed_rate    = None

        if not self._is_edit:
            layout.addRow(section_label("── Room Assignment (Optional) ──"))

            self.preferred_room = QComboBox()
            self.preferred_room.setStyleSheet(input_style())
            self.preferred_room.addItem("— No assignment yet —", userData=None)
            try:
                rooms = database.RoomModule().get_all_rooms_with_beds()
                for r in rooms:
                    avail = int(r.get('available_beds') or 0)
                    if avail > 0:
                        label = (f"Room {r['room_number']} — {r.get('floor_level','')} "
                                 f"({avail} bed{'s' if avail!=1 else ''} available)")
                        self.preferred_room.addItem(label, userData=r)
            except Exception:
                pass

            self.preferred_bed = QComboBox()
            self.preferred_bed.setStyleSheet(input_style())
            self.preferred_bed.addItem("— Select room first —", userData=None)
            self.preferred_bed.setEnabled(False)

            self.preferred_room.currentIndexChanged.connect(self._on_room_changed)

            self.check_in_date = QDateEdit()
            self.check_in_date.setDate(QDate.currentDate())
            self.check_in_date.setCalendarPopup(True)
            self.check_in_date.setStyleSheet(input_style())

            self.agreed_rate = inp("e.g. 1800.00")
            self.agreed_rate.setText("1800.00")

            layout.addRow("Preferred Room:",  self.preferred_room)
            layout.addRow("Preferred Bed:",   self.preferred_bed)
            layout.addRow("Check-in Date:",   self.check_in_date)
            layout.addRow("Agreed Rate (₱):", self.agreed_rate)

        if self._is_edit and renter:
            self.first_name.setText(renter.get('first_name',''))
            self.middle_name.setText(renter.get('middle_name','') or '')
            self.last_name.setText(renter.get('last_name',''))
            self.gender.setCurrentText(renter.get('gender','Male'))
            self.occ_type.setCurrentText(renter.get('occupation_type','Student'))
            self.institution.setText(renter.get('institution_employer','') or '')
            self.contact.setText(renter.get('contact_number','') or '')
            self.email.setText(renter.get('email','') or '')
            self.id_type.setCurrentText(renter.get('id_type','School ID') or 'School ID')
            self.id_number.setText(renter.get('id_number','') or '')
            self.address.setText(renter.get('address','') or '')
            self.emerg_name.setText(renter.get('emergency_contact_name','') or '')
            self.emerg_num.setText(renter.get('emergency_contact_number','') or '')
            self.status.setCurrentText(renter.get('renter_status','Active'))

        scroll.setWidget(form_widget)
        main_layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(24, 0, 24, 0)
        save_btn = make_btn("  Save", T("green"), "white", icon="fa5s.save", icon_color="white")
        save_btn.clicked.connect(self._validate)
        btn_row.addWidget(save_btn)
        main_layout.addLayout(btn_row)

    def _on_room_changed(self, index):
        self.preferred_bed.clear()
        room = self.preferred_room.itemData(index)
        if not room:
            self.preferred_bed.addItem("— Select room first —", userData=None)
            self.preferred_bed.setEnabled(False)
            return
        self.preferred_bed.setEnabled(True)
        room_id = room.get('room_id')
        ALL_BEDS = [
            'Bed A - Bottom', 'Bed A - Top',
            'Bed B - Bottom', 'Bed B - Top',
            'Bed C - Bottom', 'Bed C - Top',
            'Bed D - Bottom', 'Bed D - Top',
        ]
        try:
            info     = database.RoomModule().get_bed_status(room_id)
            occupied = info.get('occupied_beds', []) if info else []
        except Exception:
            occupied = []
        added = 0
        for bed in ALL_BEDS[:int(room.get('capacity', 8))]:
            if bed not in occupied:
                self.preferred_bed.addItem(f"{bed}  ✓ Available", userData=bed)
                added += 1
        if added == 0:
            self.preferred_bed.addItem("No beds available", userData=None)
            self.preferred_bed.setEnabled(False)

    def _validate(self):
        if not self.first_name.text().strip() or not self.last_name.text().strip():
            QMessageBox.warning(self, "Missing", "First name and last name are required.")
            return
        self.accept()

    def get_data(self):
        data = dict(
            first_name=self.first_name.text().strip(),
            middle_name=self.middle_name.text().strip() or None,
            last_name=self.last_name.text().strip(),
            gender=self.gender.currentText(),
            occupation_type=self.occ_type.currentText(),
            institution_employer=self.institution.text().strip() or None,
            contact_number=self.contact.text().strip(),
            email=self.email.text().strip() or None,
            id_type=self.id_type.currentText(),
            id_number=self.id_number.text().strip() or None,
            address=self.address.text().strip() or None,
            emergency_contact_name=self.emerg_name.text().strip() or None,
            emergency_contact_number=self.emerg_num.text().strip() or None,
            renter_status=self.status.currentText(),
        )
        # Room assignment fields — only present for new renter
        if not self._is_edit and self.preferred_room is not None:
            room_obj = self.preferred_room.itemData(self.preferred_room.currentIndex())
            bed_val  = self.preferred_bed.itemData(self.preferred_bed.currentIndex()) if self.preferred_bed else None
            data['room_obj']  = room_obj
            data['bed_val']   = bed_val
            data['check_in']  = self.check_in_date.date().toString("yyyy-MM-dd")
            try:
                data['agreed_rate'] = float(self.agreed_rate.text() or 1800)
            except ValueError:
                data['agreed_rate'] = 1800.0
        return data


# ─────────────────────────────────────────────
#  RENTER REGISTRATION REQUEST DIALOG (public)
# ─────────────────────────────────────────────
class RentRequestDialog(QDialog):
    """Public-facing dialog for prospective renters to request a room."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Apply to Rent a Room")
        self.setFixedWidth(520)
        self.setStyleSheet(dialog_style())

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(16)

        hdr = QLabel("Room Rental Application")
        hdr.setStyleSheet(f"color: {T('accent')}; font-size: 20px; font-weight: bold;")
        main_layout.addWidget(hdr)

        info = QLabel(
            "Fill out this form to apply for a room. Your request will be reviewed by the admin.\n"
            "Once approved, you will receive login credentials to access your tenant dashboard."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px;")
        main_layout.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        form_widget = QWidget()
        form_widget.setStyleSheet(f"background: {T('surface')};")
        layout = QFormLayout(form_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        def inp(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setStyleSheet(input_style())
            return e

        self.first_name  = inp("First Name*")
        self.middle_name = inp("Middle Name (optional)")
        self.last_name   = inp("Last Name*")
        self.gender      = QComboBox()
        self.gender.addItems(["Male", "Female", "Other"])
        self.gender.setStyleSheet(input_style())
        self.occ_type    = QComboBox()
        self.occ_type.addItems(["Student", "Professional", "Other"])
        self.occ_type.setStyleSheet(input_style())
        self.institution = inp("School / Company")
        self.contact     = inp("09XXXXXXXXX*")
        self.email       = inp("email@example.com*")
        self.address     = inp("Current Home Address")
        self.emerg_name  = inp("Emergency Contact Name")
        self.emerg_num   = inp("Emergency Contact Number")

        # ── Preferred Room dropdown ──
        self.preferred_room = QComboBox()
        self.preferred_room.setStyleSheet(input_style())
        self.preferred_room.addItem("No preference", userData=None)
        self._room_data = []
        try:
            from database import RoomModule
            rooms = RoomModule().get_all_rooms_with_beds()
            for r in rooms:
                avail = int(r.get('available_beds') or 0)
                label = f"Room {r['room_number']} — {r.get('floor_level','')} ({avail} bed{'s' if avail!=1 else ''} available)"
                self.preferred_room.addItem(label, userData=r)
                self._room_data.append(r)
        except Exception:
            pass

        # ── Preferred Bed dropdown ──
        self.preferred_bed = QComboBox()
        self.preferred_bed.setStyleSheet(input_style())
        self.preferred_bed.addItem("No preference", userData=None)
        self.preferred_bed.setEnabled(False)

        # Wire room → bed
        self.preferred_room.currentIndexChanged.connect(self._on_room_changed)

        self.message     = QTextEdit()
        self.message.setPlaceholderText("Additional message or questions for the admin (optional)...")
        self.message.setFixedHeight(70)
        self.message.setStyleSheet(input_style())

        layout.addRow("First Name*:",      self.first_name)
        layout.addRow("Middle Name:",       self.middle_name)
        layout.addRow("Last Name*:",       self.last_name)
        layout.addRow("Gender:",           self.gender)
        layout.addRow("Occupation:",       self.occ_type)
        layout.addRow("Institution:",      self.institution)
        layout.addRow("Contact*:",         self.contact)
        layout.addRow("Email*:",           self.email)
        layout.addRow("Address:",          self.address)
        layout.addRow("Emerg. Contact:",   self.emerg_name)
        layout.addRow("Emerg. Number:",    self.emerg_num)
        layout.addRow("Preferred Room:",   self.preferred_room)
        layout.addRow("Preferred Bed:",    self.preferred_bed)
        layout.addRow("Message:",          self.message)

        scroll.setWidget(form_widget)
        main_layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        cancel_btn = make_btn("Cancel", T("surface2"), T("text"))
        submit_btn = make_btn("  Submit Application", T("accent"), "black", icon="fa5s.paper-plane", icon_color="black")
        cancel_btn.clicked.connect(self.reject)
        submit_btn.clicked.connect(self._validate)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(submit_btn)
        main_layout.addLayout(btn_row)

    def _on_room_changed(self, index):
        self.preferred_bed.clear()
        self.preferred_bed.addItem("No preference", userData=None)
        room = self.preferred_room.itemData(index)
        if not room:
            self.preferred_bed.setEnabled(False)
            return
        self.preferred_bed.setEnabled(True)
        room_id = room.get('room_id')
        ALL_BEDS = [
            'Bed A - Bottom', 'Bed A - Top',
            'Bed B - Bottom', 'Bed B - Top',
            'Bed C - Bottom', 'Bed C - Top',
            'Bed D - Bottom', 'Bed D - Top',
        ]
        try:
            from database import RoomModule
            info = RoomModule().get_bed_status(room_id)
            occupied = info.get('occupied_beds', []) if info else []
        except Exception:
            occupied = []
        for bed in ALL_BEDS[:int(room.get('capacity', 8))]:
            status = " ✗ Occupied" if bed in occupied else " ✓ Available"
            self.preferred_bed.addItem(f"{bed}{status}", userData=bed if bed not in occupied else None)

    def _validate(self):
        if not self.first_name.text().strip() or not self.last_name.text().strip():
            QMessageBox.warning(self, "Missing Fields", "First name and last name are required.")
            return
        if not self.contact.text().strip() and not self.email.text().strip():
            QMessageBox.warning(self, "Contact Required", "Please provide at least a contact number or email.")
            return
        self.accept()

    def get_data(self):
        room_obj  = self.preferred_room.itemData(self.preferred_room.currentIndex())
        bed_val   = self.preferred_bed.itemData(self.preferred_bed.currentIndex())
        room_text = f"Room {room_obj['room_number']}" if room_obj else None
        room_id   = room_obj.get('room_id') if room_obj else None
        return dict(
            first_name=self.first_name.text().strip(),
            middle_name=self.middle_name.text().strip() or None,
            last_name=self.last_name.text().strip(),
            gender=self.gender.currentText(),
            occupation_type=self.occ_type.currentText(),
            institution_employer=self.institution.text().strip() or None,
            contact_number=self.contact.text().strip() or None,
            email=self.email.text().strip() or None,
            address=self.address.text().strip() or None,
            emergency_contact_name=self.emerg_name.text().strip() or None,
            emergency_contact_number=self.emerg_num.text().strip() or None,
            preferred_room=room_text,
            preferred_room_id=room_id,
            preferred_bed=bed_val,
            message=self.message.toPlainText().strip() or None,
        )


# ─────────────────────────────────────────────
#  WELCOME PAGE
# ─────────────────────────────────────────────
class WelcomeRoomDetailDialog(QDialog):
    """Modal shown when a room card is clicked - full photo, bed breakdown, amenities."""
    def __init__(self, parent, room, amenities, on_apply):
        super().__init__(parent)
        cap   = int(room.get('capacity', 0) or 0)
        occ   = int(room.get('occupied', 0) or 0)
        avail = cap - occ
        status = room.get('status', 'Available')

        self.setWindowTitle(f"Room {room.get('room_number','?')} - Details")
        self.setFixedWidth(480)
        self.setStyleSheet("""
            QDialog { background: #161B22; border-radius: 16px; }
            QLabel  { background: transparent; border: none; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 20)
        layout.setSpacing(0)

        # ── Photo ──────────────────────────────────────────────
        photo_lbl = QLabel()
        photo_lbl.setFixedSize(480, 200)
        photo_lbl.setAlignment(Qt.AlignCenter)
        photo_path = resolve_photo_path(room.get('photo_path') or '')
        if photo_path:
            pix = QPixmap(photo_path).scaled(
                480, 200, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            photo_lbl.setPixmap(pix)
            photo_lbl.setStyleSheet("border-radius: 16px 16px 0 0; background: #0D1117;")
        else:
            photo_lbl.setText("")
            photo_lbl.setStyleSheet(
                "border-radius: 16px 16px 0 0; color: #FFD700;")
        layout.addWidget(photo_lbl)

        # ── Info body ──────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(24, 16, 24, 0)
        bl.setSpacing(8)

        # Room name + floor
        title = QLabel(f"Room {room.get('room_number','?')}")
        title.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        bl.addWidget(title)

        floor_lbl = QLabel(f"{room.get('floor_level','?')}")
        floor_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        bl.addWidget(floor_lbl)

        # Rate
        rate_lbl = QLabel(f"₱{float(room.get('monthly_rate', 0)):,.0f} / month")
        rate_lbl.setStyleSheet("color: #FFD700; font-size: 15px; font-weight: bold; margin-top: 4px;")
        bl.addWidget(rate_lbl)

        # Bed breakdown
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.08);")
        bl.addWidget(sep)

        beds_widget = QWidget()
        beds_widget.setStyleSheet("background: rgba(255,215,0,0.06); border-radius: 10px;")
        beds_layout = QHBoxLayout(beds_widget)
        beds_layout.setContentsMargins(16, 10, 16, 10)

        for label, val, color in [
            ("Total Beds", str(cap), "#FFFFFF"),
            ("Occupied",   str(occ), "#FF6B6B"),
            ("Available",  str(avail), "#3FB950"),
        ]:
            col = QVBoxLayout()
            v = QLabel(val)
            v.setAlignment(Qt.AlignCenter)
            v.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
            l = QLabel(label)
            l.setAlignment(Qt.AlignCenter)
            l.setStyleSheet("color: #8B949E; font-size: 10px;")
            col.addWidget(v)
            col.addWidget(l)
            beds_layout.addLayout(col)
            if label != "Available":
                div = QFrame()
                div.setFrameShape(QFrame.VLine)
                div.setStyleSheet("color: rgba(255,255,255,0.1);")
                beds_layout.addWidget(div)
        bl.addWidget(beds_widget)

        # Amenities
        if amenities:
            am_lbl = QLabel("Amenities & Inclusions")
            am_lbl.setStyleSheet("color: white; font-size: 12px; font-weight: bold; margin-top: 8px;")
            bl.addWidget(am_lbl)
            am_grid = QGridLayout()
            am_grid.setSpacing(6)
            for idx, am in enumerate(amenities):
                pill = QLabel(f"{am.get('amenity_name','')}")
                pill.setStyleSheet(
                    "background: rgba(255,215,0,0.1); color: #FFD700; "
                    "border: 1px solid rgba(255,215,0,0.3); padding: 4px 10px; "
                    "border-radius: 10px; font-size: 11px;")
                am_grid.addWidget(pill, idx // 2, idx % 2)
            bl.addLayout(am_grid)
        else:
            no_am = QLabel("No amenities listed.")
            no_am.setStyleSheet("color: #8B949E; font-size: 11px; margin-top: 4px;")
            bl.addWidget(no_am)

        layout.addWidget(body)

        # ── Buttons ────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(24, 12, 24, 0)
        btn_row.setSpacing(10)

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet("""
            QPushButton { background: #21262D; color: white; border-radius: 8px;
                          font-size: 12px; border: 1px solid #30363D; }
            QPushButton:hover { background: #30363D; }
        """)
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)

        if avail > 0 and status == 'Available':
            apply_btn = QPushButton("Apply for this Room")
            apply_btn.setFixedHeight(36)
            apply_btn.setStyleSheet("""
                QPushButton { background: #FFD700; color: black; border-radius: 8px;
                              font-size: 12px; font-weight: bold; }
                QPushButton:hover { background: #E6C200; }
            """)
            apply_btn.clicked.connect(lambda: (self.accept(), on_apply(room)))
            btn_row.addWidget(apply_btn)

        layout.addLayout(btn_row)


class WelcomeRoomCard(QFrame):
    """Compact room card for the Welcome page - click to open detail modal."""
    def __init__(self, room, amenities, on_apply):
        super().__init__()
        self._room      = room
        self._amenities = amenities
        self._on_apply  = on_apply

        cap   = int(room.get('capacity', 0) or 0)
        occ   = int(room.get('occupied', 0) or 0)
        avail = cap - occ

        self.setFixedSize(220, 260)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background: rgba(22,27,34,0.92);
                border-radius: 16px;
                border: 1px solid rgba(255,215,0,0.25);
            }
            QFrame:hover { border: 1px solid #FFD700; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(6)

        # ── Photo area ─────────────────────────────────────────
        photo_lbl = QLabel()
        photo_lbl.setFixedSize(220, 120)
        photo_lbl.setAlignment(Qt.AlignCenter)
        photo_path = resolve_photo_path(room.get('photo_path') or '')
        if photo_path:
            pix = QPixmap(photo_path).scaled(
                220, 120, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            photo_lbl.setPixmap(pix)
            photo_lbl.setStyleSheet("border-radius: 16px 16px 0 0; background: #0D1117;")
        else:
            photo_lbl.setText("")
            photo_lbl.setStyleSheet(
                "font-size: 40px; background: rgba(255,215,0,0.08); "
                "border-radius: 16px 16px 0 0; color: #FFD700;")
        layout.addWidget(photo_lbl)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        il = QVBoxLayout(inner)
        il.setContentsMargins(12, 4, 12, 0)
        il.setSpacing(3)

        rn = QLabel(f"Room {room.get('room_number','?')}")
        rn.setStyleSheet("color: white; font-size: 15px; font-weight: bold; background: transparent; border: none;")
        il.addWidget(rn)

        fl = QLabel(f"{room.get('floor_level','?')}")
        fl.setStyleSheet("color: #8B949E; font-size: 11px; background: transparent; border: none;")
        il.addWidget(fl)

        # Beds: show both total and available
        beds_color = "#3FB950" if avail > 0 else "#FF6B6B"
        bed_txt = (f"{avail}/{cap} beds available"
                   if avail > 0 else "Full")
        beds_lbl = QLabel(bed_txt)
        beds_lbl.setStyleSheet(
            f"color: {beds_color}; font-size: 12px; font-weight: bold; "
            "background: transparent; border: none;")
        il.addWidget(beds_lbl)

        rate_lbl = QLabel(f"₱{float(room.get('monthly_rate', 0)):,.0f} / month")
        rate_lbl.setStyleSheet(
            "color: #FFD700; font-size: 12px; font-weight: bold; "
            "background: transparent; border: none;")
        il.addWidget(rate_lbl)

        # Tap hint - no more pills here
        hint = QLabel("Tap card for details & amenities")
        hint.setStyleSheet("color: #8B949E; font-size: 9px; background: transparent; border: none;")
        il.addWidget(hint)

        layout.addWidget(inner)

        if avail > 0:
            ab = QPushButton("Apply for this Room")
            ab.setFixedHeight(30)
            ab.setStyleSheet("""
                QPushButton { background: #FFD700; color: black; border-radius: 8px;
                              font-size: 11px; font-weight: bold; margin: 0 12px; }
                QPushButton:hover { background: #E6C200; }
            """)
            ab.clicked.connect(lambda: on_apply(room))
            layout.addWidget(ab)

    def mousePressEvent(self, event):
        """Open detail modal on card click (anywhere except the Apply button)."""
        dlg = WelcomeRoomDetailDialog(self, self._room, self._amenities, self._on_apply)
        dlg.exec()


class WelcomePage(QWidget):
    # ── Contact / dorm info - edit these to match the real dorm ──
    CONTACT_PHONE = "09674897575"
    CONTACT_EMAIL = "dormnorm@gmail.com"

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self._room_db = database.RoomModule()

        self.bg_label = QLabel(self)
        current_dir = os.path.dirname(__file__)
        image_path = os.path.join(current_dir, "images", "dorm_bg.png")
        if os.path.exists(image_path):
            self.bg_label.setPixmap(QPixmap(image_path))
            self.bg_label.setScaledContents(True)

        self.overlay = QFrame(self)
        self.overlay.setStyleSheet("background-color: rgba(0,0,0,130);")

        # ── Outer scroll so everything is accessible at any window size ──
        outer_scroll = QScrollArea(self)
        outer_scroll.setWidgetResizable(True)
        outer_scroll.setStyleSheet("border: none; background: transparent;")
        outer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._outer_scroll = outer_scroll

        page_widget = QWidget()
        page_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── HERO SECTION ─────────────────────────────────
        hero = QWidget()
        hero.setStyleSheet("background: transparent;")
        hero.setMinimumHeight(480)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setAlignment(Qt.AlignCenter)
        hero_layout.setSpacing(10)
        hero_layout.setContentsMargins(40, 60, 40, 40)

        title_container = QWidget()
        title_container.setStyleSheet("background: transparent;")
        title_layout = QHBoxLayout(title_container)
        title_layout.setAlignment(Qt.AlignCenter)
        dorm_label = QLabel("Dorm")
        dorm_label.setStyleSheet("color: white; font-size: 100px; font-family: 'Brush Script MT'; background: transparent; margin-right: -10px;")
        norm_label = QLabel("Norm")
        norm_label.setStyleSheet("color: white; font-size: 100px; font-family: 'Segoe UI'; font-weight: bold; background: transparent;")
        title_layout.addWidget(dorm_label)
        title_layout.addWidget(norm_label)

        tagline = QLabel("Making you feel at home away from home")
        tagline.setStyleSheet("color: #DADCE0; font-size: 20px; font-family: 'Segoe UI'; font-weight: 300; background: transparent;")

        # Contact strip
        contact_widget = QWidget()
        contact_widget.setStyleSheet("background: rgba(255,215,0,0.08); border-radius: 12px; border: 1px solid rgba(255,215,0,0.25);")
        contact_layout = QHBoxLayout(contact_widget)
        contact_layout.setContentsMargins(20, 8, 20, 8)
        contact_layout.setSpacing(30)
        ph_lbl = QLabel(f"CONTACT US: {self.CONTACT_PHONE}")
        ph_lbl.setStyleSheet("color: #FFD700; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        em_lbl = QLabel(f"EMAIL: {self.CONTACT_EMAIL}")
        em_lbl.setStyleSheet("color: #FFD700; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        contact_layout.addStretch()
        contact_layout.addWidget(ph_lbl)
        contact_layout.addWidget(em_lbl)
        contact_layout.addStretch()

        # Amenities toggle
        self.toggle_btn = QPushButton("◈ VIEW AMENITIES & INCLUSIONS ▼")
        self.toggle_btn.setFixedWidth(300)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #FFD700; border: 1px solid #FFD700;
                          border-radius: 15px; padding: 8px; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background: rgba(255,215,0,0.1); }
        """)
        self.toggle_btn.clicked.connect(self.toggle_amenities)

        self.feature_container = QWidget()
        self.feature_container.setStyleSheet("background: transparent;")
        self.feature_container.setVisible(False)
        feature_layout = QGridLayout(self.feature_container)
        feature_layout.setSpacing(10)
        all_features = [
            ("", "Fiber Wi-Fi"), ("", "Utilities Included"), ("", "24/7 Security"),
            ("", "Shared Kitchen"), ("", "Private Bath"), ("", "Smart TV"),
            ("🍽️", "Dining Area"), ("🛋️", "Living Room"),
        ]
        row, col = 0, 0
        for icon, feat in all_features:
            pill = QLabel(f"{icon}  {feat}")
            pill.setStyleSheet("background-color: rgba(255,215,0,0.12); color: #FFD700; border: 1px solid rgba(255,215,0,0.4); padding: 8px 15px; border-radius: 18px; font-size: 12px; font-weight: bold;")
            feature_layout.addWidget(pill, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)
        btn_row.setAlignment(Qt.AlignCenter)

        login_btn = QPushButton("GET STARTED - LOGIN")
        login_btn.setFixedSize(280, 60)
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setStyleSheet("""
            QPushButton { background-color: #FFD700; color: black; border-radius: 30px; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background-color: #E6C200; border: 2px solid white; }
        """)
        login_btn.clicked.connect(lambda: self.controller.parent().fade_to_page(1))

        apply_btn = QPushButton("APPLY TO RENT")
        apply_btn.setFixedSize(200, 60)
        apply_btn.setCursor(Qt.PointingHandCursor)
        apply_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #FFD700; border: 2px solid #FFD700; border-radius: 30px; font-size: 16px; font-weight: bold; }
            QPushButton:hover { background-color: rgba(255,215,0,0.1); }
        """)
        apply_btn.clicked.connect(lambda: self._open_application())

        btn_row.addWidget(login_btn)
        btn_row.addWidget(apply_btn)

        hero_layout.addWidget(title_container, alignment=Qt.AlignCenter)
        hero_layout.addWidget(tagline, alignment=Qt.AlignCenter)
        hero_layout.addSpacing(12)
        hero_layout.addWidget(contact_widget, alignment=Qt.AlignCenter)
        hero_layout.addSpacing(8)
        hero_layout.addWidget(self.toggle_btn, alignment=Qt.AlignCenter)
        hero_layout.addWidget(self.feature_container, alignment=Qt.AlignCenter)
        hero_layout.addSpacing(20)
        hero_layout.addLayout(btn_row)

        layout.addWidget(hero)

        # ── BROWSE ROOMS SECTION ──────────────────────────
        browse_section = QWidget()
        browse_section.setStyleSheet("background: rgba(13,17,23,0.85);")
        browse_layout = QVBoxLayout(browse_section)
        browse_layout.setContentsMargins(50, 40, 50, 50)
        browse_layout.setSpacing(20)

        browse_hdr = QHBoxLayout()
        browse_title = QLabel("Browse Available Rooms")
        browse_title.setStyleSheet("color: white; font-size: 24px; font-weight: bold; background: transparent; border: none;")
        self.room_avail_badge = QLabel("Loading...")
        self.room_avail_badge.setStyleSheet("color: #3FB950; font-size: 13px; font-weight: bold; background: rgba(63,185,80,0.12); border: 1px solid #3FB950; padding: 4px 12px; border-radius: 12px;")
        browse_hdr.addWidget(browse_title)
        browse_hdr.addStretch()
        browse_hdr.addWidget(self.room_avail_badge)
        browse_layout.addLayout(browse_hdr)

        sub_lbl = QLabel("See bed availability and amenities before applying. Click a room card's Apply button to get started.")
        sub_lbl.setStyleSheet("color: #8B949E; font-size: 13px; background: transparent; border: none;")
        browse_layout.addWidget(sub_lbl)

        self.room_cards_scroll = QScrollArea()
        self.room_cards_scroll.setWidgetResizable(True)
        self.room_cards_scroll.setFixedHeight(310)
        self.room_cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.room_cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.room_cards_scroll.setStyleSheet("border: none; background: transparent;")
        self.room_cards_inner = QWidget()
        self.room_cards_inner.setStyleSheet("background: transparent;")
        self.room_cards_row = QHBoxLayout(self.room_cards_inner)
        self.room_cards_row.setContentsMargins(0, 8, 0, 8)
        self.room_cards_row.setSpacing(16)
        self.room_cards_row.addStretch()
        self.room_cards_scroll.setWidget(self.room_cards_inner)
        browse_layout.addWidget(self.room_cards_scroll)

        layout.addWidget(browse_section)

        # ── PAYMENT METHODS SECTION ───────────────────────────
        pay_section = QWidget()
        pay_section.setStyleSheet("background: rgba(13,17,23,0.92);")
        pay_layout = QVBoxLayout(pay_section)
        pay_layout.setContentsMargins(50, 36, 50, 40)
        pay_layout.setSpacing(16)

        pay_title = QLabel("Payment Methods")
        pay_title.setStyleSheet("color: white; font-size: 22px; font-weight: bold; background: transparent; border: none;")
        pay_layout.addWidget(pay_title)

        pay_sub = QLabel("We accept the following payment options for monthly rent and bills.")
        pay_sub.setStyleSheet("color: #8B949E; font-size: 13px; background: transparent; border: none;")
        pay_layout.addWidget(pay_sub)

        pay_methods_row = QHBoxLayout()
        pay_methods_row.setSpacing(16)
        payment_methods = [
            ("🏦", "Bank Transfer",    "BDO / BPI / Metrobank\nDeposit to dorm account\nInclude your full name as reference"),
            ("", "GCash / Maya",     "Send to registered dorm number\nInclude your name & room number\nin the message"),
            ("💵", "Cash",             "Pay at the admin office\nMonday–Saturday, 8AM–5PM\nAlways request a receipt"),
            ("🏪", "Over-the-Counter", "7-Eleven, Bayad Center\nPalawan Pawnshop accepted\nAsk admin for reference no."),
        ]
        for icon, method, details in payment_methods:
            card = QFrame()
            card.setStyleSheet("background: rgba(22,27,34,0.95); border-radius: 14px; border: 1px solid rgba(255,215,0,0.2);")
            card.setFixedHeight(150)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(18, 16, 18, 16)
            cl.setSpacing(6)
            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet("font-size: 28px; background: transparent; border: none;")
            method_lbl = QLabel(method)
            method_lbl.setStyleSheet("color: #FFD700; font-size: 14px; font-weight: bold; background: transparent; border: none;")
            details_lbl = QLabel(details)
            details_lbl.setStyleSheet("color: #8B949E; font-size: 11px; background: transparent; border: none;")
            details_lbl.setWordWrap(True)
            cl.addWidget(icon_lbl)
            cl.addWidget(method_lbl)
            cl.addWidget(details_lbl)
            cl.addStretch()
            pay_methods_row.addWidget(card)
        pay_layout.addLayout(pay_methods_row)

        pay_note = QLabel("Note: Always keep your official receipt or payment screenshot. For issues, contact the admin office.")
        pay_note.setStyleSheet("color: #F0883E; font-size: 12px; background: transparent; border: none;")
        pay_note.setWordWrap(True)
        pay_layout.addWidget(pay_note)

        layout.addWidget(pay_section)

        outer_scroll.setWidget(page_widget)

        # Load rooms after widgets are set up
        QTimer.singleShot(200, self._load_rooms)

    def _load_rooms(self):
        try:
            rooms = self._room_db.get_all_rooms()
        except Exception:
            rooms = []

        # Clear
        while self.room_cards_row.count() > 1:
            item = self.room_cards_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        avail_total = 0
        for room in rooms:
            cap = int(room.get('capacity', 0) or 0)
            occ = int(room.get('occupied', 0) or 0)
            avail_total += max(0, cap - occ)
            try:
                ams = self._room_db.get_amenities(room.get('room_id'))
            except Exception:
                ams = []
            card = WelcomeRoomCard(room, ams, on_apply=self._open_application_for_room)
            self.room_cards_row.insertWidget(self.room_cards_row.count() - 1, card)

        self.room_avail_badge.setText(f"{avail_total} bed{'s' if avail_total != 1 else ''} available")

        if not rooms:
            lbl = QLabel("No rooms listed yet. Contact the admin.")
            lbl.setStyleSheet("color: #8B949E; font-size: 14px; padding: 20px; background: transparent; border: none;")
            self.room_cards_row.insertWidget(0, lbl)

    def _open_application_for_room(self, room=None):
        self._open_application(preferred=f"Room {room.get('room_number','')}" if room else "")

    def _open_application(self, preferred=""):
        dlg = RentRequestDialog(self)
        if preferred:
            try:
                # Try to pre-select the room in the dropdown
                for i in range(dlg.preferred_room.count()):
                    room = dlg.preferred_room.itemData(i)
                    if room and f"Room {room.get('room_number','')}" == preferred:
                        dlg.preferred_room.setCurrentIndex(i)
                        break
            except Exception:
                pass
        if dlg.exec():
            data = dlg.get_data()
            app_db = database.ApplicationModule()
            ok = app_db.submit_application(
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                gender=data.get('gender', 'Other'),
                occupation_type=data.get('occupation_type', 'Student'),
                institution=data.get('institution_employer') or '',
                contact_number=data.get('contact_number') or '',
                email=data.get('email') or '',
                address=data.get('address') or '',
                emergency_name=data.get('emergency_contact_name') or '',
                emergency_number=data.get('emergency_contact_number') or '',
                preferred_room=data.get('preferred_room') or '',
                preferred_room_id=data.get('preferred_room_id') or None,
                preferred_bed=data.get('preferred_bed') or '',
                message=data.get('message') or '',
                middle_name=data.get('middle_name') or '',
            )
            if ok:
                email_entered = data.get('email', '').strip()
                email_note = (
                    f"\nA confirmation email has been sent to:\n{email_entered}"
                    if email_entered else
                    "\n(No email provided - no confirmation sent.)"
                )
                QMessageBox.information(
                    self, "Application Submitted!",
                    f"Thank you, {data['first_name']}! Your rental application has been submitted.\n\n"
                    "The admin will review your application shortly.\n"
                    "Once approved, you will receive your login credentials\n"
                    "to access your tenant dashboard."
                    + email_note
                )
            else:
                QMessageBox.warning(
                    self, "Could Not Submit",
                    "There was a problem submitting your application.\n"
                    "Please make sure the system database is running and try again."
                )

    def toggle_amenities(self):
        is_visible = self.feature_container.isVisible()
        self.feature_container.setVisible(not is_visible)
        self.toggle_btn.setText("CLOSE AMENITIES ▲" if not is_visible else "◈ VIEW AMENITIES & INCLUSIONS ▼")

    def resizeEvent(self, event):
        self.bg_label.resize(self.size())
        self.overlay.resize(self.size())
        self._outer_scroll.resize(self.size())
        super().resizeEvent(event)


# ─────────────────────────────────────────────
#  LOGIN PAGE
# ─────────────────────────────────────────────
class LoginPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        self.bg_label = QLabel(self)
        current_dir = os.path.dirname(__file__)
        image_path = os.path.join(current_dir, "images", "dorm_bg.png")
        if os.path.exists(image_path):
            self.bg_label.setPixmap(QPixmap(image_path))
            self.bg_label.setScaledContents(True)

        self.overlay = QFrame(self)
        self.overlay.setStyleSheet("background-color: rgba(0,0,0,165);")

        main_layout = QVBoxLayout(self)
        header = QHBoxLayout()
        back_btn = QPushButton("Back")
        back_btn.setStyleSheet("color: #FFD700; background: transparent; font-size: 16px; font-weight: bold; border: none;")
        back_btn.clicked.connect(lambda: self.controller.setCurrentIndex(0))
        header.addWidget(back_btn, alignment=Qt.AlignLeft)
        header.setContentsMargins(20, 20, 20, 0)
        main_layout.addLayout(header)
        main_layout.addStretch()

        self.card = QFrame()
        self.card.setFixedSize(450, 580)
        self.card.setStyleSheet("background-color: #161B22; border-radius: 25px; border: 1px solid #30363D;")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 30, 40, 30)
        card_layout.setSpacing(15)

        brand_container = QWidget()
        brand_layout = QHBoxLayout(brand_container)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        dorm_mini = QLabel("Dorm")
        dorm_mini.setStyleSheet("color: #FFD700; font-family: 'Brush Script MT'; font-size: 28px; border: none;")
        norm_mini = QLabel("Norm")
        norm_mini.setStyleSheet("color: white; font-family: 'Segoe UI'; font-weight: bold; font-size: 28px; border: none;")
        brand_layout.addWidget(dorm_mini)
        brand_layout.addWidget(norm_mini)
        card_layout.addWidget(brand_container, alignment=Qt.AlignCenter)

        title = QLabel("Welcome Back!")
        title.setStyleSheet("color: white; font-size: 30px; font-weight: bold; border: none;")
        card_layout.addWidget(title, alignment=Qt.AlignCenter)

        role_hint = QLabel("Login as Admin, Staff, or Tenant")
        role_hint.setStyleSheet("color: #8B949E; font-size: 12px; border: none;")
        card_layout.addWidget(role_hint, alignment=Qt.AlignCenter)

        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #FF6B6B; font-size: 12px; border: none; font-weight: bold;")
        self.info_label.setWordWrap(True)
        self.info_label.setVisible(False)
        card_layout.addWidget(self.info_label)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username or Email")
        self.user_input.setFixedSize(370, 50)
        self.user_input.setStyleSheet(
            "QLineEdit { background-color: #0D1117; color: white; border: 1px solid #30363D; border-radius: 10px; padding-left: 15px; }"
            "QLineEdit:focus { border: 1px solid #FFD700; }"
        )
        card_layout.addWidget(self.user_input)

        pass_container = QWidget()
        pass_container.setFixedSize(370, 50)
        pass_container.setStyleSheet("background-color: #0D1117; border: 1px solid #30363D; border-radius: 10px;")
        pass_layout = QHBoxLayout(pass_container)
        pass_layout.setContentsMargins(0, 0, 0, 0)
        pass_layout.setSpacing(0)
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setFixedSize(320, 50)
        self.pass_input.setStyleSheet(
            "QLineEdit { background: transparent; color: white; border: none; padding-left: 15px; }"
        )
        self.pass_input.returnPressed.connect(self.handle_login)
        self.eye_btn = QPushButton()
        self.eye_btn.setIcon(qta.icon("fa5s.eye", color="#8B949E"))
        self.eye_btn.setIconSize(QSize(18, 18))
        self.eye_btn.setFixedSize(50, 50)
        self.eye_btn.setCheckable(True)
        self.eye_btn.setCursor(Qt.PointingHandCursor)
        self.eye_btn.setStyleSheet("QPushButton { background: transparent; border: none; }")
        self.eye_btn.clicked.connect(self.toggle_password_visibility)
        pass_layout.addWidget(self.pass_input)
        pass_layout.addWidget(self.eye_btn)
        card_layout.addWidget(pass_container)

        login_btn = QPushButton("LOGIN")
        login_btn.setFixedSize(370, 55)
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setStyleSheet("background-color: #FFD700; color: black; border-radius: 12px; font-size: 16px; font-weight: bold; margin-top: 10px;")
        login_btn.clicked.connect(self.handle_login)
        card_layout.addWidget(login_btn)

        forgot_btn = QPushButton("Forgot Password? Reset via Email")
        forgot_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #58A6FF; border: none; "
            "font-size: 12px; text-decoration: underline; margin-top: 4px; }"
            "QPushButton:hover { color: #FFD700; }"
        )
        forgot_btn.setCursor(Qt.PointingHandCursor)  # cursor set via Python, NOT QSS
        forgot_btn.clicked.connect(self._open_forgot_password)
        card_layout.addWidget(forgot_btn, alignment=Qt.AlignCenter)

        footer_note = QLabel("Don't have an account? Contact Admin or Apply to Rent.")
        footer_note.setStyleSheet("color: #8B949E; font-size: 12px; border: none; margin-top: 6px;")
        card_layout.addWidget(footer_note, alignment=Qt.AlignCenter)

        main_layout.addWidget(self.card, alignment=Qt.AlignCenter)
        main_layout.addStretch()

    def toggle_password_visibility(self):
        if self.eye_btn.isChecked():
            self.pass_input.setEchoMode(QLineEdit.Normal)
            self.eye_btn.setIcon(qta.icon("fa5s.eye-slash", color="#8B949E"))
        else:
            self.pass_input.setEchoMode(QLineEdit.Password)
            self.eye_btn.setIcon(qta.icon("fa5s.eye", color="#8B949E"))

    def handle_login(self):
        user = self.user_input.text().strip()
        pw   = self.pass_input.text().strip()
        if not user or not pw:
            self.info_label.setText("Please enter both username and password.")
            self.info_label.setVisible(True)
            return

        # Try admin/staff login first
        db = database.AdminModule()
        user_data = db.validate_login(user, pw)
        if user_data:
            self.info_label.setVisible(False)
            db.log_login(user_data['admin_id'], user_data['full_name'], user_data.get('role', 'Admin'))
            dashboard = self.controller.parent().dashboard
            dashboard.set_current_user(user_data)
            self.controller.parent().fade_to_page(2)
            return

        # Try renter login
        renter_data = self._try_renter_login(user, pw)
        if renter_data:
            self.info_label.setVisible(False)
            dashboard = self.controller.parent().dashboard
            dashboard.set_current_user(renter_data)
            self.controller.parent().fade_to_page(2)
            return

        self.info_label.setText("Invalid username or password.")
        self.info_label.setVisible(True)

    def _try_renter_login(self, username, password):
        try:
            db = database.RenterModule()
            row = db.validate_renter_login(username, password)
            if row:
                # validate_renter_login queries vw_renter_profile_full which only
                # exposes a combined 'full_name' column (via fn_full_name), NOT
                # separate first_name/middle_name/last_name fields. Using those
                # missing keys produced an empty string → sidebar showed "?".
                full_name = (row.get('full_name') or '').strip() or username
                return {
                    'admin_id':  None,
                    'renter_id': row['renter_id'],
                    'full_name': full_name,
                    'role':      'Renter',
                    'username':  username,
                }
        except Exception as e:
            print(f"[Renter login] {e}")
        return None

    # ── OTP / Forgot-Password flow ────────────────────────────
    def _open_forgot_password(self):
        """Step 1 - collect email and trigger OTP dispatch."""
        email, ok = self._get_text_input(
            "Password Reset",
            "Enter your registered email address:",
            placeholder="your@email.com",
        )
        if not ok or not email.strip():
            return
        email = email.strip().lower()

        admin_mod  = database.AdminModule()
        renter_mod = database.RenterModule()
        sent = admin_mod.reset_password_request(email) or \
               renter_mod.reset_password_request(email)

        if not sent:
            QMessageBox.warning(
                self, "Not Found",
                "No account was found with that email address.\n"
                "Please check the email or contact the admin.",
            )
            return

        QMessageBox.information(
            self, "OTP Sent",
            f"A 6-digit One-Time Password has been sent to:\n{email}\n\n"
            "It is valid for 10 minutes.",
        )
        self._verify_otp_and_reset(email)

    def _verify_otp_and_reset(self, email: str):
        """Step 2 - verify OTP, then set new password.
        NOTE: OTP was already consumed by email_service._otp_store when
        reset_password_request() was called. We verify exactly once here
        and then directly update the password — we do NOT call
        reset_password_confirm() on the DB module because that would call
        verify_otp() a second time on an already-cleared store entry.
        """
        otp, ok = self._get_text_input(
            "Enter OTP",
            f"Enter the 6-digit OTP sent to {email}:",
            placeholder="123456",
        )
        if not ok or not otp.strip():
            return

        if not _email_service.verify_otp(email, otp.strip()):
            QMessageBox.warning(self, "Invalid OTP",
                                "The OTP is incorrect or has expired.\n"
                                "Please request a new one.")
            return

        new_pw, ok2 = self._get_text_input(
            "New Password",
            "Enter your new password (minimum 6 characters):",
            echo_password=True,
        )
        if not ok2 or len(new_pw.strip()) < 6:
            QMessageBox.warning(self, "Too Short",
                                "Password must be at least 6 characters.")
            return

        new_hashed = hashlib.sha256(new_pw.strip().encode()).hexdigest()

        admin_mod  = database.AdminModule()
        renter_mod = database.RenterModule()
        updated = False

        # Try admin table
        conn = admin_mod.connect()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE admins SET password=%s WHERE LOWER(email)=%s",
                    (new_hashed, email),
                )
                conn.commit()
                updated = cur.rowcount > 0
            except Exception as e:
                print(f"[ForgotPW admin] {e}")
            finally:
                conn.close()

        # Try renter table
        if not updated:
            conn = renter_mod.connect()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT renter_id FROM renters WHERE LOWER(email)=%s",
                        (email,),
                    )
                    row = cur.fetchone()
                    if row:
                        cur.execute(
                            "UPDATE renter_accounts SET password=%s "
                            "WHERE renter_id=%s",
                            (new_hashed, row[0]),
                        )
                        conn.commit()
                        updated = cur.rowcount > 0
                except Exception as e:
                    print(f"[ForgotPW renter] {e}")
                finally:
                    conn.close()

        if updated:
            QMessageBox.information(
                self, "Password Updated",
                "Your password has been reset successfully.\n"
                "Please log in with your new password.",
            )
            self.user_input.setText(email)
            self.pass_input.clear()
        else:
            QMessageBox.critical(
                self, "Error",
                "Could not update password. Please try again or contact admin.",
            )

    @staticmethod
    def _get_text_input(title: str, label: str, placeholder: str = "",
                        echo_password: bool = False):
        """Lightweight single-field modal dialog. Returns (text, accepted)."""
        dlg = QDialog()
        dlg.setWindowTitle(title)
        dlg.setFixedWidth(400)
        dlg.setStyleSheet(
            "QDialog { background:#161B22; color:white; border-radius:12px; }"
        )
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(28, 28, 28, 22)
        layout.setSpacing(14)

        lbl = QLabel(label)
        lbl.setStyleSheet("color:#8B949E; font-size:13px; background:transparent;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        if echo_password:
            field.setEchoMode(QLineEdit.Password)
        field.setStyleSheet(
            "background:#0D1117; color:white; border:1px solid #30363D; "
            "border-radius:8px; padding:8px 12px; font-size:13px;"
        )
        layout.addWidget(field)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(
            "background:#21262D; color:#8B949E; border:none; border-radius:8px; "
            "padding:8px 20px; font-size:13px;"
        )
        cancel_btn.clicked.connect(dlg.reject)

        confirm_btn = QPushButton("Confirm")
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet(
            "background:#FFD700; color:black; border:none; border-radius:8px; "
            "padding:8px 20px; font-size:13px; font-weight:bold;"
        )
        confirm_btn.clicked.connect(dlg.accept)
        field.returnPressed.connect(dlg.accept)

        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(confirm_btn)
        layout.addLayout(btns)

        accepted = dlg.exec() == QDialog.Accepted
        return field.text(), accepted

    def resizeEvent(self, event):
        self.bg_label.resize(self.size())
        self.overlay.resize(self.size())
        super().resizeEvent(event)


# ─────────────────────────────────────────────
#  MAIN DASHBOARD PAGE
# ─────────────────────────────────────────────
class DashboardPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.current_user = None
        self._apply_bg()

        self.admin_db       = database.AdminModule()
        self.renter_db      = database.RenterModule()
        self.room_db        = database.RoomModule()
        self.assignment_db  = database.AssignmentModule()
        self.payment_db     = database.PaymentModule()
        self.maintenance_db = database.MaintenanceModule()
        self.utility_db     = database.UtilityModule()
        self.visitor_db     = database.VisitorModule()
        self.app_db         = database.ApplicationModule()
        self.app_db.setup_table()   # ensure table exists on startup
        self.reports_db     = database.ReportsModule()
        self.switch_db      = database.SwitchRequestModule()
        self.switch_db.setup_table()   # ensure table exists on startup
        self.payroll_db     = database.PayrollModule()
        self.payroll_db.setup_table()
        self.utility_db.setup_table()

        # ── Auto-sync timer: keeps Admin dashboard fresh so renter-
        # submitted payments / new audit-log rows appear immediately.
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(15000)   # 15 s
        self._sync_timer.timeout.connect(self._auto_sync_tick)
        self._sync_timer.start()

        # ── Automated Overdue Status Engine: runs once on startup then
        # every 6 hours - marks Pending payments past the 5th-of-month
        # due date as Overdue automatically.
        self._run_auto_overdue()
        self._overdue_timer = QTimer(self)
        self._overdue_timer.setInterval(6 * 3600 * 1000)   # 6 hours
        self._overdue_timer.timeout.connect(self._run_auto_overdue)
        self._overdue_timer.start()

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── SIDEBAR ──────────────────────────────
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(260)
        self._apply_sidebar()
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 40, 20, 20)

        brand_row = QHBoxLayout()
        logo_label = QLabel("DormNorm")
        logo_label.setStyleSheet(f"color: {T('accent')}; font-family: 'Brush Script MT'; font-size: 32px; margin-bottom: 10px;")
        self.theme_toggle = ThemeToggleBtn(self._on_theme_toggle)
        brand_row.addWidget(logo_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        brand_row.addStretch()
        brand_row.addWidget(self.theme_toggle, alignment=Qt.AlignRight | Qt.AlignVCenter)
        sidebar_layout.addLayout(brand_row)
        sidebar_layout.addSpacing(20)

        self.pages_content = QStackedWidget()

        # MENU: index-to-name mapping
        # 0=Dashboard, 1=Applications, 2=Renters, 3=Staff, 4=All Rooms,
        # 5=Vacant, 6=Occupied, 7=Bills&Pay, 8=Reports, 9=Maintenance,
        # 10=Visitors, 11=Activity Logs, 12=My Profile, 13=Switch Requests,
        # 14=Staff Allowance, 15=Utility Bills
        self._all_menu_items = [
            ("  Dashboard",      0,  "fa5s.home",           "#58A6FF"),
            ("  Applications",   1,  "fa5s.file-alt",       "#FFD700"),
            ("  Renters",        2,  "fa5s.users",          "#3FB950"),
            ("  Staff",          3,  "fa5s.user-tie",       "#FFD700"),
            ("  All Rooms",      4,  "fa5s.bed",            "#F0883E"),
            ("  Vacant Rooms",   5,  "fa5s.door-open",      "#3FB950"),
            ("  Occupied Rooms", 6,  "fa5s.door-closed",    "#FF6B6B"),
            ("  Bills & Pay",    7,  "fa5s.credit-card",    "#D2A8FF"),
            ("  Reports",        8,  "fa5s.chart-bar",      "#79C0FF"),
            ("  Maintenance",    9,  "fa5s.tools",          "#FF6B6B"),
            ("  Visitors",       10, "fa5s.eye",            "#A8D8A8"),
            ("  Activity Logs",  11, "fa5s.list-alt",       "#8B949E"),
            ("  My Profile",     12, "fa5s.user-circle",    "#D2A8FF"),
            ("  Switch Requests",13, "fa5s.exchange-alt",   "#FFD700"),
            ("  Staff Allowance",14, "fa5s.hand-holding-usd","#3FB950"),
            ("  Utility Bills",  15, "fa5s.bolt",           "#F0883E"),
        ]

        # ── Scrollable nav area ──────────────────
        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        nav_scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { background: transparent; width: 4px; border-radius: 2px; }
            QScrollBar::handle:vertical { background: #30363D; border-radius: 2px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        nav_widget = QWidget()
        nav_widget.setStyleSheet("background: transparent;")
        nav_vbox = QVBoxLayout(nav_widget)
        nav_vbox.setContentsMargins(0, 0, 0, 0)
        nav_vbox.setSpacing(2)

        self.sidebar_buttons = []
        for text, index, icon_name, icon_color in self._all_menu_items:
            btn = QPushButton(text)
            btn.setIcon(qta.icon(icon_name, color=icon_color))
            btn.setIconSize(QSize(18, 18))
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("page_index", index)
            btn.clicked.connect(lambda _, i=index: self.switch_page(i))
            if index == 0:
                btn.setChecked(True)
            btn.setStyleSheet(self._sidebar_btn_style())
            nav_vbox.addWidget(btn)
            self.sidebar_buttons.append(btn)

        nav_vbox.addStretch()
        nav_scroll.setWidget(nav_widget)
        sidebar_layout.addWidget(nav_scroll, stretch=1)

        self.user_info_widget = QFrame()
        self.user_info_widget.setStyleSheet(f"background: {T('surface2')}; border-radius: 12px; padding: 8px;")
        ui_layout = QHBoxLayout(self.user_info_widget)
        ui_layout.setContentsMargins(10, 8, 10, 8)
        self.sidebar_avatar = AvatarWidget("?", 36)
        self.sidebar_user_lbl = QLabel("Not logged in")
        self.sidebar_user_lbl.setStyleSheet(f"color: {T('text')}; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        self.sidebar_role_lbl = QLabel("")
        self.sidebar_role_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 11px; background: transparent; border: none;")
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        info_col.addWidget(self.sidebar_user_lbl)
        info_col.addWidget(self.sidebar_role_lbl)
        ui_layout.addWidget(self.sidebar_avatar)
        ui_layout.addLayout(info_col)
        ui_layout.addStretch()
        sidebar_layout.addWidget(self.user_info_widget)
        sidebar_layout.addSpacing(8)

        logout_btn = QPushButton("  Logout")
        logout_btn.setIcon(qta.icon("fa5s.sign-out-alt", color=T("red")))
        logout_btn.setIconSize(QSize(16, 16))
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setStyleSheet(f"color: {T('red')}; background: transparent; font-weight: bold; padding: 10px; border: 1px solid {T('red')}; border-radius: 10px;")
        logout_btn.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(logout_btn)

        # ── BUILD PAGES ───────────────────────────
        self.home_page        = self._build_home_page()
        self.applications_page= self._build_applications_page()
        self.renters_page     = self._build_renters_page()
        self.staff_page       = self._build_staff_page()
        self.rooms_page       = self._build_rooms_page()
        self.vacant_page      = self._build_vacant_rooms_page()
        self.occupied_page    = self._build_occupied_rooms_page()
        self.payments_page    = self._build_payments_page()
        self.reports_page     = self._build_reports_page()
        self.maintenance_page = self._build_maintenance_page()
        self.visitors_page    = self._build_visitors_page()
        self.logs_page        = self._build_logs_page()
        self.profile_page     = self._build_profile_page()
        self.switch_page_widget   = self._build_switch_requests_page()
        self.allowance_page        = self._build_staff_allowance_page()
        self.utility_bills_page    = self._build_utility_bills_page()

        for p in [self.home_page, self.applications_page, self.renters_page,
                  self.staff_page, self.rooms_page, self.vacant_page,
                  self.occupied_page, self.payments_page, self.reports_page,
                  self.maintenance_page, self.visitors_page, self.logs_page,
                  self.profile_page, self.switch_page_widget,
                  self.allowance_page, self.utility_bills_page]:
            self.pages_content.addWidget(p)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.pages_content)

    # ── STYLE HELPERS ──────────────────────────
    def _apply_bg(self):
        self.setStyleSheet(f"background-color: {T('bg')};")

    def _apply_sidebar(self):
        self.sidebar.setStyleSheet(f"background-color: {T('surface')}; border-right: 1px solid {T('border')};")

    def _on_theme_toggle(self):
        self._rebuild_styles()

    def _rebuild_styles(self):
        self._apply_bg()
        self._apply_sidebar()
        for btn in self.sidebar_buttons:
            btn.setStyleSheet(self._sidebar_btn_style())
        self.refresh_home_stats()

    def _sidebar_btn_style(self):
        t = Theme.get()
        return f"""
            QPushButton {{ text-align: left; padding: 10px 15px; font-size: 13px; font-weight: bold;
                border-radius: 8px; color: {t['text_muted']}; border: none; background: transparent; }}
            QPushButton:hover {{ background-color: {t['surface2']}; color: {t['text']}; }}
            QPushButton:checked {{ background-color: {t['accent_dim']}; color: {t['accent']}; border-left: 3px solid {t['accent']}; }}
        """

    def _make_table(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.verticalHeader().setVisible(False)
        table.setStyleSheet(table_style())
        table.setAlternatingRowColors(True)
        return table

    def _set_table_row(self, table, row, values):
        table.insertRow(row)
        for col, val in enumerate(values):
            item = QTableWidgetItem(str(val) if val is not None else "-")
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            table.setItem(row, col, item)

    def _card_frame(self):
        f = QFrame()
        f.setStyleSheet(f"background-color: {T('surface')}; border-radius: 16px; border: 1px solid {T('border')};")
        return f

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {T('text')}; font-size: 16px; font-weight: bold;")
        return lbl

    # ── USER MANAGEMENT ───────────────────────
    def set_current_user(self, user_data):
        self.current_user = user_data
        role = user_data.get('role', 'Staff')
        name = user_data.get('full_name', 'User')

        self.sidebar_avatar.set_avatar(name)
        self.sidebar_user_lbl.setText(name[:22])
        self.sidebar_role_lbl.setText(role)

        self.welcome_label.setText(
            f'Hello, <span style="color:{T("accent")};">{name}</span>! '
            f'<span style="color:{T("text_muted")}; font-size:14px;">({role})</span>'
        )
        self._apply_role_permissions(role)
        self.refresh_home_stats()

    def _apply_role_permissions(self, role):
        is_admin  = (role == 'Admin')
        is_staff  = (role in ('Admin', 'Staff', 'Maintenance', 'Security'))
        is_renter = (role == 'Renter')
        # Hide Recent Activity panel from renters/staff dashboards (admin-only)
        if hasattr(self, 'recent_activity_label'):
            self.recent_activity_label.setVisible(is_admin)
        if hasattr(self, 'recent_logs_table'):
            self.recent_logs_table.setVisible(is_admin)
        if hasattr(self, 'renters_by_room_label'):
            self.renters_by_room_label.setVisible(is_admin)
        if hasattr(self, 'renters_by_room_widget'):
            self.renters_by_room_widget.setVisible(is_admin)
        # Hide unpaid/overdue section from renters
        if hasattr(self, 'unpaid_section_label'):
            self.unpaid_section_label.setVisible(is_admin or is_staff)
        if hasattr(self, 'unpaid_table'):
            self.unpaid_table.setVisible(is_admin or is_staff)

        # 0=Dashboard, 1=Applications, 2=Renters, 3=Staff, 4=AllRooms,
        # 5=Vacant, 6=Occupied, 7=Bills, 8=Reports, 9=Maintenance,
        # 10=Visitors, 11=Logs
        visibility = {
            0:  True,
            1:  is_admin,       # Applications - admin only
            2:  is_staff,       # Renters list - staff only (renters can't see others)
            3:  is_admin,
            4:  is_staff,
            5:  True,           # Vacant - everyone can see
            6:  is_staff,
            7:  True,           # Bills & Pay - everyone (renters see own payments)
            8:  is_admin,       # Reports - admin only
            9:  True,           # Maintenance - renters can submit
            10: is_staff,
            11: is_admin,
            12: True,           # My Profile - everyone
            13: True,           # Switch Requests - admins manage, renters submit
            14: is_admin,       # Staff Allowance - Admin only
            15: is_admin or is_renter,  # Utility Bills - admin manages; renters view own
        }
        for btn in self.sidebar_buttons:
            idx = btn.property("page_index")
            btn.setVisible(visibility.get(idx, True))

        if hasattr(self, 'staff_add_btn'):
            self.staff_add_btn.setVisible(is_admin)
            self.staff_edit_btn.setVisible(is_admin)
            self.staff_delete_btn.setVisible(is_admin)
        if hasattr(self, 'renter_delete_btn'):
            self.renter_delete_btn.setVisible(is_admin)
        if hasattr(self, 'renter_edit_btn'):
            # Edit is admin-only; Staff cannot register/edit/delete renters.
            self.renter_edit_btn.setVisible(is_admin)
        if hasattr(self, 'renter_pic_btn'):
            self.renter_pic_btn.setVisible(is_admin)
        if hasattr(self, 'renter_register_btn'):
            self.renter_register_btn.setVisible(is_admin)
        if hasattr(self, 'room_add_btn'):
            self.room_add_btn.setVisible(is_admin)
            self.room_delete_btn.setVisible(is_admin)
        if hasattr(self, 'room_maint_btn'):
            self.room_maint_btn.setVisible(is_admin)
            self.room_clear_maint_btn.setVisible(is_admin)
        if hasattr(self, 'payment_delete_btn'):
            self.payment_delete_btn.setVisible(is_admin)
        if hasattr(self, 'maint_delete_btn'):
            self.maint_delete_btn.setVisible(is_admin)
        if hasattr(self, 'maint_add_btn'):
            # Only renters can submit new maintenance requests.
            self.maint_add_btn.setVisible(is_renter)
        if hasattr(self, 'maint_resolve_btn'):
            # Only staff/admin can change request workflow status.
            self.maint_resolve_btn.setVisible(is_staff)
            self.maint_progress_btn.setVisible(is_staff)
        if hasattr(self, 'visitor_delete_btn'):
            self.visitor_delete_btn.setVisible(is_admin)
        if hasattr(self, 'app_reject_btn'):
            self.app_reject_btn.setVisible(is_admin)
            self.app_approve_btn.setVisible(is_admin)

        # Update applications badge in sidebar
        self._refresh_app_badge()

        if is_renter:
            self._customize_renter_dashboard()
            # Rename labels in sidebar for renter context
            for btn in self.sidebar_buttons:
                idx = btn.property("page_index")
                if idx == 7:
                    btn.setText("  My Payments")
                elif idx == 13:
                    btn.setText("  Request Room Switch")
                elif idx == 15:
                    btn.setText("  My Utility Bills")
                    # visibility already set by the dict above (is_admin or is_renter)
        else:
            for btn in self.sidebar_buttons:
                idx = btn.property("page_index")
                if idx == 7:
                    btn.setText("  Bills & Pay")
                elif idx == 13:
                    btn.setText("  Switch Requests")
                elif idx == 15:
                    btn.setText("  Utility Bills")

    def _refresh_app_badge(self):
        """Show a red badge on the Applications sidebar button if there are pending applications."""
        try:
            count = self.app_db.get_pending_count()
            for btn in self.sidebar_buttons:
                if btn.property("page_index") == 1:   # 1 = Applications
                    if count > 0:
                        btn.setText(f"  Applications  [{count}]")
                        btn.setStyleSheet(self._sidebar_btn_style().replace(
                            f"color: {T('text_muted')}",
                            f"color: {T('accent')}"
                        ))
                    else:
                        btn.setText("  Applications")
                        btn.setStyleSheet(self._sidebar_btn_style())
                    break
        except Exception:
            pass

    def _customize_renter_dashboard(self):
        """Replace dashboard stat cards and sections with renter-specific info."""
        renter_id = self.current_user.get('renter_id')
        if not renter_id:
            return
        try:
            # ── Room card ───────────────────────
            assignment = self.renter_db.get_renter_assignment(renter_id)
            if assignment:
                room_no   = assignment.get('room_number', '?')
                floor     = assignment.get('floor_level', '?')
                rate      = float(assignment.get('monthly_rate') or 0)
                self.stat_total_rooms.value_label.setText(f"Room {room_no}")
                self.stat_total_rooms.setToolTip(
                    f"Floor: {floor}\nRate: ₱{rate:,.0f}/mo"
                )
            else:
                self.stat_total_rooms.value_label.setText("No Room")

            # ── Payments ────────────────────────
            payments = self.renter_db.get_renter_payments(renter_id)
            import calendar as _cal_hs
            from datetime import date as _d_hs
            _today_hs = _d_hs.today()
            def _eff_hs(p):
                amt     = float(p.get('amount') or 0)
                balance = float(p.get('balance_amount') or 0)
                month_text = str(p.get('billing_month', '') or '').strip()
                due_date = None
                try:
                    parts = month_text.split()
                    mo_num = list(_cal_hs.month_name).index(parts[0])
                    yr_num = int(parts[1])
                    due_date = _d_hs(yr_num, mo_num, 5)
                except Exception:
                    pass
                if amt > 0 and balance > 0:
                    return "Overdue" if (due_date and _today_hs > due_date) else "Partial"
                if amt == 0 and due_date and _today_hs > due_date:
                    return "Overdue"
                if amt == 0:
                    return "Pending"
                if amt > 0 and balance == 0:
                    return "Paid"
                return p.get('status', 'Pending')
            pending  = sum(1 for p in payments if _eff_hs(p) in ('Pending', 'Overdue'))
            # Total collected = Paid + amounts already paid in Partial records
            total_paid = sum(
                float(p.get('amount') or 0) for p in payments
                if _eff_hs(p) in ('Paid', 'Partial')
                and float(p.get('amount') or 0) > 0
            )
            self.stat_payments.value_label.setText(str(pending))
            self.stat_payments.setToolTip(f"Total paid to date: ₱{total_paid:,.0f}")
            self.stat_vacant.value_label.setText(f"₱{total_paid:,.0f}")

            # ── Maintenance ─────────────────────
            maint = self.renter_db.get_renter_maintenance(renter_id)
            pending_m = sum(1 for m in maint if m.get('status') == 'Pending')
            self.stat_maint.value_label.setText(str(pending_m))

            # ── Rename stat cards for renter context ──
            for card, title in [
                (self.stat_total_rooms, "My Room"),
                (self.stat_vacant,      "Total Paid"),
                (self.stat_payments,    "Pending Bills"),
                (self.stat_maint,       "Maintenance"),
            ]:
                # Update the title label inside the card (first QLabel in layout)
                for i in range(card.layout().count()):
                    item = card.layout().itemAt(i)
                    if item and item.layout():
                        for j in range(item.layout().count()):
                            sub = item.layout().itemAt(j)
                            if sub and sub.widget() and isinstance(sub.widget(), QLabel):
                                lbl = sub.widget()
                                if lbl.text() in ("Total Rooms", "Vacant Rooms",
                                                   "Pending Bills", "Maintenance",
                                                   "My Room", "Total Paid"):
                                    lbl.setText(title)
                                break
                        break

            # ── Payment methods info panel ───────
            # Show available payment methods in a notice below maintenance cards
            self._show_renter_payment_methods_panel()
            # ── Utility transparency panel ───────
            self._show_renter_transparency_panel()

        except Exception as e:
            print(f"[_customize_renter_dashboard] {e}")

    def _show_renter_payment_methods_panel(self):
        """Add a payment methods info card to the renter dashboard."""
        try:
            # Remove old panel if exists
            if hasattr(self, '_renter_pay_panel') and self._renter_pay_panel:
                try:
                    self._renter_pay_panel.setParent(None)
                    self._renter_pay_panel.deleteLater()
                except Exception:
                    pass

            t = Theme.get()
            panel = QFrame()
            panel.setStyleSheet(
                f"background: {t['surface']}; border-radius: 14px; "
                f"border: 1px solid {t['border']};"
            )
            pl = QVBoxLayout(panel)
            pl.setContentsMargins(20, 16, 20, 16)
            pl.setSpacing(10)

            hdr = QLabel("Payment Methods Accepted")
            hdr.setStyleSheet(f"color: {t['text']}; font-size: 15px; font-weight: bold; "
                              f"background: transparent; border: none;")
            pl.addWidget(hdr)

            methods = [
                ("Bank Transfer",  "BDO / BPI / Metrobank - deposit to dorm account"),
                ("GCash / Maya",   "Send to registered dorm number, include your name"),
                ("Cash",           "Pay in person at the admin office, request a receipt"),
                ("Over-the-Counter", "7-Eleven, Bayad Center - ask admin for reference no."),
            ]
            grid = QGridLayout()
            grid.setSpacing(8)
            for i, (method_title, desc) in enumerate(methods):
                m_lbl = QLabel(method_title)
                m_lbl.setStyleSheet(f"color: {t['accent']}; font-size: 13px; font-weight: bold; "
                                    f"background: transparent; border: none;")
                d_lbl = QLabel(desc)
                d_lbl.setStyleSheet(f"color: {t['text_muted']}; font-size: 12px; "
                                    f"background: transparent; border: none;")
                d_lbl.setWordWrap(True)
                grid.addWidget(m_lbl, i, 0)
                grid.addWidget(d_lbl, i, 1)
            pl.addLayout(grid)

            note = QLabel("Note: Always ask for an official receipt or screenshot after payment.")
            note.setStyleSheet(f"color: {t['orange']}; font-size: 11px; "
                               f"background: transparent; border: none;")
            note.setWordWrap(True)
            pl.addWidget(note)

            # Insert into home page layout (before stretch at end)
            home_inner = self.home_page.widget()
            home_layout = home_inner.layout()
            # Insert before the last stretch
            count = home_layout.count()
            home_layout.insertWidget(count - 1, panel)
            self._renter_pay_panel = panel

        except Exception as e:
            print(f"[_show_renter_payment_methods_panel] {e}")

    def switch_page(self, index):
        self.pages_content.setCurrentIndex(index)
        refresh_map = {
            0:  self.refresh_home_stats,
            1:  self.load_applications,
            2:  self.load_renters,
            3:  self.load_staff,
            4:  self.load_rooms,
            5:  self.load_vacant_rooms,
            6:  self.load_occupied_rooms,
            7:  self.load_payments,
            8:  self.load_reports,
            9:  self.load_maintenance,
            10: self.load_visitors,
            11: self.load_logs,
            12: self.load_profile,
            13: self.load_switch_requests,
            14: self.load_staff_allowance,
            15: self.load_utility_bills,
        }
        if index in refresh_map:
            refresh_map[index]()

    def handle_logout(self):
        if self.current_user:
            if self.current_user.get('admin_id'):
                self.admin_db.add_log(
                    self.current_user['admin_id'], 'LOGOUT',
                    f"{self.current_user['full_name']} logged out."
                )
            elif self.current_user.get('renter_id'):
                self.admin_db.add_log(
                    None, 'LOGOUT',
                    f"{self.current_user.get('full_name', 'Renter')} logged out.",
                    actor_role='Renter',
                    renter_id=self.current_user['renter_id']
                )
        self.current_user = None
        # Reset sidebar button labels to admin/staff defaults so that a
        # subsequent login as a different role starts with clean labels.
        _default_labels = {
            7:  "  Bills & Pay",
            13: "  Switch Requests",
            15: "  Utility Bills",
        }
        for btn in self.sidebar_buttons:
            idx = btn.property("page_index")
            if idx in _default_labels:
                btn.setText(_default_labels[idx])
        # Reset sidebar user info
        self.sidebar_avatar.set_avatar("?")
        self.sidebar_user_lbl.setText("Not logged in")
        self.sidebar_role_lbl.setText("")
        self.controller.parent().fade_to_page(1)

    # ══════════════════════════════════════════
    #  HOME / DASHBOARD PAGE
    # ══════════════════════════════════════════
    def _build_home_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # Header
        header = QHBoxLayout()
        self.welcome_label = QLabel(f'Hello, <span style="color:{T("accent")};">Admin</span>!')
        self.welcome_label.setStyleSheet(f"color: {T('text')}; font-size: 28px; font-weight: bold;")
        self.welcome_label.setTextFormat(Qt.RichText)
        date_lbl = QLabel(QDate.currentDate().toString("dddd, MMMM d, yyyy"))
        date_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 14px;")
        header.addWidget(self.welcome_label)
        header.addStretch()
        header.addWidget(date_lbl)
        layout.addLayout(header)

        # ── ROW 1: STAT CARDS ─────────────────
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(14)

        self.stat_total_rooms = StatCard(
            "Total Rooms", "-", T("blue"), "fa5s.building",
            on_click=lambda: self.switch_page(4)
        )
        self.stat_vacant = StatCard(
            "Vacant Rooms", "-", T("green"), "fa5s.door-open",
            subtitle="Available now",
            on_click=lambda: self.switch_page(5)
        )
        self.stat_occupied = StatCard(
            "Occupied", "-", T("red"), "fa5s.door-closed",
            subtitle="Rooms with renters",
            on_click=lambda: self.switch_page(6)
        )
        self.stat_boarders = StatCard(
            "Currently Assigned", "-", T("accent"), "fa5s.users",
            on_click=lambda: self.switch_page(2)
        )
        self.stat_maint = StatCard(
            "Pending Maint.", "-", T("orange"), "fa5s.tools",
            on_click=lambda: self.switch_page(9)
        )
        self.stat_payments = StatCard(
            "Pending Payments", "-", T("purple"), "fa5s.exclamation-circle",
            on_click=lambda: self.switch_page(7)
        )

        for card in [self.stat_total_rooms, self.stat_vacant, self.stat_occupied,
                     self.stat_boarders, self.stat_maint, self.stat_payments]:
            stats_layout.addWidget(card)
        layout.addLayout(stats_layout)

        # ── ROW 2: ROOM OVERVIEW + PAYMENT DONUT ─
        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        # Room availability breakdown (bar: available vs occupied vs maintenance)
        room_bar_card = self._card_frame()
        room_bar_card.setMinimumHeight(260)
        rbc_layout = QVBoxLayout(room_bar_card)
        rbc_layout.setContentsMargins(16, 16, 16, 16)
        lbl = QLabel("Room Status Breakdown")
        lbl.setStyleSheet(f"color: {T('text')}; font-size: 14px; font-weight: bold; border: none; background: transparent;")
        rbc_layout.addWidget(lbl)
        self.room_status_chart = BarChartWidget("")
        rbc_layout.addWidget(self.room_status_chart)
        charts_row.addWidget(room_bar_card, 2)

        pay_card = self._card_frame()
        pay_card.setMinimumHeight(260)
        pay_layout = QVBoxLayout(pay_card)
        pay_layout.setContentsMargins(16, 16, 16, 16)
        self.payment_donut = DonutChartWidget("Payments")
        pay_layout.addWidget(self.payment_donut)
        charts_row.addWidget(pay_card, 1)

        renter_card = self._card_frame()
        renter_card.setMinimumHeight(260)
        rc_layout = QVBoxLayout(renter_card)
        rc_layout.setContentsMargins(16, 16, 16, 16)
        self.renter_chart = BarChartWidget("Renters by Type")
        rc_layout.addWidget(self.renter_chart)
        charts_row.addWidget(renter_card, 2)

        layout.addLayout(charts_row)

        # ── ROW 3: ROOM CARDS PREVIEW ─────────
        room_preview_hdr = QHBoxLayout()
        room_preview_hdr.addWidget(self._section_label("Rooms at a Glance"))
        see_all = QPushButton("See All Rooms")
        see_all.setStyleSheet(f"color: {T('blue')}; background: transparent; border: none; font-size: 13px; font-weight: bold;")
        see_all.setCursor(Qt.PointingHandCursor)
        see_all.clicked.connect(lambda: self.switch_page(4))
        room_preview_hdr.addStretch()
        room_preview_hdr.addWidget(see_all)
        layout.addLayout(room_preview_hdr)

        self.room_cards_scroll = QScrollArea()
        self.room_cards_scroll.setFixedHeight(180)
        self.room_cards_scroll.setWidgetResizable(True)
        self.room_cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.room_cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.room_cards_scroll.setStyleSheet("border: none; background: transparent;")
        self.room_cards_inner = QWidget()
        self.room_cards_inner.setStyleSheet("background: transparent;")
        self.room_cards_row = QHBoxLayout(self.room_cards_inner)
        self.room_cards_row.setContentsMargins(0, 4, 0, 4)
        self.room_cards_row.setSpacing(12)
        self.room_cards_row.addStretch()
        self.room_cards_scroll.setWidget(self.room_cards_inner)
        layout.addWidget(self.room_cards_scroll)

        # ── ROW 4: MAINTENANCE PANEL ──────────
        maint_hdr = QHBoxLayout()
        maint_hdr.addWidget(self._section_label("Pending Maintenance"))
        see_maint = QPushButton("See All")
        see_maint.setStyleSheet(f"color: {T('blue')}; background: transparent; border: none; font-size: 13px; font-weight: bold;")
        see_maint.setCursor(Qt.PointingHandCursor)
        see_maint.clicked.connect(lambda: self.switch_page(9))
        maint_hdr.addStretch()
        maint_hdr.addWidget(see_maint)
        layout.addLayout(maint_hdr)

        self.maint_cards_widget = QWidget()
        self.maint_cards_widget.setStyleSheet("background: transparent;")
        self.maint_cards_layout = QVBoxLayout(self.maint_cards_widget)
        self.maint_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.maint_cards_layout.setSpacing(8)
        layout.addWidget(self.maint_cards_widget)

        # ── ROW 4b: UNPAID / OVERDUE RENTERS (admin real-time panel) ─
        unpaid_hdr = QHBoxLayout()
        self.unpaid_section_label = self._section_label("Unpaid & Overdue Renters")
        self.unpaid_section_label.setStyleSheet(f"color: {T('red')}; font-size: 16px; font-weight: bold;")
        see_payments = QPushButton("See All Payments →")
        see_payments.setStyleSheet(f"color: {T('blue')}; background: transparent; border: none; font-size: 13px; font-weight: bold;")
        see_payments.setCursor(Qt.PointingHandCursor)
        see_payments.clicked.connect(lambda: self.switch_page(7))
        unpaid_hdr.addWidget(self.unpaid_section_label)
        unpaid_hdr.addStretch()
        unpaid_hdr.addWidget(see_payments)
        layout.addLayout(unpaid_hdr)

        self.unpaid_table = self._make_table([
            "Invoice", "Renter", "Room", "Bed", "Billing Month", "Amount (₱)", "Status"
        ])
        self.unpaid_table.setMaximumHeight(220)
        layout.addWidget(self.unpaid_table)

        # ── ROW 5: ACTIVE RENTERS ─────────────
        faces_hdr = QHBoxLayout()
        faces_hdr.addWidget(self._section_label("Currently Assigned"))
        see_renters = QPushButton("See All")
        see_renters.setStyleSheet(f"color: {T('blue')}; background: transparent; border: none; font-size: 13px; font-weight: bold;")
        see_renters.setCursor(Qt.PointingHandCursor)
        see_renters.clicked.connect(lambda: self.switch_page(2))
        faces_hdr.addStretch()
        faces_hdr.addWidget(see_renters)
        layout.addLayout(faces_hdr)

        self.renter_faces_area = QScrollArea()
        self.renter_faces_area.setFixedHeight(88)
        self.renter_faces_area.setWidgetResizable(True)
        self.renter_faces_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.renter_faces_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.renter_faces_area.setStyleSheet("border: none; background: transparent;")
        self.renter_faces_inner = QWidget()
        self.renter_faces_inner.setStyleSheet("background: transparent;")
        self.renter_faces_row = QHBoxLayout(self.renter_faces_inner)
        self.renter_faces_row.setContentsMargins(0, 4, 0, 4)
        self.renter_faces_row.setSpacing(10)
        self.renter_faces_row.addStretch()
        self.renter_faces_area.setWidget(self.renter_faces_inner)
        layout.addWidget(self.renter_faces_area)

        # ── ROW 6b: RENTER PAYMENT STATUS TABLE (Admin real-time) ────────
        status_hdr = QHBoxLayout()
        self.renter_status_section_lbl = self._section_label("Renter Payment Status - This Month")
        self.renter_status_section_lbl.setStyleSheet(
            f"color: {T('text')}; font-size: 16px; font-weight: bold;")
        see_reports_btn = QPushButton("Full Reports")
        see_reports_btn.setStyleSheet(
            f"color: {T('blue')}; background: transparent; border: none; "
            f"font-size: 13px; font-weight: bold;")
        see_reports_btn.setCursor(Qt.PointingHandCursor)
        see_reports_btn.clicked.connect(lambda: self.switch_page(8))
        status_hdr.addWidget(self.renter_status_section_lbl)
        status_hdr.addStretch()
        status_hdr.addWidget(see_reports_btn)
        layout.addLayout(status_hdr)

        # Summary badge row
        self.renter_status_summary = QHBoxLayout()
        self.renter_status_summary.setSpacing(10)
        self._renter_status_badges = {}
        for label, color_key in [("Paid", "green"), ("Pending", "accent"), ("Overdue", "red"), ("Partial", "orange")]:
            badge = QLabel(label + "  0")
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(
                f"background: {T(color_key)}22; color: {T(color_key)}; "
                f"border: 1px solid {T(color_key)}; border-radius: 10px; "
                f"padding: 4px 14px; font-size: 12px; font-weight: bold;")
            self.renter_status_summary.addWidget(badge)
            self._renter_status_badges[label] = badge
        self.renter_status_summary.addStretch()
        layout.addLayout(self.renter_status_summary)

        self.renter_status_table = self._make_table([
            "Room", "Bed", "Renter Name", "Billing Month",
            "Status", "Paid This Month (₱)", "Debt This Month (₱)", "Total Outstanding (₱)"
        ])
        self.renter_status_table.setMaximumHeight(280)
        layout.addWidget(self.renter_status_table)

        # ── ROW 6: RECENT ACTIVITY (admin only) ────────────
        self.recent_activity_label = self._section_label("Recent Activity")
        layout.addWidget(self.recent_activity_label)
        self.recent_logs_table = self._make_table(["Admin", "Action", "Details", "Timestamp"])
        self.recent_logs_table.setMaximumHeight(200)
        layout.addWidget(self.recent_logs_table)
        # ── RENTERS BY ROOM GROUP (admin only) ──────────────────
        self.renters_by_room_label = self._section_label("Renters by Room")
        layout.addWidget(self.renters_by_room_label)

        self.renters_by_room_widget = QWidget()
        self.renters_by_room_widget.setStyleSheet("background: transparent;")
        self.renters_by_room_layout = QVBoxLayout(self.renters_by_room_widget)
        self.renters_by_room_layout.setContentsMargins(0, 0, 0, 0)
        self.renters_by_room_layout.setSpacing(10)
        layout.addWidget(self.renters_by_room_widget)

        layout.addStretch()

        scroll.setWidget(page)
        return scroll

    def refresh_home_stats(self):
        t = Theme.get()

        # ── Room stats ───────────────────────
        total_rooms = 0
        vacant_count = 0
        occupied_count = 0
        maint_count_rooms = 0
        try:
            rooms = self.room_db.get_all_rooms_with_beds()
            total_rooms = len(rooms)
            maint_count_rooms = sum(1 for r in rooms if r.get('status') == 'Under Maintenance')
            def _is_full(r):
                cap = int(r.get('capacity') or 0); occ = int(r.get('occupied') or 0)
                return cap > 0 and occ >= cap and r.get('status') != 'Under Maintenance'
            def _has_occupant(r):
                occ = int(r.get('occupied') or 0)
                return occ > 0 and r.get('status') != 'Under Maintenance'
            occupied_count = sum(1 for r in rooms if _has_occupant(r))
            vacant_count   = sum(
                1 for r in rooms
                if r.get('status') != 'Under Maintenance'
                and int(r.get('capacity') or 0) > int(r.get('occupied') or 0)
            )

            self.stat_total_rooms.set_value(total_rooms)
            self.stat_vacant.set_value(vacant_count)
            self.stat_occupied.set_value(occupied_count)

            # Room status bar chart - Available vs Occupied vs Maintenance
            bar_data = []
            if vacant_count:    bar_data.append(("Available", vacant_count, t['green']))
            if occupied_count:  bar_data.append(("Full", occupied_count, t['red']))
            if maint_count_rooms: bar_data.append(("Maint.", maint_count_rooms, t['orange']))
            reserved = sum(1 for r in rooms if r.get('status') == 'Reserved')
            if reserved:        bar_data.append(("Reserved", reserved, t['blue']))
            if not bar_data:    bar_data = [("No Rooms", 1, t['border'])]
            self.room_status_chart.set_data(bar_data)

            # Room cards preview (first 10)
            self._refresh_room_cards(rooms[:10])
        except Exception:
            pass

        # ── Renter stats ─────────────────────
        renters_count = 0
        try:
            stats = self.renter_db.get_stats()
            if stats:
                renters_count = stats.get("renters", 0)
                self.stat_boarders.set_value(renters_count)
        except Exception:
            pass

        # ── Renter chart ─────────────────────
        try:
            conn = self.renter_db.connect()
            if conn:
                cur = conn.cursor(dictionary=True)
                cur.execute("""SELECT r.occupation_type, COUNT(*) AS c
                               FROM renters r
                               JOIN assignments a ON a.renter_id = r.renter_id
                                                 AND a.status = 'Active'
                               WHERE r.renter_status='Active'
                               GROUP BY r.occupation_type""")
                rows = cur.fetchall()
                colors = [t['accent'], t['blue'], t['green'], t['orange'], t['red']]
                occ_data = [(r['occupation_type'], r['c'], colors[i % len(colors)]) for i, r in enumerate(rows)]
                conn.close()
                if not occ_data:
                    occ_data = [("Student", renters_count, t['accent'])]
                self.renter_chart.set_data(occ_data)
        except Exception:
            pass

        # ── Maintenance & Payment stats ───────
        maint_pending = 0
        pay_count = 0
        paid_count = 0
        overdue_count = 0
        partial_count = 0
        try:
            conn = self.maintenance_db.connect()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT COUNT(*) AS c FROM maintenance_requests WHERE status='Pending'")
                maint_pending = cursor.fetchone()['c']
                self.stat_maint.set_value(maint_pending)

                # Compute effective statuses using billing_month 5th rule
                from datetime import date as _d2
                import calendar as _cal2
                today2 = _d2.today()
                cursor.execute("SELECT amount, balance_amount, billing_month, status FROM payments")
                all_pays = cursor.fetchall()
                for p in all_pays:
                    amt     = float(p.get('amount') or 0)
                    balance = float(p.get('balance_amount') or 0)
                    month_text = str(p.get('billing_month', '') or '').strip()
                    due_date = None
                    try:
                        parts = month_text.split()
                        mo_num = list(_cal2.month_name).index(parts[0])
                        yr_num = int(parts[1])
                        due_date = _d2(yr_num, mo_num, 5)
                    except Exception:
                        pass
                    if amt > 0 and balance > 0:
                        eff = "Overdue" if (due_date and today2 > due_date) else "Partial"
                    elif amt == 0 and due_date and today2 > due_date:
                        eff = "Overdue"
                    elif amt == 0:
                        eff = "Pending"
                    elif amt > 0 and balance == 0:
                        eff = "Paid"
                    else:
                        eff = p.get('status', 'Pending')
                    if eff == 'Paid':    paid_count += 1
                    elif eff == 'Pending': pay_count += 1
                    elif eff == 'Overdue': overdue_count += 1
                    elif eff == 'Partial': partial_count += 1
                self.stat_payments.set_value(pay_count + overdue_count)
                conn.close()
        except Exception:
            pass

        # Payment donut
        pay_donut_data = []
        if paid_count:    pay_donut_data.append(("Paid", paid_count, t['green']))
        if pay_count:     pay_donut_data.append(("Pending", pay_count, t['accent']))
        if overdue_count: pay_donut_data.append(("Overdue", overdue_count, t['red']))
        if partial_count: pay_donut_data.append(("Partial", partial_count, t['orange']))
        if not pay_donut_data: pay_donut_data = [("No Data", 1, t['border'])]
        self.payment_donut.set_data(pay_donut_data)

        # ── Pending maintenance cards ─────────
        self._refresh_maintenance_cards()

        # ── Recent activity ───────────────────
        # For renters → show just THEIR activity (transparency).
        # For staff/admin → show full system activity.
        try:
            if self.current_user and self.current_user.get('role') == 'Renter' \
               and self.current_user.get('renter_id'):
                logs = self.admin_db.get_recent_activity_for_renter(
                    self.current_user['renter_id']
                ) or []
                # Normalize key naming
                for l in logs:
                    l['admin_name'] = l.get('actor_name', l.get('admin_name', '-'))
            else:
                logs = self.admin_db.get_activity_logs() or []
        except Exception:
            logs = []
        self.recent_logs_table.setRowCount(0)
        if not logs:
            self._set_table_row(self.recent_logs_table, 0,
                                ["No recent activity yet", "", "", ""])
        else:
            for i, log in enumerate(logs[:8]):
                self._set_table_row(self.recent_logs_table, i, [
                    log.get('admin_name', '-'),
                    log.get('action_type', '-'),
                    log.get('action_text', '-'),
                    str(log.get('log_timestamp', '-')),
                ])

        self._refresh_renter_faces()

        # ── Unpaid / Overdue renters real-time panel ──────────
        try:
            is_admin_role = (self.current_user or {}).get('role') in ('Admin', 'Staff', 'Maintenance', 'Security')
            if hasattr(self, 'unpaid_table'):
                self.unpaid_table.setVisible(is_admin_role)
                self.unpaid_section_label.setVisible(is_admin_role)
            if is_admin_role and hasattr(self, 'unpaid_table'):
                unpaid_rows = self.payment_db.get_unpaid_overdue_renters()
                self.unpaid_table.setRowCount(0)
                tc = Theme.get()
                status_c = {"Overdue": tc['red'], "Pending": tc['accent']}
                if not unpaid_rows:
                    self._set_table_row(self.unpaid_table, 0, ["All renters are paid up", "", "", "", "", "", ""])
                else:
                    for i, row in enumerate(unpaid_rows):
                        self._set_table_row(self.unpaid_table, i, [
                            row.get('invoice_number', '-'),
                            row.get('renter_name', '-'),
                            row.get('room_number') or '-',
                            row.get('bed_assignment') or '-',
                            row.get('billing_month', '-'),
                            f"₱{float(row.get('amount', 0)):,.2f}",
                            row.get('status', '-'),
                        ])
                        color = status_c.get(row.get('status', ''), tc['text'])
                        self.unpaid_table.item(i, 6).setForeground(QColor(color))
        except Exception as _ue:
            print(f"[unpaid panel] {_ue}")

        # Refresh applications badge in sidebar
        self._refresh_app_badge()

        # ── Renter Payment Status section (admin-only) ────────
        self._load_renter_status_dashboard()
        self._refresh_renters_by_room()

    def _refresh_room_cards(self, rooms):
        while self.room_cards_row.count() > 1:
            item = self.room_cards_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for room in rooms:
            card = RoomCardWidget(room, on_click=lambda r=room: self._show_room_detail(r))
            self.room_cards_row.insertWidget(self.room_cards_row.count() - 1, card)

    def _load_renter_status_dashboard(self):
        """Populate the Renter Payment Status section on the dashboard."""
        try:
            is_admin = (self.current_user or {}).get('role') in (
                'Admin', 'Staff', 'Maintenance', 'Security')

            # Hide for renters
            for attr in ('renter_status_table', 'renter_status_section_lbl'):
                if hasattr(self, attr):
                    getattr(self, attr).setVisible(is_admin)
            if hasattr(self, '_renter_status_badges'):
                for badge in self._renter_status_badges.values():
                    badge.setVisible(is_admin)

            if not is_admin:
                return

            data = self.payment_db.get_renter_payment_status_summary()
            t = Theme.get()
            status_colors = {
                'Paid':    t['green'],
                'Pending': t['accent'],
                'Overdue': t['red'],
                'Partial': t['orange'],
            }

            # Update summary badges
            counts = {'Paid': 0, 'Pending': 0, 'Overdue': 0, 'Partial': 0}
            for row in data:
                s = row.get('status', 'Pending')
                if s in counts:
                    counts[s] += 1

            badge_labels = {'Paid': 'Paid', 'Pending': 'Pending', 'Overdue': 'Overdue', 'Partial': 'Partial'}
            if hasattr(self, '_renter_status_badges'):
                for key, badge in self._renter_status_badges.items():
                    n = counts.get(key, 0)
                    badge.setText(f"{badge_labels.get(key, key)}  {n}")

            # Populate table
            if not hasattr(self, 'renter_status_table'):
                return
            self.renter_status_table.setRowCount(0)
            if not data:
                self._set_table_row(self.renter_status_table, 0,
                    ["No active renters found", "", "", "", "", "", "", ""])
                return

            for i, row in enumerate(data):
                status = row.get('status', 'Pending')
                self._set_table_row(self.renter_status_table, i, [
                    row.get('room_number', '-'),
                    row.get('bed', '-'),
                    row.get('full_name', '-'),
                    row.get('billing_month', '-'),
                    status,
                    f"₱{row.get('paid_this_month', 0):,.2f}",
                    f"₱{row.get('debt_this_month', 0):,.2f}",
                    f"₱{row.get('total_outstanding', 0):,.2f}",
                ])
                color = status_colors.get(status, t['text'])
                self.renter_status_table.item(i, 4).setForeground(QColor(color))
                if row.get('total_outstanding', 0) > 0:
                    self.renter_status_table.item(i, 7).setForeground(QColor(t['red']))
                if row.get('debt_this_month', 0) > 0:
                    self.renter_status_table.item(i, 6).setForeground(QColor(t['orange']))

        except Exception as e:
            print(f"[_load_renter_status_dashboard] {e}")

    def _show_room_detail(self, room):
        """Show full room info + amenities in a clean dialog."""
        t = Theme.get()
        cap  = int(room.get('capacity', 1) or 1)
        occ  = int(room.get('occupied', 0) or 0)
        avail = cap - occ

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Room {room.get('room_number','?')} - Full Details")
        dlg.setFixedWidth(500)
        dlg.setStyleSheet(dialog_style())
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # Photo
        photo_path = resolve_photo_path(room.get('photo_path') or '')
        if photo_path:
            photo_lbl = QLabel()
            pix = QPixmap(photo_path).scaled(440, 200, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            photo_lbl.setPixmap(pix)
            photo_lbl.setStyleSheet("border-radius: 10px; background: #0D1117;")
            photo_lbl.setFixedHeight(200)
            photo_lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(photo_lbl)

        # Title row
        title_row = QHBoxLayout()
        room_num_lbl = QLabel(f"Room {room.get('room_number','?')}")
        room_num_lbl.setStyleSheet(f"color: {t['text']}; font-size: 22px; font-weight: bold; border: none; background: transparent;")
        status = room.get('status', '?')
        status_colors = {'Available': t['green'], 'Full': t['red'], 'Under Maintenance': t['orange']}
        st_color = status_colors.get(status, t['text_muted'])
        status_lbl = QLabel(f"{status}")
        status_lbl.setStyleSheet(f"color: {st_color}; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        title_row.addWidget(room_num_lbl)
        title_row.addStretch()
        title_row.addWidget(status_lbl)
        layout.addLayout(title_row)

        # Key info grid
        info_widget = QWidget()
        info_widget.setStyleSheet(f"background: {t['surface2']}; border-radius: 10px;")
        info_grid = QGridLayout(info_widget)
        info_grid.setContentsMargins(16, 12, 16, 12)
        info_grid.setSpacing(8)

        def inf(label, value, col_offset=0):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {t['text_muted']}; font-size: 12px; background: transparent; border: none;")
            val = QLabel(str(value))
            val.setStyleSheet(f"color: {t['text']}; font-size: 13px; font-weight: bold; background: transparent; border: none;")
            return lbl, val

        fields = [
            ("Floor:", room.get('floor_level','?')),
            ("Capacity:", f"{cap} beds"),
            ("Occupied:", f"{occ} beds"),
            ("Available:", f"{avail} bed{'s' if avail != 1 else ''}"),
            ("Monthly Rate:", f"₱{float(room.get('monthly_rate',0)):,.2f}"),
            ("Notes:", room.get('description','-') or '-'),
        ]
        for i, (lbl_txt, val_txt) in enumerate(fields):
            row_i = i // 2
            col_base = (i % 2) * 2
            lbl, val = inf(lbl_txt, val_txt)
            info_grid.addWidget(lbl, row_i, col_base)
            info_grid.addWidget(val, row_i, col_base + 1)
        layout.addWidget(info_widget)

        # Amenities
        try:
            ams = self.room_db.get_amenities(room.get('room_id'))
        except Exception:
            ams = []

        if ams:
            am_hdr = QLabel("Amenities & Inclusions")
            am_hdr.setStyleSheet(f"color: {t['text']}; font-size: 14px; font-weight: bold; border: none; background: transparent;")
            layout.addWidget(am_hdr)

            am_grid = QGridLayout()
            am_grid.setSpacing(8)
            for idx, am in enumerate(ams):
                cond_colors = {'Good': t['green'], 'Fair': t['orange'], 'Poor': t['red']}
                cond = am.get('item_condition', 'Good')
                pill = QLabel(f"  {am.get('amenity_name','')}  ×{am.get('quantity',1)}  [{cond}]")
                pill.setStyleSheet(
                    f"background: {t['surface2']}; color: {cond_colors.get(cond, t['text'])}; "
                    f"border: 1px solid {t['border']}; padding: 5px 10px; border-radius: 8px; font-size: 11px;"
                )
                am_grid.addWidget(pill, idx // 2, idx % 2)
            layout.addLayout(am_grid)
        else:
            no_am = QLabel("No amenities listed for this room.")
            no_am.setStyleSheet(f"color: {t['text_muted']}; font-size: 12px; border: none; background: transparent;")
            layout.addWidget(no_am)

        # Buttons
        btn_row = QHBoxLayout()
        close_btn = make_btn("Close", T("surface2"), T("text"))
        close_btn.clicked.connect(dlg.reject)
        apply_btn = make_btn("  Apply for this Room", T("accent"), "black", icon="fa5s.paper-plane", icon_color="black")
        apply_btn.clicked.connect(lambda: (dlg.accept(), self._open_apply_for(room)))
        # Apply only makes sense for prospective renters. Staff/Admin manage
        # rooms directly and shouldn't see this button.
        role = (self.current_user or {}).get('role', '')
        apply_btn.setVisible(avail > 0 and role == 'Renter')
        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        btn_row.addWidget(apply_btn)
        layout.addLayout(btn_row)

        dlg.exec()

    def _open_apply_for(self, room):
        """Quick-apply for a specific room from the dashboard view."""
        QMessageBox.information(
            self, "Apply to Rent",
            f"To apply for Room {room.get('room_number','?')}, please go to the Welcome page "
            f"and click 'Apply to Rent', then specify your preferred room. "
            f"Or contact the admin directly."
        )


    def _refresh_maintenance_cards(self):
        # Clear existing cards
        while self.maint_cards_layout.count():
            item = self.maint_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            requests = self.maintenance_db.get_all_requests()
            pending = [r for r in requests if r.get('status') == 'Pending'][:4]
            if not pending:
                empty_lbl = QLabel("No pending maintenance requests.")
                empty_lbl.setStyleSheet(f"color: {T('green')}; font-size: 13px; padding: 10px;")
                self.maint_cards_layout.addWidget(empty_lbl)
                return
            for req in pending:
                req_copy = dict(req)
                def make_resolve(r=req_copy):
                    def fn():
                        ok = self.maintenance_db.update_status(
                            r['request_id'], "Completed",
                            "Resolved from dashboard.",
                            QDate.currentDate().toString("yyyy-MM-dd")
                        )
                        if ok:
                            if self.current_user and self.current_user.get('admin_id'):
                                self.admin_db.add_log(
                                    self.current_user['admin_id'],
                                    'RESOLVE_MAINTENANCE',
                                    f"Resolved request ID {r['request_id']} from dashboard"
                                )
                            self._refresh_maintenance_cards()
                            self.stat_maint.set_value(
                                int(self.stat_maint.value_label.text() or 0) - 1
                            )
                    return fn

                def make_view(r=req_copy):
                    def fn():
                        dlg = MaintenanceDetailDialog(self, r)
                        dlg.exec()
                    return fn

                role = (self.current_user or {}).get('role', '')
                can_resolve = role in ('Admin', 'Staff', 'Maintenance', 'Security')
                card = MaintenanceCardWidget(req_copy, make_resolve(), make_view(),
                                             can_resolve=can_resolve)
                self.maint_cards_layout.addWidget(card)
        except Exception as e:
            print(f"[Maintenance cards] {e}")

    def _refresh_renter_faces(self):
        while self.renter_faces_row.count() > 1:
            item = self.renter_faces_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        try:
            renters = self.renter_db.get_all_renters()
            active = [r for r in renters if r.get('renter_status') == 'Active']
            for r in active[:30]:
                name = f"{r.get('first_name','')} {r.get('last_name','')}".strip()
                profile_path = r.get('profile_path') or r.get('profile_pic_path')
                av = AvatarWidget(name, 48, profile_path)
                av.setCursor(Qt.PointingHandCursor)
                av.setToolTip(name)
                renter_copy = dict(r)
                av.mousePressEvent = lambda ev, rd=renter_copy: self._show_renter_detail(rd)
                short_name = name.split()[0] if name else "?"
                nm_lbl = QLabel(short_name)
                nm_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 9px;")
                nm_lbl.setAlignment(Qt.AlignCenter)
                wrapper = QWidget()
                wrapper.setStyleSheet("background: transparent;")
                wl = QVBoxLayout(wrapper)
                wl.setContentsMargins(0, 0, 0, 0)
                wl.setSpacing(2)
                wl.addWidget(av, alignment=Qt.AlignCenter)
                wl.addWidget(nm_lbl, alignment=Qt.AlignCenter)
                self.renter_faces_row.insertWidget(self.renter_faces_row.count() - 1, wrapper)
        except Exception:
            pass


    def _refresh_renters_by_room(self):
        """Build a grouped list of renters per room for the admin dashboard."""
        from itertools import groupby
        from operator import itemgetter

        is_admin = (self.current_user or {}).get('role') in (
            'Admin', 'Staff', 'Maintenance', 'Security')
        for attr in ('renters_by_room_label', 'renters_by_room_widget'):
            if hasattr(self, attr):
                getattr(self, attr).setVisible(is_admin)
        if not is_admin:
            return

        layout = self.renters_by_room_layout
        while layout.count():
            item = layout.takeAt(0)
            if w := item.widget():
                w.deleteLater()

        try:
            conn = self.renter_db.connect()
            if not conn:
                return
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT
                    rm.room_id,
                    rm.room_number,
                    rm.floor_level,
                    rm.capacity,
                    rm.status,
                    COUNT(DISTINCT a.assignment_id) AS occupied,
                    CONCAT(r.first_name,' ',r.last_name) AS full_name,
                    a.bed_assignment,
                    r.contact_number,
                    r.renter_status,
                    r.profile_pic_path
                FROM rooms rm
                LEFT JOIN assignments a
                    ON a.room_id = rm.room_id AND a.status = 'Active'
                LEFT JOIN renters r
                    ON r.renter_id = a.renter_id AND r.renter_status = 'Active'
                GROUP BY
                    rm.room_id, a.assignment_id, r.renter_id
                ORDER BY
                    rm.floor_level, rm.room_number, a.bed_assignment
            """)
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            print(f"[_refresh_renters_by_room] DB error: {e}")
            return

        t = Theme.get()
        status_colors = {
            'Available':         t['green'],
            'Full':              t['red'],
            'Under Maintenance': t['orange'],
        }

        for room_id, room_rows in groupby(rows, key=itemgetter('room_id')):
            room_rows = list(room_rows)
            first = room_rows[0]
            cap = int(first.get('capacity') or 0)
            occ = int(first.get('occupied') or 0)
            avail = cap - occ
            s_color = status_colors.get(first.get('status', ''), t['text_muted'])

            room_card = QFrame()
            room_card.setStyleSheet(
                f"background:{t['surface']};border-radius:12px;"
                f"border:1px solid {t['border']};"
                f"border-left:4px solid {s_color};"
            )
            rc = QVBoxLayout(room_card)
            rc.setContentsMargins(16, 12, 16, 12)
            rc.setSpacing(8)

            title_row = QHBoxLayout()
            lbl = QLabel(f"Room {first['room_number']}  ·  {first.get('floor_level','')}")
            lbl.setStyleSheet(
                f"color:{t['text']};font-size:14px;font-weight:bold;"
                f"background:transparent;border:none;"
            )
            badge = QLabel(f"{occ}/{cap} occupied  ·  {avail} free")
            badge.setStyleSheet(
                f"color:{s_color};font-size:12px;font-weight:bold;"
                f"background:transparent;border:none;"
            )
            title_row.addWidget(lbl)
            title_row.addStretch()
            title_row.addWidget(badge)
            rc.addLayout(title_row)

            renters = [r for r in room_rows if r.get('full_name')]
            if not renters:
                empty = QLabel("No active renters assigned.")
                empty.setStyleSheet(
                    f"color:{t['text_muted']};font-size:12px;"
                    f"background:transparent;border:none;padding-left:4px;"
                )
                rc.addWidget(empty)
            else:
                rr = QHBoxLayout()
                rr.setSpacing(12)
                for renter in renters:
                    name = renter.get('full_name', '?')
                    bed  = renter.get('bed_assignment') or '–'
                    pic  = renter.get('profile_pic_path') or ''

                    rw = QWidget()
                    rw.setStyleSheet(
                        f"background:{t['surface2']};border-radius:10px;"
                        f"border:1px solid {t['border']};"
                    )
                    rw.setFixedWidth(80)
                    rv = QVBoxLayout(rw)
                    rv.setContentsMargins(10, 8, 10, 8)
                    rv.setSpacing(4)
                    rv.setAlignment(Qt.AlignCenter)

                    av = AvatarWidget(name, 40, pic if os.path.exists(pic) else None)
                    rv.addWidget(av, alignment=Qt.AlignCenter)

                    for text, size, color in [
                        (name.split()[0], 11, t['text']),
                        (bed,            10, t['text_muted']),
                    ]:
                        l = QLabel(text)
                        l.setStyleSheet(
                            f"color:{color};font-size:{size}px;"
                            f"background:transparent;border:none;"
                        )
                        l.setAlignment(Qt.AlignCenter)
                        rv.addWidget(l)

                    rr.addWidget(rw)
                rr.addStretch()
                rc.addLayout(rr)

            layout.addWidget(room_card)

    def _show_renter_detail(self, renter_data):
        dlg = PersonDetailDialog(self, renter_data, "renter")
        dlg.exec()

    def _show_staff_detail(self, staff_data):
        dlg = PersonDetailDialog(self, staff_data, "staff")
        dlg.exec()

    # ══════════════════════════════════════════
    #  RENTERS PAGE
    # ══════════════════════════════════════════
    def _build_renters_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        # Header - Register Renter button is admin-only (added below so we
        # can toggle visibility). Renters never see this page anyway.
        hdr_w = QWidget()
        hdr_h = QHBoxLayout(hdr_w)
        hdr_h.setContentsMargins(0, 0, 0, 0)
        hdr_lbl = QLabel("Renter Management")
        hdr_lbl.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
        self.renter_register_btn = make_btn("  Register Renter", T("green"), "white",
                                            icon="fa5s.user-plus", icon_color="white")
        self.renter_register_btn.clicked.connect(self.open_add_renter_dialog)
        hdr_h.addWidget(hdr_lbl)
        hdr_h.addStretch()
        hdr_h.addWidget(self.renter_register_btn)
        layout.addWidget(hdr_w)
        layout.addSpacing(10)

        # Pending applications banner
        self.pending_banner = QFrame()
        self.pending_banner.setStyleSheet(f"background: {T('accent_dim')}; border-radius: 10px; border: 1px solid {T('accent')};")
        pb_layout = QHBoxLayout(self.pending_banner)
        pb_layout.setContentsMargins(16, 10, 16, 10)
        self.pending_label = QLabel("There are pending rental applications awaiting approval.")
        self.pending_label.setStyleSheet(f"color: {T('accent')}; font-size: 13px; font-weight: bold;")
        approve_btn = make_btn("Review & Approve", T("accent"), "black", height=34)
        approve_btn.clicked.connect(self._show_pending_applications)
        pb_layout.addWidget(self.pending_label)
        pb_layout.addStretch()
        pb_layout.addWidget(approve_btn)
        self.pending_banner.setVisible(False)
        layout.addWidget(self.pending_banner)

        search_row = QHBoxLayout()
        self.renter_search = QLineEdit()
        self.renter_search.setPlaceholderText("⌕  Search by name, contact, or email...")
        self.renter_search.setStyleSheet(input_style() + "min-height:38px;")
        self.renter_search.textChanged.connect(self.search_renters)
        search_row.addWidget(self.renter_search)

        # Filter by status
        self.renter_filter = QComboBox()
        self.renter_filter.addItems(["All", "Active", "Inactive", "Pending", "Blacklisted"])
        self.renter_filter.setStyleSheet(input_style() + "min-width: 120px;")
        self.renter_filter.currentTextChanged.connect(self._filter_renters)
        search_row.addWidget(self.renter_filter)
        layout.addLayout(search_row)
        layout.addSpacing(10)

        self.renters_table = self._make_table(
            ["ID", "Avatar", "Full Name", "Gender", "Occupation", "Contact", "Email", "Status"]
        )
        self.renters_table.setColumnWidth(1, 56)
        self.renters_table.setRowHeight(0, 52)
        self.renters_table.clicked.connect(self._on_renter_row_clicked)
        layout.addWidget(self.renters_table)

        btn_row = QHBoxLayout()
        view_btn   = make_btn("  View",    T("blue"),   "white", icon="fa5s.eye",       icon_color="white")
        self.renter_edit_btn = make_btn("  Edit",    T("blue"),   "white", icon="fa5s.edit",      icon_color="white")
        self.renter_delete_btn = make_btn("  Delete",  T("red"),    "white", icon="fa5s.trash-alt", icon_color="white")
        self.renter_pic_btn    = make_btn("  Set Pic", T("orange"), "white", icon="fa5s.camera",    icon_color="white")
        view_btn.clicked.connect(self._view_renter)
        self.renter_edit_btn.clicked.connect(self.open_edit_renter_dialog)
        self.renter_delete_btn.clicked.connect(self.delete_renter)
        self.renter_pic_btn.clicked.connect(self._renter_set_pic)
        btn_row.addStretch()
        btn_row.addWidget(view_btn)
        btn_row.addWidget(self.renter_edit_btn)
        btn_row.addWidget(self.renter_delete_btn)
        btn_row.addWidget(self.renter_pic_btn)
        layout.addLayout(btn_row)
        return page

    def _show_pending_applications(self):
        """Called from the renters page banner - navigate to Applications page."""
        self.switch_page(1)
        for btn in self.sidebar_buttons:
            if btn.property("page_index") == 1:
                btn.setChecked(True)
                break

    # ══════════════════════════════════════════
    #  APPLICATIONS PAGE  (NEW)
    # ══════════════════════════════════════════
    def _build_applications_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        hdr = QHBoxLayout()
        title = QLabel("Rental Applications")
        title.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
        hdr.addWidget(title)
        hdr.addStretch()
        layout.addLayout(hdr)

        sub = QLabel(
            "These are applications submitted through the public 'Apply to Rent' form.\n"
            "Approve an applicant to automatically create their renter record and login credentials."
        )
        sub.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        # Mini stat cards
        stat_row = QHBoxLayout()
        stat_row.setSpacing(12)
        self.app_stat_pending  = StatCard("Pending",  "0", T("accent"), "fa5s.clock")
        self.app_stat_approved = StatCard("Approved", "0", T("green"),  "fa5s.check-circle")
        self.app_stat_rejected = StatCard("Rejected", "0", T("red"),    "fa5s.times-circle")
        self.app_stat_total    = StatCard("Total",    "0", T("blue"),   "fa5s.file-alt")
        for c in [self.app_stat_pending, self.app_stat_approved, self.app_stat_rejected, self.app_stat_total]:
            c.setFixedHeight(100)
            stat_row.addWidget(c)
        layout.addLayout(stat_row)

        # Filter row
        filter_row = QHBoxLayout()
        self.app_search = QLineEdit()
        self.app_search.setPlaceholderText("⌕  Search by name, email, or contact...")
        self.app_search.setStyleSheet(input_style() + "min-height: 36px;")
        self.app_search.textChanged.connect(self._filter_applications)
        self.app_status_filter = QComboBox()
        self.app_status_filter.addItems(["All", "Pending", "Approved", "Rejected"])
        self.app_status_filter.setStyleSheet(input_style() + "min-width: 130px;")
        self.app_status_filter.currentTextChanged.connect(self._filter_applications)
        filter_row.addWidget(self.app_search)
        filter_row.addWidget(self.app_status_filter)
        layout.addLayout(filter_row)

        self.applications_table = self._make_table([
            "ID", "Full Name", "Gender", "Occupation", "Contact", "Email",
            "Preferred Room", "Submitted", "Status"
        ])
        layout.addWidget(self.applications_table)

        btn_row = QHBoxLayout()
        view_btn = make_btn("  View Details", T("blue"),  "white", icon="fa5s.eye",         icon_color="white")
        self.app_approve_btn = make_btn("  Approve",     T("green"), "white", icon="fa5s.user-check",  icon_color="white")
        self.app_reject_btn  = make_btn("  Reject",      T("red"),   "white", icon="fa5s.user-times",  icon_color="white")
        delete_btn = make_btn("  Delete",                T("surface2"), T("text_muted"), icon="fa5s.trash-alt", icon_color=T("text_muted"))
        view_btn.clicked.connect(self._view_application)
        self.app_approve_btn.clicked.connect(self._approve_application)
        self.app_reject_btn.clicked.connect(self._reject_application)
        delete_btn.clicked.connect(self._delete_application)
        btn_row.addStretch()
        btn_row.addWidget(view_btn)
        btn_row.addWidget(self.app_approve_btn)
        btn_row.addWidget(self.app_reject_btn)
        btn_row.addWidget(delete_btn)
        layout.addLayout(btn_row)
        return page

    def load_applications(self):
        apps = self.app_db.get_all_applications()
        self._display_applications(apps)
        pending  = sum(1 for a in apps if a.get('status') == 'Pending')
        approved = sum(1 for a in apps if a.get('status') == 'Approved')
        rejected = sum(1 for a in apps if a.get('status') == 'Rejected')
        if hasattr(self, 'app_stat_pending'):
            self.app_stat_pending.set_value(pending)
            self.app_stat_approved.set_value(approved)
            self.app_stat_rejected.set_value(rejected)
            self.app_stat_total.set_value(len(apps))
        self._refresh_app_badge()

    def _display_applications(self, apps):
        self.applications_table.setRowCount(0)
        t = Theme.get()
        sc = {'Pending': t['accent'], 'Approved': t['green'], 'Rejected': t['red']}
        for i, a in enumerate(apps):
            name = f"{a.get('first_name','')} {a.get('last_name','')}".strip()
            submitted = str(a.get('submitted_at', '-'))[:16]
            self._set_table_row(self.applications_table, i, [
                a['application_id'], name,
                a.get('gender', '-'), a.get('occupation_type', '-'),
                a.get('contact_number', '-'), a.get('email', '-'),
                a.get('preferred_room', '-') or '-',
                submitted, a.get('status', '-')
            ])
            status_color = sc.get(a.get('status', ''), t['text'])
            self.applications_table.item(i, 8).setForeground(QColor(status_color))

    def _filter_applications(self):
        apps = self.app_db.get_all_applications()
        kw = self.app_search.text().strip().lower() if hasattr(self, 'app_search') else ""
        sf = self.app_status_filter.currentText() if hasattr(self, 'app_status_filter') else "All"
        if kw:
            apps = [a for a in apps if
                    kw in f"{a.get('first_name','')} {a.get('last_name','')}".lower() or
                    kw in str(a.get('email', '')).lower() or
                    kw in str(a.get('contact_number', '')).lower()]
        if sf != "All":
            apps = [a for a in apps if a.get('status') == sf]
        self._display_applications(apps)

    def _get_selected_application(self):
        row = self.applications_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an application first.")
            return None
        app_id = int(self.applications_table.item(row, 0).text())
        apps = self.app_db.get_all_applications()
        return next((a for a in apps if a['application_id'] == app_id), None)

    def _view_application(self):
        app = self._get_selected_application()
        if not app:
            return
        t = Theme.get()
        dlg = QDialog(self)
        dlg.setWindowTitle("Application Details")
        dlg.setFixedWidth(500)
        dlg.setStyleSheet(dialog_style())
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(10)

        name = f"{app.get('first_name','')} {app.get('last_name','')}".strip()
        av = AvatarWidget(name, 72)
        layout.addWidget(av, alignment=Qt.AlignCenter)

        title = QLabel(name)
        title.setStyleSheet(f"color: {T('text')}; font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        status = app.get('status', '-')
        sc = {'Pending': T('accent'), 'Approved': T('green'), 'Rejected': T('red')}
        st_lbl = QLabel(f"{status}")
        st_lbl.setStyleSheet(f"color: {sc.get(status, T('text'))}; font-size: 13px; font-weight: bold;")
        st_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(st_lbl)

        line = QFrame(); line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background: {T('border')}; max-height: 1px;")
        layout.addWidget(line)

        fields = [
            ("Gender",          app.get('gender')),
            ("Occupation",      app.get('occupation_type')),
            ("Institution",     app.get('institution')),
            ("Contact",         app.get('contact_number')),
            ("Email",           app.get('email')),
            ("Address",         app.get('address')),
            ("Emergency Name",  app.get('emergency_name')),
            ("Emergency No.",   app.get('emergency_number')),
            ("Preferred Room",  app.get('preferred_room')),
            ("Message",         app.get('message')),
            ("Submitted",       str(app.get('submitted_at', '-'))[:16]),
        ]
        for lbl, val in fields:
            if not val:
                continue
            row_w = QHBoxLayout()
            l = QLabel(f"{lbl}:")
            l.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px; font-weight: bold; min-width: 110px;")
            v = QLabel(str(val))
            v.setStyleSheet(f"color: {T('text')}; font-size: 13px;")
            v.setWordWrap(True)
            row_w.addWidget(l)
            row_w.addWidget(v, stretch=1)
            layout.addLayout(row_w)

        close_btn = make_btn("Close", T("surface2"), T("text"))
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        dlg.exec()

    def _approve_application(self):
        app = self._get_selected_application()
        if not app:
            return
        if app.get('status') != 'Pending':
            QMessageBox.information(self, "Already Processed",
                                    f"This application is already '{app.get('status')}'.")
            return
        name = f"{app.get('first_name','')} {app.get('last_name','')}".strip()
        reply = QMessageBox.question(
            self, "Approve Application",
            f"Approve '{name}'?\n\n"
            f"This will create their renter record and generate login credentials.\n"
            f"Default password will be: dorm123\n\n"
            f"You can share the credentials with the applicant.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        admin_id = self.current_user.get('admin_id') if self.current_user else None
        ok, username, pw = self.app_db.approve_application(app['application_id'], admin_id)
        if ok:
            to_email = app.get('email', '')
            email_note = (
                f"\n\nCredentials email is being sent to:\n  {to_email}"
                if to_email else
                "\n\nNo email on file - share credentials manually."
            )
            QMessageBox.information(
                self, "Application Approved!",
                f"'{name}' has been approved and registered as a renter.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  Username:  {username}\n"
                f"  Password:  {pw}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
                f"{email_note}"
            )
            self.load_applications()
            self._refresh_app_badge()
            # Refresh dashboard and renters so stats reflect new assignment
            try:
                self.refresh_home_stats()
            except Exception:
                pass
            try:
                self.load_renters()
            except Exception:
                pass
        else:
            QMessageBox.critical(self, "Error", f"Approval failed: {username}")

    def _reject_application(self):
        app = self._get_selected_application()
        if not app:
            return
        if app.get('status') != 'Pending':
            QMessageBox.information(self, "Already Processed",
                                    f"This application is already '{app.get('status')}'.")
            return
        name = f"{app.get('first_name','')} {app.get('last_name','')}".strip()
        reason_dlg = QDialog(self)
        reason_dlg.setWindowTitle("Reject Application")
        reason_dlg.setFixedWidth(400)
        reason_dlg.setStyleSheet(dialog_style())
        rl = QVBoxLayout(reason_dlg)
        rl.setContentsMargins(24, 24, 24, 24)
        rl.setSpacing(12)
        rl.addWidget(QLabel(f"Rejecting application from: {name}"))
        reason_input = QTextEdit()
        reason_input.setPlaceholderText("Reason for rejection (optional)...")
        reason_input.setFixedHeight(80)
        reason_input.setStyleSheet(input_style())
        rl.addWidget(reason_input)
        btn_row = QHBoxLayout()
        cancel = make_btn("Cancel", T("surface2"), T("text"))
        confirm = make_btn("  Reject", T("red"), "white", icon="fa5s.times", icon_color="white")
        cancel.clicked.connect(reason_dlg.reject)
        confirm.clicked.connect(reason_dlg.accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(confirm)
        rl.addLayout(btn_row)
        if reason_dlg.exec():
            reason = reason_input.toPlainText().strip()
            admin_id = self.current_user.get('admin_id') if self.current_user else None
            ok = self.app_db.reject_application(app['application_id'], admin_id, reason)
            if ok:
                QMessageBox.information(self, "Rejected", f"Application from '{name}' has been rejected.")
                self.load_applications()
                self._refresh_app_badge()
            else:
                QMessageBox.critical(self, "Error", "Failed to reject application.")

    def _delete_application(self):
        app = self._get_selected_application()
        if not app:
            return
        name = f"{app.get('first_name','')} {app.get('last_name','')}".strip()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Permanently delete application from '{name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            ok = self.app_db.delete_application(app['application_id'])
            if ok:
                self.load_applications()
                self._refresh_app_badge()

    def load_renters(self, rows=None):
        # Check for pending applications via ApplicationModule
        try:
            pending_count = self.app_db.get_pending_count()
            if pending_count > 0:
                self.pending_label.setText(
                    f"{pending_count} rental application(s) pending review in Applications page."
                )
                self.pending_banner.setVisible(True)
            else:
                self.pending_banner.setVisible(False)
        except Exception:
            self.pending_banner.setVisible(False)

        if rows is None:
            rows = self.renter_db.get_all_renters()
        self.renters_table.setRowCount(0)
        t = Theme.get()
        status_colors = {"Active": t['green'], "Inactive": t['text_muted'],
                         "Pending": t['accent'], "Blacklisted": t['red']}
        for i, r in enumerate(rows):
            self.renters_table.insertRow(i)
            self.renters_table.setRowHeight(i, 52)
            mn = r.get('middle_name') or ''
            name = f"{r['first_name']} {mn} {r['last_name']}".strip().replace('  ', ' ')
            profile_path = r.get('profile_path') or r.get('profile_pic_path')
            av = AvatarWidget(name, 40, profile_path)
            self.renters_table.setCellWidget(i, 1, av)
            vals = [r['renter_id'], None, name, r['gender'], r['occupation_type'],
                    r['contact_number'], r['email'], r['renter_status']]
            for col, val in enumerate(vals):
                if col == 1:
                    continue
                item = QTableWidgetItem(str(val) if val is not None else "-")
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if col == 7:
                    item.setForeground(QColor(status_colors.get(str(val), t['text'])))
                self.renters_table.setItem(i, col, item)

    def _on_renter_row_clicked(self, index):
        pass

    def search_renters(self):
        kw = self.renter_search.text().strip()
        if kw:
            rows = self.renter_db.search_renters(kw)
        else:
            rows = self.renter_db.get_all_renters()
        status_filter = self.renter_filter.currentText() if hasattr(self, 'renter_filter') else "All"
        if status_filter != "All":
            rows = [r for r in rows if r.get('renter_status') == status_filter]
        self.load_renters(rows)

    def _filter_renters(self):
        self.search_renters()

    def _view_renter(self):
        row = self.renters_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a renter.")
            return
        renter_id = int(self.renters_table.item(row, 0).text())
        renter = self.renter_db.get_renter_by_id(renter_id)
        if renter:
            self._show_renter_detail(renter)

    def _renter_set_pic(self):
        row = self.renters_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a renter.")
            return
        renter_id = int(self.renters_table.item(row, 0).text())
        renter = self.renter_db.get_renter_by_id(renter_id)
        if not renter:
            return
        name = f"{renter.get('first_name','')} {renter.get('last_name','')}".strip()
        dlg = RenterSelfProfileDialog(self, name, renter_id, "renter")
        if dlg.exec() and dlg.chosen_path:
            try:
                conn = self.renter_db.connect()
                if not conn:
                    QMessageBox.critical(self, "Error", "Could not connect to database.")
                    return
                cur = conn.cursor()
                cur.execute("UPDATE renters SET profile_pic_path=%s WHERE renter_id=%s", (dlg.chosen_path, renter_id))
                conn.commit()
                conn.close()
            except Exception:
                pass
            QMessageBox.information(self, "Updated", f"{name}'s profile picture has been set!")
            self.load_renters()

    def open_add_renter_dialog(self):
        dlg = RenterDialog(self)
        if dlg.exec():
            data      = dlg.get_data()
            status    = data.pop('renter_status', 'Active')
            room_obj  = data.pop('room_obj',    None)
            bed_val   = data.pop('bed_val',     None)
            check_in  = data.pop('check_in',    None)
            agreed_rate = data.pop('agreed_rate', 1800.0)

            admin_id = self.current_user.get('admin_id') if self.current_user else None

            renter_id = self.renter_db.add_renter(**data, admin_id=admin_id)
            if renter_id:
                # Set status if not Active
                if status != 'Active':
                    try:
                        conn = self.renter_db.connect()
                        if conn:
                            cur = conn.cursor()
                            cur.execute("UPDATE renters SET renter_status=%s WHERE renter_id=%s", (status, renter_id))
                            conn.commit()
                            conn.close()
                    except Exception as e:
                        print(f"[open_add_renter_dialog] Failed to set renter_status to '{status}': {e}")
                        QMessageBox.warning(self, "Warning",
                                            f"Renter was created but status could not be set to '{status}'.\n{e}")

                # ── Room Assignment (if admin picked a room) ──
                assign_msg = ""
                if room_obj and bed_val and check_in:
                    room_id = room_obj.get('room_id')
                    ok, msg = self.assignment_db.assign_renter_to_room(
                        renter_id=renter_id,
                        room_id=room_id,
                        bed=bed_val,
                        check_in=check_in,
                        rate=agreed_rate,
                        admin_id=admin_id or 0,
                    )
                    if ok:
                        assign_msg = f"\n🛏 Assigned to Room {room_obj.get('room_number')} — {bed_val}"
                    else:
                        assign_msg = f"\n⚠️ Room assignment failed: {msg}"

                QMessageBox.information(self, "Success", f"Renter registered!{assign_msg}")
                self.load_renters()
            else:
                QMessageBox.critical(self, "Error", "Failed to register renter.")

    def open_edit_renter_dialog(self):
        row = self.renters_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a renter.")
            return
        renter_id = int(self.renters_table.item(row, 0).text())
        renter = self.renter_db.get_renter_by_id(renter_id)
        if not renter:
            return
        dlg = RenterDialog(self, renter)
        if dlg.exec():
            data = dlg.get_data()
            status = data.pop('renter_status', 'Active')
            data['renter_status'] = status
            ok = self.renter_db.update_renter(renter_id, **data)
            if ok:
                if self.current_user and self.current_user.get('admin_id'):
                    self.admin_db.add_log(self.current_user['admin_id'], 'EDIT_RENTER',
                                          f"Edited renter ID {renter_id}")
                QMessageBox.information(self, "Success", "Renter updated!")
                self.load_renters()
            else:
                QMessageBox.critical(self, "Error", "Update failed.")

    def delete_renter(self):
        row = self.renters_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a renter.")
            return
        renter_id = int(self.renters_table.item(row, 0).text())
        name = self.renters_table.item(row, 2).text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Delete renter '{name}'?\nThis cannot be undone.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            ok = self.renter_db.delete_renter(
                renter_id,
                admin_id=self.current_user.get('admin_id') if self.current_user else None
            )
            if ok:
                # Logging is handled inside sp_delete_renter — no duplicate call needed
                self.load_renters()
            else:
                QMessageBox.critical(self, "Error", "Delete failed.")

    # ══════════════════════════════════════════
    #  STAFF PAGE
    # ══════════════════════════════════════════
    def _build_staff_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        self.staff_page_header = page_header("Staff Management")
        layout.addWidget(self.staff_page_header)
        layout.addSpacing(10)
        self.staff_table = self._make_table(["ID", "Avatar", "Full Name", "Username", "Role", "Joined"])
        self.staff_table.setColumnWidth(1, 56)
        layout.addWidget(self.staff_table)
        btn_row = QHBoxLayout()
        view_btn = make_btn("  View", T("blue"), "white", icon="fa5s.eye", icon_color="white")
        self.staff_edit_btn   = make_btn("  Edit",   T("blue"),  "white", icon="fa5s.edit",      icon_color="white")
        self.staff_delete_btn = make_btn("  Delete", T("red"),   "white", icon="fa5s.trash-alt", icon_color="white")
        self.staff_add_btn    = make_btn("  Add Staff", T("green"), "white", icon="fa5s.user-plus", icon_color="white")
        view_btn.clicked.connect(self._view_staff)
        self.staff_edit_btn.clicked.connect(self.open_edit_staff_dialog)
        self.staff_delete_btn.clicked.connect(self.delete_staff)
        self.staff_add_btn.clicked.connect(self.open_add_staff_dialog)
        btn_row.addStretch()
        btn_row.addWidget(view_btn)
        btn_row.addWidget(self.staff_edit_btn)
        btn_row.addWidget(self.staff_delete_btn)
        btn_row.addWidget(self.staff_add_btn)
        layout.addLayout(btn_row)
        return page

    def load_staff(self):
        try:
            admins = self.admin_db.get_all_admins()
        except Exception:
            admins = []
        self.staff_table.setRowCount(0)
        for i, a in enumerate(admins):
            self.staff_table.insertRow(i)
            self.staff_table.setRowHeight(i, 52)
            name = a.get('full_name', '-')
            av = AvatarWidget(name, 40)
            self.staff_table.setCellWidget(i, 1, av)
            joined = str(a.get('created_at', '-'))[:10] if a.get('created_at') else '-'
            vals = [a.get('admin_id', i), None, name, a.get('username', '-'), a.get('role', '-'), joined]
            for col, val in enumerate(vals):
                if col == 1:
                    continue
                item = QTableWidgetItem(str(val) if val is not None else "-")
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.staff_table.setItem(i, col, item)

    def _view_staff(self):
        row = self.staff_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a staff member.")
            return
        try:
            staff_id = int(self.staff_table.item(row, 0).text())
            admins = self.admin_db.get_all_admins()
            staff = next((a for a in admins if a.get('admin_id') == staff_id), None)
            if staff:
                self._show_staff_detail(staff)
        except Exception:
            pass

    def open_add_staff_dialog(self):
        dlg = StaffDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            try:
                pw       = data.pop('password', 'changeme123')
                email    = data.get('email') or ''
                ok = self.admin_db.add_admin(
                    username  = data['username'],
                    password  = pw,
                    full_name = data['full_name'],
                    role      = data.get('role', 'Staff'),
                    email     = email,
                )
                if ok:
                    # Update email/contact columns (add_admin doesn't set contact yet)
                    contact = data.get('contact_number') or ''
                    if contact or email:
                        prof = database.ProfileModule()
                        # Fetch the new admin_id
                        conn = self.admin_db.connect()
                        if conn:
                            try:
                                cur = conn.cursor()
                                cur.execute(
                                    "SELECT admin_id FROM admins WHERE username=%s",
                                    (data['username'],),
                                )
                                row_r = cur.fetchone()
                                if row_r:
                                    prof.update_admin_profile(
                                        row_r[0],
                                        email=email or None,
                                        contact_number=contact or None,
                                    )
                            except Exception:
                                pass
                            finally:
                                conn.close()

                    if self.current_user and self.current_user.get('admin_id'):
                        self.admin_db.add_log(
                            self.current_user['admin_id'], 'ADD_STAFF',
                            f"Added staff: {data['full_name']} - "
                            f"invitation email {'sent' if email else 'skipped (no email)'}.",
                        )
                    msg = "Staff member added successfully!"
                    if email:
                        msg += f"\n\nAn invitation email with login credentials\nhas been sent to: {email}"
                    else:
                        msg += f"\n\nNo email provided - credentials:\nUsername: {data['username']}\nPassword: {pw}"
                    QMessageBox.information(self, "Staff Added", msg)
                    self.load_staff()
                else:
                    QMessageBox.critical(self, "Error",
                                         "Failed to add staff. Username may already exist.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed: {e}")

    def open_edit_staff_dialog(self):
        row = self.staff_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a staff member.")
            return
        try:
            staff_id = int(self.staff_table.item(row, 0).text())
            admins = self.admin_db.get_all_admins()
            staff = next((a for a in admins if a.get('admin_id') == staff_id), None)
            if not staff:
                return
            dlg = StaffDialog(self, staff)
            if dlg.exec():
                data = dlg.get_data()
                try:
                    conn = self.admin_db.connect()
                    if not conn:
                        QMessageBox.critical(self, "Error", "Could not connect to database.")
                        return
                    try:
                        cur = conn.cursor()
                        if 'password' in data:
                            hashed = hashlib.sha256(data.pop('password').encode()).hexdigest()
                            cur.execute("UPDATE admins SET password=%s WHERE admin_id=%s", (hashed, staff_id))
                        cur.execute("UPDATE admins SET full_name=%s, username=%s, role=%s WHERE admin_id=%s",
                                    (data['full_name'], data['username'], data.get('role', 'Staff'), staff_id))
                        conn.commit()
                    finally:
                        conn.close()
                    QMessageBox.information(self, "Success", "Staff updated!")
                    if self.current_user and self.current_user.get('admin_id'):
                        self.admin_db.add_log(
                            self.current_user['admin_id'], 'EDIT_STAFF',
                            f"Updated staff: {data.get('full_name', '')} (ID {staff_id})",
                            staff_id=staff_id
                        )
                    self.load_staff()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Update failed: {e}")
        except Exception:
            pass

    def delete_staff(self):
        row = self.staff_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a staff member.")
            return
        staff_id = int(self.staff_table.item(row, 0).text())
        name = self.staff_table.item(row, 2).text()
        if self.current_user and self.current_user.get('admin_id') == staff_id:
            QMessageBox.warning(self, "Cannot Delete", "You cannot delete your own account.")
            return
        reply = QMessageBox.question(self, "Confirm", f"Delete staff '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                ok = self.admin_db.delete_admin(staff_id)
                if ok:
                    if self.current_user and self.current_user.get('admin_id'):
                        self.admin_db.add_log(
                            self.current_user['admin_id'], 'DELETE_STAFF',
                            f"Deleted staff/admin: {name} (ID {staff_id})",
                            staff_id=staff_id
                        )
                    self.load_staff()
                else:
                    QMessageBox.critical(self, "Error", "Delete failed.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete failed: {e}")

    # ══════════════════════════════════════════
    #  ALL ROOMS PAGE
    # ══════════════════════════════════════════
    def _build_rooms_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)

        header_row = QHBoxLayout()
        title = QLabel("Room Management")
        title.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
        self.room_add_btn = make_btn("  Add Room", T("green"), "white", icon="fa5s.plus", icon_color="white")
        self.room_add_btn.clicked.connect(self.open_add_room_dialog)
        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(self.room_add_btn)
        layout.addLayout(header_row)
        layout.addSpacing(10)

        # Mini stats row
        mini_stats = QHBoxLayout()
        mini_stats.setSpacing(12)
        self.rm_stat_total = StatCard("Total Rooms", "-", T("blue"), "fa5s.building")
        self.rm_stat_avail = StatCard("Available", "-", T("green"), "fa5s.door-open")
        self.rm_stat_full  = StatCard("Full", "-", T("red"), "fa5s.door-closed")
        self.rm_stat_maint = StatCard("Under Maint.", "-", T("orange"), "fa5s.tools")
        for c in [self.rm_stat_total, self.rm_stat_avail, self.rm_stat_full, self.rm_stat_maint]:
            c.setFixedHeight(100)
            mini_stats.addWidget(c)
        layout.addLayout(mini_stats)
        layout.addSpacing(10)

        self.rooms_table = self._make_table(
            ["ID", "Room No.", "Floor", "Rate (₱)", "Capacity", "Occupied", "Available", "Status", "Notes"]
        )
        self.rooms_table.doubleClicked.connect(self.open_edit_room_dialog)
        layout.addWidget(self.rooms_table)

        btn_row = QHBoxLayout()
        edit_btn = make_btn("  Edit", T("blue"), "white", icon="fa5s.edit", icon_color="white")
        self.room_delete_btn = make_btn("  Delete", T("red"), "white", icon="fa5s.trash-alt", icon_color="white")
        self.room_photo_btn  = make_btn("  Set Photo", T("purple"), "white", icon="fa5s.camera", icon_color="white")
        self.room_maint_btn = make_btn("  Set Under Maintenance", T("orange"), "white",
                                       icon="fa5s.tools", icon_color="white")
        self.room_clear_maint_btn = make_btn("  Clear Maintenance", T("green"), "white",
                                             icon="fa5s.check", icon_color="white")
        edit_btn.clicked.connect(self.open_edit_room_dialog)
        self.room_delete_btn.clicked.connect(self.delete_room)
        self.room_photo_btn.clicked.connect(self.set_room_photo)
        self.room_maint_btn.clicked.connect(self.set_room_under_maintenance)
        self.room_clear_maint_btn.clicked.connect(self.clear_room_maintenance)
        btn_row.addStretch()
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(self.room_photo_btn)
        btn_row.addWidget(self.room_maint_btn)
        btn_row.addWidget(self.room_clear_maint_btn)
        btn_row.addWidget(self.room_delete_btn)
        layout.addLayout(btn_row)
        return page

    def load_rooms(self):
        rooms = self.room_db.get_all_rooms_with_beds()
        self.rooms_table.setRowCount(0)
        t = Theme.get()
        status_colors = {'Available': t['green'], 'Full': t['red'],
                         'Under Maintenance': t['orange'], 'Reserved': t['blue']}

        def _full(r):
            cap = int(r.get('capacity') or 0); occ = int(r.get('occupied') or 0)
            return cap > 0 and occ >= cap and r.get('status') != 'Under Maintenance'
        total = len(rooms)
        maint = sum(1 for r in rooms if r.get('status') == 'Under Maintenance')
        full  = sum(1 for r in rooms if _full(r))
        avail = sum(1 for r in rooms if r.get('status') != 'Under Maintenance' and not _full(r))

        if hasattr(self, 'rm_stat_total'):
            self.rm_stat_total.set_value(total)
            self.rm_stat_avail.set_value(avail)
            self.rm_stat_full.set_value(full)
            self.rm_stat_maint.set_value(maint)

        for i, r in enumerate(rooms):
            cap = r.get('capacity', 0) or 0
            occ = r.get('occupied', 0) or 0
            avail_slots = cap - occ
            self._set_table_row(self.rooms_table, i, [
                r['room_id'], r['room_number'], r['floor_level'],
                f"₱{r['monthly_rate']:,.2f}", cap, occ, avail_slots,
                r['status'], r.get('description', '') or '-'
            ])
            status = r.get('status', '')
            color = status_colors.get(status, t['text'])
            self.rooms_table.item(i, 7).setForeground(QColor(color))

    def open_add_room_dialog(self):
        dlg = RoomDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            ok = self.room_db.add_room(
                **data,
                admin_id=self.current_user.get('admin_id') if self.current_user else None
            )
            if ok:
                # Logging is handled inside sp_add_room — no duplicate call needed
                QMessageBox.information(self, "Success", "Room added!")
                self.load_rooms()
            else:
                QMessageBox.critical(self, "Error", "Failed to add room.")

    def open_edit_room_dialog(self):
        row = self.rooms_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a room.")
            return
        room_id = int(self.rooms_table.item(row, 0).text())
        room = self.room_db.get_room_by_id(room_id)
        if not room:
            return
        dlg = RoomDialog(self, room)
        if dlg.exec():
            data = dlg.get_data()
            ok = self.room_db.update_room(room_id, **data)
            if ok:
                if self.current_user and self.current_user.get('admin_id'):
                    self.admin_db.add_log(self.current_user['admin_id'], 'EDIT_ROOM', f"Edited room ID {room_id}")
                QMessageBox.information(self, "Success", "Room updated!")
                self.load_rooms()
            else:
                QMessageBox.critical(self, "Error", "Update failed.")

    def delete_room(self):
        row = self.rooms_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a room.")
            return
        room_id = int(self.rooms_table.item(row, 0).text())
        reply = QMessageBox.question(self, "Confirm", f"Delete room ID {room_id}?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            ok = self.room_db.delete_room(
                room_id,
                admin_id=self.current_user.get('admin_id') if self.current_user else None
            )
            if ok:
                # Logging is handled inside sp_delete_room — no duplicate call needed
                self.load_rooms()
            else:
                QMessageBox.critical(self, "Error", "Delete failed.")

    def set_room_photo(self):
        """Let admin pick an image file and save it as the room's photo."""
        row = self.rooms_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a room first.")
            return
        room_id = int(self.rooms_table.item(row, 0).text())
        room_no = self.rooms_table.item(row, 1).text()

        # Start from user's Downloads folder so they can find downloaded pics easily
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        start_dir = downloads if os.path.exists(downloads) else os.path.expanduser("~")

        path, _ = QFileDialog.getOpenFileName(
            self, f"Select Photo for Room {room_no}",
            start_dir, "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not path:
            return

        # Save a copy into images/rooms/ beside main.py so it's portable
        import shutil
        dest_dir = os.path.join(os.path.dirname(__file__), "images", "rooms")
        os.makedirs(dest_dir, exist_ok=True)
        ext = os.path.splitext(path)[1]
        dest = os.path.join(dest_dir, f"room_{room_id}{ext}")
        shutil.copy2(path, dest)

        relative_path = os.path.join("images", "rooms", f"room_{room_id}{ext}")
        ok = self.room_db.update_room(room_id, photo_path=relative_path)
        if ok:
            if self.current_user and self.current_user.get('admin_id'):
                self.admin_db.add_log(
                    self.current_user['admin_id'], 'SET_ROOM_PHOTO',
                    f"Updated photo for Room {room_no}"
                )
            QMessageBox.information(self, "Photo Set",
                                    f"Photo for Room {room_no} has been updated!")
            self.load_rooms()
        else:
            QMessageBox.critical(self, "Error", "Failed to save photo path.")

    # ── Admin-only: toggle Under Maintenance with a reason ──────────────
    def _require_admin(self) -> bool:
        role = (self.current_user or {}).get('role', '')
        if role != 'Admin':
            QMessageBox.warning(self, "Permission Denied",
                                "Only Admin can change a room's maintenance status.")
            return False
        return True

    def set_room_under_maintenance(self):
        if not self._require_admin():
            return
        row = self.rooms_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a room.")
            return
        room_id = int(self.rooms_table.item(row, 0).text())
        room = self.room_db.get_room_by_id(room_id)
        if not room:
            return
        reason, ok = QInputDialog.getMultiLineText(
            self, "Under Maintenance",
            f"Reason for marking Room {room.get('room_number','?')} as Under Maintenance:",
            ""
        )
        if not ok:
            return
        reason = (reason or "").strip()
        if not reason:
            QMessageBox.warning(self, "Reason Required",
                                "A reason is required when setting a room Under Maintenance.")
            return
        existing_notes = room.get('description', '') or ''
        new_notes = (existing_notes + ("\n" if existing_notes else "")
                     + f"[Under Maintenance - {QDate.currentDate().toString('yyyy-MM-dd')}] {reason}")
        try:
            ok2 = self.room_db.update_room(
                room_id,
                room_number=room.get('room_number'),
                floor_level=room.get('floor_level'),
                monthly_rate=float(room.get('monthly_rate') or 0),
                capacity=int(room.get('capacity') or 0),
                status='Under Maintenance',
                description=new_notes,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        if ok2:
            if self.current_user and self.current_user.get('admin_id'):
                self.admin_db.add_log(self.current_user['admin_id'], 'ROOM_UNDER_MAINTENANCE',
                                      f"Room {room.get('room_number')} set Under Maintenance: {reason}")
            QMessageBox.information(self, "Success",
                                    f"Room {room.get('room_number')} is now Under Maintenance.")
            self.load_rooms()
        else:
            QMessageBox.critical(self, "Error", "Failed to update room status.")

    def clear_room_maintenance(self):
        if not self._require_admin():
            return
        row = self.rooms_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a room.")
            return
        room_id = int(self.rooms_table.item(row, 0).text())
        room = self.room_db.get_room_by_id(room_id)
        if not room or room.get('status') != 'Under Maintenance':
            QMessageBox.information(self, "Not Applicable",
                                    "This room is not currently Under Maintenance.")
            return
        cap = int(room.get('capacity') or 0)
        occ = int(room.get('occupied') or 0)
        new_status = 'Full' if (cap > 0 and occ >= cap) else 'Available'
        try:
            ok2 = self.room_db.update_room(
                room_id,
                room_number=room.get('room_number'),
                floor_level=room.get('floor_level'),
                monthly_rate=float(room.get('monthly_rate') or 0),
                capacity=cap,
                status=new_status,
                description=room.get('description', '') or '',
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        if ok2:
            if self.current_user and self.current_user.get('admin_id'):
                self.admin_db.add_log(self.current_user['admin_id'], 'ROOM_CLEAR_MAINTENANCE',
                                      f"Room {room.get('room_number')} maintenance cleared → {new_status}")
            self.load_rooms()

    # ══════════════════════════════════════════
    #  VACANT ROOMS PAGE
    # ══════════════════════════════════════════
    def _build_vacant_rooms_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Vacant Rooms")
        title.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
        self.vacant_count_lbl = QLabel("0 rooms available")
        self.vacant_count_lbl.setStyleSheet(f"color: {T('green')}; font-size: 14px; font-weight: bold; background: {T('surface2')}; padding: 6px 14px; border-radius: 16px;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.vacant_count_lbl)
        layout.addLayout(header)

        sub = QLabel("Rooms with available beds. Click any room card for full details including current assignments.")
        sub.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px;")
        layout.addWidget(sub)

        # ── Interactive Room-Detail List ─────────────────────────────────
        detail_hdr = QLabel("Room & Assignment Details")
        detail_hdr.setStyleSheet(f"color: {T('text')}; font-size: 15px; font-weight: bold;")
        layout.addWidget(detail_hdr)

        self.vacant_detail_table = self._make_table([
            "Room No.", "Floor", "Capacity", "Occupied", "Available Beds",
            "Current Tenants", "Bed Assignments", "Rate (₱)", "Status"
        ])
        self.vacant_detail_table.setMinimumHeight(220)
        layout.addWidget(self.vacant_detail_table)

        # ── Card Grid ───────────────────────────────────────────────────
        cards_hdr = QLabel("Room Cards")
        cards_hdr.setStyleSheet(f"color: {T('text')}; font-size: 15px; font-weight: bold;")
        layout.addWidget(cards_hdr)

        self.vacant_grid_widget = QWidget()
        self.vacant_grid_widget.setStyleSheet("background: transparent;")
        self.vacant_grid_layout = QGridLayout(self.vacant_grid_widget)
        self.vacant_grid_layout.setSpacing(16)
        self.vacant_grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.vacant_grid_widget)
        layout.addStretch()

        scroll.setWidget(page)
        return scroll

    def load_vacant_rooms(self):
        rooms = self.room_db.get_all_rooms_with_beds()
        vacant = [r for r in rooms if (int(r.get('capacity') or 0) - int(r.get('occupied') or 0)) > 0 and r.get('status') != 'Under Maintenance']

        total_beds = sum(max(0, int(r.get('capacity',0) or 0) - int(r.get('occupied',0) or 0)) for r in vacant)
        self.vacant_count_lbl.setText(f"{len(vacant)} rooms · {total_beds} beds available")

        # ── Populate Interactive Detail Table ───────────────────────────
        if hasattr(self, 'vacant_detail_table'):
            self.vacant_detail_table.setRowCount(0)
            t = Theme.get()
            for i, room in enumerate(vacant):
                cap = int(room.get('capacity', 0) or 0)
                occ = int(room.get('occupied', 0) or 0)
                avail = cap - occ

                # Fetch current tenant names and bed assignments from DB
                tenant_names = "-"
                bed_assignments = "-"
                try:
                    conn = self.renter_db.connect()
                    if conn:
                        cur = conn.cursor(dictionary=True)
                        cur.execute("""
                            SELECT full_name AS name, bed_assignment
                            FROM vw_renter_profile_full
                            WHERE room_id=%s
                        """, (room['room_id'],))
                        rows_db = cur.fetchall()
                        conn.close()
                        if rows_db:
                            tenant_names = ", ".join(r['name'] for r in rows_db)
                            beds_raw = [r.get('bed_assignment') or '-' for r in rows_db]
                            bed_assignments = ", ".join(beds_raw)
                except Exception:
                    pass

                self._set_table_row(self.vacant_detail_table, i, [
                    room.get('room_number', '-'),
                    room.get('floor_level', '-'),
                    cap,
                    occ,
                    avail,
                    tenant_names,
                    bed_assignments,
                    f"₱{float(room.get('monthly_rate', 0)):,.2f}",
                    room.get('status', 'Available'),
                ])
                # Colour available beds column green
                self.vacant_detail_table.item(i, 4).setForeground(QColor(t['green']))

        # ── Card Grid ──────────────────────────────────────────────────
        while self.vacant_grid_layout.count():
            item = self.vacant_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not vacant:
            empty = QLabel("No vacant rooms at this time.")
            empty.setStyleSheet(f"color: {T('text_muted')}; font-size: 15px; padding: 30px;")
            self.vacant_grid_layout.addWidget(empty, 0, 0)
            return

        for i, room in enumerate(vacant):
            card = RoomCardWidget(room, on_click=lambda r=room: self._show_room_detail(r))
            self.vacant_grid_layout.addWidget(card, i // 4, i % 4)


    # ══════════════════════════════════════════
    #  OCCUPIED ROOMS PAGE
    # ══════════════════════════════════════════
    def _build_occupied_rooms_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Occupied Rooms")
        title.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
        self.occupied_count_lbl = QLabel("0 rooms occupied")
        self.occupied_count_lbl.setStyleSheet(f"color: {T('red')}; font-size: 14px; font-weight: bold; background: {T('surface2')}; padding: 6px 14px; border-radius: 16px;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.occupied_count_lbl)
        layout.addLayout(header)

        sub = QLabel("Rooms currently with at least one renter assigned. Double-click a row to view renters & set check-out date.")
        sub.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px;")
        layout.addWidget(sub)

        # Occupancy table
        self.occupied_table = self._make_table([
            "Room No.", "Floor", "Rate (₱)", "Capacity", "Occupied", "Renters"
        ])
        self.occupied_table.cellDoubleClicked.connect(self._open_room_renters_dialog)
        layout.addWidget(self.occupied_table)
        layout.addStretch()

        scroll.setWidget(page)
        return scroll

    def load_occupied_rooms(self):
        rooms = self.room_db.get_all_rooms_with_beds()
        occupied = [r for r in rooms if int(r.get('occupied') or 0) > 0 and r.get('status') != 'Under Maintenance']
        self.occupied_count_lbl.setText(f"{len(occupied)} rooms occupied")

        self.occupied_table.setRowCount(0)
        for i, r in enumerate(occupied):
            renter_names = "-"
            try:
                conn = self.renter_db.connect()
                if conn:
                    cur = conn.cursor(dictionary=True)
                    cur.execute("""
                        SELECT full_name AS name
                        FROM vw_renter_profile_full
                        WHERE room_id=%s
                    """, (r['room_id'],))
                    names = [row['name'] for row in cur.fetchall()]
                    conn.close()
                    if names:
                        renter_names = ", ".join(names)
            except Exception:
                pass

            cap = r.get('capacity', 0) or 0
            occ = r.get('occupied', 0) or 0
            self._set_table_row(self.occupied_table, i, [
                r['room_number'], r['floor_level'],
                f"₱{r['monthly_rate']:,.2f}", cap, occ, renter_names
            ])

    def _open_room_renters_dialog(self, row, col):
        t = Theme.get()
        room_no_item = self.occupied_table.item(row, 0)
        if not room_no_item:
            return
        room_no = room_no_item.text()

        # Get room_id from DB
        room_id = None
        try:
            conn = self.renter_db.connect()
            if conn:
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT room_id FROM rooms WHERE room_number=%s", (room_no,))
                res = cur.fetchone()
                conn.close()
                if res:
                    room_id = res['room_id']
        except Exception:
            pass

        if not room_id:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Room {room_no} — Renters")
        dlg.setMinimumWidth(650)
        dlg.setStyleSheet(dialog_style())
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        hdr = QLabel(f"Renters in Room {room_no}")
        hdr.setStyleSheet(f"color: {t['text']}; font-size: 18px; font-weight: bold;")
        lay.addWidget(hdr)

        hint = QLabel("Select a renter then click 'Set Check-out Date' to assign their move-out date.")
        hint.setStyleSheet(f"color: {t['text_muted']}; font-size: 12px;")
        lay.addWidget(hint)

        tbl = self._make_table(["Renter ID", "Name", "Bed", "Check-in", "Check-out", "Status"])
        tbl.setMinimumHeight(200)
        lay.addWidget(tbl)

        def load_renters():
            tbl.setRowCount(0)
            try:
                conn = self.renter_db.connect()
                if conn:
                    cur = conn.cursor(dictionary=True)
                    cur.execute("""
                        SELECT a.assignment_id, a.renter_id,
                               CONCAT(r.first_name,' ',r.last_name) AS name,
                               a.bed_assignment, a.check_in_date,
                               a.check_out_date, a.status
                        FROM assignments a
                        JOIN renters r ON a.renter_id = r.renter_id
                        WHERE a.room_id = %s AND a.status = 'Active'
                        ORDER BY r.first_name
                    """, (room_id,))
                    rows = cur.fetchall()
                    conn.close()
                    for i, rec in enumerate(rows):
                        self._set_table_row(tbl, i, [
                            rec['renter_id'],
                            rec['name'],
                            rec['bed_assignment'] or '-',
                            str(rec['check_in_date']) if rec['check_in_date'] else '-',
                            str(rec['check_out_date']) if rec['check_out_date'] else 'Not set',
                            rec['status']
                        ])
            except Exception as e:
                print(f"[load_renters dialog] {e}")

        load_renters()

        # Buttons row
        btn_row = QHBoxLayout()
        btn_checkout = make_btn("  Set Check-out Date", T("orange"), "white",
                                icon="fa5s.calendar-times", icon_color="white")
        btn_clear = make_btn("  Clear Check-out Date", T("red"), "white",
                             icon="fa5s.times-circle", icon_color="white")
        btn_close = make_btn("Close", T("surface2"), T("text"))

        def set_checkout():
            selected = tbl.currentRow()
            if selected < 0:
                QMessageBox.warning(dlg, "No Selection", "Select a renter from the list first.")
                return
            renter_id_item = tbl.item(selected, 0)
            renter_name_item = tbl.item(selected, 1)
            if not renter_id_item:
                return
            renter_id = int(renter_id_item.text())
            renter_name = renter_name_item.text() if renter_name_item else ""

            date_dlg = QDialog(dlg)
            date_dlg.setWindowTitle(f"Set Check-out — {renter_name}")
            date_dlg.setStyleSheet(dialog_style())
            date_lay = QVBoxLayout(date_dlg)
            date_lay.setContentsMargins(20, 20, 20, 20)
            date_lay.setSpacing(10)

            lbl = QLabel(f"Select check-out date for {renter_name}:")
            lbl.setStyleSheet(f"color: {t['text']}; font-size: 13px;")
            date_lay.addWidget(lbl)

            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDate(QDate.currentDate())
            date_edit.setStyleSheet(input_style())
            date_lay.addWidget(date_edit)

            note = QLabel("Note: The system will automatically mark this assignment as 'Expired' on the check-out date.")
            note.setStyleSheet(f"color: {t['text_muted']}; font-size: 11px;")
            note.setWordWrap(True)
            date_lay.addWidget(note)

            btn_r = QHBoxLayout()
            btn_confirm = make_btn("Confirm", T("green"), "white")
            btn_cancel = make_btn("Cancel", T("red"), "white")
            btn_r.addWidget(btn_confirm)
            btn_r.addWidget(btn_cancel)
            date_lay.addLayout(btn_r)

            btn_cancel.clicked.connect(date_dlg.reject)

            def confirm_checkout():
                chosen_date = date_edit.date().toString("yyyy-MM-dd")
                try:
                    conn = self.renter_db.connect()
                    if conn:
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE assignments
                            SET check_out_date = %s
                            WHERE renter_id = %s AND room_id = %s AND status = 'Active'
                        """, (chosen_date, renter_id, room_id))
                        conn.commit()
                        conn.close()
                    QMessageBox.information(date_dlg, "Saved",
                        f"Check-out date set to {chosen_date} for {renter_name}.")
                    date_dlg.accept()
                    load_renters()
                except Exception as e:
                    QMessageBox.critical(date_dlg, "Error", str(e))

            btn_confirm.clicked.connect(confirm_checkout)
            date_dlg.exec()

        def clear_checkout():
            selected = tbl.currentRow()
            if selected < 0:
                QMessageBox.warning(dlg, "No Selection", "Select a renter from the list first.")
                return
            renter_id_item = tbl.item(selected, 0)
            renter_name_item = tbl.item(selected, 1)
            if not renter_id_item:
                return
            renter_id = int(renter_id_item.text())
            renter_name = renter_name_item.text() if renter_name_item else ""
            reply = QMessageBox.question(dlg, "Confirm Clear",
                f"Remove check-out date for {renter_name}?",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    conn = self.renter_db.connect()
                    if conn:
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE assignments SET check_out_date = NULL
                            WHERE renter_id = %s AND room_id = %s AND status = 'Active'
                        """, (renter_id, room_id))
                        conn.commit()
                        conn.close()
                    load_renters()
                except Exception as e:
                    QMessageBox.critical(dlg, "Error", str(e))

        btn_checkout.clicked.connect(set_checkout)
        btn_clear.clicked.connect(clear_checkout)
        btn_close.clicked.connect(dlg.accept)

        btn_row.addWidget(btn_checkout)
        btn_row.addWidget(btn_clear)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        lay.addLayout(btn_row)

        dlg.exec()

    # ══════════════════════════════════════════
    #  BILLS & PAYMENTS PAGE
    # ══════════════════════════════════════════
    def _build_payments_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        _pay_hdr = page_header("Bills & Payments", "  Add Payment", self.open_add_payment_dialog, btn_icon="fa5s.plus")
        # Keep a ref to the header's Add Payment button so we can hide it for renters
        _hdr_btns = _pay_hdr.findChildren(QPushButton)
        self.pay_header_add_btn = _hdr_btns[0] if _hdr_btns else None
        layout.addWidget(_pay_hdr)


        # Summary cards
        pay_stats_row = QHBoxLayout()
        pay_stats_row.setSpacing(12)
        self.pay_stat_total  = StatCard("Total Collected", "₱0", T("green"),  "fa5s.check-circle")
        self.pay_stat_pend   = StatCard("Pending",         "0",  T("accent"), "fa5s.clock")
        self.pay_stat_over   = StatCard("Overdue",         "0",  T("red"),    "fa5s.exclamation-triangle")
        self.pay_stat_partial= StatCard("Partial",         "0",  T("orange"), "fa5s.adjust")
        for c in [self.pay_stat_total, self.pay_stat_pend, self.pay_stat_over, self.pay_stat_partial]:
            c.setFixedHeight(100)
            pay_stats_row.addWidget(c)
        layout.addLayout(pay_stats_row)

        # Filter row
        filter_row = QHBoxLayout()
        self.pay_search = QLineEdit()
        self.pay_search.setPlaceholderText("⌕  Search by invoice, renter, or billing month...")
        self.pay_search.setStyleSheet(input_style() + "min-height: 38px;")
        self.pay_search.textChanged.connect(self._filter_payments)
        self.pay_status_filter = QComboBox()
        self.pay_status_filter.addItems(["All", "Paid", "Pending", "Overdue", "Partial", "Advanced"])
        self.pay_status_filter.setStyleSheet(input_style() + "min-width: 120px;")
        self.pay_status_filter.currentTextChanged.connect(self._filter_payments)
        filter_row.addWidget(self.pay_search)
        filter_row.addWidget(self.pay_status_filter)
        layout.addLayout(filter_row)

        self.payments_table = self._make_table(
            ["ID", "Invoice", "Renter", "Amount (₱)", "Balance (₱)", "Method", "Billing Month", "Date", "Status"]
        )
        layout.addWidget(self.payments_table)

        btn_row = QHBoxLayout()
        self.pay_mark_paid_btn = make_btn("  Mark Paid", T("green"), "white", icon="fa5s.check-circle", icon_color="white")
        self.pay_add_btn = make_btn("  Add Payment", T("green"), "white", icon="fa5s.plus", icon_color="white")
        self.pay_edit_btn = make_btn("  Edit", T("blue"), "white", icon="fa5s.edit", icon_color="white")
        self.pay_refund_btn = make_btn("  Refund", T("orange"), "white", icon="fa5s.undo", icon_color="white")
        self.pay_adjust_btn = make_btn("  Adjust", T("purple"), "white", icon="fa5s.balance-scale", icon_color="white")
        self.payment_delete_btn = make_btn("  Delete", T("red"), "white", icon="fa5s.trash-alt", icon_color="white")
        # Renter-only: submit a payment reference for admin verification
        self.renter_submit_btn = make_btn("  Submit Payment Proof", T("accent"), "black",
                                          icon="fa5s.upload", icon_color="black")
        self.renter_submit_btn.setVisible(False)  # shown only for Renter role
        self.pay_mark_paid_btn.clicked.connect(self.mark_payment_paid)
        self.pay_add_btn.clicked.connect(self.open_add_payment_dialog)
        self.pay_edit_btn.clicked.connect(self.edit_selected_payment)
        self.pay_refund_btn.clicked.connect(self.refund_selected_payment)
        self.pay_adjust_btn.clicked.connect(self.adjust_selected_payment)
        self.payment_delete_btn.clicked.connect(self.delete_payment)
        self.renter_submit_btn.clicked.connect(self._renter_submit_payment)
        btn_row.addStretch()
        btn_row.addWidget(self.renter_submit_btn)
        btn_row.addWidget(self.pay_mark_paid_btn)
        btn_row.addWidget(self.pay_add_btn)
        btn_row.addWidget(self.pay_edit_btn)
        btn_row.addWidget(self.pay_refund_btn)
        btn_row.addWidget(self.pay_adjust_btn)
        btn_row.addWidget(self.payment_delete_btn)
        layout.addLayout(btn_row)
        return page

    # ── Admin payment edit / refund / adjust ─────────────────
    def _selected_payment_id(self):
        row = self.payments_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a payment.")
            return None
        try:
            return int(self.payments_table.item(row, 0).text())
        except Exception:
            return None

    def edit_selected_payment(self):
        if not self._require_admin():
            return
        pid = self._selected_payment_id()
        if pid is None:
            return
        before = self.payment_db.get_payment_by_id(pid)
        if not before:
            return
        # Reuse the PaymentDialog seeded with existing values; pretend renter
        # is the only entry to keep renter_id stable.
        dlg = PaymentDialog(self, [{"renter_id": before["renter_id"],
                                    "first_name": before["renter_name"].split(" ")[0],
                                    "last_name": " ".join(before["renter_name"].split(" ")[1:]) or ""}])
        dlg.invoice.setText(str(before.get("invoice_number") or ""))
        dlg.amount.setText(str(before.get("amount") or ""))
        dlg.balance.setText(str(before.get("balance_amount") or 0))
        if before.get("payment_method"):
            i = dlg.method.findText(before["payment_method"])
            if i >= 0: dlg.method.setCurrentIndex(i)
        dlg.reference.setText(str(before.get("reference_number") or ""))
        dlg.billing_month.setText(str(before.get("billing_month") or ""))
        try:
            d = QDate.fromString(str(before.get("payment_date"))[:10], "yyyy-MM-dd")
            if d.isValid(): dlg.pay_date.setDate(d)
        except Exception:
            pass
        if before.get("status"):
            i = dlg.status.findText(before["status"])
            if i >= 0: dlg.status.setCurrentIndex(i)
        dlg.remarks.setText(str(before.get("remarks") or ""))
        dlg.setWindowTitle(f"Edit Payment #{pid}")
        if dlg.exec():
            data = dlg.get_data()
            data.pop("processed_by", None)
            data.pop("renter_id", None)
            ok = self.payment_db.edit_payment(pid, self.current_user["admin_id"], **data)
            if ok:
                QMessageBox.information(self, "Saved", "Payment updated and audit log written.")
                self.load_payments()
            else:
                QMessageBox.critical(self, "Error", "Update failed.")

    def refund_selected_payment(self):
        if not self._require_admin():
            return
        pid = self._selected_payment_id()
        if pid is None:
            return
        before = self.payment_db.get_payment_by_id(pid)
        if not before:
            return
        amt_str, ok = QInputDialog.getText(
            self, "Refund Payment",
            f"Refund amount for {before.get('invoice_number')} "
            f"(paid: ₱{float(before.get('amount') or 0):,.2f}):",
            QLineEdit.Normal, str(before.get("amount") or "0"))
        if not ok or not amt_str.strip():
            return
        try:
            refund_amt = float(amt_str)
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Refund must be a number.")
            return
        reason, ok = QInputDialog.getMultiLineText(
            self, "Refund Reason", "Reason for the refund:")
        if not ok:
            return
        if self.payment_db.refund_payment(pid, self.current_user["admin_id"],
                                          refund_amt, reason.strip()):
            QMessageBox.information(self, "Refunded",
                                    "Refund recorded and audit log written.")
            self.load_payments()

    def adjust_selected_payment(self):
        if not self._require_admin():
            return
        pid = self._selected_payment_id()
        if pid is None:
            return
        before = self.payment_db.get_payment_by_id(pid)
        if not before:
            return
        amt_str, ok = QInputDialog.getText(
            self, "Adjust Payment",
            f"New amount for {before.get('invoice_number')} "
            f"(currently ₱{float(before.get('amount') or 0):,.2f}):",
            QLineEdit.Normal, str(before.get("amount") or "0"))
        if not ok or not amt_str.strip():
            return
        try:
            new_amt = float(amt_str)
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Amount must be a number.")
            return
        reason, ok = QInputDialog.getMultiLineText(
            self, "Adjustment Reason", "Reason for adjustment:")
        if not ok:
            return
        if self.payment_db.adjust_payment(pid, self.current_user["admin_id"],
                                          new_amt, reason.strip()):
            QMessageBox.information(self, "Adjusted",
                                    "Adjustment recorded and audit log written.")
            self.load_payments()

    def load_payments(self):
        role = self.current_user.get('role', '') if self.current_user else ''
        admin_btn_attrs = ['pay_add_btn','pay_mark_paid_btn','payment_delete_btn',
                           'pay_edit_btn','pay_refund_btn','pay_adjust_btn']
        if role == 'Renter':
            renter_id = self.current_user.get('renter_id')
            payments = self.renter_db.get_renter_payments(renter_id) if renter_id else []
            for a in admin_btn_attrs:
                if hasattr(self, a):
                    getattr(self, a).setVisible(False)
            if hasattr(self, 'pay_header_add_btn') and self.pay_header_add_btn:
                self.pay_header_add_btn.setVisible(False)
            if hasattr(self, 'renter_submit_btn'):
                self.renter_submit_btn.setVisible(True)
        else:
            payments = self.payment_db.get_all_payments()
            for a in admin_btn_attrs:
                if hasattr(self, a):
                    getattr(self, a).setVisible(True)
            if hasattr(self, 'pay_header_add_btn') and self.pay_header_add_btn:
                self.pay_header_add_btn.setVisible(True)
            if hasattr(self, 'renter_submit_btn'):
                self.renter_submit_btn.setVisible(False)
        self._display_payments(payments)
        self._update_payment_stats(payments)

    def _display_payments(self, payments):
        import calendar as _cal
        from datetime import date as _d
        self.payments_table.setRowCount(0)
        t = Theme.get()
        today = _d.today()

        def _effective_status(p):
            """Re-derive correct status from balance + billing month, overriding DB value."""
            stored  = p.get('status', 'Pending')
            amt     = float(p.get('amount') or 0)
            balance = float(p.get('balance_amount') or 0)
            month_text = str(p.get('billing_month', '') or '').strip()

            # Parse billing month → due date (5th)
            due_date = None
            try:
                parts = month_text.split()
                mo_num = list(_cal.month_name).index(parts[0])
                yr_num = int(parts[1])
                due_date = _d(yr_num, mo_num, 5)
            except Exception:
                pass

            # Rule 1: balance > 0 and amount > 0 → always Partial (or Overdue if past 5th)
            if amt > 0 and balance > 0:
                if due_date and today > due_date:
                    return "Overdue"   # paid something but still owes money past due date
                return "Partial"

            # Rule 2: amount == 0 and past due date → Overdue
            if amt == 0 and due_date and today > due_date:
                return "Overdue"

            # Rule 3: amount == 0 and not past due → Pending
            if amt == 0:
                return "Pending"

            # Rule 4: balance == 0 and amount > 0 → Paid
            if amt > 0 and balance == 0:
                return "Paid"

            return stored

        status_colors = {"Paid": t['green'], "Pending": t['accent'],
                         "Overdue": t['red'], "Partial": t['orange'], "Advanced": t['blue']}

        for i, p in enumerate(payments):
            effective = _effective_status(p)
            balance = float(p.get('balance_amount') or 0)

            self._set_table_row(self.payments_table, i, [
                p.get('payment_id', '-'),
                p.get('invoice_number', '-'),
                p.get('renter_name', '-'),
                f"₱{float(p.get('amount') or 0):,.2f}", f"₱{balance:,.2f}",
                p.get('payment_method', '-'),
                p.get('billing_month', '-'),
                str(p.get('payment_date', '-')), effective
            ])
            color = status_colors.get(effective, t['text'])
            self.payments_table.item(i, 8).setForeground(QColor(color))
            # If effective status differs from stored, highlight balance cell orange as a warning
            if effective != p.get('status') and balance > 0:
                self.payments_table.item(i, 4).setForeground(QColor(t['red']))

    def _update_payment_stats(self, payments):
        import calendar as _cal
        from datetime import date as _d
        today = _d.today()

        def _eff(p):
            amt     = float(p.get('amount') or 0)
            balance = float(p.get('balance_amount') or 0)
            month_text = str(p.get('billing_month', '') or '').strip()
            due_date = None
            try:
                parts = month_text.split()
                mo_num = list(_cal.month_name).index(parts[0])
                yr_num = int(parts[1])
                due_date = _d(yr_num, mo_num, 5)
            except Exception:
                pass
            if amt > 0 and balance > 0:
                return "Overdue" if (due_date and today > due_date) else "Partial"
            if amt == 0 and due_date and today > due_date:
                return "Overdue"
            if amt == 0:
                return "Pending"
            if amt > 0 and balance == 0:
                return "Paid"
            return p.get('status', 'Pending')

        # ── CONSISTENCY FIX: "Collected" = Paid + Partial only,
        #    matching the same formula used in Reports total_revenue.
        #    Overdue payments have NOT been collected — do not count them.
        total_collected = sum(
            float(p.get('amount') or 0) for p in payments
            if _eff(p) in ('Paid', 'Partial')
            and float(p.get('amount') or 0) > 0
        )
        pending    = sum(1 for p in payments if _eff(p) == 'Pending')
        overdue    = sum(1 for p in payments if _eff(p) == 'Overdue')
        partial    = sum(1 for p in payments if _eff(p) == 'Partial')
        if hasattr(self, 'pay_stat_total'):
            self.pay_stat_total.set_value(f"₱{total_collected:,.0f}")
            self.pay_stat_pend.set_value(pending)
            self.pay_stat_over.set_value(overdue)
            self.pay_stat_partial.set_value(partial)

    def _filter_payments(self):
        try:
            import calendar as _cal
            from datetime import date as _d
            today = _d.today()

            role = (self.current_user or {}).get('role', '')
            if role == 'Renter':
                renter_id = (self.current_user or {}).get('renter_id')
                payments = self.renter_db.get_renter_payments(renter_id) if renter_id else []
            else:
                payments = self.payment_db.get_all_payments()
            kw = self.pay_search.text().strip().lower() if hasattr(self, 'pay_search') else ""
            sf = self.pay_status_filter.currentText() if hasattr(self, 'pay_status_filter') else "All"
            if kw:
                payments = [p for p in payments if
                            kw in str(p.get('invoice_number', '')).lower() or
                            kw in str(p.get('renter_name', '')).lower() or
                            kw in str(p.get('billing_month', '')).lower()]
            if sf != "All":
                def _eff(p):
                    amt     = float(p.get('amount') or 0)
                    balance = float(p.get('balance_amount') or 0)
                    month_text = str(p.get('billing_month', '') or '').strip()
                    due_date = None
                    try:
                        parts = month_text.split()
                        mo_num = list(_cal.month_name).index(parts[0])
                        yr_num = int(parts[1])
                        due_date = _d(yr_num, mo_num, 5)
                    except Exception:
                        pass
                    if amt > 0 and balance > 0:
                        return "Overdue" if (due_date and today > due_date) else "Partial"
                    if amt == 0 and due_date and today > due_date:
                        return "Overdue"
                    if amt == 0:
                        return "Pending"
                    if amt > 0 and balance == 0:
                        return "Paid"
                    return p.get('status', 'Pending')
                payments = [p for p in payments if _eff(p) == sf]
            self._display_payments(payments)
            self._update_payment_stats(payments)
        except Exception:
            pass

    def open_add_payment_dialog(self):
        renters = self.renter_db.get_all_renters()
        dlg = PaymentDialog(self, renters)
        if dlg.exec():
            data = dlg.get_data()
            if self.current_user and self.current_user.get('admin_id'):
                data['processed_by'] = self.current_user['admin_id']
            ok = self.payment_db.add_payment(**data)
            if ok:
                QMessageBox.information(self, "Success", "Payment recorded!")
                self.load_payments()
            else:
                QMessageBox.critical(self, "Error", "Failed to add payment.")

    def _renter_submit_payment(self):
        """
        Full payment submission dialog for renters.
        Renter fills in: amount paid, billing month, payment method, reference #.
        Creates a Pending record that reflects immediately on their dashboard
        and on the admin Bills & Pay page for verification.
        Once admin verifies, they mark it Paid via Edit or Mark Paid.
        """
        renter_id = (self.current_user or {}).get('renter_id')
        if not renter_id:
            return

        from datetime import date as _d
        import calendar as _cal

        # ── Get renter's agreed rate for default amount hint ──
        try:
            assignment = self.renter_db.get_renter_assignment(renter_id)
            default_rate = float(assignment.get('agreed_rate') or
                                 assignment.get('monthly_rate') or 1800) if assignment else 1800.0
        except Exception:
            default_rate = 1800.0

        now = _d.today()
        default_billing = f"{_cal.month_name[now.month]} {now.year}"

        # ── Build dialog ──────────────────────────────────────
        t = Theme.get()
        dlg = QDialog(self)
        dlg.setWindowTitle("Submit Payment")
        dlg.setFixedWidth(440)
        dlg.setStyleSheet(dialog_style())
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)

        # Header
        hdr = QLabel("💳  Submit Your Payment")
        hdr.setStyleSheet(f"color: {t['accent']}; font-size: 17px; font-weight: bold;")
        lay.addWidget(hdr)

        sub = QLabel(
            "Fill in the details below. Your payment will show as\n"
            "Pending until the admin verifies and confirms it."
        )
        sub.setStyleSheet(f"color: {t['text_muted']}; font-size: 12px;")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(10)

        def inp(placeholder="", default=""):
            e = QLineEdit()
            e.setPlaceholderText(placeholder)
            e.setText(default)
            e.setStyleSheet(input_style())
            return e

        # Amount
        amt_field = inp("e.g. 1800.00", str(int(default_rate)))
        form.addRow("Amount Paid (₱)*:", amt_field)

        # Billing month
        billing_field = inp("e.g. May 2026", default_billing)
        form.addRow("Billing Month*:", billing_field)

        # Payment method
        method_combo = QComboBox()
        method_combo.addItems(["Cash", "GCash", "Bank Transfer", "Other"])
        method_combo.setStyleSheet(input_style())
        form.addRow("Payment Method*:", method_combo)

        # Reference number
        ref_field = inp("GCash ref #, bank transaction ID, etc.")
        form.addRow("Reference # / Proof:", ref_field)

        # Notes
        notes_field = inp("Optional notes for the admin")
        form.addRow("Notes:", notes_field)

        lay.addLayout(form)

        # Status hint
        hint = QLabel("⏳ Will appear as Pending until admin verifies.")
        hint.setStyleSheet(f"color: {t['orange']}; font-size: 11px;")
        lay.addWidget(hint)

        # Buttons
        btn_row = QHBoxLayout()
        cancel_btn = make_btn("Cancel", t['surface2'], t['text'])
        submit_btn = make_btn("  Submit Payment", t['accent'], "black",
                              icon="fa5s.paper-plane", icon_color="black")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(submit_btn)
        lay.addLayout(btn_row)

        # ── Validate & submit ─────────────────────────────────
        def do_submit():
            try:
                amt = float(amt_field.text().strip() or 0)
            except ValueError:
                QMessageBox.warning(dlg, "Invalid Amount",
                                    "Please enter a valid amount (numbers only).")
                return
            if amt <= 0:
                QMessageBox.warning(dlg, "Invalid Amount",
                                    "Amount must be greater than 0.")
                return
            billing = billing_field.text().strip()
            if not billing:
                QMessageBox.warning(dlg, "Missing Field", "Please enter the billing month.")
                return

            method   = method_combo.currentText()
            ref      = ref_field.text().strip()
            notes    = notes_field.text().strip()
            invoice  = f"RENTER-{renter_id}-{now.strftime('%Y%m%d%H%M%S')}"
            remarks  = f"Submitted by renter — awaiting admin verification."
            if ref:
                remarks += f" Ref: {ref}"
            if notes:
                remarks += f" | Notes: {notes}"

            # balance = agreed rate minus what they claim to have paid
            balance = max(0.0, default_rate - amt)

            # NOTE: Ginagamit ang renter_submit_payment (hindi add_payment)
            # para laging Pending ang status — hindi auto-correct sa Paid
            # kahit balance=0. Admin lang ang mag-ve-verify at mag-ma-mark Paid.
            ok2 = self.payment_db.renter_submit_payment(
                invoice_number=invoice,
                renter_id=renter_id,
                amount=amt,
                balance_amount=balance,
                payment_method=method,
                billing_month=billing,
                payment_date=now.strftime("%Y-%m-%d"),
                reference_number=ref or None,
                remarks=remarks,
            )
            if ok2:
                QMessageBox.information(
                    dlg, "Submitted!",
                    f"Payment of ₱{amt:,.2f} for {billing} submitted!\n\n"
                    "It will show as Pending on your dashboard.\n"
                    "The admin will verify and mark it Paid once confirmed."
                )
                dlg.accept()
                self.load_payments()
            else:
                QMessageBox.critical(dlg, "Error",
                                     "Could not submit payment.\n"
                                     "Please try again or contact the admin.")

        submit_btn.clicked.connect(do_submit)
        dlg.exec()

    def mark_payment_paid(self):
        row = self.payments_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a payment.")
            return
        payment_id = int(self.payments_table.item(row, 0).text())
        ok = self.payment_db.update_payment_status(payment_id, "Paid")
        if ok:
            self.load_payments()

    def delete_payment(self):
        row = self.payments_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a payment.")
            return
        payment_id = int(self.payments_table.item(row, 0).text())
        reply = QMessageBox.question(self, "Confirm", "Delete this payment record?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            ok = self.payment_db.delete_payment(payment_id)
            if ok:
                self.load_payments()

    # ══════════════════════════════════════════
    #  REPORTS PAGE  (rich payment analytics)
    # ══════════════════════════════════════════
    def _build_reports_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # ── Header ────────────────────────────
        hdr_row = QHBoxLayout()
        title_lbl = QLabel("Reports & Analytics")
        title_lbl.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
        refresh_btn = make_btn("  Refresh", T("surface2"), T("text"), icon="fa5s.sync-alt", icon_color=T("text"), height=36)
        refresh_btn.clicked.connect(self.load_reports)
        hdr_row.addWidget(title_lbl)
        hdr_row.addStretch()
        hdr_row.addWidget(refresh_btn)
        layout.addLayout(hdr_row)

        sub_lbl = QLabel("Payment performance, revenue trends, and collection analytics for your dormitory.")
        sub_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px;")
        layout.addWidget(sub_lbl)

        # ── KPI Cards Row ─────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)
        self.rpt_total_revenue   = StatCard("Total Revenue",      "₱0",  T("green"),  "fa5s.money-bill-wave")
        self.rpt_total_pending   = StatCard("Total Pending",       "₱0",  T("accent"), "fa5s.clock")
        self.rpt_total_overdue   = StatCard("Total Overdue",       "₱0",  T("red"),    "fa5s.exclamation-triangle")
        self.rpt_collection_rate = StatCard("Collection Rate",     "0%",  T("blue"),   "fa5s.percentage")
        self.rpt_txn_count       = StatCard("Total Transactions",  "0",   T("purple"), "fa5s.list-alt")
        self.rpt_avg_payment     = StatCard("Avg. Payment",        "₱0",  T("teal"),   "fa5s.calculator")
        for c in [self.rpt_total_revenue, self.rpt_total_pending, self.rpt_total_overdue,
                  self.rpt_collection_rate, self.rpt_txn_count, self.rpt_avg_payment]:
            c.setFixedHeight(115)
            kpi_row.addWidget(c)
        layout.addLayout(kpi_row)

        # ── Revenue Trend Line Chart ───────────
        sep1 = QLabel("Monthly Revenue Trend")
        sep1.setStyleSheet(f"color: {T('text')}; font-size: 15px; font-weight: bold; margin-top: 6px;")
        layout.addWidget(sep1)

        revenue_card = self._card_frame()
        revenue_card.setMinimumHeight(280)
        rev_layout = QVBoxLayout(revenue_card)
        rev_layout.setContentsMargins(16, 16, 16, 16)

        # Filter row inside chart card
        rev_filter = QHBoxLayout()
        self.rpt_period_filter = QComboBox()
        self.rpt_period_filter.addItems(["Last 6 Months", "Last 12 Months", "All Time"])
        self.rpt_period_filter.setStyleSheet(input_style() + "max-width: 160px;")
        self.rpt_period_filter.currentTextChanged.connect(self.load_reports)
        rev_filter.addStretch()
        rev_filter.addWidget(QLabel("Period:"))
        rev_filter.addWidget(self.rpt_period_filter)
        rev_layout.addLayout(rev_filter)

        self.revenue_line_chart = LineChartWidget("Revenue (₱) - Collected vs Expected")
        self.revenue_line_chart.setMinimumHeight(230)
        rev_layout.addWidget(self.revenue_line_chart)
        layout.addWidget(revenue_card)

        # ── Two charts side by side ───────────
        sep2 = QLabel("Payment Breakdown")
        sep2.setStyleSheet(f"color: {T('text')}; font-size: 15px; font-weight: bold; margin-top: 4px;")
        layout.addWidget(sep2)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        # Monthly bar chart (collected by month)
        bar_card = self._card_frame()
        bar_card.setMinimumHeight(250)
        bc_layout = QVBoxLayout(bar_card)
        bc_layout.setContentsMargins(16, 16, 16, 16)
        self.monthly_bar_chart = BarChartWidget("Monthly Collections (₱)")
        bc_layout.addWidget(self.monthly_bar_chart)
        charts_row.addWidget(bar_card, 3)

        # Payment method donut
        method_card = self._card_frame()
        method_card.setMinimumHeight(250)
        mth_layout = QVBoxLayout(method_card)
        mth_layout.setContentsMargins(16, 16, 16, 16)
        mth_title = QLabel("By Payment Method")
        mth_title.setStyleSheet(f"color: {T('text')}; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        mth_layout.addWidget(mth_title)
        self.method_donut = DonutChartWidget("Method")
        mth_layout.addWidget(self.method_donut)
        charts_row.addWidget(method_card, 2)

        # Status donut
        status_card = self._card_frame()
        status_card.setMinimumHeight(250)
        st_layout = QVBoxLayout(status_card)
        st_layout.setContentsMargins(16, 16, 16, 16)
        st_title = QLabel("By Status")
        st_title.setStyleSheet(f"color: {T('text')}; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        st_layout.addWidget(st_title)
        self.status_donut_rpt = DonutChartWidget("Status")
        st_layout.addWidget(self.status_donut_rpt)
        charts_row.addWidget(status_card, 2)

        layout.addLayout(charts_row)

        # ── Per-Renter Table ──────────────────
        sep3 = QLabel("Per-Renter Payment Summary")
        sep3.setStyleSheet(f"color: {T('text')}; font-size: 15px; font-weight: bold; margin-top: 4px;")
        layout.addWidget(sep3)

        renter_filter_row = QHBoxLayout()
        self.rpt_renter_search = QLineEdit()
        self.rpt_renter_search.setPlaceholderText("⌕  Search renter...")
        self.rpt_renter_search.setStyleSheet(input_style() + "min-height: 36px; max-width: 280px;")
        self.rpt_renter_search.textChanged.connect(self._filter_rpt_renter_table)
        renter_filter_row.addWidget(self.rpt_renter_search)
        renter_filter_row.addStretch()
        layout.addLayout(renter_filter_row)

        self.rpt_renter_table = self._make_table([
            "Renter Name", "Renter Status", "Paid (₱)", "Pending (₱)", "Overdue (₱)", "Partial (₱)", "Txns", "Last Payment", "Collection %"
        ])
        layout.addWidget(self.rpt_renter_table)

        # ── Overdue Alerts ────────────────────
        sep4 = QLabel("Overdue Payment Alerts")
        sep4.setStyleSheet(f"color: {T('red')}; font-size: 15px; font-weight: bold; margin-top: 4px;")
        layout.addWidget(sep4)

        self.rpt_overdue_table = self._make_table([
            "Invoice", "Renter", "Amount (₱)", "Balance (₱)", "Billing Month", "Due Date", "Days Overdue"
        ])
        layout.addWidget(self.rpt_overdue_table)

        # ── Recent Payments ───────────────────
        sep5 = QLabel("Recent Payments")
        sep5.setStyleSheet(f"color: {T('text')}; font-size: 15px; font-weight: bold; margin-top: 4px;")
        layout.addWidget(sep5)

        self.rpt_recent_table = self._make_table([
            "Invoice", "Renter", "Amount (₱)", "Method", "Billing Month", "Date", "Status"
        ])
        self.rpt_recent_table.setMaximumHeight(220)
        layout.addWidget(self.rpt_recent_table)

        # ── Renter Status Donut + Debt List ───
        sep_status = QLabel("Renter Payment Status - Current Month")
        sep_status.setStyleSheet(
            f"color: {T('text')}; font-size: 15px; font-weight: bold; margin-top: 6px;")
        layout.addWidget(sep_status)

        renter_status_sub = QLabel(
            "Automatic classification of all active renters as Paid, Pending, or Overdue "
            "(Overdue = no full payment after the 5th of the billing month). "
            "Debt column shows balance owed for the current month."
        )
        renter_status_sub.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px;")
        renter_status_sub.setWordWrap(True)
        layout.addWidget(renter_status_sub)

        renter_status_row = QHBoxLayout()
        renter_status_row.setSpacing(16)

        # Donut for this-month statuses
        rs_donut_card = self._card_frame()
        rs_donut_card.setMinimumHeight(280)
        rs_donut_card.setMaximumWidth(320)
        rs_dc_layout = QVBoxLayout(rs_donut_card)
        rs_dc_layout.setContentsMargins(16, 16, 16, 16)
        rs_donut_title = QLabel("Status Distribution")
        rs_donut_title.setStyleSheet(
            f"color: {T('text')}; font-size: 13px; font-weight: bold; "
            f"border: none; background: transparent;")
        rs_dc_layout.addWidget(rs_donut_title)
        self.rpt_renter_status_donut = DonutChartWidget("Status")
        rs_dc_layout.addWidget(self.rpt_renter_status_donut)
        renter_status_row.addWidget(rs_donut_card)

        # KPI cards beside donut
        rs_kpi_col = QVBoxLayout()
        rs_kpi_col.setSpacing(10)
        self.rpt_rs_paid    = StatCard("Paid",    "0", T("green"),  "fa5s.check-circle")
        self.rpt_rs_pending = StatCard("Pending", "0", T("accent"), "fa5s.clock")
        self.rpt_rs_overdue = StatCard("Overdue", "0", T("red"),    "fa5s.exclamation-circle")
        self.rpt_rs_partial = StatCard("Partial", "0", T("orange"), "fa5s.adjust")
        for c in [self.rpt_rs_paid, self.rpt_rs_pending,
                  self.rpt_rs_overdue, self.rpt_rs_partial]:
            c.setFixedHeight(80)
            rs_kpi_col.addWidget(c)
        rs_kpi_col.addStretch()
        renter_status_row.addLayout(rs_kpi_col)
        layout.addLayout(renter_status_row)

        # Structured debt table: Room | Bed | Name | Status | Paid | Debt | Total Outstanding
        sep_debt = QLabel("Renter Debt Breakdown - Room by Room")
        sep_debt.setStyleSheet(
            f"color: {T('text')}; font-size: 15px; font-weight: bold; margin-top: 4px;")
        layout.addWidget(sep_debt)

        debt_filter_row = QHBoxLayout()
        self.rpt_debt_search = QLineEdit()
        self.rpt_debt_search.setPlaceholderText("⌕  Search by name or room...")
        self.rpt_debt_search.setStyleSheet(input_style() + "min-height: 36px; max-width: 280px;")
        self.rpt_debt_search.textChanged.connect(self._filter_rpt_debt_table)
        self.rpt_debt_status_filter = QComboBox()
        self.rpt_debt_status_filter.addItems(["All", "Paid", "Pending", "Overdue", "Partial"])
        self.rpt_debt_status_filter.setStyleSheet(input_style() + "min-width: 120px;")
        self.rpt_debt_status_filter.currentTextChanged.connect(self._filter_rpt_debt_table)
        debt_filter_row.addWidget(self.rpt_debt_search)
        debt_filter_row.addWidget(self.rpt_debt_status_filter)
        debt_filter_row.addStretch()
        layout.addLayout(debt_filter_row)

        self.rpt_debt_table = self._make_table([
            "Room", "Bed", "Renter Name", "Billing Month",
            "Status", "Paid (₱)", "This Month Debt (₱)", "Total Outstanding (₱)"
        ])
        self.rpt_debt_table.setMinimumHeight(220)
        layout.addWidget(self.rpt_debt_table)

        # ── Monthly Revenue for ALL Months (Enhanced Reports) ───
        sep_all = QLabel("Monthly Revenue - All Time")
        sep_all.setStyleSheet(f"color: {T('text')}; font-size: 15px; font-weight: bold; margin-top: 6px;")
        layout.addWidget(sep_all)

        all_rev_sub = QLabel(
            "Complete month-by-month revenue history. Use the selector to highlight a specific month. "
            "Expected = active renters × ₱1,800 (updates automatically as renters move in/out)."
        )
        all_rev_sub.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px;")
        all_rev_sub.setWordWrap(True)
        layout.addWidget(all_rev_sub)

        # Month-jump selector row
        all_month_row = QHBoxLayout()
        self.rpt_all_month_filter = QComboBox()
        self.rpt_all_month_filter.addItem("All Months")
        self.rpt_all_month_filter.setStyleSheet(input_style() + "max-width: 200px;")
        self.rpt_all_month_filter.currentTextChanged.connect(self._filter_all_months_table)
        all_month_row.addWidget(QLabel("Jump to month:"))
        all_month_row.addWidget(self.rpt_all_month_filter)
        all_month_row.addStretch()
        export_all_btn = make_btn("  Export Summary", T("surface2"), T("text"),
                                  icon="fa5s.file-export", icon_color=T("text"), height=34)
        export_all_btn.clicked.connect(self._export_all_months_summary)
        all_month_row.addWidget(export_all_btn)
        layout.addLayout(all_month_row)

        # All-months bar chart
        all_rev_card = self._card_frame()
        all_rev_card.setMinimumHeight(260)
        all_rev_layout = QVBoxLayout(all_rev_card)
        all_rev_layout.setContentsMargins(16, 16, 16, 16)
        self.all_months_bar_chart = BarChartWidget("Revenue per Month - All Time (₱ Collected)")
        self.all_months_bar_chart.setMinimumHeight(220)
        all_rev_layout.addWidget(self.all_months_bar_chart)
        layout.addWidget(all_rev_card)

        # All-months detail table
        self.rpt_all_months_table = self._make_table([
            "Month", "Collected (₱)", "Expected (₱)", "Gap (₱)", "Collection %", "Health"
        ])
        self.rpt_all_months_table.setMaximumHeight(300)
        layout.addWidget(self.rpt_all_months_table)

        layout.addStretch()
        scroll.setWidget(page)
        return scroll

    # ══════════════════════════════════════════
    #  PROFITABILITY & ALL-MONTHS HELPERS
    # ══════════════════════════════════════════
    def _build_profitability_section(self, layout):
        """Build the profitability cards + table and attach to layout."""
        t = Theme.get()
        sep6 = QLabel("Profitability Overview")
        sep6.setStyleSheet(f"color: {T('green')}; font-size: 15px; font-weight: bold; margin-top: 4px;")
        layout.addWidget(sep6)

        profit_sub = QLabel(
            "All-in rate: ₱1,800/renter/month × active renters (live count). "
            "Utility costs (electricity & water estimated, WiFi fixed) are subtracted to show net profit."
        )
        profit_sub.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px;")
        profit_sub.setWordWrap(True)
        layout.addWidget(profit_sub)

        profit_kpi_row = QHBoxLayout()
        profit_kpi_row.setSpacing(14)
        self.rpt_gross_revenue  = StatCard("Gross Revenue",    "₱0", T("green"),  "fa5s.hand-holding-usd")
        self.rpt_total_expenses = StatCard("Est. Expenses",    "₱0", T("red"),    "fa5s.file-invoice-dollar")
        self.rpt_net_profit     = StatCard("Net Profit",       "₱0", T("blue"),   "fa5s.chart-line")
        self.rpt_profit_margin  = StatCard("Profit Margin",    "0%", T("purple"), "fa5s.percentage")
        self.rpt_wifi_cost      = StatCard("WiFi (Fixed/mo)",  "₱0", T("teal"),   "fa5s.wifi")
        for c in [self.rpt_gross_revenue, self.rpt_total_expenses,
                  self.rpt_net_profit, self.rpt_profit_margin, self.rpt_wifi_cost]:
            c.setFixedHeight(115)
            profit_kpi_row.addWidget(c)
        layout.addLayout(profit_kpi_row)

        self.rpt_expense_breakdown_lbl = QLabel("Avg monthly breakdown: calculating...")
        self.rpt_expense_breakdown_lbl.setStyleSheet(
            f"color: {T('text_muted')}; font-size: 12px; padding: 4px 0;"
        )
        layout.addWidget(self.rpt_expense_breakdown_lbl)

        self.rpt_profit_table = self._make_table([
            "Month", "Revenue (₱)", "Est. Expenses (₱)", "Net Profit (₱)", "Margin %", "Health"
        ])
        self.rpt_profit_table.setMaximumHeight(280)
        layout.addWidget(self.rpt_profit_table)

    def _filter_all_months_table(self):
        """Filter rpt_all_months_table when user picks a specific month."""
        if not hasattr(self, '_all_months_data'):
            return
        sel = self.rpt_all_month_filter.currentText() if hasattr(self, 'rpt_all_month_filter') else "All Months"
        data = self._all_months_data
        if sel and sel != "All Months":
            data = [d for d in data if self._fmt_month_label(d.get("month", "")) == sel]
        self._populate_all_months_table(data)

    def _populate_all_months_table(self, data):
        t = Theme.get()
        # Fallback expected = live active renters × ₱1,800 (never hardcoded)
        try:
            _fallback_expected = self.utility_db.get_active_renter_count() * 1800.0
        except Exception:
            _fallback_expected = 0.0
        self.rpt_all_months_table.setRowCount(0)
        for i, d in enumerate(data):
            coll = d.get("collected", 0.0)
            exp  = d.get("expected", 0.0) or _fallback_expected
            gap  = coll - exp
            pct  = round(coll / exp * 100, 1) if exp > 0 else 0.0
            health = "Full" if pct >= 100 else ("Good" if pct >= 70 else ("Low" if pct >= 40 else "Poor"))
            self._set_table_row(self.rpt_all_months_table, i, [
                self._fmt_month_label(d.get("month", "-")),
                f"₱{coll:,.2f}",
                f"₱{exp:,.2f}",
                f"₱{gap:,.2f}",
                f"{pct}%",
                health,
            ])
            gap_col = t['green'] if gap >= 0 else t['red']
            pct_col = t['green'] if pct >= 100 else (t['accent'] if pct >= 70 else t['red'])
            self.rpt_all_months_table.item(i, 3).setForeground(QColor(gap_col))
            self.rpt_all_months_table.item(i, 4).setForeground(QColor(pct_col))
            self.rpt_all_months_table.item(i, 5).setForeground(QColor(pct_col))

    def _export_all_months_summary(self):
        """Export all-months revenue to a simple text summary dialog."""
        if not hasattr(self, '_all_months_data') or not self._all_months_data:
            QMessageBox.information(self, "No Data", "No monthly revenue data to export.")
            return
        try:
            _fallback_exp = self.utility_db.get_active_renter_count() * 1800.0
        except Exception:
            _fallback_exp = 0.0
        lines = ["Month              Collected       Expected        Gap             %"]
        lines.append("-" * 72)
        for d in self._all_months_data:
            coll = d.get("collected", 0.0)
            exp  = d.get("expected", 0.0) or _fallback_exp
            gap  = coll - exp
            pct  = round(coll / exp * 100, 1) if exp > 0 else 0.0
            lines.append(
                f"{self._fmt_month_label(d.get('month','-')):<18} ₱{coll:>12,.2f}  ₱{exp:>12,.2f}  ₱{gap:>12,.2f}  {pct}%"
            )
        text = "\n".join(lines)
        dlg = QDialog(self)
        dlg.setWindowTitle("All-Month Revenue Summary")
        dlg.setFixedSize(820, 500)
        dlg.setStyleSheet(dialog_style())
        v = QVBoxLayout(dlg)
        v.setContentsMargins(20, 20, 20, 20)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setFont(QFont("Courier New", 10))
        te.setPlainText(text)
        te.setStyleSheet(f"background:{T('bg')}; color:{T('text')}; border:1px solid {T('border')}; border-radius:8px;")
        v.addWidget(te)
        copy_btn = make_btn("  Copy to Clipboard", T("blue"), "white", icon="fa5s.copy", icon_color="white")
        copy_btn.clicked.connect(lambda: (
            QApplication.clipboard().setText(text),
            QMessageBox.information(dlg, "Copied", "Summary copied to clipboard!")
        ))
        close_btn = make_btn("Close", T("surface2"), T("text"))
        close_btn.clicked.connect(dlg.accept)
        br = QHBoxLayout()
        br.addWidget(copy_btn)
        br.addStretch()
        br.addWidget(close_btn)
        v.addLayout(br)
        dlg.exec()

    def _dummy_profitability(self):
        """Placeholder - profitability cards built inline in _build_reports_page."""
        pass

    def _filter_rpt_debt_table(self):
        """Live-filter the renter debt table."""
        kw = self.rpt_debt_search.text().strip().lower() if hasattr(self, 'rpt_debt_search') else ""
        sf = self.rpt_debt_status_filter.currentText() if hasattr(self, 'rpt_debt_status_filter') else "All"
        for row in range(self.rpt_debt_table.rowCount()):
            name_item   = self.rpt_debt_table.item(row, 2)
            room_item   = self.rpt_debt_table.item(row, 0)
            status_item = self.rpt_debt_table.item(row, 4)
            name_match   = (not kw) or (name_item and kw in name_item.text().lower())
            room_match   = (not kw) or (room_item and kw in room_item.text().lower())
            status_match = (sf == "All") or (status_item and status_item.text() == sf)
            self.rpt_debt_table.setRowHidden(row, not ((name_match or room_match) and status_match))

    def _filter_rpt_renter_table(self):
        """Live-filter the per-renter table by name."""
        kw = self.rpt_renter_search.text().strip().lower() if hasattr(self, 'rpt_renter_search') else ""
        for row in range(self.rpt_renter_table.rowCount()):
            item = self.rpt_renter_table.item(row, 0)
            match = (kw in item.text().lower()) if item else True
            self.rpt_renter_table.setRowHidden(row, not match)

    @staticmethod
    def _fmt_month_label(key: str) -> str:
        """Convert '2026-01', 'January 2026', or bare 'January' → 'Jan 2026'."""
        import calendar as _cal
        import datetime as _dt
        key = str(key).strip()
        parts = key.split()

        # "Month YYYY" format  e.g. "January 2026"
        if len(parts) == 2 and parts[0] in list(_cal.month_name):
            try:
                mo = list(_cal.month_name).index(parts[0])
                return f"{_cal.month_abbr[mo]} {parts[1]}"
            except Exception:
                return key

        # "YYYY-MM" format  e.g. "2026-01"
        if len(key) == 7 and key[4] == '-':
            try:
                yr, mo = int(key[:4]), int(key[5:])
                return f"{_cal.month_abbr[mo]} {yr}"
            except Exception:
                pass

        # Bare month name only  e.g. "January"
        if len(parts) == 1 and parts[0] in list(_cal.month_name):
            try:
                mo = list(_cal.month_name).index(parts[0])
                yr = _dt.date.today().year
                return f"{_cal.month_abbr[mo]} {yr}"
            except Exception:
                return key

        # Abbreviated month only  e.g. "Jan"
        if len(parts) == 1 and parts[0] in list(_cal.month_abbr):
            try:
                mo = list(_cal.month_abbr).index(parts[0])
                yr = _dt.date.today().year
                return f"{_cal.month_abbr[mo]} {yr}"
            except Exception:
                return key

        return key

    def load_reports(self):
        try:
            payments = self.payment_db.get_all_payments()
        except Exception:
            payments = []

        t = Theme.get()

        # ── KPI calculations (use effective status, not just stored) ─────────
        import calendar as _cal_kpi
        from datetime import date as _d_kpi
        _today_kpi = _d_kpi.today()

        def _kpi_eff(p):
            amt     = float(p.get('amount') or 0)
            balance = float(p.get('balance_amount') or 0)
            month_text = str(p.get('billing_month', '') or '').strip()
            due_date = None
            try:
                parts = month_text.split()
                mo_num = list(_cal_kpi.month_name).index(parts[0])
                yr_num = int(parts[1])
                due_date = _d_kpi(yr_num, mo_num, 5)
            except Exception:
                pass
            if amt > 0 and balance == 0:
                return "Paid"
            if amt > 0 and balance > 0:
                return "Overdue" if (due_date and _today_kpi > due_date) else "Partial"
            if amt == 0 and due_date and _today_kpi > due_date:
                return "Overdue"
            return "Pending"

        # Total Revenue = Paid + Partial amounts already collected
        total_revenue   = sum(
            float(p.get('amount') or 0) for p in payments
            if _kpi_eff(p) in ('Paid', 'Partial')
            and float(p.get('amount') or 0) > 0
        )
        total_pending_v = sum(float(p.get('amount') or 0) for p in payments if _kpi_eff(p) == 'Pending')

        # Total Overdue = balance still owed by overdue renters
        # get_all_payments() only has renters WITH a payment record.
        # Renters with NO payment record this month are fetched separately.
        def _overdue_owed(p):
            bal = float(p.get('balance_amount') or 0)
            if bal > 0:
                return bal
            return float(p.get('agreed_rate') or p.get('monthly_rate') or 0)

        overdue_from_payments = sum(
            _overdue_owed(p) for p in payments if _kpi_eff(p) == 'Overdue'
        )
        try:
            unpaid_all = self.payment_db.get_unpaid_overdue_renters()
            no_record_overdue = sum(
                float(r.get('agreed_rate') or r.get('monthly_rate') or 1800)
                for r in unpaid_all
                if r.get('status') == 'No Payment'
            )
        except Exception:
            no_record_overdue = 0

        total_overdue_v = overdue_from_payments + no_record_overdue

        # paid_count = records that have ANY payment (Paid + Partial)
        paid_count  = sum(1 for p in payments if _kpi_eff(p) in ('Paid', 'Partial'))
        total_count = len(payments)

        # Collection Rate = renters who paid (fully or partially) / total renters
        collection_rate = int((paid_count / total_count * 100)) if total_count else 0

        # Avg Payment = total collected / number of payment transactions that have amount > 0
        txn_with_payment = sum(1 for p in payments if float(p.get('amount') or 0) > 0)
        avg_payment = (total_revenue / txn_with_payment) if txn_with_payment else 0

        self.rpt_total_revenue.set_value(f"₱{total_revenue:,.0f}")
        self.rpt_total_pending.set_value(f"₱{total_pending_v:,.0f}")
        self.rpt_total_overdue.set_value(f"₱{total_overdue_v:,.0f}")
        self.rpt_collection_rate.set_value(f"{collection_rate}%")
        self.rpt_txn_count.set_value(total_count)
        self.rpt_avg_payment.set_value(f"₱{avg_payment:,.0f}")

        # ── Determine period for trend charts ─
        period = self.rpt_period_filter.currentText() if hasattr(self, 'rpt_period_filter') else "Last 6 Months"
        n_months = {"Last 6 Months": 6, "Last 12 Months": 12, "All Time": 99}.get(period, 6)

        # Build monthly buckets - normalize 'May 2026' / '2026-05' / etc.
        from database import DatabaseEngine as _DBE

        # ── Compute expected revenue from actual agreed_rate sum (per-renter rates),
        #    not a hardcoded ₱1,800 × active_count which ignores custom rates.
        #    Falls back to count × 1,800 if agreed_rate is not set in assignments.
        try:
            _expected_per_month = self.renter_db.get_total_expected_monthly()
        except Exception:
            try:
                _expected_per_month = self.utility_db.get_active_renter_count() * 1800.0
            except Exception:
                _expected_per_month = 0.0

        monthly_collected = {}
        monthly_expected  = {}
        for p in payments:
            key = _DBE._month_key(p.get('billing_month', ''))
            if not key:
                continue
            amt = float(p.get('amount') or 0)
            # ── BUG FIX 2: Use effective status (includes Partial), not raw DB status
            eff = _kpi_eff(p)
            if eff in ('Paid', 'Partial') and amt > 0:
                monthly_collected[key] = monthly_collected.get(key, 0) + amt
            else:
                monthly_collected.setdefault(key, 0)
            # Expected = fixed amount per month (active renters × rate), not payment amounts
            monthly_expected[key] = _expected_per_month

        # Sort chronologically by YYYY-MM key
        all_months = sorted(set(list(monthly_collected.keys()) + list(monthly_expected.keys())))
        if n_months < 99:
            all_months = all_months[-n_months:]

        # ── Revenue Line Chart (Collected vs Expected) ─
        # Pad to at least 2 months so the line chart always renders
        if len(all_months) == 1:
            yr_p, mo_p = map(int, all_months[0].split("-"))
            prev_key = f"{yr_p-1}-12" if mo_p == 1 else f"{yr_p}-{mo_p-1:02d}"
            all_months = [prev_key] + all_months
            monthly_collected.setdefault(prev_key, 0)
            monthly_expected[prev_key] = _expected_per_month

        if len(all_months) >= 2:
            collected_pts = [(self._fmt_month_label(m), monthly_collected.get(m, 0)) for m in all_months]
            expected_pts  = [(self._fmt_month_label(m), monthly_expected.get(m, 0))  for m in all_months]
            self.revenue_line_chart.set_data([
                ("Collected", collected_pts, t['green']),
                ("Expected",  expected_pts,  t['teal']),
            ])
        else:
            self.revenue_line_chart.set_data([
                ("Collected", [("No data", 0), ("-", 0)], t['border'])
            ])

        # ── Monthly Bar Chart (collected only) ─
        bar_data = []
        bar_colors = [t['green'], t['blue'], t['accent'], t['orange'], t['purple'], t['teal'],
                      t['red'], t['green'], t['blue'], t['accent'], t['orange'], t['purple']]
        for i, m in enumerate(all_months[-8:]):
            bar_data.append((self._fmt_month_label(m), int(monthly_collected.get(m, 0)), bar_colors[i % len(bar_colors)]))
        if bar_data:
            self.monthly_bar_chart.set_data(bar_data)
        else:
            self.monthly_bar_chart.set_data([("No data", 0, t['border'])])

        # ── Payment Method Donut ─────────────
        method_counts = {}
        for p in payments:
            # Include Paid AND Partial — both have actual money collected
            if _kpi_eff(p) in ('Paid', 'Partial') and float(p.get('amount') or 0) > 0:
                m = p.get('payment_method', 'Other') or 'Other'
                method_counts[m] = method_counts.get(m, 0) + float(p.get('amount') or 0)
        method_colors = [t['green'], t['blue'], t['accent'], t['orange'], t['purple']]
        method_data = [(m, int(v), method_colors[i % len(method_colors)])
                       for i, (m, v) in enumerate(sorted(method_counts.items(), key=lambda x: -x[1]))]
        self.method_donut.set_data(method_data if method_data else [("No data", 1, t['border'])])

        # ── Status Donut ─────────────────────
        status_counts = {}
        for p in payments:
            s = _kpi_eff(p)  # use computed status, not raw DB status
            status_counts[s] = status_counts.get(s, 0) + 1
        status_c = {'Paid': t['green'], 'Pending': t['accent'], 'Overdue': t['red'],
                    'Partial': t['orange'], 'Advanced': t['blue']}
        status_data = [(s, c, status_c.get(s, t['text_muted']))
                       for s, c in sorted(status_counts.items(), key=lambda x: -x[1])]
        self.status_donut_rpt.set_data(status_data if status_data else [("No data", 1, t['border'])])

        # ── Per-Renter Table (all active renters, even those with no payments) ─
        try:
            all_renters = self.renter_db.get_all_renters()
        except Exception:
            all_renters = []

        # Build base dict from all renters first
        renter_data = {}
        for renter in all_renters:
            name = f"{renter.get('first_name', '')} {renter.get('last_name', '')}".strip()
            if not name:
                continue
            status = renter.get('renter_status', 'Active')
            renter_data[name] = {
                'paid': 0.0, 'pending': 0.0, 'overdue': 0.0,
                'partial': 0.0, 'txns': 0, 'last': None,
                'renter_status': status
            }

        # Now fill in payment data
        for p in payments:
            name = p.get('renter_name', '?') or '?'
            if name not in renter_data:
                renter_data[name] = {'paid': 0.0, 'pending': 0.0, 'overdue': 0.0,
                                     'partial': 0.0, 'txns': 0, 'last': None, 'renter_status': 'Active'}
            renter_data[name]['txns'] += 1
            amt = float(p.get('amount') or 0)
            s = _kpi_eff(p)
            if s == 'Paid':
                renter_data[name]['paid'] += amt
                pd_val = p.get('payment_date')
                if pd_val and (not renter_data[name]['last'] or pd_val > renter_data[name]['last']):
                    renter_data[name]['last'] = pd_val
            elif s == 'Pending':
                renter_data[name]['pending'] += amt
            elif s == 'Overdue':
                renter_data[name]['overdue'] += amt
            elif s == 'Partial':
                renter_data[name]['partial'] += amt

        self.rpt_renter_table.setRowCount(0)
        for i, (name, d) in enumerate(sorted(renter_data.items())):
            total_due = d['paid'] + d['pending'] + d['overdue'] + d['partial']
            rate = int(d['paid'] / total_due * 100) if total_due > 0 else 0
            health = "Good" if rate >= 80 else ("At Risk" if rate >= 50 else "Poor")
            renter_status = d.get('renter_status', 'Active')
            self._set_table_row(self.rpt_renter_table, i, [
                name,
                renter_status,
                f"₱{d['paid']:,.2f}",
                f"₱{d['pending']:,.2f}",
                f"₱{d['overdue']:,.2f}",
                f"₱{d['partial']:,.2f}",
                d['txns'],
                str(d['last'])[:10] if d['last'] else "-",
                f"{rate}% - {health}",
            ])
            # Color renter status
            rs_colors = {'Active': t['green'], 'Inactive': t['text_muted'], 'Blacklisted': t['red']}
            self.rpt_renter_table.item(i, 1).setForeground(QColor(rs_colors.get(renter_status, t['text_muted'])))
            # Color the overdue column
            if d['overdue'] > 0:
                self.rpt_renter_table.item(i, 4).setForeground(QColor(t['red']))
            # Color the status column
            health_colors = {"Good": t['green'], "At Risk": t['accent'], "Poor": t['red']}
            h_color = next((v for k, v in health_colors.items() if k in health), t['text'])
            self.rpt_renter_table.item(i, 8).setForeground(QColor(h_color))

        # ── Overdue Alerts ────────────────────
        # Use effective status (not raw DB status) so newly-overdue bills appear
        overdue_payments = [p for p in payments if _kpi_eff(p) == 'Overdue']
        self.rpt_overdue_table.setRowCount(0)
        import calendar as _cal_ov
        from datetime import date as _d_ov
        _today_ov = _d_ov.today()
        today_q = QDate.currentDate()
        for i, p in enumerate(overdue_payments):
            # Compute due date = 5th of billing month
            due_date_str = '-'
            days = "-"
            try:
                parts = str(p.get('billing_month', '') or '').strip().split()
                mo_num = list(_cal_ov.month_name).index(parts[0])
                yr_num = int(parts[1])
                due_dt = _d_ov(yr_num, mo_num, 5)
                due_date_str = due_dt.strftime("%Y-%m-%d")
                days = str((_today_ov - due_dt).days)
            except Exception:
                pass
            self._set_table_row(self.rpt_overdue_table, i, [
                p.get('invoice_number', '-'),
                p.get('renter_name', '-'),
                f"₱{float(p.get('amount') or 0):,.2f}",
                f"₱{float(p.get('balance_amount') or 0):,.2f}",
                p.get('billing_month', '-'),
                due_date_str,
                days
            ])
            self.rpt_overdue_table.item(i, 2).setForeground(QColor(t['red']))
            self.rpt_overdue_table.item(i, 3).setForeground(QColor(t['orange']))
            if days != "-":
                try:
                    d_int = int(days)
                    urgency = t['red'] if d_int > 30 else t['orange']
                    self.rpt_overdue_table.item(i, 6).setForeground(QColor(urgency))
                except Exception:
                    pass

        # ── Recent Payments (last 15) ─────────
        sorted_payments = sorted(payments, key=lambda p: str(p.get('payment_date', '')), reverse=True)
        self.rpt_recent_table.setRowCount(0)
        status_colors = {'Paid': t['green'], 'Pending': t['accent'], 'Overdue': t['red'],
                         'Partial': t['orange'], 'Advanced': t['blue']}
        for i, p in enumerate(sorted_payments[:15]):
            self._set_table_row(self.rpt_recent_table, i, [
                p.get('invoice_number', '-'),
                p.get('renter_name', '-'),
                f"₱{float(p.get('amount') or 0):,.2f}",
                p.get('payment_method', '-'),
                p.get('billing_month', '-'),
                str(p.get('payment_date', '-'))[:10],
                p.get('status', '-'),
            ])
            sc = status_colors.get(p.get('status', ''), t['text'])
            item = self.rpt_recent_table.item(i, 6)
            if item is not None:
                item.setForeground(QColor(sc))

        # ── Renter Status Donut + Debt Table ─────────────────────
        try:
            renter_status_data = self.payment_db.get_renter_payment_status_summary()
            self._all_renter_status_data = renter_status_data   # cache for filter
            counts = {'Paid': 0, 'Pending': 0, 'Overdue': 0, 'Partial': 0}
            for row in renter_status_data:
                s = row.get('status', 'Pending')
                if s in counts:
                    counts[s] += 1

            # Update KPI cards in reports tab
            for attr, key in [('rpt_rs_paid', 'Paid'), ('rpt_rs_pending', 'Pending'),
                               ('rpt_rs_overdue', 'Overdue'), ('rpt_rs_partial', 'Partial')]:
                if hasattr(self, attr):
                    getattr(self, attr).set_value(counts[key])

            # Status donut
            status_donut_data = []
            sc = {'Paid': t['green'], 'Pending': t['accent'], 'Overdue': t['red'], 'Partial': t['orange']}
            for s, n in counts.items():
                if n > 0:
                    status_donut_data.append((s, n, sc[s]))
            if hasattr(self, 'rpt_renter_status_donut'):
                self.rpt_renter_status_donut.set_data(
                    status_donut_data if status_donut_data else [("No Data", 1, t['border'])]
                )

            # Debt table
            if hasattr(self, 'rpt_debt_table'):
                self.rpt_debt_table.setRowCount(0)
                for i, row in enumerate(renter_status_data):
                    status = row.get('status', 'Pending')
                    self._set_table_row(self.rpt_debt_table, i, [
                        row.get('room_number', '-'),
                        row.get('bed', '-'),
                        row.get('full_name', '-'),
                        row.get('billing_month', '-'),
                        status,
                        f"₱{row.get('paid_this_month', 0):,.2f}",
                        f"₱{row.get('debt_this_month', 0):,.2f}",
                        f"₱{row.get('total_outstanding', 0):,.2f}",
                    ])
                    color = sc.get(status, t['text'])
                    self.rpt_debt_table.item(i, 4).setForeground(QColor(color))
                    if row.get('debt_this_month', 0) > 0:
                        self.rpt_debt_table.item(i, 6).setForeground(QColor(t['orange']))
                    if row.get('total_outstanding', 0) > 0:
                        self.rpt_debt_table.item(i, 7).setForeground(QColor(t['red']))
        except Exception as _rs_e:
            print(f"[load_reports renter_status] {_rs_e}")

        # ── ALL-MONTHS Revenue Section ────────
        try:
            all_rev_data = self.reports_db.get_monthly_revenue_all()
            self._all_months_data = all_rev_data

            # Update month-jump combo
            if hasattr(self, 'rpt_all_month_filter'):
                sel = self.rpt_all_month_filter.currentText()
                self.rpt_all_month_filter.blockSignals(True)
                self.rpt_all_month_filter.clear()
                self.rpt_all_month_filter.addItem("All Months")
                for d in all_rev_data:
                    self.rpt_all_month_filter.addItem(self._fmt_month_label(d.get("month", "")))
                idx = self.rpt_all_month_filter.findText(sel)
                self.rpt_all_month_filter.setCurrentIndex(idx if idx >= 0 else 0)
                self.rpt_all_month_filter.blockSignals(False)

            # All-months bar chart (all data, colour by health)
            if hasattr(self, 'all_months_bar_chart'):
                bar_colors_all = [t['green'], t['blue'], t['accent'], t['orange'],
                                  t['purple'], t['teal'], t['red']]
                bar_data_all = [
                    (self._fmt_month_label(d["month"]), int(d["collected"]), bar_colors_all[i % len(bar_colors_all)])
                    for i, d in enumerate(all_rev_data)
                ]
                self.all_months_bar_chart.set_data(
                    bar_data_all if bar_data_all else [("No data", 0, t['border'])]
                )

            # All-months table
            if hasattr(self, 'rpt_all_months_table'):
                self._populate_all_months_table(all_rev_data)
        except Exception as _am_e:
            print(f"[load_reports all-months] {_am_e}")
            period       = self.rpt_period_filter.currentText() if hasattr(self, 'rpt_period_filter') else "Last 6 Months"
            n_months_map = {"Last 6 Months": 6, "Last 12 Months": 12, "All Time": 99}
            n_months     = n_months_map.get(period, 6)
            summary      = self.reports_db.get_profitability_summary(n_months)

            totals = summary.get("totals", {})
            gross  = totals.get("revenue",    0.0)
            exp    = totals.get("expenses",   0.0)
            profit = totals.get("profit",     0.0)
            margin = totals.get("margin_pct", 0.0)
            breakdown = summary.get("expense_breakdown", {})

            if hasattr(self, 'rpt_gross_revenue'):
                self.rpt_gross_revenue.set_value(f"₱{gross:,.0f}")
            if hasattr(self, 'rpt_total_expenses'):
                self.rpt_total_expenses.set_value(f"₱{exp:,.0f}")
            if hasattr(self, 'rpt_net_profit'):
                self.rpt_net_profit.set_value(f"₱{profit:,.0f}")
            if hasattr(self, 'rpt_profit_margin'):
                self.rpt_profit_margin.set_value(f"{margin}%")
            if hasattr(self, 'rpt_wifi_cost'):
                self.rpt_wifi_cost.set_value(f"₱{breakdown.get('wifi', 0):,.0f}")

            elec  = breakdown.get('electricity', 0)
            water = breakdown.get('water', 0)
            wifi  = breakdown.get('wifi',  0)
            self.rpt_expense_breakdown_lbl.setText(
                f"Avg monthly expense breakdown - "
                f"⚡ Electricity: ₱{elec:,.0f}  |  💧 Water: ₱{water:,.0f}  |   WiFi: ₱{wifi:,.0f} (fixed)"
            )

            # Monthly profitability table
            monthly_rows = summary.get("monthly", [])
            self.rpt_profit_table.setRowCount(0)
            for i, row in enumerate(monthly_rows):
                rev   = row["revenue"]
                exp_m = row["expenses"]
                prf   = row["profit"]
                mrg   = row["margin_pct"]
                health = "Profitable" if prf >= 0 else "Loss"
                self._set_table_row(self.rpt_profit_table, i, [
                    row["month"],
                    f"₱{rev:,.2f}",
                    f"₱{exp_m:,.2f}",
                    f"₱{prf:,.2f}",
                    f"{mrg}%",
                    health,
                ])
                profit_col = t['green'] if prf >= 0 else t['red']
                for col_idx in [3, 5]:
                    item = self.rpt_profit_table.item(i, col_idx)
                    if item:
                        item.setForeground(QColor(profit_col))
        except Exception as e:
            print(f"[load_reports profitability] {e}")

    # ══════════════════════════════════════════
    #  MAINTENANCE PAGE
    # ══════════════════════════════════════════
    def _build_maintenance_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        hdr_row = QHBoxLayout()
        title = QLabel("Maintenance Requests")
        title.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
        # Only renters submit maintenance requests; staff/admin manage them.
        self.maint_add_btn = make_btn("  Submit Request", T("green"), "white",
                                      icon="fa5s.plus", icon_color="white")
        self.maint_add_btn.clicked.connect(self.open_add_maintenance_dialog)
        hdr_row.addWidget(title)
        hdr_row.addStretch()
        hdr_row.addWidget(self.maint_add_btn)
        layout.addLayout(hdr_row)

        # Mini stats
        maint_stats = QHBoxLayout()
        maint_stats.setSpacing(12)
        self.mst_pending   = StatCard("Pending",   "-", T("accent"), "fa5s.clock")
        self.mst_progress  = StatCard("In Progress","-", T("blue"),   "fa5s.spinner")
        self.mst_completed = StatCard("Completed", "-", T("green"),  "fa5s.check-circle")
        self.mst_high      = StatCard("High Prio", "-", T("red"),    "fa5s.fire")
        for c in [self.mst_pending, self.mst_progress, self.mst_completed, self.mst_high]:
            c.setFixedHeight(100)
            maint_stats.addWidget(c)
        layout.addLayout(maint_stats)

        # Filter
        filter_row = QHBoxLayout()
        self.maint_search = QLineEdit()
        self.maint_search.setPlaceholderText("⌕  Search by room or issue...")
        self.maint_search.setStyleSheet(input_style() + "min-height: 36px;")
        self.maint_search.textChanged.connect(self._filter_maintenance)
        self.maint_status_filter = QComboBox()
        self.maint_status_filter.addItems(["All", "Pending", "In Progress", "Completed"])
        self.maint_status_filter.setStyleSheet(input_style() + "min-width: 120px;")
        self.maint_status_filter.currentTextChanged.connect(self._filter_maintenance)
        self.maint_priority_filter = QComboBox()
        self.maint_priority_filter.addItems(["All Priorities", "High", "Medium", "Low"])
        self.maint_priority_filter.setStyleSheet(input_style() + "min-width: 120px;")
        self.maint_priority_filter.currentTextChanged.connect(self._filter_maintenance)
        filter_row.addWidget(self.maint_search)
        filter_row.addWidget(self.maint_status_filter)
        filter_row.addWidget(self.maint_priority_filter)
        layout.addLayout(filter_row)

        self.maintenance_table = self._make_table(
            ["ID", "Room", "Renter", "Issue", "Priority", "Status", "Date Requested"]
        )
        layout.addWidget(self.maintenance_table)

        btn_row = QHBoxLayout()
        view_btn    = make_btn("  View Detail",  T("blue"),  "white", icon="fa5s.eye",          icon_color="white")
        self.maint_resolve_btn = make_btn("  Mark Resolved", T("green"), "white",
                                          icon="fa5s.check-circle", icon_color="white")
        self.maint_progress_btn = make_btn("  In Progress", T("blue"), "white",
                                           icon="fa5s.spinner", icon_color="white")
        self.maint_delete_btn = make_btn("  Delete", T("red"), "white", icon="fa5s.trash-alt", icon_color="white")
        view_btn.clicked.connect(self._view_maintenance)
        self.maint_resolve_btn.clicked.connect(self.resolve_maintenance)
        self.maint_progress_btn.clicked.connect(self._mark_maintenance_in_progress)
        self.maint_delete_btn.clicked.connect(self.delete_maintenance)
        btn_row.addStretch()
        btn_row.addWidget(view_btn)
        btn_row.addWidget(self.maint_progress_btn)
        btn_row.addWidget(self.maint_resolve_btn)
        btn_row.addWidget(self.maint_delete_btn)
        layout.addLayout(btn_row)
        return page

    def _get_all_maintenance(self):
        try:
            return self.maintenance_db.get_all_requests()
        except Exception:
            return []

    def load_maintenance(self):
        requests = self._get_all_maintenance()
        self._display_maintenance(requests)
        self._update_maintenance_stats(requests)

    def _update_maintenance_stats(self, requests):
        pending   = sum(1 for r in requests if r.get('status') == 'Pending')
        progress  = sum(1 for r in requests if r.get('status') == 'In Progress')
        completed = sum(1 for r in requests if r.get('status') == 'Completed')
        high      = sum(1 for r in requests if r.get('priority') == 'High')
        if hasattr(self, 'mst_pending'):
            self.mst_pending.set_value(pending)
            self.mst_progress.set_value(progress)
            self.mst_completed.set_value(completed)
            self.mst_high.set_value(high)

    def _display_maintenance(self, requests):
        self.maintenance_table.setRowCount(0)
        t = Theme.get()
        priority_colors = {"High": t['red'], "Medium": t['accent'], "Low": t['green']}
        status_colors   = {"Pending": t['accent'], "In Progress": t['blue'], "Completed": t['green']}
        for i, r in enumerate(requests):
            self._set_table_row(self.maintenance_table, i, [
                r.get('request_id', ''), r.get('room_number', '-'), r.get('renter_name', '-'),
                r.get('description', '-'), r.get('priority', '-'), r.get('status', '-'),
                str(r.get('request_date', '-'))
            ])
            self.maintenance_table.item(i, 4).setForeground(QColor(priority_colors.get(r['priority'], t['text'])))
            self.maintenance_table.item(i, 5).setForeground(QColor(status_colors.get(r['status'], t['text'])))

    def _filter_maintenance(self):
        requests = self._get_all_maintenance()
        kw = self.maint_search.text().strip().lower() if hasattr(self, 'maint_search') else ""
        sf = self.maint_status_filter.currentText() if hasattr(self, 'maint_status_filter') else "All"
        pf = self.maint_priority_filter.currentText() if hasattr(self, 'maint_priority_filter') else "All Priorities"
        if kw:
            requests = [r for r in requests if
                        kw in str(r.get('room_number', '')).lower() or
                        kw in str(r.get('description', '')).lower() or
                        kw in str(r.get('renter_name', '')).lower()]
        if sf != "All":
            requests = [r for r in requests if r.get('status') == sf]
        if pf != "All Priorities":
            requests = [r for r in requests if r.get('priority') == pf]
        self._display_maintenance(requests)
        self._update_maintenance_stats(requests)

    def _view_maintenance(self):
        row = self.maintenance_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a request.")
            return
        request_id = int(self.maintenance_table.item(row, 0).text())
        requests = self._get_all_maintenance()
        req = next((r for r in requests if r['request_id'] == request_id), None)
        if req:
            dlg = MaintenanceDetailDialog(self, req)
            dlg.exec()

    def _mark_maintenance_in_progress(self):
        row = self.maintenance_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a request.")
            return
        request_id = int(self.maintenance_table.item(row, 0).text())
        try:
            ok = self.maintenance_db.update_status(request_id, "In Progress", "", None)
            if ok:
                self.load_maintenance()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def open_add_maintenance_dialog(self):
        rooms   = self.room_db.get_all_rooms()
        renters = self.renter_db.get_all_renters()
        dlg = MaintenanceDialog(self, rooms, renters)
        if dlg.exec():
            data = dlg.get_data()
            _actor_role = (self.current_user or {}).get('role', 'Admin')
            _actor_id   = (self.current_user or {}).get('admin_id') or \
                          (self.current_user or {}).get('renter_id')
            ok = self.maintenance_db.add_request(
                **data,
                actor_role=_actor_role,
                actor_id=_actor_id
            )
            if ok:
                QMessageBox.information(self, "Success", "Request added!")
                self.load_maintenance()
            else:
                QMessageBox.critical(self, "Error", "Failed to add request.")

    def resolve_maintenance(self):
        row = self.maintenance_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a request.")
            return
        request_id = int(self.maintenance_table.item(row, 0).text())
        ok = self.maintenance_db.update_status(request_id, "Completed",
                                               "Resolved by admin.",
                                               QDate.currentDate().toString("yyyy-MM-dd"))
        if ok:
            if self.current_user and self.current_user.get('admin_id'):
                self.admin_db.add_log(self.current_user['admin_id'], 'RESOLVE_MAINTENANCE',
                                      f"Resolved request ID {request_id}")
            self.load_maintenance()

    def delete_maintenance(self):
        row = self.maintenance_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a request.")
            return
        request_id = int(self.maintenance_table.item(row, 0).text())
        reply = QMessageBox.question(self, "Confirm", "Delete this request?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            ok = self.maintenance_db.delete_request(request_id)
            if ok:
                self.load_maintenance()

    # ══════════════════════════════════════════
    #  VISITORS PAGE
    # ══════════════════════════════════════════
    def _build_visitors_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addWidget(page_header("Visitor Logs", "  Log Visitor In", self.open_add_visitor_dialog, btn_icon="fa5s.sign-in-alt"))
        layout.addSpacing(10)
        self.visitors_table = self._make_table(
            ["ID", "Visitor Name", "Relationship", "Visiting Renter", "Time In", "Time Out"]
        )
        layout.addWidget(self.visitors_table)
        btn_row = QHBoxLayout()
        out_btn = make_btn("  Log Out",  T("blue"), "white", icon="fa5s.sign-out-alt", icon_color="white")
        self.visitor_delete_btn = make_btn("  Delete", T("red"), "white", icon="fa5s.trash-alt", icon_color="white")
        out_btn.clicked.connect(self.log_visitor_out)
        self.visitor_delete_btn.clicked.connect(self.delete_visitor)
        btn_row.addStretch()
        btn_row.addWidget(out_btn)
        btn_row.addWidget(self.visitor_delete_btn)
        layout.addLayout(btn_row)
        return page

    def load_visitors(self):
        visitors = self.visitor_db.get_all_visitors()
        self.visitors_table.setRowCount(0)
        for i, v in enumerate(visitors):
            self._set_table_row(self.visitors_table, i, [
                v['visitor_id'], v['visitor_name'], v['relationship'],
                v['renter_name'], str(v['time_in']),
                str(v['time_out']) if v['time_out'] else "Still In"
            ])
            t = Theme.get()
            if not v.get('time_out'):
                self.visitors_table.item(i, 5).setForeground(QColor(t['green']))

    def open_add_visitor_dialog(self):
        renters = self.renter_db.get_all_renters()
        dlg = VisitorDialog(self, renters)
        if dlg.exec():
            data = dlg.get_data()
            ok = self.visitor_db.log_visitor_in(**data)
            if ok:
                self.load_visitors()

    def log_visitor_out(self):
        row = self.visitors_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a visitor.")
            return
        visitor_id = int(self.visitors_table.item(row, 0).text())
        from datetime import datetime
        ok = self.visitor_db.log_visitor_out(visitor_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if ok:
            self.load_visitors()

    def delete_visitor(self):
        row = self.visitors_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a visitor.")
            return
        visitor_id = int(self.visitors_table.item(row, 0).text())
        reply = QMessageBox.question(self, "Confirm", "Delete this visitor log?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            ok = self.visitor_db.delete_visitor_log(visitor_id)
            if ok:
                self.load_visitors()

    # ══════════════════════════════════════════
    #  ACTIVITY LOGS PAGE
    # ══════════════════════════════════════════
    # ══════════════════════════════════════════
    #  MY PROFILE PAGE  (all roles)
    # ══════════════════════════════════════════
    def _build_profile_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        layout.addWidget(page_header("My Profile"))

        # ── Profile card ──────────────────────
        top_card = self._card_frame()
        top_card.setFixedHeight(160)
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(24, 24, 24, 24)
        top_layout.setSpacing(20)

        self.profile_avatar = AvatarWidget("?", 100)
        top_layout.addWidget(self.profile_avatar)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        self.profile_name_lbl = QLabel("-")
        self.profile_name_lbl.setStyleSheet(f"color: {T('text')}; font-size: 22px; font-weight: bold; background: transparent; border: none;")
        self.profile_role_lbl = QLabel("-")
        self.profile_role_lbl.setStyleSheet(f"color: {T('accent')}; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        self.profile_user_lbl = QLabel("-")
        self.profile_user_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px; background: transparent; border: none;")
        info_col.addWidget(self.profile_name_lbl)
        info_col.addWidget(self.profile_role_lbl)
        info_col.addWidget(self.profile_user_lbl)
        info_col.addStretch()

        top_layout.addLayout(info_col)
        top_layout.addStretch()

        change_pic_btn = make_btn("  Change Photo", T("blue"), "white", icon="fa5s.camera", icon_color="white")
        change_pic_btn.clicked.connect(self._profile_change_photo)
        top_layout.addWidget(change_pic_btn, alignment=Qt.AlignBottom)

        remove_pic_btn = make_btn("  Remove Photo", T("red"), "white", icon="fa5s.trash-alt", icon_color="white")
        remove_pic_btn.clicked.connect(self._profile_remove_photo)
        top_layout.addWidget(remove_pic_btn, alignment=Qt.AlignBottom)
        layout.addWidget(top_card)

        # ── Edit info form ──────────────────
        edit_card = self._card_frame()
        edit_layout = QVBoxLayout(edit_card)
        edit_layout.setContentsMargins(24, 24, 24, 24)
        edit_layout.setSpacing(14)

        edit_hdr = QLabel("Edit Profile Information")
        edit_hdr.setStyleSheet(f"color: {T('text')}; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        edit_layout.addWidget(edit_hdr)

        form_grid = QGridLayout()
        form_grid.setSpacing(10)

        def mk_lbl(txt):
            l = QLabel(txt)
            l.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px; background: transparent; border: none;")
            return l

        def mk_inp(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setStyleSheet(input_style())
            return e

        self.prof_fullname   = mk_inp("Full Name")
        self.prof_email      = mk_inp("Email")
        self.prof_contact    = mk_inp("Contact Number")

        form_grid.addWidget(mk_lbl("Full Name"),       0, 0)
        form_grid.addWidget(self.prof_fullname,         0, 1)
        form_grid.addWidget(mk_lbl("Email"),           1, 0)
        form_grid.addWidget(self.prof_email,            1, 1)
        form_grid.addWidget(mk_lbl("Contact No."),     2, 0)
        form_grid.addWidget(self.prof_contact,          2, 1)
        edit_layout.addLayout(form_grid)

        save_info_btn = make_btn("  Save Changes", T("green"), "white", icon="fa5s.save", icon_color="white", width=160)
        save_info_btn.clicked.connect(self._profile_save_info)
        edit_layout.addWidget(save_info_btn, alignment=Qt.AlignRight)
        layout.addWidget(edit_card)

        # ── Change password ──────────────────
        pw_card = self._card_frame()
        pw_layout = QVBoxLayout(pw_card)
        pw_layout.setContentsMargins(24, 24, 24, 24)
        pw_layout.setSpacing(14)

        pw_hdr = QLabel("Change Password")
        pw_hdr.setStyleSheet(f"color: {T('text')}; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        pw_layout.addWidget(pw_hdr)

        pw_grid = QGridLayout()
        pw_grid.setSpacing(10)
        self.prof_old_pw  = mk_inp("Current Password")
        self.prof_old_pw.setEchoMode(QLineEdit.Password)
        self.prof_new_pw  = mk_inp("New Password")
        self.prof_new_pw.setEchoMode(QLineEdit.Password)
        self.prof_new_pw2 = mk_inp("Confirm New Password")
        self.prof_new_pw2.setEchoMode(QLineEdit.Password)

        pw_grid.addWidget(mk_lbl("Current Password"),  0, 0)
        pw_grid.addWidget(self.prof_old_pw,             0, 1)
        pw_grid.addWidget(mk_lbl("New Password"),       1, 0)
        pw_grid.addWidget(self.prof_new_pw,             1, 1)
        pw_grid.addWidget(mk_lbl("Confirm Password"),   2, 0)
        pw_grid.addWidget(self.prof_new_pw2,            2, 1)
        pw_layout.addLayout(pw_grid)

        save_pw_btn = make_btn("  Update Password", T("orange"), "white", icon="fa5s.lock", icon_color="white", width=180)
        save_pw_btn.clicked.connect(self._profile_save_password)
        pw_layout.addWidget(save_pw_btn, alignment=Qt.AlignRight)
        layout.addWidget(pw_card)

        # ── Payroll section (staff/admin only) ──
        self.payroll_card = self._card_frame()
        payroll_layout = QVBoxLayout(self.payroll_card)
        payroll_layout.setContentsMargins(24, 24, 24, 24)
        payroll_layout.setSpacing(14)

        pay_hdr = QLabel("My Monthly Salary Records")
        pay_hdr.setStyleSheet(f"color: {T('text')}; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        payroll_layout.addWidget(pay_hdr)

        self.payroll_table = self._make_table([
            "Period", "Basic Salary", "Allowances", "Deductions", "Net Pay", "Pay Date", "Method"
        ])
        self.payroll_table.setMaximumHeight(220)
        payroll_layout.addWidget(self.payroll_table)

        # Summary row
        self.payroll_summary_lbl = QLabel("")
        self.payroll_summary_lbl.setStyleSheet(f"color: {T('green')}; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        payroll_layout.addWidget(self.payroll_summary_lbl)
        layout.addWidget(self.payroll_card)

        layout.addStretch()
        scroll.setWidget(page)
        return scroll

    # ══════════════════════════════════════════
    #  ROOM SWITCH REQUESTS PAGE  (Admin only)
    # ══════════════════════════════════════════
    def _build_switch_requests_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header = QHBoxLayout()
        self.switch_title_lbl = QLabel("Room Switch Requests")
        self.switch_title_lbl.setStyleSheet(f"color: {T('text')}; font-size: 26px; font-weight: bold;")
        self.switch_count_lbl = QLabel("0 pending")
        self.switch_count_lbl.setStyleSheet(
            f"color: {T('accent')}; font-size: 14px; font-weight: bold; "
            f"background: {T('surface2')}; padding: 6px 14px; border-radius: 16px;"
        )
        refresh_btn = QPushButton("  Refresh")
        refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color=T("accent")))
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet(
            f"color: {T('accent')}; background: {T('surface2')}; "
            f"padding: 8px 16px; border-radius: 10px; font-weight: bold; border: none;"
        )
        refresh_btn.clicked.connect(self.load_switch_requests)

        header.addWidget(self.switch_title_lbl)
        header.addStretch()
        header.addWidget(self.switch_count_lbl)
        header.addSpacing(10)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        # ── RENTER SUBMIT PANEL (visible only to renters) ──
        self.renter_switch_panel = QFrame()
        self.renter_switch_panel.setStyleSheet(
            f"background: {T('surface')}; border-radius: 14px; "
            f"border: 1px solid {T('border')};"
        )
        rsp_l = QVBoxLayout(self.renter_switch_panel)
        rsp_l.setContentsMargins(20, 16, 20, 16)
        rsp_l.setSpacing(10)
        rsp_hdr = QLabel("Request to Switch Rooms")
        rsp_hdr.setStyleSheet(f"color: {T('text')}; font-size: 16px; font-weight: bold; "
                              f"background: transparent; border: none;")
        rsp_sub = QLabel("Pick the room you'd like to move to. Admins will review and "
                         "confirm - no movement happens until they approve.")
        rsp_sub.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px; "
                              f"background: transparent; border: none;")
        rsp_sub.setWordWrap(True)
        rsp_l.addWidget(rsp_hdr)
        rsp_l.addWidget(rsp_sub)

        form_row = QHBoxLayout()
        self.renter_switch_room_combo = QComboBox()
        self.renter_switch_room_combo.setStyleSheet(input_style() + "min-width: 180px;")
        self.renter_switch_bed = QLineEdit()
        self.renter_switch_bed.setPlaceholderText("Bed (e.g. Bed 2 - optional)")
        self.renter_switch_bed.setStyleSheet(input_style() + "min-height: 36px;")
        self.renter_switch_reason = QLineEdit()
        self.renter_switch_reason.setPlaceholderText("Reason for switching...")
        self.renter_switch_reason.setStyleSheet(input_style() + "min-height: 36px;")
        submit_btn = make_btn("  Submit Request", T("accent"), T("bg"),
                              icon="fa5s.paper-plane", icon_color=T("bg"))
        submit_btn.clicked.connect(self._renter_submit_switch_request)
        form_row.addWidget(QLabel("Desired Room:"))
        form_row.addWidget(self.renter_switch_room_combo, 1)
        form_row.addWidget(self.renter_switch_bed, 1)
        form_row.addWidget(self.renter_switch_reason, 2)
        form_row.addWidget(submit_btn)
        rsp_l.addLayout(form_row)
        layout.addWidget(self.renter_switch_panel)
        self.renter_switch_panel.setVisible(False)

        sub = QLabel("Renters request to move to a different room/bed. Approve to "
                     "automatically end their current assignment and create the new one.")
        sub.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px;")
        layout.addWidget(sub)

        filter_row = QHBoxLayout()
        self.switch_filter = QComboBox()
        self.switch_filter.addItems(["All", "Pending", "Approved", "Rejected"])
        self.switch_filter.setCurrentText("Pending")
        self.switch_filter.setStyleSheet(
            f"color: {T('text')}; background: {T('surface2')}; "
            f"padding: 8px 14px; border-radius: 8px; border: 1px solid {T('border')};"
        )
        self.switch_filter.currentTextChanged.connect(lambda _: self.load_switch_requests())
        f_lbl = QLabel("Status:")
        f_lbl.setStyleSheet(f"color: {T('text_muted')}; font-size: 13px;")
        filter_row.addWidget(f_lbl)
        filter_row.addWidget(self.switch_filter)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.switch_table = QTableWidget()
        self.switch_table.setColumnCount(8)
        self.switch_table.setHorizontalHeaderLabels(
            ["Renter", "Current Room", "Desired Room", "Bed", "Reason",
             "Status", "Requested", "Action"]
        )
        self.switch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.switch_table.verticalHeader().setVisible(False)
        self.switch_table.setStyleSheet(
            f"QTableWidget {{ background: {T('surface')}; color: {T('text')}; "
            f"border: 1px solid {T('border')}; border-radius: 10px; gridline-color: {T('border')}; }}"
            f"QHeaderView::section {{ background: {T('surface2')}; color: {T('text')}; "
            f"padding: 10px; border: none; font-weight: bold; }}"
        )
        self.switch_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.switch_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.switch_table)

        scroll.setWidget(page)
        return scroll

    def _renter_submit_switch_request(self):
        renter_id = (self.current_user or {}).get('renter_id')
        if not renter_id:
            return
        idx = self.renter_switch_room_combo.currentIndex()
        if idx < 0 or not getattr(self, '_renter_switch_room_ids', None):
            QMessageBox.warning(self, "Pick a Room", "Please choose a room.")
            return
        desired_room_id = self._renter_switch_room_ids[idx]
        bed = self.renter_switch_bed.text().strip() or None
        reason = self.renter_switch_reason.text().strip()
        # Find current assignment room id
        current_room_id = None
        try:
            assignment = self.renter_db.get_renter_assignment(renter_id)
            if assignment:
                current_room_id = assignment.get('room_id')
        except Exception:
            pass
        if current_room_id == desired_room_id:
            QMessageBox.information(self, "Same Room",
                                    "That's already your current room.")
            return
        ok = self.switch_db.add_request(renter_id, current_room_id,
                                        desired_room_id, bed, reason)
        if ok:
            try:
                self.admin_db.add_log(
                    None, "RENTER_SWITCH_REQUEST",
                    f"Renter #{renter_id} requested switch to room "
                    f"#{desired_room_id} ({bed or 'any bed'}) - {reason or 'no reason'}",
                    actor_role="Renter", renter_id=renter_id)
            except Exception:
                pass
            QMessageBox.information(self, "Submitted",
                                    "Your switch request was sent. Admin will review.")
            self.renter_switch_reason.clear()
            self.renter_switch_bed.clear()
            self.load_switch_requests()
        else:
            QMessageBox.critical(self, "Error", "Could not submit request.")

    def _populate_renter_switch_rooms(self):
        try:
            rooms = self.room_db.get_all_rooms_with_beds()
        except Exception:
            rooms = []
        self._renter_switch_room_ids = []
        self.renter_switch_room_combo.clear()
        for r in rooms:
            cap = int(r.get('capacity') or 0)
            occ = int(r.get('occupied') or 0)
            if cap > 0 and occ < cap and r.get('status') != 'Under Maintenance':
                self.renter_switch_room_combo.addItem(
                    f"Room {r.get('room_number')} · {r.get('floor_level','')} "
                    f"· {cap-occ} bed(s) free")
                self._renter_switch_room_ids.append(r.get('room_id'))

    def load_switch_requests(self):
        if not hasattr(self, 'switch_table'):
            return
        is_renter = (self.current_user or {}).get('role') == 'Renter'
        self.renter_switch_panel.setVisible(is_renter)
        if is_renter:
            self.switch_title_lbl.setText("My Room Switch Requests")
            self._populate_renter_switch_rooms()
            renter_id = self.current_user.get('renter_id')
            try:
                rows = self.switch_db.get_renter_requests(renter_id) or []
            except Exception:
                rows = []
            try:
                self.switch_filter.setVisible(False)
            except Exception:
                pass
        else:
            self.switch_title_lbl.setText("Room Switch Requests")
            try:
                self.switch_filter.setVisible(True)
            except Exception:
                pass
            status = self.switch_filter.currentText()
            rows = self.switch_db.get_all_requests(
                status=None if status == "All" else status
            )

        total_pending = self.switch_db.pending_count()
        self.switch_count_lbl.setText(f"{total_pending} pending")

        self.switch_table.clearSpans()
        self.switch_table.setRowCount(len(rows) if rows else 1)

        if not rows:
            empty = QTableWidgetItem("No switch requests found.")
            empty.setForeground(QColor(T("text_muted")))
            self.switch_table.setItem(0, 0, empty)
            self.switch_table.setSpan(0, 0, 1, 8)
            return

        for i, r in enumerate(rows):
            req_at = r.get("requested_at")
            req_str = req_at.strftime("%Y-%m-%d %H:%M") if hasattr(req_at, "strftime") else str(req_at or "")
            cells = [
                r.get("renter_name", self.current_user.get('full_name','You') if is_renter else ""),
                r.get("current_room_number") or "-",
                r.get("desired_room_number", ""),
                r.get("desired_bed") or "-",
                (r.get("reason") or "")[:60],
                r.get("status", ""),
                req_str,
            ]
            for c, val in enumerate(cells):
                item = QTableWidgetItem(str(val))
                if c == 5:
                    color = {"Pending": T("accent"), "Approved": T("green"),
                             "Rejected": T("red")}.get(val, T("text"))
                    item.setForeground(QColor(color))
                self.switch_table.setItem(i, c, item)

            if r.get("status") == "Pending" and not is_renter:
                action_widget = QWidget()
                ah = QHBoxLayout(action_widget)
                ah.setContentsMargins(4, 2, 4, 2)
                ah.setSpacing(6)
                approve_btn = QPushButton("Approve")
                approve_btn.setCursor(Qt.PointingHandCursor)
                approve_btn.setStyleSheet(
                    f"background: {T('green')}; color: white; border: none; "
                    f"padding: 6px 12px; border-radius: 6px; font-weight: bold;"
                )
                approve_btn.clicked.connect(
                    lambda _, rid=r["request_id"]: self._decide_switch(rid, True)
                )
                reject_btn = QPushButton("Reject")
                reject_btn.setCursor(Qt.PointingHandCursor)
                reject_btn.setStyleSheet(
                    f"background: {T('red')}; color: white; border: none; "
                    f"padding: 6px 12px; border-radius: 6px; font-weight: bold;"
                )
                reject_btn.clicked.connect(
                    lambda _, rid=r["request_id"]: self._decide_switch(rid, False)
                )
                ah.addWidget(approve_btn)
                ah.addWidget(reject_btn)
                ah.addStretch()
                self.switch_table.setCellWidget(i, 7, action_widget)
            else:
                decided = QTableWidgetItem("-")
                decided.setForeground(QColor(T("text_muted")))
                self.switch_table.setItem(i, 7, decided)

    def _decide_switch(self, request_id, approve):
        admin_id = (self.current_user or {}).get("admin_id")
        if not admin_id:
            QMessageBox.warning(self, "Unauthorized",
                                "Only admins can decide switch requests.")
            return

        action = "approve" if approve else "reject"
        past_tense = "Approved" if approve else "Rejected"
        notes, ok = QInputDialog.getText(
            self, f"{action.title()} Switch Request",
            f"Optional notes for this {action}:"
        )
        if not ok:
            return

        success = self.switch_db.decide(request_id, admin_id, approve, notes or "")
        if success:
            self.admin_db.add_log(
                admin_id,
                f"{'APPROVE' if approve else 'REJECT'}_SWITCH",
                f"{past_tense} switch request #{request_id}"
            )
            QMessageBox.information(self, "Done", f"Request {past_tense.lower()} successfully.")
            self.load_switch_requests()
            if hasattr(self, "load_vacant_rooms"):
                try: self.load_vacant_rooms()
                except Exception: pass
        else:
            QMessageBox.warning(
                self, "Failed",
                "Could not process the request. The desired room may be full "
                "or the request is no longer pending."
            )

    def load_profile(self):
        if not self.current_user:
            return
        role = self.current_user.get('role', '')
        name = self.current_user.get('full_name', '?')
        username = self.current_user.get('username', '-')

        self.profile_avatar.set_avatar(name)
        self.profile_name_lbl.setText(name)
        self.profile_role_lbl.setText(role)
        self.profile_user_lbl.setText(f"@{username}")

        # Show/hide payroll card
        is_staff_role = role in ('Admin', 'Staff', 'Maintenance', 'Security')
        self.payroll_card.setVisible(is_staff_role)

        if role == 'Renter':
            renter_id = self.current_user.get('renter_id')
            if renter_id:
                try:
                    prof_mod = database.ProfileModule()
                    data = prof_mod.get_renter_profile(renter_id)
                    if data:
                        self.prof_fullname.setText(f"{data.get('first_name','')} {data.get('last_name','')}".strip())
                        self.prof_email.setText(data.get('email') or '')
                        self.prof_contact.setText(data.get('contact_number') or '')
                        pic = data.get('profile_pic_path') or ''
                        if pic and os.path.exists(pic):
                            self.profile_avatar.set_avatar(name, pic)
                except Exception as e:
                    print(f"[load_profile renter] {e}")
        else:
            admin_id = self.current_user.get('admin_id')
            if admin_id:
                try:
                    prof_mod = database.ProfileModule()
                    data = prof_mod.get_admin_profile(admin_id)
                    if data:
                        self.prof_fullname.setText(data.get('full_name') or '')
                        self.prof_email.setText(data.get('email') or '')
                        self.prof_contact.setText(data.get('contact_number') or '')
                        pic = data.get('profile_pic_path') or ''
                        if pic and os.path.exists(pic):
                            self.profile_avatar.set_avatar(name, pic)
                except Exception as e:
                    print(f"[load_profile admin] {e}")

            # Load payroll
            if is_staff_role and admin_id:
                try:
                    pay_mod = database.PayrollModule()
                    pay_mod.setup_table()
                    records = pay_mod.get_payroll_for_admin(admin_id)
                    self.payroll_table.setRowCount(0)
                    total_net = 0.0
                    for i, rec in enumerate(records):
                        net = float(rec.get('net_pay') or 0)
                        total_net += net
                        self._set_table_row(self.payroll_table, i, [
                            rec.get('period_month', '-'),
                            f"₱{float(rec.get('basic_salary',0)):,.2f}",
                            f"₱{float(rec.get('allowances',0)):,.2f}",
                            f"₱{float(rec.get('deductions',0)):,.2f}",
                            f"₱{net:,.2f}",
                            str(rec.get('payment_date') or '-')[:10],
                            rec.get('payment_method', '-'),
                        ])
                    self.payroll_summary_lbl.setText(f"Total net pay received: ₱{total_net:,.2f}")
                except Exception as e:
                    print(f"[load_profile payroll] {e}")

    def _profile_change_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose Profile Photo", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if not path:
            return
        role = self.current_user.get('role', '') if self.current_user else ''
        name = self.current_user.get('full_name', '?') if self.current_user else '?'
        try:
            prof_mod = database.ProfileModule()
            if role == 'Renter':
                renter_id = self.current_user.get('renter_id')
                prof_mod.update_renter_profile(renter_id, profile_pic_path=path)
            else:
                admin_id = self.current_user.get('admin_id')
                prof_mod.update_admin_profile(admin_id, profile_pic_path=path)
            self.profile_avatar.set_avatar(name, path)
            self.sidebar_avatar.set_avatar(name, path)
            QMessageBox.information(self, "Updated", "Profile photo updated!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not update photo: {e}")

    def _profile_remove_photo(self):
        if not self.current_user:
            return
        reply = QMessageBox.question(
            self, "Remove Photo",
            "Remove your profile photo? Your avatar will revert to initials.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        role = self.current_user.get('role', '')
        name = self.current_user.get('full_name', '?')
        try:
            prof_mod = database.ProfileModule()
            if role == 'Renter':
                renter_id = self.current_user.get('renter_id')
                prof_mod.update_renter_profile(renter_id, profile_pic_path='')
            else:
                admin_id = self.current_user.get('admin_id')
                prof_mod.update_admin_profile(admin_id, profile_pic_path='')
            self.profile_avatar.set_avatar(name, None)
            self.sidebar_avatar.set_avatar(name, None)
            QMessageBox.information(self, "Removed", "Profile photo removed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not remove photo: {e}")

    def _profile_save_info(self):
        if not self.current_user:
            return
        full_name = self.prof_fullname.text().strip()
        email     = self.prof_email.text().strip()
        contact   = self.prof_contact.text().strip()
        if not full_name:
            QMessageBox.warning(self, "Required", "Full name cannot be empty.")
            return
        role = self.current_user.get('role', '')
        try:
            prof_mod = database.ProfileModule()
            if role == 'Renter':
                renter_id = self.current_user.get('renter_id')
                prof_mod.update_renter_profile(renter_id, email=email, contact_number=contact)
            else:
                admin_id = self.current_user.get('admin_id')
                prof_mod.update_admin_profile(admin_id, full_name=full_name, email=email, contact_number=contact)
                self.current_user['full_name'] = full_name
                self.sidebar_user_lbl.setText(full_name[:22])
                self.sidebar_avatar.set_avatar(full_name)
                self.welcome_label.setText(
                    f'Hello, <span style="color:{T("accent")};">{full_name}</span>! '
                    f'<span style="color:{T("text_muted")}; font-size:14px;">({role})</span>'
                )
                self.profile_name_lbl.setText(full_name)
            QMessageBox.information(self, "Saved", "Profile information updated!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save: {e}")

    def _profile_save_password(self):
        if not self.current_user:
            return
        old_pw  = self.prof_old_pw.text()
        new_pw  = self.prof_new_pw.text()
        new_pw2 = self.prof_new_pw2.text()
        if not old_pw or not new_pw:
            QMessageBox.warning(self, "Required", "Please fill in all password fields.")
            return
        if new_pw != new_pw2:
            QMessageBox.warning(self, "Mismatch", "New passwords do not match.")
            return
        if len(new_pw) < 6:
            QMessageBox.warning(self, "Too Short", "New password must be at least 6 characters.")
            return
        role = self.current_user.get('role', '')
        try:
            prof_mod = database.ProfileModule()
            if role == 'Renter':
                result = prof_mod.change_renter_password(self.current_user.get('renter_id'), old_pw, new_pw)
            else:
                result = prof_mod.change_admin_password(self.current_user.get('admin_id'), old_pw, new_pw)
            if result == 'wrong_password':
                QMessageBox.warning(self, "Wrong Password", "Current password is incorrect.")
            elif result:
                self.prof_old_pw.clear()
                self.prof_new_pw.clear()
                self.prof_new_pw2.clear()
                QMessageBox.information(self, "Updated", "Password changed successfully!")
            else:
                QMessageBox.critical(self, "Error", "Could not update password.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {e}")

    # ══════════════════════════════════════════
    #  AUTO-SYNC (Admin dashboard ↔ live DB)
    # ══════════════════════════════════════════
    def _run_auto_overdue(self):
        """Automated Status Engine: flip Pending payments past the 5th to Overdue."""
        try:
            updated = self.payment_db.auto_mark_overdue()
            if updated:
                print(f"[AutoOverdue] Marked {updated} payment(s) Overdue.")
        except Exception as e:
            print(f"[AutoOverdue] {e}")
    def _auto_sync_tick(self):
        """Refresh the currently-visible page so renter activity (new
        payments, maintenance, etc.) shows up without manual reload."""
        try:
            idx = self.pages_content.currentIndex()
            if idx == 0:
                self.refresh_home_stats()
            elif idx == 7:
                self.load_payments()
            elif idx == 11:
                self.load_logs()
            elif idx == 15:
                self.load_utility_bills()
        except Exception:
            pass

    # ══════════════════════════════════════════
    #  STAFF ALLOWANCE PAGE (Admin only)
    # ══════════════════════════════════════════
    def _build_staff_allowance_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        layout.addWidget(page_header(
            "Staff Monthly Allowance",
            "  Pay Allowance",
            self.open_pay_allowance_dialog,
            btn_icon="fa5s.hand-holding-usd",
        ))

        # Summary
        sum_row = QHBoxLayout()
        sum_row.setSpacing(12)
        self.allow_stat_total = StatCard(
            "Total Disbursed (All-Time)", "₱0", T("green"),
            "fa5s.money-bill-wave"
        )
        self.allow_stat_month = StatCard(
            "This Month", "₱0", T("accent"), "fa5s.calendar-check"
        )
        self.allow_stat_count = StatCard(
            "Payouts Recorded", "0", T("blue"), "fa5s.list-ol"
        )
        for c in [self.allow_stat_total, self.allow_stat_month, self.allow_stat_count]:
            c.setFixedHeight(100)
            sum_row.addWidget(c)
        layout.addLayout(sum_row)

        self.allowance_table = self._make_table(
            ["ID", "Staff", "Role", "Period", "Basic", "Allowance",
             "Deductions", "Net Pay", "Pay Date", "Method"]
        )
        layout.addWidget(self.allowance_table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        del_btn = make_btn("  Delete Selected", T("red"), "white",
                           icon="fa5s.trash-alt", icon_color="white")
        del_btn.clicked.connect(self.delete_allowance_row)
        btn_row.addWidget(del_btn)
        layout.addLayout(btn_row)
        return page

    def load_staff_allowance(self):
        try:
            records = self.payroll_db.get_all_payroll() or []
        except Exception:
            records = []
        self.allowance_table.setRowCount(0)
        total_all = 0.0
        total_month = 0.0
        cur_period = QDate.currentDate().toString("MMMM yyyy")
        for i, r in enumerate(records):
            self._set_table_row(self.allowance_table, i, [
                r.get('payroll_id', ''),
                r.get('full_name', '-'),
                r.get('role', '-'),
                r.get('period_month', '-'),
                f"₱{float(r.get('basic_salary',0)):,.2f}",
                f"₱{float(r.get('allowances',0)):,.2f}",
                f"₱{float(r.get('deductions',0)):,.2f}",
                f"₱{float(r.get('net_pay',0)):,.2f}",
                str(r.get('payment_date') or '-'),
                r.get('payment_method', 'Cash'),
            ])
            total_all += float(r.get('net_pay', 0) or 0)
            if r.get('period_month') == cur_period:
                total_month += float(r.get('net_pay', 0) or 0)
        self.allow_stat_total.set_value(f"₱{total_all:,.0f}")
        self.allow_stat_month.set_value(f"₱{total_month:,.0f}")
        self.allow_stat_count.set_value(len(records))

    def open_pay_allowance_dialog(self):
        # Pick a staff member, period, amount.
        staff_list = [a for a in (self.admin_db.get_all_admins() or [])
                      if a.get('role') in ('Staff', 'Maintenance', 'Security', 'Admin')]
        if not staff_list:
            QMessageBox.warning(self, "No Staff", "No staff accounts found.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Pay Staff Allowance")
        dlg.setFixedWidth(420)
        dlg.setStyleSheet(dialog_style())
        form = QFormLayout(dlg)
        form.setContentsMargins(24, 24, 24, 24)
        form.setSpacing(12)

        staff_cb = QComboBox()
        staff_cb.setStyleSheet(input_style())
        for s in staff_list:
            staff_cb.addItem(
                f"{s.get('full_name','-')}  ({s.get('role','-')})",
                s.get('admin_id'),
            )

        period_edit = QLineEdit(QDate.currentDate().toString("MMMM yyyy"))
        period_edit.setStyleSheet(input_style())

        amount_edit = QLineEdit("3000")
        amount_edit.setPlaceholderText("e.g. 3000")
        amount_edit.setStyleSheet(input_style())

        method_cb = QComboBox()
        method_cb.addItems(["Cash", "GCash", "Bank Transfer", "Other"])
        method_cb.setStyleSheet(input_style())

        date_edit = QDateEdit(QDate.currentDate())
        date_edit.setCalendarPopup(True)
        date_edit.setStyleSheet(input_style())

        notes_edit = QLineEdit("Monthly staff allowance")
        notes_edit.setStyleSheet(input_style())

        form.addRow("Staff:", staff_cb)
        form.addRow("Period:", period_edit)
        form.addRow("Amount (₱):", amount_edit)
        form.addRow("Method:", method_cb)
        form.addRow("Pay Date:", date_edit)
        form.addRow("Notes:", notes_edit)

        btn_row = QHBoxLayout()
        cancel = make_btn("Cancel", T("surface2"), T("text"))
        ok_btn = make_btn("  Pay", T("green"), "white",
                          icon="fa5s.check", icon_color="white")
        cancel.clicked.connect(dlg.reject)
        ok_btn.clicked.connect(dlg.accept)
        btn_row.addStretch()
        btn_row.addWidget(cancel)
        btn_row.addWidget(ok_btn)
        form.addRow(btn_row)

        if not dlg.exec():
            return

        try:
            amt = float(amount_edit.text().strip() or 0)
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Amount must be numeric.")
            return
        if amt <= 0:
            QMessageBox.warning(self, "Invalid", "Amount must be greater than 0.")
            return

        actor_id = self.current_user.get('admin_id') if self.current_user else None
        ok = self.payroll_db.pay_monthly_allowance(
            admin_id=staff_cb.currentData(),
            period_month=period_edit.text().strip(),
            allowance_amount=amt,
            payment_date=date_edit.date().toString("yyyy-MM-dd"),
            payment_method=method_cb.currentText(),
            notes=notes_edit.text().strip(),
            actor_admin_id=actor_id,
        )
        if ok:
            QMessageBox.information(self, "Success", "Allowance recorded.")
            self.load_staff_allowance()
        else:
            QMessageBox.critical(self, "Error", "Failed to record allowance.")

    def delete_allowance_row(self):
        row = self.allowance_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Select a row first.")
            return
        try:
            payroll_id = int(self.allowance_table.item(row, 0).text())
        except Exception:
            return
        if QMessageBox.question(self, "Confirm", "Delete this payroll record?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        if self.payroll_db.delete_payroll(payroll_id):
            self.load_staff_allowance()

    # ══════════════════════════════════════════
    #  UTILITY BILLS PAGE  (Admin only)
    # ══════════════════════════════════════════
    def _build_utility_bills_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        # Header w/ generate + mark paid buttons
        hdr = QHBoxLayout()
        title = QLabel("Utility Bills  (₱1,800/renter fixed rate · Due 5th of month)")
        title.setStyleSheet(f"color: {T('text')}; font-size: 22px; font-weight: bold;")
        self.util_gen_btn = make_btn("  Generate Monthly Bills", T("accent"), T("bg"),
                           icon="fa5s.bolt", icon_color=T("bg"))
        self.util_gen_btn.clicked.connect(self.generate_monthly_utility_bills)
        self.util_mark_btn = make_btn("  Mark Paid", T("green"), "white",
                            icon="fa5s.check", icon_color="white")
        self.util_mark_btn.clicked.connect(self.utility_mark_paid)
        self.util_delete_btn = make_btn("  Delete", T("red"), "white",
                              icon="fa5s.trash-alt", icon_color="white")
        self.util_delete_btn.clicked.connect(self.utility_delete_bill)
        self.util_renter_pay_btn = make_btn("  I Already Paid", T("green"), "white",
                                   icon="fa5s.check-circle", icon_color="white")
        self.util_renter_pay_btn.clicked.connect(self.utility_renter_mark_paid)
        self.util_renter_pay_btn.setVisible(False)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self.util_renter_pay_btn)
        hdr.addWidget(self.util_delete_btn)
        hdr.addWidget(self.util_mark_btn)
        hdr.addWidget(self.util_gen_btn)
        layout.addLayout(hdr)

        # Info strip
        info_strip = QLabel(
            "Bills are generated as a snapshot of room occupancy at the time of generation. "
            "\"# Renters (billed)\" = headcount when the bill was created. "
            "\"Current Tenants\" = who is in the room now (may differ if renters checked in/out after billing). "
            "The 5th of each billing month is the due date."
        )
        info_strip.setStyleSheet(f"color: {T('text_muted')}; font-size: 12px;")
        info_strip.setWordWrap(True)
        layout.addWidget(info_strip)

        # ── FILTERS ROW ─────────────────────
        filt_row = QHBoxLayout()
        self.util_filter_renter = QLineEdit()
        self.util_filter_renter.setPlaceholderText("⌕  Filter by renter name...")
        self.util_filter_renter.setStyleSheet(input_style() + "min-height: 36px;")
        self.util_filter_renter.textChanged.connect(self.load_utility_bills)

        self.util_filter_month = QComboBox()
        self.util_filter_month.addItem("All Months")
        self.util_filter_month.setStyleSheet(input_style() + "min-width: 160px;")
        self.util_filter_month.currentTextChanged.connect(self.load_utility_bills)

        self.util_filter_status = QComboBox()
        self.util_filter_status.addItems(["All", "Unpaid", "Paid"])
        self.util_filter_status.setStyleSheet(input_style() + "min-width: 110px;")
        self.util_filter_status.currentTextChanged.connect(self.load_utility_bills)

        filt_row.addWidget(QLabel("Renter:"))
        filt_row.addWidget(self.util_filter_renter, 2)
        filt_row.addSpacing(12)
        filt_row.addWidget(QLabel("Month:"))
        filt_row.addWidget(self.util_filter_month, 1)
        filt_row.addSpacing(12)
        filt_row.addWidget(QLabel("Status:"))
        filt_row.addWidget(self.util_filter_status, 1)
        layout.addLayout(filt_row)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.util_stat_unpaid = StatCard("Unpaid Bills",    "0",  T("red"),    "fa5s.exclamation-triangle")
        self.util_stat_paid   = StatCard("Paid Bills",      "0",  T("green"),  "fa5s.check-circle")
        self.util_stat_collect= StatCard("Collected (₱)",  "₱0", T("blue"),   "fa5s.coins")
        self.util_stat_owed   = StatCard("Outstanding (₱)","₱0", T("orange"), "fa5s.hourglass-half")
        self.util_stat_rooms  = StatCard("Rooms Billed",   "0",  T("teal"),   "fa5s.building")
        for c in [self.util_stat_unpaid, self.util_stat_paid,
                  self.util_stat_collect, self.util_stat_owed, self.util_stat_rooms]:
            c.setFixedHeight(100)
            stats_row.addWidget(c)
        layout.addLayout(stats_row)

        # ── Structured columnar table with clear sections ────────────────
        # Columns: Bill ID | Room | Floor | Renters (count) | Renter Names |
        #          Type | Total | Per Renter | Billing Month | Due Date |
        #          Payment Date | Status | Reference
        self.utility_table = self._make_table([
            "Bill ID", "Room No.", "Floor", "# Renters (billed)", "Current Tenants",
            "Bill Type", "Total (₱)", "Per Renter (₱)",
            "Billing Month", "Due Date", "Paid Date", "Status", "Ref #"
        ])
        self.utility_table.setAlternatingRowColors(True)
        # Wider columns for name and status
        header_obj = self.utility_table.horizontalHeader()
        header_obj.setSectionResizeMode(4, QHeaderView.Stretch)   # Tenant Names stretches
        header_obj.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        layout.addWidget(self.utility_table)

        self._utility_bills_scroll = scroll  # keep reference so Qt doesn't GC the scroll area
        scroll.setWidget(page)
        return scroll

    def load_utility_bills(self):
        # Renter view: see ONLY their own bills, hide admin actions/filters
        is_renter = (self.current_user or {}).get('role') == 'Renter'
        if is_renter:
            renter_id = self.current_user.get('renter_id')
            try:
                bills = self.utility_db.get_bills_for_renter(renter_id) or []
                for b in bills:
                    b.setdefault('renter_count', 1)
                    b.setdefault('renter_names', self.current_user.get('full_name', ''))
            except Exception:
                bills = []
            for w in (getattr(self, 'util_gen_btn', None),
                      getattr(self, 'util_mark_btn', None),
                      getattr(self, 'util_delete_btn', None),
                      getattr(self, 'util_filter_renter', None)):
                if w:
                    w.setVisible(False)
            if hasattr(self, 'util_renter_pay_btn'):
                self.util_renter_pay_btn.setVisible(True)
        else:
            try:
                # Fetch all bills with floor_level joined
                bills = self.utility_db.get_all_bills() or []
                # Enrich with floor_level if not present
                for b in bills:
                    if 'floor_level' not in b:
                        b['floor_level'] = '-'
            except Exception:
                bills = []
            for w in (getattr(self, 'util_gen_btn', None),
                      getattr(self, 'util_mark_btn', None),
                      getattr(self, 'util_delete_btn', None),
                      getattr(self, 'util_filter_renter', None)):
                if w:
                    w.setVisible(True)
            if hasattr(self, 'util_renter_pay_btn'):
                self.util_renter_pay_btn.setVisible(False)

        # Refresh the months filter combo (preserve selection)
        try:
            current_month = self.util_filter_month.currentText()
            months = self.utility_db.get_distinct_billing_months() or []
            self.util_filter_month.blockSignals(True)
            self.util_filter_month.clear()
            self.util_filter_month.addItem("All Months")
            for m in months:
                self.util_filter_month.addItem(m)
            idx = self.util_filter_month.findText(current_month)
            self.util_filter_month.setCurrentIndex(idx if idx >= 0 else 0)
            self.util_filter_month.blockSignals(False)
        except Exception:
            pass

        # Apply filters
        kw = (self.util_filter_renter.text() if hasattr(self, 'util_filter_renter') else "").strip().lower()
        sel_month = self.util_filter_month.currentText() if hasattr(self, 'util_filter_month') else "All Months"
        status_f  = self.util_filter_status.currentText() if hasattr(self, 'util_filter_status') else "All"
        if kw:
            bills = [b for b in bills if kw in (b.get('renter_names') or '').lower()]
        if sel_month and sel_month != "All Months":
            bills = [b for b in bills if str(b.get('billing_month', '')) == sel_month]
        if status_f != "All":
            bills = [b for b in bills if (b.get('status', 'Unpaid')) == status_f]

        self.utility_table.setRowCount(0)
        t = Theme.get()
        unpaid = 0; paid = 0; collected = 0.0; owed = 0.0; unique_rooms = set()

        for i, b in enumerate(bills):
            status = b.get('status', 'Unpaid')
            renter_count = int(b.get('renter_count', 0) or 0)  # current live occupancy
            room_id = b.get('room_id') or b.get('room_number', '')
            unique_rooms.add(str(b.get('room_number', room_id)))

            floor = b.get('floor_level') or '-'
            paid_date = b.get('payment_date') or '-'

            # 13 columns: Bill ID, Room No., Floor, # Renters (billed), Current Tenants,
            # Bill Type, Total, Per Renter, Billing Month, Due Date, Paid Date, Status, Ref #
            self._set_table_row(self.utility_table, i, [
                b.get('bill_id', ''),
                b.get('room_number', '-'),
                floor,
                renter_count,
                (b.get('renter_names') or '-')[:80],
                b.get('bill_type', '-'),
                f"₱{float(b.get('amount_per_person', 0) or 0):,.2f}",
                f"₱{float(b.get('amount_per_person', 0) or 0):,.2f}",
                b.get('billing_month', '-'),
                str(b.get('due_date') or '-'),
                str(paid_date)[:10] if paid_date and paid_date != '-' else '-',
                status,
                b.get('reference_no') or '-',
            ])

            # Colour status column
            status_col = t['green'] if status == 'Paid' else t['red']
            self.utility_table.item(i, 11).setForeground(QColor(status_col))

            # Colour due date red if overdue
            due = b.get('due_date')
            if due and status != 'Paid':
                try:
                    from datetime import date as _d
                    due_d = _d.fromisoformat(str(due)[:10])
                    if _d.today() > due_d:
                        self.utility_table.item(i, 9).setForeground(QColor(t['red']))
                except Exception:
                    pass

            # Colour renter count cell red if unpaid
            if status != 'Paid' and renter_count:
                self.utility_table.item(i, 3).setForeground(QColor(t['red']))

            amt = float(b.get('amount_per_person', 0) or 0) if is_renter else float(b.get('amount', 0) or 0)
            if status == 'Paid':
                paid += 1; collected += amt
            else:
                unpaid += 1; owed += amt

        self.util_stat_unpaid.set_value(unpaid)
        self.util_stat_paid.set_value(paid)
        self.util_stat_collect.set_value(f"₱{collected:,.0f}")
        self.util_stat_owed.set_value(f"₱{owed:,.0f}")
        if hasattr(self, 'util_stat_rooms'):
            self.util_stat_rooms.set_value(len(unique_rooms))

    def generate_monthly_utility_bills(self):
        t = Theme.get()

        dlg = QDialog(self)
        dlg.setWindowTitle("Generate Utility Bills")
        dlg.setMinimumWidth(420)
        dlg.setStyleSheet(dialog_style())
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        # Header
        hdr = QLabel("⚡ Generate Monthly Utility Bills")
        hdr.setStyleSheet(f"color: {t['text']}; font-size: 16px; font-weight: bold;")
        lay.addWidget(hdr)

        # BATELEC — combined Electricity + Water actual bill
        EXPECTED_PER_RENTER = 700.00
        ACTIVE_RENTERS      = self.utility_db.get_active_renter_count()   # live from DB
        EXPECTED_TOTAL      = EXPECTED_PER_RENTER * ACTIVE_RENTERS

        note = QLabel(
            f"Enter the actual BATELEC bill (Electricity + Water combined). "
            f"Expected: ₱{EXPECTED_PER_RENTER:,.0f}/renter × {ACTIVE_RENTERS} active renters "
            f"= ₱{EXPECTED_TOTAL:,.0f}/month. "
            f"If actual is higher, the overage is split equally among all active renters "
            f"and added to their existing balance."
        )
        note.setStyleSheet(f"color: {t['text_muted']}; font-size: 12px;")
        note.setWordWrap(True)
        lay.addWidget(note)

        # Billing month
        form = QFormLayout()
        form.setSpacing(10)

        month_input = QLineEdit(QDate.currentDate().toString("MMMM yyyy"))
        month_input.setStyleSheet(input_style())
        form.addRow(QLabel("📅  Billing Month:", styleSheet=f"color:{t['text']}; font-size:13px;"), month_input)

        batelec_input = QLineEdit("0.00")
        batelec_input.setStyleSheet(input_style())
        batelec_input.setPlaceholderText(f"Actual BATELEC bill (₱)  — expected ₱{EXPECTED_TOTAL:,.0f}")
        form.addRow(QLabel("💡💧 BATELEC (₱):", styleSheet=f"color:{t['text']}; font-size:13px;"), batelec_input)

        # WiFi — FIXED, always ₱2,000 ÷ active renters (Converge)
        WIFI_TOTAL      = 2000.00
        WIFI_PER_RENTER = round(WIFI_TOTAL / ACTIVE_RENTERS, 2) if ACTIVE_RENTERS else 0.0
        wifi_lbl = QLabel(f"₱{WIFI_TOTAL:,.2f} fixed  (Converge ÷ 36 = ₱{WIFI_PER_RENTER:,.2f}/renter)")
        wifi_lbl.setStyleSheet(f"color: {t['green']}; font-size: 13px; font-weight: bold; background: transparent;")
        form.addRow(QLabel("📶  WiFi (Fixed):", styleSheet=f"color:{t['text']}; font-size:13px;"), wifi_lbl)

        lay.addLayout(form)

        # Info label
        self._util_info_lbl = QLabel("")
        self._util_info_lbl.setStyleSheet(f"color: {t['text_muted']}; font-size: 11px;")
        self._util_info_lbl.setWordWrap(True)
        lay.addWidget(self._util_info_lbl)

        # Update info when amounts change
        FIXED_BEDS = 36
        def update_info():
            try:
                actual   = float(batelec_input.text() or 0)
                per_r    = actual / ACTIVE_RENTERS if ACTIVE_RENTERS else 0
                overage  = max(0.0, actual - EXPECTED_TOTAL)
                over_per = overage / ACTIVE_RENTERS if ACTIVE_RENTERS else 0
                status_txt = (
                    f"🔴 Over by ₱{overage:,.2f}  →  +₱{over_per:,.2f}/renter added to balance"
                    if overage > 0
                    else f"🟢 Within expected  (surplus ₱{EXPECTED_TOTAL - actual:,.2f})"
                )
                self._util_info_lbl.setText(
                    f"👥 Active renters: {ACTIVE_RENTERS}  |  "
                    f"Expected: ₱{EXPECTED_TOTAL:,.0f}  |  "
                    f"Actual: ₱{actual:,.2f}  |  ₱{per_r:,.2f}/renter\n"
                    f"{status_txt}\n"
                    f"📶 WiFi: ₱{WIFI_PER_RENTER:,.2f}/renter (fixed)"
                )
            except Exception:
                pass

        batelec_input.textChanged.connect(update_info)
        update_info()

        # Buttons
        btn_row = QHBoxLayout()
        btn_gen = make_btn("⚡ Generate", T("accent"), "black")
        btn_cancel = make_btn("Cancel", T("red"), "white")
        btn_row.addWidget(btn_gen)
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

        btn_cancel.clicked.connect(dlg.reject)

        def do_generate():
            period = month_input.text().strip()
            if not period:
                QMessageBox.warning(dlg, "Missing", "Please enter a billing month.")
                return
            try:
                actual_batelec = float(batelec_input.text() or 0)
            except ValueError:
                QMessageBox.warning(dlg, "Invalid", "Please enter a valid BATELEC amount.")
                return

            from database import DatabaseEngine as _DBE
            key = _DBE._month_key(period)
            try:
                yr, mo = key.split("-")
                due = f"{int(yr):04d}-{int(mo):02d}-05"
            except Exception:
                from datetime import date as _d_fb
                _today = _d_fb.today()
                due = f"{_today.year:04d}-{_today.month:02d}-05"

            actor_id  = self.current_user.get('admin_id') if self.current_user else None
            results   = []

            # ── 1. Generate BATELEC utility bill (Electricity bill_type) ──
            if actual_batelec > 0:
                per_renter_batelec = actual_batelec / ACTIVE_RENTERS
                try:
                    n = self.utility_db.generate_monthly_bills(
                        billing_month=period,
                        due_date=due,
                        amount_per_renter=per_renter_batelec,
                        bill_type='Electricity',
                        actor_admin_id=actor_id,
                    )
                    results.append(f"✅ BATELEC: {n} bill(s) @ ₱{per_renter_batelec:,.2f}/renter")
                except Exception as e:
                    results.append(f"❌ BATELEC: {e}")

            # ── 2. WiFi — always ₱2,000 fixed ──
            try:
                n = self.utility_db.generate_monthly_bills(
                    billing_month=period,
                    due_date=due,
                    amount_per_renter=WIFI_PER_RENTER,
                    bill_type='Internet',
                    actor_admin_id=actor_id,
                )
                results.append(f"✅ WiFi: {n} bill(s) @ ₱{WIFI_PER_RENTER:,.2f}/renter (fixed)")
            except Exception as e:
                results.append(f"❌ WiFi: {e}")

            # ── 3. Overage check — if actual > expected, add to balance ──
            overage = actual_batelec - EXPECTED_TOTAL
            if overage > 0:
                over_per_renter = round(overage / ACTIVE_RENTERS, 2)
                try:
                    charged = self.payment_db.apply_overage_charge(
                        billing_month=period,
                        overage_per_renter=over_per_renter,
                        actor_admin_id=actor_id,
                    )
                    results.append(
                        f"🔴 Overage ₱{overage:,.2f} detected  →  "
                        f"+₱{over_per_renter:,.2f} added to {charged} renter(s)' balance"
                    )
                except Exception as e:
                    results.append(f"❌ Overage charge: {e}")
            else:
                surplus = EXPECTED_TOTAL - actual_batelec
                if surplus > 0:
                    results.append(f"🟢 Within budget — surplus ₱{surplus:,.2f} (no overage charge)")

            if results:
                QMessageBox.information(dlg, "Done", "\n".join(results))
                dlg.accept()
                self.load_utility_bills()
            else:
                QMessageBox.warning(dlg, "Nothing Generated", "Enter at least one amount greater than 0.")

        btn_gen.clicked.connect(do_generate)
        dlg.exec()

    def utility_renter_mark_paid(self):
        """Renter clicks 'I Already Paid' — asks for reference number then marks bill as paid."""
        row = self.utility_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a bill first.")
            return
        try:
            bill_id = int(self.utility_table.item(row, 0).text())
            status  = self.utility_table.item(row, 11).text()
        except Exception:
            return
        if status == 'Paid':
            QMessageBox.information(self, "Already Paid", "This bill has already been marked as paid.")
            return
        ref, ok = QInputDialog.getText(
            self, "Reference Number",
            "Enter your GCash / bank / receipt reference number:"
        )
        if not ok:
            return
        today = QDate.currentDate().toString("yyyy-MM-dd")
        if self.utility_db.mark_paid(bill_id, today, ref.strip() or None):
            QMessageBox.information(self, "Payment Recorded", "Your payment has been recorded. ✅")
            self.load_utility_bills()
        else:
            QMessageBox.critical(self, "Error", "Could not record payment. Please try again.")

    def utility_mark_paid(self):
        row = self.utility_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Select a bill first.")
            return
        try:
            bill_id = int(self.utility_table.item(row, 0).text())
        except Exception:
            return
        ref, ok = QInputDialog.getText(
            self, "Reference Number",
            "Reference / receipt number (optional):"
        )
        if not ok:
            return
        today = QDate.currentDate().toString("yyyy-MM-dd")
        if self.utility_db.mark_paid(bill_id, today, ref.strip() or None):
            self.load_utility_bills()

    def utility_delete_bill(self):
        row = self.utility_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Select a bill first.")
            return
        try:
            bill_id = int(self.utility_table.item(row, 0).text())
        except Exception:
            return
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Permanently delete utility bill #{bill_id}?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.utility_db.delete_bill(bill_id):
                self.load_utility_bills()
            else:
                QMessageBox.critical(self, "Error", "Could not delete bill.")

    # ══════════════════════════════════════════
    #  RENTER TRANSPARENCY PANEL
    # ══════════════════════════════════════════
    def _show_renter_transparency_panel(self):
        """Render 'Where your money goes' for the renter on the home page."""
        try:
            renter_id = self.current_user.get('renter_id')
            if not renter_id:
                return
            if hasattr(self, '_renter_transparency_panel') and \
               self._renter_transparency_panel:
                try:
                    self._renter_transparency_panel.setParent(None)
                    self._renter_transparency_panel.deleteLater()
                except Exception:
                    pass
            t = Theme.get()
            summary = self.utility_db.get_transparency_summary(renter_id) or {}
            breakdown = summary.get('breakdown', {}) or {}

            panel = QFrame()
            panel.setStyleSheet(
                f"background: {t['surface']}; border-radius: 14px; "
                f"border: 1px solid {t['border']};"
            )
            pl = QVBoxLayout(panel)
            pl.setContentsMargins(20, 16, 20, 16)
            pl.setSpacing(10)

            hdr = QLabel("Utility Transparency - Where Your Money Goes")
            hdr.setStyleSheet(
                f"color: {t['text']}; font-size: 15px; font-weight: bold; "
                f"background: transparent; border: none;"
            )
            pl.addWidget(hdr)

            note = QLabel(
                f"Fixed dorm rate: ₱{database.UtilityModule.UTILITY_FIXED_RATE:,.0f} "
                f"per renter / month · Total paid: "
                f"₱{summary.get('total_paid', 0):,.2f} · Outstanding: "
                f"₱{summary.get('total_due', 0):,.2f}"
            )
            note.setStyleSheet(
                f"color: {t['text_muted']}; font-size: 12px; "
                f"background: transparent; border: none;"
            )
            note.setWordWrap(True)
            pl.addWidget(note)

            grid = QGridLayout()
            grid.setSpacing(8)
            if not breakdown:
                lbl = QLabel("No utility bills issued yet for your room.")
                lbl.setStyleSheet(
                    f"color: {t['text_muted']}; background: transparent; border: none;"
                )
                grid.addWidget(lbl, 0, 0)
            else:
                colors = [t['accent'], t['blue'], t['green'], t['orange'], t['purple']]
                for i, (kind, amt) in enumerate(breakdown.items()):
                    k_lbl = QLabel(f"{kind}")
                    k_lbl.setStyleSheet(
                        f"color: {colors[i % len(colors)]}; font-size: 13px; "
                        f"font-weight: bold; background: transparent; border: none;"
                    )
                    a_lbl = QLabel(f"₱{amt:,.2f}  (your share)")
                    a_lbl.setStyleSheet(
                        f"color: {t['text']}; font-size: 13px; "
                        f"background: transparent; border: none;"
                    )
                    grid.addWidget(k_lbl, i, 0)
                    grid.addWidget(a_lbl, i, 1)
            pl.addLayout(grid)

            home_inner = self.home_page.widget()
            home_layout = home_inner.layout()
            home_layout.insertWidget(home_layout.count() - 1, panel)
            self._renter_transparency_panel = panel
        except Exception as e:
            print(f"[_show_renter_transparency_panel] {e}")

    def _build_logs_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addWidget(page_header("Activity Logs"))
        layout.addSpacing(10)
        self.logs_table = self._make_table(["Log ID", "Admin", "Action", "Details", "Timestamp"])
        layout.addWidget(self.logs_table)
        return page

    def load_logs(self):
        logs = self.admin_db.get_activity_logs()
        self.logs_table.setRowCount(0)
        for i, log in enumerate(logs):
            self._set_table_row(self.logs_table, i, [
                log['log_id'], log['admin_name'],
                log['action_type'], log['action_text'],
                str(log['log_timestamp'])
            ])


# ─────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────
class DormNormApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DormNorm")
        self.setMinimumSize(1200, 750)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.welcome   = WelcomePage(self.stack)
        self.login     = LoginPage(self.stack)
        self.dashboard = DashboardPage(self.stack)

        self.stack.addWidget(self.welcome)
        self.stack.addWidget(self.login)
        self.stack.addWidget(self.dashboard)
        self.stack.setCurrentIndex(0)

    def fade_to_page(self, index):
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(350)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)

        def change_page():
            self.stack.setCurrentIndex(index)
            self.anim2 = QPropertyAnimation(self, b"windowOpacity")
            self.anim2.setDuration(350)
            self.anim2.setStartValue(0.0)
            self.anim2.setEndValue(1.0)
            self.anim2.start()

        self.anim.finished.connect(change_page)
        self.anim.start()


if __name__ == "__main__":
    # ── Schema migration + password hashing on first run ──
    try:
        _db_engine = database.DatabaseEngine()
        _db_engine.ensure_schema()          # add 'Refunded' to payments ENUM etc.
    except Exception as _e:
        print(f"[Startup schema migration] {_e}")
    try:
        _am = database.AdminModule()
        _am.ensure_admin_columns()          # add email/contact/pic columns if missing
        _am.hash_existing_admin_passwords()
        _rm = database.RenterModule()
        _rm.hash_existing_renter_passwords()
    except Exception as _e:
        print(f"[Startup migration] {_e}")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = DormNormApp()
    window.showMaximized()
    sys.exit(app.exec())