from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 800})
    pg.goto("https://ramonsierrarey.github.io/liga_vcm/", wait_until="networkidle")
    pg.wait_for_timeout(15000)
    pg.screenshot(path="shot.png")
    for f in pg.frames:
        print(f.url, "|", f.inner_text("body")[:300].replace("\n", " "))
    b.close()
