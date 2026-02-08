#!/usr/bin/env python3
"""Generate a colored PNG image from the dashboard ASCII preview."""

from PIL import Image, ImageDraw, ImageFont
import re

# Dashboard ASCII art with color annotations
DASHBOARD = """
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  DEBUGGING YOUR RUNNING: CONVERTING DATA TO INSIGHT                                     │
├─────────────────┬─────────────────┬─────────────────────────┬───────────────┬───────────┤
│   Total Runs    │   Total Miles   │       Date Range        │ Avg Weekly Mi │ Avg Pace  │
│      339        │     1,448       │  2023-10-12 to 2026-02  │     12.3      │  5.87     │
├─────────────────┴─────────────────┴─────────────────────────┴───────────────┴───────────┤
│  ROW 1: WAS THE EASY RUN ACTUALLY TOO HARD?                                             │
├───────────────────────────┬───────────────────────────┬─────────────────────────────────┤
│   Effort vs Pace Scatter  │   HR Drift Detection      │   Relative Effort Distribution  │
│                           │                           │                                 │
│    HR ▲                   │   effort ▲    · ·         │   ▐██                           │
│       │  · ·  ·           │          │ ·  ·  · ·      │   ▐████                         │
│       │ ·  · ·· ·         │          │·  ·   ·  ·     │   ▐██████                       │
│       │· · ·· · ·         │          └──────────► t   │   ▐████████                     │
│       └──────────► pace   │                           │   ▐██████                       │
│                           │                           │   └──────────► effort           │
├───────────────────────────┴───────────────────────────┴─────────────────────────────────┤
│  ROW 2: DID THE WEATHER WRECK ME?                                                       │
├──────────────────┬──────────────────┬──────────────────┬────────────────────────────────┤
│  Temp vs Pace    │  Temp vs HR      │  Humidity vs Pace│   Weather Heatmap              │
│                  │                  │                  │   ┌─────────────────┐          │
│  pace ▲   ·      │  HR ▲      ·     │  pace ▲    ·     │   │░░▒▒▓▓██████████│ humid    │
│      │ ·  · ·    │     │   · · ·    │      │  · · ·    │   │░░▒▒▓▓████████░░│          │
│      │  · · · ·  │     │ · · · ·    │      │ · · · ·   │   │░░▒▒▓▓██████░░░░│          │
│      └────────►  │     └────────►   │      └────────►  │   │░░▒▒▓▓████░░░░░░│          │
│           temp   │          temp    │        humidity  │   └─────────────────┘ temp    │
├──────────────────┴──────────────────┴──────────────────┴────────────────────────────────┤
│  ROW 3: DID THE TRAIL JUST SUCK?                                                        │
├─────────────────────────────────────────┬───────────────────────────────────────────────┤
│   Elevation Gain vs Pace                │   Flat vs Hilly: The Hill Tax                 │
│                                         │                                               │
│   pace ▲       ·  ·                     │   ┌─────┐                                     │
│        │    ·  · ·  ·                   │   │█████│ 5.90  Flat (<50m)                   │
│        │  · · · ·  ·  ·                 │   │█████│ 5.97  Rolling                       │
│        │ · · · ·                        │   │█████│ 6.17  Hilly (>100m)                 │
│        └─────────────────► elevation    │   └─────┘                                     │
├─────────────────────────────────────────┴───────────────────────────────────────────────┤
│  ROW 4: WAS SLEEP THE PROBLEM?                                                          │
├──────────────────┬──────────────────┬──────────────────┬────────────────────────────────┤
│ Sleep vs Pace    │ HRV vs Effort    │ Readiness vs Pace│ Deep Sleep vs Pace             │
│                  │                  │                  │                                │
│ pace ▲  ·  ·     │ effort ▲   ·     │ pace ▲   ·  ·    │ pace ▲     ·  ·                │
│     │ ·  · · ·   │       │ · · ·    │     │  · · · ·   │     │   · · · ·                │
│     │· · · · ·   │       │  · · ·   │     │ · · · ·    │     │  · · · ·                 │
│     └─────────►  │       └───────►  │     └─────────►  │     └───────────►              │
│       sleep score│          HRV     │      readiness   │        deep sleep min          │
├──────────────────┴──────────────────┴──────────────────┴────────────────────────────────┤
│  ROW 5: THE BIG PICTURE                                                                 │
├─────────────────────────────────────────┬───────────────────────────────────────────────┤
│  Training Load vs Sleep (Weekly)        │   Monthly Pace Trend                          │
│                                         │                                               │
│  miles ▲          ╱╲    ╱╲   sleep     │   pace ▲                                       │
│       │    ╱╲   ╱    ╲╱   ╲            │        │ ·                                     │
│       │  ╱    ╲╱              ╲        │        │   ·  ·                                │
│       │╱                        ╲      │        │     ·  · ·  · ·                       │
│       └─────────────────────────► week │        └─────────────────► month               │
├─────────────────────────────────────────┴───────────────────────────────────────────────┤
│  Best & Worst Runs                                                                      │
│ ┌──────────┬────────────┬─────────────────────────────┬───────┬────────┬──────┬───────┐ │
│ │ category │ date       │ name                        │ pace  │ dist   │ HR   │ temp  │ │
│ ├──────────┼────────────┼─────────────────────────────┼───────┼────────┼──────┼───────┤ │
│ │ Fastest  │ 2025-05-03 │ Mindful 5k                  │ 4.53  │ 3.2    │ 172  │ 18    │ │
│ │ Fastest  │ 2025-01-01 │ Fear Less 5K                │ 5.05  │ 3.1    │ 168  │ 5     │ │
│ │ Slowest  │ 2024-07-05 │ Morning run with Becca      │ 8.53  │ 3.9    │      │ 20    │ │
│ │ Slowest  │ 2024-06-26 │ Nike Run Club: The Shifter  │ 7.93  │ 3.2    │ 141  │       │ │
│ └──────────┴────────────┴─────────────────────────────┴───────┴────────┴──────┴───────┘ │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│  ROW 6: DID I FUEL PROPERLY?                                                            │
├────────────────┬────────────────┬────────────────┬────────────────┬─────────────────────┤
│ Long Runs      │ Total Gels     │ Total Carbs    │ Avg Carb       │ Carb Cal vs Burned  │
│   (9+ mi)      │  Consumed      │  Consumed      │ Replacement    │                     │
│     30         │    119         │   3,570g       │   23.9%        │  ▐██ carbs          │
│                │                │                │                │  ▐████████ burned   │
├────────────────┴────────────────┴────────────────┴────────────────┤                     │
│  Long Run Fueling Log                                             │  9mi  13mi  26mi    │
│ ┌────────────┬─────────────────────────┬───────┬──────┬─────────┐ ├─────────────────────┤
│ │ date       │ name                    │ miles │ gels │ carbs   │ │ Gels vs Pace        │
│ ├────────────┼─────────────────────────┼───────┼──────┼─────────┤ │                     │
│ │ 2025-11-02 │ NYC Marathon            │ 26.3  │ 8    │ 240g    │ │ pace ▲   ·          │
│ │ 2025-10-04 │ Morning Run             │ 21.0  │ 7    │ 210g    │ │      │ · · ·        │
│ │ 2026-01-18 │ Morning Run             │ 19.3  │ 6    │ 180g    │ │      │  · ·  ·      │
│ │ 2025-04-27 │ Brooklyn half!          │ 13.3  │ 4    │ 120g    │ │      └──────► gels  │
│ └────────────┴─────────────────────────┴───────┴──────┴─────────┘ └─────────────────────┤
├─────────────────────────────────────────────────────────────────────────────────────────┤
│  ROW 7: PUTTING IT ALL TOGETHER                                                         │
├───────────────────────────┬───────────────────────────┬─────────────────────────────────┤
│  Optimal Conditions       │  Pace by Day of Week      │  Pace by Time of Day            │
│  (Temp × Sleep Heatmap)   │                           │                                 │
│  ┌─────────────────┐      │  ▐███ 5.82  Mon           │  ▐████ 6.12  Early (0-6)        │
│  │░░▒▒▓▓██████████│ sleep│  ▐███ 5.74  Tue           │  ▐███  5.89  Morning (6-12)     │
│  │░░▒▒▓▓████████░░│      │  ▐███ 5.93  Wed           │  ▐███  5.91  Afternoon (12-18)  │
│  │░░▒▒▓▓██████░░░░│      │  ▐███ 5.77  Thu           │  ▐██   5.77  Evening (18-24)    │
│  │░░▒▒▓▓████░░░░░░│      │  ▐███ 5.88  Fri           │                                 │
│  └─────────────────┘ temp │  ▐███ 5.86  Sat           │                                 │
│   green=fast, red=slow    │  ▐███ 5.93  Sun           │                                 │
├───────────────────────────┴───────────────────────────┴─────────────────────────────────┤
│  ROW 8: ADVANCED METRICS (GARMIN)                                                       │
├──────────────────┬──────────────────┬──────────────────┬────────────────────────────────┤
│ Real 80/20       │ Training Effect  │  VO2max Trend    │ Running Dynamics               │
│   (Pie Chart)    │   Trend          │                  │                                │
│   ┌────────┐     │  TE ▲     ·      │  VO2 ▲           │  Ground Contact │ 264 ms       │
│   │ ██░░░░ │     │     │  · · ·     │      │    ╱──╲   │  Stride Length  │ 92 cm        │
│   │ ██░░░░ │     │     │ · ·  ·  ·  │      │ ╱─╱    ╲  │  Vertical Osc   │ 7.6 cm       │
│   │ ██████ │     │     └────────►   │      └───────►   │  Avg Power      │ 378 W        │
│   └────────┘     │        date      │       date       │                                │
│ ██ Easy (10%)    │  · Aerobic       │                  │                                │
│ ░░ Hard (90%)    │  · Anaerobic     │                  │                                │
├──────────────────┴──────────────────┴──────────────────┴────────────────────────────────┤
│  Body Battery          │  Weekly Training Intensity    │  Stats                         │
│  Drain by Distance     │  (Stacked Bar)                │  ┌──────────────────────────┐  │
│                        │                               │  │ Runs w/ Garmin │   200   │  │
│  drain ▲   ·  ·        │  hrs ▲ ████████  ░░░░        │  │ Current VO2max │   49    │  │
│       │ ·  ·  · ·      │      │ ████████  ░░░░        │  │ Avg Load       │   156   │  │
│       │  · ·  ·  ·     │      │ ████████  ░░░░        │  │ Easy Zone %    │  9.9%   │  │
│       └──────────► km  │      └──────────► week       │  └──────────────────────────┘  │
│                        │  ████ Easy (Z1-2) ░░ Hard    │   (Target: 80% easy)           │
└────────────────────────┴───────────────────────────────┴────────────────────────────────┘
"""

