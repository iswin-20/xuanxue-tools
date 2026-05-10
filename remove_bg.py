"""Remove background from images using flood-fill from corners for clean transparency."""
from PIL import Image, ImageDraw
import sys
from collections import deque

def flood_fill_remove_bg(path, tolerance=45):
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    pixels = img.load()
    visited = set()
    to_remove = set()
    
    # Sample background color from corners
    corners = [(0,0), (w-1,0), (0,h-1), (w-1,h-1)]
    bg_colors = [pixels[x,y][:3] for x,y in corners]
    
    def color_distance(c1, c2):
        return sum((a-b)**2 for a,b in zip(c1, c2)) ** 0.5
    
    def is_bg(r, g, b):
        return any(color_distance((r,g,b), bg) < tolerance for bg in bg_colors)
    
    # BFS from edges
    queue = deque()
    # Add all edge pixels as starting points
    for x in range(w):
        queue.append((x, 0))
        queue.append((x, h-1))
    for y in range(h):
        queue.append((0, y))
        queue.append((w-1, y))
    
    while queue:
        x, y = queue.popleft()
        if (x, y) in visited:
            continue
        if x < 0 or x >= w or y < 0 or y >= h:
            continue
        visited.add((x, y))
        
        r, g, b, a = pixels[x, y]
        if is_bg(r, g, b):
            to_remove.add((x, y))
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = x+dx, y+dy
                if 0 <= nx < w and 0 <= ny < h and (nx,ny) not in visited:
                    queue.append((nx, ny))
    
    # Apply transparency
    for x, y in to_remove:
        pixels[x, y] = (0, 0, 0, 0)
    
    # Smooth edges - make border pixels semi-transparent
    for x, y in to_remove:
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < w and 0 <= ny < h and (nx,ny) not in to_remove:
                r, g, b, a = pixels[nx, ny]
                if a > 0:
                    pixels[nx, ny] = (r, g, b, max(0, a - 60))
    
    img.save(path)
    print(f"Done: {path} — removed {len(to_remove)} background pixels")

if __name__ == "__main__":
    for f in sys.argv[1:]:
        flood_fill_remove_bg(f)