# Color scheme (Grafana-inspired dark theme)
COLORS = {
    'background': (30, 30, 30),
    'border': (60, 60, 60),
    'title': (255, 152, 0),      # Orange for titles
    'row_header': (33, 150, 243), # Blue for row headers
    'text': (200, 200, 200),     # Light gray for text
    'value': (76, 175, 80),      # Green for values
    'chart_dot': (255, 87, 34),  # Orange-red for chart dots
    'bar': (156, 39, 176),       # Purple for bars
    'heatmap_cool': (76, 175, 80),   # Green
    'heatmap_warm': (255, 152, 0),   # Orange
    'heatmap_hot': (244, 67, 54),    # Red
    'easy': (76, 175, 80),       # Green for easy
    'hard': (244, 67, 54),       # Red for hard
}

def get_char_color(char, line, col, full_text):
    """Determine color for a character based on context."""
    # Row headers (ROW X:)
    if 'ROW' in line and ':' in line:
        return COLORS['row_header']

    # Main title
    if 'DEBUGGING YOUR RUNNING' in line:
        return COLORS['title']

    # Stat values (numbers)
    if char.isdigit() or char in '.,:%':
        # Check if part of a number
        return COLORS['value']

    # Chart elements
    if char in '·•':
        return COLORS['chart_dot']

    # Bar chart blocks
    if char in '▐█':
        return COLORS['bar']

    # Heatmap gradients
    if char == '░':
        return COLORS['heatmap_cool']
    if char == '▒':
        return COLORS['heatmap_warm']
    if char == '▓':
        return COLORS['heatmap_hot']

    # Box drawing characters
    if char in '┌┐└┘├┤┬┴┼─│╱╲▲►':
        return COLORS['border']

    # Easy/Hard labels
    if 'Easy' in line and col > line.find('Easy') and col < line.find('Easy') + 10:
        return COLORS['easy']
    if 'Hard' in line and col > line.find('Hard') and col < line.find('Hard') + 10:
        return COLORS['hard']

    return COLORS['text']


def render_dashboard():
    """Render the dashboard to a PNG image."""
    lines = DASHBOARD.strip().split('\n')

    # Calculate dimensions
    char_width = 10
    char_height = 18
    padding = 40

    max_line_length = max(len(line) for line in lines)
    width = max_line_length * char_width + padding * 2
    height = len(lines) * char_height + padding * 2

    # Create image
    img = Image.new('RGB', (width, height), COLORS['background'])
    draw = ImageDraw.Draw(img)

    # Try to use a monospace font
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 14)
        except:
            try:
                font = ImageFont.truetype("DejaVuSansMono.ttf", 14)
            except:
                font = ImageFont.load_default()

    # Render each character with appropriate color
    y = padding
    for line in lines:
        x = padding
        for col, char in enumerate(line):
            color = get_char_color(char, line, col, DASHBOARD)
            draw.text((x, y), char, font=font, fill=color)
            x += char_width
        y += char_height

    # Add a subtle gradient overlay at the top for title emphasis
    for i in range(60):
        alpha = int(255 * (1 - i / 60) * 0.3)
        draw.line([(0, padding + i), (width, padding + i)],
                  fill=(COLORS['title'][0], COLORS['title'][1], COLORS['title'][2], alpha))

    return img


def main():
    print("Generating dashboard preview PNG...")
    img = render_dashboard()

    output_path = "dashboard_preview.png"
    img.save(output_path, "PNG")
    print(f"Saved to {output_path}")

    # Also save a high-res version
    img_hires = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
    img_hires.save("dashboard_preview_2x.png", "PNG")
    print("Saved high-res version to dashboard_preview_2x.png")


if __name__ == "__main__":
    main()
